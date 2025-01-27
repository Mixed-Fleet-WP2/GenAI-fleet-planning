import json

"""
/**/*:
  ros__parameters:
    broker:
      host: 0.0.0.0
      port: 1883
    bridge:
      ros2mqtt:
        ros_topics: 
          - /ping/ros
        /ping/ros:
          mqtt_topic: pingpong/ros
      mqtt2ros:
        mqtt_topics: 
          - pingpong/ros
        pingpong/ros:
          ros_topic: /pong/ros

  
"""
def main():
    filename = './bridge_params.json'
    namespace = 'forklift'
    params = rewrite_config()
    return params

"""
def rewrite_config(file_path, namespaces):

    abilities = ['move', 'pick_up', 'drop', 'pong', 'ping']
    
    with open(file_path, 'r') as f:
        data = json.load(f)

        for namespace in namespaces:

            #Add the capablities of the robot
            ros_to_mqtt = data['mqtt_client']['ros__parameters']['bridge']['ros2mqtt']
            mqtt_to_ros = data['mqtt_client']['ros__parameters']['bridge']['mqtt2ros']

            ros_topic_names = ros_to_mqtt['ros_topics']
            mqtt_topic_names = mqtt_to_ros['mqtt_topics']

            #Add the topics to the ros2mqtt and mqtt2ros bridges
            for ability in abilities:
                ros_topic_names.append(f'/{namespace}/{ability}')
                mqtt_topic_names.append(f'/{namespace}/{ability}')

                ros_to_mqtt[f'/{namespace}/{ability}'] = {'mqtt_topic': f'{namespace}/{ability}'}
                mqtt_to_ros[f'{namespace}/{ability}'] = {'ros_topic': f'/{namespace}/{ability}'}
    
    return data
"""

def rewrite_config():

    #Namespaces are added automatically by ros2
    mqtt_topics = ['move', 'pick_up', 'drop', 'ping', 'pong']

    mqtt_to_ros = []
    ros_to_mqtt = []

    for topic in mqtt_topics:
        mqtt_to_ros.append({
            "mqtt_topic": topic,
            "ros_topic": f"/{topic}"
        })

        ros_to_mqtt.append({
            "ros_topic": f"/{topic}",
            "mqtt_topic": topic
        })
    
    param_overrides = {
        'mqtt2ros': mqtt_to_ros,
        'ros2mqtt': ros_to_mqtt
    }
    print(param_overrides)
    return param_overrides

if __name__ == '__main__':
    main()