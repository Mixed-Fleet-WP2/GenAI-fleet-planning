#ifndef FORKLIFT_CONTROLLER_HPP
#define FORKLIFT_CONTROLLER_HPP

#include <memory>
#include <chrono>
#include <filesystem>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "tf2_ros/transform_broadcaster.h"
#include "tf2_ros/transform_listener.h"
#include "tf2_ros/buffer.h"
#include "std_msgs/msg/string.hpp"
#include "std_msgs/msg/float64.hpp"
#include "std_msgs/msg/empty.hpp"
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
#include "ros_gz_interfaces/srv/spawn_entity.hpp"
#include "ros_gz_interfaces/srv/delete_entity.hpp"
#include "attach_interfaces/srv/change_attach.hpp"

class ForkliftController : public Navigatable {

    public:
        ForkliftController();

    private:

        /** PRIMITIVES */
        void move_fork(const JointPositionAction& action);
        void pick_up(const ObjectAction& action);
        void drop(const ObjectAction& action);
        void navigate_to_pose(const MoveAction& action) override;

        rclcpp::TimerBase::SharedPtr lift_timer_;
        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr pick_up_subscription_;
        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr drop_subscription_;
        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr move_fork_subscription_;
        rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_state_subscription_;
        rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr fork_control_publisher_;
        rclcpp::Client<ros_gz_interfaces::srv::SetEntityPose>::SharedPtr object_pose_setter_client_;
        rclcpp::Client<ros_gz_interfaces::srv::DeleteEntity>::SharedPtr entity_delete_client_;
        rclcpp::Client<ros_gz_interfaces::srv::SpawnEntity>::SharedPtr entity_spawn_client_ ;
        rclcpp::Subscription<tf2_msgs::msg::TFMessage>::SharedPtr ground_truth_tf_subscription_;
        rclcpp::Client<attach_interfaces::srv::ChangeAttach>::SharedPtr object_attach_client_;

        float current_fork_pos_;
        void move_fork_callback_(const std_msgs::msg::String::ConstSharedPtr msg);
        void drop_callback_(const std_msgs::msg::String::ConstSharedPtr msg);
        void pick_up_callback_(const std_msgs::msg::String::ConstSharedPtr msg);
        void joint_states_callback_(const sensor_msgs::msg::JointState::ConstSharedPtr joint_states);
        
        std::unordered_map<std::string, bool> pallet_statues_;
        std::vector<rclcpp::Subscription<std_msgs::msg::String>::SharedPtr> pallet_subscriptions_;
        bool move_object_relative_to_fork(const std::string object, float offset_x = 0.0, float offset_y = 0.0, float offset_z = 0.0);
        geometry_msgs::msg::Vector3 forklift_location_;
        geometry_msgs::msg::Quaternion forklift_orientation_;

};


#endif //FORKLIFT_CONTROLLER_HPP