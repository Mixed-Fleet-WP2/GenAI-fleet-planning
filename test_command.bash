# !/bin/bash

# Source - https://stackoverflow.com/a/2013573
# Posted by miku, modified by community. See post 'Timeline' for change history
# Retrieved 2026-05-02, License - CC BY-SA 4.0

HOST="${1:-localhost}"
PORT="${2:-1883}"
echo "Publishing test command to MQTT broker at ${HOST}:${PORT}..."
mosquitto_pub -h ${HOST} -p ${PORT} \
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