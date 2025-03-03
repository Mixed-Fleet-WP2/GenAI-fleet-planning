class MqttPayload():

    def __init__(self, type:str, action_id:int, payload={}):
        self.type = type
        self.payload = payload
        self.action_id = action_id

    def __str__(self):
        return f"""{{
            "type": {self.type},
            "action_id": {self.action_id},
            "payload": {self.payload}
        }}"""