#include "ServiceBroker.h"
#include "games/GameServices.h"
#include "cores/RetroPlayer/guibridge/GUIGameRenderManager.h"
#include "cores/RetroPlayer/streams/RetroPlayerVideo.h"
#include "cores/RetroPlayer/streams/RetroPlayerAudio.h"

#include <memory>
#include <mutex>
#include <libavutil/pixfmt.h>
#include <cstdint>
#include <cstring>

using namespace KODI::RETRO;

extern "C" bool browser_retro_open(
    CRetroPlayerVideo* video,
    unsigned int width,
    unsigned int height)
{
    if (!video)
        return false;

    VideoStreamProperties properties(
        AV_PIX_FMT_0RGB32,
        width, height,
        width, height,
        1.0f
    );

    return video->OpenStream(properties);
}

extern "C" bool browser_retro_frame(
    CRetroPlayerVideo* video,
    const uint8_t* bgra,
    unsigned int width,
    unsigned int height)
{
    if (!video || !bgra || !width || !height)
        return false;

    VideoStreamBuffer buffer;

    if (!video->GetStreamBuffer(width, height, buffer))
        return false;

    const size_t bytes =
        static_cast<size_t>(width) * height * 4;

    if (!buffer.data || buffer.size < bytes)
        return false;

    std::memcpy(buffer.data, bgra, bytes);

    VideoStreamPacket packet(
        width,
        height,
        static_cast<VideoRotation>(0),
        buffer.data,
        bytes
    );

    video->AddStreamData(packet);

    return true;
}

// Direkter RetroPlayer-Laufzeittest
#include "threads/CriticalSection.h"
#include "cores/RetroPlayer/process/RPProcessInfo.h"
#include "cores/RetroPlayer/rendering/RPRenderManager.h"

#include <cstdio>
#include <atomic>
#include <vector>
#include "browser_video.h"
#include "browser_input.h"


namespace
{
std::atomic<KODI::RETRO::CRetroPlayerVideo*> g_retro_video{nullptr};
std::atomic<unsigned int> g_retro_frames{0};
std::atomic<bool> g_retro_gui_active{false};
std::atomic<bool> g_retro_audio_active{false};
bool g_retro_stream_open = false;

std::mutex g_retro_audio_mutex;
std::unique_ptr<KODI::RETRO::CRetroPlayerAudio> g_retro_audio;
unsigned int g_retro_audio_rate = 0;
unsigned int g_retro_audio_channels = 0;

KODI::RETRO::CRPProcessInfo* g_retro_process = nullptr;
KODI::RETRO::CRPRenderManager* g_retro_renderer = nullptr;

void RetroCefFrame(const uint8_t* bgra,
                   unsigned int width,
                   unsigned int height,
                   unsigned int stride)
{
    using namespace KODI::RETRO;

    if (!g_retro_gui_active.load())
        return;

    auto* video = g_retro_video.load();

    if (!video || !bgra || !width || !height ||
        width > UINT32_MAX / 4 ||
        stride < width * 4)
        return;

    const uint8_t* data = bgra;
    std::vector<uint8_t> packed;

    const size_t rowBytes = size_t(width) * 4;
    const size_t bytes = rowBytes * height;

    if (stride != rowBytes)
    {
        packed.resize(bytes);

        for (unsigned int y = 0; y < height; ++y)
        {
            std::memcpy(
                packed.data() + size_t(y) * rowBytes,
                bgra + size_t(y) * stride,
                rowBytes
            );
        }

        data = packed.data();
    }

    VideoStreamPacket packet(
        width,
        height,
        static_cast<VideoRotation>(0),
        data,
        bytes
    );

    video->AddStreamData(packet);

    const unsigned int count = ++g_retro_frames;

    if (count == 1 || count == 100)
    {
        std::fprintf(stderr,
                     "RETRO CEF: Frame %u, %ux%u, stride=%u\n",
                     count, width, height, stride);
        std::fflush(stderr);
    }
}
}

