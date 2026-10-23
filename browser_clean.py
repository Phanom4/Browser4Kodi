#!/usr/bin/env python3

import os
import subprocess
import time
import shutil
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

# Warten, bis Kodi beendet ist.
while True:
    if os.name == "nt":
        status = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq kodi.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True
        )
        laeuft = '"kodi.exe"' in status.stdout.lower()
    else:
        laeuft = subprocess.run(
            ["pgrep", "-x", "kodi.*"],
            stdout=subprocess.DEVNULL
        ).returncode == 0

    if not laeuft:
        break

    time.sleep(1)

# Löschbefehle:
shutil.rmtree("../browser")
shutil.rmtree("../addons/script.browser.installer")
# shutil.rmtree(PFAD_3)
# shutil.rmtree(PFAD_4)

Path(__file__).unlink()
