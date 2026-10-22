#!/usr/bin/env python3

from pathlib import Path
import os
import shutil
import subprocess
import sys
import time

# ============================================================
# HEADER / VERZEICHNISSE / PFADE
# ============================================================

BASE = Path(__file__).resolve().parent
KODI = Path.home() / ".kodi"
BROWSER = KODI / "browser"
INSTALLER_ADDON = KODI / "addons/script.browser.installer"
PVR_HTS = KODI / "userdata/addon_data/pvr.hts"

# Ausschliesslich diese Dateien verwaltet der zentrale Installer.
PYTHON_DATEIEN = (
    "browser_k21_3_c150_install_0_1.py",
    "browser_k21_3_c150_load.py",
    "browser_k21_3_c150_retroplayer.py",
    "browser_k21_3_c150_skin.py",
)

# Schnittstellen der eigenstaendigen Programme.
# Diese beiden install.py existieren im jetzigen GitHub-Stand NOCH NICHT.
BROWSER_QUELLE = BASE / "addon/browser/install.py"
BROWSER_INSTALLIERT = BROWSER / "components/browser/install.py"
HBBTV_QUELLE = BASE / "addon/HBBTV/install.py"
HBBTV_INSTALLIERT = KODI / "addons/hbbtv-hts/install.py"

if len(sys.argv) != 2 or sys.argv[1] not in ("-0", "-1", "-rm"):
    sys.exit("Verwendung: browser_k21_3_c150_install_0_1.py -1 | -0 | -rm")

OPTION = sys.argv[1]

