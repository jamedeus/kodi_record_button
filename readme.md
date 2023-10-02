[![pipeline status](https://gitlab.com/jamedeus/kodi_record_button/badges/master/pipeline.svg)](https://gitlab.com/jamedeus/kodi_record_button/-/commits/master)
[![coverage report](https://gitlab.com/jamedeus/kodi_record_button/badges/master/coverage.svg)](https://gitlab.com/jamedeus/kodi_record_button/-/commits/master)
[![Latest Release](https://gitlab.com/jamedeus/kodi_record_button/-/badges/release.svg)](https://gitlab.com/jamedeus/kodi_record_button/-/releases)

# Kodi Record Button Addon

This addon serves a webapp that allows you to generate clips from media playing in Kodi. Just press and hold the record button to start recording and release it to stop. A download button will appear when the mp4 has been generated.

A notification is shown at startup with a QR code link to the webapp. Simply point your phone camera at the notification to open the app. The default address is `http://<kodi-host-ip>:8123`, this can be changed in settings.

Previously-generated clips can be downloaded from the history menu at the bottom of the page.

## Installation

Download the latest [release](https://gitlab.com/jamedeus/kodi_record_button/-/releases) zip, then launch Kodi and go to `Settings -> Add-ons -> Install from zip file`. See [Kodi Wiki](https://kodi.wiki/view/Add-on_manager#How_to_install_from_a_ZIP_file) for more details.

## Configuration

After installation the settings menu within Kodi can be used to:
- Change the IP and port where the webapp is accessed
- Set the output quality (Megabytes per minute of video)
- Enable autodelete to remove clips older than a certain number of days
- Enable/disable specific notifications
- Advanced: Use a SQL server instead of the default sqlite database (can be shared by multiple Kodi instances)

All settings changes are applied automatically, restarting Kodi is not necessary.

## Development

### Building the addon

Building the addon requires a unix-like system with python3.10, pip, and npm.

First install dependencies for the frontend by running:
```
npm install
```

Then run the included packaging script:
```
python3 package_addon.py
```

This will write a file called `kodi_record_button.zip` to your home folder. All python dependencies are installed automatically via pip and copied into the addon zip, no dependencies are required on the Kodi host.

### Unit tests

Running unit tests requires [pipenv](https://pipenv.pypa.io/en/latest/).

Paste the following commands in the repository root directory:
```
pipenv run coverage run --source='flask_backend,database' -m unittest discover tests
pipenv run coverage report -m --precision=1
```
