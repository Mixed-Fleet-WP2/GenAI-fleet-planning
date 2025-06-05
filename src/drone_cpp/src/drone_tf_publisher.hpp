#ifndef DRONE_TF_PUBLISHER_HH
#define DRONE_TF_PUBLISHER_HH

#include <string>
#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "tf2_ros/transform_broadcaster.h"
#include <nav_msgs/msg/odometry.hpp>
#include "tf2/LinearMath/Quaternion.h"
#include "tf2/LinearMath/Matrix3x3.h"

//## From the ros2 docs:
//(https://docs.ros.org/en/jazzy/How-To-Guides/Ament-CMake-Documentation.html#adding-targets)

// https://docs.ros.org/en/humble/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Broadcaster-Cpp.html
class DroneTfPublisher : public rclcpp::Node {
    public:
        DroneTfPublisher(const std::string& node_name);

    private:
        // Could also be: std::shared_ptr<nav_msgs::msg::Odometry>
        // or nav_msgs::msg::Odometry::SharedPtr
        void publish_transform(const nav_msgs::msg::Odometry &msg);
        rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odometry_subscription_;
        std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
};

#endif