#!/usr/bin/env python3

from pathlib import Path
import re
import shutil
import sys


# ============================================================
# Verzeichnisse
# ============================================================

# Kodis distributionsunabhaengiger virtueller Profilpfad.
# Ausserhalb Kodi nicht direkt mit pathlib aufloesbar.
KODI_SPECIAL_PROFILE = "special://profile/"

# Fuer die aktuelle externe Python-Installation unter Linux:
PROFILE = Path.home() / ".kodi"
SKIN = PROFILE / "addons/skin.confluence/1080p"

# ============================================================
# Hauptmenue Browser
# ============================================================

BROWSER_ITEM = '''\
					<!-- browser START -->
					<item id="33033">
						<label>Browser</label>
						<onclick>RunScript(special://home/addons/browser4kodi/k21_3_c150/browser_load.py)</onclick>
						<icon />
						<thumb />
					</item>
					<!-- browser END -->
'''

def install_browser_menu(path):
    text = path.read_text(encoding="utf-8")

    if "<!-- browser START -->" in text:
        print("browser: Hauptmenüeintrag bereits vorhanden")
        return

    if re.search(r'<item\s+id="33033">', text):
        raise RuntimeError(
            "browser: Menü-ID 33033 bereits vergeben"
        )

    pattern = re.compile(
        r'<item id="14">.*?</item>',
        re.DOTALL
    )

    match = pattern.search(text)

    if not match:
        raise RuntimeError(
            "browser: SPIELE in Home.xml nicht gefunden"
        )

    text = (
        text[:match.end()]
        + "\n"
        + BROWSER_ITEM.rstrip("\n")
        + text[match.end():]
    )

    path.write_text(text, encoding="utf-8")
    print("browser: Hauptmenüeintrag eingefügt")

def gameosd_rules():
    condition = (
        "String.IsEqual("
        "Window(10000).Property(browser.GameOSD),1)"
    )

    return [
        # Fortsetzen
        (
            "<onclick>Play</onclick>",
            f'<onclick condition="{condition}">Close</onclick>\n'
            f'\t\t\t\t\t<onclick condition="!{condition}">Play</onclick>'
        ),

        # Zurücksetzen
        (
            "<onclick>PlayerControl(Reset)</onclick>",
            f'<onclick condition="{condition}">Close</onclick>\n'
            f'\t\t\t\t\t<onclick condition="{condition}">ActivateWindow(Home)</onclick>\n'
            f'\t\t\t\t\t<onclick condition="!{condition}">PlayerControl(Reset)</onclick>'
        ),

        # Verlassen
        (
            "<onclick>Stop</onclick>",
            f'<onclick condition="{condition}">Close</onclick>\n'
            f'\t\t\t\t\t<onclick condition="{condition}">ActivateWindow(Home)</onclick>\n'
            f'\t\t\t\t\t<onclick condition="!{condition}">Stop</onclick>'
        ),

        # Ports bei aktivem Browser ignorieren
        (
            "<onclick>ActivateWindow(GamePorts)</onclick>",
            f'<onclick condition="!{condition}">ActivateWindow(GamePorts)</onclick>'
        ),
    ]

def install_gameosd(skin):
    path = skin / "GameOSD.xml"
    original = path.read_text(encoding="utf-8")
    updated = original

    for old, new in gameosd_rules():
        if new in updated:
            continue

        if updated.count(old) != 1:
            raise RuntimeError(
                f"GameOSD: Eintrag nicht eindeutig: {old}"
            )

        updated = updated.replace(old, new, 1)

    if updated != original:
        backup = path.with_name(
            "GameOSD.xml.browser.bak"
        )
        if not backup.exists():
            shutil.copy2(path, backup)

        path.write_text(updated, encoding="utf-8")

    print("browser: GameOSD installiert")


def install_skin(skin):
    home = skin / "Home.xml"
    gameosd = skin / "GameOSD.xml"

    for path in (home, gameosd):
        if not path.is_file():
            raise RuntimeError(f"Skin-Datei fehlt: {path}")

    for path in (home, gameosd):
        backup = path.with_name(path.name + ".browser.bak")
        if not backup.exists():
            shutil.copy2(path, backup)

    install_browser_menu(home)
    install_gameosd(skin)

    print("browser: Skin-Installation abgeschlossen")


if __name__ == "__main__":
    install_skin(SKIN)
