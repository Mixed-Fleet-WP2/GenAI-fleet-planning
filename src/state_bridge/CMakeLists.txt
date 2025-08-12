cmake_minimum_required(VERSION 3.8)
project(state_bridge)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# HOW TO MAKE A LIBRARY: https://docs.ros.org/en/foxy/How-To-Guides/Ament-CMake-Documentation.html
# HOW TO MAKE A COMPOSABLE NODE: https://docs.ros.org/en/humble/Tutorials/Intermediate/Writing-a-Composable-Node.html
# HOW NAV2 DOES IT: https://github.com/ros-navigation/navigation2/blob/e690ef0ed2391bbf93e856fe4a6cd4b371335318/nav2_amcl/src/amcl_node.cpp

# Find packages
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED) 
find_package(tf2_msgs REQUIRED)
find_package(mf_utils REQUIRED)
find_package(attach_interfaces REQUIRED)

add_library(state_bridge SHARED src/state_bridge.cpp)

target_include_directories(state_bridge PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(state_bridge
  rclcpp
  geometry_msgs
  std_msgs
  tf2_msgs
  mf_utils
  attach_interfaces
  rclcpp_components
)

# Register as composable component
rclcpp_components_register_node(
  state_bridge
  PLUGIN "state_bridge::StateBridge"
  EXECUTABLE state_bridge_component
)

# Create standalone executable
add_executable(state_bridge_exe src/main.cpp)

# Link the executable to the shared library
target_link_libraries(state_bridge_exe PRIVATE state_bridge)


# CANNOT BE USED BECAUSE OF CONFLIT OF PRIVATE AND NOT SPECIFIED
# Set dependencies for the standalone executable
# ament_target_dependencies(state_bridge_exe
#   rclcpp
# )

install(TARGETS state_bridge
  EXPORT state_bridge_targets #This becomes the name of the export
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(TARGETS state_bridge_exe
  DESTINATION lib/${PROJECT_NAME}
)

# Export targets and dependencies so users can find it
ament_export_targets(state_bridge_targets HAS_LIBRARY_TARGET) # <-- export name is used
ament_export_dependencies(
  rclcpp
  geometry_msgs
  std_msgs
  tf2_msgs
  mf_utils
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()