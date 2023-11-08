import sys
import typing as t

import attrs
import pytest
from packaging.version import Version

from tungstenkit import exceptions
from tungstenkit._internal.containerize.dockerfile_generators.gpu_pkg_collections import (
    GPUPackageCollection,
    GPUPackageConstraint,
    GPUPackageRelease,
    gpu_pkg_collection_class_dict,
    supported_gpu_pkg_names,
)
from tungstenkit._internal.containerize.dockerfile_generators.pkg_manager import (
    PythonPackageManager,
)

pkg_a_releases = [
    GPUPackageRelease(
        pkg_name="a",
        pkg_ver=Version("0.1.1+cu116"),
        no_cuda=False,
        cuda_ver=Version("11.6"),
        py_vers={Version("3.7"), Version("3.8")},
    ),
    GPUPackageRelease(
        pkg_name="a",
        pkg_ver=Version("0.1.2+cu116"),
        no_cuda=False,
        cuda_ver=Version("11.6"),
        py_vers={Version("3.7"), Version("3.8")},
    ),
    GPUPackageRelease(
        pkg_name="a",
        pkg_ver=Version("0.1.3+cu117"),
        no_cuda=False,
        cuda_ver=Version("11.7"),
        py_vers={Version("3.7"), Version("3.8"), Version("3.9"), Version("3.10")},
    ),
]

pkg_b_releases = [
    GPUPackageRelease(
        pkg_name="b",
        pkg_ver=Version("1.1.1+cu116"),
        no_cuda=False,
        cuda_ver=Version("11.6"),
        py_vers={Version("3.7"), Version("3.8"), Version("3.9")},
    ),
    GPUPackageRelease(
        pkg_name="b",
        pkg_ver=Version("1.1.2+cu117"),
        no_cuda=False,
        cuda_ver=Version("11.7"),
        py_vers={Version("3.7"), Version("3.8"), Version("3.9")},
    ),
    GPUPackageRelease(
        pkg_name="b",
        pkg_ver=Version("1.1.3+cu118"),
        no_cuda=False,
        cuda_ver=Version("11.8"),
        py_vers={Version("3.7"), Version("3.8"), Version("3.9")},
    ),
]


@attrs.define
class DummyCollection(GPUPackageCollection):
    a: t.List[GPUPackageRelease]
    b: t.List[GPUPackageRelease]

    @classmethod
    def from_remote(cls):
        return cls(a=pkg_a_releases, b=pkg_b_releases)

    @classmethod
    def get_pkg_names(cls):
        return list(attrs.fields_dict(cls).keys())

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


gpu_pkg_collection_class_dict["dummy"] = DummyCollection  # type: ignore
for pkg_name in DummyCollection.get_pkg_names():
    supported_gpu_pkg_names.update(pkg_name)


def test_infer_cuda_version():
    pkg_manager = PythonPackageManager()
    pkg_manager.add_requirement_str("a")
    pkg_manager.set_gpu(gpu=True)
    cuda_ver = pkg_manager.infer_cuda_ver()
    assert cuda_ver == Version("11.7")

    pkg_manager = PythonPackageManager()
    pkg_manager.add_requirement_str("a")
    pkg_manager.add_requirement_str("b")
    pkg_manager.set_gpu(gpu=True)
    cuda_ver = pkg_manager.infer_cuda_ver()
    assert cuda_ver == Version("11.7")

    pkg_manager = PythonPackageManager()
    pkg_manager.add_requirement_str("a")
    pkg_manager.add_requirement_str("b==1.1.1")
    pkg_manager.set_gpu(gpu=True)
    cuda_ver = pkg_manager.infer_cuda_ver()
    assert cuda_ver == Version("11.6")

    pkg_manager = PythonPackageManager()
    pkg_manager.add_requirement_str("a")
    pkg_manager.add_requirement_str("b==1.1.3")
    pkg_manager.set_gpu(gpu=True)
    with pytest.raises(exceptions.NoCompatiblePythonPackage):
        cuda_ver = pkg_manager.infer_cuda_ver()


def test_infer_python_version():
    pkg_manager = PythonPackageManager()
    pkg_manager.add_requirement_str("a")
    pkg_manager.set_gpu(gpu=True)
    py_ver = pkg_manager.infer_python_ver()
    assert py_ver == Version("3.10")

    pkg_manager = PythonPackageManager()
    pkg_manager.add_requirement_str("a")
    pkg_manager.set_gpu(gpu=True)
    py_ver = pkg_manager.infer_python_ver()
    assert py_ver == Version("3.10")

    pkg_manager = PythonPackageManager()
    pkg_manager.add_requirement_str("a==0.1.2")
    pkg_manager.add_requirement_str("b==1.1.1")
    pkg_manager.set_gpu(gpu=True)
    py_ver = pkg_manager.infer_python_ver()
    assert py_ver == Version("3.8")

    this_py_ver = Version(f"{sys.version_info.major}.{sys.version_info.minor}")
    pkg_manager = PythonPackageManager()
    py_ver = pkg_manager.infer_python_ver()
    assert py_ver == this_py_ver
    pkg_manager = PythonPackageManager()
    py_ver = pkg_manager.infer_python_ver()
    assert py_ver == this_py_ver


def test_infer_gpu_pkg_ver():
    pkg_manager = PythonPackageManager()
    pkg_manager.add_requirement_str("a")
    pkg_manager.add_requirement_str("b==1.1.1")
    pkg_manager.set_gpu(True)
    cuda_ver = pkg_manager.infer_cuda_ver()
    pkg_manager.set_cuda_equal_to(cuda_ver)
    py_ver = pkg_manager.infer_python_ver()
    pkg_manager.set_python_equal_to(py_ver)
    requirements = pkg_manager.list_gpu_pkg_pip_requirements()
    assert any(r.name == "a" and r.spec == Version("0.1.2+cu116") for r in requirements)
    pkg_manager = PythonPackageManager()

    pkg_manager = PythonPackageManager()
    pkg_manager.add_requirement_str("a==0.1.2")
    pkg_manager.add_requirement_str("b")
    pkg_manager.set_gpu(True)
    cuda_ver = pkg_manager.infer_cuda_ver()
    pkg_manager.set_cuda_equal_to(cuda_ver)
    py_ver = pkg_manager.infer_python_ver()
    pkg_manager.set_python_equal_to(py_ver)
    requirements = pkg_manager.list_gpu_pkg_pip_requirements()
    assert any(r.name == "b" and r.spec == Version("1.1.1+cu116") for r in requirements)

    pkg_manager = PythonPackageManager()
    pkg_manager.add_requirement_str("a")
    pkg_manager.add_requirement_str("b")
    pkg_manager.set_gpu(True)
    cuda_ver = pkg_manager.infer_cuda_ver()
    pkg_manager.set_cuda_equal_to(cuda_ver)
    py_ver = pkg_manager.infer_python_ver()
    pkg_manager.set_python_equal_to(py_ver)
    requirements = pkg_manager.list_gpu_pkg_pip_requirements()
    assert any(r.name == "a" and r.spec == Version("0.1.3+cu117") for r in requirements)
    assert any(r.name == "b" and r.spec == Version("1.1.2+cu117") for r in requirements)
