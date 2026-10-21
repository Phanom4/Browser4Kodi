#include "browser_k21_3_c150.h"

void browser_k21_3_c150_submit_frame(
    const void* data,
    unsigned int width,
    unsigned int height);


#include <cstring>
#include <limits>

void CBrowser_21_3::GetViewRect(
    CefRefPtr<CefBrowser> browser,
    CefRect& rect)
{
  std::lock_guard<std::mutex> lock(m_frameMutex);

  rect = CefRect(0, 0, m_width, m_height);
}

void CBrowser_21_3::OnPaint(
    CefRefPtr<CefBrowser> browser,
    PaintElementType type,
    const RectList& dirtyRects,
    const void* buffer,
    int width,
    int height)
{
    if (type != PET_VIEW || !buffer || width <= 0 || height <= 0)
        return;

    browser_k21_3_c150_submit_frame(
        buffer,
        static_cast<unsigned int>(width),
        static_cast<unsigned int>(height));
}

bool CBrowser_21_3::GetLatestFrame(
    std::vector<uint8_t>& frame,
    int& width,
    int& height)
{
  std::lock_guard<std::mutex> lock(m_frameMutex);

  if (!m_frameReady)
    return false;

  frame = m_frame;
  width = m_width;
  height = m_height;

  m_frameReady = false;
  return true;
}
