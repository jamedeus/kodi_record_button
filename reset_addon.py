#!/usr/bin/env python3

import os
import json
import shutil
import sqlite3
import requests
from package_addon import zip_addon


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

    # Delete addon_data dir (contains output clips, database)
    try:
        shutil.rmtree("/home/jamedeus/.kodi/userdata/addon_data/script.record.button/")
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


if __name__ == "__main__":
    exit_kodi()
    uninstall_addon()
    zip_addon()
