#ifndef TYPES_HPP
#define TYPES_HPP

#include <cmath>
#include "json.hpp"
#include <vector>
#include <unordered_map>
#include <string>

using json = nlohmann::json;

struct ExecutableAction{
    int action_id;
    std::unordered_map<std::string, std::string> args;
};

//https://json.nlohmann.me/features/arbitrary_types/
//OR
//https://json.nlohmann.me/features/arbitrary_types/#simplify-your-life-with-macros


// void from_json(const json& j, ExecutableAction& e){
//     j.at("action_id").get_to(e.action_id);
//     j.at("args").get_to(e.args);


// }

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(ExecutableAction, action_id, args);

enum RobotStatus {
    ONLINE = 1,
    OFFLINE = 0,
    UNKNOWN = -1
};

struct Position{
    float x;
    float y;
    float z;
    float roll;
    float pitch;
    float yaw;
    void round();
};

struct RobotState {
    Position robot_position;
    RobotStatus robot_status;
    int32_t timestamp;
};

NLOHMANN_JSON_SERIALIZE_ENUM(RobotStatus, {
    {ONLINE, "ONLINE"},
    {OFFLINE, "OFFLINE"},
    {UNKNOWN, "UNKNOWN"}
})

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(RobotState, robot_position, robot_status, timestamp);

/**
 * Round the value of the Position to one decimal place
 */
void Position::round() {
    // https://www.reddit.com/r/cpp_questions/comments/173uhmq/how_do_i_round_a_double_to_one_decimal/
    this->x = std::round(x*10) / 10;
    this->y = std::round(y*10) / 10;
    this->z = std::round(z*10) / 10;
    this->roll = std::round(roll*10) / 10;
    this->roll = std::round(pitch*10) / 10;
    this->roll = std::round(yaw*10) / 10;

}


void to_json(json& j, const Position& p) {
    j = json{ 
                {"x", p.x},
                {"y", p.y},
                {"z", p.z},
                {"roll", p.roll}, 
                {"pitch", p.pitch},
                {"yaw", p.yaw}
    };
}

void from_json(const json& j, Position& p) {
    j.at("x").get_to(p.x);
    j.at("y").get_to(p.y);
    j.at("z").get_to(p.z); 
    j.at("roll").get_to(p.roll);
    j.at("pitch").get_to(p.pitch);
    j.at("yaw").get_to(p.yaw);
}


#endif