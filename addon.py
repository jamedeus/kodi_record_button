import os
import re
import xbmc
import ffmpeg
import xbmcgui
import xbmcaddon
from flask import Flask, request, render_template, jsonify, send_from_directory

 
addon       = xbmcaddon.Addon()
addonname   = addon.getAddonInfo('name')

# Read currently-playing info
player = xbmc.Player()

# Set a string variable to use 
#line1 = "Hello World! We can write anything we want here Using Python"

## Launch a dialog box in kodi showing the string variable 'line1' as the contents
#xbmcgui.Dialog().ok(addonname, line1)


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

    data = request.get_json()
    duration = stop_time - float(data["startTime"])

    # Get user-set filename (or random 16 char string if user left blank)
    filename = re.sub(r'[^A-Za-z0-9\s._-]', '', data["filename"])

    # Remove extension if present (prevents double extension)
    if filename.endswith(".mp4"):
        filename = filename[:-4]

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


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory('/var/tmp/kodi_addon_test', filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8123, debug=False)
