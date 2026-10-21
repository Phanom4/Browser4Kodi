#!/usr/bin/env python3

import os
import shutil
import subprocess
from pathlib import Path

import xbmcgui
import xbmcvfs


INSTALLER = Path(xbmcvfs.translatePath(
    "special://home/browser/browser_k21_3_c150_install_0_1.py"
))

ACTIONS = [
    ("Installieren", "-1"),
    ("Deinstallieren", "-0"),
    ("Alles löschen", "-rm"),
]


def main():
    dialog = xbmcgui.Dialog()

    selection = dialog.select(
        "Browser-Installer",
        [label for label, _ in ACTIONS],
    )
    if selection < 0:
        return

    _, option = ACTIONS[selection]

    if option == "-rm" and not dialog.yesno(
        "Browser-Installer",
        "Browser, HbbTV und das Installer-Add-on vollständig entfernen?",
    ):
        return

    if not INSTALLER.is_file():
        dialog.ok(
            "Browser-Installer",
            "Zentraler Installer nicht gefunden. "
            "Bitte zuerst die Erstinstallation manuell durchführen.",
        )
        return

    python = shutil.which("python3") or shutil.which("python")
    if python is None:
        dialog.ok("Browser-Installer", "Externes Python 3 wurde nicht gefunden.")
        return

    options = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }

    if os.name == "nt":
        options["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        options["start_new_session"] = True

    try:
        subprocess.Popen([python, str(INSTALLER), option], **options)
    except OSError as error:
        dialog.ok("Browser-Installer", f"Start fehlgeschlagen: {error}")
        return

    dialog.ok(
        "Browser-Installer",
        "Kodi muss neu gestartet werden, damit die Änderungen wirksam werden.",
    )


if __name__ == "__main__":
    main()

