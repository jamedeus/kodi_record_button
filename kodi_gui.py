'''Functions used to display notifications and error popups within Kodi.'''

import xbmc
import xbmcgui
import xbmcaddon

# Used to read settings.xml
addon = xbmcaddon.Addon()


def show_notification(title, message, display_time=5000, icon=xbmcgui.NOTIFICATION_INFO):
    '''Takes title and message strings, shows notification in top-right corner.
    Optional timeout arg (milliseconds) changes visibility time (default 5,000).
    Optional icon arg (filesystem path) adds a custom icon.
    Skips notification if "notifications_enabled" setting if False.
    '''
    if xbmcaddon.Addon().getSetting('notifications_enabled') == 'true':
        xbmcgui.Dialog().notification(title, message, icon, display_time)


def show_error(title, message):
    '''Takes title and error message strings, shows full-size popup with
    button to open addon settings.
    '''
    dialog = xbmcgui.Dialog()
    choice = dialog.yesno(title, message, yeslabel="Open Settings", nolabel="Cancel")
    # Redirect to addon settings if option selected
    if choice:
        addon.openSettings()


def address_unavailable_error(host, port):
    '''Takes host and port, shows error popup with link to addon settings.
    Called when unable to start server because configured address is in use.
    '''
    show_error(
        "Record Button",
        f"Unable to start - the address {host}:{port} is not available, please change it in settings"  # pylint: disable=line-too-long
    )
    xbmc.log(f"Unable to start web server, {host}:{port} not available", xbmc.LOGINFO)


def autodelete_notification(number_deleted):
    '''Takes number of deleted files, shows autodelete notification.
    Skips notification if "autodelete_notification" setting if False.
    '''
    if xbmcaddon.Addon().getSetting('autodelete_notification') == 'true':
        show_notification(
            "Record Button",
            f"Automatically deleted {number_deleted} old clips",
            5000
        )


def generate_notification():
    '''Shows notification when finished generating a clip.
    Skips notification if "generate_notification" setting if False.
    '''
    if xbmcaddon.Addon().getSetting('generate_notification') == 'true':
        show_notification(
            "Record Button",
            "Finished generating clip",
            1000
        )
