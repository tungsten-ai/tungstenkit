import os
import shutil
import time
import typing as t
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from uuid import uuid4

import attrs
import requests
from docker.types import DeviceRequest, Mount

from tungstenkit import exceptions
from tungstenkit._internal.logging import log_info
from tungstenkit._internal.model_server.enums import ModelServerMode
from tungstenkit._internal.storables import ModelData
from tungstenkit._internal.utils.docker import ServerContainer, start_server_container
from tungstenkit._internal.utils.file import convert_to_unique_path
from tungstenkit._internal.utils.json import apply_to_jsonable
from tungstenkit._internal.utils.uri import (
    check_if_file_uri,
    get_path_from_file_url,
    get_pure_posix_path_from_file_uri,
)

MODEL_CHECK_INTERVAL = 0.2
MODEL_CONTAINER_MODE = ModelServerMode.FILE_TUNNEL.value
MODEL_CONTAINER_PORT = 3000


@attrs.define
class ModelContainer(ServerContainer):
    model_name: str
    bind_dir_in_host: Path
    bind_dir_in_container: PurePosixPath

    def __attrs_post_init__(self):
        self.bind_dir_in_host = self.bind_dir_in_host.resolve()

    @property
    def url(self):
        return f"http://{self.ip}:{self.port}"

    def wait_for_setup(self):
        log_info("Setting up the model")
        while True:
            try:
                requests.get(self.url, timeout=0.5)
                break

            except requests.ConnectionError:
                time.sleep(MODEL_CHECK_INTERVAL)

    def convert_file_uris_in_inputs(
        self, inputs: t.List[t.Dict], move: bool = False
    ) -> t.Tuple[t.List[t.Dict], t.List[Path]]:
        saved_file_paths: t.List[Path] = []
        saved_file_uris: t.Dict[str, str] = dict()

        with ThreadPoolExecutor(max_workers=8) as executor:
            future_list: t.List[Future] = []

            def convert_file_uri(file_uri: str) -> str:
                if file_uri in saved_file_uris:
                    return saved_file_uris[file_uri]

                src_in_host = get_path_from_file_url(file_uri)
                if not src_in_host.exists():
                    raise exceptions.InvalidInput(f"File not found: {src_in_host}")
                elif not src_in_host.is_file():
                    raise exceptions.InvalidInput(f"Not a file: {src_in_host}")

                dest_in_host = self.bind_dir_in_host / src_in_host.name
                dest_in_host = convert_to_unique_path(dest_in_host)
                dest_in_host.touch()
                dest_in_container = self.bind_dir_in_container / dest_in_host.name
                if move:
                    os.replace(src_in_host, dest_in_host)
                else:
                    fut = executor.submit(shutil.copy, str(src_in_host), str(dest_in_host))
                    future_list.append(fut)

                updated_file_uri = dest_in_container.as_uri()
                saved_file_uris[file_uri] = updated_file_uri
                saved_file_paths.append(dest_in_host)
                return updated_file_uri

            if len(future_list) > 0:
                for fut in future_list:
                    fut.result()

            return apply_to_jsonable(inputs, check_if_file_uri, convert_file_uri), saved_file_paths

    def convert_file_uris_in_outputs(
        self, outputs: t.List[t.Dict]
    ) -> t.Tuple[t.List[t.Dict], t.List[Path]]:
        saved_file_paths: t.List[Path] = []

        def convert_file_uri(file_uri: str):
            path_in_container = get_pure_posix_path_from_file_uri(file_uri)
            path_in_host = self.bind_dir_in_host / path_in_container.relative_to(
                self.bind_dir_in_container
            )
            saved_file_paths.append(path_in_host)

            return path_in_host.as_uri()

        return apply_to_jsonable(outputs, check_if_file_uri, convert_file_uri), saved_file_paths


@contextmanager
def start_model_container(model_data: ModelData, bind_dir_in_host: Path):
    bind_dir_in_container = f"/mnt/host-{uuid4().hex}"
    mount = Mount(
        target=str(bind_dir_in_container),
        source=str(bind_dir_in_host.resolve()),
        consistency="consistent",
        type="bind",
    )
    device_request = DeviceRequest(capabilities=[["gpu"]], count=-1) if model_data.gpu else None
    env_var = {"MOUNT_POINT": bind_dir_in_container}

    # Start the container
    with start_server_container(
        image_name_or_id=model_data.docker_image_id,
        internal_port=MODEL_CONTAINER_PORT,
        command=f"-m file_tunnel -p {MODEL_CONTAINER_PORT}",
        device_requests=[device_request] if device_request else None,
        mounts=[mount],
        environment=env_var,
    ) as server_container:
        service = ModelContainer(
            model_name=model_data.name,
            bind_dir_in_host=bind_dir_in_host,
            bind_dir_in_container=PurePosixPath(bind_dir_in_container),
            **attrs.asdict(server_container, recurse=False),
        )
        service.wait_for_setup()
        yield service
