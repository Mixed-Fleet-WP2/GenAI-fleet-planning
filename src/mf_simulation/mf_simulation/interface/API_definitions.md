# Gazebo simulation api definitions

## Available robot types:
- drone
- forklift

## MQTT endpoint

/plan

## Format

The endpoint accepts an array of json objects (i.e. actions) that follow
the format below

## Action template (shared for all actions)

- executing_robot: string (the robot name of the form robot_{id}, 1 is smallest id)
- action_id: int (id of this actions, starts from 1)
- prerequisites: list[int]  
(list of action ids that must complete before this action can be fired, can be empty if no preconditions)
- command_arguments: object (key value pairs of arguments and the values)
- command: string (the action to execute)

## Drone actions

### move
- x: float
- y: float
- z: float
- roll: float (degrees)
- pitch: float (degrees)
- yaw: float (degrees)

### search
- No params, provide an empty object {}

## Forklift actions

### move

- x: float
- y: float
- z: float (not used but required)
- roll: float (not used but required, degrees)
- pitch: float (not used but required, degrees)
- yaw: float (degrees)

### pick_up

- object: string

### drop

- object: string
(should this also have a location param or is it always dropped directly to front?)

### move_fork

- position: float (0.0 - 2.0)

## Example:
```
[
    {
        "executing_robot": "drone_1",
        "command": "search",
        "command_arguments": {},
        "action_id": 2,
        "prerequisites": []
    },
    {
        "executing_robot": "forklift_1",
        "command": "move",
        "command_arguments": {
            "x": 1.0,
            "y": 2.0,
            "z" : 0.0,
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0
        },
        "action_id": 2,
        "prerequisites": [1]
    }

]
```