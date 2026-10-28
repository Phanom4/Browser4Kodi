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
SKIN = Path(sys.argv[-1]) if len(sys.argv) >= 2 else None

# ============================================================
# Browser
# ============================================================



# ============================================================
# Hauptmenue
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

def uninstall_browser_menu(path):
    text = path.read_text(encoding="utf-8")

    pattern = re.compile(
        r'\n[ \t]*<!-- browser START -->'
        r'.*?'
        r'<!-- browser END -->',
        re.DOTALL
    )

    text, count = pattern.subn("", text, count=1)

    if count:
        path.write_text(text, encoding="utf-8")
        print("browser: Hauptmenüeintrag entfernt")
    else:
        print("browser: kein Hauptmenüeintrag vorhanden")

# ============================================================
# Untermenue xy
# ============================================================

# Noch nicht benoetigt.

# ============================================================
# GameOSD
# ============================================================

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

def uninstall_gameosd(skin):
    path = skin / "GameOSD.xml"
    original = path.read_text(encoding="utf-8")
    updated = original

    for old, new in gameosd_rules():
        if new in updated:
            updated = updated.replace(new, old, 1)
        elif updated.count(old) != 1:
            raise RuntimeError(
                f"GameOSD: Eintrag nicht eindeutig: {old}"
            )

    if updated != original:
        path.write_text(updated, encoding="utf-8")

    print("browser: GameOSD entfernt")

# ============================================================
# Weitere Browser-Menues
# ============================================================

# Noch nicht benoetigt.

# ============================================================
# HBBTV
# ============================================================



# ============================================================
# Hauptmenue
# ============================================================

# Derzeit kein eigener HbbTV-Hauptmenueeintrag.

# ============================================================
# Untermenue PVR
# ============================================================

PVR_CONTROL = '''\
				<control type="button" id="33">
					<description>HbbTV</description>
					<textwidth>353</textwidth>
					<include>ButtonCommonValues</include>
					<label>HbbTV</label>
					<onclick>RunAddon(hbbtv-hts)</onclick>
				</control>
'''

def replace_or_insert_pvr(path):
    text = path.read_text(encoding="utf-8")

    pattern = re.compile(
        r'^[ \t]*<control type="button" id="33">.*?'
        r'^[ \t]*</control>\n?',
        re.MULTILINE | re.DOTALL
    )

    if pattern.search(text):
        text = pattern.sub(PVR_CONTROL, text, count=1)
        print("HbbTV: PVR Control 33 aktualisiert")
    else:
        marker = '\t\t\t\t<control type="button" id="104">'

        if marker not in text:
            raise RuntimeError(
                "HbbTV: Control 104 in IncludesPVR.xml nicht gefunden"
            )

        text = text.replace(marker, PVR_CONTROL + marker, 1)
        print("HbbTV: PVR Control 33 eingefügt")

    path.write_text(text, encoding="utf-8")

# ============================================================
# TV-Untermenue
# ============================================================

HOME_CONTROL = '''\
		<control type="button" id="33">
			<include>ButtonHomeSubCommonValues</include>
			<label>HbbTV</label>
			<onclick>RunAddon(hbbtv-hts)</onclick>
		</control>
'''

def replace_or_insert_home(path):
    text = path.read_text(encoding="utf-8")

    start_marker = '<include name="HomeSubMenuTV">'

    start = text.find(start_marker)
    if start == -1:
        raise RuntimeError("HbbTV: HomeSubMenuTV nicht gefunden")

    end = text.find(
        '<include name="',
        start + len(start_marker)
    )
    if end == -1:
        end = len(text)

    before = text[:start]
    menu = text[start:end]
    after = text[end:]

    pattern = re.compile(
        r'^[ \t]*<control type="button" id="33">.*?'
        r'^[ \t]*</control>\n?',
        re.MULTILINE | re.DOTALL
    )

    if pattern.search(menu):
        menu = pattern.sub(HOME_CONTROL, menu, count=1)
        print("HbbTV: Home Control 33 aktualisiert")
    else:
        marker = '\t\t<control type="button" id="90148">'

        if marker not in menu:
            raise RuntimeError(
                "HbbTV: Control 90148 in HomeSubMenuTV nicht gefunden"
            )

        menu = menu.replace(marker, HOME_CONTROL + marker, 1)
        print("HbbTV: Home Control 33 eingefügt")

    path.write_text(before + menu + after, encoding="utf-8")

