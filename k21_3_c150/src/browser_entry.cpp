#include "browser.h"
#include "browser_url.h"
#include "browser_osd.h"

#include <sqlite3.h>
#include "include/cef_command_line.h"
#include "include/cef_app.h"
#include "include/cef_browser.h"
#include "include/cef_browser_process_handler.h"
#include "include/cef_client.h"
#include "include/cef_life_span_handler.h"
#include "include/cef_task.h"
#include "include/cef_parser.h"
#include <iostream>
#include <sstream>
#include <cstdio>
#include <condition_variable>
#include <cstdlib>
#include <filesystem>
#include <dlfcn.h>
#include <mutex>
#include <thread>


#include "include/cef_audio_handler.h"

CefRefPtr<CefAudioHandler> browser_create_audio_handler();

namespace
{



std::mutex g_mutex;
std::condition_variable g_cv;
std::thread g_owner;

bool g_initialized = false;
bool g_ready = false;
bool g_contextReady = false;
bool g_running = false;
bool g_finished = false;
bool g_creating = false;
bool g_closePending = false;
bool g_closing = false;
bool g_shutdown = false;

int g_result = 0;

int g_screenWidth = 1280;
int g_screenHeight = 720;

CefRefPtr<CefBrowser> g_browser;
CefRefPtr<CefClient> g_client;

// ============================================================
// Popup-URL im bestehenden Browser oeffnen
// ============================================================

class PopupRedirectTask final : public CefTask
{
public:
    PopupRedirectTask(CefRefPtr<CefBrowser> browser,
                      const std::string& url)
        : m_browser(browser), m_url(url)
    {
    }

    void Execute() override
    {
        if (!m_browser || m_url.empty())
            return;

        auto frame = m_browser->GetMainFrame();

        if (frame)
            frame->LoadURL(m_url);
    }

private:
    CefRefPtr<CefBrowser> m_browser;
    std::string m_url;

