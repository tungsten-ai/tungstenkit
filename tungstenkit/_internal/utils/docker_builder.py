import hashlib
import json
import math
import multiprocessing as mp
import shutil
import tarfile
import tempfile
import time
import typing as t
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pydantic
import pytz
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from tungstenkit._versions import pkg_version

from .context import change_workingdir
from .file import is_relative_to

READ_BLOCK_SIZE = 5 * 1024 * 1024  # 5MB
PBAR_PATH_LENGTH = 21
DOCKER_IMAGE_VERSION = "1.0"
DOCKER_IMAGE_OS = "linux"


def _current():
    return datetime.utcnow().replace(tzinfo=pytz.utc)


class DockerHealthcheckConfig(pydantic.BaseModel):
    """
    Holds configuration settings for the HEALTHCHECK feature.

    Test is the test to perform to check that the container is healthy.
    An empty slice means to inherit the default.
    The options are:
    {} : inherit healthcheck
    {"NONE"} : disable healthcheck
    {"CMD", args...} : exec arguments directly
    {"CMD-SHELL", command} : run command with system's default shell

    Reference:
        https://github.com/moby/moby/blob/791549508a3ed3b95d00556d53940b24a54d901a/image/spec/specs-go/v1/image.go
    """

    interval: t.Optional[pydantic.NonNegativeInt] = pydantic.Field(default=None, alias="Interval")
    timeout: t.Optional[pydantic.NonNegativeInt] = pydantic.Field(default=None, alias="Timeout")
    start_period: t.Optional[pydantic.NonNegativeInt] = pydantic.Field(
        default=None, alias="StartPeriod"
    )
    start_interval: t.Optional[pydantic.NonNegativeInt] = pydantic.Field(
        default=None, alias="StartInterval"
    )
    retries: t.Optional[pydantic.NonNegativeInt] = pydantic.Field(default=None, alias="Retries")


class DockerContainerRequiredConfig(pydantic.BaseModel):
    hostname: str = pydantic.Field(default="", alias="Hostname")
    domainname: str = pydantic.Field(default="", alias="Domainname")
    user: str = pydantic.Field(default="", alias="User")
    attach_stdin: bool = pydantic.Field(default=False, alias="AttachStdin")
    attach_stdout: bool = pydantic.Field(default=False, alias="AttachStdout")
    attach_stderr: bool = pydantic.Field(default=False, alias="AttachStderr")
    tty: bool = pydantic.Field(default=False, alias="Tty")
    open_stdin: bool = pydantic.Field(default=False, alias="OpenStdin")
    stdin_once: bool = pydantic.Field(default=False, alias="StdinOnce")
    env: t.Optional[t.List[str]] = pydantic.Field(default=None, alias="Env")
    cmd: t.Optional[t.Union[str, t.List[str]]] = pydantic.Field(default=None, alias="Cmd")
    image: str = pydantic.Field(default="", alias="Image")
    volumes: t.Optional[t.Dict[str, str]] = pydantic.Field(default=None, alias="Volumes")
    working_dir: str = pydantic.Field(default="", alias="WorkingDir")
    entrypoint: t.Optional[t.Union[str, t.List[str]]] = pydantic.Field(
        default=None, alias="Entrypoint"
    )
    on_build: t.Optional[t.List[str]] = pydantic.Field(default=None, alias="OnBuild")
    labels: t.Optional[t.Dict[str, str]] = pydantic.Field(default=None, alias="Labels")


class DockerContainerOptionalConfig(pydantic.BaseModel):
    exposed_ports: t.Optional[t.Set[pydantic.PositiveInt]] = pydantic.Field(
        default=None, alias="ExposedPorts"
    )
    healthcheck: t.Optional[DockerHealthcheckConfig] = pydantic.Field(
        default=None, alias="Healthcheck"
    )
    network_disabled: t.Optional[bool] = pydantic.Field(default=None, alias="NetworkDisabled")
    mac_address: t.Optional[str] = pydantic.Field(default=None, alias="MacAddress")
    stop_signal: t.Optional[str] = pydantic.Field(default=None, alias="StopSignal")
    stop_timeout: t.Optional[int] = pydantic.Field(default=None, alias="StopTimeout")
    shell: t.Optional[t.Union[str, t.List[str]]] = pydantic.Field(default=None, alias="Shell")


class DockerContainerConfig(DockerContainerRequiredConfig, DockerContainerOptionalConfig):
    """
    Contains the configuration data about a container.
    It should hold only portable information about the container.
    Here, "portable" means "independent from the host we are running on".
    Non-portable information *should* appear in HostConfig.
    All fields added to this struct must be marked `omitempty` to keep getting
    predictable hashes from the old `v1Compatibility` configuration.

    Reference:
        https://github.com/moby/moby/blob/791549508a3ed3b95d00556d53940b24a54d901a/api/types/container/config.go
    """

    pass


