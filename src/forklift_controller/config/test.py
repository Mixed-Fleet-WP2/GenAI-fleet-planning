import yaml

def add_namespace(yaml_file, namespace):
    with open(yaml_file, "r") as file:
        config = yaml.safe_load(file)

    # Iterate through bridge topics and add namespace
    bridge = config["/**/*"]["ros__parameters"]["bridge"]

    ros_to_mqtt_topics = bridge["ros2mqtt"]["ros_topics"]

    #Topic names for the mqtt messages (mqtt -> ros)
    mqtt_to_ros_topics_mqtt_names = bridge["mqtt2ros"]["mqtt_topics"]
    print(mqtt_to_ros_topics_mqtt_names)

    namespaced_topics = []
    #Append namespaces to mqtt topics as that is not done by ros2 system
    for topic in mqtt_to_ros_topics_mqtt_names:
        namespaced_topics.append(f"{namespace}/{topic}") 

    bridge["mqtt2ros"]["mqtt_topics"] = namespaced_topics

    with open(f"modified_{yaml_file}", "w") as file:
        yaml.dump(config, file, default_flow_style=False)

# Example Usage
add_namespace("test.yaml", "robot1")
