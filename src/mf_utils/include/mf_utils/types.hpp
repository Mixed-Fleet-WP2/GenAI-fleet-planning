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
    std::unordered_map<std::string, json> command_arguments;
};


//https://json.nlohmann.me/features/arbitrary_types/
//OR
//https://json.nlohmann.me/features/arbitrary_types/#simplify-your-life-with-macros

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(ExecutableAction, action_id, command_arguments);

struct MoveAction{
    int action_id;
    float x;
    float y;
    float z;
    float roll;
    float pitch;
    float yaw;
};

struct ObjectAction {
    int action_id;
    std::string object;
};

struct JointPositionAction {
    int action_id;
    float position;
};

struct SearchAction{
    int action_id;
};

void from_json(const json& j, ObjectAction& action) {
    j.at("action_id").get_to(action.action_id);
    j.at("command_arguments").at("object").get_to(action.object);
}

void from_json(const json& j, JointPositionAction& action) {
    j.at("action_id").get_to(action.action_id);
    j.at("command_arguments").at("position").get_to(action.position);
}

void from_json(const json& j, SearchAction& action) {
    j.at("action_id").get_to(action.action_id);
}


// https://github.com/nlohmann/json/issues/2199

void from_json(const json& j, MoveAction& action) {
    j.at("action_id").get_to(action.action_id);
    j.at("command_arguments").at("x").get_to(action.x);
    j.at("command_arguments").at("y").get_to(action.y);
    j.at("command_arguments").at("z").get_to(action.z);
    j.at("command_arguments").at("roll").get_to(action.roll);
    j.at("command_arguments").at("pitch").get_to(action.pitch);
    j.at("command_arguments").at("yaw").get_to(action.yaw);
}

enum FeedbackType{
    SUCCESS = 1,
    ERROR = 0,
    CANCELLED = -1
};

//https://json.nlohmann.me/features/enum_conversion/
NLOHMANN_JSON_SERIALIZE_ENUM(FeedbackType, {
    {SUCCESS, "SUCCESS"},
    {ERROR, "ERROR"},
    {CANCELLED, "CANCELLED"}
})

struct Feedback{
    int action_id;
    FeedbackType type;
    std::string message;
    json return_value = {};
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(Feedback, action_id, type, message, return_value);


struct Position{
    float x;
    float y;
    float z;
    float roll;
    float pitch;
    float yaw;
    void round();
    // float diff(const Position& other);
};

/**
 * Round the value of the Position to one decimal place
 */
void Position::round() {
    // https://www.reddit.com/r/cpp_questions/comments/173uhmq/how_do_i_round_a_double_to_one_decimal/
    this->x = std::round(x*10) / 10;
    this->y = std::round(y*10) / 10;
    this->z = std::round(z*10) / 10;
    this->roll = std::round(roll*10) / 10;
    this->pitch = std::round(pitch*10) / 10;
    this->yaw = std::round(yaw*10) / 10;

}

// float Position::diff(const Position& other){


// }

enum RobotStatus {
    ONLINE = 1,
    OFFLINE = 0,
    UNKNOWN = -1
};

struct RobotState {
    Position robot_position;
    RobotStatus robot_status;
    int32_t timestamp;
};

//https://json.nlohmann.me/features/enum_conversion/
NLOHMANN_JSON_SERIALIZE_ENUM(RobotStatus, {
    {ONLINE, "ONLINE"},
    {OFFLINE, "OFFLINE"},
    {UNKNOWN, "UNKNOWN"}
})

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(RobotState, robot_position, robot_status, timestamp);




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