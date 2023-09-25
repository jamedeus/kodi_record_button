import xbmc
import xbmcgui
import xbmcaddon

# Used to read settings.xml
addon = xbmcaddon.Addon()


# Takes title and message strings (optional: timeout ms, icon)
# Show notification in top-right corner
def show_notification(title, message, display_time=5000, icon=xbmcgui.NOTIFICATION_INFO):
    xbmcgui.Dialog().notification(title, message, icon, display_time)


# Takes title and message strings
# Show full-size popup with button that opens addon settings
def show_error(title, message):
    dialog = xbmcgui.Dialog()
    choice = dialog.yesno(title, message, yeslabel="Open Settings", nolabel="Cancel")
    # Redirect to addon settings if option selected
    if choice:
        addon.openSettings()


# Takes host and port, shows error popup with link to addon settings
def address_unavailable_error(host, port):
    show_error(
        "Record Button",
        f"Unable to start - the address {host}:{port} is not available, please change it in settings"
    )
    xbmc.log(f"Unable to start web server, {host}:{port} not available", xbmc.LOGINFO)