    IMPLEMENT_REFCOUNTING(PopupRedirectTask);
};

class SimpleClient final : public CefClient,
                           public CefDisplayHandler,
                           public CefLifeSpanHandler,
                           public CefLoadHandler
{
public:
    SimpleClient()
        : m_renderer(new CBrowser_21_3(g_screenWidth, g_screenHeight)),
          m_audio(browser_create_audio_handler())
    {
    }

    CefRefPtr<CefRenderHandler> GetRenderHandler() override
    {
        return m_renderer;
    }
    CefRefPtr<CefAudioHandler> GetAudioHandler() override
    {
    return m_audio;
    }

    CefRefPtr<CefLifeSpanHandler> GetLifeSpanHandler() override
    {
        return this;
    }
    // ============================================================
// Zusaetzliche Browserfenster verhindern
// ============================================================

bool OnBeforePopup(
    CefRefPtr<CefBrowser> browser,
    CefRefPtr<CefFrame> frame,
    int popup_id,
    const CefString& target_url,
    const CefString& target_frame_name,
    WindowOpenDisposition target_disposition,
    bool user_gesture,
    const CefPopupFeatures& popupFeatures,
    CefWindowInfo& windowInfo,
    CefRefPtr<CefClient>& client,
    CefBrowserSettings& settings,
    CefRefPtr<CefDictionaryValue>& extra_info,
    bool* no_javascript_access) override
{
    // Nur bewusst angeklickte Links im bestehenden Browser laden.
    // Automatisch erzeugte Popups dagegen einfach blockieren.
    if (user_gesture && !target_url.empty())
    {
        CefPostTask(
            TID_UI,
            new PopupRedirectTask(browser, target_url.ToString())
        );
    }

    // Niemals ein weiteres CEF-Fenster erzeugen.
    return true;
}

    CefRefPtr<CefDisplayHandler> GetDisplayHandler() override
    {
        return this;
    }

    CefRefPtr<CefLoadHandler> GetLoadHandler() override
    {
        return this;
    }

    // CefDisplayHandler
    void OnTitleChange(
        CefRefPtr<CefBrowser> browser,
        const CefString& title) override
    {
        std::cerr << "browser: Title: "
                  << title.ToString() << std::endl;
    }

    // CefLifeSpanHandler: wie im funktionierenden SimpleHandler
    bool DoClose(CefRefPtr<CefBrowser> browser) override
    {
        {
            std::lock_guard<std::mutex> lock(g_mutex);
            g_closing = true;
        }

        std::cerr << "browser: DoClose" << std::endl;

        return false;
    }

    // CefLoadHandler
    void OnLoadingStateChange(
        CefRefPtr<CefBrowser> browser,
        bool isLoading,
        bool canGoBack,
        bool canGoForward) override
    {
        std::cerr << "browser: LoadState: isLoading="
                  << isLoading
                  << " canGoBack=" << canGoBack
                  << " canGoForward=" << canGoForward
                  << std::endl;
    }

    void OnLoadError(
        CefRefPtr<CefBrowser> browser,
        CefRefPtr<CefFrame> frame,
        ErrorCode errorCode,
        const CefString& errorText,
        const CefString& failedUrl) override
    {
        if (errorCode == ERR_ABORTED)
            return;

        std::cerr << "browser: LoadError: "
                  << failedUrl.ToString()
                  << " error=" << errorText.ToString()
                  << " code=" << errorCode
                  << std::endl;

        // Verhalten der funktionierenden Alloy-Variante:
        // Bei Ladefehlern eine HTML-Fehlerseite anzeigen.
        std::stringstream ss;
        ss << "<html><body bgcolor=\\\"white\\\">"
              "<h2>Failed to load URL "
           << failedUrl.ToString()
           << " with error "
           << errorText.ToString()
           << " (" << errorCode << ").</h2></body></html>";

        const std::string html = ss.str();

        const std::string dataUrl =
            "data:text/html;base64," +
            CefURIEncode(
                CefBase64Encode(html.data(), html.size()),
                false
            ).ToString();

        frame->LoadURL(dataUrl);
    }

    void OnAfterCreated(CefRefPtr<CefBrowser> browser) override
    {
        g_browser = browser;
        g_creating = false;

        bool closeNow = false;

        {
            std::lock_guard<std::mutex> lock(g_mutex);

            closeNow = g_shutdown;

            if (closeNow)
                g_closing = true;
        }

        if (closeNow)
            browser->GetHost()->CloseBrowser(true);
    }

    void OnBeforeClose(CefRefPtr<CefBrowser> browser) override
    {
        g_browser = nullptr;
        g_client = nullptr;
        g_creating = false;

        bool quit = false;

        {
            std::lock_guard<std::mutex> lock(g_mutex);

            g_running = false;
            g_finished = true;
            g_closing = false;
            g_closePending = false;
            g_result = 1;

            quit = g_shutdown;

            g_cv.notify_all();
        }

        if (quit)
            CefQuitMessageLoop();
    }

private:
    CefRefPtr<CBrowser_21_3> m_renderer;
    CefRefPtr<CefAudioHandler> m_audio;

    IMPLEMENT_REFCOUNTING(SimpleClient);
};

// Letzte besuchte URL aus der Chromium-History lesen.
// Keine Änderung an der History und keine Verlauf-Rekonstruktion.
std::string LastHistoryUrl()
{
    namespace fs = std::filesystem;

    Dl_info info{};

    if (!dladdr(reinterpret_cast<void*>(&LastHistoryUrl), &info) ||
        !info.dli_fname)
        return {};

    const fs::path base =
        fs::absolute(info.dli_fname).parent_path().parent_path().parent_path();

    const fs::path history = base / "cache/Default/History";

    sqlite3* db = nullptr;

    if (sqlite3_open_v2(
            history.string().c_str(),
            &db,
            SQLITE_OPEN_READONLY,
            nullptr) != SQLITE_OK)
    {
        if (db)
            sqlite3_close(db);
        return {};
    }

    sqlite3_busy_timeout(db, 1000);

    const char* sql =
        "SELECT url FROM urls "
        "WHERE last_visit_time > 0 "
        "ORDER BY last_visit_time DESC LIMIT 1";

    sqlite3_stmt* statement = nullptr;
    std::string url;

    if (sqlite3_prepare_v2(db, sql, -1, &statement, nullptr)
        == SQLITE_OK)
    {
        if (sqlite3_step(statement) == SQLITE_ROW)
        {
            const auto* value = sqlite3_column_text(statement, 0);

            if (value)
                url = reinterpret_cast<const char*>(value);
        }
    }

    if (statement)
        sqlite3_finalize(statement);

    sqlite3_close(db);
    return url;
}

enum class Command
{
    Open,
    Quit
};

void ExecuteCommand(Command command)
{
    if (command == Command::Open)
{
    {
        std::lock_guard<std::mutex> lock(g_mutex);

        if (g_shutdown || g_creating)
            return;
    }

    std::string url;
    const bool hasPending = browser21url::TakePending(url);

    if (!hasPending)
    {
        const auto mode = browser21osd::GetStartMode();

        if (mode == browser21osd::StartMode::LastPage)
        {
            // Laufenden Browser unverändert weiterverwenden.
            if (g_browser)
                return;

            // Nur beim erstmaligen Erzeugen aus History lesen.
            url = LastHistoryUrl();
        }

        if (url.empty())
            url = browser21osd::GetHomepage();
    }

    // Vorhandenen CEF-Browser wiederverwenden.
    if (g_browser)
    {
        g_browser->GetMainFrame()->LoadURL(url);
        g_browser->GetHost()->Invalidate(PET_VIEW);
        return;
    }

    // CEF-Browser erstmalig erzeugen.
    g_client = new SimpleClient;
    g_creating = true;

    CefWindowInfo windowInfo;
    windowInfo.SetAsWindowless(0);
    windowInfo.runtime_style = CEF_RUNTIME_STYLE_ALLOY;

    CefBrowserSettings browserSettings;

    const bool accepted = CefBrowserHost::CreateBrowser(
        windowInfo,
        g_client,
        url,
        browserSettings,
        nullptr,
        nullptr
    );

    if (!accepted)
    {
        g_creating = false;
        g_client = nullptr;

        std::lock_guard<std::mutex> lock(g_mutex);

        g_running = false;
        g_finished = true;
        g_result = -2;

        g_cv.notify_all();
    }

    return;
}

    if (command == Command::Quit)
    {
        {
            std::lock_guard<std::mutex> lock(g_mutex);
            g_closePending = true;
        }

        if (g_browser)
        {
            g_browser->GetHost()->CloseBrowser(true);
        }
        else if (!g_creating)
        {
            CefQuitMessageLoop();
        }
    }
}

// ============================================================
// Browser-Navigation auf dem CEF-UI-Thread
// ============================================================

class BrowserZoomTask final : public CefTask
{
public:
    explicit BrowserZoomTask(int action) : m_action(action) {}

