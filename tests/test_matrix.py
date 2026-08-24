import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.matrix import expand, render_readme_table


def valid_document():
    return {
        "images": [
            {
                "ubuntu_version": "24.04",
                "ubuntu_codename": "noble",
                "ros_distro": "jazzy",
                "ros_apt_source_version": "1.2.0",
                "ros_apt_source_package": "ros2-apt-source",
                "ros_apt_source_sha256": (
                    "0804d9b13db770eb87019be414cd78378835228ad5fa801fc88758596dd8f7e5"
                ),
                "platforms": {
                    "linux/amd64": {
                        "base_image": (
                            "nvcr.io/nvidia/cuda:13.2.1-runtime-ubuntu24.04"
                        ),
                        "cuda_version": "13.2.1",
                    },
                    "linux/arm64": {
                        "base_image": (
                            "nvcr.io/nvidia/cuda:13.2.1-runtime-ubuntu24.04"
                        ),
                        "cuda_version": "13.2.1",
                    },
                },
            }
        ]
    }


class MatrixTests(unittest.TestCase):
    def test_rejects_jetpack_metadata(self):
        document = valid_document()
        document["images"][0]["jetpack_version"] = "7.2.1"

        with self.assertRaisesRegex(ValueError, "jetpack_version"):
            expand(document)

    def test_accepts_official_ros_testing_source(self):
        document = valid_document()
        document["images"][0]["ros_apt_source_package"] = (
            "ros2-testing-apt-source"
        )

        matrix = expand(document)

        self.assertEqual(
            matrix["builds"]["include"][0]["ros_apt_source_package"],
            "ros2-testing-apt-source",
        )

    def test_rejects_unknown_ros_apt_source_package(self):
        document = valid_document()
        document["images"][0]["ros_apt_source_package"] = "invalid-source"

        with self.assertRaisesRegex(ValueError, "invalid-source"):
            expand(document)

    def test_repository_matrix_contains_supported_ros_distributions(self):
        document = json.loads(
            (Path(__file__).resolve().parents[1] / "images.json").read_text()
        )

        matrix = expand(document)
        manifests = matrix["manifests"]["include"]
        builds = matrix["builds"]["include"]

        self.assertEqual(
            {entry["tag"] for entry in manifests},
            {
                "humble-ros-core",
                "humble-ros-base",
                "jazzy-ros-core",
                "jazzy-ros-base",
                "kilted-ros-core",
                "kilted-ros-base",
                "lyrical-ros-core",
                "lyrical-ros-base",
                "rolling-ros-core",
                "rolling-ros-base",
            },
        )
        self.assertEqual(len(manifests), 10)
        self.assertEqual(len(builds), 20)
        self.assertEqual(
            {(entry["tag"], entry["platform"]) for entry in builds},
            {
                (tag, platform)
                for tag in {entry["tag"] for entry in manifests}
                for platform in ("linux/amd64", "linux/arm64")
            },
        )

    def test_expands_platform_builds_and_derives_tags(self):
        try:
            matrix = expand(valid_document())
        except ValueError as error:
            self.fail(str(error))
        manifests = matrix["manifests"]["include"]
        builds = matrix["builds"]["include"]

        self.assertEqual(
            [entry["tag"] for entry in manifests],
            ["jazzy-ros-core", "jazzy-ros-base"],
        )
        self.assertEqual(
            [entry["os_tag"] for entry in manifests],
            ["jazzy-ros-core-noble", "jazzy-ros-base-noble"],
        )
        self.assertEqual(
            [
                (
                    entry["tag"],
                    entry["platform"],
                    entry["platform_slug"],
                    entry["base_image"],
                    entry["cuda_version"],
                )
                for entry in builds
            ],
            [
                (
                    "jazzy-ros-core",
                    "linux/amd64",
                    "linux-amd64",
                    "nvcr.io/nvidia/cuda:13.2.1-runtime-ubuntu24.04",
                    "13.2.1",
                ),
                (
                    "jazzy-ros-core",
                    "linux/arm64",
                    "linux-arm64",
                    "nvcr.io/nvidia/cuda:13.2.1-runtime-ubuntu24.04",
                    "13.2.1",
                ),
                (
                    "jazzy-ros-base",
                    "linux/amd64",
                    "linux-amd64",
                    "nvcr.io/nvidia/cuda:13.2.1-runtime-ubuntu24.04",
                    "13.2.1",
                ),
                (
                    "jazzy-ros-base",
                    "linux/arm64",
                    "linux-arm64",
                    "nvcr.io/nvidia/cuda:13.2.1-runtime-ubuntu24.04",
                    "13.2.1",
                ),
            ],
        )
        self.assertEqual(builds[0]["ros_variant"], "ros-core")
        self.assertNotIn("platforms", builds[0])

    def test_requires_both_platforms(self):
        document = valid_document()
        del document["images"][0]["platforms"]["linux/arm64"]

        with self.assertRaisesRegex(ValueError, "linux/arm64"):
            expand(document)

    def test_rejects_l4t_base_for_amd64(self):
        document = valid_document()
        document["images"][0]["platforms"]["linux/amd64"]["base_image"] = (
            "nvcr.io/nvidia/l4t-cuda:12.6.11-runtime"
        )

        with self.assertRaisesRegex(ValueError, "linux/amd64"):
            expand(document)

    def test_rejects_unknown_platform_field(self):
        document = valid_document()
        document["images"][0]["platforms"]["linux/arm64"]["target"] = "jetson"

        with self.assertRaisesRegex(ValueError, "target"):
            expand(document)

    def test_rejects_duplicate_derived_tags(self):
        document = valid_document()
        document["images"].append(copy.deepcopy(document["images"][0]))

        with self.assertRaisesRegex(ValueError, "jazzy-ros-core"):
            expand(document)

    def test_rejects_missing_required_field(self):
        document = valid_document()
        del document["images"][0]["platforms"]["linux/amd64"]["cuda_version"]

        with self.assertRaisesRegex(ValueError, "cuda_version"):
            expand(document)

    def test_rejects_unknown_field(self):
        document = valid_document()
        document["images"][0]["ubuntu"] = "noble"

        with self.assertRaisesRegex(ValueError, "ubuntu"):
            expand(document)

    def test_rejects_empty_allowlist(self):
        with self.assertRaisesRegex(ValueError, "images"):
            expand({"images": []})

    def test_cli_prints_github_matrix(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            matrix_path = Path(temporary_directory) / "images.json"
            matrix_path.write_text(json.dumps(valid_document()))

            result = subprocess.run(
                [sys.executable, "scripts/matrix.py", str(matrix_path)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"tag":"jazzy-ros-core"', result.stdout)
        self.assertIn('"platform":"linux/arm64"', result.stdout)

    def test_cli_prints_readme_table(self):
        expected = """<!-- BEGIN GENERATED CONFIGURATIONS -->
| ROS 2 | Ubuntu | CUDA | `amd64` image | `arm64` image |
| :---: | --- | --- | :---: | :---: |
| <a href="https://docs.ros.org/en/jazzy/Releases/Release-Jazzy-Jalisco.html"><img src="https://raw.githubusercontent.com/ros2/ros2_documentation/a74c8f1ddc1dafaf144998dc793ffca0c3d5a5fc/source/Get-Started/Releases/jazzy-small.png" height="48" alt="Jazzy Jalisco artwork"></a><br>Jazzy | 24.04 Noble | 13.2.1 | Available | Available · JetPack 7 |
<!-- END GENERATED CONFIGURATIONS -->
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            matrix_path = Path(temporary_directory) / "images.json"
            matrix_path.write_text(json.dumps(valid_document()))

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/matrix.py",
                    "--readme-table",
                    str(matrix_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected)

    def test_readme_table_preserves_platform_cuda_versions(self):
        document = valid_document()
        document["images"][0]["ros_distro"] = "humble"
        document["images"][0]["platforms"]["linux/amd64"]["cuda_version"] = (
            "12.6.3"
        )
        document["images"][0]["platforms"]["linux/arm64"]["cuda_version"] = (
            "12.6.11"
        )

        table = render_readme_table(document)

        self.assertIn(
            "| 12.6.3 / 12.6.11² | Available | Available · JetPack 6 |", table
        )
        self.assertIn(
            "2. Humble uses CUDA 12.6.3 on `amd64` and the Jetson-specific "
            "L4T CUDA 12.6.11 runtime on `arm64`.",
            table,
        )

    def test_readme_table_marks_arm64_without_jetpack_as_preview(self):
        document = valid_document()
        document["images"][0]["ros_distro"] = "lyrical"

        table = render_readme_table(document)

        self.assertIn("| Available | Preview³ |", table)
        self.assertIn(
            "3. The `arm64` image is available, but no matching JetPack release "
            "exists and Jetson is not currently supported.",
            table,
        )

    def test_readme_table_marks_rolling_testing_source(self):
        document = valid_document()
        document["images"][0]["ros_distro"] = "rolling"

        table = render_readme_table(document)

        self.assertIn("<br>Rolling¹ |", table)
        self.assertIn(
            "1. Rolling images use packages from the official ROS testing "
            "repository.",
            table,
        )


if __name__ == "__main__":
    unittest.main()
