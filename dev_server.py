#!/usr/bin/env python3

import os
import json
import datetime
from flask import Flask, request, render_template, jsonify, send_from_directory


app = Flask(__name__, static_url_path='', static_folder='node_modules')


# Serve non-node_modules static files
@app.get("/static/<path:filename>")
def static_serve(filename):
    return send_from_directory('static', filename)


@app.get("/")
def serve():
    return render_template('index.html')


@app.get("/get_playing_now")
def get_playing_now():
    return jsonify({"title": "Nothing", "subtext": "Season 1 Episode 1"})


@app.get('/get_history')
def get_history():
    return jsonify(load_history())


@app.post('/delete')
def delete():
    filename = request.get_json()

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

    # Change name in history file
    history = load_history()
    for i in history:
        if history[i]['output'] == old:
            history[i]['output'] = new
            break
    save_history(history)

    return jsonify({'filename': new})


# Returns current timestamp, used as key in history file
def get_timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')


# Returns contents of test_history.json
def load_history():
    if not os.path.exists('test_history.json'):
        return {}

    with open('test_history.json', 'r') as file:
        return json.load(file)


# Takes history dict, writes to test_history.json
def save_history(history):
    with open('test_history.json', 'w') as file:
        json.dump(history, file)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8125, debug=True)
