[![pipeline status](https://gitlab.com/jamedeus/kodi_record_button/badges/master/pipeline.svg)](https://gitlab.com/jamedeus/kodi_record_button/-/commits/master)
[![coverage report](https://gitlab.com/jamedeus/kodi_record_button/badges/master/coverage.svg)](https://gitlab.com/jamedeus/kodi_record_button/-/commits/master)

# Record Button Addon

This addon serves a webapp with a record button used to generate clips from currently-playing media.

A notification is shown at startup with a QR code link to the webapp. Simply point your phone camera at the notifiation to open the app. The default address is `http://<kodi-host-ip>:8123`, this can be changed in settings.

While media is playing in Kodi simply hold down the button to start recording and release when done. A download button will appear on the page once the mp4 has been generated.

Previously-generated clips can be downloaded from the history menu at the bottom of the page.

## Installation

To build the addon install the frontend dependencies:
```
npm install
```

Then package the addon by running the included script:
```
reset_addon.py
```

This will write a file `test.zip` to your home folder.

Launch Kodi and go to `Settings -> Add-ons -> Install from zip file`, then navigate to `test.zip` in your home folder.

## Unit tests

Paste these commands while in the repo root directory:
```
coverage run --source='.' --omit='tests/*,dev_server.py,play_test_file.py,refresh.py,reset_addon.py' -m unittest discover tests
coverage report -m --precision=1
```
