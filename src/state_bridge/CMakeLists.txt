cmake_minimum_required(VERSION 3.8)
project(state_bridge)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# https://stackoverflow.com/questions/29688115/how-do-i-check-if-an-environment-variable-is-set-in-cmake
if (NOT DEFINED ENV{UTILS_DIR})
  # https://stackoverflow.com/questions/7035734/how-do-i-get-the-parent-directory-path-of-a-path-in-cmake

  # Get the path of the current project i.e. where
  # this CMakeLists resides. Then get its parent directory
  # and store in WS_SRC. This is the src directory of the whole ROS2 workspace
  cmake_path(GET CMAKE_SOURCE_DIR PARENT_PATH WS_SRC)
  # Append utils directory to the workspace source directory
  # and this becomes the final directory
  cmake_path(APPEND_STRING WS_SRC "/utils" OUTPUT_VARIABLE UTILS_DIR)
  message("DEFININING")
else()
  message("ALREADY DEFINED")
endif()


# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs)
find_package(tf2_msgs)
# Required for utils to work, in the future, utils should be made to proper library to make
# it so the inclusion is not required here
find_package(tf2)

add_executable(state_bridge src/state_bridge.cpp)

ament_target_dependencies(state_bridge rclcpp geometry_msgs std_msgs tf2_msgs tf2)
target_include_directories(state_bridge PUBLIC ${UTILS_DIR})


install(DIRECTORY
  launch config
  DESTINATION share/${PROJECT_NAME}
)


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

ament_package()
