#!/bin/bash

# How to read a file and redirect it to a variable in bash
# https://stackoverflow.com/questions/4749905/how-can-i-read-a-file-and-redirect-it-to-a-variable

plan=$(cat ./plan.json)

# Publish the plan to the MQTT topic
mosquitto_pub -h 2883 -t "/plan" -m "$plan"
