#!/usr/bin/env python3

'''Development script, sends API calls to Kodi to disables addon and re-enable
100ms later. Used to detect changes when editing files directly in ~/.kodi.
Not included in packaged zip.
'''

# pylint: disable=duplicate-code

import os
import json
import time
import requests


def set_enabled_state(state):
    '''Takes bool, sends API call to enable addon if True, disable if False.'''
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
            f"{os.environ['KODI_JSON_RPC_URL']}?request",
            headers={'Content-Type': 'application/json'},
            data=json.dumps(command),
            timeout=2
        )
    except requests.exceptions.ConnectionError:
        print("Connection error when exiting Kodi")


if __name__ == "__main__":
    set_enabled_state(False)
    time.sleep(0.1)
    set_enabled_state(True)