class DockerV1ImageConfig(pydantic.BaseModel):
    """
    Stores the V1 image configuration.

    Reference:
        https://github.com/moby/moby/blob/2c95ddf4f3948e5c959f69eaf9ef1eef4d0f6a4d/image/image.go#L64
    """

    id: t.Optional[str] = pydantic.Field(default=None)
    created_at: datetime = pydantic.Field(default_factory=_current, alias="created")
    parent_id: t.Optional[str] = pydantic.Field(default=None, alias="parent")
    container: t.Optional[str] = None
    container_config: t.Optional[DockerContainerConfig] = None
    docker_version: t.Optional[str] = None
    author: t.Optional[str] = None
    config: t.Optional[DockerContainerConfig] = None
    architecture: t.Optional[str] = None
    variant: t.Optional[str] = None
    os: t.Optional[str] = None
    size: t.Optional[int] = None


class OCIHistory(pydantic.BaseModel):
    created: datetime = pydantic.Field(default_factory=_current, alias="Created")
    created_by: str = pydantic.Field(alias="CreatedBy")
    comment: t.Optional[str] = pydantic.Field(default=None, alias="Comment")


class DockerImageRootFS(pydantic.BaseModel):
    """
    Describes images root filesystem

    Reference:
        https://github.com/moby/moby/blob/2c95ddf4f3948e5c959f69eaf9ef1eef4d0f6a4d/api/types/types.go#L26
    """

    type_: t.Optional[str] = pydantic.Field(default=None, alias="type")
    diff_ids: t.Optional[t.List[str]] = None


class DockerImageConfig(DockerV1ImageConfig):
    """
    Stores the image configuration

    Reference:
        https://github.com/moby/moby/blob/2c95ddf4f3948e5c959f69eaf9ef1eef4d0f6a4d/image/image.go#L92
    """

    rootfs: t.Optional[DockerImageRootFS] = None
    history: t.Optional[t.List[OCIHistory]] = None


class OCIManifest(pydantic.BaseModel):
    config: str = pydantic.Field(alias="Config")
    repo_tags: t.List[str] = pydantic.Field(alias="RepoTags")
    layers: t.List[str] = pydantic.Field(alias="Layers")


