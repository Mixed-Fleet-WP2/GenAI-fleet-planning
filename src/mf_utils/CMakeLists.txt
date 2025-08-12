cmake_minimum_required(VERSION 3.8)
project(mf_utils VERSION 1.0)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(geometry_msgs REQUIRED)

add_library(mf_utils SHARED src/navigatable.cpp)

ament_target_dependencies(mf_utils rclcpp nav2_msgs rclcpp_action geometry_msgs tf2_ros)

# Make header files findable for both user of this target as well as the target itself
# https://leimao.github.io/blog/CMake-Public-Private-Interface/
target_include_directories(mf_utils
  PUBLIC
    # Where to look for headers when building
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    # Where the users of the library should look for headers after install
    $<INSTALL_INTERFACE:include>
)

ament_export_targets(export_mf_utils HAS_LIBRARY_TARGET)
ament_export_dependencies(
    rclcpp 
    rclcpp_action
    nav2_msgs
    tf2_ros
    geometry_msgs)

# Install header files
install(DIRECTORY include/
        DESTINATION include)

install(
    TARGETS ${PROJECT_NAME}
    EXPORT export_${PROJECT_NAME}
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    INCLUDES DESTINATION include
)

# The argument to ament_python_install_package() 
# is the name of the directory alongside the CMakeLists.txt that contains the Python file. 
# See: https://docs.ros.org/en/foxy/How-To-Guides/Ament-CMake-Python-Documentation.html
ament_python_install_package(${PROJECT_NAME})

ament_package()