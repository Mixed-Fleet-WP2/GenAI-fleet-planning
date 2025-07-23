#ifndef NAVIGATABLE_HPP
#define NAVIGATABLE_HPP

#include <memory>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "mf_utils/types.hpp"
#include "std_msgs/msg/string.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "mf_utils/utils.hpp"

using TwistMsg = geometry_msgs::msg::Twist;
using PoseStampedMsg = geometry_msgs::msg::PoseStamped;
using NavToPoseAction = nav2_msgs::action::NavigateToPose;
using NavToPoseGoalHandle = rclcpp_action::ClientGoalHandle<NavToPoseAction>;
using OdomMsg = nav_msgs::msg::Odometry;

class Navigatable : public rclcpp::Node {
    public:
        Navigatable();
        void send_feedback(Feedback feedback);
    protected:
        std::string node_name_ = "";

        rclcpp_action::Client<NavToPoseAction>::SharedPtr nav_to_pose_client_;
        rclcpp::CallbackGroup::SharedPtr nav_callback_group_;
        rclcpp::CallbackGroup::SharedPtr odom_callback_group_;
        //rclcpp::executors::SingleThreadedExecutor callback_group_executor_;
        std::shared_future<rclcpp_action::ClientGoalHandle<NavToPoseAction>::SharedPtr> future_goal_handle_;
        Position current_pos_;

        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr move_to_pose_subscriber_;
        rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_publisher_;
        std::shared_ptr<rclcpp::Publisher<std_msgs::msg::String>> feedback_publisher_;
        rclcpp::Subscription<OdomMsg>::SharedPtr odom_subsciber_;

        void odom_received_callback(const std::shared_ptr<OdomMsg> msg);
        virtual void navigate_to_pose(const Position& pos, int action_id) = 0;
        void send_nav_goal(const Position& pos, int action_id);
        void nav_result_callback(const rclcpp_action::ClientGoalHandle<NavToPoseAction>::WrappedResult &result, int action_id);
        void nav_feedback_callback(std::shared_ptr<NavToPoseGoalHandle> g, const std::shared_ptr<const NavToPoseAction::Feedback> feedback, int action_id);
        void nav_goal_acknowledged_callback(std::shared_ptr<rclcpp_action::ClientGoalHandle<NavToPoseAction>> goal, int action_id);
        void move_to_pose_callback(const std::shared_ptr<std_msgs::msg::String> msg);
};

#endif