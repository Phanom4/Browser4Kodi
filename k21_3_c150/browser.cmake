# browser - eigener Build, unabhängig vom Kodi-Hauptbuild

set(BROWSER_DIR "${CMAKE_CURRENT_LIST_DIR}")
set(CEF_ROOT "${BROWSER_DIR}/chromium/src/out/Release_GN_x64")
file(GLOB CEF_DISTRIBUTIONS
    "${BROWSER_DIR}/chromium/src/cef/binary_distrib/cef_binary_*_linux64"
)

list(LENGTH CEF_DISTRIBUTIONS CEF_COUNT)
if(NOT CEF_COUNT EQUAL 1)
    message(FATAL_ERROR "Genau eine CEF-Binary-Distribution erforderlich")
endif()
list(GET CEF_DISTRIBUTIONS 0 CEF_HEADER_ROOT)

# ============================================================
# GCC-CEF-Wrapper automatisch bauen (ein Build, keine Handarbeit)
# ============================================================
# CEF 150 wurde mit Chromium-Clang/libc++ gebaut. Der C++-Wrapper
# muss dagegen wie Browser4Kodi mit GCC/libstdc++ gebaut werden.
if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    message(FATAL_ERROR "Browser4Kodi mit GCC konfigurieren: CEF-Wrapper braucht dieselbe C++-ABI")
endif()

find_program(CEF_GCC_EXECUTABLE NAMES gcc REQUIRED)
include(ExternalProject)

# Der Wrapper wird im aktuellen Build-Verzeichnis erzeugt.
# Damit funktioniert auch ein vollständig leeres build/.
set(CEF_WRAPPER_BUILD_DIR "${CMAKE_BINARY_DIR}/cef-wrapper-gcc")
set(CEF_WRAPPER
    "${CEF_WRAPPER_BUILD_DIR}/libcef_dll_wrapper/libcef_dll_wrapper.a"
)
set(CEF_WRAPPER_JOBS 32 CACHE STRING "Parallele Jobs beim Bau des GCC-CEF-Wrappers")

ExternalProject_Add(cef_wrapper_gcc_build
    SOURCE_DIR "${CEF_HEADER_ROOT}"
    BINARY_DIR "${CEF_WRAPPER_BUILD_DIR}"
    CMAKE_GENERATOR "Ninja"
    DOWNLOAD_COMMAND ""
    UPDATE_COMMAND ""
    PATCH_COMMAND ""
    CMAKE_ARGS
        "-DCMAKE_C_COMPILER:FILEPATH=${CEF_GCC_EXECUTABLE}"
        "-DCMAKE_CXX_COMPILER:FILEPATH=${CMAKE_CXX_COMPILER}"
        "-DCMAKE_BUILD_TYPE:STRING=Release"
    BUILD_COMMAND
        "${CMAKE_COMMAND}" --build <BINARY_DIR>
        --target libcef_dll_wrapper --parallel "${CEF_WRAPPER_JOBS}"
    INSTALL_COMMAND ""
    BUILD_BYPRODUCTS "${CEF_WRAPPER}"
)

# Erst den Wrapper bauen, danach Browser und Helper linken.
add_library(cef_wrapper_gcc STATIC IMPORTED GLOBAL)
set_target_properties(cef_wrapper_gcc PROPERTIES
    IMPORTED_LOCATION "${CEF_WRAPPER}"
)
add_dependencies(cef_wrapper_gcc cef_wrapper_gcc_build)

add_library(browser SHARED
    "${BROWSER_DIR}/src/browser.cpp"
    "${BROWSER_DIR}/src/browser_frames.cpp"
    "${BROWSER_DIR}/src/browser_retro.cpp"
    "${BROWSER_DIR}/src/browser_entry.cpp"
    "${BROWSER_DIR}/src/browser_audio.cpp"
    "${BROWSER_DIR}/src/browser_url.cpp"
    "${BROWSER_DIR}/src/browser_osd.cpp"
)

target_compile_features(browser PRIVATE cxx_std_17)

target_compile_options(browser PRIVATE
    -fno-rtti
)

target_include_directories(browser PRIVATE
    "${BROWSER_DIR}/src"
    "${BROWSER_DIR}/Kodi-Header/xbmc"
    "${CEF_HEADER_ROOT}"
)

target_link_libraries(browser PRIVATE
    cef_wrapper_gcc
    "${CEF_ROOT}/libcef.so"
    pthread
    dl
    sqlite3
)


set_target_properties(browser PROPERTIES
    PREFIX ""
    OUTPUT_NAME "browser"
    BUILD_WITH_INSTALL_RPATH TRUE
    INSTALL_RPATH "$ORIGIN/../chromium/src/out/Release_GN_x64"
)


# CEF Chromium-Unterprozess

# ============================================================
# CEF Chromium-Unterprozess
# ============================================================

add_executable(browser_helper
    "${BROWSER_DIR}/src/browser_helper.cpp"
)

target_compile_features(browser_helper PRIVATE cxx_std_17)

target_compile_options(browser_helper PRIVATE
    -fno-rtti
)

target_include_directories(browser_helper PRIVATE
    "${CEF_HEADER_ROOT}"
)

target_link_libraries(browser_helper PRIVATE
    cef_wrapper_gcc
    "${CEF_ROOT}/libcef.so"
    pthread
    dl
    sqlite3
)

set_target_properties(browser_helper PROPERTIES
    BUILD_WITH_INSTALL_RPATH TRUE
    INSTALL_RPATH "$ORIGIN/../chromium/src/out/Release_GN_x64"
)

# CEF-BGRA direkt als Rawvideo-Stream für Kodi VideoPlayer
target_link_libraries(browser PRIVATE avformat avcodec avutil)

# CEF-Laufzeit bleibt innerhalb des Kodi-Prozesses bestehen.
target_link_options(browser PRIVATE "-Wl,-z,nodelete")

# Kodi-interne RetroPlayer-Header benötigen TARGET_POSIX
target_compile_definitions(browser PRIVATE TARGET_POSIX)

# Chromium LLD 23 für CEF-150-Objektdateien mit CREL
set(CEF_LLD_BIN
    "${BROWSER_DIR}/chromium/src/third_party/llvm-build/Release+Asserts/bin"
)

foreach(target browser browser_helper)
    target_link_options(${target} PRIVATE
        "-fuse-ld=lld"
        "-B${CEF_LLD_BIN}/"
    )
endforeach()

# ============================================================
