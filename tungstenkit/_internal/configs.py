import os
import tempfile
import typing as t
from pathlib import Path

from filelock import FileLock
from packaging.version import Version
from pydantic import AnyHttpUrl, BaseModel, Field, create_model, validator

from tungstenkit._internal.constants import (
    CONFIG_DIR,
    LOCK_DIR,
    MAX_SUPPORTED_PYTHON_VER,
    MIN_SUPPORTED_PYTHON_VER,
)
from tungstenkit._internal.io import BaseIO, FileType
from tungstenkit._internal.io_schema import get_filetypes
from tungstenkit.exceptions import NotLoggedIn

CONFIG_PATH = CONFIG_DIR / "config.json"
CONFIG_LOCK_PATH = LOCK_DIR / "config.json.lock"


class _Version(Version):
    validate_always = True

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: t.Any):
        if isinstance(v, Version):
            return v
        if not isinstance(v, str):
            raise ValueError(f"Should be 'str', not '{type(v)}'.")
        return cls(v)


def _default_include_files():
    return ["*"]


def _default_exclude_files():
    return [
        ".*/",
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".venv",
        "venv",
        ".env",
        "env",
        ".git*",
        ".vscode",
        ".*cache",
        ".ipynb_checkpoints",
    ]


# TODO print warnings if there are ignored fields
# TODO more validators (e.g., include_files)
class BuildConfig(BaseModel):
    gpu: bool = False
    mem_gb: int = 8
    gpu_mem_gb: int = 16

    python_packages: t.List[str] = Field(default_factory=list)
    include_files: t.List[str] = Field(default_factory=_default_include_files)
    copy_files: t.List[t.Tuple[str, str]] = Field(default_factory=list)
    exclude_files: t.List[str] = Field(default_factory=_default_exclude_files)
    pip_wheels: t.List[Path] = Field(default_factory=list)
    environment_variables: t.Dict[str, str] = Field(default_factory=dict)
    tungsten_environment_variables: t.Dict[str, str] = Field(default_factory=dict)

    system_packages: t.List[str] = Field(default_factory=list)
    dockerfile_commands: t.List[str] = Field(default_factory=list)
    python_version: t.Optional[_Version] = None
    cuda_version: t.Optional[_Version] = None

    base_image: t.Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    @validator("cuda_version")
    def validate_cuda_ver(cls, v, values, **kwargs):
        if not values["gpu"] and v is not None:
            raise ValueError("'gpu' is not set")
        return v

    @validator("python_version")
    def validate_py_ver(cls, v: t.Optional[_Version]):
        if v is not None:
            if v < MIN_SUPPORTED_PYTHON_VER or v > MAX_SUPPORTED_PYTHON_VER:
                raise ValueError(
                    f"unsupported Python version: {str(v)}. "
                    "Tungstenkit supports Python version "
                    f"from {MIN_SUPPORTED_PYTHON_VER} to {MAX_SUPPORTED_PYTHON_VER}"
                )


class ModelConfig(BuildConfig):
    batch_size: int = 1
    readme_md: t.Optional[Path] = None
    input_schema: t.Dict
    output_schema: t.Dict
    demo_output_schema: t.Dict
    input_filetypes: t.Dict[str, FileType]
    output_filetypes: t.Dict[str, FileType]
    demo_output_filetypes: t.Dict[str, FileType]

    @classmethod
    def with_types(
        cls, input_cls: t.Type[BaseIO], output_cls: t.Type[BaseIO], demo_output_cls: t.Type[BaseIO]
    ):
        input_filetypes = get_filetypes(input_cls)
        output_filetypes = get_filetypes(output_cls)
        demo_output_filetypes = get_filetypes(demo_output_cls)
        return create_model(
            cls.__name__,
            __base__=cls,
            input_schema=(t.Dict, Field(default_factory=input_cls.schema)),
            output_schema=(t.Dict, Field(default_factory=output_cls.schema)),
            demo_output_schema=(t.Dict, Field(default_factory=demo_output_cls.schema)),
            input_filetypes=(t.Dict, Field(default=input_filetypes)),
            output_filetypes=(t.Dict, Field(default=output_filetypes)),
            demo_output_filetypes=(t.Dict, Field(default=demo_output_filetypes)),
        )

    @validator("readme_md")
    def validate_readme(cls, v):
        if v is not None:
            readme_path = Path(v).resolve()
            if not readme_path.exists():
                raise ValueError(f"Not found: {v}")
            if not readme_path.is_file():
                raise ValueError(f"Not a file: {v}")
            return readme_path


class TungstenClientConfig(BaseModel):
    url: AnyHttpUrl
    access_token: str

    def save(self, path: t.Optional[Path] = None, lock_path: t.Optional[Path] = None):
        path = path if path else CONFIG_PATH
        lock_path = lock_path if lock_path else CONFIG_LOCK_PATH

        dumped = self.json()
        tmp_config_fd, tmp_config_path_str = tempfile.mkstemp(suffix=path.name)
        try:
            tmp_config_path = Path(tmp_config_path_str)
            with FileLock(lock_path, timeout=30.0):
                tmp_config_path.write_text(dumped)
                os.close(tmp_config_fd)
                os.replace(tmp_config_path, path)
        finally:
            try:
                os.close(tmp_config_fd)
            except OSError:
                pass

    @staticmethod
    def from_env(path: t.Optional[Path] = None) -> "TungstenClientConfig":
        path = path if path else CONFIG_PATH
        if not path.exists():
            raise NotLoggedIn("Please log in first")
        # TODO catch a pydantic exception and convert to a tungsten exception.
        return TungstenClientConfig.parse_raw(path.read_text())
