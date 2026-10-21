# browser_k21_3_c150 - eigener Build, unabhängig vom Kodi-Hauptbuild

set(BROWSER_K21_3_C150_DIR "${CMAKE_CURRENT_LIST_DIR}")
set(CEF_ROOT "${BROWSER_K21_3_C150_DIR}/cef")

add_library(browser_k21_3_c150 SHARED
    "${BROWSER_K21_3_C150_DIR}/src/browser_k21_3_c150.cpp"
    "${BROWSER_K21_3_C150_DIR}/src/browser_k21_3_c150_frames.cpp"
    "${BROWSER_K21_3_C150_DIR}/src/browser_k21_3_c150_retro.cpp"
    "${BROWSER_K21_3_C150_DIR}/src/browser_k21_3_c150_entry.cpp"
    "${BROWSER_K21_3_C150_DIR}/src/browser_k21_3_c150_audio.cpp"
    "${BROWSER_K21_3_C150_DIR}/src/browser_k21_3_c150_url.cpp"
    "${BROWSER_K21_3_C150_DIR}/src/browser_k21_3_c150_osd.cpp"
)

target_compile_features(browser_k21_3_c150 PRIVATE cxx_std_17)

target_compile_options(browser_k21_3_c150 PRIVATE
    -fno-rtti
)

target_include_directories(browser_k21_3_c150 PRIVATE
    "${BROWSER_K21_3_C150_DIR}/src"
    "${BROWSER_K21_3_C150_DIR}/../xbmc-Omega-git/xbmc"
    "${BROWSER_K21_3_C150_DIR}/CEF-Header"
)

target_link_libraries(browser_k21_3_c150 PRIVATE
    "${CEF_ROOT}/libcef_dll_wrapper.a"
    "${CEF_ROOT}/libcef.so"
    pthread
    dl
)

set_target_properties(browser_k21_3_c150 PROPERTIES
    PREFIX ""
    OUTPUT_NAME "browser_k21_3_c150"
    BUILD_RPATH "\$ORIGIN/../cef"
)

# CEF Chromium-Unterprozess
add_executable(browser_k21_3_c150_helper
    "${BROWSER_K21_3_C150_DIR}/src/browser_k21_3_c150_helper.cpp"
)

target_compile_features(browser_k21_3_c150_helper PRIVATE cxx_std_17)

target_compile_options(browser_k21_3_c150_helper PRIVATE
    -fno-rtti
)

target_include_directories(browser_k21_3_c150_helper PRIVATE
    "${BROWSER_K21_3_C150_DIR}/CEF-Header"
)

target_link_libraries(browser_k21_3_c150_helper PRIVATE
    "${CEF_ROOT}/libcef_dll_wrapper.a"
    "${CEF_ROOT}/libcef.so"
    pthread
    dl
)

set_target_properties(browser_k21_3_c150_helper PROPERTIES
    BUILD_RPATH "${CEF_ROOT}"
)

# CEF-BGRA direkt als Rawvideo-Stream für Kodi VideoPlayer
target_link_libraries(browser_k21_3_c150 PRIVATE avformat avcodec avutil)

# CEF-Laufzeit bleibt innerhalb des Kodi-Prozesses bestehen.
target_link_options(browser_k21_3_c150 PRIVATE "-Wl,-z,nodelete")

# Eigenständiger CEF-Browser mit Chromium Views
# Unabhängig von Kodi, OSR und NUT.
add_executable(browser_k21_3_c150_standalone
    "${BROWSER_K21_3_C150_DIR}/src/browser_k21_3_c150_standalone.cpp"
)

target_compile_features(browser_k21_3_c150_standalone PRIVATE cxx_std_17)

target_compile_options(browser_k21_3_c150_standalone PRIVATE -fno-rtti)

target_include_directories(browser_k21_3_c150_standalone PRIVATE
    "${BROWSER_K21_3_C150_DIR}/CEF-Header"
)

target_link_libraries(browser_k21_3_c150_standalone PRIVATE
    "${CEF_ROOT}/libcef_dll_wrapper.a"
    "${CEF_ROOT}/libcef.so"
    pthread
    dl
)

set_target_properties(browser_k21_3_c150_standalone PROPERTIES
    BUILD_RPATH "${CEF_ROOT}"
)

# Kodi-interne RetroPlayer-Header benötigen TARGET_POSIX
target_compile_definitions(browser_k21_3_c150 PRIVATE TARGET_POSIX)