extern "C" int browser_retro_probe()
{
    using namespace KODI::RETRO;

    auto& process = g_retro_process;
    auto& renderer = g_retro_renderer;
    auto* video = g_retro_video.load();

    std::fprintf(stderr, "RETRO PROBE: BEGIN\n");
    std::fflush(stderr);

    try
    {
        if (!process)
        {
            auto instance = CRPProcessInfo::CreateInstance();

            if (!instance)
                return -1;

            process = instance.release();
        }

        std::fprintf(stderr, "RETRO PROBE: ProcessInfo OK\n");
        std::fflush(stderr);

        if (!renderer)
        {
            renderer = new CRPRenderManager(*process);
            renderer->Initialize();
        }

        std::fprintf(stderr, "RETRO PROBE: RenderManager OK\n");
        std::fflush(stderr);

        if (!video)
            video = new CRetroPlayerVideo(*renderer, *process);

        std::fprintf(stderr, "RETRO PROBE: Videoobjekt OK\n");
        std::fflush(stderr);

        VideoStreamProperties properties(
            AV_PIX_FMT_0RGB32,
            1280, 720,
            1280, 720,
            1.0f
        );

        bool result = g_retro_stream_open;

        if (!result)
        {
            result = video->OpenStream(properties);

            if (result)
                g_retro_stream_open = true;
        }

        if (result)
            g_retro_video.store(video);

        std::fprintf(stderr,
                     "RETRO PROBE: OpenStream = %d\n",
                     result ? 1 : 0);
        std::fflush(stderr);

        return result ? 1 : 0;
    }
    catch (...)
    {
        std::fprintf(stderr, "RETRO PROBE: Exception\n");
        std::fflush(stderr);
        return -2;
    }
}

extern "C" unsigned int browser_retro_frame_count()
{
    return g_retro_frames.load();
}

extern "C" int browser_retro_render_step()
{
    if (!g_retro_renderer || !g_retro_gui_active.load())
        return 0;

    g_retro_renderer->FrameMove();
    return 1;

}
extern "C" void browser_retro_audio_start();

extern "C" int browser_retro_gui_register()
{
    if (!g_retro_renderer || !g_retro_video.load())
        return 0;

    CServiceBroker::GetGameServices()
        .GameRenderManager()
        .RegisterPlayer(
            g_retro_renderer->GetGUIRenderTargetFactory(),
            g_retro_renderer,
            nullptr
        );

    browser_set_video_callback(&RetroCefFrame);
    g_retro_gui_active.store(true);
    browser21input::Register();
    
    browser_retro_audio_start();

    return 1;
}
extern "C" void browser_retro_audio_stop();
extern "C" void browser_retro_gui_unregister()
{
    browser21input::Unregister();
    g_retro_gui_active.store(false);
    browser_set_video_callback(nullptr);

    browser_retro_audio_stop();

    CServiceBroker::GetGameServices()
        .GameRenderManager()
        .UnregisterPlayer();
}

extern "C" void browser_retro_audio_packet(
    const uint8_t* data,
    size_t bytes,
    unsigned int sampleRate,
    unsigned int channels)
{
    using namespace KODI::RETRO;

    if (!data || !bytes || !sampleRate ||
        (channels != 1 && channels != 2))
        return;

    std::lock_guard<std::mutex> lock(g_retro_audio_mutex);

    if (!g_retro_gui_active.load() || !g_retro_process)
        return;

    if (g_retro_audio &&
        (g_retro_audio_rate != sampleRate ||
         g_retro_audio_channels != channels))
    {
        g_retro_audio->CloseStream();
        g_retro_audio.reset();
    }

    if (!g_retro_audio)
    {
        AudioChannelMap channelMap{};
        channelMap[0] = AudioChannel::CH_FL;

        if (channels == 2)
            channelMap[1] = AudioChannel::CH_FR;

        auto audio = std::make_unique<CRetroPlayerAudio>(
            *g_retro_process);

        AudioStreamProperties properties(
            PCMFormat::FMT_S16NE,
            static_cast<double>(sampleRate),
            channelMap
        );

        if (!audio->OpenStream(properties))
            return;

        g_retro_audio_rate = sampleRate;
        g_retro_audio_channels = channels;
        g_retro_audio = std::move(audio);
    }

    AudioStreamPacket packet(data, bytes);
    g_retro_audio->AddStreamData(packet);
}

extern "C" void browser_retro_audio_start()
{
    std::lock_guard<std::mutex> lock(g_retro_audio_mutex);

    if (!g_retro_process)
    {
        auto instance =
            KODI::RETRO::CRPProcessInfo::CreateInstance();

        if (!instance)
        {
            std::fprintf(stderr,
                         "RETRO AUDIO: ProcessInfo failed\n");
            return;
        }

        g_retro_process = instance.release();
    }

    g_retro_audio_active.store(true);
}

extern "C" void browser_retro_audio_stop()
{
    std::lock_guard<std::mutex> lock(g_retro_audio_mutex);


    if (g_retro_audio)
    {
        g_retro_audio->CloseStream();
        g_retro_audio.reset();
    }

    g_retro_audio_rate = 0;
    g_retro_audio_channels = 0;
}
