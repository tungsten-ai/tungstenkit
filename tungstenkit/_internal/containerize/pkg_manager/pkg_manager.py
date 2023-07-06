import sys
import typing as t

import attrs
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from tungstenkit import exceptions
from tungstenkit._internal.constants import MAX_SUPPORTED_PYTHON_VER, MIN_SUPPORTED_PYTHON_VER
from tungstenkit._internal.logging import log_info
from tungstenkit._internal.utils.version import (
    NotRequired,
    check_if_two_versions_compatible,
    find_latest_compatible_version,
)

from ..gpu_pkg_collections import (
    GPUPackageCollection,
    GPUPackageConstraint,
    get_gpu_pkg_collection_name_by_pkg_name,
    gpu_pkg_collection_class_dict,
)
from .pip_requirement import PipRequirement

# TODO provide more info when exception raised


@attrs.frozen
class GPUCollectionStatus:
    pkg_vers: t.Set[Version] = attrs.field(factory=set)
    cuda_vers: t.Set[t.Union[None, Version]] = attrs.field(factory=set)
    py_vers: t.Set[Version] = attrs.field(factory=set)


# TODO track history and show kind err msg
@attrs.frozen
class UpdateHistory:
    name: str
    spec: GPUPackageConstraint
    status: GPUCollectionStatus
    reason: t.Optional[str] = attrs.field(default=None)
    err_msg: t.Optional[str] = attrs.field(default=None)


