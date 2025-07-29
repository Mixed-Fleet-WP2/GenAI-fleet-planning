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

    // Use the nav callback group with the object pose setter. It does not matter
    // significantly because the operation returning takes minimal time and
    // the actions are not used together.
    object_pose_setter_client_ = this->create_client<ros_gz_interfaces::srv::SetEntityPose>(
        "/world/warehouse/set_pose",
        rclcpp::ServicesQoS(), 
        nav_callback_group_);


}
void ForkliftController::move_fork_callback_(const std_msgs::msg::String::ConstSharedPtr msg) {

    

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
void ForkliftController::navigate_to_pose(const MoveAction& action) {
    send_nav_goal(action);
};

void ForkliftController::pick_up_callback_(const std_msgs::msg::String::ConstSharedPtr msg){

    const std::string &msg_str = msg->data;

    auto action = parse_json<PickUpAction>(msg_str, this);
    
    if (!action.has_value()){
        RCLCPP_INFO_STREAM(get_logger(), "RETURNED EMPTY");
        return;
    }

    pick_up(action.value());

}

void ForkliftController::pick_up(const PickUpAction& action){
    
    const std::string object = action.object;
    const int id = action.action_id;

    try {
    // https://docs.ros.org/en/foxy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Listener-Cpp.html
    auto buffer = tf2_ros::Buffer(
        this->get_clock(), 
        tf2::Duration(tf2::BUFFER_CORE_DEFAULT_CACHE_TIME), this
    );

    auto tf_listener = tf2_ros::TransformListener(buffer);


    // Get fork's pose in the map frame i.e. global pose
    auto transform = buffer.lookupTransform(
        "map",
        "fork_1",
        rclcpp::Time(0),
        rclcpp::Duration::from_seconds(10)
    );

    auto fork_global_rotation = transform.transform.rotation;
    auto [fork_global_x, fork_global_y, fork_global_z] = transform.transform.translation;

    // Service definitions:
    // https://docs.ros.org/en/iron/p/ros_gz_interfaces/interfaces/srv/SetEntityPose.html
    // https://docs.ros.org/en/iron/p/ros_gz_interfaces/interfaces/msg/Entity.html
    auto move_request = std::make_shared<ros_gz_interfaces::srv::SetEntityPose::Request>();

    static const float DISTANCE_BETWEEN_FORK_ORIGINS = 0.4;

    auto position = geometry_msgs::msg::Point();
    position.x = static_cast<float>(fork_global_x);
    position.y = static_cast<float>(fork_global_y - DISTANCE_BETWEEN_FORK_ORIGINS / 2);
    position.z = static_cast<float>(fork_global_z);
    
    // See urdf fork_attach_offsets for where these come from
    //const float FORK_WIDTH = 0.1;
    

    move_request->pose.orientation = fork_global_rotation;
    move_request->pose.position = position;

    // Specify the request type with an enum, in this case
    // a model (object) is moved
    move_request->entity.type = move_request->entity.MODEL;
    move_request->entity.name = object;

    auto future = object_pose_setter_client_->async_send_request(
    move_request);
    
    // A timeout is set in case the simulation returns no response (unlikely)
    // in real scenario this would be checked with sensors inside a timer
    // but simulation returns a boolean.
    auto status = future.wait_for(std::chrono::seconds(10));
    
    // https://en.cppreference.com/w/cpp/thread/future/wait_for.html
    if (status == std::future_status::timeout){
        send_feedback({id, ERROR, "Picking up object " + object + " failed. Timeout exceeded"});
        return;
    }
   
    auto result= future.get();

    if (!result->success){
        send_feedback({
            id,
            ERROR, 
            "Picking up object " + object + " failed"
        });
    }else{
        send_feedback({
            id,
            SUCCESS, 
            "Picking up object " + object + " succeeded"
        });
    }

    }
    catch(const tf2::TransformException & ex) {
        send_feedback({id, ERROR, ex.what()});
        return;
    }
}

void ForkliftController::joint_states_callback_(
    const sensor_msgs::msg::JointState::ConstSharedPtr joint_states){
    
    // Message definition for JointState:
    // https://docs.ros2.org/foxy/api/sensor_msgs/msg/JointState.html

    // The topic only publishes the state of the joints if alphabetic
    // order so fork_plate is the first item
    // Just in case this ever changes, add a guard that uses std::find
    if (joint_states->name.at(0) != "fork_plate_joint"){
        
        RCLCPP_INFO_STREAM(get_logger(), "Using std::find");
        std::vector<std::string> joint_names = joint_states->name;

        const auto iter = std::find(joint_names.begin(), joint_names.end(), "fork_plate_joint");
        // https://stackoverflow.com/questions/1425349/how-do-i-find-an-element-position-in-stdvector
        auto joint_index = std::distance(joint_names.begin(), iter);
        current_fork_pos_ = joint_states->position.at(joint_index);

    }

    current_fork_pos_ = joint_states->position.at(0);
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