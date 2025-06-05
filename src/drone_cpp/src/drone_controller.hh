#ifndef DRONE_CONTROLLER.HH
#define DRONE_CONTROLLER.HH

#include <chrono>
#include <functional>
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "tf2_ros/transform_broadcaster.h"

using TwistMsg = geometry_msgs::msg::Twist;

class DroneController:rclcpp::Node{

    public:
        DroneController(std::string node_name);
    private:
        void publish_cmd_vel_msg(const TwistMsg::SharedPtr msg);
        rclcpp::Subscription<TwistMsg>::SharedPtr cmd_vel_subscriber;
        std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;

};


#endif