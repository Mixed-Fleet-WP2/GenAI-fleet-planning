# !/bin/bash
mosquitto_pub -h localhost -p 2883 \
-t drone_1/move \
-m "$(cat <<EOF
{
  "executing_robot": "drone_1",
  "command": "move",
  "command_arguments": {
    "destination": {
      "X": 1,
      "Y": 2,
      "Z": 1,
      "roll": 0,
      "pitch": 0,
      "yaw": 0
    }
  },
  "action_id": 1,
  "prerequisites": []
}
EOF
)"