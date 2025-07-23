#ifndef CONVERSION_UTILS_HPP
#define CONVERSION_UTILS_HPP

#include <cmath>
#include <tuple>
#include <optional>
#include "mf_utils/types.hpp"

// https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles

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
 * Convert roll, pitch and yaw in euler to quaternion
 * @param roll roll in radians
 * @param pitch pitch in radians
 * @param yaw yaw in radians
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

template <typename T>
std::optional<ExecutableAction> parse_json(std::string msg_str, T node)

    try {
        
        if (!json::accept(msg_str)){
            std::cerr << "Received invalid json of the format: " + msg_str << std::flush << std::endl;;
            return std::nullopt;
        }
        
        json json_object = json::parse(msg_str);
        // https://json.nlohmann.me/home/exceptions/#jsonexceptiontype_error302
        ExecutableAction action = json_object.template get<ExecutableAction>();
        return action;
    }catch (json::type_error &e){
        node->send_feedback({-1, ERROR, "Parsing json failed"});
        return std::nullopt;
    }

#endif