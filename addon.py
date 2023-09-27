import xbmc
from paths import qr_path
from database import replace_engine
from flask_backend import run_server
from kodi_gui import show_notification


# Detect when user changes settings in GUI
class SettingsMonitor(xbmc.Monitor):
    def __init__(self):
        self.changed = False
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        xbmc.log("Settings were changed, restarting flask", xbmc.LOGINFO)
        self.changed = True


def main():
    # Get object used to detect settings changes.
    # Must instantiate before showing error - monitor detects when settings are opened and
    # closed, if settings are already open when instantiated no changes will be detected.
    monitor = SettingsMonitor()

    # Start flask server in new thread, don't wait for address if unavailable
    server_instance = run_server(timeout=1)
    if server_instance:
        # Show notification if server started successfully
        show_notification("Record Button", "Scan QR code to open webapp", 15000, qr_path)

    # Monitor for settings changes, restart server when user makes changes
    while not monitor.abortRequested():
        # Kodi shutting down, stop flask server
        if monitor.waitForAbort(1):
            if server_instance:
                server_instance.shutdown()
                server_instance.server_close()
            xbmc.log("Closed web server", xbmc.LOGINFO)
            break

        # Restart flask if user made changes
        elif monitor.changed:
            xbmc.log("Restarting flask...", xbmc.LOGINFO)
            show_notification("Record Button", "Restarting web server")

            # Shut down old server to release address
            if server_instance:
                server_instance.shutdown()
                server_instance.server_close()
                xbmc.log("Old server stopped", xbmc.LOGINFO)

            # Close old database and get new engine before starting new server thread
            xbmc.log("Restarting database...", xbmc.LOGINFO)
            replace_engine()
            xbmc.log("Finished restarting database", xbmc.LOGINFO)

            # Start new server (waits up to 2 minutes if address is unavailable)
            server_instance = run_server()
            xbmc.log("Finished restarting flask...", xbmc.LOGINFO)
            # Show notification with QR code link as icon
            show_notification("Record Button", "Finished starting web server", 10000, qr_path)
            monitor.changed = False


if __name__ == '__main__':
    main()
    xbmc.log("Addon exiting", xbmc.LOGINFO)
