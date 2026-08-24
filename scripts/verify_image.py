import argparse
import json
import re
from pathlib import Path


EXPECTED_PLATFORMS = {"linux/amd64", "linux/arm64"}
DIGEST_FILE = re.compile(r"^(linux-(?:amd64|arm64))-([0-9a-f]{64})$")
ENTRYPOINT = ["/opt/nvidia/nvidia_entrypoint.sh"]


def collect_digests(directory: Path) -> dict[str, str]:
    digests = {}
    for path in sorted(directory.iterdir()):
        match = DIGEST_FILE.fullmatch(path.name)
        if not path.is_file() or match is None:
            raise ValueError(f"invalid digest file: {path.name}")

        platform = match.group(1).replace("-", "/", 1)
        if platform in digests:
            raise ValueError(f"duplicate digest for {platform}")
        digests[platform] = f"sha256:{match.group(2)}"

    if set(digests) != EXPECTED_PLATFORMS:
        raise ValueError(
            f"digest platforms {sorted(digests)} != {sorted(EXPECTED_PLATFORMS)}"
        )
    if len(set(digests.values())) != len(digests):
        raise ValueError("platform digests must be unique")
    return digests


def config_for_platform(image: object, expected_platform: str) -> dict:
    if not isinstance(image, dict):
        raise ValueError("image inspection must be an object")

    if "architecture" in image:
        actual_platform = f'{image.get("os")}/{image.get("architecture")}'
        if actual_platform != expected_platform:
            raise ValueError(
                f"image platform {actual_platform} != {expected_platform}"
            )
        config = image.get("config")
    else:
        if set(image) != {expected_platform}:
            raise ValueError(
                f"image platforms {sorted(image)} != [{expected_platform}]"
            )
        config = image[expected_platform].get("config")

    if not isinstance(config, dict):
        raise ValueError("image config is missing")
    return config


def verify_platform_image(
    image: object,
    expected_platform: str,
    expected_labels: dict[str, str],
) -> None:
    config = config_for_platform(image, expected_platform)
    if config.get("Entrypoint") != ENTRYPOINT:
        raise ValueError(f'Entrypoint {config.get("Entrypoint")} != {ENTRYPOINT}')

    labels = config.get("Labels")
    if not isinstance(labels, dict):
        raise ValueError("image labels are missing")
    for key, expected in expected_labels.items():
        actual = labels.get(key)
        if actual != expected:
            raise ValueError(f"{key} {actual!r} != {expected!r}")


def verify_manifest_platforms(image: object) -> None:
    if not isinstance(image, dict):
        raise ValueError("manifest inspection must be an object")
    if "architecture" in image:
        platform = f'{image.get("os")}/{image.get("architecture")}'
        platforms = {platform}
    else:
        platforms = set(image)
    if platforms != EXPECTED_PLATFORMS:
        raise ValueError(
            f"manifest platforms {sorted(platforms)} != {sorted(EXPECTED_PLATFORMS)}"
        )


def expected_labels(arguments: argparse.Namespace) -> dict[str, str]:
    return {
        "org.opencontainers.image.base.name": arguments.base_image,
        "io.github.shkwon98.cuda.version": arguments.cuda_version,
        "io.github.shkwon98.ubuntu.version": arguments.ubuntu_version,
        "io.github.shkwon98.ubuntu.codename": arguments.ubuntu_codename,
        "io.github.shkwon98.ros.distro": arguments.ros_distro,
        "io.github.shkwon98.ros.variant": arguments.ros_variant,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify image publication inputs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    digests_parser = subparsers.add_parser("digests")
    digests_parser.add_argument("directory", type=Path)

    platform_parser = subparsers.add_parser("platform")
    platform_parser.add_argument("inspection", type=Path)
    for name in (
        "platform",
        "base-image",
        "cuda-version",
        "ubuntu-version",
        "ubuntu-codename",
        "ros-distro",
        "ros-variant",
    ):
        platform_parser.add_argument(f"--{name}", required=True)

    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser.add_argument("inspection", type=Path)

    arguments = parser.parse_args()
    try:
        if arguments.command == "digests":
            print(json.dumps(collect_digests(arguments.directory), sort_keys=True))
        elif arguments.command == "platform":
            image = json.loads(arguments.inspection.read_text())
            verify_platform_image(
                image,
                arguments.platform,
                expected_labels(arguments),
            )
        else:
            image = json.loads(arguments.inspection.read_text())
            verify_manifest_platforms(image)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
