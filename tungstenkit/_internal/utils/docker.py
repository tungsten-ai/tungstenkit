import json
import os
import shutil
import signal
import subprocess
import threading
import time
import typing as t
from contextlib import contextmanager
from enum import Enum, auto
from pathlib import Path, PurePosixPath

import attrs
import docker
import pydantic
import urllib3
from docker import DockerClient
from docker import errors as docker_errors
from docker.models.containers import Container
from docker.models.images import Image
from docker.types import DeviceRequest, Mount
from rich import print as rprint
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from typing_extensions import Literal

from tungstenkit.exceptions import DockerError, InvalidName

DEFAULT_PUSH_TIMEOUT = 30 * 60
DEFAULT_PULL_TIMEOUT = 30 * 60
CONTAINER_CHECK_INTERVAL_SEC = 0.1
CONTAINER_LOGS_HEADER = "============ Container logs ============"
CONTAINER_LOGS_FOOTER = "========================================"
ENGINE_API_UNAUTHORIZED_ERROR_SUFFIX = "unauthorized: authentication required"


class DockerEngineJSONError(pydantic.BaseModel, extra=pydantic.Extra.allow):
    """
    JSONError in Docker Engine API

    References:
    - https://pkg.go.dev/github.com/docker/docker/pkg/jsonmessage
    - https://github.com/docker/engine/blob/-/pkg/jsonmessage/jsonmessage.go
    """

    code: t.Optional[int] = None
    message: t.Optional[str] = None


class DockerEngineJSONProgress(pydantic.BaseModel, extra=pydantic.Extra.allow):
    """
    JSONProgress in Docker Engine API

    References:
    - https://pkg.go.dev/github.com/docker/docker/pkg/jsonmessage
    - https://github.com/docker/engine/blob/-/pkg/jsonmessage/jsonmessage.go
    """

    current: t.Optional[int] = None
    total: t.Optional[int] = None
    start: t.Optional[int] = None
    hidecounts: t.Optional[bool] = None
    units: t.Optional[str] = None


class DockerEngineJSONMessage(pydantic.BaseModel, extra=pydantic.Extra.allow):
    """
    JSONMessage in Docker Engine API

    References:
    - https://pkg.go.dev/github.com/docker/docker/pkg/jsonmessage
    - https://github.com/docker/engine/blob/-/pkg/jsonmessage/jsonmessage.go
    """

    stream: t.Optional[str] = None
    status: t.Optional[str] = None
    progress: t.Optional[DockerEngineJSONProgress] = pydantic.Field(None, alias="progressDetail")
    progress_message: t.Optional[str] = pydantic.Field(None, alias="progress")
    id: t.Optional[str] = None
    from_: t.Optional[str] = pydantic.Field(None, alias="from")
    time: t.Optional[int] = None
    time_nano: t.Optional[int] = pydantic.Field(None, alias="timeNano")
    error: t.Optional[DockerEngineJSONError] = pydantic.Field(None, alias="errorDetail")
    error_message: t.Optional[str] = pydantic.Field(None, alias="error")


class PullPushFailureReason(Enum):
    UNAUTHORIZED = auto()
    TIMEOUT = auto()
    API_ERROR = auto()
    UNKNOWN = auto()


@attrs.define
class PullPushResult:
    type: Literal["pull", "push"]
    repo: str
    tag: str

    _failure_reason: t.Optional[PullPushFailureReason] = attrs.field(
        default=None, alias="failure_reason"
    )
    _error_message: t.Optional[str] = attrs.field(default=None, alias="error_message")

    @property
    def is_success(self) -> bool:
        return self._failure_reason is None

    @property
    def failure_reason(self) -> t.Optional[PullPushFailureReason]:
        return self._failure_reason

    @property
    def error_message(self) -> t.Optional[str]:
        return self._error_message

    def raise_on_error(self) -> None:
        if not self.is_success:
            full_error_message = f"Failed to {self.type} '{self.repo}:{self.tag}'"
            if self._error_message:
                full_error_message += " - " + self._error_message
            raise DockerError(full_error_message)

    def set_error(
        self, failure_reason: PullPushFailureReason, error_message: t.Optional[str] = None
    ):
        self._failure_reason = failure_reason
        self._error_message = error_message


@attrs.define(kw_only=True)
class ServerContainer:
    ip: str
    port: int
    container: Container


