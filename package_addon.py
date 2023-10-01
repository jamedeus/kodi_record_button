#!/usr/bin/env python3

import os
import shutil
import zipfile

# Absolute path to repository root
pwd = os.path.dirname(os.path.realpath(__file__))

# Absolute path to venv site packages
lib = os.path.join(pwd, '.venv', 'lib', 'python3.10', 'site-packages')

exclude_from_zip = [
    '.coverage',
    '.env',
    '.gitignore',
    '.gitlab-ci.yml',
    'kodi_record_button.zip',
    'dev_server.py',
    'package_addon.py',
    'package.json',
    'package-lock.json',
    'Pipfile',
    'Pipfile.lock',
    'play_test_file.py',
    'refresh.py',
    'reset_addon.py',
    'tailwind.config.js',
    'test_history.json',
    'mock_kodi_modules.py',
    'test_database.py',
    'test_flask_backend.py'
]


# Zip entire repository (excluding development files)
# Creates kodi_record_button.zip in current working directory
def zip_addon():
    # Create zip file and get handler
    zip_handler = zipfile.ZipFile('kodi_record_button.zip', 'w', zipfile.ZIP_DEFLATED)

    # Add all repo files to zip without including repo dir
    for root, dirs, files in os.walk(pwd):
        # Skip .git and .venv
        if '.git' in root or '.venv' in root:
            continue

        for file in files:
            # Skip development scripts, config files, .pyc files
            if file in exclude_from_zip or file.endswith('.pyc'):
                continue

            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, os.path.join(pwd, '..'))
            zip_handler.write(abs_path, rel_path)

    # Add all pipenv dependencies
    for root, dirs, files in os.walk(lib):
        for file in files:
            abs_path = os.path.join(root, file)
            # Move dependencies to repository root where python can find them
            # Example: kodi_record_button/.venv/lib/python3.10/site-packages/sqlalchemy > kodi_record_button/sqlalchemy
            rel_path = os.path.join('kodi_record_button', os.path.relpath(abs_path, lib))
            zip_handler.write(abs_path, rel_path)

    zip_handler.close()


if __name__ == '__main__':
    # Create zip in current working directory
    zip_addon()
    # Move to home folder for easier installation
    shutil.move('kodi_record_button.zip', os.path.join(os.path.expanduser('~/'), 'kodi_record_button.zip'))
