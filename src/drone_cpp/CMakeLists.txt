cmake_minimum_required(VERSION 3.8)
project(drone_cpp)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(rclcpp_components)
find_package(std_msgs)
find_package(mf_utils)

# https://roboticsbackend.com/ros2-package-for-both-python-and-cpp-nodes/

# Define an executable target (cmake compiles and links the object files
# together into a target named according to first param)

add_executable(drone_node src/drone.cpp)
add_executable(drone_tf_publisher src/drone_tf_publisher.cpp)
add_executable(drone_controller src/drone_controller.cpp)
# Add necessary dependecies to the target (specified as first argument)
#https://docs.ros.org/en/foxy/How-To-Guides/Ament-CMake-Documentation.html#adding-dependencies
ament_target_dependencies(drone_tf_publisher rclcpp geometry_msgs tf2_ros nav_msgs tf2)
ament_target_dependencies(drone_controller rclcpp std_msgs tf2_ros nav2_msgs rclcpp_components tf2 mf_utils)


# This installs the target named drone_node to directory specified after DESTINATION
# the directory is a relative path relative to. From cmake docs:
# When a relative path is given, it is interpreted relative to the value of the CMAKE_INSTALL_PREFIX variable.
# (in ros2 case, the CMAKE_INSTALL_PREFIX is set by colcon)
install(TARGETS drone_node drone_tf_publisher drone_controller DESTINATION lib/${PROJECT_NAME})


# Install launch files.
install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}/
)

install(DIRECTORY
  models
  DESTINATION share/${PROJECT_NAME}/
)

install(DIRECTORY
  config
  DESTINATION share/${PROJECT_NAME})

# Used for installing programs not built with cmake (ie python nodes)
# install(PROGRAMS
#   scripts/drone.py
#   DESTINATION
#   lib/${PROJECT_NAME}
# )

# Installs the python modules from folder PROJECT_NAME into the install folder's
# site packages
ament_python_install_package(${PROJECT_NAME})


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
