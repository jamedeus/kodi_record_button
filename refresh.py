#!/usr/bin/env python3

import json
import time
import requests


# Takes bool, enables or disables addon
def set_enabled_state(state):
    command = {
        "jsonrpc": "2.0",
        "method": "Addons.SetAddonEnabled",
        "params": {
            "addonid": "script.record.button",
            "enabled": bool(state)
        },
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
    set_enabled_state(False)
    time.sleep(0.1)
    set_enabled_state(True)
