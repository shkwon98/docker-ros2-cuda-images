# syntax=docker/dockerfile:1
# check=skip=InvalidDefaultArgInFrom,InvalidBaseImagePlatform;error=true

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG BASE_IMAGE
ARG BUILD_DATE=1970-01-01T00:00:00Z
ARG CUDA_TYPE
ARG EXPECTED_CUDA_VERSION
ARG EXPECTED_UBUNTU_VERSION
ARG ROS_APT_SOURCE_PACKAGE
ARG ROS_APT_SOURCE_SHA256
ARG ROS_APT_SOURCE_VERSION
ARG ROS_DISTRO
ARG ROS_VARIANT
ARG UBUNTU_CODENAME
ARG VCS_REF=unknown

LABEL org.opencontainers.image.base.name="${BASE_IMAGE}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.description="ROS 2 on an official NVIDIA CUDA base" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/shkwon98/docker-ros2-cuda-images" \
      org.opencontainers.image.title="ROS 2 CUDA" \
      io.github.shkwon98.cuda.type="${CUDA_TYPE}" \
      io.github.shkwon98.cuda.version="${EXPECTED_CUDA_VERSION}" \
      io.github.shkwon98.ros.distro="${ROS_DISTRO}" \
      io.github.shkwon98.ros.variant="${ROS_VARIANT}" \
      io.github.shkwon98.ubuntu.codename="${UBUNTU_CODENAME}" \
      io.github.shkwon98.ubuntu.version="${EXPECTED_UBUNTU_VERSION}"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    ROS_DISTRO=${ROS_DISTRO} \
    ROS_VARIANT=${ROS_VARIANT}

RUN set -eux; \
    test -n "${BASE_IMAGE}"; \
    test -n "${EXPECTED_CUDA_VERSION}"; \
    test -n "${EXPECTED_UBUNTU_VERSION}"; \
    test -n "${ROS_DISTRO}"; \
    test -n "${ROS_APT_SOURCE_PACKAGE}"; \
    test -n "${ROS_VARIANT}"; \
    test -n "${UBUNTU_CODENAME}"; \
    test "${CUDA_VERSION}" = "${EXPECTED_CUDA_VERSION}"; \
    source /etc/os-release; \
    test "${VERSION_ID}" = "${EXPECTED_UBUNTU_VERSION}"; \
    test "${VERSION_CODENAME}" = "${UBUNTU_CODENAME}"; \
    [[ "${ROS_VARIANT}" == "ros-core" || "${ROS_VARIANT}" == "ros-base" ]]

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl; \
    ros_apt_source=/tmp/ros2-apt-source.deb; \
    curl -fsSL \
      -o "${ros_apt_source}" \
      "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/${ROS_APT_SOURCE_PACKAGE}_${ROS_APT_SOURCE_VERSION}.${UBUNTU_CODENAME}_all.deb"; \
    echo "${ROS_APT_SOURCE_SHA256}  ${ros_apt_source}" | sha256sum --strict --check; \
    apt-get install -y --no-install-recommends "${ros_apt_source}"; \
    rm -f "${ros_apt_source}"; \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    packages=("ros-${ROS_DISTRO}-${ROS_VARIANT}"); \
    if [[ "${ROS_VARIANT}" == "ros-base" ]]; then \
      packages+=( \
        build-essential \
        git \
        python3-colcon-common-extensions \
        python3-colcon-mixin \
        python3-rosdep \
        python3-vcstool \
      ); \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends "${packages[@]}"; \
    rm -rf /var/lib/apt/lists/*; \
    if [[ "${ROS_VARIANT}" == "ros-base" ]]; then \
      rosdep init; \
      rosdep update --rosdistro "${ROS_DISTRO}"; \
      colcon mixin add default \
        https://raw.githubusercontent.com/colcon/colcon-mixin-repository/master/index.yaml; \
      colcon mixin update; \
      colcon metadata add default \
        https://raw.githubusercontent.com/colcon/colcon-metadata-repository/master/index.yaml; \
      colcon metadata update; \
    fi; \
    set +u; \
    source "/opt/ros/${ROS_DISTRO}/setup.bash"; \
    set -u; \
    ros2 --help >/dev/null

COPY --chmod=755 ros_entrypoint.sh /opt/nvidia/entrypoint.d/99-ros.sh

CMD ["bash"]
