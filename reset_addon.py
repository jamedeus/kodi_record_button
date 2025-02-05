#!/usr/bin/env python3

'''Development script, sends Kodi API call to exit Kodi, uninstalls addon, and
repackages addon in working directory. Not included in packaged zip.
'''

# pylint: disable=duplicate-code

import os
import json
import shutil
import sqlite3
import requests
from package_addon import zip_addon


def uninstall_addon():
    '''Remove Kodi Record Button addon from Kodi database and delete all files
    from userdata directory (simulate uninstalling manually).
    '''

    # Open addons database
    conn = sqlite3.connect(f"{os.environ['HOME']}/.kodi/userdata/Database/Addons33.db")
    c = conn.cursor()

    # Delete addon from database
    c.execute("DELETE FROM installed WHERE addonID=?", ("script.record.button",))
    conn.commit()
    conn.close()

    # Delete addon dir from Kodi user dir
    try:
        shutil.rmtree(f"{os.environ['HOME']}/.kodi/addons/script.record.button/")
    except FileNotFoundError:
        pass

    # Delete addon_data dir (contains output clips, database)
    try:
        shutil.rmtree(f"{os.environ['HOME']}/.kodi/userdata/addon_data/script.record.button/")
    except FileNotFoundError:
        pass

    # Clear kodi log
    try:
        os.remove(f"{os.environ['HOME']}/.kodi/temp/kodi.log")
    except FileNotFoundError:
        pass


def exit_kodi():
    '''Sends API call to exit Kodi.'''
    command = {
        "jsonrpc": "2.0",
        "method": "Application.Quit",
        "id": 1
    }
    try:
        requests.post(
            f"{os.environ['KODI_JSON_RPC_URL']}?request",
            headers={'Content-Type': 'application/json'},
            data=json.dumps(command),
            timeout=2
        )
    except requests.exceptions.ConnectionError:
        print("Connection error when exiting Kodi")


if __name__ == "__main__":
    exit_kodi()
    uninstall_addon()
    zip_addon()
