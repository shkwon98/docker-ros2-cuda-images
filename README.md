<div align="center">

<h1>ROS 2 CUDA Container Images</h1>

<p><strong>Multi-architecture ROS 2 containers with CUDA support for NVIDIA GPUs and Jetson.</strong></p>

<p>
  <a href="https://github.com/shkwon98/docker-ros2-cuda-images/actions/workflows/build.yml"><img alt="Build status" src="https://github.com/shkwon98/docker-ros2-cuda-images/actions/workflows/build.yml/badge.svg"></a>
  <a href="#supported-configurations"><img alt="ROS 2" src="https://img.shields.io/badge/ROS%202-supported-22314E?logo=ros&logoColor=white"></a>
  <a href="#supported-configurations"><img alt="CUDA" src="https://img.shields.io/badge/CUDA-enabled-76B900?logo=nvidia&logoColor=white"></a>
  <a href="#platform-support"><img alt="Platforms" src="https://img.shields.io/badge/platform-linux%2Famd64%20%7C%20linux%2Farm64-0078D4?logo=linux&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-D22128"></a>
</p>

<p>
  <a href="#quick-start">Quick start</a> ·
  <a href="#supported-configurations">Images</a> ·
  <a href="#image-variants">Variants</a> ·
  <a href="#platform-support">Platforms</a> ·
  <a href="#tags-and-reproducibility">Tags</a>
</p>

</div>

---

Every multi-platform tag provides the same Ubuntu release and ROS 2 distribution on both architectures.

| Registry | Architectures | Image variants |
| :--- | :--- | :--- |
| `ghcr.io/shkwon98/ros2-cuda` | `linux/amd64`, `linux/arm64` | `ros-core`, `ros-base` |

> [!IMPORTANT]
> This is a community project. It is not an official NVIDIA or ROS image.

## Quick start

### Prerequisites

- Docker Engine
- A compatible NVIDIA driver or JetPack installation
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

Pull an image:

```bash
docker pull ghcr.io/shkwon98/ros2-cuda:jazzy-ros-base
```

Run on a system with an NVIDIA discrete GPU:

```bash
docker run --rm -it --gpus all \
  ghcr.io/shkwon98/ros2-cuda:jazzy-ros-base
```

Run on Jetson:

```bash
docker run --rm -it --runtime=nvidia \
  ghcr.io/shkwon98/ros2-cuda:jazzy-ros-base
```

ROS is sourced automatically when the container starts.

## Supported configurations

| ROS 2 | Ubuntu | CUDA | `amd64` | `arm64` | Image tags |
| --- | --- | --- | --- | --- | --- |
| Humble | 22.04 Jammy | 12.6 | Available | JetPack 6 target | `humble-ros-core`, `humble-ros-base` |
| Jazzy | 24.04 Noble | 13.2.1 | Available | JetPack 7 target | `jazzy-ros-core`, `jazzy-ros-base` |
| Kilted | 24.04 Noble | 13.2.1 | Available | JetPack 7 target | `kilted-ros-core`, `kilted-ros-base` |
| Lyrical | 26.04 Resolute | 13.3.1 | Available | Preview¹ | `lyrical-ros-core`, `lyrical-ros-base` |
| Rolling | 26.04 Resolute | 13.3.1 | Available | Preview¹ | `rolling-ros-core`, `rolling-ros-base` |

1. The `arm64` image is available, but no matching JetPack release exists and Jetson is not currently supported.

Humble uses CUDA 12.6.3 on `amd64` and L4T CUDA 12.6.11 on `arm64`; both belong to the CUDA 12.6 compatibility family. Rolling images use packages from the official ROS testing repository.

## Image variants

| Variant | Intended use | Additional tools |
| --- | --- | --- |
| `ros-core` | Minimal ROS 2 runtime | ROS core packages only |
| `ros-base` | Development and general ROS 2 workloads | rosdep, vcstool, colcon extensions, build tools, and Git |

## Platform support

### NVIDIA discrete GPUs

The `linux/amd64` images use NVIDIA CUDA runtime bases and run with the NVIDIA Container Toolkit.

### NVIDIA Jetson

Humble targets JetPack 6 using the Jetson/L4T CUDA runtime. Jazzy and Kilted target the CUDA compute environment provided by JetPack 7.

Lyrical and Rolling `arm64` images are published for future compatibility. They are not currently supported on Jetson because no matching JetPack release is available.

Jetson-specific multimedia and SDK components are outside the scope of these images.

## Tags and reproducibility

Each image is published with a short tag and an OS-qualified alias. For example:

```text
jazzy-ros-base
jazzy-ros-base-noble
```

Both tags point to the same multi-platform image. Tags may be updated when their base image or ROS packages change. Pin the published image digest when exact reproducibility is required.

## License

This repository is licensed under the Apache License 2.0. NVIDIA CUDA container contents and ROS packages remain subject to their respective licenses.
