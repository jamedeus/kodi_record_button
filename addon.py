import os
import xbmc
import json
import string
import ffmpeg
import random
import xbmcvfs
import datetime
import xbmcaddon
from flask import Flask, request, render_template, jsonify, send_from_directory
 
# Read currently-playing info
player = xbmc.Player()

# Get path to addon_data dir, history file
addon = xbmcaddon.Addon()
profile_path = addon.getAddonInfo('profile')
history_path = os.path.join(profile_path, 'history.json')

# Create addon_data dir if doesn't exist
if not xbmcvfs.exists(profile_path):
    xbmcvfs.mkdir(profile_path)


app = Flask(__name__, static_url_path='', static_folder='node_modules')

# Disable template caching TODO remove in prod
app.jinja_env.cache = {}


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
    gen_mp4(player.getPlayingFile(), data["startTime"], str(duration), filename)

    return jsonify(f'{filename}.mp4')


def gen_mp4(source, start_time, duration, filename):
    xbmc.log(f"Generating clip of {source}", level=xbmc.LOGINFO)
    xbmc.log(f"Start time = {start_time}, duration = {duration}, output file = {filename}", level=xbmc.LOGINFO)
    # Create MP4
    # Currently fails here with: ffmpeg._run.Error: ffmpeg error (see stderr output for detail)
    ffmpeg.input(
        source
    ).output(
        # TODO temporary test location, make configurable in addon menu
        os.path.join('/var/tmp/kodi_addon_test/', f'{filename}.mp4'),
        ss=start_time,
        t=duration,
        vcodec="libx264",
        crf="30",
        acodec="aac",
        ac="2"
    ).run(overwrite_output=True)

    # Write params to history file
    log_generated_file(source, start_time, duration, filename)


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory('/var/tmp/kodi_addon_test', filename, as_attachment=True)


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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8123, debug=False)
