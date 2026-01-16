#!/bin/bash
source /opt/ros/humble/setup.bash
source /home/metin/itu_robotics_ws/itu_project_ws/install/setup.bash
export TURTLEBOT3_MODEL=waffle_pi
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/home/metin/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models

echo "Launching Simulation..."
ros2 launch simulation_pkg simulation.launch.py
