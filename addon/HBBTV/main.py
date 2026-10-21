import mmap
import os
import sqlite3
import subprocess
import threading
import time
from pathlib import Path

import xbmc
import xbmcgui
import xbmcvfs



XML_FILE = "custom_HbbTVChannels.xml"
LIST_ID = 50

SHM = "/dev/shm/kodi-browser-osr"
FIFO = "/tmp/core32-browser.nut"
FFMPEG = "/usr/lib/ffmpeg6/bin/ffmpeg"

HEADER_SIZE = 56
WIDTH = 1280
HEIGHT = 720
STRIDE = 5120
FRAME_SIZE = STRIDE * HEIGHT
FPS = 30

DATABASE_DIR = (
    Path.home()
    / ".kodi/userdata/Database"
)

HBBTV_DB_VERSION = 1

HBBTV_DB = (
    DATABASE_DIR
    / f"HbbTV{HBBTV_DB_VERSION}.db"
)


def find_tv_database():
    databases = []

    for path in DATABASE_DIR.glob("TV*.db"):
        version = path.stem[2:]

        if version.isdigit():
            databases.append(
                (int(version), path)
            )

    if not databases:
        raise RuntimeError(
            f"Keine Kodi-TV-Datenbank in {DATABASE_DIR} gefunden"
        )

    return max(databases)[1]


def get_hbbtv_channels():
    if not HBBTV_DB.exists():
        raise RuntimeError(
            f"HbbTV-Datenbank nicht gefunden: {HBBTV_DB}"
        )

    tv_db = find_tv_database()

    con = sqlite3.connect(
        f"file:{tv_db}?mode=ro",
        uri=True
    )

    try:
        con.execute(
            "ATTACH DATABASE ? AS hbbtv",
            (f"file:{HBBTV_DB}?mode=ro",)
        )

        rows = con.execute(
            """
            SELECT
                tv.iUniqueId,
                tv.sChannelName,
                tv.sIconPath
            FROM channels AS tv
            WHERE tv.bIsRadio = 0
              AND tv.iUniqueId IN (
                  SELECT DISTINCT iUniqueId
                  FROM hbbtv.hbbtv_apps
              )
            ORDER BY tv.sChannelName COLLATE NOCASE
            """
        ).fetchall()

        return [
            {
                "iUniqueId": row[0],
                "name": row[1],
                "icon": row[2] or "",
            }
            for row in rows
        ]

    finally:
        con.close()

def get_hbbtv_apps(iuniqueid):
    if not HBBTV_DB.exists():
        raise RuntimeError(
            f"HbbTV-Datenbank nicht gefunden: {HBBTV_DB}"
        )

    con = sqlite3.connect(
        f"file:{HBBTV_DB}?mode=ro",
        uri=True
    )

    try:
        rows = con.execute(
            """
            SELECT
                name,
                url
            FROM hbbtv_apps
            WHERE iUniqueId = ?
            ORDER BY name COLLATE NOCASE
            """,
            (iuniqueid,)
        ).fetchall()

        return [
            {
                "name": row[0],
                "url": row[1] or "",
            }
            for row in rows
        ]

    finally:
        con.close()

def shm_to_ffmpeg(proc, stop_event):
    try:
        with open(SHM, "rb", buffering=0) as f:
            mm = mmap.mmap(
                f.fileno(),
                0,
                access=mmap.ACCESS_READ
            )

            xbmc.log(
                f"HbbTV: SHM geöffnet, Größe={len(mm)}",
                xbmc.LOGINFO
            )

            frame_time = 1.0 / FPS

            while not stop_event.is_set():
                start = time.monotonic()

                frame = mm[
                    HEADER_SIZE:
                    HEADER_SIZE + FRAME_SIZE
                ]

                try:
                    proc.stdin.write(frame)
                    proc.stdin.flush()

                except (BrokenPipeError, OSError):
                    xbmc.log(
                        "HbbTV: ffmpeg pipe beendet",
                        xbmc.LOGERROR
                    )
                    break

                delay = frame_time - (
                    time.monotonic() - start
                )

                if delay > 0:
                    time.sleep(delay)

            mm.close()

    except Exception as e:
        xbmc.log(
            f"HbbTV: SHM-Reader Fehler: {e}",
            xbmc.LOGERROR
        )

