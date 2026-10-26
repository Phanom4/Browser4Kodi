#pragma once

#include <string>

// Zentrale URL-Uebergabe fuer browser.
// Alle Quellen (Browser-Menue, Kodi-Dialog, spaeter HbbTV) nutzen diese Schnittstelle.
// Kein Kodi-/CEF-Code: Die URL wird erst auf dem CEF-UI-Thread geladen.
namespace browser21url
{

// Nur fuer den normalen Start ueber den Browser-Menueeintrag.
constexpr const char* DEFAULT_URL = "https://kodi.tv/";

// Merkt die neueste URL. Eine bereits wartende URL wird ersetzt.
// Liefert false bei leerer URL oder nur Leerzeichen.
bool Submit(const std::string& url);

// Setzt die Standard-URL, aber nur wenn der Aufrufer dies explizit verlangt.
void SubmitDefault();

// Nur aufrufen, NACHDEM CEF und der Browser zur Navigation bereit sind.
// Liefert true und entfernt dann die wartende URL aus dem Zwischenspeicher.
// Bei false bleibt 'url' unveraendert.
bool TakePending(std::string& url);

// Zeigt an, ob aktuell eine URL auf die Uebergabe wartet.
bool HasPending();

} // namespace browser21url
