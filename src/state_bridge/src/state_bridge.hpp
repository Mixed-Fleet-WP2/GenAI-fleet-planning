#ifndef STATE_BRIDGE_HPP
#define STATE_BRIDGE_HPP

#include <unordered_set>
#include <future>
#include "geometry_msgs/msg/pose.hpp"
#include "std_msgs/msg/string.hpp"
#include "rclcpp/rclcpp.hpp"
#include "tf2_msgs/msg/tf_message.hpp"
#include "mf_utils/utils.hpp"
#include "mf_utils/types.hpp"
#include "mf_utils/json.hpp"
#include "std_msgs/msg/empty.hpp"
#include "std_msgs/msg/string.hpp"
#include "attach_interfaces/srv/change_attach.hpp"

namespace state_bridge {

    class StateBridge : public rclcpp::Node {
    public:
        // Use default values for options as default
        // https://docs.ros2.org/dashing/api/rclcpp/classrclcpp_1_1NodeOptions.html
        StateBridge(const rclcpp::NodeOptions & option = rclcpp::NodeOptions());
    private:
        rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pose_publisher_;
        rclcpp::Subscription<tf2_msgs::msg::TFMessage>::SharedPtr pose_subscriber_;
        void pose_callback(const tf2_msgs::msg::TFMessage::SharedPtr msg);
        std::unordered_set<std::string> object_names_;
        bool detach_object(const std::string & object_name);
        rclcpp::CallbackGroup::SharedPtr cb_group_;
        rclcpp::TimerBase::SharedPtr timer_;
        rclcpp::SubscriptionOptions sub_options_;
        rclcpp::Service<attach_interfaces::srv::ChangeAttach>::SharedPtr attach_srv_;
        void attach_srv_callback(const attach_interfaces::srv::ChangeAttach::Request::SharedPtr req, attach_interfaces::srv::ChangeAttach::Response::SharedPtr res);
    };
}

#endif // STATE_BRIDGE_HPP
