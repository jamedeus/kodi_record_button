#!/usr/bin/env python3

'''Development server used to serve frontend and test changes without
rebuilding and reinstalling the addon. Not included in packaged zip.
Database contents are mocked by editing test_history.json.
'''

import os
import json
import time
import string
import random
import datetime
from flask import Flask, request, render_template, jsonify, send_from_directory


app = Flask(__name__, static_url_path='', static_folder='node_modules')


@app.get("/static/<path:filename>")
def static_serve(filename):
    '''Serves javascript static files used by frontend.'''
    return send_from_directory('static', filename)


@app.get("/")
def serve():
    '''Serves webapp.'''
    return render_template('index.html')


@app.get("/get_playing_now")
def get_playing_now():
    '''Returns mock playing now payload.'''
    return jsonify({"title": "Nothing", "subtext": "Season 1 Episode 1"})


@app.get('/get_history')
def get_history():
    '''Returns mock JSON with existing clips, used to populate history menu.'''
    history = load_history()
    payload = [(key, value["output"]) for key, value in history.items()]
    return jsonify(payload)


@app.get("/get_playtime")
def get_playtime():
    '''Returns mock timestamp to allow recording animation to start.'''
    return jsonify('12:34')


@app.post("/submit")
def submit():
    '''Waits 2 seconds to allow loading animation to appear, returns random
    filename to allow download button to appear.
    '''
    time.sleep(1)
    filename = ''.join(
        random.choice(string.ascii_letters + string.digits)
        for _ in range(16)
    )
    return jsonify(f'{filename}.mp4')


@app.post('/delete')
def delete():
    '''Takes JSON payload containing existing clip filename, deletes from
    test_history.json.
    '''

    filename = request.get_json()

    # Remove from history file
    history = load_history()
    history = {i: history[i] for i in history if history[i]['output'] != filename}
    save_history(history)

    return (f"{filename} deleted", 200)


@app.post('/rename')
def rename():
    '''Takes JSON payload with "old" and "new" keys, updates test_history.json.'''

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

    # Change name in history file
    history = load_history()
    for i in history:
        if history[i]['output'] == old:
            history[i]['output'] = new
            break
    save_history(history)
    return jsonify({'filename': new})


@app.post("/regenerate")
def regenerate():
    '''Waits 2 seconds to allow frontend animation to run, returns filename.'''
    time.sleep(2)
    filename = request.get_json()
    return jsonify(f'{filename}.mp4')


def is_duplicate(filename):
    '''Takes filename, returns True if it exists in test_history.json or on
    disk, returns False if filename is unique.
    '''
    if filename in os.listdir():
        return True

    history = load_history()
    for i in history:
        if filename == history[i]['output']:
            return True

    return False


def get_timestamp():
    '''Returns current timestamp, used as key in test_history.json.'''
    return datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')


def load_history():
    '''Returns contents of test_history.json or empty dict if not found.'''
    if not os.path.exists('test_history.json'):
        return {}

    with open('test_history.json', 'r', encoding='utf-8') as file:
        return json.load(file)


def save_history(history):
    '''Takes history dict, writes to test_history.json.'''
    with open('test_history.json', 'w', encoding='utf-8') as file:
        json.dump(history, file)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8125, debug=True)
