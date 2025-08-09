#include "forklift_controller.hpp"

ForkliftController::ForkliftController() : Navigatable() {


    // Deattach the pallets
    // const auto PALLETS = std::vector<std::string>{"euro_pallet_2"};

    // rclcpp::SubscriptionOptions options;
    // options.callback_group = odom_callback_group_;
    // for (const auto &pallet : PALLETS){
    //     pallet_subscriptions_.push_back(
    //         this->create_subscription<std_msgs::msg::String>(
    //             "/" + pallet + "/state", 10, 
    //             [this, pallet](const std_msgs::msg::String::ConstSharedPtr msg) {
                    
    //                 if (msg->data == "attached") {
    //                     RCLCPP_INFO_STREAM(get_logger(), "Pallet " << pallet << " is attached");
    //                     pallet_statues_[pallet] = true;
    //                 } else if (msg->data == "detached") {
    //                     RCLCPP_INFO_STREAM(get_logger(), "Pallet " << pallet << " is detached");
    //                     pallet_statues_[pallet] = false;
    //                 }
                    
    //             }, options
    //         )
    //     );
    //     pallet_statues_[pallet] = true; // Assume all pallets are attached at the start
    // }

    // for (const auto &pallet : PALLETS){
    //     auto publisher = this->create_publisher<std_msgs::msg::Empty>(
    //         "/" + pallet + "/detach", 10
    //     );
    //     auto msg = std_msgs::msg::Empty();

    //         // If the pallet is attached, loop until it is detached
    //         while (pallet_statues_[pallet]) {
    //             publisher->publish(msg);
    //             // Refactor in the future
    //             rclcpp::spin_some(this->get_node_base_interface());
    //         }
            
    //     // Give Gazebo some time to process the detach
    //     rclcpp::sleep_for(std::chrono::milliseconds(100));
    // }

    move_to_pose_subscriber_ = this->create_subscription<std_msgs::msg::String>(
        "move", 10, 
        [this](const std::shared_ptr<std_msgs::msg::String> msg) {
             RCLCPP_INFO_STREAM(get_logger(), "Move callback triggered with: " << msg->data);
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

    rclcpp::SubscriptionOptions options2;
    options2.callback_group = odom_callback_group_;
    ground_truth_tf_subscription_ = this->create_subscription<tf2_msgs::msg::TFMessage>(
        "pose", 10,
        [this](const tf2_msgs::msg::TFMessage::ConstSharedPtr msg) {
            forklift_location_ = msg->transforms[0].transform.translation;
            forklift_orientation_ = msg->transforms[0].transform.rotation;
        }, options2
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

    const std::string &msg_str = msg->data;

    auto action = parse_json<JointPositionAction>(msg_str, this);
    
    if (!action.has_value()){
        return;
    }

    //Async action because of timer
    move_fork(action.value());

}

void ForkliftController::drop(const ObjectAction &action){

    const int id = action.action_id;
    const std::string object = action.object;

    // See fork_attach_offsets in robot_core.xacro for where these come from
    // Simply, this is the straight distance from the link origin
    // of fork_1 to fork_2
    static const float DISTANCE_BETWEEN_FORK_ORIGINS = 0.4;
    static const float DISTANCE_FROM_FORK_1_TO_CENTER = DISTANCE_BETWEEN_FORK_ORIGINS / 2;
    //Check forklift.urdf.xacro and fork.xacro for what these come from
    static const float FORK_LENGTH = 1.0;

    //Assume everything is on pallets with dimensions 1.2x0.8x0.144m (see euro_pallet model)
    const float PALLET_LENGTH = 0.8;

    // Detach the object
    auto detach_publisher = this->create_publisher<std_msgs::msg::Empty>(
        "/" + object + "/detach", 10
    );

    auto msg = std_msgs::msg::Empty();
    while(pallet_statues_[object]) {
        detach_publisher->publish(msg);
        // Refactor in the future
       rclcpp::sleep_for(std::chrono::milliseconds(100));
    };

    rclcpp::sleep_for(std::chrono::milliseconds(200));

    const bool drop_success = move_object_relative_to_fork(
        object, 
        (FORK_LENGTH / 2 + PALLET_LENGTH / 2),
        -DISTANCE_FROM_FORK_1_TO_CENTER
    );

    if (!drop_success){
        send_feedback({
            id,
            ERROR, 
            "Dropping the object " + object + " failed"
        });
    
    }
    
    send_feedback({
        id,
        SUCCESS, 
        "Dropping the object " + object + " succeeded"
    });
    
}


void ForkliftController::drop_callback_(const std_msgs::msg::String::ConstSharedPtr msg){

    const std::string &msg_str = msg->data;
    auto action = parse_json<ObjectAction>(msg_str, this);

    if (!action.has_value()){
        return;
    }

    drop(action.value());



}

void ForkliftController::move_fork(const JointPositionAction& action) {
    
    auto msg = std_msgs::msg::Float64();
    msg.data = action.position;
    fork_control_publisher_->publish(msg);

    auto desired_pos = 

    // Periodically check if the desired height has been reached
    // (simulates sensor input/hardware interrrupts)
    lift_timer_ = this->create_wall_timer(std::chrono::milliseconds(100),
        [this, action]() {
            // Smaller error possible because the gz sim joint controller is basically
            // as accurate as ground truth
            const float error = std::abs(current_fork_pos_ - action.position);
            RCLCPP_INFO_STREAM(get_logger(), std::to_string(error));
            if (error < 0.025){
                lift_timer_->cancel();
                send_feedback({
                    action.action_id, 
                    SUCCESS, 
                    "Fork raised to elevation: " + std::to_string(action.position)
                });
            }
        }
    );

}

void ForkliftController::navigate_to_pose(const MoveAction& action) {
    RCLCPP_INFO_STREAM(get_logger(), "Navigating to pose");
    send_nav_goal(action);
}

/**
 * @brief Utility function to move/teleport an object relative
 * to a forklift's fork number one. 
 * @note Without offsets, the object is move to the center
 * of the fork_1's coordinate frame (see forklift.urdf.xacro and fork.xacro for details)
 */
bool ForkliftController::move_object_relative_to_fork(
        const std::string object,  float offset_x, 
        float offset_y, float offset_z
        ) {
    
    // Hardcode transformations

    /**
     * - header:
    stamp:
      sec: 20
      nanosec: 970000000
    frame_id: forklift_1
  child_frame_id: forklift_1/fork_1
  transform:
    translation:
      x: 1.6999999952900167
      y: 0.20000000650070746
      z: -0.5549995100742626
    rotation:
      x: -7.301019404737875e-08
      y: -5.2422970161522105e-08
      z: -2.0704110233432486e-11
      w: 0.999999999999996
     */
    auto fork_pos_x_wrt_world = forklift_location_.x + 1.7;
    auto fork_pos_y_wrt_world = forklift_location_.y + 0.2;
    auto fork_pos_z_wrt_world = forklift_location_.z - 0.5;


    auto position = geometry_msgs::msg::Point();
    position.x = static_cast<float>(fork_pos_x_wrt_world + offset_x);
    position.y = static_cast<float>(fork_pos_y_wrt_world + offset_y);
    position.z = static_cast<float>(fork_pos_z_wrt_world + offset_z);

    // Service definitions:
    // https://docs.ros.org/en/iron/p/ros_gz_interfaces/interfaces/srv/SetEntityPose.html
    // https://docs.ros.org/en/iron/p/ros_gz_interfaces/interfaces/msg/Entity.html
    auto move_request = std::make_shared<ros_gz_interfaces::srv::SetEntityPose::Request>();
    
    // Forks have same orientation as the forklift
    move_request->pose.orientation = forklift_orientation_;
    move_request->pose.position = position;

    // Specify the request type with an enum, in this case
    // a model (object) is moved
    move_request->entity.type = move_request->entity.MODEL;
    move_request->entity.name = object;

    // RCLCPP_INFO_STREAM(get_logger(), "Moving object: " << object);
    // RCLCPP_INFO_STREAM(get_logger(), "Position: " << position.x << ", " << position.y << ", " << position.z);
    // RCLCPP_INFO_STREAM(get_logger(), "Orientation: " << forklift_orientation_.x << ", " 
    //     << forklift_orientation_.y << ", " << forklift_orientation_.z << ", " 
    //     << forklift_orientation_.w);
    // Send the request to the service
    auto future = object_pose_setter_client_->async_send_request(move_request);

    auto status = future.wait_for(std::chrono::seconds(10));

    if (status == std::future_status::timeout) {
        RCLCPP_ERROR_STREAM(get_logger(), "Timeout while moving object: " << object);
        return false;
    }


    RCLCPP_INFO_STREAM(get_logger(), "Object " << object << " attached to fork_1");

    return future.get()->success;
    

};

void ForkliftController::pick_up_callback_(const std_msgs::msg::String::ConstSharedPtr msg){

    const std::string &msg_str = msg->data;

    auto action = parse_json<ObjectAction>(msg_str, this);
    
    if (!action.has_value()){
        return;
    }

    pick_up(action.value());

}

void ForkliftController::pick_up(const ObjectAction& action){
    
    const std::string object = action.object;
    const int id = action.action_id;

    // See fork_attach_offsets in robot_core.xacro for where these come from
    // Simply, this is the straight distance from the link origin
    // of fork_1 to fork_2
    static const float DISTANCE_BETWEEN_FORK_ORIGINS = 0.4;
    static const float DISTANCE_FROM_FORK_1_TO_CENTER = DISTANCE_BETWEEN_FORK_ORIGINS / 2;

    const bool pick_up_success = move_object_relative_to_fork(object, 0.0, -DISTANCE_FROM_FORK_1_TO_CENTER, 0.0);

    // A small timeout to allow Gazebo to process the request
    // (otherwise the object is necessarily not in the right place
    // before the attach request is sent)
    rclcpp::sleep_for(std::chrono::milliseconds(200));

    if (!pick_up_success){
        send_feedback({
            id,
            ERROR, 
            "Picking up object " + object + " failed"
        });
        return;
    }

    //Attach the object to the fork_1 link
    auto attach_publisher = this->create_publisher<std_msgs::msg::Empty>(
        "/" + object + "/attach", 10
    );

    auto msg = std_msgs::msg::Empty();
    while(!pallet_statues_[object]) {
        attach_publisher->publish(msg);
        // Refactor in the future
       rclcpp::sleep_for(std::chrono::milliseconds(100));
    };

   
    send_feedback({
        id,
        SUCCESS, 
        "Picking up object " + object + " succeeded"
    });
    

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