def create_files_image_tarball(
    local_image_name: str,
    files: t.List[Path],
    image_tar_path: Path,
    base_dir: Path,
    *,
    architecture: str = "amd64",
):
    """
    Create a docker image only with files.

    Using this function, `layer.tar` is equal if two files have the same content and path.
    So, the repository will say that "Layer already exists" regardless of the file metadata.
    """
    assert len(files) > 0
    assert all(f.exists() for f in files)
    assert len(local_image_name.split(":")) == 2
    assert str(image_tar_path).endswith(".tar")
    assert not image_tar_path.exists()

    absolute_file_paths = list(set(f.absolute() for f in files))
    base_dir = base_dir.absolute()

    assert all(is_relative_to(f, base_dir) for f in absolute_file_paths)

    local_image_repository, local_image_tag = local_image_name.split(":")

    image_tar_dir = Path(*image_tar_path.parts[:-1])
    image_tar_dir.mkdir(parents=True, exist_ok=True)
    image_tar_path = image_tar_path.absolute()

    # Largest file first in the output docker image
    absolute_file_paths = sorted(absolute_file_paths, key=lambda p: p.stat().st_size, reverse=True)
    relative_file_paths = [p.relative_to(base_dir) for p in absolute_file_paths]
    files_count = len(absolute_file_paths)

    # Console progress view
    progress_cols = [
        TextColumn("{task.description}"),
        BarColumn(bar_width=None),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(compact=True),
    ]

    with tempfile.TemporaryDirectory(prefix="tungsten-build-") as tmpdir_str:
        base_tmp_dir = Path(tmpdir_str)

        with Progress(*progress_cols, expand=True) as progress:
            progress_task_ids = [
                progress.add_task(description="Waiting") for _ in range(files_count)
            ]

            with ThreadPoolExecutor(
                max_workers=max(1, math.floor(0.9 * mp.cpu_count()))
            ) as worker:
                with ThreadPoolExecutor(max_workers=files_count) as executor:
                    # Write {diff_id}/layer.tar
                    with change_workingdir(base_dir):
                        futures: t.List[Future] = []
                        layer_dirs: t.List[Path] = []
                        for layer_idx in range(files_count):
                            futures.append(
                                executor.submit(
                                    _create_file_layer_directory_and_tar_file,
                                    relative_file_paths[layer_idx],
                                    layer_idx=layer_idx,
                                    image_base_dir=base_tmp_dir,
                                    executor=worker,
                                    progress=progress,
                                    progress_task_id=progress_task_ids[layer_idx],
                                )
                            )

                        for fut in futures:
                            layer_dirs.append(fut.result())

                diff_ids = [d.parts[-1] for d in layer_dirs]

                # Write {diff_id}/VERSION
                for i in range(files_count):
                    with (layer_dirs[i] / "VERSION").open("w") as f:
                        f.write(DOCKER_IMAGE_VERSION)

                # Write {diff_id}/json
                for i in range(files_count):
                    layer_config = DockerV1ImageConfig(
                        id=diff_ids[i],
                        parent=None if i == 0 else diff_ids[i - 1],
                        os=DOCKER_IMAGE_OS,
                        architecture=architecture if i == files_count - 1 else None,
                        created=_current()
                        if i == files_count - 1
                        else datetime.fromtimestamp(0.0),
                    )
                    layer_config_dict = json.loads(
                        layer_config.json(exclude_none=True, by_alias=True)
                    )

                    container_config_dict = json.loads(DockerContainerRequiredConfig().json())
                    layer_config_dict["container_config"] = container_config_dict
                    if i == files_count - 1:
                        config_dict = json.loads(
                            DockerContainerRequiredConfig(
                                Env=[
                                    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"  # noqa: E501
                                ],
                                WorkingDir="/",
                            ).json(by_alias=True)
                        )
                        layer_config_dict["config"] = config_dict

                    with (layer_dirs[i] / "json").open("w") as f:
                        serialized_layer_config = json.dumps(layer_config_dict)
                        f.write(serialized_layer_config)

                # Write {image_id}.json
                serialized_image_config = DockerImageConfig(
                    architecture=architecture,
                    config=DockerContainerConfig(
                        Env=["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"],
                        WorkingDir="/",
                    ),
                    history=[
                        OCIHistory(
                            CreatedBy=f"COPY {p} /{p} # tungstenkit",
                            Comment=f"Tungstenkit {pkg_version}",
                        )
                        for p in relative_file_paths
                    ],
                    os=DOCKER_IMAGE_OS,
                    rootfs=DockerImageRootFS(
                        type="layers", diff_ids=["sha256:" + diff_id for diff_id in diff_ids]
                    ),
                ).json(by_alias=True, exclude_none=True, exclude_defaults=True, sort_keys=True)
                image_id = hashlib.sha256(serialized_image_config.encode()).hexdigest()
                image_config_path = base_tmp_dir / (image_id + ".json")
                with (image_config_path).open("w") as f:
                    f.write(serialized_image_config)

                # Write manifest.json
                serialized_manifest = OCIManifest(
                    Config=image_config_path.parts[-1],
                    RepoTags=[local_image_name],
                    Layers=[f"{diff_id}/layer.tar" for diff_id in diff_ids],
                ).json(by_alias=True, exclude_defaults=True, exclude_none=True, sort_keys=True)
                with (base_tmp_dir / "manifest.json").open("w") as f:
                    f.write("[" + serialized_manifest + "]")

                # Write repositories
                repositories_dict = {local_image_repository: {local_image_tag: diff_ids[-1]}}
                serialized_repositories = json.dumps(repositories_dict)
                with (base_tmp_dir / "repositories").open("w") as f:
                    f.write(serialized_repositories)

                # Create image's tar file
                with change_workingdir(base_tmp_dir):
                    with tarfile.open(
                        image_tar_path,
                        "w",
                        bufsize=READ_BLOCK_SIZE * 20,
                        copybufsize=READ_BLOCK_SIZE * 20,
                    ) as tf:
                        all_file_paths = list(p for p in Path().rglob("*") if not p.is_dir())
                        for file_idx in range(len(all_file_paths)):
                            path = all_file_paths[file_idx]
                            filesize = path.stat().st_size

                            with path.open("rb") as fp:
                                fut = worker.submit(tf.addfile, tf.gettarinfo(str(path)), fp)
                                if len(path.parts) != 2 or path.parts[-1] != "layer.tar":
                                    layer_idx_of_file: t.Optional[int] = None
                                else:
                                    layer_idx_of_file = diff_ids.index(path.parts[-2])
                                    formatted_file_path = _formatted_path(
                                        relative_file_paths[layer_idx_of_file]
                                    )
                                while not fut.done():
                                    if layer_idx_of_file is not None:
                                        progress.update(
                                            progress_task_ids[layer_idx_of_file],
                                            description=f"\[{formatted_file_path}] Adding to image tarball",  # noqa: E501
                                            completed=fp.tell(),
                                            total=filesize,
                                        )
                                    time.sleep(0.1)

                                if layer_idx_of_file is not None:
                                    progress.update(
                                        progress_task_ids[layer_idx_of_file],
                                        description=f"\[{formatted_file_path}] Adding to image tarball",  # noqa: E501
                                        completed=filesize,
                                        total=filesize,
                                    )


