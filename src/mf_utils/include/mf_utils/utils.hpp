#ifndef CONVERSION_UTILS_HPP
#define CONVERSION_UTILS_HPP

#include <cmath>
#include <tuple>

// https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles
std::tuple<float, float, float> quaternion_to_euler(float x, float y, float z, float w){

    double sinr_cosp = 2 * (w * x + y * z);
    double cosr_cosp = 1 - 2 * (x * x + y * y);
    double roll = std::atan2(sinr_cosp, cosr_cosp);

    double sinp = std::sqrt(1 + 2 * (w * y - x * z));
    double cosp = std::sqrt(1 - 2 * (w * y - x * z));
    double pitch = 2 * std::atan2(sinp, cosp) - M_PI / 2;

    double siny_cosp = 2 * (w * z + x * y);
    double cosy_cosp = 1 - 2 * (y * y + z * z);
    double yaw = std::atan2(siny_cosp, cosy_cosp);

    return {static_cast<float>(roll), static_cast<float>(pitch), static_cast<float>(yaw)};

}

#endif