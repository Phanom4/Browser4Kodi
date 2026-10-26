#pragma once

#include "include/cef_browser.h"
#include "include/cef_client.h"
#include "include/cef_render_handler.h"

#include <cstdint>
#include <mutex>
#include <vector>

class CBrowser_21_3 final : public CefClient,
                           public CefRenderHandler
{
public:
  CBrowser_21_3() = default;

  CefRefPtr<CefRenderHandler> GetRenderHandler() override
  {
    return this;
  }

  void GetViewRect(
      CefRefPtr<CefBrowser> browser,
      CefRect& rect) override;

  void OnPaint(
      CefRefPtr<CefBrowser> browser,
      PaintElementType type,
      const RectList& dirtyRects,
      const void* buffer,
      int width,
      int height) override;

  bool GetLatestFrame(
      std::vector<uint8_t>& frame,
      int& width,
      int& height);

private:
  std::mutex m_frameMutex;

  std::vector<uint8_t> m_frame;

  int m_width = 1280;
  int m_height = 720;

  bool m_frameReady = false;

  IMPLEMENT_REFCOUNTING(CBrowser_21_3);
};
