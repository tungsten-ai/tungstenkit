import re
import typing as t
from urllib.parse import unquote

import attrs
import bs4
import requests
from packaging.version import Version

from tungstenkit._internal.logging import log_warning
from tungstenkit._internal.utils.string import removeprefix
from tungstenkit.exceptions import PythonPackageMetadataError

from .base_collection import GPUPackageCollection
from .common import GPUPackageConstraint, GPUPackageRelease

BASE_TORCH_WHEEL_DOWNLOAD_URL = "https://download.pytorch.org/whl"
TORCH_WHEEL_REGEX = (
    # URL subpath containing device spec
    r"(?:(cu[0-9]+|cpu)[/]){0,1}"
    # Package name
    r"(\w+)-"
    # Package version
    r"([0-9]+[.][0-9]+[.][0-9]+\w*(?:[.](?:\w*)){0,1}(?:[+](?:cu[0-9]+|cpu)){0,1})+-"
    # Python version
    r"(?:cp|py)(\w+)-(?:\w*-)"
    # Platform
    r"(?:(?:linux|manylinux\w*)_x86_64|none-any)"
    # Extension
    r"[.]whl"
)


@attrs.define
class TorchCollection(GPUPackageCollection):
    # TODO filter by available cuda images
    torch: t.List[GPUPackageRelease]
    torchvision: t.List[GPUPackageRelease]
    torchaudio: t.List[GPUPackageRelease]

    @classmethod
    def from_remote(cls):
        pkg_names = cls.get_pkg_names()
        release_dict: t.Dict[str, t.List[GPUPackageRelease]] = {n: [] for n in pkg_names}

        # Get wheel names from torch wheel download url
        resp = requests.get(f"{BASE_TORCH_WHEEL_DOWNLOAD_URL}/torch_stable.html")
        if not resp.ok:
            raise PythonPackageMetadataError(
                "Fail to fetch Torch package metadata: "
                f"failed to get HTML from {BASE_TORCH_WHEEL_DOWNLOAD_URL} "
                f"({resp.status_code}: {resp.reason})"
            )

        html = resp.text
        soup = bs4.BeautifulSoup(html, "html.parser")
        wheel_names: t.List[str] = [unquote(tag.get("href")) for tag in soup.find_all("a")]

        # Parse
        regex = re.compile(TORCH_WHEEL_REGEX)
        for wheel_name in wheel_names:
            matches = regex.findall(wheel_name)
            if not matches:
                continue

            segments: t.List[str] = matches[0]
            (
                url_subpath,
                pkg_name,
                pkg_ver_str,
                py_ver_str,
            ) = segments
            if pkg_name not in pkg_names:
                continue

            pkg_ver = Version(pkg_ver_str)
            cuda_ver, pip_index_url, pip_extra_index_url = None, None, None
            if pkg_ver.local and pkg_ver.local.startswith("cu"):
                cuda_ver_str = removeprefix(pkg_ver.local, "cu").split("_")[0]
                cuda_ver = Version(cuda_ver_str[:-1] + "." + cuda_ver_str[-1])
            elif url_subpath.startswith("cu"):
                cuda_ver_str = removeprefix(url_subpath, "cu").split("_")[0]
                cuda_ver = Version(cuda_ver_str[:-1] + "." + cuda_ver_str[-1])
            py_ver = Version(
                py_ver_str[0] + "." + py_ver_str[1:] if len(py_ver_str) > 1 else py_ver_str
            )

            pip_index_url, pip_extra_index_url = None, None
            if not pkg_ver.local and url_subpath:
                pip_index_url = BASE_TORCH_WHEEL_DOWNLOAD_URL + f"/{url_subpath}"
            elif url_subpath:
                pip_extra_index_url = BASE_TORCH_WHEEL_DOWNLOAD_URL + f"/{url_subpath}"
            else:
                pip_extra_index_url = BASE_TORCH_WHEEL_DOWNLOAD_URL

            ver_matched_pkgs = list(
                filter(
                    lambda pkg: pkg.pkg_ver == pkg_ver
                    and pkg.cuda_ver == cuda_ver
                    and pkg.pip_index_url == pip_index_url
                    and pkg.pip_extra_index_url == pip_extra_index_url,
                    release_dict[pkg_name],
                )
            )
            if len(ver_matched_pkgs) > 0:
                ver_matched_pkgs[0].py_vers.add(py_ver)
                if len(ver_matched_pkgs) > 1:
                    log_warning(f"duplicated torch packages -- {ver_matched_pkgs}")

            else:
                release = GPUPackageRelease(
                    pkg_name=pkg_name,
                    pkg_ver=pkg_ver,
                    py_vers={py_ver},
                    pip_extra_index_url=pip_extra_index_url,
                    pip_index_url=pip_index_url,
                    cuda_ver=cuda_ver,
                    no_cuda=cuda_ver is None,
                )
                release_dict[pkg_name].append(release)

        return cls(**release_dict)

    @property
    def packages(self) -> t.List[t.List[GPUPackageRelease]]:
        return [getattr(self, pkg_name) for pkg_name in self.get_pkg_names()]

    @property
    def has_no_compatible_vers(self):
        return any(len(pkg_name) == 0 for pkg_name in self.get_pkg_names())

    def get_available_cuda_vers(self, pkg_names: t.List[str]):
        if len(pkg_names) == 0:
            return {None}

        pkg: t.List[GPUPackageRelease] = getattr(self, pkg_names[0])
        intersected = set(release.cuda_ver for release in pkg)
        for pkg_name in pkg_names[1:]:
            pkg = getattr(self, pkg_name)
            intersected = intersected.intersection(set(release.cuda_ver for release in pkg))

        return intersected

    def get_available_cudnn_vers(self, pkg_names: t.List[str]):
        return {None}

    def get_available_py_vers(self, pkg_names: t.List[str]):
        if len(pkg_names) == 0:
            return {None}

        pkg: t.List[GPUPackageRelease] = getattr(self, pkg_names[0])
        intersected = set(py_ver for release in pkg for py_ver in release.py_vers)
        for pkg_name in pkg_names[1:]:
            pkg = getattr(self, pkg_name)
            intersected = intersected.intersection(
                set(py_ver for release in pkg for py_ver in release.py_vers)
            )

        return intersected

    def add_constraint(self, constraint: GPUPackageConstraint):
        target_pkg_names = [constraint.pkg_name] if constraint.pkg_name else self.get_pkg_names()
        for pkg_name in target_pkg_names:
            filtered = self.filter_releases_by_constraint(getattr(self, pkg_name), constraint)
            setattr(self, pkg_name, list(filtered))

    def get_latest_releases(self, pkg_names: t.Iterable[str]):
        return [
            max(getattr(self, pkg_name))
            for pkg_name in self.get_pkg_names()
            if pkg_name in pkg_names
        ]

    def get_err_msg_for_constraint(self, pkg_spec: GPUPackageConstraint):
        # TODO
        return ""

    @classmethod
    def get_pkg_names(cls):
        return list(attrs.fields_dict(cls).keys())

    @classmethod
    def requires_system_cuda(cls):
        return False
