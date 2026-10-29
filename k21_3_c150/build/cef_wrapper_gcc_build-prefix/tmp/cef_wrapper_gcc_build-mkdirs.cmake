# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file LICENSE.rst or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

# If CMAKE_DISABLE_SOURCE_CHANGES is set to true and the source directory is an
# existing directory in our source tree, calling file(MAKE_DIRECTORY) on it
# would cause a fatal error, even though it would be a no-op.
if(NOT EXISTS "/run/media/kasia/Frank_10_25/make/Browser4Kodi/k21_3_c150/cef")
  file(MAKE_DIRECTORY "/run/media/kasia/Frank_10_25/make/Browser4Kodi/k21_3_c150/cef")
endif()
file(MAKE_DIRECTORY
  "/run/media/kasia/Frank_10_25/make/Browser4Kodi/k21_3_c150/build/cef-wrapper-gcc"
  "/run/media/kasia/Frank_10_25/make/Browser4Kodi/k21_3_c150/build/cef_wrapper_gcc_build-prefix"
  "/run/media/kasia/Frank_10_25/make/Browser4Kodi/k21_3_c150/build/cef_wrapper_gcc_build-prefix/tmp"
  "/run/media/kasia/Frank_10_25/make/Browser4Kodi/k21_3_c150/build/cef_wrapper_gcc_build-prefix/src/cef_wrapper_gcc_build-stamp"
  "/run/media/kasia/Frank_10_25/make/Browser4Kodi/k21_3_c150/build/cef_wrapper_gcc_build-prefix/src"
  "/run/media/kasia/Frank_10_25/make/Browser4Kodi/k21_3_c150/build/cef_wrapper_gcc_build-prefix/src/cef_wrapper_gcc_build-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/run/media/kasia/Frank_10_25/make/Browser4Kodi/k21_3_c150/build/cef_wrapper_gcc_build-prefix/src/cef_wrapper_gcc_build-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "/run/media/kasia/Frank_10_25/make/Browser4Kodi/k21_3_c150/build/cef_wrapper_gcc_build-prefix/src/cef_wrapper_gcc_build-stamp${cfgdir}") # cfgdir has leading slash
endif()