def _create_file_layer_directory_and_tar_file(
    file_path: Path,
    *,
    layer_idx: int,
    image_base_dir: Path,
    executor: ThreadPoolExecutor,
    progress: Progress,
    progress_task_id: TaskID,
) -> Path:
    tmp_tar_dir = image_base_dir / str(layer_idx)
    tmp_tar_dir.mkdir(exist_ok=True, parents=True)
    tmp_tar_path = tmp_tar_dir / "layer.tar"
    file_stat = file_path.stat()
    truncated_path_str = _formatted_path(file_path)
    progress.update(
        progress_task_id,
        description=f"\[{truncated_path_str}] Waiting",  # noqa: W605
        total=file_stat.st_size,
        visible=True,
    )
    file_buffer = file_path.open("rb")

    # Create {base_tmp_dir}/{layer_idx}/layer.tar
    try:
        fut = executor.submit(
            _create_file_layer_tar_file,
            file_path=file_path,
            tar_path=tmp_tar_path,
            file_buffer=file_buffer,
        )
        while not fut.done():
            progress.update(
                progress_task_id,
                description=f"\[{truncated_path_str}] Creating layer",  # noqa: W605
                completed=file_buffer.tell(),
                visible=True,
            )
            time.sleep(0.1)
    finally:
        file_buffer.close()
    progress.update(progress_task_id, completed=file_stat.st_size)

    # Caculate sha256 checksum
    tar_file_stat = tmp_tar_path.stat()
    progress.update(
        progress_task_id,
        description=f"\[{truncated_path_str}] Calculating checksum",  # noqa: W605
        completed=0,
        total=tar_file_stat.st_size,
        visible=True,
    )
    tar_file_buffer = tmp_tar_path.open("rb")
    try:
        fut = executor.submit(_calculate_layer_tar_checksum, tar_file_buffer)
        while not fut.done():
            progress.update(progress_task_id, completed=tar_file_buffer.tell(), visible=True)
            time.sleep(0.1)
    finally:
        tar_file_buffer.close()
    progress.update(progress_task_id, completed=tar_file_stat.st_size, visible=True)

    layer_dir = image_base_dir / fut.result()
    shutil.move(str(tmp_tar_dir), str(layer_dir))
    return layer_dir


def _create_file_layer_tar_file(file_path: Path, file_buffer: t.IO[bytes], tar_path: Path):
    tarinfo = tarfile.TarInfo(str(file_path))
    filestat = file_path.stat()
    tarinfo.size = filestat.st_size
    tarinfo.mode = filestat.st_mode
    tarinfo.uid = 0
    tarinfo.gid = 0
    tarinfo.uname = "root"
    tarinfo.gname = "root"
    tarinfo.mtime = 0
    with tarfile.open(
        tar_path, "w", bufsize=READ_BLOCK_SIZE * 20, copybufsize=READ_BLOCK_SIZE * 20
    ) as tf:
        tf.addfile(tarinfo, file_buffer)


def _calculate_layer_tar_checksum(layer_tar_buffer: t.IO[bytes]):
    h = hashlib.sha256()

    while True:
        b = layer_tar_buffer.read(READ_BLOCK_SIZE)
        if not b:
            break

        h.update(b)

    return h.hexdigest()


def _formatted_path(path: Path) -> str:
    path_str = str(path)

    if len(path_str) <= PBAR_PATH_LENGTH:
        return path_str + " " * (PBAR_PATH_LENGTH - len(path_str))

    separator = "..."
    chars_count_to_show = PBAR_PATH_LENGTH - len(separator)
    front_chars_count = chars_count_to_show // 2
    back_chars_count = (
        chars_count_to_show // 2 + 1 if chars_count_to_show % 2 == 1 else chars_count_to_show // 2
    )
    front_chars = path_str[:front_chars_count]
    back_chars = path_str[-back_chars_count:]
    return front_chars + separator + back_chars


if __name__ == "__main__":
    create_files_image_tarball(
        "files:4",
        [
            Path("examples/blur-complex/README.md"),
            Path("files-3.tar"),
            Path("examples/failure/tungsten_model.py"),
        ],
        Path("files-4.tar"),
        Path("."),
    )

    # create_files_image_tarball(
    #     "files:4",
    #     [
    #         Path("examples/torch-cpu/mobilenetv2_weights.pth"),
    #         Path("examples/blur-complex/tungsten_model.py"),
    #     ],
    #     Path("files-4.tar"),
    #     Path("."),
    # )