    void Execute() override
    {
        if (!g_browser)
            return;

        auto host = g_browser->GetHost();
        if (!host)
            return;

        double level = host->GetZoomLevel();

        if (m_action == 0)
            level = 0.0;
        else if (m_action > 0)
            level += 1.0;
        else
            level -= 1.0;

        if (level < -10.0)
            level = -10.0;
        if (level > 10.0)
            level = 10.0;

        host->SetZoomLevel(level);
    }

private:
    int m_action;
    IMPLEMENT_REFCOUNTING(BrowserZoomTask);
};

class BrowserNavigationTask final : public CefTask
{
public:
    explicit BrowserNavigationTask(int action)
        : m_action(action)
    {
    }

    void Execute() override
    {
        if (!g_browser)
            return;

        switch (m_action)
        {
            case 1: // Zurueck
                if (g_browser->CanGoBack())
                    g_browser->GoBack();
                break;

            case 2: // Vorwaerts
                if (g_browser->CanGoForward())
                    g_browser->GoForward();
                break;

            case 3: // Neu laden
                g_browser->Reload();
                break;
        }
    }

private:
    int m_action;

    IMPLEMENT_REFCOUNTING(BrowserNavigationTask);
};

class MouseTask final : public CefTask
{
public:
    MouseTask(int type, int x, int y, int value1, int value2)
        : m_type(type), m_x(x), m_y(y),
          m_value1(value1), m_value2(value2)
    {
    }

