import abc
import typing as t

from packaging.version import Version

from tungstenkit._internal.utils.string import removesuffix
from tungstenkit._internal.utils.version import (
    check_if_two_versions_compatible,
    check_version_with_constraint,
)

from .common import GPUPackageConstraint, GPUPackageRelease


class GPUPackageCollection(abc.ABC):
    @classmethod
    def init(cls):
        # TODO call from_file or from_remote periodically
        # raise NotImplementedError
        return cls.from_remote()

    @classmethod
    def from_remote(cls):
        raise NotImplementedError

    @property
    def has_no_compatible_vers(self) -> bool:
        raise NotImplementedError

    def get_available_cuda_vers(self, pkg_names: t.List[str]) -> t.Set[t.Optional[Version]]:
        raise NotImplementedError

    def get_available_cudnn_vers(self, pkg_names: t.List[str]) -> t.Set[t.Optional[Version]]:
        raise NotImplementedError

    def get_available_py_vers(self, pkg_names: t.List[str]) -> t.Set[Version]:
        raise NotImplementedError

    def add_constraint(self, constraint: GPUPackageConstraint) -> None:
        raise NotImplementedError

    def get_latest_releases(self, pkg_names: t.Iterable[str]) -> t.List[GPUPackageRelease]:
        raise NotImplementedError

    def get_err_msg_for_constraint(self, constraint: GPUPackageConstraint) -> t.Optional[str]:
        raise NotImplementedError

    @classmethod
    def get_pkg_names(cls) -> t.Set[str]:
        raise NotImplementedError

    @classmethod
    def requires_system_cuda(cls) -> bool:
        raise NotImplementedError

    @classmethod
    def name(cls):
        return removesuffix(cls.__name__, "Collection").lower()

    @staticmethod
    def filter_releases_by_constraint(
        releases: t.List[GPUPackageRelease], constraint: GPUPackageConstraint
    ) -> t.List[GPUPackageRelease]:
        filter_fns: t.List[t.Callable[[GPUPackageRelease], bool]] = list()
        if constraint.pkg_ver is not None:
            filter_fns.append(
                lambda release: check_version_with_constraint(
                    ver=release.pkg_ver, constraint=constraint.pkg_ver
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
            releases = list(filtered)
        return releases
