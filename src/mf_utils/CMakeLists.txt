cmake_minimum_required(VERSION 3.8)
project(mf_utils)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(tf2 REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

add_library(mf_utils INTERFACE)

# This directive populates INTERFACE_INCLUDE_DIRECTORIES which is a list of include directory requirements
# https://cmake.org/cmake/help/latest/prop_tgt/INTERFACE_INCLUDE_DIRECTORIES.html#prop_tgt:INTERFACE_INCLUDE_DIRECTORIES
target_include_directories(mf_utils
  INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    # Where the users of the library should look for headers after install
    $<INSTALL_INTERFACE:include>
)


ament_target_dependencies(mf_utils INTERFACE tf2)

ament_export_targets(mf_utils HAS_LIBRARY_TARGET)
ament_export_dependencies(tf2)

install(
  DIRECTORY include/
  DESTINATION include
)

# From CMAKE docs

#INCLUDES DESTINATION
 # This option specifies a list of directories which will be added to the
 # INTERFACE_INCLUDE_DIRECTORIES target property of the <targets>
 # when exported by the install(EXPORT) command.

 #Thus, the generator INSTALL_INTERFACE already 
 # does this and it is commented out here

install(
  TARGETS mf_utils
  EXPORT mf_utils
  # From Cmake docs: 
  #INCLUDES DESTINATION include
)

ament_package()
