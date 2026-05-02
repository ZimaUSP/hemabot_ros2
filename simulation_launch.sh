#!/bin/bash

colcon build
source install/setup.bash
ros2 launch d_hospital_gazebo2 hospital.py use_sim_time:=true
