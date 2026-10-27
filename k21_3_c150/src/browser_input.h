#pragma once

// Browser 21.3: Kodi-Driver-Eingabe an die bestehende CEF-Instanz.
// Diese Datei wird ausschließlich von browser_retro.cpp eingebunden.

#include "ServiceBroker.h"
#include "input/InputManager.h"
#include "input/keyboard/Key.h"
#include "input/keyboard/XBMC_vkeys.h"
#include "input/keyboard/interfaces/IKeyboardDriverHandler.h"
#include "input/mouse/interfaces/IMouseDriverHandler.h"
#include "guilib/GUIComponent.h"
#include "guilib/GUIDialog.h"
#include "guilib/GUIWindowManager.h"
#include "guilib/WindowIDs.h"
#include "windowing/WinSystem.h"
#include "windowing/GraphicContext.h"
#include <cstdio>
#include "browser_osd.h"

#include <algorithm>

extern "C" {
void browser_mouse_move(int x, int y);
void browser_mouse_button(int x, int y, int button, int pressed);
void browser_mouse_wheel(int x, int y, int deltaX, int deltaY);
void browser_key_event(int pressed, int vkey, int native, unsigned int unicode,
                             unsigned int kodiModifiers);
void browser_navigation(int action);
void browser_open_url();
}

