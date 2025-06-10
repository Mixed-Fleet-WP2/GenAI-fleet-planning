#ifndef DRONE_CONTROLLER.HH
#define DRONE_CONTROLLER.HH

#include <chrono>
#include <functional>
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "tf2_ros/transform_broadcaster.h"
#include "std_msgs/msg/string.hpp"
#include "json.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"


using json = nlohmann::json;

using TwistMsg = geometry_msgs::msg::Twist;
using NavToPoseAction = nav2_msgs::action::NavigateToPose;

class DroneController:rclcpp::Node{

    public:
        DroneController(const std::string &node_name);
        ~DroneController();
    private:
        
    rclcpp_action::Client<NavToPoseAction>::SharedPtr nav_to_pose_client_;
    rclcpp::CallbackGroup::SharedPtr callback_group_;
    rclcpp::executors::SingleThreadedExecutor callback_group_executor_;

        struct Position{
            float x;
            float y;
            float z;
            float angular_x;
            float angular_y;
            float angular_z;
        };

        void navigate_to_pose(const Position &pos);
        rclcpp::Subscription<TwistMsg>::SharedPtr move_to_pose_subscriber_;
        std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
        void move_to_pose_callback(const std::shared_ptr<std_msgs::msg::String> msg);
};


#endif