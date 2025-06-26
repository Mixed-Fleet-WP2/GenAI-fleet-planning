#ifndef STATE_BRIDGE_HPP
#define STATE_BRIDGE_HPP

#include "geometry_msgs/msg/pose.hpp"
#include "std_msgs/msg/string.hpp"
#include "rclcpp/rclcpp.hpp"
#include "tf2_msgs/msg/tf_message.hpp"
#include "mf_utils/utils.hpp"
#include "mf_utils/types.hpp"
#include "mf_utils/json.hpp"

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
    };
}

#endif // STATE_BRIDGE_HPP
