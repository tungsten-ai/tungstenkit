#!/usr/bin/env python

"""
Write requirements.txt and pyproject.toml to the package.
They are used for building docker images.
"""

import subprocess
from pathlib import Path

from tungstenkit._internal import containerize
from tungstenkit._versions import py_version

pyproject_toml_path_in_proj = Path(__file__).parent.parent / "pyproject.toml"
if not pyproject_toml_path_in_proj.is_file():
    raise FileNotFoundError(pyproject_toml_path_in_proj)


requirements_txt_path_in_pkg = (
    Path(containerize.__file__).parent / "metadata" / "tungstenkit" / "requirements.txt"
)
pyproject_toml_path_in_pkg = requirements_txt_path_in_pkg.with_name(
    pyproject_toml_path_in_proj.name
)

requirements_txt_path_in_pkg.parent.mkdir(exist_ok=True)

subprocess.run(
    [
        "poetry",
        "export",
        "--without-hashes",
        "-f",
        "requirements.txt",
        "-o",
        str(requirements_txt_path_in_pkg),
    ],
    check=True,
)
print(requirements_txt_path_in_pkg.read_text())
print(f"Written to {requirements_txt_path_in_pkg}")
print()

included_pyproject_toml = """
[project]
name = "tungstenkit"
dynamic = ["dependencies"]
version = "{version}"
""".format(
    version=str(py_version)
)
included_pyproject_toml += """
[tool.setuptools.dynamic]
dependencies = {file = ["requirements.txt"]}
"""
pyproject_toml_path_in_pkg.write_text(included_pyproject_toml)
print(included_pyproject_toml)
print(f"Written to {pyproject_toml_path_in_proj}")
