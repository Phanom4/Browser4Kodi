import ctypes
import os
import threading

import xbmc
import xbmcgui
import time
import xbmcvfs

from browser_retroplayer import RetroPlayerFrontend


EXE = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(EXE, "build", "Linux_x64", "browser.so")
# Kodi ermittelt das Benutzerverzeichnis plattformunabhängig.
DATA_DIR = xbmcvfs.translatePath(
    "special://profile/addon_data/browser4kodi/"
)

os.environ["BROWSER4KODI_DATA_DIR"] = DATA_DIR

# Gemeinsame Steuerung über das Kodi-Home-Fenster
window = xbmcgui.Window(10000)

class BrowserMonitor(xbmc.Monitor):

    def __init__(self):
        super().__init__()
        self.quitting = threading.Event()

    def onNotification(self, sender, method, data):
        if method == "System.OnQuit":
            log("SHUTDOWN: System.OnQuit empfangen")
            self.quitting.set()


monitor = BrowserMonitor()

ACTIVE = "browser.ControllerActive"
REQUEST = "browser.OpenRequested"
BACKEND_SHUTDOWN = "browser.BackendShutdownRequested"


def log(message):
    xbmc.log("browser: " + str(message), xbmc.LOGINFO)


def selected_frontend():
    return "retro"


# Bereits laufende CEF-Steuerung weiterverwenden
if window.getProperty(ACTIVE) == "1":

    browser = ctypes.CDLL(
        LIBRARY,
        mode=os.RTLD_NOW | os.RTLD_NODELETE
    )

    browser.browser_open_default.argtypes = []
    browser.browser_open_default.restype = None

    # Bestehende CEF-Instanz auf die Startseite zurücksetzen
    browser.browser_open_default()

    window.setProperty(REQUEST, selected_frontend())
    log("Vorhandene CEF-Steuerung mit Startseite angefordert")

else:
    browser = ctypes.CDLL(
        LIBRARY,
        mode=os.RTLD_NOW | os.RTLD_NODELETE
    )

    browser.browser_run.argtypes = []
    browser.browser_run.restype = ctypes.c_int

    browser.browser_stop.argtypes = []
    browser.browser_stop.restype = None

    browser.browser_backend_shutdown.argtypes = []
    browser.browser_backend_shutdown.restype = None

    browser.browser_backend_active.argtypes = []
    browser.browser_backend_active.restype = ctypes.c_int

    screen_width = int(xbmcgui.getScreenWidth())
    screen_height = int(xbmcgui.getScreenHeight())

    if screen_width <= 0 or screen_height <= 0:
        raise RuntimeError("Ungueltige Kodi-Aufloesung")

    browser.browser_set_resolution.argtypes = [
        ctypes.c_int, ctypes.c_int
    ]
    browser.browser_set_resolution.restype = None

    browser.browser_set_resolution(
        screen_width, screen_height
    )

    log("Kodi-Aufloesung: {}x{}".format(
        screen_width, screen_height
    ))

    cef_result = [None]

    def run_cef():
        log("CEF START")
        cef_result[0] = browser.browser_run()
        log("CEF RETURN = {}".format(cef_result[0]))

    cef_thread = None
    frontend = None

    window.setProperty(ACTIVE, "1")
    window.setProperty(REQUEST, selected_frontend())

    try:
        # CEF gehört ausschließlich dieser Steuerung
        cef_thread = threading.Thread(
            target=run_cef,
            name="browser_cef"
        )

        cef_thread.start()

        # Steuerung bleibt bis zum Kodi-Shutdown bestehen
        last_debug = time.monotonic()
        backend_shutdown_requested = False
        while True:
            if monitor.quitting.is_set():
                log("SHUTDOWN: Python-Steuerung beenden")
                break

            if monitor.abortRequested():
                log("SHUTDOWN: abortRequested = True")
                break

            if window.getProperty(BACKEND_SHUTDOWN) == "1":
                window.clearProperty(BACKEND_SHUTDOWN)

                if not backend_shutdown_requested:
                    backend_shutdown_requested = True
                    log("BACKEND Shutdown-Test gestartet")
                    browser.browser_backend_shutdown()

            if backend_shutdown_requested:
                if browser.browser_backend_active() == 0:
                    log("BACKEND CefShutdown abgeschlossen")
                    break

                monitor.waitForAbort(0.2)
                continue

            request = window.getProperty(REQUEST)

            if not request:
                aborted = monitor.waitForAbort(0.2)
                now = time.monotonic()
                if now - last_debug >= 2:
                    last_debug = now
                    
                if aborted:
                    log("SHUTDOWN: waitForAbort = True")
                    break

                continue

            window.clearProperty(REQUEST)

            if request != "retro":
                continue

            log("RetroPlayer starten")
            frontend = RetroPlayerFrontend(
                browser, monitor, screen_width, screen_height
            )

            try:
                frontend.start()
                frontend.wait(cef_thread)

            except Exception as error:
                log("Frontend-Fehler: " + repr(error))

            finally:
                # Ausschließlich Player/Videoausgabe trennen
                frontend.stop()
                frontend = None
                log("Frontend getrennt, CEF bleibt bestehen")

            if not cef_thread.is_alive():
                log("CEF-Thread beendet")
                break

    finally:
        log("SHUTDOWN: finally erreicht")
        if frontend is not None:
            frontend.stop()

        window.clearProperty(REQUEST)
        window.clearProperty(ACTIVE)

        # CEF nur beim Beenden der zentralen Steuerung stoppen
        if cef_thread is not None:
            log("CEF herunterfahren")
            browser.browser_stop()
            log("SHUTDOWN: CEF-Thread join BEGIN")
            cef_thread.join(timeout=5)
            log("SHUTDOWN: CEF-Thread join ENDE")

        log("ENDE")
