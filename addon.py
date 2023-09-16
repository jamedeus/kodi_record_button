import time
import xbmc
import socket
import xbmcgui
import xbmcaddon
import threading
from wsgiref.simple_server import make_server, WSGIServer
from flask_backend import app

# Used to read settings.xml
addon = xbmcaddon.Addon()


# Detect when user changes settings in GUI
class SettingsMonitor(xbmc.Monitor):
    def __init__(self):
        self.changed = False
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        xbmc.log("Settings were changed, restarting flask", xbmc.LOGINFO)
        self.changed = True


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


# Takes host and port, returns True if available, False if in use
def address_available(host, port):
    xbmc.log(f"Checking {host}:{port} availablility...", xbmc.LOGINFO)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return not s.connect_ex((host, port)) == 0


# Takes host and port, check if available every 5 seconds, return True when available
# If timeout (seconds) given returns False after timeout seconds
def wait_for_address_release(host, port, timeout=None):
    start_time = time.time()
    while not address_available(host, port):
        xbmc.log(f"Waiting for {host}:{port} to open...", xbmc.LOGINFO)
        time.sleep(5)
        if timeout and time.time() - start_time > timeout:
            xbmc.log(f"Timed out waiting for {host}:{port}", xbmc.LOGINFO)
            return False

    xbmc.log(f"Address {host}:{port} available", xbmc.LOGINFO)
    return True


# Starts flask server, returns server object so it can be stopped later
def run_server():
    # Read address from settings.xml
    host = addon.getSetting('flask_host')
    port = int(addon.getSetting('flask_port'))

    # Check if address is available, wait up to 2 minutes
    if not address_available(host, port):
        # If address still in use after 2 minutes show error
        if not wait_for_address_release(host, port, 120):
            address_unavailable_error(host, port)
            return None

    # Create WSGIServer serving flask app on host:port
    httpd = make_server(host, port, app, server_class=WSGIServer)

    # Run server in new thread
    def start_server():
        httpd.serve_forever()
    server_thread = threading.Thread(target=start_server)
    server_thread.start()

    return httpd


def main():
    # Get object used to detect settings changes.
    # Must instantiate before showing error - monitor detects when settings are opened and
    # closed, if settings are already open when instantiated no changes will be detected.
    monitor = SettingsMonitor()

    # Confirm port is available before starting web server
    host = addon.getSetting('flask_host')
    port = int(addon.getSetting('flask_port'))
    if address_available(host, port):
        # Start flask server in new thread
        server_instance = run_server()
        xbmc.log(f"Web server on {host}:{port}", xbmc.LOGINFO)
        show_notification("Record Button", f"Available at http://{host}:{port}")

    # If port not available show error message with link to settings
    else:
        address_unavailable_error(host, port)
        server_instance = None

    # Monitor for settings changes, restart server when user makes changes
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break

        # Restart flask if user made changes
        elif monitor.changed:
            xbmc.log("Restarting flask...", xbmc.LOGINFO)
            show_notification("Record Button", "Restarting web server")
            # Shut down old server to release address
            try:
                server_instance.shutdown()
                server_instance.server_close()
                xbmc.log("Old server stopped", xbmc.LOGINFO)
            except AttributeError:
                pass
            # Start new server
            server_instance = run_server()
            xbmc.log("Finished restarting flask...", xbmc.LOGINFO)
            show_notification("Record Button", "Finished starting web server")
            monitor.changed = False


if __name__ == '__main__':
    main()
