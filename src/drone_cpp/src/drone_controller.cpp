#include "drone_controller.hh"



explicit DroneController::DroneController(const std::string &node_name) : Node(node_name){

    this->nav_to_pose_client_ = rclcpp_action::create_client<NavToPoseAction>(
        this,
        "navigate_to_pose"
    );

    this->move_to_pose_subscriber_ = this->create_subscription<TwistMsg>(
        "cmd_vel", 10, 
        [this](const std::shared_ptr<std_msgs::msg::String> msg) {
            this->move_to_pose_callback(msg);
        }
    );

    this->callback_group_ = create_callback_group(
        rclcpp::CallbackGroupType::MutuallyExclusive,
        false);
    
    this->callback_group_executor_.add_callback_group(callback_group_, get_node_base_interface());
    
    
    


}


DroneController::~DroneController()
    {
        RCLCPP_INFO(this->get_logger(), "DroneController node destroyed!");
        // ... your cleanup code here ...
    }
void DroneController::move_to_pose_callback(const std::shared_ptr<std_msgs::msg::String> msg){

    const std::string &msg_str = msg->data;
    json json_object = json::parse(msg_str);

    for (const auto& key : json_object){

        if (json_object[key].is_number_float()){
            // https://cplusplus.com/reference/string/stof/
            float arg_as_float = json_object[key];
        }else{
            RCLCPP_ERROR_STREAM(this->get_logger(), "The argument of json was not a float!");
        }

    }

};

void DroneController::navigate_to_pose(const Position &pos){




}