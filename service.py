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
browser_helper = addon_dir / "k21_3_c150" / "build" / "Linux_x64" / "browser_helper"

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
            [sys.executable, str(skin_script), xbmcvfs.translatePath("special://home/addons/skin.confluence/1080p/")],
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
    import json

    addon_id = "browser4kodi.helper"

    def get_status():
        request = {
            "jsonrpc": "2.0",
            "method": "Addons.GetAddonDetails",
            "params": {
                "addonid": addon_id,
                "properties": ["enabled"]
            },
            "id": 1
        }

        response = json.loads(
            xbmc.executeJSONRPC(json.dumps(request))
        )

        return response.get("result", {}).get("addon")

    def activate():
        request = {
            "jsonrpc": "2.0",
            "method": "Addons.SetAddonEnabled",
            "params": {
                "addonid": addon_id,
                "enabled": True
            },
            "id": 2
        }

        response = json.loads(
            xbmc.executeJSONRPC(json.dumps(request))
        )

        if "error" in response:
            xbmc.log(
                f"Browser4Kodi: Helper-Aktivierung fehlgeschlagen: "
                f"{response['error']}",
                xbmc.LOGERROR
            )
            return False

        xbmc.log(
            "Browser4Kodi: Helper aktiviert",
            xbmc.LOGINFO
        )
        return True

    try:
        addon = get_status()

        if addon and addon.get("enabled"):
            xbmc.log(
                "Browser4Kodi: Helper bereits aktiv",
                xbmc.LOGINFO
            )
            return

        if not addon:
            source = addon_dir / "plus" / addon_id
            destination = (
                Path(xbmcvfs.translatePath("special://home/addons"))
                / addon_id
            )

            if not (source / "addon.xml").is_file():
                xbmc.log(
                    "Browser4Kodi: Helper-Quelle fehlt",
                    xbmc.LOGERROR
                )
                return

            if not destination.exists():
                shutil.copytree(source, destination)

            xbmc.executebuiltin("UpdateLocalAddons")

            # Warten, bis Kodi den Helper registriert hat.
            for attempt in range(20):
                if monitor.waitForAbort(0.5):
                    return

                addon = get_status()

                if addon:
                    break

            if not addon:
                xbmc.log(
                    "Browser4Kodi: Helper nicht registriert",
                    xbmc.LOGERROR
                )
                return

        # Nur aktivieren, wenn tatsächlich deaktiviert.
        if not addon.get("enabled"):
            if activate():
                xbmc.executebuiltin("UpdateLocalAddons")
                xbmc.executebuiltin("Container.Refresh")

    except Exception as e:
        xbmc.log(
            f"Browser4Kodi: Helper-Prüfung fehlgeschlagen: {e}",
            xbmc.LOGERROR
        )

ensure_helper()


# Kodi-Deinstallationsdialog beobachten
def watch_uninstall_dialog():
    dialog_seen = False

    while not monitor.abortRequested():
        dialog_open = xbmc.getCondVisibility(
            "Window.IsActive(10100)"
        )

        if dialog_open:
            dialog_seen = True

        elif dialog_seen:
            dialog_seen = False

            # Erst zwei Sekunden nach dem Schließen prüfen.
            if monitor.waitForAbort(2):
                break

            xbmc.log(
                "Browser4Kodi: Dialog geschlossen, Helper prüfen",
                xbmc.LOGINFO
            )

            ensure_helper()

        if monitor.waitForAbort(0.2):
            break


# Service aktiv halten
watch_uninstall_dialog()
