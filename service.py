import xbmc
import subprocess
import shutil
import xbmcaddon
import xbmcvfs
import sys
from pathlib import Path



monitor = xbmc.Monitor()

xbmc.log(
    "HbbTV: service.py gestartet",
    xbmc.LOGINFO
)

# Browser4Kodi: einmalige Skin-Installation
addon_dir = Path(__file__).resolve().parent
pending_file = addon_dir / "install.pending"
skin_script = addon_dir / "k21_3_c150" / "browser_skin.py"
# Browser4Kodi: Ausführungsrecht für CEF-Unterprozess sicherstellen
browser_helper = addon_dir / "k21_3_c150" / "build" / "browser_helper"

try:
    if browser_helper.is_file():
        mode = browser_helper.stat().st_mode

        if not mode & 0o111:
            browser_helper.chmod(mode | 0o111)
            xbmc.log(
                "Browser4Kodi: browser_helper ausführbar gemacht",
                xbmc.LOGINFO
            )

except OSError as e:
    xbmc.log(
        f"Browser4Kodi: browser_helper Berechtigungsfehler: {e}",
        xbmc.LOGERROR
    )

if pending_file.is_file():
    xbmc.log("Browser4Kodi: install.pending gefunden", xbmc.LOGINFO)

    try:
        result = subprocess.run(
            [sys.executable, str(skin_script)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            xbmc.log(
                "Browser4Kodi: Skin-Installation erfolgreich",
                xbmc.LOGINFO
            )
            xbmc.executebuiltin("ReloadSkin()")

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


# Browser4Kodi Helper installieren oder aktivieren
def ensure_helper():
    addon_id = "browser4kodi.helper"

    try:
        xbmcaddon.Addon(id=addon_id)
        xbmc.log("Browser4Kodi: Helper vorhanden", xbmc.LOGINFO)
        xbmc.executebuiltin(f"EnableAddon({addon_id})")
        return
    except RuntimeError:
        pass

    source = addon_dir / "plus" / addon_id
    destination = (
        Path(xbmcvfs.translatePath("special://home/addons"))
        / addon_id
    )

    if not (source / "addon.xml").is_file():
        xbmc.log(
            "Browser4Kodi: Helper-Quelldateien fehlen",
            xbmc.LOGERROR
        )
        return

    try:
        if not destination.exists():
            shutil.copytree(source, destination)

        xbmc.log(
            "Browser4Kodi: Helper-Dateien installiert",
            xbmc.LOGINFO
        )

        xbmc.executebuiltin("UpdateLocalAddons")
        xbmc.executebuiltin(f"EnableAddon({addon_id})")

    except Exception as e:
        xbmc.log(
            f"Browser4Kodi: Helper-Installation fehlgeschlagen: {e}",
            xbmc.LOGERROR
        )


ensure_helper()

# Service aktiv halten
while not monitor.abortRequested():
    if monitor.waitForAbort(1):
        break
