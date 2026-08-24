import copy
import tempfile
import unittest
from pathlib import Path

from scripts.verify_image import (
    collect_digests,
    verify_manifest_platforms,
    verify_platform_image,
)


EXPECTED_LABELS = {
    "org.opencontainers.image.base.name": (
        "nvcr.io/nvidia/cuda:13.2.1-runtime-ubuntu24.04"
    ),
    "io.github.shkwon98.cuda.version": "13.2.1",
    "io.github.shkwon98.ubuntu.version": "24.04",
    "io.github.shkwon98.ubuntu.codename": "noble",
    "io.github.shkwon98.ros.distro": "jazzy",
    "io.github.shkwon98.ros.variant": "ros-core",
}


def platform_image():
    return {
        "architecture": "amd64",
        "os": "linux",
        "config": {
            "Entrypoint": ["/opt/nvidia/nvidia_entrypoint.sh"],
            "Labels": copy.deepcopy(EXPECTED_LABELS),
        },
    }


class VerifyImageTests(unittest.TestCase):
    def test_accepts_expected_platform_image(self):
        verify_platform_image(
            platform_image(),
            "linux/amd64",
            EXPECTED_LABELS,
        )

    def test_accepts_indexed_single_platform_image(self):
        image = {"linux/amd64": {"config": platform_image()["config"]}}

        verify_platform_image(image, "linux/amd64", EXPECTED_LABELS)

    def test_rejects_wrong_platform(self):
        image = platform_image()
        image["architecture"] = "arm64"

        with self.assertRaisesRegex(ValueError, "linux/arm64"):
            verify_platform_image(image, "linux/amd64", EXPECTED_LABELS)

    def test_rejects_wrong_entrypoint(self):
        image = platform_image()
        image["config"]["Entrypoint"] = ["/bin/bash"]

        with self.assertRaisesRegex(ValueError, "Entrypoint"):
            verify_platform_image(image, "linux/amd64", EXPECTED_LABELS)

    def test_rejects_each_mismatched_label(self):
        for label in EXPECTED_LABELS:
            with self.subTest(label=label):
                image = platform_image()
                image["config"]["Labels"][label] = "wrong"

                with self.assertRaisesRegex(ValueError, label):
                    verify_platform_image(image, "linux/amd64", EXPECTED_LABELS)

    def test_collects_one_unique_digest_per_platform(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            amd64 = "a" * 64
            arm64 = "b" * 64
            (directory / f"linux-amd64-{amd64}").touch()
            (directory / f"linux-arm64-{arm64}").touch()

            digests = collect_digests(directory)

        self.assertEqual(
            digests,
            {
                "linux/amd64": f"sha256:{amd64}",
                "linux/arm64": f"sha256:{arm64}",
            },
        )

    def test_rejects_duplicate_platform_digest_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            (directory / f"linux-amd64-{'a' * 64}").touch()
            (directory / f"linux-amd64-{'b' * 64}").touch()
            (directory / f"linux-arm64-{'c' * 64}").touch()

            with self.assertRaisesRegex(ValueError, "linux/amd64"):
                collect_digests(directory)

    def test_rejects_same_digest_for_both_platforms(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            digest = "a" * 64
            (directory / f"linux-amd64-{digest}").touch()
            (directory / f"linux-arm64-{digest}").touch()

            with self.assertRaisesRegex(ValueError, "unique"):
                collect_digests(directory)

    def test_manifest_requires_exactly_two_platforms(self):
        image = {
            "linux/amd64": {"config": {}},
            "linux/arm64": {"config": {}},
        }

        verify_manifest_platforms(image)

        del image["linux/arm64"]
        with self.assertRaisesRegex(ValueError, "linux/arm64"):
            verify_manifest_platforms(image)


if __name__ == "__main__":
    unittest.main()
