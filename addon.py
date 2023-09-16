import os
import time
import xbmc
import json
import string
import ffmpeg
import random
import socket
import xbmcvfs
import xbmcgui
import datetime
import xbmcaddon
import threading
from wsgiref.simple_server import make_server, WSGIServer
from flask import Flask, request, render_template, jsonify, send_from_directory
 
# Read currently-playing info
player = xbmc.Player()

# Get absolute paths to addon_data dir, history file, output dir
addon = xbmcaddon.Addon()
profile_path = xbmc.translatePath(addon.getAddonInfo('profile'))
history_path = os.path.join(profile_path, 'history.json')
output_path = os.path.join(profile_path, 'output')

# Create addon_data dir and output dir if they don't exist
if not xbmcvfs.exists(profile_path):
    xbmcvfs.mkdir(profile_path)
if not xbmcvfs.exists(output_path):
    xbmcvfs.mkdir(output_path)


app = Flask(__name__, static_url_path='', static_folder='node_modules')

# Disable template caching TODO remove in prod
app.jinja_env.cache = {}


# Serve non-node_modules static files
# TODO remove in prod
@app.get("/static/<path:filename>")
def static_serve(filename):
    return send_from_directory('static', filename)


@app.get("/")
def serve():
    return render_template('index.html')


@app.get("/get_playtime")
def get_playtime():
    return jsonify(player.getTime())


@app.get("/get_playing_now")
def get_playing_now():
    try:
        video_info_tag = player.getVideoInfoTag()
        show = video_info_tag.getTVShowTitle()
        episode_title = video_info_tag.getTitle()
        episode_number = video_info_tag.getEpisode()
        season_number = video_info_tag.getSeason()

        payload = {
            "title": episode_title,
            "subtext": f"{show} - Season {season_number} - Episode {episode_number}"
        }
        return jsonify(payload)
    except RuntimeError:
        return jsonify({"title": "Nothing", "subtext": ""})


@app.post("/submit")
def submit():
    # Get stop time immediately
    stop_time = player.getTime()

    # Parse post body, calculcate clip duration
    data = request.get_json()
    duration = stop_time - float(data["startTime"])

    # Generate random 16 char string
    filename = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))

    # Generate
    try:
        gen_mp4(player.getPlayingFile(), data["startTime"], str(duration), filename)
        return jsonify(f'{filename}.mp4')

    except ffmpeg.Error as e:
        xbmc.log("Failed to generate file:", xbmc.LOGERROR)
        xbmc.log(str(e.stderr, "utf-8"), xbmc.LOGERROR)
        # Return the captured stderr from the ffmpeg process
        return jsonify({'error': 'Unable to generate file, see logs for details'}), 500


def gen_mp4(source, start_time, duration, filename):
    xbmc.log(f"Generating clip of {source}", level=xbmc.LOGINFO)
    xbmc.log(f"Start time = {start_time}, duration = {duration}, output file = {filename}", level=xbmc.LOGINFO)
    # Create MP4
    ffmpeg.input(
        source
    ).output(
        os.path.join(output_path, f'{filename}.mp4'),
        ss=start_time,
        t=duration,
        vcodec="libx264",
        crf="30",
        acodec="aac",
        ac="2"
    ).run(overwrite_output=True, capture_stderr=True)

    # Write params to history file
    log_generated_file(source, start_time, duration, filename)


@app.get('/download/<filename>')
def download(filename):
    return send_from_directory(output_path, filename, as_attachment=True)


@app.get('/get_history')
def get_history():
    return jsonify(load_history())


@app.post('/delete')
def delete():
    filename = request.get_json()

    # If file exists on disk, delete
    if xbmcvfs.exists(os.path.join(output_path, filename)):
        xbmcvfs.delete(os.path.join(output_path, filename))

    # Remove from history file
    history = load_history()
    history = {i: history[i] for i in history if history[i]['output'] != filename}
    save_history(history)

    return (f"{filename} deleted", 200)


