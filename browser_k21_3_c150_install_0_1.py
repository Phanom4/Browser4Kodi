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
    "browser_clean.py",
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

        # ========================================================
        # INSTALLER - GRUNDDATEIEN
        # ========================================================

        if BASE != BROWSER:
            BROWSER.mkdir(parents=True, exist_ok=True)

            for name in PYTHON_DATEIEN:
                quelle = BASE / name
                ziel = BROWSER / name

                if not quelle.is_file():
                    raise FileNotFoundError(
                        f"Installer: {quelle} fehlt"
                    )

                shutil.copy2(quelle, ziel)
                print(f"Grunddatei kopiert: {name}")

            print("Grunddateien kopiert", flush=True)

        else:
            print("Grunddateien bereits im Kodi-Verzeichnis", flush=True)


        # ========================================================
        # INSTALLER - ADDON
        # ========================================================

        if BASE != BROWSER:
            quelle = BASE / "addon" / "installer"

            if not quelle.is_dir():
                raise FileNotFoundError(
                    f"Installer-Add-on fehlt: {quelle}"
                )

            INSTALLER_ADDON.mkdir(parents=True, exist_ok=True)

            for name in ("addon.xml", "main.py"):
                shutil.copy2(
                    quelle / name,
                    INSTALLER_ADDON / name
                )
                print(f"Installer-Add-on kopiert: {name}")

        print("Installer: Installation abgeschlossen", flush=True)

        # ====================================================
        # BROWSER
        # ====================================================
        
        # ====================================================
        # BROWSER - DATEIEN INSTALLIEREN
        # ====================================================

        if BASE != BROWSER:

            # Quellverzeichnisse
            quelle_build = BASE / "build"
            quelle_cef = BASE / "chromium/src/out/Release_GN_x64"

            # Zielverzeichnisse
            ziel_build = BROWSER / "build"
            ziel_cef = BROWSER / "cef"

            ziel_build.mkdir(parents=True, exist_ok=True)
            ziel_cef.mkdir(parents=True, exist_ok=True)

            # ====================================================
            # BROWSER - KOMPILIERTE DATEIEN
            # ====================================================

            for name in (
                "browser_k21_3_c150.so",
                "browser_k21_3_c150_helper",
            ):
                quelle = quelle_build / name

                if not quelle.is_file():
                    raise FileNotFoundError(f"Browser: {quelle} fehlt")

                shutil.copy2(quelle, ziel_build / name)
                print(f"Browser kopiert: {name}")

            # ====================================================
            # CEF - LAUFZEITDATEIEN
            # ====================================================

            for name in (
                "libcef.so",
                "chrome_100_percent.pak",
                "chrome_200_percent.pak",
                "resources.pak",
                "icudtl.dat",
                "libEGL.so",
                "libGLESv2.so",
                "libvulkan.so.1",
                "libvk_swiftshader.so",
                "vk_swiftshader_icd.json",
                "v8_context_snapshot.bin",
            ):
                quelle = quelle_cef / name

                if not quelle.is_file():
                    raise FileNotFoundError(f"CEF: {quelle} fehlt")

                shutil.copy2(quelle, ziel_cef / name)
                print(f"CEF kopiert: {name}")

            # ====================================================
            # CEF - SPRACHDATEIEN
            # ====================================================

            quelle = quelle_cef / "locales"

            if not quelle.is_dir():
                raise FileNotFoundError(f"CEF: {quelle} fehlt")

            shutil.copytree(
                quelle,
                ziel_cef / "locales",
                dirs_exist_ok=True
            )

            print("CEF: Sprachdateien kopiert")

        else:
            print("Browser: Kopieren aus Kodi-Verzeichnis übersprungen")

        # ====================================================
        # BROWSER - SKIN INSTALLIEREN
        # ====================================================

        subprocess.run(
            [
                sys.executable,
                str(BROWSER / "browser_k21_3_c150_skin.py"),
                "-1"
            ],
            check=True
        )

        print("Browser: Installation abgeschlossen", flush=True)
        
        # ====================================================
        # HBBTV - NUR WENN pvr.hts VORHANDEN
        # ====================================================
        if (PVR_HTS / "instance-settings-1.xml").is_file():

            if BASE != BROWSER:
                shutil.copytree(
                    BASE / "addon" / "HBBTV",
                    BROWSER / "addon" / "HBBTV",
                    dirs_exist_ok=True
                )

            # Add-on immer installieren
            shutil.copytree(
                BROWSER / "addon" / "HBBTV",
                KODI / "addons" / "hbbtv-hts",
                dirs_exist_ok=True
            )

            # Skin immer installieren
            subprocess.run(
                [
                    sys.executable,
                    str(BROWSER / "browser_k21_3_c150_skin.py"),
                    "-1", "hbbtv"
                ],
                check=True
            )

            if BASE == BROWSER:
                import xbmc
                xbmc.executebuiltin("UpdateLocalAddons")

        # ====================================================
        # PROGRAMM 4 - KOMMT NOCH
        # ====================================================
        #if hbbtv_installiert:
         #   pass  # Erst einbinden, wenn das vierte Programm feststeht.

        print("Installation abgeschlossen")

    # ========================================================
    # VOLLSTAENDIG ENTFERNEN -rm
    # ========================================================
    elif OPTION == "-rm":
        print("Vollstaendige Entfernung angefordert", flush=True)

        # Zuerst deaktivieren
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "-0"],
            check=True
        )

        # Löschskript nach Kodi/temp kopieren
        quelle = BASE / "browser_clean.py"
        ziel = KODI / "temp" / "browser_clean.py"

        shutil.copy2(quelle, ziel)

        # Unabhängig starten
        subprocess.Popen(
            [sys.executable, str(ziel)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=(os.name != "nt"),
            creationflags=(
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt" else 0
            )
        )

        print("Browser: Entfernung gestartet", flush=True)

except (OSError, subprocess.CalledProcessError, RuntimeError) as fehler:
    print(f"FEHLER: {fehler}", file=sys.stderr)
    sys.exit(1)
