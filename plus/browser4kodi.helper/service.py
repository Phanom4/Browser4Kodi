import xbmc
import json
import subprocess
import sys
from pathlib import Path

monitor = xbmc.Monitor()
addon_dir = Path(__file__).resolve().parent


def browser_installed():
    request = {
        "jsonrpc": "2.0",
        "method": "Addons.GetAddonDetails",
        "params": {
            "addonid": "browser4kodi",
            "properties": ["enabled"]
        },
        "id": 1
    }

    response = json.loads(
        xbmc.executeJSONRPC(json.dumps(request))
    )

    return bool(response.get("result", {}).get("addon"))


def cleanup_browser_skin():
    script = addon_dir / "helper_skin.py"

    if not script.is_file():
        xbmc.log(
            "Browser4Kodi Helper: helper_skin.py fehlt",
            xbmc.LOGERROR
        )
        return

    result = subprocess.run(
        [sys.executable, str(script), "-0"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        xbmc.log(
            f"Browser4Kodi Helper: Skin-Bereinigung fehlgeschlagen: "
            f"{result.stderr}",
            xbmc.LOGERROR
        )
        return

    xbmc.executebuiltin("ReloadSkin()")
    xbmc.log(
        "Browser4Kodi Helper: Skin bereinigt",
        xbmc.LOGINFO
    )


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

            if monitor.waitForAbort(2):
                break

            try:
                if not browser_installed():
                    xbmc.log(
                        "Browser4Kodi Helper: Browser entfernt",
                        xbmc.LOGINFO
                    )
                    cleanup_browser_skin()
                    break

            except Exception as e:
                xbmc.log(
                    f"Browser4Kodi Helper: Prüfung fehlgeschlagen: {e}",
                    xbmc.LOGERROR
                )

        if monitor.waitForAbort(0.2):
            break


xbmc.log(
    "Browser4Kodi Helper: Service gestartet",
    xbmc.LOGINFO
)

watch_uninstall_dialog()

xbmc.log(
    "Browser4Kodi Helper: Service beendet",
    xbmc.LOGINFO
)
