#ifndef STATE_BRIDGE_HPP
#define STATE_BRIDGE_HPP

#include "geometry_msgs/msg/pose.hpp"
#include "std_msgs/msg/string.hpp"
#include "rclcpp/rclcpp.hpp"
#include "tf2_msgs/msg/tf_message.hpp"
#include "utils.hpp"
#include "types.hpp"
#include "json.hpp"


class StateBridge : public rclcpp::Node {
public:
    StateBridge();
private:
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pose_publisher_;
    rclcpp::Subscription<tf2_msgs::msg::TFMessage>::SharedPtr pose_subscriber_;
    void pose_callback(const tf2_msgs::msg::TFMessage::SharedPtr msg);
};

#endif // STATE_BRIDGE_HPP
