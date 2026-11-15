#!/usr/bin/env bash
set -eu
printf '=== Ubuntu ===\n'
cat /etc/os-release
printf '\n=== ROS ===\n'
printenv ROS_DISTRO ROS_DOMAIN_ID ROS_LOCALHOST_ONLY RMW_IMPLEMENTATION || true
python3 --version
ros2 pkg prefix smartyard_lab
ros2 interface show smartyard_interfaces/action/TransportBlock
printf '\n=== Network ===\n'
ip -brief address
ip route
printf '\n=== Nodes ===\n'
ros2 node list
printf '\n=== Sensor endpoints ===\n'
ros2 topic info /yard01/sensor_state --verbose
