import xbmcaddon
import xbmcgui


def installed(addon_id):
    try:
        xbmcaddon.Addon(id=addon_id)
        return True
    except RuntimeError:
        return False


def main():
    dialog = xbmcgui.Dialog()

    browser = installed("browser4kodi")
    pvr = installed("pvr.hts")

    entries = [
        "Browser4Kodi: " + ("Installiert" if browser else "Nicht installiert"),
        "Browser4Kodi HbbTV",
        "Skin-Verwaltung (in Vorbereitung)"
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
            "Browser4Kodi HbbTV benötigt PVR HTS. PVR HTS ist nicht installiert."
        )

    elif selected == 2:
        dialog.ok(
            "Skin-Verwaltung",
            "Die Skin-Verwaltung wird noch eingebunden."
        )


if __name__ == "__main__":
    main()
