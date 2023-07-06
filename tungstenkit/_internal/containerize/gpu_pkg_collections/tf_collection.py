import typing as t

import attrs
import bs4
import requests
from packaging.version import Version

from tungstenkit.exceptions import PythonPackageMetadataError

from .base_collection import GPUPackageCollection
from .common import GPUPackageConstraint, GPUPackageRelease

TF_METADATA_URL = "https://www.tensorflow.org/install/source"


@attrs.define
class TFCollection(GPUPackageCollection):
    releases: t.List[GPUPackageRelease]

    @classmethod
    def from_remote(cls):
        all_releases: t.List[GPUPackageRelease] = []
        # TODO add parse error type

        resp = requests.get(TF_METADATA_URL, timeout=30)
        if not resp.ok:
            raise PythonPackageMetadataError(
                "Fail to fetch Tensorflow package metadata: "
                f"failed to get HTML from {TF_METADATA_URL} "
                f"({resp.status_code}: {resp.reason})"
            )

        parse_error = PythonPackageMetadataError(
            "Fail to fetch Tensorflow package metadata: "
            f"error while parsing HTML at {TF_METADATA_URL}."
        )
        soup = bs4.BeautifulSoup(resp.content, "html.parser")
        name_tag = soup.find("h4", id="gpu")
        if (
            name_tag is None
            or name_tag.next_sibling is None
            or name_tag.next_sibling.next_sibling is None
        ):
            raise parse_error

        pkg_table: bs4.element.Tag = name_tag.next_sibling.next_sibling  # type: ignore
        rows: t.List[bs4.element.Tag] = pkg_table.find_all("tr")
        if not rows:
            raise parse_error

        for row_idx, row in enumerate(rows):
            if row_idx == 0:
                continue

            cols: t.List[bs4.element.Tag] = row.find_all("th") + row.find_all("td")
            if len(cols) != 6:
                raise parse_error

            col_texts = [col.text for col in cols]
            pkg_str, py_vers_str, _, _, cudnn_ver_str, cuda_ver_str = col_texts
            gpu_pkg_name, pkg_ver_str = pkg_str.split("-")
            pkg_ver = Version(pkg_ver_str)
            py_vers = set()
            for py_ver_range in py_vers_str.split(","):
                if "-" in py_ver_range:
                    start_ver_str, final_ver_str = py_ver_range.split("-")
                    major, start_minor = start_ver_str.split(".")
                    start_minor = int(start_minor)
                    final_minor = int(final_ver_str.split(".")[-1])
                    for minor in range(start_minor, final_minor + 1):
                        py_vers.add(Version(f"{major}.{minor}"))
                else:
                    py_vers.add(Version(py_ver_range))
            cuda_ver = Version(cuda_ver_str)
            cudnn_ver = Version(cudnn_ver_str)

            gpu_release = GPUPackageRelease(
                pkg_name=gpu_pkg_name,
                pkg_ver=pkg_ver,
                py_vers=py_vers,
                no_cuda=False,
                cuda_ver=cuda_ver,
                cudnn_ver=cudnn_ver,
            )
            cpu_release = GPUPackageRelease(
                pkg_name="tensorflow",
                no_cuda=True,
                pkg_ver=pkg_ver,
                py_vers=py_vers,
            )
            all_releases.append(cpu_release)
            all_releases.append(gpu_release)

        return TFCollection(releases=all_releases)

    @classmethod
    def get_pkg_names(cls):
        return {"tensorflow", "tensorflow-gpu", "tensorflow_gpu"}

    @property
    def has_no_compatible_vers(self):
        return len(self.releases) == 0

    def get_available_cuda_vers(self, pkg_names: t.List[str]):
        return {r.cuda_ver for r in self.releases}

    def get_available_cudnn_vers(self, pkg_names: t.List[str]):
        return {r.cudnn_ver for r in self.releases}

    def get_available_py_vers(self, pkg_names: t.List[str]):
        py_vers = set()
        for r in self.releases:
            py_vers.update(r.py_vers)
        return py_vers

    def add_constraint(self, constraint: GPUPackageConstraint):
        self.releases = self.filter_releases_by_constraint(self.releases, constraint)

    def get_latest_releases(self, pkg_names: t.Iterable[str]):
        return [max(self.releases)] if pkg_names else []

    def get_err_msg_for_constraint(self, pkg_spec: GPUPackageConstraint):
        # TODO
        return ""

    @classmethod
    def requires_system_cuda(cls):
        return True
