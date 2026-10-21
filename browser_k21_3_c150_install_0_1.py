#!/usr/bin/env python3

from pathlib import Path
import shutil
import subprocess
import sys
import os
import time

# ============================================================
# Verzeichnisse
# ============================================================

BASE = Path(__file__).resolve().parent

# Kodi-interne Schreibweise (spaeter innerhalb Kodis aufloesen):
KODI_SPECIAL_PROFILE = "special://profile/"
KODI_SPECIAL_ADDON_DATA = "special://profile/addon_data/"
KODI_SPECIAL_PVR_HTS = "special://profile/addon_data/pvr.hts/"

# Vorlaeufiger Dateisystempfad fuer das externe Python-Programm.
# 'special://' kann pathlib ausserhalb von Kodi nicht aufloesen.
PROFILE = Path.home() / ".kodi"
SKIN = PROFILE / "addons/skin.confluence/1080p"
PVR_HTS = PROFILE / "userdata/addon_data/pvr.hts"
HBBTV_DATABASE = PROFILE / "userdata/Database/HbbTV1.db"
HBBTV_WINDOW = SKIN / "custom_HbbTVChannels.xml"
BROWSER = PROFILE / "browser"
INSTALLER_ADDON = PROFILE / "addons/script.browser.installer"
HBBTV_ADDON = PROFILE / "addons/hbbtv-hts"


# ============================================================
# Browser-Verzeichnis anlegen und Python-Dateien kopieren
# ============================================================
def install_browser():
    BROWSER.mkdir(parents=True, exist_ok=True)

    if BASE != BROWSER:
        for source in BASE.glob("browser_k21_3_c150+*.py"):
            shutil.copy2(source, BROWSER / source.name)

        for old in BROWSER.glob("browser_k21_3_c150+*.py"):
            if not (BASE / old.name).is_file():
                old.unlink()


def remove_all():
    subprocess.run(
        [sys.executable, str(BASE / "browser_k21_3_c150_skin.py"), "-0"],
        check=True
    )

    uninstall_hbbtv()
    uninstall_browser()

    if INSTALLER_ADDON.is_dir():
        shutil.rmtree(INSTALLER_ADDON)
     
    if HBBTV_ADDON.is_dir():
        shutil.rmtree(HBBTV_ADDON)

    if BROWSER.is_dir():
        shutil.rmtree(BROWSER)
 
# ============================================================
# Installer addon - immer
# ============================================================

def install_installer_addon():
    source = BASE / "addon" / "installer"

    if source.is_dir():
        INSTALLER_ADDON.mkdir(parents=True, exist_ok=True)

        for name in ("addon.xml", "main.py"):
            shutil.copy2(source / name, INSTALLER_ADDON / name)


# ============================================================
# Browser - immer
# ============================================================

def uninstall_browser():
    # Der Menueintrag wird spaeter vom getrennten Skin-Programm entfernt.
    print("Browser: Skin-Rueckbau folgt ueber das separate Skin-Programm")


# ============================================================
# HBBTV addon - nur bei vorhandenem pvr.hts
# ============================================================

def hbbtv_available():
    return PVR_HTS.is_dir()


def find_hbbtv_window():
    candidates = [
        PROFILE / "addons/hbbtv-hts/custom_HbbTVChannels.xml",
        BASE / "addon/HBBTV/custom_HbbTVChannels.xml",
    ]

    for source in candidates:
        if source.is_file():
            return source

    raise RuntimeError(
        "HbbTV: custom_HbbTVChannels.xml nicht gefunden. "
        "Bitte den urspruenglichen Add-on-Pfad eintragen."
    )


def install_hbbtv():
    source = find_hbbtv_window()
    shutil.copy2(source, HBBTV_WINDOW)
    print("HbbTV: custom_HbbTVChannels.xml installiert")


def uninstall_hbbtv():
    if HBBTV_WINDOW.exists():
        HBBTV_WINDOW.unlink()
        print("HbbTV: custom_HbbTVChannels.xml entfernt")
    else:
        print("HbbTV: custom_HbbTVChannels.xml nicht vorhanden")

    # Die selbst erzeugte Datenbank soll bei der Deinstallation mit weg.
    if HBBTV_DATABASE.exists():
        HBBTV_DATABASE.unlink()
        print("HbbTV: HbbTV1.db entfernt")
    else:
        print("HbbTV: HbbTV1.db nicht vorhanden")


# ============================================================
# hbbtv-browser schnittstelle - spaeter
# ============================================================




# ============================================================
# Installation
# ============================================================

def install():
    print("browser_k21_3_c150: Installation gestartet")

    install_browser()
    
    install_installer_addon()

    if hbbtv_available():
        print("HbbTV: pvr.hts erkannt")
        install_hbbtv()

        subprocess.run(
            [sys.executable, str(BASE / "browser_k21_3_c150_skin.py"), "-1", "hbbtv"],
            check=True
        )
    else:
        print("HbbTV: pvr.hts fehlt - keine HbbTV-Installation")

        subprocess.run(
            [sys.executable, str(BASE / "browser_k21_3_c150_skin.py"), "-1"],
            check=True
        )

    print("browser_k21_3_c150: Installation abgeschlossen")
    
# ============================================================
# Deinstallation
# ============================================================

def uninstall():
    print("browser_k21_3_c150: Deinstallation gestartet")

    subprocess.run(
        [sys.executable, str(BASE / "browser_k21_3_c150_skin.py"), "-0"],
        check=True
    )

    uninstall_hbbtv()
    uninstall_browser()

    print("browser_k21_3_c150: Deinstallation abgeschlossen")

# ============================================================
# Auf Kodi-Ende warten (Linux / Windows)
# ============================================================

def kodi_running():
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq kodi.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=True
        )
        return '"kodi.exe"' in result.stdout.lower()

    return subprocess.run(
        ["pgrep", "-x", "kodi.bin"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ).returncode == 0


def wait_for_kodi():
    while kodi_running():
        time.sleep(1)
            
# ============================================================
# Hauptprogramm
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("-1", "-0", "-rm"):
        print("Verwendung: browser_k21_3_c150_install_0_1.py -1 | -0 | -rm")
        sys.exit(1)

    if sys.argv[1] == "-1":
        install()

    elif sys.argv[1] == "-0":
        wait_for_kodi()
        uninstall()

    elif sys.argv[1] == "-rm":
        wait_for_kodi()
        remove_all()
