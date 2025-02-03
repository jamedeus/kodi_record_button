import os
import time
import xbmc
import string
import ffmpeg
import random
import socket
import xbmcgui
import segno
import xbmcaddon
import threading
from socketserver import ThreadingMixIn
from sqlalchemy.exc import OperationalError
from wsgiref.simple_server import make_server, WSGIServer
from flask import Flask, request, render_template, jsonify, send_from_directory
from paths import output_path, qr_path
from kodi_gui import address_unavailable_error, generate_notification, show_notification
from database import (
    log_generated_file,
    load_history_json,
    load_history_search_results,
    rename_entry,
    delete_entry,
    is_duplicate,
    get_orm_entry,
    autodelete
)


# Read currently-playing info
player = xbmc.Player()


app = Flask(__name__, static_url_path='', static_folder='node_modules')

# Disable template caching TODO remove in prod
app.jinja_env.cache = {}


# Multi-threaded WSGIServer
class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    pass


# Takes host and port, returns True if available, False if in use
def address_available(host, port):
    xbmc.log(f"Checking {host}:{port} availablility...", xbmc.LOGINFO)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return not s.connect_ex((host, port)) == 0


# Takes host and port, check if available every 5 seconds, return True when available
# If timeout (seconds) given returns False after timeout seconds
def wait_for_address_release(host, port, timeout=None):
    start_time = time.time()
    while not address_available(host, port):
        show_notification(
            "Record Button",
            f"Configured address {host}:{port} is not available, waiting...",
            5000,
            xbmcgui.NOTIFICATION_WARNING
        )
        xbmc.log(f"Waiting for {host}:{port} to open...", xbmc.LOGINFO)
        time.sleep(5)
        if timeout and time.time() - start_time > timeout:
            xbmc.log(f"Timed out waiting for {host}:{port}", xbmc.LOGINFO)
            return False

    xbmc.log(f"Address {host}:{port} available", xbmc.LOGINFO)
    return True


# Starts flask server, returns server object so it can be stopped later
# Optional timeout arg determines how many seconds to wait if address unavailable
def run_server(timeout=120):
    # Read address from settings.xml
    # Reinstantiate Addon() to avoid caching issue
    host = xbmcaddon.Addon().getSetting('flask_host')
    port = int(xbmcaddon.Addon().getSetting('flask_port'))

    # Check if address is available, wait timeout seconds (default = 2 minutes)
    if not address_available(host, port):
        # Show error if address still in use after timeout seconds
        if not wait_for_address_release(host, port, timeout):
            address_unavailable_error(host, port)
            return None

    # Create WSGIServer serving flask app on host:port
    httpd = make_server(host, port, app, server_class=ThreadedWSGIServer)

    # Run server in new thread
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.start()
    xbmc.log(f"Web server started on {host}:{port}", xbmc.LOGINFO)

    # Run autodelete if enabled
    if xbmcaddon.Addon().getSetting('autodelete') == 'true':
        xbmc.log("Autodelete enabled", xbmc.LOGINFO)
        autodelete()

    # Generate web interface QR code link
    generate_qr_code_link(xbmc.getIPAddress(), port)

    return httpd


# Takes IP and port, creates QR code link, writes PNG to userdata dir
def generate_qr_code_link(ip, port):
    qr = segno.make(f"http://{ip}:{port}")
    qr.save(qr_path, scale=8, border=1)


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
    try:
        playtime = player.getTime()
        return jsonify(playtime)
    except RuntimeError:
        return jsonify('Nothing playing'), 500


@app.get("/get_playing_now")
def get_playing_now():
    try:
        video_info_tag = player.getVideoInfoTag()

        # TV shows: add subext with show name + season and episode numbers
        if video_info_tag.getMediaType() == "episode":
            show = video_info_tag.getTVShowTitle()
            episode_number = video_info_tag.getEpisode()
            season_number = video_info_tag.getSeason()
            subtext = f"{show} - Season {season_number} - Episode {episode_number}"
        # Movies: no subtext
        else:
            subtext = ""

        payload = {
            "title": video_info_tag.getTitle(),
            "subtext": subtext
        }
        return jsonify(payload)
    except RuntimeError:
        return jsonify({"title": "Nothing", "subtext": ""})