namespace browser21input {

// Kodi-XBMCVKey entspricht bei Sondertasten NICHT Windows-VK.
// CEF erwartet für windows_key_code Windows-VK-Werte.
inline int WindowsVKey(int vk) {
    switch (vk) {
        case XBMCVK_LCONTROL: case XBMCVK_RCONTROL: return 0x11;
        case XBMCVK_LSHIFT: case XBMCVK_RSHIFT: return 0x10;
        case XBMCVK_LMENU: case XBMCVK_RMENU: return 0x12;
        case XBMCVK_LEFT: return 0x25;
        case XBMCVK_UP: return 0x26;
        case XBMCVK_RIGHT: return 0x27;
        case XBMCVK_DOWN: return 0x28;
        case XBMCVK_PAGEUP: return 0x21;
        case XBMCVK_PAGEDOWN: return 0x22;
        case XBMCVK_END: return 0x23;
        case XBMCVK_HOME: return 0x24;
        case XBMCVK_INSERT: return 0x2D;
        case XBMCVK_DELETE: return 0x2E;
        case XBMCVK_CAPSLOCK: return 0x14;
        case XBMCVK_NUMLOCK: return 0x90;
        case XBMCVK_SCROLLLOCK: return 0x91;
        case XBMCVK_PRINTSCREEN: return 0x2C;
        default:
            if (vk >= XBMCVK_F1 && vk <= XBMCVK_F24)
                return 0x70 + (vk - XBMCVK_F1);
            return vk;
    }
}

class Handler final : public KODI::MOUSE::IMouseDriverHandler,
                      public KODI::KEYBOARD::IKeyboardDriverHandler {
public:
bool OnPosition(int x, int y) override {
    static FILE* log = std::fopen("/tmp/browser_mouse.log", "a");

    const bool active = CefActive();

    if (log) {
        std::fprintf(log, "KODI: x=%d y=%d active=%d\n",
                     x, y, active ? 1 : 0);
        std::fflush(log);
    }

    if (!active) {
    CServiceBroker::GetWinSystem()->ShowOSMouse(false);
    return false;
}

CServiceBroker::GetWinSystem()->ShowOSMouse(true);

    m_x = x;
    m_y = y;

    const int cefX = ScaledX();
    const int cefY = ScaledY();

    if (log) {
        std::fprintf(log, "CEF:  x=%d y=%d\n", cefX, cefY);
        std::fflush(log);
    }

    browser_mouse_move(cefX, cefY);
    return true;
}

    bool OnButtonPress(KODI::MOUSE::BUTTON_ID button) override {
        if (!CefActive()) return false;
        using KODI::MOUSE::BUTTON_ID;
        switch (button) {
            case BUTTON_ID::LEFT:   MouseButton(1, 1); return true;
            case BUTTON_ID::RIGHT:
    // Rechtsklick fuer unser Kodi-Browsermenue reservieren.
    // Nicht an CEF weitergeben.
    return true;
            case BUTTON_ID::MIDDLE: MouseButton(3, 1); return true;
            case BUTTON_ID::WHEEL_UP:         Wheel(0, 120); return true;
            case BUTTON_ID::WHEEL_DOWN:       Wheel(0, -120); return true;
            case BUTTON_ID::HORIZ_WHEEL_LEFT: Wheel(-120, 0); return true;
            case BUTTON_ID::HORIZ_WHEEL_RIGHT:Wheel(120, 0); return true;
            default: return false;
        }
    }

    void OnButtonRelease(KODI::MOUSE::BUTTON_ID button) override {
        if (!CefActive()) return;
        using KODI::MOUSE::BUTTON_ID;
        switch (button) {
            case BUTTON_ID::LEFT:   MouseButton(1, 0); break;
            case BUTTON_ID::RIGHT:
{
    const auto action = browser21osd::Show();

    switch (action)
    {
        case browser21osd::Action::Back:
            browser_navigation(1);
            break;

        case browser21osd::Action::Forward:
            browser_navigation(2);
            break;

        case browser21osd::Action::Reload:
            browser_navigation(3);
            break;
        case browser21osd::Action::UrlSubmitted:
            browser_open_url();
            break;

        case browser21osd::Action::Exit:
            CServiceBroker::GetGUI()
               ->GetWindowManager()
               .ActivateWindow(WINDOW_HOME);
            break;

        default:
            break;
    }

    break;
}
            case BUTTON_ID::MIDDLE: MouseButton(3, 0); break;
            default: break;  // Mausrad hat kein Release-Ereignis für CEF
        }
    }

    bool OnKeyPress(const CKey& key) override {
        if (!CefActive()) return false;

        // Einzige reservierte Tastenkombination: Strg+B -> eigenes Kodi-OSD.
        if (key.GetVKey() == XBMCVK_B &&
    (key.GetModifiers() & CKey::MODIFIER_CTRL)) {
    // Strg-Zustand in CEF freigeben.
    browser_key_event(0, 0x11, 0, 0, 0);

    // Dasselbe Browser-Menue wie beim Rechtsklick verwenden.
    OnButtonRelease(KODI::MOUSE::BUTTON_ID::RIGHT);
    return true;
}

        browser_key_event(1, WindowsVKey(key.GetVKey()), key.GetKeycode(),
                              static_cast<unsigned int>(key.GetUnicode()),
                              key.GetModifiers());
        return true;
    }

    void OnKeyRelease(const CKey& key) override {
        if (!CefActive()) return;
        browser_key_event(0, WindowsVKey(key.GetVKey()), key.GetKeycode(),
                              0, key.GetModifiers());
    }

private:
    bool CefActive() const {
        auto& wm = CServiceBroker::GetGUI()->GetWindowManager();
        if (wm.GetActiveWindowOrDialog() != WINDOW_FULLSCREEN_GAME) return false;
        if (wm.IsWindowVisible(WINDOW_DIALOG_GAME_OSD)) return false;
        auto* osd = wm.GetDialog(WINDOW_DIALOG_GAME_OSD);
        return !osd || !osd->IsDialogRunning();
    }

    int ScaledX() const {
        const int width = std::max(1, CServiceBroker::GetWinSystem()
                                         ->GetGfxContext().GetWidth());
        return std::clamp(static_cast<int>(static_cast<long long>(m_x) * 1280 / width),
                          0, 1279);
    }
    int ScaledY() const {
        const int height = std::max(1, CServiceBroker::GetWinSystem()
                                          ->GetGfxContext().GetHeight());
        return std::clamp(static_cast<int>(static_cast<long long>(m_y) * 720 / height),
                          0, 719);
    }
    void MouseButton(int button, int pressed) {
        browser_mouse_button(ScaledX(), ScaledY(), button, pressed);
    }
    void Wheel(int dx, int dy) {
        browser_mouse_wheel(ScaledX(), ScaledY(), dx, dy);
    }

    int m_x{0};
    int m_y{0};
};

inline Handler& Instance() {
    static Handler handler;
    return handler;
}
inline void Register() {
    auto& manager = CServiceBroker::GetInputManager();
    manager.RegisterMouseDriverHandler(&Instance());
    manager.RegisterKeyboardDriverHandler(&Instance());
}
inline void Unregister() {
    CServiceBroker::GetWinSystem()->ShowOSMouse(false);

    auto& manager = CServiceBroker::GetInputManager();
    manager.UnregisterKeyboardDriverHandler(&Instance());
    manager.UnregisterMouseDriverHandler(&Instance());
}

} // namespace browser21input
