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

    // https://github.com/gazebosim/ros_gz/pull/380
    object_pose_setter_client_ = this->create_client<ros_gz_interfaces::srv::SetEntityPose>("/set_model_pose");


}
void ForkliftController::move_fork_callback_(const std_msgs::msg::String::ConstSharedPtr msg) {

    try {
        const std::string &msg_str = msg->data;
        
       auto action = parse_json(msg_str, this);
        
        if (!action.has_value()){
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

void ForkliftController::drop_callback_(const std_msgs::msg::String::ConstSharedPtr msg)
{
}

void ForkliftController::move_fork(float z, int action_id) {
    
    auto msg = std_msgs::msg::Float64();
    msg.data = z;
    fork_control_publisher_->publish(msg);
    
    // Periodically check if the desired height has been reached
    // (simulates sensor input/hardware interrrupts)
    this -> create_wall_timer(std::chrono::milliseconds(100),
        [this, z, action_id]() {
            
            // Smaller error possible because the gz sim joint controller is basically
            // as accurate as ground truth
            if (std::abs(current_fork_pos_ - z) < 0.025)
                send_feedback({action_id, SUCCESS, "Fork raised to elevation: " + std::to_string(z)});
        }
    );

}
void ForkliftController::navigate_to_pose(const Position &pos, int action_id) {
    send_nav_goal(pos, action_id);
};

void ForkliftController::pick_up_callback_(const std_msgs::msg::String::ConstSharedPtr msg){

    try {
        const std::string &msg_str = msg->data;
        
       auto action = parse_json(msg_str, this);
        
        if (!action.has_value()){
            send_feedback({-1, ERROR, "Failed to parse payload. Is the json in correct format?"});
            return;
        }

        auto args = action->command_arguments;

        std::string object_name = args.at("object").get<std::string>();

        pick_up(object_name);

        
    }catch (json::type_error &e){
        RCLCPP_ERROR_STREAM(get_logger(), e.what());
    // If json does not have the key
    }catch (std::out_of_range &e){
        RCLCPP_ERROR_STREAM(get_logger(), e.what());
    }catch(std::invalid_argument &e){
        // If the object name cannot be converted to string
        RCLCPP_ERROR_STREAM(get_logger(), e.what());
    }

}

void ForkliftController::pick_up(std::string object){
    
    try {
    // https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Listener-Cpp.html
    auto buffer = tf2_ros::Buffer(this->get_clock(), tf2::Duration(tf2::BUFFER_CORE_DEFAULT_CACHE_TIME), this);

    auto tf_listener = tf2_ros::TransformListener(buffer);

    auto transform = buffer.lookupTransform("map", "fork_1", rclcpp::Time(0), rclcpp::Duration::from_seconds(10));
    auto rotation = transform.transform.rotation;
    auto translation = transform.transform.translation;

    }
    catch(const tf2::TransformException & ex) {
          RCLCPP_INFO_STREAM(get_logger(), "Unable to get transform!");
          return;
        }
}

void ForkliftController::joint_states_callback_(const sensor_msgs::msg::JointState::ConstSharedPtr joint_states){

    // The topic only publishes the state of the fork_plate joint so the
    // array's length is always one
    current_fork_pos_ = joint_states->position[0];
    RCLCPP_INFO_STREAM(get_logger(), "THE POSITION OF THE FORK IS: " + std::to_string(current_fork_pos_));
}

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    
    // Assign 3 threads: the main thread and two other for the two callback groups
    auto executor = rclcpp::executors::MultiThreadedExecutor(rclcpp::ExecutorOptions(), 3);
    auto node = std::make_shared<ForkliftController>();
    executor.add_node(node);
    executor.spin();

    rclcpp::shutdown();

    rclcpp::shutdown();
    return 0;
}