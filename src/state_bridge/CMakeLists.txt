cmake_minimum_required(VERSION 3.8)
project(state_bridge)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

#https://stackoverflow.com/questions/15201064/cmake-conditional-preprocessor-define-on-code


# When changin this option, be sure to delete the build directory
# to ensure that the CMake cache is cleared and the option is re-evaluated.
# see: https://stackoverflow.com/questions/27015940/cmake-option-default-value
option(IS_COMPOSED "Define IS_COMPOSED to compile as a composable node" ON)

# https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-a-Composable-Node.html
if(IS_COMPOSED)
  message("Compiling as a composable node")
  add_definitions(-DIS_COMPOSED)
  find_package(rclcpp_components REQUIRED)
  # !!! THIS MUST BE A SHARED LIBRARY AS OPPOSED TO STATIC LIKE SPECIFIED IN THE TUTORIAL !!!
  # https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-a-Composable-Node.html#creating-the-composable-node-library
  add_library(state_bridge SHARED src/state_bridge.cpp)
  
  rclcpp_components_register_node(state_bridge
    PLUGIN "state_bridge::StateBridge"
    EXECUTABLE state_bridge_exec
  )

  ament_target_dependencies(state_bridge rclcpp_components)
else()
  # Do not define IS_COMPOSED
  add_executable(state_bridge src/state_bridge.cpp)
endif()


# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs)
find_package(tf2_msgs)
find_package(mf_utils)

ament_target_dependencies(state_bridge rclcpp geometry_msgs std_msgs tf2_msgs)

# Add non-ament utils
target_link_libraries(state_bridge mf_utils)

if (IS_COMPOSED)
  ament_export_targets(state_bridge)
  install(TARGETS state_bridge
        EXPORT state_bridge #This refers to the export above (with ament_export_targets)
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
        RUNTIME DESTINATION bin
  )
else()
  install(TARGETS 
    state_bridge
    DESTINATION lib/${PROJECT_NAME}
  )
endif()

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
