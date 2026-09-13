import json
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


@unittest.skipUnless(shutil.which("docker"), "Docker is required for base selection checks")
class DockerfileTests(unittest.TestCase):
    def test_platform_selection_and_existing_single_platform_arguments(self):
        # Build the actual FROM/ARG/LABEL instructions with empty bases; no downloads or ROS installation.
        source = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text()
        source = "\n".join(source.splitlines()[2:]).split("SHELL [", 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "Dockerfile").write_text(source)
            for arch, cuda in (("amd64", "12.6.3"), ("arm64", "12.6.11")):
                for legacy in (False, True):
                    with self.subTest(arch=arch, legacy=legacy):
                        tag = f"ros2-base-selection-test:{uuid.uuid4().hex}"
                        args = (["BASE_IMAGE=scratch", f"EXPECTED_CUDA_VERSION={cuda}"] if legacy else [
                            "BASE_IMAGE_AMD64=scratch", "BASE_IMAGE_ARM64=scratch",
                            "CUDA_AMD64=12.6.3", "CUDA_ARM64=12.6.11",
                        ])
                        command = ["docker", "buildx", "build", "--platform", f"linux/{arch}",
                                   "--load", "--provenance=false", "--tag", tag]
                        for arg in args:
                            command.extend(["--build-arg", arg])
                        try:
                            result = subprocess.run(command + [directory], capture_output=True, text=True)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            image = json.loads(subprocess.check_output(["docker", "image", "inspect", tag]))[0]
                            self.assertEqual(image["Architecture"], arch)
                            self.assertEqual(image["Config"]["Labels"]["org.opencontainers.image.base.name"], "scratch")
                            self.assertEqual(image["Config"]["Labels"]["io.github.shkwon98.cuda.version"], cuda)
                        finally:
                            subprocess.run(["docker", "image", "rm", tag], capture_output=True)
