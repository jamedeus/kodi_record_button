import os
import xbmc
import xbmcvfs
import xbmcaddon


# Get absolute paths to addon source dir + addon_data dir
addon = xbmcaddon.Addon()
addon_path = xbmc.translatePath(addon.getAddonInfo('path'))
profile_path = xbmc.translatePath(addon.getAddonInfo('profile'))

# Create addon_data dir if it doesn't exist
if not xbmcvfs.exists(profile_path):
    xbmcvfs.mkdir(profile_path)

# Get absolute path to output directory, create if it doesn't exist
output_path = os.path.join(profile_path, 'output')
if not xbmcvfs.exists(output_path):
    xbmcvfs.mkdir(output_path)

# Get absolute path to sqlite3 database
# Import database template from /resources if it doesn't exist
database_path = os.path.join(profile_path, 'history.db')
if not xbmcvfs.exists(database_path):
    template_path = os.path.join(addon_path, 'resources', 'history.db')
    xbmcvfs.copy(template_path, database_path)
