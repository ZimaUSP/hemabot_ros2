# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_firmware_minihema_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED firmware_minihema_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(firmware_minihema_FOUND FALSE)
  elseif(NOT firmware_minihema_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(firmware_minihema_FOUND FALSE)
  endif()
  return()
endif()
set(_firmware_minihema_CONFIG_INCLUDED TRUE)

# output package information
if(NOT firmware_minihema_FIND_QUIETLY)
  message(STATUS "Found firmware_minihema: 0.0.0 (${firmware_minihema_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'firmware_minihema' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT ${firmware_minihema_DEPRECATED_QUIET})
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(firmware_minihema_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "ament_cmake_export_libraries-extras.cmake")
foreach(_extra ${_extras})
  include("${firmware_minihema_DIR}/${_extra}")
endforeach()
