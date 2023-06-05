import re
import typing as t

import attrs
from packaging.version import Version

from tungstenkit._internal.utils.version import check_if_two_versions_compatible
from tungstenkit.exceptions import NoCompatiblePythonImage

from .base_image import BaseImage
from .common import fetch_tags_from_docker_hub_repo

RE_PYTHON_IMAGE = r"((?:[0-9]+)(?:[.][0-9]+){0,1}(?:[.][0-9]+){0,1})-slim$"


@attrs.frozen(order=True)
class PythonImage(BaseImage):
    ver: Version

    @staticmethod
    def get_repository():
        return "library/python"

    def get_tag(self):
        tag = str(self.ver) + "-slim"
        return tag


@attrs.define
class PythonImageCollection:
    images: t.List[PythonImage]

    @staticmethod
    def from_file():
        # TODO implement this
        return PythonImageCollection.from_docker_hub()

    @staticmethod
    def from_docker_hub():
        # Fetch all tags from docker hub
        tags = fetch_tags_from_docker_hub_repo(PythonImage.get_repository())

        # Parse
        images = []
        cuda_image_pattern = re.compile(RE_PYTHON_IMAGE)
        for tag in tags:
            matches = re.findall(cuda_image_pattern, tag)
            if matches:
                images.append(PythonImage(ver=Version(matches[0])))

        return PythonImageCollection(images=images)

    def get_py_image_by_ver(self, py_ver: Version) -> PythonImage:
        candidates = [
            img for img in self.images if check_if_two_versions_compatible(img.ver, v2=py_ver)
        ]
        if len(candidates) == 0:
            raise NoCompatiblePythonImage(str(py_ver))
        return max(candidates)
