import xbmc
import subprocess
import sys
from pathlib import Path

from resources.lib import htsp_hbbtv


monitor = xbmc.Monitor()

xbmc.log(
    "HbbTV: service.py gestartet",
    xbmc.LOGINFO
)

# Browser4Kodi: einmalige Skin-Installation
addon_dir = Path(__file__).resolve().parent
pending_file = addon_dir / "install.pending"
skin_script = addon_dir / "k21_3_c150" / "browser_skin.py"

if pending_file.is_file():
    xbmc.log("Browser4Kodi: install.pending gefunden", xbmc.LOGINFO)

    try:
        result = subprocess.run(
            [sys.executable, str(skin_script), "-1"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            xbmc.log(
                "Browser4Kodi: Skin-Installation erfolgreich",
                xbmc.LOGINFO
            )

            # Erst nach erfolgreichem Test aktivieren:
            # pending_file.unlink()

        else:
            xbmc.log(
                f"Browser4Kodi: Skin-Installation fehlgeschlagen: {result.stderr}",
                xbmc.LOGERROR
            )

    except Exception as e:
        xbmc.log(
            f"Browser4Kodi: Fehler bei Skin-Installation: {e}",
            xbmc.LOGERROR
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
