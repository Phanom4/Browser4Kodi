#include "browser_osd.h"
#include "browser_url.h"

#include "ServiceBroker.h"
#include "dialogs/GUIDialogSelect.h"
#include "guilib/GUIComponent.h"
#include "guilib/GUIKeyboardFactory.h"
#include "guilib/GUIWindowManager.h"
#include "guilib/WindowIDs.h"
#include "utils/Variant.h"

#include <atomic>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>

namespace browser21osd
{
namespace
{
std::atomic<StartMode> g_startMode{StartMode::Home};

// Startseite im Kodi-Benutzerprofil speichern.
const std::filesystem::path& HomepageFile()
{
    static const std::filesystem::path path =
        std::filesystem::path(std::getenv("HOME")) /
            ".kodi/userdata/addon_data/browser4kodi/homepage.txt";
    return path;
}

std::string GetHomepage()
{
    std::ifstream file(HomepageFile());
    std::string url;

    if (file && std::getline(file, url))
    {
        if (!url.empty() && url.back() == '\r')
            url.pop_back();

        if (url.find_first_not_of(" \\t\\r\\n") != std::string::npos)
            return url;
    }

    return browser21url::DEFAULT_URL;
}

bool SetHomepage(const std::string& url)
{
    if (url.find_first_not_of(" \\t\\r\\n") == std::string::npos)
        return false;

    std::error_code error;
    std::filesystem::create_directories(
        HomepageFile().parent_path(), error);

    if (error)
        return false;

    std::ofstream file(HomepageFile(), std::ios::trunc);

    if (!file)
        return false;

    file << url << '\n';
    return file.good();
}

const char* StartModeLabel()
{
    return GetStartMode() == StartMode::Home ? "Startseite" : "Letzte Seite";
}
} // namespace

StartMode GetStartMode()
{
    return g_startMode.load();
}

void SetStartMode(StartMode mode)
{
    g_startMode.store(mode);
}

Action Show()
{
    // Kodi-Dialoge duerfen nur aus dem GUI-Kontext geoeffnet werden.
    auto* gui = CServiceBroker::GetGUI();
    if (!gui)
        return Action::None;

    auto* menu = static_cast<CGUIDialogSelect*>(
    gui->GetWindowManager().GetWindow(WINDOW_DIALOG_SELECT));
    if (!menu)
        return Action::None;

    while (true)
    {
        menu->Reset();
        menu->SetHeading(CVariant{std::string("Browser")});

        // Die Positionen sind fuer die nachfolgende Auswertung fest.
        menu->Add("Startseite");                  // 0
        menu->Add(GetHomepage());                // 1
        menu->Add("Zurueck");                     // 2
        menu->Add("Vorwaerts");                   // 3
        menu->Add("Neu laden");                   // 4
        menu->Add("Tastatur / URL eingeben");     // 5
        menu->Add(std::string("Startverhalten: ") + StartModeLabel()); // 6
        menu->Add("Verlassen");                   // 7

        menu->Open();
        const int selected = menu->GetSelectedItem();

        switch (selected)
        {
            case 0:
                // Gespeicherte Startseite im vorhandenen Browser laden.
                if (browser21url::Submit(GetHomepage()))
                    return Action::UrlSubmitted;
                return Action::None;

            case 1:
            {
                // Startseitenadresse ändern, ohne sie sofort zu laden.
                std::string url = GetHomepage();

                if (CGUIKeyboardFactory::ShowAndGetInput(
                        url, CVariant{std::string("Startseiten-URL")}, false))
                    SetHomepage(url);

                // Menü mit aktueller Adresse erneut anzeigen.
                continue;
            }

            case 2:
                return Action::Back;

            case 3:
                return Action::Forward;

            case 4:
                return Action::Reload;

            case 5:
            {
                std::string url;

                if (CGUIKeyboardFactory::ShowAndGetInput(
                        url, CVariant{std::string("URL eingeben")}, false) &&
                    browser21url::Submit(url))
                    return Action::UrlSubmitted;

                return Action::None;
            }

            case 6:
                SetStartMode(GetStartMode() == StartMode::Home
                                 ? StartMode::LastPage
                                 : StartMode::Home);
                continue;

            case 7:
                return Action::Exit;

            default:
                return Action::None;
        }
    }
}

} // namespace browser21osd
