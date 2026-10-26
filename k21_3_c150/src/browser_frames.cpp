#include "browser_video.h"

#include <cstdint>
#include <limits>
#include <mutex>

namespace
{
std::mutex g_mutex;
BrowserVideoCallback g_callback = nullptr;
}

extern "C" void browser_set_video_callback(
    BrowserVideoCallback callback)
{
    std::lock_guard<std::mutex> lock(g_mutex);
    g_callback = callback;
}

void browser_submit_frame(
    const void* data,
    unsigned int width,
    unsigned int height)
{
    if (!data || !width || !height ||
        width > std::numeric_limits<unsigned int>::max() / 4)
        return;

    std::lock_guard<std::mutex> lock(g_mutex);

    if (g_callback)
        g_callback(
            static_cast<const uint8_t*>(data),
            width, height, width * 4);
}
