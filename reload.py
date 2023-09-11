#!/usr/bin/env python3

import os
import json
import shutil
import sqlite3
import zipfile
import requests

pwd = os.path.dirname(os.path.realpath(__file__))
git = os.path.split(pwd)[0]


def uninstall_addon():
    # Open addons database
    conn = sqlite3.connect("/home/jamedeus/.kodi/userdata/Database/Addons33.db")
    c = conn.cursor()

    # Delete addon from database
    c.execute("DELETE FROM installed WHERE addonID=?", ("script.record.button",))
    conn.commit()
    conn.close()

    # Delete addon dir from Kodi user dir
    try:
        shutil.rmtree("/home/jamedeus/.kodi/addons/script.record.button/")
    except FileNotFoundError:
        pass

    # Clear kodi log
    try:
        os.remove("/home/jamedeus/.kodi/temp/kodi.log")
    except FileNotFoundError:
        pass


# Send API call to close Kodi
def exit_kodi():
    command = {
        "jsonrpc": "2.0",
        "method": "Application.Quit",
        "id": 1
    }
    try:
        requests.post(
            'http://192.168.1.216:8998/jsonrpc?request',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(command)
        )
    except requests.exceptions.ConnectionError:
        print("Connection error when exiting Kodi")


# Re-zip repository, write to ~/test.zip
def re_zip_addon():
    # Create zip file and get handler
    zip_path = os.path.join(os.path.expanduser("~/"), "test.zip")
    zip_handler = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)

    # Add all repo files to zip without including repo dir
    for root, dirs, files in os.walk(pwd):
        for file in files:
            # Don't add this script
            if file == "reload.py":
                continue

            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, os.path.join(pwd, '..'))
            zip_handler.write(abs_path, rel_path)

    zip_handler.close()


if __name__ == "__main__":
    exit_kodi()
    uninstall_addon()
    re_zip_addon()
