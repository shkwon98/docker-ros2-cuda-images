import argparse
import hashlib
import json
import re
import subprocess
import urllib.request
from pathlib import Path

from scripts.matrix import REQUIRED_PLATFORMS, expand


EXPECTED_PLATFORMS = set(REQUIRED_PLATFORMS)
ENTRYPOINT = ["/opt/nvidia/nvidia_entrypoint.sh"]
SMOKE_TEST = """import subprocess
import rclpy
subprocess.run(["ros2", "--help"], check=True, stdout=subprocess.DEVNULL)
rclpy.init()
node = rclpy.create_node("container_smoke_test")
node.destroy_node()
rclpy.shutdown()
"""


def inspect_image(reference: str) -> dict:
    print(f"Checking {reference}", flush=True)
    return json.loads(subprocess.check_output(
        ["docker", "buildx", "imagetools", "inspect", "--format", "{{json .Image}}", reference],
        text=True,
    ))


def config_for_platform(image: object, expected_platform: str) -> dict:
    if not isinstance(image, dict):
        raise ValueError("image inspection must be an object")
    if "architecture" in image:
        actual = f'{image.get("os")}/{image.get("architecture")}'
        if actual != expected_platform:
            raise ValueError(f"image platform {actual} != {expected_platform}")
        config = image.get("config")
    else:
        if expected_platform not in image:
            raise ValueError(f"missing platform {expected_platform}")
        config = image[expected_platform].get("config")
    if not isinstance(config, dict):
        raise ValueError("image config is missing")
    return config


def verify_platform_image(image: object, platform: str, labels: dict[str, str]) -> None:
    config = config_for_platform(image, platform)
    if config.get("Entrypoint") != ENTRYPOINT:
        raise ValueError(f'Entrypoint {config.get("Entrypoint")} != {ENTRYPOINT}')
    actual_labels = config.get("Labels") or {}
    for key, expected in labels.items():
        if actual_labels.get(key) != expected:
            raise ValueError(f"{key} {actual_labels.get(key)!r} != {expected!r}")


def verify_manifest_platforms(image: object) -> None:
    if not isinstance(image, dict):
        raise ValueError("manifest inspection must be an object")
    if "architecture" in image:
        platforms = {f'{image.get("os")}/{image["architecture"]}'}
    else:
        platforms = set(image)
    if platforms != EXPECTED_PLATFORMS:
        raise ValueError(f"manifest platforms {sorted(platforms)} != {sorted(EXPECTED_PLATFORMS)}")


def repositories(owner: str) -> list[str]:
    return [f"{registry}/{owner.lower()}/ros2-cuda" for registry in ("ghcr.io", "docker.io")]


def publish(image: dict, digest: str, owner: str, revision: str) -> None:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("builder did not return a valid image digest")
    repos = repositories(owner)
    # Inspect both registries before changing either registry's public tags.
    for repo in repos:
        inspection = inspect_image(f"{repo}@{digest}")
        verify_manifest_platforms(inspection)
        for platform in REQUIRED_PLATFORMS:
            config = image["platforms"][platform]
            verify_platform_image(inspection, platform, {
                "org.opencontainers.image.base.name": config["base_image"],
                "org.opencontainers.image.revision": revision,
                "io.github.shkwon98.cuda.version": config["cuda_version"],
                "io.github.shkwon98.ubuntu.version": image["ubuntu_version"],
                "io.github.shkwon98.ubuntu.codename": image["ubuntu_codename"],
                "io.github.shkwon98.ros.distro": image["ros_distro"],
                "io.github.shkwon98.ros.variant": image["ros_variant"],
            })
    for platform in REQUIRED_PLATFORMS:
        subprocess.run([
            "docker", "run", "--rm", "--pull=always", "--platform", platform,
            f"{repos[0]}@{digest}", "python3", "-c", SMOKE_TEST,
        ], check=True)
    for repo in repos:
        subprocess.run([
            "docker", "buildx", "imagetools", "create",
            "--tag", f'{repo}:{image["tag"]}',
            "--tag", f'{repo}:{image["os_tag"]}', f"{repo}@{digest}",
        ], check=True)
        verify_manifest_platforms(inspect_image(f'{repo}:{image["tag"]}'))


def check_compatibility(document: dict, owner: str) -> None:
    images = expand(document)["include"]
    bases = {}
    packages = set()
    for image in document["images"]:
        for platform, config in image["platforms"].items():
            base = config["base_image"]
            if base not in bases:
                bases[base] = inspect_image(base)
            environment = config_for_platform(bases[base], platform).get("Env", [])
            if f'CUDA_VERSION={config["cuda_version"]}' not in environment:
                raise ValueError(f"unexpected CUDA version in {base} ({platform})")
        packages.add((
            image["ros_apt_source_package"], image["ros_apt_source_version"],
            image["ubuntu_codename"], image["ros_apt_source_sha256"],
        ))
    for package, version, codename, checksum in sorted(packages):
        url = ("https://github.com/ros-infrastructure/ros-apt-source/releases/download/"
               f"{version}/{package}_{version}.{codename}_all.deb")
        print(f"Checking {url}", flush=True)
        with urllib.request.urlopen(url, timeout=60) as response:
            actual = hashlib.sha256(response.read()).hexdigest()
        if actual != checksum:
            raise ValueError(f"SHA256 mismatch for {url}: {actual} != {checksum}")
    for repo in repositories(owner):
        for image in images:
            verify_manifest_platforms(inspect_image(f'{repo}:{image["tag"]}'))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check ROS images and promote tested builds")
    commands = parser.add_subparsers(dest="command", required=True)
    promotion = commands.add_parser("publish")
    promotion.add_argument("--config", type=json.loads, required=True)
    promotion.add_argument("--digest", required=True)
    promotion.add_argument("--owner", required=True)
    promotion.add_argument("--revision", required=True)
    compatibility = commands.add_parser("compatibility")
    compatibility.add_argument("configuration", type=Path)
    compatibility.add_argument("--owner", required=True)
    arguments = parser.parse_args()
    try:
        if arguments.command == "publish":
            publish(arguments.config, arguments.digest, arguments.owner, arguments.revision)
        else:
            check_compatibility(json.loads(arguments.configuration.read_text()), arguments.owner)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
