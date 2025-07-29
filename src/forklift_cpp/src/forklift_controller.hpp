#ifndef FORKLIFT_CONTROLLER_HPP
#define FORKLIFT_CONTROLLER_HPP

#include <memory>
#include <chrono>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "tf2_ros/transform_broadcaster.h"
#include "tf2_ros/transform_listener.h"
#include "tf2_ros/buffer.h"
#include "std_msgs/msg/string.hpp"
#include "std_msgs/msg/float64.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "mf_utils/types.hpp"
#include "mf_utils/utils.hpp"
#include "mf_utils/json.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "mf_utils/navigatable.hpp"
#include "sensor_msgs/msg/joint_state.hpp"
#include "ros_gz_interfaces/srv/set_entity_pose.hpp"

class ForkliftController : public Navigatable {

    public:
        ForkliftController();

    private:

        rclcpp::TimerBase::SharedPtr lift_timer_;
        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr pick_up_subscription_;
        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr drop_subscription_;
        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr move_fork_subscription_;
        rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_state_subscription_;
        rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr fork_control_publisher_;
        rclcpp::Client<ros_gz_interfaces::srv::SetEntityPose>::SharedPtr object_pose_setter_client_;

        float current_fork_pos_;
        void move_fork_callback_(const std_msgs::msg::String::ConstSharedPtr msg);
        void drop_callback_(const std_msgs::msg::String::ConstSharedPtr msg);
        void pick_up_callback_(const std_msgs::msg::String::ConstSharedPtr msg);
        void joint_states_callback_(const sensor_msgs::msg::JointState::ConstSharedPtr joint_states);
        void move_fork(const JointPositionAction& action);
        void pick_up(const ObjectAction& action);
        void navigate_to_pose(const MoveAction& action) override;

};


#endif //FORKLIFT_CONTROLLER_HPP