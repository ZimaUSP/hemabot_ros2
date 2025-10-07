# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_minihema_launch_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED minihema_launch_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(minihema_launch_FOUND FALSE)
  elseif(NOT minihema_launch_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(minihema_launch_FOUND FALSE)
  endif()
  return()
endif()
set(_minihema_launch_CONFIG_INCLUDED TRUE)

# output package information
if(NOT minihema_launch_FIND_QUIETLY)
  message(STATUS "Found minihema_launch: 0.0.0 (${minihema_launch_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'minihema_launch' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT ${minihema_launch_DEPRECATED_QUIET})
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(minihema_launch_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "ament_cmake_export_libraries-extras.cmake")
foreach(_extra ${_extras})
  include("${minihema_launch_DIR}/${_extra}")
endforeach()