@app.post("/submit")
def submit():
    try:
        # Get stop time immediately
        stop_time = player.getTime()

        # Parse post body, calculcate clip duration
        data = request.get_json()
        duration = stop_time - float(data["startTime"])

        # Generate random 16 char string
        filename = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))

        # Get show and episode names for history search
        video_info_tag = player.getVideoInfoTag()
        show_name = video_info_tag.getTVShowTitle()
        episode_name = video_info_tag.getTitle()

        source = player.getPlayingFile()

        # Generate, write params to database and return filename if successful
        if gen_mp4(source, data["startTime"], str(duration), filename, show_name, episode_name):
            log_generated_file(source, data["startTime"], str(duration), filename, show_name, episode_name)
            generate_notification()
            return jsonify(f'{filename}.mp4')

    except RuntimeError as e:
        xbmc.log("Failed to generate file due to Kodi RuntimeError:", xbmc.LOGERROR)
        xbmc.log(e.args[0], xbmc.LOGERROR)

    except OperationalError as e:
        xbmc.log("Failed to generate file due to SQL error:", xbmc.LOGERROR)
        xbmc.log(e.args[0], xbmc.LOGERROR)

    return jsonify({'error': 'Unable to generate file, see Kodi logs for details'}), 500


@app.post("/regenerate")
def regenerate():
    try:
        # Read filename from post body, get ORM entry from database
        filename = request.get_json()
        xbmc.log(f"Regenerating {filename}", xbmc.LOGINFO)
        entry = get_orm_entry(filename)

        # Prevent double extension
        output = filename.replace('.mp4', '')

        # Regenerate with params from database, return filename if successful
        if gen_mp4(entry.source, entry.start_time, entry.duration, output, entry.show_name, entry.episode_name):
            return jsonify(f'{filename}.mp4')

    except OperationalError as e:
        xbmc.log("Failed to regenerate file due to SQL error:", xbmc.LOGERROR)
        xbmc.log(e.args[0], xbmc.LOGERROR)

    return jsonify({'error': 'Unable to generate file, see Kodi logs for details'}), 500


# Return bit/s calculated from user-configured quality (MB per minute)
def get_bitrate():
    mb_per_min = int(xbmcaddon.Addon().getSetting('mb_per_min'))
    return int(mb_per_min * 1024 * 1024 * 8 / 60)


def gen_mp4(source, start_time, duration, filename, show_name, episode_name):
    try:
        # Get target bitrate from quality setting, input file original bitrate
        bitrate = get_bitrate()

        # Clamp bitrate to input file original bitrate
        original_bitrate = int(ffmpeg.probe(source)['format']['bit_rate'])
        bitrate = min(bitrate, original_bitrate)

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
            b=str(bitrate),
            acodec="aac",
            ac="2"
        ).run(overwrite_output=True, capture_stderr=True)

        return True

    except ffmpeg.Error as e:
        xbmc.log("Failed to generate file due to ffmpeg error:", xbmc.LOGERROR)
        xbmc.log(str(e.stderr, "utf-8"), xbmc.LOGERROR)

    return False


@app.get('/download/<filename>')
def download(filename):
    return send_from_directory(output_path, filename, as_attachment=True)


@app.get('/get_history')
def get_history():
    return jsonify(load_history_json())


@app.post('/search_history')
def search_history():
    search_string = request.get_json()
    return jsonify(load_history_search_results(search_string))


@app.post('/delete')
def delete():
    filename = request.get_json()

    # Delete from disk and database
    delete_entry(filename)

    return (f"{filename} deleted", 200)


@app.post('/rename')
def rename():
    # Parse old and new filename from payload
    data = request.get_json()
    old = data['old']
    new = data['new'].strip()

    # Add extension if missing
    if not new.lower().endswith('.mp4'):
        new = f'{new}.mp4'

    # Return error if file with same name exists
    if is_duplicate(new):
        return (jsonify({'error': f'File named {new} already exists'}), 409)

    # Rename on disk and in database
    rename_entry(old, new)

    return jsonify({'filename': new})
