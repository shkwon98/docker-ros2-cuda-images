import copy
import json
import unittest
from pathlib import Path

from scripts.matrix import expand


CONFIGURATION = json.loads((Path(__file__).resolve().parents[1] / "images.json").read_text())


class MatrixTests(unittest.TestCase):
    def test_configured_images_keep_their_tags_and_platform_settings(self):
        entries = expand(CONFIGURATION)["include"]
        images = {(entry["ros_distro"], entry["ros_variant"]): entry for entry in entries}
        self.assertEqual(len(entries), 2 * len(CONFIGURATION["images"]))
        self.assertEqual(len(images), len(entries))
        for source in CONFIGURATION["images"]:
            for variant in ("ros-core", "ros-base"):
                entry = images[source["ros_distro"], variant]
                self.assertEqual(entry["tag"], f'{source["ros_distro"]}-{variant}')
                self.assertEqual(entry["os_tag"], f'{entry["tag"]}-{source["ubuntu_codename"]}')
                self.assertEqual({key: entry[key] for key in source}, source)

    def test_rejects_a_missing_architecture(self):
        document = copy.deepcopy(CONFIGURATION)
        del document["images"][0]["platforms"]["linux/arm64"]
        with self.assertRaises(ValueError):
            expand(document)

    def test_rejects_l4t_on_amd64(self):
        document = copy.deepcopy(CONFIGURATION)
        document["images"][0]["platforms"]["linux/amd64"]["base_image"] = (
            "nvcr.io/nvidia/l4t-cuda:12.6.11-runtime"
        )
        with self.assertRaises(ValueError):
            expand(document)

    def test_rejects_duplicate_tags(self):
        document = copy.deepcopy(CONFIGURATION)
        document["images"].append(copy.deepcopy(document["images"][0]))
        with self.assertRaises(ValueError):
            expand(document)
