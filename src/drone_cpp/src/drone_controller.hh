#ifndef DRONE_CONTROLLER_HH
#define DRONE_CONTROLLER_HH

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <future>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "tf2_ros/transform_broadcaster.h"
#include "std_msgs/msg/string.hpp"
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


using json = nlohmann::json;

using TwistMsg = geometry_msgs::msg::Twist;
using PoseStampedMsg = geometry_msgs::msg::PoseStamped;
using NavToPoseAction = nav2_msgs::action::NavigateToPose;
using NavToPoseGoalHandle = rclcpp_action::ClientGoalHandle<NavToPoseAction>;
using OdomMsg = nav_msgs::msg::Odometry;


class DroneController: public rclcpp::Node{

    public:
        DroneController();
        //Needed to resolve compatibility error with the base destructor
        // needs to be taken care of some other way in the future??
        ~DroneController() noexcept;
    private:
        
        std::string node_name_ = "";

        

        rclcpp_action::Client<NavToPoseAction>::SharedPtr nav_to_pose_client_;
        rclcpp::CallbackGroup::SharedPtr nav_callback_group_;
        rclcpp::CallbackGroup::SharedPtr odom_callback_group_;
        rclcpp::executors::SingleThreadedExecutor callback_group_executor_;
        std::shared_future<rclcpp_action::ClientGoalHandle<NavToPoseAction>::SharedPtr> future_goal_handle_;
        Position current_pos_;
        
        
        void navigate_to_pose(const float x, const float y, const float z, const float roll, const float pitch, const float yaw);
        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr move_to_pose_subscriber_;
        rclcpp::Subscription<OdomMsg>::SharedPtr odom_subsciber_;
        rclcpp::Publisher<TwistMsg>::SharedPtr lift_publisher_;
        rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_publisher_;
        std::shared_ptr<rclcpp::Publisher<std_msgs::msg::String>> feedback_publisher_;
        std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
        void move_to_pose_callback(const std::shared_ptr<std_msgs::msg::String> msg);
        void lift(const float z);
        void odom_received_callback(const std::shared_ptr<OdomMsg> msg);
        void nav_result_callback(const rclcpp_action::ClientGoalHandle<NavToPoseAction>::WrappedResult &result);
        void nav_feedback_callback(std::shared_ptr<NavToPoseGoalHandle>, const std::shared_ptr<const NavToPoseAction::Feedback> feedback);
        void nav_goal_acknowledged_callback(const std::shared_ptr<rclcpp_action::ClientGoalHandle<NavToPoseAction>> &goal);
    };


#endif