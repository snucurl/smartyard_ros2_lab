#!/usr/bin/env bash
# Source this file in EVERY new Ubuntu terminal: source scripts/env.sh 31
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo 'Use: source scripts/env.sh 31' >&2
  exit 1
fi
_yard_domain="${1:-31}"
if [[ ! "$_yard_domain" =~ ^[0-9]{1,3}$ ]] || ((10#$_yard_domain > 101)); then
  echo 'Domain must be 0..101' >&2
  return 1
fi
export ROS_DOMAIN_ID="$((10#$_yard_domain))"
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
_yard_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
if [[ -f "$_yard_root/install/setup.bash" ]]; then
  source "$_yard_root/install/setup.bash"
else
  echo 'Overlay not built yet. Run colcon build --symlink-install in the workspace.'
fi
printf 'ROS=%s DOMAIN=%s LOCALHOST=%s RMW=%s\n' "$ROS_DISTRO" "$ROS_DOMAIN_ID" "$ROS_LOCALHOST_ONLY" "$RMW_IMPLEMENTATION"
unset _yard_domain _yard_root
