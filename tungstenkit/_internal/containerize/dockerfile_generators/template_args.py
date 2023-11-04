import typing as t
from pathlib import Path, PurePosixPath

import attrs
from packaging.version import Version

from tungstenkit._internal.constants import WORKING_DIR_IN_CONTAINER
from tungstenkit._versions import pkg_version

from .base_images import BaseImage


@attrs.define(kw_only=True)
class TemplateArgs:
    # Docker
    image: BaseImage

    # Tungsten
    tungstenkit_version: str = str(pkg_version)
    python_entrypoint: str
    large_file_rel_paths: t.List[Path]
    small_files_base_dir_rel_path: Path
    tungsten_env_vars: t.Dict[str, str] = attrs.field(factory=dict)
    home_dir_in_container: PurePosixPath = attrs.field(default=WORKING_DIR_IN_CONTAINER)
    copy_files: t.List[t.Tuple[str, str]] = attrs.field(factory=list)

    # System
    device: str
    gpu_mem_gb: float
    system_packages: t.List[str] = attrs.field(factory=list)
    dockerfile_commands: t.List[str] = attrs.field(factory=list)
    env_vars: t.Dict[str, str] = attrs.field(factory=dict)
    skip_install_system_packages: bool = attrs.field(default=False)

    # Python
    python_version: Version
    pip_wheels_in_build_ctx: t.List[Path] = attrs.field(factory=list)
    pip_requirements_txt_in_build_ctx: t.Optional[Path] = attrs.field(default=None)
    list_pip_install_args: t.List[t.List[str]] = attrs.field(factory=list)
    skip_install_python_packages: bool = attrs.field(default=False)
