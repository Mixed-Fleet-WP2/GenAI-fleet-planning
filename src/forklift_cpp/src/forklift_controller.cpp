#include "forklift_controller.hpp"

ForkliftController::ForkliftController() : Navigatable() {

    move_to_pose_subscriber_ = this->create_subscription<std_msgs::msg::String>(
        "move", 10, 
        [this](const std::shared_ptr<std_msgs::msg::String> msg) {
            this->move_to_pose_callback(msg);
        }
    );

    move_fork_subscription_ = this->create_subscription<std_msgs::msg::String>(
        "move_fork", 10, 
        [this](const std_msgs::msg::String::ConstSharedPtr msg){
            this->move_fork_callback_(msg);
        }
    );

    pick_up_subscription_ = this->create_subscription<std_msgs::msg::String>(
        "pick_up", 10,
        [this](const std_msgs::msg::String::ConstSharedPtr msg){
            pick_up_callback_(msg);
        }
    );

    drop_subscription_ = this->create_subscription<std_msgs::msg::String>(
        "drop", 10,
        [this](const std_msgs::msg::String::ConstSharedPtr msg){
            this->drop_callback_(msg);
        }
    );

    joint_state_subscription_ = this->create_subscription<sensor_msgs::msg::JointState>(
        "joint_states", 10,
        [this](const sensor_msgs::msg::JointState::ConstSharedPtr msg){
            this->joint_states_callback_(msg);
        }

    );

    fork_control_publisher_ = this->create_publisher<std_msgs::msg::Float64>(
        "fork_control", 10
    );


}
void ForkliftController::move_fork_callback_(const std_msgs::msg::String::ConstSharedPtr msg) {

    try {
        const std::string &msg_str = msg->data;
        
       auto action = parse_json(msg_str);
        
        if (!action.has_value()){
            send_feedback({-1, ERROR, "Failed to parse payload"});
            return;
        }

        auto args = action->command_arguments;

        float z = args.at("z").get<float>();

        move_fork(z, action->action_id);

        
    }catch (json::type_error &e){
        RCLCPP_ERROR_STREAM(get_logger(), e.what());
    // If json does not have the key
    }catch (std::out_of_range &e){
        RCLCPP_ERROR_STREAM(get_logger(), e.what());
    }catch(std::invalid_argument &e){
        // If strings cannot be parsed to floats
        RCLCPP_ERROR_STREAM(get_logger(), e.what());
    }

}

void ForkliftController::move_fork(float z, int action_id) {
    
    auto msg = std_msgs::msg::Float64();
    msg.data = z;
    fork_control_publisher_->publish(msg);
    
    // Periodically check if the desired height has been reached
    // (simulates sensor input/hardware interrrupts)
    this -> create_wall_timer(std::chrono::milliseconds(100),
        [this, z, action_id]() {
            
            if (std::abs(current_fork_pos_ - z) < 0.05)
                send_feedback({action_id, SUCCESS, "Fork raised"});
        }
    );

};

void ForkliftController::joint_states_callback_(const sensor_msgs::msg::JointState::ConstSharedPtr joint_states)
{
}