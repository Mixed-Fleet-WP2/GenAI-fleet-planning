import json

class MqttPayload():

    def __init__(self, type:str, action_id:int, payload={}):
        self.type = type
        self.payload = payload
        self.action_id = action_id

        self.msg = {}

        self.msg['type'] = type
        self.msg['action_id'] = action_id
        self.msg['payload'] = payload

    def __str__(self):
        return json.dumps(self.msg)