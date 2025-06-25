cmake_minimum_required(VERSION 3.8)
project(mf_utils VERSION 1.0)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()


# https://leimao.github.io/blog/CMake-Public-Private-Interface/
# "All the include directories following INTERFACE will NOT be used for
# the current target but will be accessible for the other targets
# that have dependencies on the current target"
add_library(mf_utils INTERFACE)

# This directive populates INTERFACE_INCLUDE_DIRECTORIES which is a list of include paths to header files
# https://cmake.org/cmake/help/latest/prop_tgt/INTERFACE_INCLUDE_DIRECTORIES.html#prop_tgt:INTERFACE_INCLUDE_DIRECTORIES
target_include_directories(mf_utils
  INTERFACE
    # Where to look for headers when building
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    # Where the users of the library should look for headers after install
    $<INSTALL_INTERFACE:include>
)

install(
  DIRECTORY include/
  DESTINATION include
)

# From CMAKE docs

#INCLUDES DESTINATION
 # This option specifies a list of directories which will be added to the
 # INTERFACE_INCLUDE_DIRECTORIES target property of the <targets>
 # when exported by the install(EXPORT) command.

 # Thus, the generator INSTALL_INTERFACE already 
 # does this and it is commented out here

install(
  TARGETS mf_utils
  # This option associates the installed target files with an export called <export-name>. 
  # It must appear before any target options. 
  # To actually install the export file itself, call install(EXPORT), documented below.
  # See documentation of the EXPORT_NAME target property to change the name of the exported target.
  
  # This refers to the export below, not the target
  EXPORT mf_utils
  INCLUDES DESTINATION include
)

# https://iamsorush.com/posts/cpp-cmake-config/
# https://stackoverflow.com/questions/49857596/simple-find-package-config-file-example

#The EXPORT form generates and installs a CMake file containing code
# to import targets from the installation tree into another project.

#  By default the generated file will be called <export-name>.cmake
# but the FILE option may be used to specify a different name.
install(EXPORT mf_utils
  FILE "mf_utilsConfig.cmake"
  DESTINATION share/${PROJECT_NAME}/cmake
)


# How ament does things behind the scenes:

# 1) https://github.com/ament/ament_cmake/blob/7f8f485aedd76548f6d4280f26289528fed7ef92/ament_cmake_export_targets/cmake/ament_export_targets.cmake#L45
# 2) https://github.com/ament/ament_cmake/blob/7f8f485aedd76548f6d4280f26289528fed7ef92/ament_cmake_export_targets/cmake/ament_cmake_export_targets_package_hook.cmake#L26
# 3) https://github.com/ament/ament_cmake/blob/7f8f485aedd76548f6d4280f26289528fed7ef92/ament_cmake_core/cmake/core/ament_package.cmake#L143