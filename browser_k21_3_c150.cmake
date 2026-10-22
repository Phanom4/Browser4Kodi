# browser_k21_3_c150 - eigener Build, unabhängig vom Kodi-Hauptbuild

set(BROWSER_K21_3_C150_DIR "${CMAKE_CURRENT_LIST_DIR}")
set(CEF_ROOT "${BROWSER_K21_3_C150_DIR}/chromium/src/out/Release_GN_x64")
set(CEF_WRAPPER
    "${BROWSER_K21_3_C150_DIR}/build/cef-wrapper-gcc/libcef_dll_wrapper/libcef_dll_wrapper.a"
)

file(GLOB CEF_DISTRIBUTIONS
    "${BROWSER_K21_3_C150_DIR}/chromium/src/cef/binary_distrib/cef_binary_*_linux64"
)

list(LENGTH CEF_DISTRIBUTIONS CEF_COUNT)
if(NOT CEF_COUNT EQUAL 1)
    message(FATAL_ERROR "Genau eine CEF-Binary-Distribution erforderlich")
endif()
list(GET CEF_DISTRIBUTIONS 0 CEF_HEADER_ROOT)

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
    "${BROWSER_K21_3_C150_DIR}/Kodi-Header/xbmc"
    "${CEF_HEADER_ROOT}"
)

target_link_libraries(browser_k21_3_c150 PRIVATE
    "${CEF_WRAPPER}"
    "${CEF_ROOT}/libcef.so"
    pthread
    dl
)

set_target_properties(browser_k21_3_c150 PROPERTIES
    PREFIX ""
    OUTPUT_NAME "browser_k21_3_c150"
    BUILD_RPATH "\$ORIGIN/../chromium/src/out/Release_GN_x64"
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
    "${CEF_HEADER_ROOT}"
)

target_link_libraries(browser_k21_3_c150_helper PRIVATE
    "${CEF_WRAPPER}"
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

# Kodi-interne RetroPlayer-Header benötigen TARGET_POSIX
target_compile_definitions(browser_k21_3_c150 PRIVATE TARGET_POSIX)

# Chromium LLD 23 für CEF-150-Objektdateien mit CREL
set(CEF_LLD_BIN
    "${BROWSER_K21_3_C150_DIR}/chromium/src/third_party/llvm-build/Release+Asserts/bin"
)

foreach(target browser_k21_3_c150 browser_k21_3_c150_helper)
    target_link_options(${target} PRIVATE
        "-fuse-ld=lld"
        "-B${CEF_LLD_BIN}/"
    )
endforeach()


