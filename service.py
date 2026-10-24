import xbmc

from resources.lib import htsp_hbbtv


monitor = xbmc.Monitor()

xbmc.log(
    "HbbTV: service.py gestartet",
    xbmc.LOGINFO
)

# HbbTV1.db einmal beim Kodi-Start aktualisieren
try:
    htsp_hbbtv.main()

    xbmc.log(
        "HbbTV: HbbTV1.db beim Kodi-Start aktualisiert",
        xbmc.LOGINFO
    )

except Exception as e:
    xbmc.log(
        f"HbbTV: Fehler beim Aktualisieren von HbbTV1.db: {e}",
        xbmc.LOGERROR
    )

# Service aktiv halten
while not monitor.abortRequested():
    if monitor.waitForAbort(1):
        break