@app.post('/rename')
def rename():
    # Parse old and new filename from payload
    data = request.get_json()
    old = data['old']
    new = data['new']

    # Add extension if missing
    if not new.lower().endswith('.mp4'):
        new = f'{new}.mp4'

    # Return error if file with same name exists
    if is_duplicate(new):
        return (jsonify({'error': f'File named {new} already exists'}), 409)

    # If file exists on disk, rename
    if xbmcvfs.exists(os.path.join(output_path, old)):
        xbmcvfs.rename(os.path.join(output_path, old), os.path.join(output_path, new))

    # Change name in history file
    history = load_history()
    for i in history:
        if history[i]['output'] == old:
            history[i]['output'] = new
            break
    save_history(history)

    return jsonify({'filename': new})


# Takes filename, returns True if it exists on disk or in history,
# otherwise returns False if unique
def is_duplicate(filename):
    if filename in os.listdir(output_path):
        return True

    history = load_history()
    for i in history:
        if filename == history[i]['output']:
            return True

    return False


# Returns current timestamp, used as key in history file
def get_timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')


# Returns contents of history.json
def load_history():
    if not xbmcvfs.exists(history_path):
        return {}

    with xbmcvfs.File(history_path, 'r') as file:
        return json.load(file)


# Takes history dict, writes to history.json
def save_history(history):
    with xbmcvfs.File(history_path, 'w') as file:
        json.dump(history, file)


# Takes same arguments as gen_mp4, writes entry to history.json
def log_generated_file(source, start_time, duration, filename):
    history = load_history()
    history[get_timestamp()] = {
        'source': source,
        'output': f'{filename}.mp4',
        'start_time': start_time,
        'duration': duration
    }
    save_history(history)


# Detect when user changes settings in GUI
class SettingsMonitor(xbmc.Monitor):
    def __init__(self):
        self.changed = False
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        xbmc.log("Settings were changed, restarting flask", xbmc.LOGINFO)
        self.changed = True


# Starts flask, returns server object so it can be stopped later
def run_server():
    # Read from settings.xml
    host = addon.getSetting('flask_host')
    port = int(addon.getSetting('flask_port'))

    # Check if address is available, wait until released
    if not address_available(host, port):
        xbmc.log(f"Address {host}:{port} is in use, waiting...")
        wait_for_address_release(host, port)

    # Create WSGIServer serving flask app on host:port
    httpd = make_server(host, port, app, server_class=WSGIServer)

    # Run server in new thread
    def start_server():
        httpd.serve_forever()
    server_thread = threading.Thread(target=start_server)
    server_thread.start()

    return httpd


# Returns True if host:port is available, False if in use
def address_available(host, port):
    xbmc.log(f"Checking {host}:{port} availablility...", xbmc.LOGINFO)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return not s.connect_ex((host, port)) == 0


# Check if host:port is available every 5 seconds, return when available
def wait_for_address_release(host, port):
    while not address_available(host, port):
        xbmc.log(f"Waiting for {host}:{port} to open...", xbmc.LOGINFO)
        time.sleep(5)
    xbmc.log(f"Address {host}:{port} released")


def show_notification(title, message, display_time=5000, icon=xbmcgui.NOTIFICATION_INFO):
    xbmcgui.Dialog().notification(title, message, icon, display_time)


if __name__ == '__main__':
    # Start flask server in thread
    server_instance = run_server()
    show_notification(
        "Record Button",
        f"Available at http://{addon.getSetting('flask_host')}:{addon.getSetting('flask_port')}"
    )

    # Monitor for user settings changes
    monitor = SettingsMonitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break

        # Restart flask if user made changes
        elif monitor.changed:
            xbmc.log("Restarting flask...", xbmc.LOGINFO)
            show_notification("Record Button", "Restarting web server")
            # Shut down old server to release address
            server_instance.shutdown()
            server_instance.server_close()
            xbmc.log("Old server stopped", xbmc.LOGINFO)
            # Start new server
            server_instance = run_server()
            xbmc.log("Finished restarting flask...", xbmc.LOGINFO)
            show_notification("Record Button", "Finished starting web server")
            monitor.changed = False
