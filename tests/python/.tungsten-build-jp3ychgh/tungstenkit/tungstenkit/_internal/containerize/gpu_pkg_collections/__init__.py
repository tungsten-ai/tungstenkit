from typing import Set

from .base_collection import GPUPackageCollection
from .common import GPUPackageConstraint, GPUPackageRelease
from .tf_collection import TFCollection
from .torch_collection import TorchCollection

gpu_pkg_collection_class_dict = {cls.name(): cls for cls in GPUPackageCollection.__subclasses__()}

supported_gpu_pkg_names: Set[str] = set.union(
    *[cls.get_pkg_names() for cls in gpu_pkg_collection_class_dict.values()]
)


def get_gpu_pkg_collection_name_by_pkg_name(pkg_name: str):
    for collection_name, cls in gpu_pkg_collection_class_dict.items():
        if pkg_name in cls.get_pkg_names():
            return collection_name
    return None


__all__ = [
    "GPUPackageRelease",
    "GPUPackageConstraint",
    "GPUPackageCollection",
    "TFCollection",
    "TorchCollection",
    "gpu_pkg_collection_class_dict",
    "get_gpu_pkg_collection_name_by_pkg_name",
]
