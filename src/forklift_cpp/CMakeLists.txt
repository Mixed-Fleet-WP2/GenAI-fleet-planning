cmake_minimum_required(VERSION 3.8)
project(forklift_cpp)

find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(mf_utils REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(ros_gz_interfaces REQUIRED)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

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

#https://docs.ros.org/en/foxy/How-To-Guides/Ament-CMake-Documentation.html
add_executable(forklift_controller src/forklift_controller.cpp)

ament_target_dependencies(forklift_controller rclcpp tf2_ros sensor_msgs mf_utils ros_gz_interfaces)

install(TARGETS 
  forklift_controller
  DESTINATION 
  lib/${PROJECT_NAME}
)

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

install(DIRECTORY
  urdf
  DESTINATION share/${PROJECT_NAME})

ament_package()
