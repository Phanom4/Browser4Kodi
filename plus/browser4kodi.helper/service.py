import xbmc
import xbmcaddon

monitor = xbmc.Monitor()

xbmc.log("Browser4Kodi Helper: Service gestartet", xbmc.LOGINFO)

while not monitor.abortRequested():
    if monitor.waitForAbort(5):
        break

xbmc.log("Browser4Kodi Helper: Service beendet", xbmc.LOGINFO)
