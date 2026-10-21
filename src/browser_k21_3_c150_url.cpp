#include "browser_k21_3_c150_url.h"

#include <mutex>
#include <string>
#include <utility>

namespace browser21url
{
namespace
{
std::mutex g_urlMutex;
std::string g_pendingUrl;
bool g_hasPendingUrl = false;
}

bool Submit(const std::string& url)
{
    // Keine feste Beschraenkung auf http(s): Spaetere Quellen duerfen
    // auch andere von CEF unterstuetzte URL-Schemata liefern.
    if (url.find_first_not_of(" \t\r\n") == std::string::npos)
        return false;

    std::lock_guard<std::mutex> lock(g_urlMutex);
    g_pendingUrl = url;
    g_hasPendingUrl = true;
    return true;
}

void SubmitDefault()
{
    Submit(DEFAULT_URL);
}

bool TakePending(std::string& url)
{
    std::lock_guard<std::mutex> lock(g_urlMutex);
    if (!g_hasPendingUrl)
        return false;

    url = std::move(g_pendingUrl);
    g_pendingUrl.clear();
    g_hasPendingUrl = false;
    return true;
}

bool HasPending()
{
    std::lock_guard<std::mutex> lock(g_urlMutex);
    return g_hasPendingUrl;
}

} // namespace browser21url
