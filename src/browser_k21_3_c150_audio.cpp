
#include "include/cef_audio_handler.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <vector>

extern "C" void browser_k21_3_c150_retro_audio_packet(
    const uint8_t* data,
    size_t bytes,
    unsigned int sampleRate,
    unsigned int channels);

extern "C" void browser_k21_3_c150_retro_audio_stop();

namespace
{
class BrowserAudio final : public CefAudioHandler
{
public:
    bool GetAudioParameters(
        CefRefPtr<CefBrowser> browser,
        CefAudioParameters& params) override
    {
        return true;
    }

    void OnAudioStreamStarted(
        CefRefPtr<CefBrowser> browser,
        const CefAudioParameters& params,
        int channels) override
    {
        std::lock_guard<std::mutex> lock(m_mutex);

        browser_k21_3_c150_retro_audio_stop();

        m_channels = 0;
        m_sampleRate = 0;

        if (channels != 1 && channels != 2 ||
            params.sample_rate <= 0)
        {
            std::cerr
                << "browser_k21_3_c150[AUDIO]: Unsupported format\n";
            return;
        }

        m_channels = channels;
        m_sampleRate = params.sample_rate;

        std::cerr
            << "browser_k21_3_c150[AUDIO]: CEF started "
            << m_sampleRate << " Hz / "
            << m_channels << " channels\n";
    }

    void OnAudioStreamPacket(
        CefRefPtr<CefBrowser> browser,
        const float** data,
        int frames,
        int64_t pts) override
    {
        if (!data || frames <= 0)
            return;

        std::lock_guard<std::mutex> lock(m_mutex);

        if (!m_channels || !m_sampleRate)
            return;

        for (int channel = 0; channel < m_channels; ++channel)
        {
            if (!data[channel])
                return;
        }

        std::vector<int16_t> pcm(
            static_cast<size_t>(frames) * m_channels
        );

        for (int frame = 0; frame < frames; ++frame)
        {
            for (int channel = 0;
                 channel < m_channels;
                 ++channel)
            {
                const float sample = data[channel][frame];

                const float limited =
                    std::isfinite(sample)
                        ? std::clamp(sample, -1.0f, 1.0f)
                        : 0.0f;

                pcm[static_cast<size_t>(frame) *
                    m_channels + channel] =
                    static_cast<int16_t>(
                        std::lrint(
                            limited * (limited < 0.0f
                                ? 32768.0f
                                : 32767.0f)
                        )
                    );
            }
        }

        browser_k21_3_c150_retro_audio_packet(
            reinterpret_cast<const uint8_t*>(pcm.data()),
            pcm.size() * sizeof(int16_t),
            static_cast<unsigned int>(m_sampleRate),
            static_cast<unsigned int>(m_channels)
        );
    }

    void OnAudioStreamStopped(
        CefRefPtr<CefBrowser> browser) override
    {
        std::lock_guard<std::mutex> lock(m_mutex);

        m_channels = 0;
        m_sampleRate = 0;

        browser_k21_3_c150_retro_audio_stop();

        std::cerr
            << "browser_k21_3_c150[AUDIO]: Stopped\n";
    }

    void OnAudioStreamError(
        CefRefPtr<CefBrowser> browser,
        const CefString& message) override
    {
        std::cerr
            << "browser_k21_3_c150[AUDIO]: CEF error: "
            << message.ToString() << '\n';
    }

private:
    std::mutex m_mutex;
    int m_channels = 0;
    int m_sampleRate = 0;

    IMPLEMENT_REFCOUNTING(BrowserAudio);
};
} // namespace

CefRefPtr<CefAudioHandler>
browser_k21_3_c150_create_audio_handler()
{
    return new BrowserAudio;
}

