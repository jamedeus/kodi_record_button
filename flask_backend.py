import os
import xbmc
import string
import ffmpeg
import random
import xbmcaddon
from sqlalchemy.exc import OperationalError
from flask import Flask, request, render_template, jsonify, send_from_directory
from paths import output_path
from database import (
    log_generated_file,
    load_history_json,
    load_history_search_results,
    rename_entry,
    delete_entry,
    is_duplicate,
    get_older_than,
    bulk_delete,
    get_orm_entry
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


# Temporary workaround
@app.get('/autodelete')
def autodelete():
    # Read user settings (number of days, whether to keep renamed files)
    days = int(xbmcaddon.Addon().getSetting('delete_after_days'))

    if xbmcaddon.Addon().getSetting('keep_renamed_files') == 'true':
        xbmc.log(f"Deleting clips older than {days} days (keeping renamed)", xbmc.LOGINFO)
        bulk_delete(get_older_than(days), True)

    else:
        xbmc.log(f"Deleting clips older than {days} days", xbmc.LOGINFO)
        bulk_delete(get_older_than(days), False)

    return jsonify('done')