    void Execute() override
    {
        if (!g_browser)
            return;

        auto host = g_browser->GetHost();
        if (!host)
            return;

        CefMouseEvent event;
        event.x = m_x;
        event.y = m_y;
        event.modifiers = 0;

        switch (m_type)
        {
            case 0:
{
    static FILE* log = std::fopen("/tmp/browser_cef_mouse.log", "a");

    if (log)
    {
        std::fprintf(log, "CEF UI: x=%d y=%d\n", event.x, event.y);
        std::fflush(log);
    }

    host->SendMouseMoveEvent(event, false);
    break;
}

            case 1:
                host->SendMouseClickEvent(
                    event,
                    m_value1 == 2 ? MBT_RIGHT :
                    m_value1 == 3 ? MBT_MIDDLE : MBT_LEFT,
                    m_value2 == 0,
                    1);
                break;

            case 2:
                host->SendMouseWheelEvent(
                    event, m_value1, m_value2);
                break;
        }
    }

private:
    int m_type;
    int m_x;
    int m_y;
    int m_value1;
    int m_value2;

    IMPLEMENT_REFCOUNTING(MouseTask);
};

// CEF-Eingabe auf dem vorhandenen CEF-UI-Thread ausführen.
class KeyTask final : public CefTask
{
public:
    KeyTask(int pressed, int vkey, int native, unsigned int unicode,
            unsigned int kodiModifiers)
      : m_pressed(pressed), m_vkey(vkey), m_native(native),
        m_unicode(unicode), m_modifiers(kodiModifiers) {}

    void Execute() override
    {
        if (!g_browser) return;
        auto host = g_browser->GetHost();
        if (!host) return;
        if (m_pressed) host->SetFocus(true);

        int flags = 0;
        if (m_modifiers & 0x00010000u) flags |= EVENTFLAG_CONTROL_DOWN;
        if (m_modifiers & 0x00020000u) flags |= EVENTFLAG_SHIFT_DOWN;
        if (m_modifiers & 0x00040000u) flags |= EVENTFLAG_ALT_DOWN;
        if (m_modifiers & 0x00080000u) flags |= EVENTFLAG_ALTGR_DOWN;
        if (m_modifiers & 0x02000000u) flags |= EVENTFLAG_NUM_LOCK_ON;
        if (m_modifiers & 0x04000000u) flags |= EVENTFLAG_CAPS_LOCK_ON;

        CefKeyEvent event;
        event.type = m_pressed ? KEYEVENT_RAWKEYDOWN : KEYEVENT_KEYUP;
        event.windows_key_code = m_vkey;
        event.native_key_code = m_native;
        event.modifiers = flags;
        host->SendKeyEvent(event);

        // Text bei KeyDown gesondert als Unicode an CEF senden.
        // Ctrl/Alt sind Shortcuts und erzeugen keinen normalen Text.
        if (m_pressed && m_unicode &&
            !(flags & (EVENTFLAG_CONTROL_DOWN | EVENTFLAG_ALT_DOWN)))
        {
            event.type = KEYEVENT_CHAR;
            if (m_unicode <= 0xFFFFu)
            {
                event.character = static_cast<char16_t>(m_unicode);
                event.unmodified_character = event.character;
                host->SendKeyEvent(event);
            }
            else if (m_unicode <= 0x10FFFFu)
            {
                const unsigned int value = m_unicode - 0x10000u;
                event.character = static_cast<char16_t>(0xD800u + (value >> 10));
                event.unmodified_character = event.character;
                host->SendKeyEvent(event);
                event.character = static_cast<char16_t>(0xDC00u + (value & 0x3FFu));
                event.unmodified_character = event.character;
                host->SendKeyEvent(event);
            }
        }
    }
private:
    int m_pressed;
    int m_vkey;
    int m_native;
    unsigned int m_unicode;
    unsigned int m_modifiers;
    IMPLEMENT_REFCOUNTING(KeyTask);
};

class BrowserTask final : public CefTask
{
public:
    explicit BrowserTask(Command command)
        : m_command(command)
    {
    }