def parse_docker_image_name(name: str) -> t.Tuple[str, t.Optional[str]]:
    path_components = name.split("/")
    last_component_splitted = path_components[-1].split(":")
    if len(last_component_splitted) > 2:
        raise InvalidName(f"'{name}' (format: '<repo_name>[:<tag>]')")

    repo = "/".join(path_components[:-1] + [last_component_splitted[0]])
    if len(last_component_splitted) == 2:
        tag: t.Optional[str] = last_component_splitted[1]
    else:
        tag = None
    if not repo:
        raise InvalidName("'' (format: '<repo_name>[:<tag>]')")
    return repo, tag


def get_docker_client(*args, **kwargs) -> DockerClient:
    try:
        return docker.from_env(*args, **kwargs)
    except docker_errors.DockerException:
        pass

    subprocess_args = [
        "docker",
        "context",
        "ls",
        "--format",
        r"{{- if .Current -}} {{- .DockerEndpoint -}} {{- end -}}",
    ]
    docker_host = subprocess.check_output(subprocess_args).decode("utf-8").strip()
    assert docker_host
    os.environ["DOCKER_HOST"] = docker_host
    return docker.from_env(*args, **kwargs)


def check_if_docker_available():
    if shutil.which("docker") is None:
        raise DockerError("'docker' command is not available. Please install docker.")
    try:
        docker_client = get_docker_client(timeout=10)
        assert docker_client.ping()
    except (docker_errors.DockerException, AssertionError):
        raise DockerError(
            "Fail to connect to the docker host. Please check if docker is installed properly."
        )


