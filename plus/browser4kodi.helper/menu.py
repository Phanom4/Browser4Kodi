import xbmc
import xbmcaddon
import helper_skin
import xbmcgui


def installed(addon_id):
    try:
        xbmcaddon.Addon(id=addon_id)
        return True
    except RuntimeError:
        return False



def skin_debug():
    names = [
        "browser-menu",
        "browser-osd",
        "hbbtv-pvr",
        "hbbtv-tv",
    ]

    labels = [
        "Browser – Hauptmenü",
        "Browser – OSD",
        "HbbTV – PVR-Menü",
        "HbbTV – TV-Untermenü",
    ]

    try:
        active = [
            i for i, name in enumerate(names)
            if helper_skin.skin_status(helper_skin.SKIN, name)
        ]

        selected = xbmcgui.Dialog().multiselect(
            "Browser4Kodi Helper – Skin-Debug",
            labels,
            preselect=active
        )

        if selected is None:
            return

        changed = False
        errors = []

        for i, name in enumerate(names):
            enabled = i in selected
            was_enabled = i in active

            if enabled == was_enabled:
                continue

            try:
                if helper_skin.change_skin(
                    helper_skin.SKIN, name, enabled
                ):
                    changed = True
            except Exception as e:
                errors.append(f"{labels[i]}: {e}")

        if changed:
            xbmc.executebuiltin("ReloadSkin()")

        if errors:
            xbmcgui.Dialog().ok(
                "Skin-Debug – Fehler",
                "\\n".join(errors)
            )

    except Exception as e:
        xbmcgui.Dialog().ok(
            "Skin-Debug – Fehler",
            str(e)
        )


def main():
    dialog = xbmcgui.Dialog()

    browser = installed("browser4kodi")
    pvr = installed("pvr.hts")

    entries = [
        "Browser4Kodi: " + ("Installiert" if browser else "Nicht installiert"),
        "Browser4Kodi HbbTV",
        "Skin-Debug"
    ]

    selected = dialog.select(
        "Browser4Kodi Helper",
        entries
    )

    if selected == 0:
        dialog.ok(
            "Browser4Kodi",
            "Browser4Kodi ist installiert." if browser
            else "Browser4Kodi ist nicht installiert."
        )

    elif selected == 1:
        dialog.ok(
            "Browser4Kodi HbbTV",
            "PVR HTS ist vorhanden. Die HbbTV-Erweiterung kann separat installiert werden."
            if pvr else
            "Leider wurde kein PVR-HTS-Add-on erkannt. Bitte informieren Sie sich über die Voraussetzungen für PVR HTS."
        )

    elif selected == 2:
        skin_debug()


if __name__ == "__main__":
    main()