    void Execute() override
    {
        ExecuteCommand(m_command);
    }

private:
    Command m_command;

    IMPLEMENT_REFCOUNTING(BrowserTask);
};

void PostCommand(Command command)
{
    CefPostTask(TID_UI, new BrowserTask(command));
}

class SimpleApp final : public CefApp,
                        public CefBrowserProcessHandler
{
public:
    void OnBeforeCommandLineProcessing(
        const CefString& process_type,
        CefRefPtr<CefCommandLine> command_line) override
    {
        if (process_type.empty())
        {
            command_line->AppendSwitchWithValue(
                "autoplay-policy", "no-user-gesture-required");
        }
    }

    CefRefPtr<CefBrowserProcessHandler>
    GetBrowserProcessHandler() override
    {
        return this;
    }

    void OnContextInitialized() override
    {
        std::lock_guard<std::mutex> lock(g_mutex);

        g_contextReady = true;
        g_cv.notify_all();
    }

private:
    IMPLEMENT_REFCOUNTING(SimpleApp);
};

void OwnerThread()
{
    namespace fs = std::filesystem;

    Dl_info info{};
    if (dladdr(reinterpret_cast<void*>(&OwnerThread), &info) == 0 ||
        !info.dli_fname)
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        g_ready = true;
        g_cv.notify_all();
        return;
    }

    const fs::path base =
        fs::absolute(info.dli_fname).parent_path().parent_path().parent_path();
    const fs::path cef = base / "cef/Release";
    const fs::path build = base / "build/Linux_x64";

    char processName[] = "browser";
    char native[] = "--use-native";
    char alloy[] = "--use-alloy-style";
    char sandbox[] = "--no-sandbox";

    char* argv[] = {
        processName,
        native,
        alloy,
        sandbox,
        nullptr
    };

    CefMainArgs mainArgs(4, argv);

    CefSettings settings;
    CefString(&settings.root_cache_path) =
        (base / "cache").string();

    CefString(&settings.cache_path) =
        (base / "cache").string();

    settings.no_sandbox = true;
    settings.windowless_rendering_enabled = true;
    settings.remote_debugging_port = 9229;
    settings.multi_threaded_message_loop = false;

    CefString(&settings.browser_subprocess_path) =
        (build / "browser_helper").string();

    CefString(&settings.resources_dir_path) =
        (base / "cef/Resources").string();

    CefString(&settings.locales_dir_path) =
        (base / "cef/Resources/locales").string();

    CefRefPtr<SimpleApp> app(new SimpleApp);

    const bool initialized =
        CefInitialize(mainArgs, settings, app.get(), nullptr);

    {
        std::lock_guard<std::mutex> lock(g_mutex);

        g_initialized = initialized;
        g_ready = true;

        g_cv.notify_all();
    }

    if (!initialized)
        return;

    // CEF verarbeitet seine Ereignisse jetzt selbst.
    // Die Loop bleibt auch ohne geöffneten Browser aktiv.
    CefRunMessageLoop();

    std::cerr << "browser: BACKEND CefShutdown BEGIN"
              << std::endl;

    CefShutdown();

    std::cerr << "browser: BACKEND CefShutdown ENDE"
              << std::endl;

    {
        std::lock_guard<std::mutex> lock(g_mutex);

        g_initialized = false;
        g_contextReady = false;

        g_cv.notify_all();
    }
}

void ShutdownAtExit()
{
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        g_shutdown = true;
    }

    if (!g_owner.joinable())
        return;

    if (g_initialized && g_contextReady)
        PostCommand(Command::Quit);

    g_owner.join();
}

} // namespace