@attrs.frozen
class PythonPackageManager:
    _gpu_pkg_collections: t.Dict[str, GPUPackageCollection] = attrs.field(factory=dict, init=False)
    _required_gpu_pkg_names: t.Dict[str, t.Set[str]] = attrs.field(factory=dict, init=False)
    _update_history: t.List[UpdateHistory] = attrs.field(factory=list, init=False)
    _extra_pkgs: t.List[PipRequirement] = attrs.field(factory=list, init=False)

    def requires_system_cuda(self) -> bool:
        return any(col.requires_system_cuda() for col in self._gpu_pkg_collections.values())

    def add_requirement_str(self, requirement_str: str):
        # Parse requirement string
        # TODO support --extra-index-url and --index-url

        try:
            parsed = Requirement(requirement_str)
        except IndexError:
            raise exceptions.PipPackageParseError(
                f"No package name in requirement string: {requirement_str}"
            )
        except Exception as e:
            raise exceptions.PipPackageParseError(str(e))

        pkg_name = parsed.name
        specifier_set = parsed.specifier
        specifier_list = list(specifier_set)

        if len(specifier_set) == 1 and specifier_list[0].operator == "==":
            spec: Version | SpecifierSet = Version(specifier_list[0].version)
        else:
            spec = specifier_set

        # Check if a GPU package
        collection_name = get_gpu_pkg_collection_name_by_pkg_name(pkg_name)
        if collection_name is None:
            self._extra_pkgs.append(PipRequirement(name=pkg_name, spec=spec))
            return

        # Lazy initialization of a GPU package collection
        if collection_name not in self._gpu_pkg_collections:
            log_info(f"Fetching the list of {collection_name} packages")
            collection_cls = gpu_pkg_collection_class_dict[collection_name]
            self._gpu_pkg_collections[collection_name] = collection_cls.init()
            self._required_gpu_pkg_names[collection_name] = set()

        self._required_gpu_pkg_names[collection_name].add(pkg_name)
        if spec and (isinstance(spec, Version) or len(spec) > 0):
            self._set_gpu_pkg_constraint(GPUPackageConstraint(pkg_name=pkg_name, pkg_spec=spec))

    def set_gpu(self, gpu: bool):
        self._set_gpu_pkg_constraint(GPUPackageConstraint(no_cuda=not gpu))

    def set_cuda_equal_to(self, cuda_ver: Version):
        self._set_gpu_pkg_constraint(GPUPackageConstraint(cuda_ver=cuda_ver))

    def set_any_cuda_in(self, cuda_vers: t.Iterable[Version]):
        self._set_gpu_pkg_constraint(GPUPackageConstraint(any_cuda_in=cuda_vers))

    def set_python_equal_to(self, py_ver: Version):
        self._set_gpu_pkg_constraint(GPUPackageConstraint(py_ver=py_ver))

    def set_any_python_in(self, py_vers: t.Iterable[Version]):
        self._set_gpu_pkg_constraint(GPUPackageConstraint(any_py_in=py_vers))

    def infer_cuda_ver(self) -> t.Optional[t.Union[Version, NotRequired]]:
        """
        Return the latest CUDA version compatible with required GPU packages.
        """
        list_cuda_ver_sets = [
            collection.get_available_cuda_vers(list(self._required_gpu_pkg_names[collection_name]))
            for collection_name, collection in self._gpu_pkg_collections.items()
        ]
        if len(list_cuda_ver_sets) == 0:
            return NotRequired()
        try:
            return find_latest_compatible_version(list_cuda_ver_sets)
        except exceptions.NoCompatibleVersion:
            raise exceptions.NoCompatiblePythonPackage

    def infer_cudnn_ver(self) -> t.Optional[Version]:
        """
        Return the latest CuDNN version compatible with required GPU packages.
        """
        list_cudnn_ver_sets = [
            collection.get_available_cudnn_vers(
                list(self._required_gpu_pkg_names[collection_name])
            )
            for collection_name, collection in self._gpu_pkg_collections.items()
        ]
        try:
            return find_latest_compatible_version(list_cudnn_ver_sets)
        except exceptions.NoCompatibleVersion:
            raise exceptions.NoCompatiblePythonPackage

    def infer_python_ver(self) -> Version:
        """
        Return Python version compatible with required GPU packages
        following priorities below:
        1) The version of Python where Tungsten installed
        2) The latest version among candidates
        """
        this_py_ver_in_sys = sys.version_info
        default_py_ver = min(
            max(
                Version(f"{this_py_ver_in_sys.major}.{this_py_ver_in_sys.minor}"),
                MIN_SUPPORTED_PYTHON_VER,
            ),
            MAX_SUPPORTED_PYTHON_VER,
        )
        list_py_ver_sets = [
            collection.get_available_py_vers(list(self._required_gpu_pkg_names[collection_name]))
            for collection_name, collection in self._gpu_pkg_collections.items()
        ]
        if default_py_ver and all(
            len(ver_set) > 0
            and any(check_if_two_versions_compatible(ver, default_py_ver) for ver in ver_set)
            for ver_set in list_py_ver_sets
        ):
            return default_py_ver

        try:
            py_ver = find_latest_compatible_version(list_py_ver_sets)
        except exceptions.NoCompatibleVersion:
            raise exceptions.NoCompatiblePythonVersion

        if py_ver is None:
            return default_py_ver
        return py_ver

    def list_extra_pkg_pip_requirements(self) -> t.List[PipRequirement]:
        return self._extra_pkgs

    def list_gpu_pkg_pip_requirements(self) -> t.List[PipRequirement]:
        pkgs: t.List[PipRequirement] = list()
        for gpu_pkg_collection_name, gpu_pkg_collection in self._gpu_pkg_collections.items():
            gpu_pkgs_in_collection = gpu_pkg_collection.get_latest_releases(
                self._required_gpu_pkg_names[gpu_pkg_collection_name]
            )
            pkgs.extend(
                [
                    PipRequirement(
                        name=gpu_pkg.pkg_name,
                        spec=gpu_pkg.pkg_ver,
                        index_url=gpu_pkg.pip_index_url,
                        extra_index_url=gpu_pkg.pip_extra_index_url,
                    )
                    for gpu_pkg in gpu_pkgs_in_collection
                ]
            )
        pkgs = sorted(pkgs, key=lambda pkg: pkg.name)
        return pkgs

    def _set_gpu_pkg_constraint(self, constraint: GPUPackageConstraint):
        for collection_name, collection in self._gpu_pkg_collections.items():
            if constraint.pkg_name:
                if (
                    constraint.pkg_name in collection.get_pkg_names()
                    and constraint.pkg_name in self._required_gpu_pkg_names[collection_name]
                ):
                    collection.add_constraint(constraint)
            else:
                for pkg_name in self._required_gpu_pkg_names[collection_name]:
                    constraint.pkg_name = pkg_name
                    collection.add_constraint(constraint)