# ============================================================
# HbbTV-Menueeintraege entfernen
# ============================================================

def remove_control(path, home=False):
    text = path.read_text(encoding="utf-8")

    if home:
        start_marker = '<include name="HomeSubMenuTV">'
        start = text.find(start_marker)

        if start == -1:
            raise RuntimeError("HbbTV: HomeSubMenuTV nicht gefunden")

        end = text.find(
            '<include name="',
            start + len(start_marker)
        )
        if end == -1:
            end = len(text)

        before = text[:start]
        area = text[start:end]
        after = text[end:]
    else:
        before = ""
        area = text
        after = ""

    pattern = re.compile(
        r'^[ \t]*<control type="button" id="33">\s*'
        r'(?:<description>HbbTV</description>\s*)?'
        r'.*?<label>HbbTV</label>.*?'
        r'^[ \t]*</control>\n?',
        re.MULTILINE | re.DOTALL
    )

    area, count = pattern.subn("", area, count=1)

    if count:
        path.write_text(before + area + after, encoding="utf-8")
        print(f"HbbTV: Control 33 aus {path.name} entfernt")
    else:
        print(f"HbbTV: kein HbbTV-Control in {path.name} vorhanden")

# ============================================================
# Weitere HbbTV-Menues
# ============================================================

# Noch nicht benoetigt.

# ============================================================
# Programm 3
# ============================================================

# Noch nicht vorhanden.

# ============================================================
# Weitere Menues
# ============================================================

# Noch nicht vorhanden.

# ============================================================
# Programm 4
# ============================================================

# Noch nicht vorhanden.

# ============================================================
# Weitere Menues
# ============================================================

# Noch nicht vorhanden.

# ============================================================
# Skin installieren
# ============================================================

def install_skin(skin, with_hbbtv=False):
    # Browser wird immer eingerichtet.
    home = skin / "Home.xml"
    gameosd = skin / "GameOSD.xml"
    required = [home, gameosd]

    if with_hbbtv:
        required.extend([
            skin / "IncludesPVR.xml",
            skin / "IncludesHomeMenuItems.xml",
        ])

    # Erst alle benoetigten Dateien pruefen, dann aendern.
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"Skin-Datei fehlt: {path}")

    for path in required:
        backup = path.with_name(path.name + ".browser.bak")
        if not backup.exists():
            shutil.copy2(path, backup)

    install_browser_menu(home)
    install_gameosd(skin)

    if with_hbbtv:
        replace_or_insert_pvr(skin / "IncludesPVR.xml")
        replace_or_insert_home(skin / "IncludesHomeMenuItems.xml")

    print("browser: Skin-Installation abgeschlossen")

# ============================================================
# Skin deinstallieren
# ============================================================

def uninstall_skin(skin):
    # Browser-Menue und GameOSD zuruecksetzen.
    uninstall_gameosd(skin)
    uninstall_browser_menu(skin / "Home.xml")

    # HbbTV-Menues auch entfernen, wenn pvr.hts inzwischen fehlt.
    pvr = skin / "IncludesPVR.xml"
    if pvr.is_file() and "<label>HbbTV</label>" in pvr.read_text(encoding="utf-8"):
        remove_control(pvr)

    home_items = skin / "IncludesHomeMenuItems.xml"
    if home_items.is_file() and "<label>HbbTV</label>" in home_items.read_text(encoding="utf-8"):
        remove_control(home_items, home=True)

    print("browser: Skin-Deinstallation abgeschlossen")