extern "C"
{


void browser_key_event(int pressed, int vkey, int native,
                           unsigned int unicode, unsigned int kodiModifiers)
{
    if (!g_initialized || !g_contextReady)
        return;
    CefPostTask(TID_UI,
                new KeyTask(pressed, vkey, native, unicode, kodiModifiers));
}

void browser_open_url()
{
    if (!g_initialized || !g_contextReady)
        return;

    PostCommand(Command::Open);
}

void browser_zoom(int action)
{
    if (action < -1 || action > 1)
        return;

    if (!g_initialized || !g_contextReady)
        return;

    CefPostTask(TID_UI, new BrowserZoomTask(action));
}

void browser_navigation(int action)
{
    if (action < 1 || action > 3)
        return;

    if (!g_initialized || !g_contextReady)
        return;

    CefPostTask(
        TID_UI,
        new BrowserNavigationTask(action)
    );
}

void browser_mouse_move(int x, int y)
{
    if (!g_initialized || !g_contextReady)
        return;

    CefPostTask(TID_UI, new MouseTask(0, x, y, 0, 0));
}

void browser_mouse_button(
    int x, int y, int button, int pressed)
{
    if (!g_initialized || !g_contextReady)
        return;

    CefPostTask(TID_UI, new MouseTask(
        1, x, y, button, pressed));
}

void browser_mouse_wheel(
    int x, int y, int deltaX, int deltaY)
{
    if (!g_initialized || !g_contextReady)
        return;

    CefPostTask(TID_UI, new MouseTask(
        2, x, y, deltaX, deltaY));
}

const char* browser_version()
{
    return "browser / CEF 144";
}

// Browser aus dem Kodi-Hauptmenü erneut öffnen:
// bestehende CEF-Instanz verwenden, Standard-URL laden.
void browser_open_default()
{
    if (!g_initialized || !g_contextReady)
        return;

    PostCommand(Command::Open);
}

// Manueller Test: Nur das CEF-Backend herunterfahren.
void browser_backend_shutdown()
{
    bool ready = false;

    {
        std::lock_guard<std::mutex> lock(g_mutex);

        if (g_shutdown || !g_initialized)
            return;

        g_shutdown = true;
        ready = g_contextReady;
    }

    std::cerr << "browser: BACKEND Shutdown angefordert"
              << std::endl;

    if (ready)
        PostCommand(Command::Quit);
}

// Status erst nach abgeschlossenem CefShutdown() = 0.
int browser_backend_active()
{
    std::lock_guard<std::mutex> lock(g_mutex);
    return g_initialized ? 1 : 0;
}

// Kodi-Auflösung vor der CEF-Initialisierung setzen.
void browser_set_resolution(int width, int height)
{
    if (width <= 0 || height <= 0)
        return;

    std::lock_guard<std::mutex> lock(g_mutex);

    if (g_owner.joinable())
        return;

    g_screenWidth = width;
    g_screenHeight = height;

    std::cerr << "browser: CEF Aufloesung "
              << width << "x" << height << std::endl;
}

void browser_stop()
{
    std::lock_guard<std::mutex> lock(g_mutex);

    if (!g_running)
        return;

    g_running = false;
    g_finished = true;
    g_result = 1;

    g_cv.notify_all();

    // CEF und Browser bleiben bestehen.
}

int browser_run()
{
    std::unique_lock<std::mutex> lock(g_mutex);

    if (g_running)
        return 2;

    if (g_shutdown)
        return -1;

    if (!g_owner.joinable())
    {
        g_owner = std::thread(OwnerThread);
        std::atexit(ShutdownAtExit);
    }

    g_cv.wait(lock, [] {
        return g_ready;
    });

    if (!g_initialized)
        return -1;

    g_cv.wait(lock, [] {
        return g_contextReady || !g_initialized;
    });

    if (!g_initialized)
        return -1;

    g_running = true;
    g_finished = false;
    g_closePending = false;
    g_closing = false;
    g_result = 0;

    lock.unlock();

    PostCommand(Command::Open);

    lock.lock();

    g_cv.wait(lock, [] {
        return g_finished;
    });

    return g_result;
}

} // extern "C"
