import os
import xbmc
import string
import ffmpeg
import random
from flask import Flask, request, render_template, jsonify, send_from_directory
from paths import output_path
from database import (
    log_generated_file,
    load_history_json,
    load_history_search_results,
    rename_entry,
    delete_entry,
    is_duplicate
)

# Read currently-playing info
player = xbmc.Player()


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

    # Write params to database
    log_generated_file(source, start_time, duration, filename)


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
    new = data['new']

    # Add extension if missing
    if not new.lower().endswith('.mp4'):
        new = f'{new}.mp4'

    # Return error if file with same name exists
    if is_duplicate(new):
        return (jsonify({'error': f'File named {new} already exists'}), 409)

    # Rename on disk and in database
    rename_entry(old, new)

    return jsonify({'filename': new})
