#!/usr/bin/env bash
# Run in Ubuntu 22.04, not PowerShell. Review before running.
set -euo pipefail
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 22.04 ]] || {
  echo 'This course targets Ubuntu 22.04 only.' >&2; exit 1;
}
sudo apt update
sudo apt install -y locales curl software-properties-common git unzip python3
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository -y universe
YARD_APT_VERSION="$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | python3 -c 'import sys,json; print(json.load(sys.stdin)["tag_name"])')"
YARD_APT_DEB="$(mktemp --suffix=.deb)"
trap 'rm -f -- "$YARD_APT_DEB"' EXIT
curl -fL "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${YARD_APT_VERSION}/ros2-apt-source_${YARD_APT_VERSION}.${UBUNTU_CODENAME}_all.deb" -o "$YARD_APT_DEB"
sudo dpkg -i "$YARD_APT_DEB"
sudo apt update
sudo apt upgrade -y
sudo apt install -y ros-humble-desktop ros-humble-rmw-fastrtps-cpp \
  python3-colcon-common-extensions python3-rosdep python3-pytest
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
rosdep update
printf '\nInstalled. In a new terminal: source /opt/ros/humble/setup.bash\n'
