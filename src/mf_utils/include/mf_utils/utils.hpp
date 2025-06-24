#ifndef CONVERSION_UTILS_HPP
#define CONVERSION_UTILS_HPP

#include <tuple>
#include "tf2/LinearMath/Quaternion.h"
#include "tf2/LinearMath/Matrix3x3.h"

std::tuple<float, float, float> quaternion_to_euler(float x, float y, float z, float w){

    auto quaternion = tf2::Quaternion(x, y, z, w);
    
    //https://robotics.stackexchange.com/questions/46421/transform-quaternion
    // Convert quaternion into matrix
    auto matrix = tf2::Matrix3x3(quaternion);

    double roll = 0.0;
    double pitch = 0.0;
    double yaw = 0.0;
    // Get euler from the matrix by passing references and populating
    matrix.getRPY(roll, pitch, yaw);

    return {static_cast<float>(roll), static_cast<float>(pitch), static_cast<float>(yaw)};

}

#endif