try:
    # ========================================================
    # DEINSTALLATION -0
    # ========================================================
    if OPTION == "-0":
        print("Deinstallation gestartet", flush=True)

        # ====================================================
        # PROGRAMM 4 - KOMMT NOCH
        # ====================================================
        # Nur wenn installiert; eigene Deinstallation.

        # ====================================================
        # HBBTV
        # ====================================================
        programm = HBBTV_INSTALLIERT if HBBTV_INSTALLIERT.is_file() else HBBTV_QUELLE
        if programm.is_file():
            subprocess.run([sys.executable, str(programm), "-0"], check=True)
        else:
            print("HbbTV: kein eigener Installer vorhanden; uebersprungen")

        # ====================================================
        # BROWSER
        # ====================================================
        programm = BROWSER_INSTALLIERT if BROWSER_INSTALLIERT.is_file() else BROWSER_QUELLE
        if programm.is_file():
            subprocess.run([sys.executable, str(programm), "-0"], check=True)
        else:
            print("Browser: kein eigener Installer vorhanden; uebersprungen")

        # ====================================================
        # INSTALLER
        # ====================================================
        # Bei -0 bleibt er selbst vollstaendig erhalten.
        print("Installer: bleibt erhalten")

    # ========================================================
    # INSTALLATION -1
    # ========================================================
    elif OPTION == "-1":
        print("Installation gestartet", flush=True)

        # Vor der Installation pruefen, ob die Programme vorhanden sind.
        browser_programm = (BROWSER_QUELLE if BROWSER_QUELLE.is_file()
                            else BROWSER_INSTALLIERT)
        hbbtv_programm = (HBBTV_QUELLE if HBBTV_QUELLE.is_file()
                          else HBBTV_INSTALLIERT)
        if not browser_programm.is_file():
            raise FileNotFoundError("Browser: eigenes Installationsprogramm fehlt")
        if PVR_HTS.is_dir() and not hbbtv_programm.is_file():
            raise FileNotFoundError("HbbTV: eigenes Installationsprogramm fehlt")

        # ====================================================
        # INSTALLER
        # ====================================================
        # Nur seine vier Python-Dateien und sein Kodi-Add-on.
        for name in PYTHON_DATEIEN:
            if not (BASE / name).is_file():
                raise FileNotFoundError(f"Installer-Datei fehlt: {BASE / name}")

        addon_quelle = BASE / "addon/installer"
        if addon_quelle.is_dir():
            for name in ("addon.xml", "main.py"):
                if not (addon_quelle / name).is_file():
                    raise FileNotFoundError(f"Installer-Add-on-Datei fehlt: {name}")
        elif not all((INSTALLER_ADDON / name).is_file()
                     for name in ("addon.xml", "main.py")):
            raise FileNotFoundError("Installer-Add-on-Quelldateien fehlen")

        BROWSER.mkdir(parents=True, exist_ok=True)
        if BASE != BROWSER:
            for name in PYTHON_DATEIEN:
                shutil.copy2(BASE / name, BROWSER / name)

        if addon_quelle.is_dir():
            INSTALLER_ADDON.mkdir(parents=True, exist_ok=True)
            for name in ("addon.xml", "main.py"):
                shutil.copy2(addon_quelle / name, INSTALLER_ADDON / name)
        print("Installer: Python-Dateien und Kodi-Add-on installiert")

        # ====================================================
        # BROWSER
        # ====================================================
        # Browser holt seine Bibliotheken und Laufzeitdateien
        # selbst und richtet seine eigenen Skin-Eintraege ein.
        subprocess.run([sys.executable, str(browser_programm), "-1"], check=True)
        print("Browser: eigene Installation abgeschlossen")

        # ====================================================
        # HBBTV - NUR WENN pvr.hts VORHANDEN
        # ====================================================
        hbbtv_installiert = False
        if PVR_HTS.is_dir():
            subprocess.run([sys.executable, str(hbbtv_programm), "-1"], check=True)
            hbbtv_installiert = True
            print("HbbTV: eigene Installation abgeschlossen")
        else:
            print("HbbTV: pvr.hts fehlt; uebersprungen")

        # ====================================================
        # PROGRAMM 4 - KOMMT NOCH
        # ====================================================
        if hbbtv_installiert:
            pass  # Erst einbinden, wenn das vierte Programm feststeht.

        print("Installation abgeschlossen")

    # ========================================================
    # VOLLSTAENDIG ENTFERNEN -rm
    # ========================================================
    elif OPTION == "-rm":
        print("Vollstaendige Entfernung angefordert", flush=True)

        # ====================================================
        # WARTEN, BIS KODI GESCHLOSSEN IST
        # ====================================================
        if os.name == "nt":
            while True:
                status = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq kodi.exe", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, check=True,
                )
                if '"kodi.exe"' not in status.stdout.lower():
                    break
                time.sleep(1)
        else:
            while subprocess.run(
                ["pgrep", "-x", "kodi.bin"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False,
            ).returncode == 0:
                time.sleep(1)

        # ====================================================
        # PROGRAMM 4 - KOMMT NOCH
        # ====================================================
        # Eigene Dateien und Ordner entfernen.

        # ====================================================
        # HBBTV
        # ====================================================
        programm = HBBTV_INSTALLIERT if HBBTV_INSTALLIERT.is_file() else HBBTV_QUELLE
        if programm.is_file():
            subprocess.run([sys.executable, str(programm), "-rm"], check=True)
        elif HBBTV_INSTALLIERT.parent.exists():
            raise RuntimeError("HbbTV-Verzeichnis vorhanden, eigener Installer fehlt")

        # ====================================================
        # BROWSER
        # ====================================================
        programm = BROWSER_INSTALLIERT if BROWSER_INSTALLIERT.is_file() else BROWSER_QUELLE
        if programm.is_file():
            subprocess.run([sys.executable, str(programm), "-rm"], check=True)
        elif (BROWSER / "components/browser").exists():
            raise RuntimeError("Browser-Komponente vorhanden, eigener Installer fehlt")

        # ====================================================
        # INSTALLER - IMMER ZULETZT
        # ====================================================
        # Der Kodi-Ordner 'browser' gehoert dieser Installation.
        # Er wird erst nach erfolgreichem Rueckbau aller Komponenten geloescht.
        if HBBTV_INSTALLIERT.parent.exists():
            raise RuntimeError("HbbTV-Add-on ist nach -rm noch vorhanden")
        if INSTALLER_ADDON.is_dir():
            shutil.rmtree(INSTALLER_ADDON)
        if BROWSER.is_dir():
            shutil.rmtree(BROWSER)
        print("Alle eigenen Installationsverzeichnisse entfernt")

except (OSError, subprocess.CalledProcessError, RuntimeError) as fehler:
    print(f"FEHLER: {fehler}", file=sys.stderr)
    sys.exit(1)
