import copy
import hashlib
import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify_image import check_compatibility, publish


CONFIGURATION = json.loads((Path(__file__).resolve().parents[1] / "images.json").read_text())


class VerifyImageTests(unittest.TestCase):
    def test_promotion_uses_the_tested_digest_and_stops_on_failure(self):
        image = copy.deepcopy(CONFIGURATION["images"][0])
        tag = f'{image["ros_distro"]}-ros-core'
        image.update(ros_variant="ros-core", tag=tag, os_tag=f'{tag}-{image["ubuntu_codename"]}')
        digest = "sha256:" + "a" * 64
        inspection = {}
        for platform, config in image["platforms"].items():
            inspection[platform] = {"config": {
                "Entrypoint": ["/opt/nvidia/nvidia_entrypoint.sh"],
                "Labels": {
                    "org.opencontainers.image.base.name": config["base_image"],
                    "org.opencontainers.image.revision": "revision",
                    "io.github.shkwon98.cuda.version": config["cuda_version"],
                    "io.github.shkwon98.ubuntu.version": image["ubuntu_version"],
                    "io.github.shkwon98.ubuntu.codename": image["ubuntu_codename"],
                    "io.github.shkwon98.ros.distro": image["ros_distro"],
                    "io.github.shkwon98.ros.variant": "ros-core",
                },
            }}

        for failure in (None, "registry", "arm64", "platform", "revision", "entrypoint", "digest"):
            with self.subTest(failure=failure), \
                 patch("scripts.verify_image.inspect_image", return_value=copy.deepcopy(inspection)) as inspect, \
                 patch("scripts.verify_image.subprocess.run") as run:
                if failure == "registry":
                    inspect.side_effect = [inspection, subprocess.CalledProcessError(1, "inspect")]
                elif failure == "arm64":
                    run.side_effect = [None, subprocess.CalledProcessError(42, "docker run")]
                elif failure == "platform":
                    del inspect.return_value["linux/arm64"]
                elif failure == "revision":
                    inspect.return_value["linux/arm64"]["config"]["Labels"]["org.opencontainers.image.revision"] = "old"
                elif failure == "entrypoint":
                    inspect.return_value["linux/arm64"]["config"]["Entrypoint"] = ["/bin/bash"]
                candidate = "" if failure == "digest" else digest
                if failure:
                    with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                        publish(image, candidate, "Review", "revision")
                    self.assertFalse(any("create" in call.args[0] for call in run.call_args_list))
                else:
                    publish(image, candidate, "Review", "revision")
                    commands = [call.args[0] for call in run.call_args_list]
                    self.assertEqual([c[5] for c in commands[:2]], ["linux/amd64", "linux/arm64"])
                    self.assertTrue(all(c[6] == f"ghcr.io/review/ros2-cuda@{digest}" for c in commands[:2]))
                    for command, registry in zip(commands[2:], ("ghcr.io", "docker.io"), strict=True):
                        self.assertEqual(command, [
                            "docker", "buildx", "imagetools", "create",
                            "--tag", f'{registry}/review/ros2-cuda:{image["tag"]}',
                            "--tag", f'{registry}/review/ros2-cuda:{image["os_tag"]}',
                            f"{registry}/review/ros2-cuda@{digest}",
                        ])

    def test_weekly_check_rejects_unavailable_published_images(self):
        image = copy.deepcopy(CONFIGURATION["images"][0])
        image["ros_apt_source_sha256"] = hashlib.sha256(b"package").hexdigest()
        base = {platform: {"config": {"Env": [f'CUDA_VERSION={config["cuda_version"]}']}}
                for platform, config in image["platforms"].items()}

        def inspect(reference):
            if reference.startswith("nvcr.io/"):
                return base
            raise subprocess.CalledProcessError(1, "inspect", stderr="manifest unknown")

        with patch("scripts.verify_image.inspect_image", side_effect=inspect), \
             patch("scripts.verify_image.urllib.request.urlopen", return_value=io.BytesIO(b"package")):
            with self.assertRaises(subprocess.CalledProcessError):
                check_compatibility({"images": [image]}, "review")