class Core32Player(xbmc.Player):

    def onAVStarted(self):
        xbmc.log(
            "HbbTV: Browser VideoPlayer onAVStarted",
            xbmc.LOGINFO
        )

    def onPlayBackStarted(self):
        xbmc.log(
            "HbbTV: Browser VideoPlayer onPlayBackStarted",
            xbmc.LOGINFO
        )

    def onPlayBackStopped(self):
        xbmc.log(
            "HbbTV: Browser VideoPlayer onPlayBackStopped",
            xbmc.LOGINFO
        )

    def onPlayBackEnded(self):
        xbmc.log(
            "HbbTV: Browser VideoPlayer onPlayBackEnded",
            xbmc.LOGINFO
        )

    def onPlayBackError(self):
        xbmc.log(
            "HbbTV: Browser VideoPlayer onPlayBackError",
            xbmc.LOGERROR
        )

class HbbTVWindow(xbmcgui.WindowXML):

    def onInit(self):
        xbmc.log(
            "HbbTV: WindowXML gestartet",
            xbmc.LOGINFO
        )

        self.level = 1
        self.current_iuniqueid = None
        self.current_channel_name = None
        self.current_app_name = None
        self.current_app_url = None
        self.browser_proc = None
        self.browser_stop_event = None
        self.browser_thread = None
        self.browser_player = None

        # Navigationsverlauf.
        # Jeder Eintrag beschreibt eine vollständig wiederherstellbare Seite.
        self.history = []

        # Neuer Einstieg in HbbTV beginnt immer auf Seite 1.
        self.show_level_1(reset_history=True)

    def show_level_1(self, reset_history=False):
        try:
            channels = get_hbbtv_channels()

            channel_list = self.getControl(LIST_ID)
            channel_list.reset()

            items = []

            for channel in channels:
                item = xbmcgui.ListItem(
                    label=channel["name"]
                )

                item.setProperty(
                    "type",
                    "channel"
                )

                item.setProperty(
                    "iUniqueId",
                    str(channel["iUniqueId"])
                )

                icon = channel.get("icon", "")

                if icon:
                    item.setArt({
                        "icon": icon
                    })

                items.append(item)

            channel_list.addItems(items)

            self.level = 1

            if reset_history:
                self.history = []

            self.history.append({
                "level": 1
            })

            xbmc.log(
                f"HbbTV: Ebene 1 - {len(items)} Sender eingetragen",
                xbmc.LOGINFO
            )

        except Exception as e:
            xbmc.log(
                f"HbbTV: Fehler Ebene 1: {e}",
                xbmc.LOGERROR
            )

    def show_level_2(self, iuniqueid, channel_name):
        try:
            apps = get_hbbtv_apps(iuniqueid)

            channel_list = self.getControl(LIST_ID)
            channel_list.reset()

            back_item = xbmcgui.ListItem(
                label=".."
            )

            back_item.setProperty(
                "type",
                "back"
            )

            channel_list.addItem(back_item)

            items = []

            for app in apps:
                item = xbmcgui.ListItem(
                    label=app["name"]
                )

                item.setProperty(
                    "type",
                    "app"
                )

                item.setProperty(
                    "url",
                    app["url"]
                )

                items.append(item)

            channel_list.addItems(items)

            self.level = 2
            self.current_iuniqueid = iuniqueid
            self.current_channel_name = channel_name
            self.history.append({
                "level": 2,
                "iuniqueid": iuniqueid,
                "channel_name": channel_name
            })

            xbmc.log(
                f"HbbTV: Ebene 2 - {len(apps)} Anwendungen für "
                f"{channel_name} (iUniqueId={iuniqueid}) eingetragen",
                xbmc.LOGINFO
            )

        except Exception as e:
            xbmc.log(
                f"HbbTV: Fehler Ebene 2: {e}",
                xbmc.LOGERROR
            )
    def start_browser_video(self):
        try:
            if os.path.exists(FIFO):
                os.unlink(FIFO)

            os.mkfifo(FIFO)

            cmd = [
                FFMPEG,
                "-hide_banner",
                "-loglevel", "warning",

                "-f", "rawvideo",
                "-pixel_format", "bgra",
                "-video_size",
                f"{WIDTH}x{HEIGHT}",
                "-framerate", str(FPS),
                "-i", "pipe:0",

                "-c:v", "copy",
                "-f", "nut",
                "-y",
                FIFO
            ]

            xbmc.log(
                "HbbTV: starte Browser-FFmpeg: "
                + " ".join(cmd),
                xbmc.LOGINFO
            )

            self.browser_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE
            )

            self.browser_stop_event = threading.Event()

            self.browser_thread = threading.Thread(
                target=shm_to_ffmpeg,
                args=(
                    self.browser_proc,
                    self.browser_stop_event
                ),
                daemon=True
            )

            self.browser_thread.start()

            self.browser_player = Core32Player()

            item = xbmcgui.ListItem(
                path=FIFO
            )

            item.setProperty(
                "IsPlayable",
                "true"
            )

            item.setProperty(
                "IsLive",
                "true"
            )

            xbmc.log(
                "HbbTV: Browser VideoPlayer play()",
                xbmc.LOGINFO
            )

            self.browser_player.play(
                FIFO,
                item
            )

        except Exception as e:
            xbmc.log(
                f"HbbTV: Browser VideoPlayer Startfehler: {e}",
                xbmc.LOGERROR
            )


    def show_level_3(self, app_name, app_url):
        self.level = 3
        self.current_app_name = app_name
        self.current_app_url = app_url
        self.start_browser_video()
        channel_list = self.getControl(LIST_ID)
        channel_list.reset()


        back_item = xbmcgui.ListItem(
            label=".."
        )

        back_item.setProperty(
            "type",
            "back"
        )

        channel_list.addItem(back_item)

        self.history.append({
            "level": 3,
            "app_name": app_name,
            "app_url": app_url
        })

        # Rechte Browser-Fläche einschalten.
        # Im Moment nur schwarze Testfläche,
        # später kommt hier das Browserbild hin.
        self.setProperty(
            "HbbTVBrowser",
            "true"
        )

        xbmc.log(
            f"HbbTV: Ebene 3 vorbereitet - "
            f"{app_name}, URL={app_url}",
            xbmc.LOGINFO
        )

        # ---------------------------------------------------------
        # ALTER IFO-TEST - bleibt erhalten, derzeit deaktiviert
        # ---------------------------------------------------------
        #
        # Hier wird später für den gewählten Sender/App-Link
        # die VIDEO_TS.IFO neu erstellt.
        #
        # create_hbbtv_ifo(...)
        #
        # TEST: vorhandene feste VIDEO_TS.IFO öffnen
        #
        # ifo_path = xbmcvfs.translatePath(
        #     "special://home/addons/hbbtv-hts/hbbtv-dvd/VIDEO_TS.IFO"
        # )
        #
        # xbmc.log(
        #     f"HbbTV: Ebene 3 TEST - öffne VIDEO_TS.IFO: {ifo_path}",
        #     xbmc.LOGINFO
        # )
        #
        # xbmc.Player().play(ifo_path)
    def go_back(self):
        if len(self.history) <= 1:
            return

        # Aktuelle Seite entfernen.
        self.history.pop()

        # Vorherige Seite merken.
        previous = self.history[-1]

        # Die show_* Funktion würde die Seite sonst erneut
        # in die History eintragen.
        self.history.pop()

        level = previous["level"]

        xbmc.log(
            f"HbbTV: History zurück -> Ebene {level}",
            xbmc.LOGINFO
        )

        if level == 1:
            self.setProperty(
                "HbbTVBrowser",
                "false"
            )

            self.show_level_1()
            return

        if level == 2:
            self.setProperty(
                "HbbTVBrowser",
                "false"
            )

            self.show_level_2(
                previous["iuniqueid"],
                previous["channel_name"]
            )
            return
    def onClick(self, control_id):
        if control_id != LIST_ID:
            return

        channel_list = self.getControl(LIST_ID)
        selected_item = channel_list.getSelectedItem()

        if selected_item is None:
            return

        item_type = selected_item.getProperty("type")

        # Ebene 1 -> Ebene 2
        if self.level == 1 and item_type == "channel":
            iuniqueid = selected_item.getProperty("iUniqueId")
            channel_name = selected_item.getLabel()

            xbmc.log(
                f"HbbTV: Ebene 1 -> 2: "
                f"{channel_name}, iUniqueId={iuniqueid}",
                xbmc.LOGINFO
            )

            self.show_level_2(
                iuniqueid,
                channel_name
            )
            return

        # ".." bedeutet immer genau eine Seite zurück.
        if item_type == "back":
            self.go_back()
            return

        # Ebene 2 -> Ebene 3
        if self.level == 2 and item_type == "app":
            app_name = selected_item.getLabel()
            app_url = selected_item.getProperty("url")

            xbmc.log(
                f"HbbTV: Ebene 2 -> 3: {app_name}",
                xbmc.LOGINFO
            )

            self.show_level_3(
                app_name,
                app_url
                
            )
            return



addon_path = xbmcvfs.translatePath(
    "special://home/addons/hbbtv-hts"
)

window = HbbTVWindow(
    XML_FILE,
    addon_path
)

window.doModal()

del window
