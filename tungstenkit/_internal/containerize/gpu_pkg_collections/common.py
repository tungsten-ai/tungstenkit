import typing as t

import attrs
from packaging.version import Version

from tungstenkit._internal.utils.version import MIN_VER, order_optional_version


@attrs.frozen(order=True)
class GPUPackageRelease:
    # TODO validators
    pkg_name: str
    pkg_ver: Version
    no_cuda: bool
    cuda_ver: t.Optional[Version] = attrs.field(default=None, order=order_optional_version)
    cudnn_ver: t.Optional[Version] = attrs.field(default=None, order=order_optional_version)
    py_vers: t.Set[Version] = attrs.field(
        factory=set, order=lambda ver_lst: max(ver_lst) if ver_lst else MIN_VER
    )
    pip_index_url: t.Optional[str] = attrs.field(default=None, order=False)
    pip_extra_index_url: t.Optional[str] = attrs.field(default=None, order=False)
    env_vars: t.Optional[t.Dict[str, str]] = attrs.field(default=None, order=False)


@attrs.define
class GPUPackageConstraint:
    pkg_name: t.Optional[str] = attrs.field(default=None)
    pkg_ver: t.Optional[Version] = attrs.field(default=None)
    no_cuda: t.Optional[bool] = attrs.field(default=None)
    cuda_ver: t.Optional[Version] = attrs.field(default=None)
    any_cuda_in: t.Optional[t.Iterable[Version]] = attrs.field(default=None)
    py_ver: t.Optional[Version] = attrs.field(default=None)
    any_py_in: t.Optional[t.Iterable[Version]] = attrs.field(default=None)

    def __attrs_post_init__(self):
        if self.no_cuda and self.cuda_ver:
            raise ValueError(
                f"{self.__class__.__name__}.no_cuda and {self.__class__.__name__}.cuda_ver "
                "cannot be set together."
            )
