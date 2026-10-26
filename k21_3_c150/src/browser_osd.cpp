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
#include <string>

namespace browser21osd
{
namespace
{
std::atomic<StartMode> g_startMode{StartMode::Home};

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
        menu->Add("Zurueck");                     // 0
        menu->Add("Vorwaerts");                   // 1
        menu->Add("Neu laden");                   // 2
        menu->Add("Startseite");                  // 3
        menu->Add("Tastatur / URL eingeben");     // 4
        menu->Add(std::string("Startverhalten: ") + StartModeLabel()); // 5
        menu->Add("Verlassen");                   // 6

        menu->Open();
        const int selected = menu->GetSelectedItem();

        switch (selected)
        {
            case 0:
                return Action::Back;
            case 1:
                return Action::Forward;
            case 2:
                return Action::Reload;
            case 3:
                return Action::Home;
            case 4:
            {
                std::string url;
                // Kodi stellt die Tastatur inkl. Fernbedienungsbedienung bereit.
                if (CGUIKeyboardFactory::ShowAndGetInput(
                        url, CVariant{std::string("URL eingeben")}, false) &&
                    browser21url::Submit(url))
                {
                    return Action::UrlSubmitted;
                }
                return Action::None;
            }
            case 5:
                SetStartMode(GetStartMode() == StartMode::Home
                                 ? StartMode::LastPage
                                 : StartMode::Home);
                // Nach Umschalten das Menue mit aktualisiertem Text zeigen.
                continue;
            case 6:
                return Action::Exit;
            default:
                return Action::None; // Abbrechen
        }
    }
}

} // namespace browser21osd
