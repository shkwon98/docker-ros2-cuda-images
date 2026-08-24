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
README_TABLE_START = "<!-- BEGIN GENERATED CONFIGURATIONS -->"
README_TABLE_END = "<!-- END GENERATED CONFIGURATIONS -->"
ROS_ARTWORK = {
    "humble": (
        "Humble Hawksbill",
        "https://docs.ros.org/en/humble/Releases/Release-Humble-Hawksbill.html",
        "https://raw.githubusercontent.com/ros2/ros2_documentation/a74c8f1ddc1dafaf144998dc793ffca0c3d5a5fc/source/Get-Started/Releases/humble-small.png",
    ),
    "jazzy": (
        "Jazzy Jalisco",
        "https://docs.ros.org/en/jazzy/Releases/Release-Jazzy-Jalisco.html",
        "https://raw.githubusercontent.com/ros2/ros2_documentation/a74c8f1ddc1dafaf144998dc793ffca0c3d5a5fc/source/Get-Started/Releases/jazzy-small.png",
    ),
    "kilted": (
        "Kilted Kaiju",
        "https://docs.ros.org/en/kilted/Releases/Release-Kilted-Kaiju.html",
        "https://raw.githubusercontent.com/ros2/ros2_documentation/a74c8f1ddc1dafaf144998dc793ffca0c3d5a5fc/source/Get-Started/Releases/kilted-small.png",
    ),
    "lyrical": (
        "Lyrical Luth",
        "https://docs.ros.org/en/rolling/Releases/Release-Lyrical-Luth.html",
        "https://raw.githubusercontent.com/ros2/ros2_documentation/a74c8f1ddc1dafaf144998dc793ffca0c3d5a5fc/source/Get-Started/Releases/lyrical-small.png",
    ),
    "rolling": (
        "Rolling Ridley",
        "https://docs.ros.org/en/rolling/Releases/Release-Rolling-Ridley.html",
        "https://raw.githubusercontent.com/ros2/ros2_documentation/a74c8f1ddc1dafaf144998dc793ffca0c3d5a5fc/source/Get-Started/Releases/rolling-small.png",
    ),
}
ARM64_IMAGE_STATUS = {
    "humble": "Available · JetPack 6",
    "jazzy": "Available · JetPack 7",
    "kilted": "Available · JetPack 7",
    "lyrical": "Preview³",
    "rolling": "Preview³",
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


def render_readme_table(document: object) -> str:
    expand(document)
    images = document["images"]
    lines = [
        README_TABLE_START,
        "| ROS 2 | Ubuntu | CUDA | `amd64` image | `arm64` image |",
        "| :---: | --- | --- | :---: | :---: |",
    ]

    for image in images:
        ros_distro = image["ros_distro"]
        artwork_name, release_url, artwork_url = ROS_ARTWORK[ros_distro]
        ros_label = ros_distro.capitalize() + ("¹" if ros_distro == "rolling" else "")
        ros_cell = (
            f'<a href="{release_url}"><img src="{artwork_url}" height="48" '
            f'alt="{artwork_name} artwork"></a><br>{ros_label}'
        )
        platforms = image["platforms"]
        amd64 = platforms["linux/amd64"]
        arm64 = platforms["linux/arm64"]
        amd64_cuda = amd64["cuda_version"]
        arm64_cuda = arm64["cuda_version"]
        cuda_version = (
            amd64_cuda
            if amd64_cuda == arm64_cuda
            else f"{amd64_cuda} / {arm64_cuda}²"
        )
        lines.append(
            "| {ros} | {ubuntu_version} {ubuntu_codename} | "
            "{cuda_version} | Available | {arm64_status} |".format(
                ros=ros_cell,
                ubuntu_version=image["ubuntu_version"],
                ubuntu_codename=image["ubuntu_codename"].capitalize(),
                cuda_version=cuda_version,
                arm64_status=ARM64_IMAGE_STATUS[ros_distro],
            )
        )

    notes = []
    if any(image["ros_distro"] == "rolling" for image in images):
        notes.append(
            "1. Rolling images use packages from the official ROS testing "
            "repository."
        )
    humble = next(
        (image for image in images if image["ros_distro"] == "humble"), None
    )
    if humble is not None:
        amd64_cuda = humble["platforms"]["linux/amd64"]["cuda_version"]
        arm64_cuda = humble["platforms"]["linux/arm64"]["cuda_version"]
        if amd64_cuda != arm64_cuda:
            notes.append(
                f"2. Humble uses CUDA {amd64_cuda} on `amd64` and the "
                f"Jetson-specific L4T CUDA {arm64_cuda} runtime on `arm64`."
            )
    if any(
        ARM64_IMAGE_STATUS[image["ros_distro"]] == "Preview³" for image in images
    ):
        notes.append(
            "3. The `arm64` image is available, but no matching JetPack "
            "release exists and Jetson is not currently supported."
        )
    if notes:
        lines.extend(["", *notes])

    lines.append(README_TABLE_END)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and expand the image allowlist")
    parser.add_argument(
        "--readme-table",
        action="store_true",
        help="print the generated README configuration table",
    )
    parser.add_argument("images", type=Path)
    arguments = parser.parse_args()

    try:
        document = json.loads(arguments.images.read_text())
        output = (
            render_readme_table(document)
            if arguments.readme_table
            else json.dumps(expand(document), separators=(",", ":"))
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    print(output, end="" if arguments.readme_table else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
