#!/usr/bin/env python3

'''Script used to package addon as kodi_record_button.zip.'''

import os
import sys
import shutil
import zipfile
import subprocess

# Absolute path to repository root
pwd = os.path.dirname(os.path.realpath(__file__))

# Absolute path to local site packages (installed automatically)
lib = os.path.join(pwd, '.zip_dependencies')

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
    'requirements.txt',
    'reset_addon.py',
    'tailwind.config.js',
    'test_history.json',
    'mock_kodi_modules.py',
    'test_database.py',
    'test_flask_backend.py'
]


def zip_addon():
    '''Zips entire repository (excluding development files).
    Creates kodi_record_button.zip in current working directory.
    '''

    # Build tailwind CSS
    subprocess.run('npm run build:css', shell=True, check=False)

    # Create zip file and get handler
    with zipfile.ZipFile('kodi_record_button.zip', 'w', zipfile.ZIP_DEFLATED) as zip_handler:

        # Add all repo files to zip without including repo dir
        for root, _, files in os.walk(pwd):
            # Skip .git and .zip_dependencies
            if '.git' in root or '.zip_dependencies' in root:
                continue

            for file in files:
                # Skip development scripts, config files, .pyc files
                if file in exclude_from_zip or file.endswith('.pyc'):
                    continue

                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, os.path.join(pwd, '..'))
                zip_handler.write(abs_path, rel_path)

        # Install dependencies to local site packages folder
        print("Installing python dependencies...\n")
        subprocess.run([
            sys.executable,
            '-m',
            'pip',
            'install',
            '--upgrade',
            '-r',
            'requirements.txt',
            '--target',
            lib
        ], check=False)

        # Clone ffmpeg-python repo and install (PyPi version outdated)
        subprocess.run([
            'git',
            'clone',
            'https://github.com/kkroening/ffmpeg-python.git'
        ], check=False)
        subprocess.run([
            sys.executable,
            '-m',
            'pip',
            'install',
            '--upgrade',
            './ffmpeg-python',
            '--target',
            lib
        ], check=False)
        shutil.rmtree('ffmpeg-python')

        # Add all dependencies to zip
        for root, _, files in os.walk(lib):
            for file in files:
                abs_path = os.path.join(root, file)
                # Move dependencies to repository root where python can find them
                # Example: kodi_record_button/.zip_dependencies/flask > kodi_record_button/flask
                rel_path = os.path.join('kodi_record_button', os.path.relpath(abs_path, lib))
                zip_handler.write(abs_path, rel_path)


if __name__ == '__main__':
    # Create zip in current working directory
    zip_addon()
    # Move to home folder for easier installation
    destination = os.path.join(os.path.expanduser('~/'), 'kodi_record_button.zip')
    shutil.move('kodi_record_button.zip', destination)
    print("\nDone")
    print(f"\nFinished addon: {destination}")
