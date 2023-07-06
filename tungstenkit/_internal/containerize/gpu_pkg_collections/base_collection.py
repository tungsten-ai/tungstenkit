import abc
import typing as t

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from tungstenkit._internal.utils.string import removesuffix
from tungstenkit._internal.utils.version import (
    check_if_two_versions_compatible,
    check_version_matching_clause_loosely,
)

from .common import GPUPackageConstraint, GPUPackageRelease


class GPUPackageCollection(abc.ABC):
    @classmethod
    def init(cls):
        # TODO call from_file or from_remote periodically
        # raise NotImplementedError
        return cls.from_remote()

    @classmethod
    @abc.abstractmethod
    def from_remote(cls):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def has_no_compatible_vers(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def get_available_cuda_vers(self, pkg_names: t.List[str]) -> t.Set[t.Optional[Version]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_available_cudnn_vers(self, pkg_names: t.List[str]) -> t.Set[t.Optional[Version]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_available_py_vers(self, pkg_names: t.List[str]) -> t.Set[Version]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_constraint(self, constraint: GPUPackageConstraint) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_latest_releases(self, pkg_names: t.Iterable[str]) -> t.List[GPUPackageRelease]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_err_msg_for_constraint(self, constraint: GPUPackageConstraint) -> t.Optional[str]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def requires_system_cuda(cls):
        raise NotImplementedError

    @classmethod
    def get_pkg_names(cls) -> t.Set[str]:
        raise NotImplementedError

    @classmethod
    def name(cls):
        return removesuffix(cls.__name__, "Collection").lower()

    @staticmethod
    def filter_releases_by_constraint(
        releases: t.List[GPUPackageRelease], constraint: GPUPackageConstraint
    ) -> t.List[GPUPackageRelease]:
        filter_fns: t.List[t.Callable[[GPUPackageRelease], bool]] = list()
        if isinstance(constraint.pkg_spec, SpecifierSet):
            pkg_specifier_set = constraint.pkg_spec
            filter_fns.append(lambda release: release.pkg_ver in pkg_specifier_set)
        if isinstance(constraint.pkg_spec, Version):
            pkg_version_spec = constraint.pkg_spec
            filter_fns.append(
                lambda release: check_version_matching_clause_loosely(
                    release.pkg_ver, pkg_version_spec
                )
            )
        if constraint.no_cuda is not None:
            filter_fns.append(
                lambda release: release.no_cuda == constraint.no_cuda,
            )
        if constraint.cuda_ver is not None:
            filter_fns.append(
                lambda release: check_if_two_versions_compatible(
                    v1=release.cuda_ver, v2=constraint.cuda_ver
                )
            )
        if constraint.any_cuda_in is not None:
            filter_fns.append(
                lambda release: any(
                    check_if_two_versions_compatible(v1=release.cuda_ver, v2=cuda_ver)
                    for cuda_ver in constraint.any_cuda_in  # type: ignore
                )
            )
        if constraint.py_ver is not None:
            filter_fns.append(
                lambda release: any(
                    check_if_two_versions_compatible(v1=release_py_ver, v2=constraint.py_ver)
                    for release_py_ver in release.py_vers  # type: ignore
                ),
            )
        if constraint.any_py_in is not None:
            filter_fns.append(
                lambda release: any(
                    any(
                        check_if_two_versions_compatible(v1=release_py_ver, v2=py_ver)
                        for py_ver in constraint.any_py_in  # type: ignore
                    )
                    for release_py_ver in release.py_vers
                ),
            )
        filtered: t.Union[filter, t.List] = releases
        for filter_fn in filter_fns:
            filtered = filter(filter_fn, filtered)

        if len(filter_fns) > 0:
            filtered_list = list(filtered)

        return filtered_list
