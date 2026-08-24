#!/bin/bash
set -euo pipefail

usage='usage: smoke-image.sh IMAGE ROS_DISTRO ROS_VARIANT UBUNTU_VERSION UBUNTU_CODENAME CUDA_VERSION CUDA_TYPE BASE_IMAGE'
image=${1:?${usage}}
ros_distro=${2:?${usage}}
ros_variant=${3:?${usage}}
ubuntu_version=${4:?${usage}}
ubuntu_codename=${5:?${usage}}
cuda_version=${6:?${usage}}
cuda_type=${7:?${usage}}
base_image=${8:?${usage}}

docker run --rm \
  -e EXPECTED_CUDA_VERSION="${cuda_version}" \
  -e EXPECTED_ROS_DISTRO="${ros_distro}" \
  -e EXPECTED_ROS_VARIANT="${ros_variant}" \
  -e EXPECTED_UBUNTU_CODENAME="${ubuntu_codename}" \
  -e EXPECTED_UBUNTU_VERSION="${ubuntu_version}" \
  "${image}" bash -c '
  . /etc/os-release
  test "${VERSION_ID}" = "${EXPECTED_UBUNTU_VERSION}"
  test "${VERSION_CODENAME}" = "${EXPECTED_UBUNTU_CODENAME}"
  test "${ROS_DISTRO}" = "${EXPECTED_ROS_DISTRO}"
  test "${ROS_VARIANT}" = "${EXPECTED_ROS_VARIANT}"
  test "${CUDA_VERSION}" = "${EXPECTED_CUDA_VERSION}"
  ros2 --help >/dev/null
'

test "$(docker image inspect "${image}" --format '{{json .Config.Entrypoint}}')" = \
  '["/opt/nvidia/nvidia_entrypoint.sh"]'

for label in \
  org.opencontainers.image.base.name="${base_image}" \
  io.github.shkwon98.ros.distro="${ros_distro}" \
  io.github.shkwon98.ros.variant="${ros_variant}" \
  io.github.shkwon98.ubuntu.version="${ubuntu_version}" \
  io.github.shkwon98.ubuntu.codename="${ubuntu_codename}" \
  io.github.shkwon98.cuda.version="${cuda_version}" \
  io.github.shkwon98.cuda.type="${cuda_type}"
do
  key=${label%%=*}
  expected=${label#*=}
  actual=$(docker image inspect "${image}" --format "{{index .Config.Labels \"${key}\"}}")
  test "${actual}" = "${expected}"
done

if [[ "${ros_variant}" == "ros-base" ]]; then
  docker run --rm "${image}" rosdep --version >/dev/null
  docker run --rm "${image}" colcon --help >/dev/null
fi
