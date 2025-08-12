#ifndef CONVERSION_UTILS_HPP
#define CONVERSION_UTILS_HPP

#include <cmath>
#include <tuple>
#include <optional>
#include <utility>
#include "mf_utils/types.hpp"
#include "tf2_ros/transform_broadcaster.h"
#include "tf2_ros/transform_listener.h"
#include "tf2_ros/buffer.h"
#include "geometry_msgs/msg/transform_stamped.h"
#include <string>
#include "geometry_msgs/msg/vector3.h"
#include "geometry_msgs/msg/quaternion.h"

// https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles

/**
 * @brief Convert a quaternion to euler angles
 * @param x X component of the quaternion
 * @param y Y component of the quaternion
 * @param z Z component of the quaternion
 * @param w W component of the quaternion
 * @returns Tuple containing roll, pitch and yaw (in this order)
 */
std::tuple<float, float, float> quaternion_to_euler(float x, float y, float z, float w){

    double sinr_cosp = 2 * (w * x + y * z);
    double cosr_cosp = 1 - 2 * (x * x + y * y);
    float roll = static_cast<float>(std::atan2(sinr_cosp, cosr_cosp));

    double sinp = std::sqrt(1 + 2 * (w * y - x * z));
    double cosp = std::sqrt(1 - 2 * (w * y - x * z));
    float pitch = static_cast<float>(2 * std::atan2(sinp, cosp) - M_PI / 2);

    double siny_cosp = 2 * (w * z + x * y);
    double cosy_cosp = 1 - 2 * (y * y + z * z);
    float yaw = static_cast<float>(std::atan2(siny_cosp, cosy_cosp));

    return {roll, pitch, yaw};

}


// 

/**
 * @brief Convert roll, pitch and yaw in euler to quaternion
 * @arg roll roll in radians
 * @arg pitch pitch in radians
 * @arg yaw yaw in radians
 * @return tuple that contains x, y, z, w parts of the quaternion in this order
 */
std::tuple<float, float, float, float>euler_to_quaternion(double roll, double pitch, double yaw) // roll (x), pitch (y), yaw (z), angles are in radians
{
    // Abbreviations for the various angular functions

    double cr = cos(roll * 0.5);
    double sr = sin(roll * 0.5);
    double cp = cos(pitch * 0.5);
    double sp = sin(pitch * 0.5);
    double cy = cos(yaw * 0.5);
    double sy = sin(yaw * 0.5);

    double w = static_cast<float>(cr * cp * cy + sr * sp * sy);
    double x = static_cast<float>(sr * cp * cy - cr * sp * sy);
    double y = static_cast<float>(cr * sp * cy + sr * cp * sy);
    double z = static_cast<float>(cr * cp * sy - sr * sp * cy);

    return {x,y,z, w};
}


/**
 * Parses a json-formatted string into a type specified 
 * by caller.
 * @arg msg_str Json formatted string
 * @arg node Ros2 node that implements send_feedback
 * @tparam ToType The type to convert the string to
 * @tparam NodeLike Object that inherits from
 * rclcpp::Node and implements send_feedback
 */
template <typename ToType, typename NodeLike>
std::optional<ToType> parse_json(std::string msg_str, NodeLike node)
 {
    
    try {
        
        if (!json::accept(msg_str)) {
            RCLCPP_INFO_STREAM(node->get_logger(), "invalid json");
            std::cerr << "Received invalid json of the format: " + msg_str << std::flush << std::endl;
            return std::nullopt;
        }

        json json_object = json::parse(msg_str);
        ToType action = json_object.template get<ToType>();
        return action;

    } catch (json::exception &e) {
        RCLCPP_INFO_STREAM(node->get_logger(), e.what());
        node->send_feedback({-1, ERROR, "Parsing json failed"});
        return std::nullopt;
    
    // If json does not have the key
    } catch (std::out_of_range &e){
        RCLCPP_INFO_STREAM(node->get_logger(), e.what());
        node->send_feedback({-1, ERROR, e.what()});
        return std::nullopt;
    } catch(std::invalid_argument &e){
        RCLCPP_INFO_STREAM(node->get_logger(), e.what());
        // If the object name cannot be converted to string
        node->send_feedback({-1, ERROR, e.what()});
        return std::nullopt;
    }
}

/**
 * Get a transform from one coordinate frame to another (i.e. express the coordinates in
 * one coordinate frame in another). 
 * 
 * @arg node A rclcpp::Node instance
 * @arg target_frame Coordinate frame to convert to
 * @arg source_frame Coordinate frame to convert from
 * @tparam NodeLike Object that inherits from rclcpp::Node. Needed
 * to infer the namespace the coordinate frames live in
 * 
 * @return Pair where the first item is translation and second rotation. Nullopt if
 * transform could not be retrieved.
 */
template <typename NodeLike>
std::optional<std::pair<geometry_msgs::msg::Vector3, geometry_msgs::msg::Quaternion>> get_coords_in_other_frame(NodeLike node,
    const std::string& target_frame, const std::string& source_frame){

    try{
        // https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Listener-Cpp.html
        auto buffer = tf2_ros::Buffer(
            node->get_clock(), 
            tf2::Duration(tf2::BUFFER_CORE_DEFAULT_CACHE_TIME), node
        );

        auto tf_listener = tf2_ros::TransformListener(buffer);

        // Get fork's pose in the map frame i.e. global pose
        auto transform = buffer.lookupTransform(
            target_frame,
            source_frame,
            rclcpp::Time(0),
            rclcpp::Duration::from_seconds(10)
        );

        const auto translation_and_rotation = std::make_pair(transform.transform.translation, transform.transform.rotation);
        return translation_and_rotation;

    }catch(const tf2::TransformException & ex) {
        return std::nullopt;
    }

}

#endif