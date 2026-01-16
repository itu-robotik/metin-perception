    #!/bin/bash
source /opt/ros/humble/setup.bash
source /home/metin/itu_robotics_ws/itu_project_ws/install/setup.bash
export TURTLEBOT3_MODEL=waffle_pi
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/home/metin/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models

# Cleanup
pkill -f patrol_node
pkill -f gemini_node
pkill -f planner_node
pkill -f ign

# 1. Launch Simulation (Background)
echo "Starting Simulation..."
ros2 launch simulation_pkg simulation.launch.py &
SIM_PID=$!
sleep 10

# 2. Launch Perception (Background)
echo "Starting Perception Node..."
ros2 run perception_pkg gemini_node &
PERCEPTION_PID=$!
sleep 5

# 3. Launch Patrol (Background)
echo "Starting Patrol Node..."
ros2 run simulation_pkg patrol_node.py &
PATROL_PID=$!
sleep 2

# 4. Launch Planner (Background)
echo "Starting Planner Node..."
ros2 run simulation_pkg planner_node.py &
PLANNER_PID=$!

echo "System running. Waiting for docking..."
# Keep running for 60 seconds to observe
sleep 60

# Cleanup
echo "Stopping system..."
kill $PATROL_PID
kill $PERCEPTION_PID
kill $PLANNER_PID
kill $SIM_PID
pkill -f ign
