'''Contains paths to sqlite database and QR code shown in startup notification.'''

import os
import xbmcvfs
import xbmcaddon


# Get absolute paths to addon source dir + addon_data dir
addon = xbmcaddon.Addon()
addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
profile_path = xbmcvfs.translatePath(addon.getAddonInfo('profile'))

# Create addon_data dir if it doesn't exist
if not xbmcvfs.exists(profile_path):
    xbmcvfs.mkdir(profile_path)

# Get absolute path to output directory, create if it doesn't exist
output_path = os.path.join(profile_path, 'output')
if not xbmcvfs.exists(output_path):
    xbmcvfs.mkdir(output_path)

# Get absolute path to sqlite3 database
database_path = os.path.join(profile_path, 'history.db')

# Get absolute path to web interface QR code link
qr_path = os.path.join(profile_path, 'qr_code_link.png')
