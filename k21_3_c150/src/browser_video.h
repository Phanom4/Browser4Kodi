#pragma once

#include <cstdint>

using BrowserVideoCallback =
    void (*)(const uint8_t* bgra,
             unsigned int width,
             unsigned int height,
             unsigned int stride);

extern "C" void browser_set_video_callback(
    BrowserVideoCallback callback);
