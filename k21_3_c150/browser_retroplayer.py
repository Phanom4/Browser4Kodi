import ctypes
import time

import xbmc
import xbmcgui


class RetroPlayerFrontend:


    def __init__(self, browser, monitor, width, height):
        self.browser = browser
        self.monitor = monitor
        self.width = width
        self.height = height
        self.retro = 0
        self.gui = 0

        browser.browser_retro_probe.argtypes = [
            ctypes.c_uint, ctypes.c_uint
        ]
        browser.browser_retro_probe.restype = ctypes.c_int

        browser.browser_retro_frame_count.argtypes = []
        browser.browser_retro_frame_count.restype = ctypes.c_uint

        browser.browser_retro_render_step.argtypes = []
        browser.browser_retro_render_step.restype = ctypes.c_int

        browser.browser_retro_gui_register.argtypes = []
        browser.browser_retro_gui_register.restype = ctypes.c_int

        browser.browser_retro_gui_unregister.argtypes = []
        browser.browser_retro_gui_unregister.restype = None

    def start(self):
        player = xbmc.Player()

        if player.isPlaying():
            player.stop()

        self.retro = self.browser.browser_retro_probe(
            self.width, self.height
        )

        if self.retro != 1:
            raise RuntimeError("RetroPlayer OpenStream fehlgeschlagen")

        self.gui = self.browser.browser_retro_gui_register()

        if self.gui != 1:
            raise RuntimeError("RetroPlayer GUI-Registrierung fehlgeschlagen")

        xbmcgui.Window(10000).setProperty("browser.GameOSD", "1")
        xbmc.executebuiltin("ActivateWindow(FullscreenGame)")

    def wait(self, worker):
        fullscreen_seen = False
        startup_osd_done = False
        startup_osd_deadline = time.monotonic() + 3.0

        while not self.monitor.abortRequested():
            if self.monitor.quitting.is_set():
                xbmc.log(
                    "RetroPlayer: Kodi-Shutdown erkannt",
                    xbmc.LOGINFO
                )
                break

            if self.monitor.waitForAbort(0.2):
                break

            if not worker.is_alive():
                break

            fullscreen = xbmc.getCondVisibility(
                "Window.IsActive(FullscreenGame)"
            )

            if fullscreen:
                fullscreen_seen = True
            elif fullscreen_seen:
                xbmc.log(
                    "RetroPlayer: Vollbild verlassen",
                    xbmc.LOGINFO
                )
                break
                        # GameOSD nur einmal beim Browserstart automatisch schliessen.
            # Spaeteres Strg+B bleibt davon unberuehrt.
            if not startup_osd_done:
                if xbmc.getCondVisibility("Window.IsVisible(10822)"):
                    xbmc.executebuiltin("Dialog.Close(gameosd,true)")
                    startup_osd_done = True

                elif time.monotonic() >= startup_osd_deadline:
                    startup_osd_done = True

            self.browser.browser_retro_render_step()

    def stop(self):
        xbmcgui.Window(10000).clearProperty("browser.GameOSD")
        if self.gui == 1:
            self.browser.browser_retro_gui_unregister()
            self.gui = 0
