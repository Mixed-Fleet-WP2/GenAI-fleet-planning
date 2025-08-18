#ifndef NAVIGATABLE_HPP
#define NAVIGATABLE_HPP

#include <memory>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "nav2_msgs/action/navigate_through_poses.hpp"
#include "nav2_msgs/action/follow_waypoints.hpp"
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


using FollowWaypointsAction = nav2_msgs::action::FollowWaypoints;
using FollowWaypointsActionGoalHandle = rclcpp_action::ClientGoalHandle<FollowWaypointsAction>;

class Navigatable : public rclcpp::Node {
    public:
        Navigatable();
        void send_feedback(Feedback feedback);
    protected:
        std::string node_name_ = "";

        rclcpp_action::Client<NavToPoseAction>::SharedPtr nav_to_pose_client_;
        rclcpp_action::Client<FollowWaypointsAction>::SharedPtr nav_through_poses_client_;
        rclcpp::CallbackGroup::SharedPtr nav_callback_group_;
        rclcpp::CallbackGroup::SharedPtr odom_callback_group_;
        //rclcpp::executors::SingleThreadedExecutor callback_group_executor_;
        std::shared_future<rclcpp_action::ClientGoalHandle<NavToPoseAction>::SharedPtr> future_goal_handle_;
        std::shared_future<rclcpp_action::ClientGoalHandle<FollowWaypointsAction>::SharedPtr> waypoint_future_goal_handle_;
        Position current_pos_;

        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr move_to_pose_subscriber_;
        rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_publisher_;
        std::shared_ptr<rclcpp::Publisher<std_msgs::msg::String>> feedback_publisher_;
        rclcpp::Subscription<OdomMsg>::SharedPtr odom_subsciber_;

        void odom_received_callback(const std::shared_ptr<OdomMsg> msg);
        virtual void navigate_to_pose(const MoveAction&) = 0;
        void send_nav_goal(const MoveAction&);
        //void nav_result_callback(const rclcpp_action::ClientGoalHandle<NavToPoseAction>::WrappedResult &result, int action_id);
        //void nav_feedback_callback(std::shared_ptr<NavToPoseGoalHandle> g, const std::shared_ptr<const NavToPoseAction::Feedback> feedback, int action_id);
        //void nav_goal_acknowledged_callback(std::shared_ptr<rclcpp_action::ClientGoalHandle<NavToPoseAction>> goal, int action_id);
        void move_to_pose_callback(const std::shared_ptr<std_msgs::msg::String> msg);

        void send_nav_goals(std::vector<MoveAction> waypoints, std::function<void(const FollowWaypointsActionGoalHandle::WrappedResult&, int)> result_callback = nullptr);

        // NavAction = NavToPoseAction | NavThroughPosesAction
        // NavActionGoalHandle = NavToPoseGoalHandle | NavThroughPosesGoalHandle
        template <typename NavActionGoalHandle, typename NavAction>
        void nav_feedback_callback(std::shared_ptr<NavActionGoalHandle>, const std::shared_ptr<const typename NavAction::Feedback> feedback, int action_id){
            //auto curr_pose_x = feedback->current_pose.pose.position.x;
            //auto curr_pose_y = feedback->current_pose.pose.position.y;
        }

        template <typename NavActionGoalHandle>
        void nav_goal_acknowledged_callback(std::shared_ptr<NavActionGoalHandle> goal, int action_id){
            if (!goal) {
                Feedback feedback = {action_id, ERROR, "Failed to send nav goal to action server"};
                send_feedback(feedback);
            }else{
                RCLCPP_INFO(get_logger(), "Sent goal to server");
            }
        }
        //https://robotics.stackexchange.com/questions/107697/turtlebot4-nav2-how-to-call-action-navigatetopose-from-node-in-cpp
        template <typename NavActionGoalHandle>
        void nav_result_callback(
            const typename NavActionGoalHandle::WrappedResult &result, int action_id){
            Feedback feedback = {};
            feedback.action_id = action_id;
            
            switch (result.code) {
                case rclcpp_action::ResultCode::SUCCEEDED:
                    feedback.type = SUCCESS;
                    feedback.message = "Navigation succeeded";
                    break;
                case rclcpp_action::ResultCode::ABORTED:
                    feedback.type = ERROR;
                    feedback.message = result.result->error_msg;
                    break;
                case rclcpp_action::ResultCode::CANCELED:
                    feedback.type = CANCELLED;
                    feedback.message = "Goal was canceled";
                    break;
                default:
                    feedback.type = ERROR;
                    feedback.message = "Unknow status code received from navigation";
                    break;
                }
            RCLCPP_INFO_STREAM(get_logger(), "SENDIN NAV FEED");
            send_feedback(feedback);
        }



};

#endif