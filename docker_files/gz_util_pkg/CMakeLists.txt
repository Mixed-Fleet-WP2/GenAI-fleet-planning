cmake_minimum_required(VERSION 3.5)

project(gz_util_package)

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")
endif()

find_package(ament_cmake REQUIRED)
find_package(gz_math_vendor REQUIRED)
find_package(gz-math REQUIRED)
find_package(gz_msgs_vendor REQUIRED)
find_package(gz-msgs REQUIRED)
find_package(gz_transport_vendor REQUIRED)
find_package(gz-transport REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rcpputils REQUIRED)
find_package(std_msgs REQUIRED)

# From gz_cmake_vendor
gz_find_package(gflags REQUIRED PKGCONFIG gflags)

# Install the python module for this package
ament_python_install_package(${PROJECT_NAME})

# create
add_executable(create src/create.cpp)
target_link_libraries(create
  gflags
  gz-math::core
  gz-msgs::core
  gz-transport::core
  rclcpp::rclcpp
  rcpputils::rcpputils
  ${std_msgs_TARGETS}
)

# Install targets
install(TARGETS
    create
  DESTINATION
    lib/${PROJECT_NAME})

# Tests
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_gtest REQUIRED)
  find_package(launch_testing_ament_cmake REQUIRED)
  ament_find_gtest()

  ament_add_gtest_executable(test_create test/test_create.cpp)
  target_link_libraries(test_create gz-transport::core)

  install(TARGETS
      test_create
    DESTINATION
      lib/${PROJECT_NAME})

  add_launch_test(test/test_create_node.launch.py TIMEOUT 200)
endif()

ament_package()