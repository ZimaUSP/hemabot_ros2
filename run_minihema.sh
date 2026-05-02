#!/bin/bash

colcon build
source install/setup.bash
ros2 launch minihema_launch minihema_launch.py
