import argparse
import json
from pathlib import Path


REQUIRED_FIELDS = {
    "platforms",
    "ros_apt_source_package",
    "ros_apt_source_sha256",
    "ros_apt_source_version",
    "ros_distro",
    "ubuntu_codename",
    "ubuntu_version",
}
REQUIRED_PLATFORMS = ("linux/amd64", "linux/arm64")
REQUIRED_PLATFORM_FIELDS = {"base_image", "cuda_version"}
ROS_VARIANTS = ("ros-core", "ros-base")
SUPPORTED_ROS_APT_SOURCE_PACKAGES = {
    "ros2-apt-source",
    "ros2-testing-apt-source",
}
SUPPORTED_BASE_IMAGE_PREFIXES = {
    "linux/amd64": ("nvcr.io/nvidia/cuda:",),
    "linux/arm64": (
        "nvcr.io/nvidia/cuda:",
        "nvcr.io/nvidia/l4t-cuda:",
    ),
}


def expand(document: object) -> dict[str, list[dict[str, object]]]:
    images = document.get("images") if isinstance(document, dict) else None
    if not isinstance(images, list) or not images:
        raise ValueError("images must be a non-empty list")

    builds = []
    manifests = []
    tags = set()

    for index, image in enumerate(images):
        if not isinstance(image, dict):
            raise ValueError(f"images[{index}] must be an object")

        fields = set(image)
        missing = REQUIRED_FIELDS - fields
        unexpected = fields - REQUIRED_FIELDS
        if missing or unexpected:
            problems = sorted(missing | unexpected)
            raise ValueError(f"images[{index}] has invalid fields: {', '.join(problems)}")

        platforms = image["platforms"]
        if not isinstance(platforms, dict) or set(platforms) != set(
            REQUIRED_PLATFORMS
        ):
            raise ValueError("platforms must contain linux/amd64 and linux/arm64")

        for platform in REQUIRED_PLATFORMS:
            platform_config = platforms[platform]
            if not isinstance(platform_config, dict):
                raise ValueError(f"{platform} configuration must be an object")

            platform_fields = set(platform_config)
            missing_platform_fields = REQUIRED_PLATFORM_FIELDS - platform_fields
            unexpected_platform_fields = platform_fields - REQUIRED_PLATFORM_FIELDS
            if missing_platform_fields or unexpected_platform_fields:
                problems = sorted(
                    missing_platform_fields | unexpected_platform_fields
                )
                raise ValueError(
                    f"{platform} has invalid fields: {', '.join(problems)}"
                )

            base_image = platform_config["base_image"]
            allowed_prefixes = SUPPORTED_BASE_IMAGE_PREFIXES[platform]
            if not isinstance(base_image, str) or not base_image.startswith(
                allowed_prefixes
            ):
                raise ValueError(f"unsupported base image for {platform}: {base_image}")

            cuda_version = platform_config["cuda_version"]
            if not isinstance(cuda_version, str) or not cuda_version:
                raise ValueError(f"invalid cuda_version for {platform}")

        apt_source_package = image["ros_apt_source_package"]
        if apt_source_package not in SUPPORTED_ROS_APT_SOURCE_PACKAGES:
            raise ValueError(f"unsupported ROS apt source package: {apt_source_package}")

        for variant in ROS_VARIANTS:
            tag = f'{image["ros_distro"]}-{variant}'
            if tag in tags:
                raise ValueError(f"duplicate tag: {tag}")
            tags.add(tag)

            manifest = dict(image)
            manifest.update(
                {
                    "ros_variant": variant,
                    "tag": tag,
                    "os_tag": f'{tag}-{image["ubuntu_codename"]}',
                }
            )
            manifests.append(manifest)

            shared = {
                key: value
                for key, value in image.items()
                if key != "platforms"
            }
            for platform in REQUIRED_PLATFORMS:
                build = dict(shared)
                build.update(platforms[platform])
                build.update(
                    {
                        "platform": platform,
                        "platform_slug": platform.replace("/", "-"),
                        "ros_variant": variant,
                        "tag": tag,
                        "os_tag": f'{tag}-{image["ubuntu_codename"]}',
                    }
                )
                builds.append(build)

    return {
        "builds": {"include": builds},
        "manifests": {"include": manifests},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and expand the image allowlist")
    parser.add_argument("images", type=Path)
    arguments = parser.parse_args()

    try:
        document = json.loads(arguments.images.read_text())
        matrix = expand(document)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    print(json.dumps(matrix, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
