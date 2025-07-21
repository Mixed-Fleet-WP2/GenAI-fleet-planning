#ifndef DRONE_CONTROLLER_HH
#define DRONE_CONTROLLER_HH

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <algorithm>

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

// https://www.wevolver.com/article/pid-loops-a-comprehensive-guide-to-understanding-and-implementation

// For the drone, the error is y and time is x-axis
class PIDController {

    public:
        //https://stackoverflow.com/questions/14495536/how-do-i-initialize-a-const-data-member?noredirect=1&lq=1
        PIDController(float interval=100, float kp=1, float ki=0, float kd=0){
            interval_ = interval / 100;
            Kp_ = kp;
            Ki_ = ki;
            Kd_ = kd;

        }

        float calculate_input(float error){
            
            std::cerr << "kp is " + std::to_string(Kp_) << std::endl;
            std::cerr << "kd is " + std::to_string(Kd_) << std::endl;
            std::cerr << "ki is " + std::to_string(Ki_) << std::endl;
            std::cerr << "Error is " + std::to_string(error) << std::endl;
            float p = Kp_ * error;
            // Use approximation: https://en.wikipedia.org/wiki/Numerical_differentiation
            // Goes near zero on the first feedback round
            // the time difference is constant because of the timer interval
            float d = Kd_* (error - previous_error_) / interval_;
            previous_error_ = error;

            //Use Riehmann sum for approximation (with constant-size intervals)
            //https://en.wikipedia.org/wiki/Riemann_sum
            cumulative_error_ += error;
            //Interval is constant so it can be taken out of the sum
            
            float i = Ki_* interval_ * cumulative_error_;
            // std::cout << "Integral: " + std::to_string(i) << std::endl << std::flush;
            // std::cout << "Derivative: " + std::to_string(d) << std::endl << std::flush;
            // std::cout << "Proportional: " + std::to_string(p) << std::endl << std::flush;

            // std::cerr << "Integral: " + std::to_string(i) << std::endl;
            // std::cerr << "Derivative: " + std::to_string(d) << std::endl;
            // std::cerr << "Proportional: " + std::to_string(p) << std::endl;
            // std::cerr.flush();

            return p+d+i;

        }
        void set_new_goal(float goal, float curr_pos){
            goal_ = goal;
            previous_error_ = goal-curr_pos;
            cumulative_error_ = 0;
        }

    private:
        float interval_;
        float Kp_;
        float Ki_;
        float Kd_;
        float previous_error_ = 0;
        float goal_;
        float cumulative_error_ = 0;

};

class DroneController: public rclcpp::Node{

    public:
        DroneController();
        //Needed to resolve compatibility error with the base destructor
        // needs to be taken care of some other way in the future??
        //~DroneController() noexcept;
    private:
        

        std::string node_name_ = "";

        

        rclcpp_action::Client<NavToPoseAction>::SharedPtr nav_to_pose_client_;
        rclcpp::CallbackGroup::SharedPtr nav_callback_group_;
        rclcpp::CallbackGroup::SharedPtr odom_callback_group_;
        rclcpp::executors::SingleThreadedExecutor callback_group_executor_;
        std::shared_future<rclcpp_action::ClientGoalHandle<NavToPoseAction>::SharedPtr> future_goal_handle_;
        Position current_pos_;
        rclcpp::TimerBase::SharedPtr lift_timer_;

        //Interval for the timer callback for lifting the drone up runs (in ms)
        const int lift_interval_ = 100;
        PIDController pid_controller_ = PIDController(lift_interval_, 0.18, 0.0, 0.4);
        
        
        void navigate_to_pose(const Position& pos, int action_id);
        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr move_to_pose_subscriber_;
        rclcpp::Subscription<OdomMsg>::SharedPtr odom_subsciber_;
        rclcpp::Publisher<TwistMsg>::SharedPtr lift_publisher_;
        rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_publisher_;
        std::shared_ptr<rclcpp::Publisher<std_msgs::msg::String>> feedback_publisher_;
        std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
        void move_to_pose_callback(const std::shared_ptr<std_msgs::msg::String> msg);
        void lift_callback(const float z, std::function<void()> cb, rclcpp::Time start);
        void odom_received_callback(const std::shared_ptr<OdomMsg> msg);
        void send_nav_goal(const Position& pos, int action_id);
        void nav_result_callback(const rclcpp_action::ClientGoalHandle<NavToPoseAction>::WrappedResult &result, int action_id);
        void nav_feedback_callback(std::shared_ptr<NavToPoseGoalHandle> g, const std::shared_ptr<const NavToPoseAction::Feedback> feedback, int action_id);
        void nav_goal_acknowledged_callback(std::shared_ptr<rclcpp_action::ClientGoalHandle<NavToPoseAction>> goal);
    };


#endif