# ============================================================
# Einzelne Skin-Anpassungen
# ============================================================

SKIN_FILES = {
    "browser-menu": "Home.xml",
    "browser-osd": "GameOSD.xml",
    "hbbtv-pvr": "IncludesPVR.xml",
    "hbbtv-tv": "IncludesHomeMenuItems.xml",
}


def skin_status(skin, name):
    path = skin / SKIN_FILES[name]

    if not path.is_file():
        return False

    content = path.read_text(encoding="utf-8")

    if name == "browser-menu":
        return (
            "<!-- browser START -->" in content
            and "<!-- browser END -->" in content
        )

    if name == "browser-osd":
        return all(
            new in content
            for old, new in gameosd_rules()
        )

    if name == "hbbtv-pvr":
        return bool(re.search(
            r'<control type="button" id="33">.*?'
            r'<label>HbbTV</label>.*?</control>',
            content,
            re.DOTALL
        ))

    if name == "hbbtv-tv":
        start = content.find('<include name="HomeSubMenuTV">')
        if start < 0:
            return False

        end = content.find('<include name="', start + 1)
        area = content[start:end] if end >= 0 else content[start:]

        return bool(re.search(
            r'<control type="button" id="33">.*?'
            r'<label>HbbTV</label>.*?</control>',
            area,
            re.DOTALL
        ))

    raise ValueError(name)


def change_skin(skin, name, enable):
    if name not in SKIN_FILES:
        raise ValueError(f"Unbekannter Skin: {name}")

    path = skin / SKIN_FILES[name]

    if not path.is_file():
        raise RuntimeError(f"Skin-Datei fehlt: {path}")

    current = skin_status(skin, name)

    if current == enable:
        print(f"{name}: bereits {'aktiv' if enable else 'inaktiv'}")
        return False

    if enable:
        backup = path.with_name(path.name + ".browser.bak")
        if not backup.exists():
            shutil.copy2(path, backup)

        if name == "browser-menu":
            install_browser_menu(path)
        elif name == "browser-osd":
            install_gameosd(skin)
        elif name == "hbbtv-pvr":
            replace_or_insert_pvr(path)
        elif name == "hbbtv-tv":
            replace_or_insert_home(path)

    else:
        if name == "browser-menu":
            uninstall_browser_menu(path)
        elif name == "browser-osd":
            uninstall_gameosd(skin)
        elif name == "hbbtv-pvr":
            remove_control(path)
        elif name == "hbbtv-tv":
            remove_control(path, home=True)

    print(f"{name}: {'aktiviert' if enable else 'deaktiviert'}")
    return True


if __name__ == "__main__":
    if SKIN is None:
        sys.exit("Skin-Pfad fehlt")
    args = sys.argv[1:-1]
    changed = False

    if len(args) == 2 and args[0] in SKIN_FILES:
        name, action = args

        if action == "status":
            print("aktiv" if skin_status(SKIN, name) else "inaktiv")
            sys.exit(0)

        if action in ("+", "-"):
            changed = change_skin(SKIN, name, action == "+")
        else:
            sys.exit("Aktion muss +, - oder status sein")

    elif args == ["-1"]:
        install_skin(SKIN, with_hbbtv=False)
        changed = True

    elif args == ["-1", "hbbtv"]:
        install_skin(SKIN, with_hbbtv=True)
        changed = True

    elif args == ["-0"]:
        uninstall_skin(SKIN)
        changed = True

    else:
        sys.exit(
            "Verwendung: helper_skin.py "
            "<skin> [+|-|status] | -1 [hbbtv] | -0"
        )

    if changed:
        try:
            import xbmc
            xbmc.executebuiltin("ReloadSkin()")
        except ModuleNotFoundError:
            pass
