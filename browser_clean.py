#!/usr/bin/env python3

import os
import subprocess
import time
import shutil
from pathlib import Path

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
            ["pgrep", "-x", "kodi.bin"],
            stdout=subprocess.DEVNULL
        ).returncode == 0

    if not laeuft:
        break

    time.sleep(1)

# Ab hier deine drei, später vier Löschbefehle:
# shutil.rmtree(PFAD_1)
# shutil.rmtree(PFAD_2)
# shutil.rmtree(PFAD_3)
# shutil.rmtree(PFAD_4)
