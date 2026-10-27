#pragma once
#include <string>

// Browser 21.3 - eigenes Kodi-Browsermenue.
// Das Menue verwendet Kodi DialogSelect und die vorhandene Kodi-Tastatur.
// Es steuert CEF nicht selbst: Der Aufrufer erhaelt die ausgewaehlte Aktion.

namespace browser21osd
{

enum class Action
{
    None,          // Abbrechen / Dialog konnte nicht geoeffnet werden
    Back,          // Zurueck
    Forward,       // Vorwaerts
    Reload,        // Neu laden
    Home,          // Startseite https://kodi.tv/
    UrlSubmitted,   // URL aus Kodi-Tastatur an browser21url uebergeben
    Exit             // Browser verlassen
};



enum class StartMode
{
    Home,          // Bei normalem Browserstart Startseite laden
    LastPage       // Bei normalem Browserstart aktuelle Seite behalten
};

// Kodi-Menue anzeigen. Nur vom Kodi-GUI-Thread aufrufen.
// Die Auswahl wird als Action zurueckgegeben und spaeter zentral ausgefuehrt.
// Bei "Tastatur" wird die URL schon an browser21url::Submit() uebergeben.
Action Show();

std::string GetHomepage();

// Startverhalten nur waehrend der laufenden Kodi-Sitzung merken.
// Ein spaeterer Anschluss an den Browserstart wertet diesen Schalter aus.
StartMode GetStartMode();
void SetStartMode(StartMode mode);

} // namespace browser21osd
