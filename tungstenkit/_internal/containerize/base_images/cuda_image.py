import re
import typing as t

import attrs
from packaging.version import Version

from tungstenkit._internal.utils.version import check_if_two_versions_compatible
from tungstenkit.exceptions import NoCompatibleCUDAImage

from .base_image import BaseImage
from .common import fetch_tags_from_docker_hub_repo

RE_CUDA_IMAGE = (
    r"([0-9]+(?:[.][0-9]+){0,2})-cudnn([0-9]+(?:[.][0-9]+){0,2})-devel-ubuntu([0-9]+[.][0-9]{2})"
)


@attrs.frozen(order=True)
class CUDAImage(BaseImage):
    cuda_ver: Version
    cudnn_ver: Version
    ubuntu_ver: Version

    @staticmethod
    def get_repository():
        return "nvidia/cuda"

    def get_tag(self):
        tag = (
            f"{self.cuda_ver}-cudnn{self.cudnn_ver}-devel-"
            f"ubuntu{self.ubuntu_ver.major}.{self.ubuntu_ver.minor:02}"
        )
        return tag


@attrs.define
class CUDAImageCollection:
    images: t.List[CUDAImage]

    @staticmethod
    def from_file():
        # TODO implement this
        return CUDAImageCollection.from_docker_hub()

    @staticmethod
    def from_docker_hub():
        # Fetch all tags from docker hub
        tags = fetch_tags_from_docker_hub_repo(CUDAImage.get_repository())

        # Parse
        images = []
        cuda_image_pattern = re.compile(RE_CUDA_IMAGE)
        for tag in tags:
            matches = re.findall(cuda_image_pattern, tag)
            if matches:
                cuda_ver_str, cudnn_ver_str, ubuntu_ver_str = matches[0]
                cuda_ver = Version(cuda_ver_str)
                cudnn_ver = Version(cudnn_ver_str)
                ubuntu_ver = Version(ubuntu_ver_str)
                images.append(
                    CUDAImage(
                        cuda_ver=cuda_ver,
                        cudnn_ver=cudnn_ver,
                        ubuntu_ver=ubuntu_ver,
                    )
                )

        return CUDAImageCollection(images=images)

    def get_cuda_image_by_cuda_cudnn_ver(
        self, cuda_ver: Version, cudnn_ver: t.Optional[Version]
    ) -> CUDAImage:
        candidates = [
            img
            for img in self.images
            if check_if_two_versions_compatible(img.cuda_ver, v2=cuda_ver)
            and check_if_two_versions_compatible(img.cudnn_ver, v2=cudnn_ver)
        ]
        if len(candidates) == 0:
            cudnn_ver_str = str(cudnn_ver) if cudnn_ver else ""
            raise NoCompatibleCUDAImage(f"CUDA version: {cuda_ver}" + cudnn_ver_str)
        return max(candidates)

    def get_latest_image(self) -> CUDAImage:
        return max(self.images)