def login_to_docker_registry(
    registry: str, auth_config: t.Dict[str, str], check: bool = True
) -> bool:
    """Update $HOME/.docker/config.json"""
    ret = subprocess.run(
        [
            "docker",
            "login",
            registry,
            "--username",
            auth_config["username"],
            "--password",
            auth_config["password"],
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and ret.returncode != 0:
        raise DockerError(f"Failed to login to registry '{registry}'")
    return ret == 0


def push_to_docker_registry(
    repo: str,
    tag: str,
    docker_client: DockerClient,
    auth_config: t.Optional[t.Dict[str, str]] = None,
) -> PullPushResult:
    return _run_pull_or_push(
        "push", docker_client=docker_client, repo=repo, tag=tag, auth_config=auth_config
    )


def pull_from_docker_registry(
    repo: str,
    tag: str,
    docker_client: DockerClient,
    auth_config: t.Optional[t.Dict[str, str]] = None,
) -> PullPushResult:
    return _run_pull_or_push(
        "pull", docker_client=docker_client, repo=repo, tag=tag, auth_config=auth_config
    )


def load_container_logs(
    container_name_or_id: str,
    header: bool = True,
    footer: bool = True,
    docker_client: t.Optional[DockerClient] = None,
) -> str:
    docker_client = docker_client if docker_client else get_docker_client()
    container: Container = docker_client.containers.get(container_name_or_id)
    logs = container.logs().decode("utf-8")
    if header:
        logs = CONTAINER_LOGS_HEADER + "\n" + logs
    if footer:
        logs += "\n" + CONTAINER_LOGS_FOOTER
    return logs


def print_container_logs(
    container_name_or_id: str, pretty: bool = True, docker_client: t.Optional[DockerClient] = None
):
    err_msg = CONTAINER_LOGS_HEADER + "\n"
    err_msg += load_container_logs(container_name_or_id, docker_client=docker_client)
    err_msg += CONTAINER_LOGS_FOOTER
    if pretty:
        rprint(err_msg)
    else:
        print(err_msg)


def remove_docker_container(
    container_name_or_id: str, force: bool = False, docker_client: t.Optional[DockerClient] = None
):
    docker_client = docker_client if docker_client else get_docker_client()
    try:
        container: Container = docker_client.containers.get(container_name_or_id)
        container.remove(force=force)
    except (docker_errors.NotFound, docker_errors.APIError) as e:
        if force:
            return
        raise DockerError(str(e))


def remove_docker_image(
    image_name_or_id: str,
    force: bool = False,
    docker_client: t.Optional[DockerClient] = None,
):
    docker_client = docker_client if docker_client else get_docker_client()
    try:
        docker_client.api.remove_image(image_name_or_id, force=force)
    except (docker_errors.NotFound, docker_errors.APIError) as e:
        if force:
            return
        raise DockerError(str(e))


def copy_from_image(
    image_name_or_id: str,
    path_in_image: PurePosixPath,
    path_in_host: Path,
    image_desc: t.Optional[str] = None,
    docker_client: t.Optional[DockerClient] = None,
) -> None:
    path_in_host = path_in_host.resolve()
    if path_in_host.exists():
        if not path_in_host.is_dir():
            raise DockerError(f"Not a directory: {path_in_host}")

    path_in_host.parent.mkdir(parents=True, exist_ok=True)

    docker_client = docker_client if docker_client else get_docker_client()
    image: Image = docker_client.images.get(image_name_or_id)

    container: Container = docker_client.containers.create(image)

    try:
        _cp(
            f"{container.name}:{path_in_image}",
            str(path_in_host.resolve()),
            err_msg=f"Failed to extract {image_desc if image_desc else image_name_or_id}",
        )
    finally:
        remove_docker_container(container.id, docker_client=docker_client)


def export_image_to_file(
    image_name_or_id: str,
    output_path: Path,
    image_desc: t.Optional[str] = None,
    docker_client: t.Optional[DockerClient] = None,
):
    # Get container
    docker_client = docker_client if docker_client else get_docker_client()
    image: Image = docker_client.images.get(image_name_or_id)
    container: Container = docker_client.containers.create(image)

    # Export the container
    try:
        _export(
            container.name,
            output=str(output_path),
            err_msg=f"Failed to export {image_desc if image_desc else image_name_or_id}",
        )
    finally:
        remove_docker_container(container.id, docker_client=docker_client)


def import_image_from_file(tarball_path: Path, name: str):
    _import(str(tarball_path), name, err_msg=f"Failed to import '{tarball_path}' to {name}")


@contextmanager
def start_server_container(
    image_name_or_id: str,
    internal_port: int,
    command: str,
    host: str = "0.0.0.0",
    mounts: t.Optional[t.List[Mount]] = None,
    device_requests: t.Optional[t.List[DeviceRequest]] = None,
    environment: t.Optional[t.Dict[str, str]] = None,
    docker_client: t.Optional[DockerClient] = None,
):
    _docker_client = docker_client if docker_client else get_docker_client()
    internal_port_with_type = f"{internal_port}/tcp"
    termination_event = threading.Event()
    orig_sig_handler = signal.getsignal(signal.SIGTERM)

    # TODO environment variables
    _docker_client = docker_client if docker_client else get_docker_client()

    retry = 0
    while True:
        try:
            container: Container = _docker_client.containers.run(
                image_name_or_id,
                command,
                detach=True,
                device_requests=device_requests,
                mounts=mounts,
                environment=environment,
                ports={internal_port_with_type: 0},
            )
            break
        except docker_errors.APIError as e:
            if retry < 5:
                time.sleep(0.1)
                retry += 1
            else:
                raise e

        except BaseException:
            if "container" in locals():
                container.remove(force=True)

    def handle_signal(*args, **argv):
        if termination_event.is_set():
            raise DockerError(
                "Container unexpectedly terminated\n"
                f"{load_container_logs(container.id, docker_client=_docker_client)}\n"
            )
        else:
            orig_sig_handler(*args, **argv)

    def check_model_server():
        _container: Container = _docker_client.containers.get(container.id)
        while not termination_event.is_set():
            _container.reload()
            if not termination_event.is_set() and _container.status == "exited":
                termination_event.set()
                os.kill(os.getpid(), signal.SIGTERM)
            else:
                time.sleep(CONTAINER_CHECK_INTERVAL_SEC)

    try:
        signal.signal(signal.SIGTERM, handle_signal)

        thread_checking_model_container = threading.Thread(target=check_model_server, daemon=True)
        thread_checking_model_container.start()

        # Wait until the port is ready
        ip = "127.0.0.1"
        port_in_url = None
        port_check_start_time = time.monotonic()
        while port_in_url is None and time.monotonic() - port_check_start_time < 5:
            ports = _docker_client.containers.get(container.id).ports
            try:
                for expose_spec in ports[internal_port_with_type]:
                    if expose_spec["HostIp"] == host:
                        port_in_url = int(expose_spec["HostPort"])

                if port_in_url is None:
                    time.sleep(CONTAINER_CHECK_INTERVAL_SEC)

            except KeyError:
                time.sleep(CONTAINER_CHECK_INTERVAL_SEC)

        if port_in_url is None:
            raise DockerError("Fail to expose a port for a container")

        yield ServerContainer(container=container, ip=ip, port=port_in_url)

    finally:
        termination_event.set()
        container.remove(force=True)
        signal.signal(signal.SIGTERM, orig_sig_handler)


def run(*docker_run_args: str):
    subprocess.run(["docker", "run"] + list(docker_run_args))


def _run_pull_or_push(
    method: Literal["pull", "push"],
    docker_client: DockerClient,
    repo: str,
    tag: str,
    auth_config: t.Optional[t.Dict[str, str]] = None,
) -> PullPushResult:
    if method == "pull":
        fn = docker_client.api.pull
    elif method == "push":
        fn = docker_client.images.push
    else:
        raise NotImplementedError(method)

    tasks: t.Dict[str, t.Any] = dict()
    result = PullPushResult(type=method, repo=repo, tag=tag)
    try:
        with _build_pull_push_progress() as progress:
            for line in fn(
                repo,
                tag=tag,
                stream=True,
                auth_config=auth_config,
            ):
                try:
                    loaded_json = json.loads(line)
                except json.JSONDecodeError:
                    continue

                resp = DockerEngineJSONMessage.parse_obj(loaded_json)
                if resp.error is not None:
                    err_msg = resp.error.message if isinstance(resp.error.message, str) else None
                    if err_msg and err_msg.endswith(ENGINE_API_UNAUTHORIZED_ERROR_SUFFIX):
                        result.set_error(PullPushFailureReason.UNAUTHORIZED, err_msg)
                    else:
                        result.set_error(PullPushFailureReason.API_ERROR, err_msg)
                    break

                _show_pull_push_progress(resp, progress, tasks)

    except urllib3.exceptions.ReadTimeoutError:
        result.set_error(
            PullPushFailureReason.TIMEOUT,
            f"Timeout reached while {method}ing image '{repo}:{tag}'",
        )
    except docker_errors.APIError as e:
        err_msg = e.explanation if isinstance(e.explanation, str) else None
        if e.status_code == 401 or (
            err_msg and err_msg.endswith(ENGINE_API_UNAUTHORIZED_ERROR_SUFFIX)
        ):
            result.set_error(PullPushFailureReason.UNAUTHORIZED, err_msg)
        else:
            result.set_error(PullPushFailureReason.API_ERROR, err_msg)
    except Exception as e:
        raise e

    return result


def _show_pull_push_progress(msg: DockerEngineJSONMessage, progress: Progress, tasks: t.Dict):
    status = msg.status
    id = msg.id

    if status is None:
        return

    if id is None:
        return

    desc = _docker_status_to_desc(status, id)
    if status in ["Download complete", "Pushed", "Pull complete"]:
        if id in tasks.keys():
            if "total" in tasks[id]:
                completed = tasks[id]["total"]
            else:
                completed = None
            progress.update(tasks[id]["task_id"], description=desc, completed=completed)

    elif status in ["Downloading", "Extracting", "Pushing"]:
        if id in tasks.keys():
            if msg.progress and msg.progress.current:
                progress.update(
                    tasks[id]["task_id"],
                    description=desc,
                    completed=msg.progress.current,
                    total=msg.progress.total,
                )
        elif msg.progress and msg.progress.total:
            if id in tasks:
                progress.update(tasks[id]["task_id"], description=desc, total=msg.progress.total)
            else:
                tasks[id] = {
                    "task_id": progress.add_task(desc, total=msg.progress.total),
                    "total": msg.progress.total,
                }

    elif status in ["Preparing", "Layer already exists", "Already exists", "Waiting"]:
        total = None if status == "Waiting" else 0
        if id in tasks:
            progress.update(tasks[id]["task_id"], description=desc, total=total)
        else:
            tasks[id] = {"task_id": progress.add_task(desc, total=total)}


def _build_pull_push_progress():
    cols = [
        TextColumn("{task.description}"),
        BarColumn(bar_width=None),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(compact=True),
    ]
    return Progress(*cols)


def _docker_status_to_desc(status: str, id: str) -> str:
    return f"[blue]\[{id}] {status}[/blue]"


def _cp(src: str, dest: str, err_msg: str):
    args = ["docker", "cp", src, dest]
    try:
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError:
        raise DockerError(err_msg)


def _export(container_name_or_id: str, output: str, err_msg: str):
    try:
        subprocess.run(["docker", "export", "--output", output, container_name_or_id], check=True)
    except subprocess.CalledProcessError:
        raise DockerError(err_msg)


def _import(tarball: str, name: str, err_msg: str):
    try:
        subprocess.run(["docker", "import", tarball, name], check=True)
    except subprocess.CalledProcessError:
        raise DockerError(err_msg)
