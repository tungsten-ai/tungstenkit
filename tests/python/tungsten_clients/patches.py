import mimetypes
import typing as t
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from unittest.mock import patch
from urllib.parse import quote_plus
from uuid import uuid4

import responses
from requests_toolbelt.multipart import decoder

from tungstenkit._internal import storables
from tungstenkit._internal.tungsten_clients import schemas
from tungstenkit._internal.utils.string import removeprefix, removesuffix

from .fixtures import (
    MODEL_README_IMAGES_FOLDER_URL,
    MODEL_SOURCE_FILES_BASE_URL,
    PROJECT_AVATAR_DATA_PNG,
    PROJECT_AVATAR_URL,
    PROJECT_FILE_UPLOAD_URL,
    PROJECT_FILES_BASE_URL,
)

POSTED_FILE_ID_TO_PATH_MAPPING: t.Dict[int, Path] = dict()

_file_upload_lock = Lock()


def patch_file_get_resp_by_path(url: str, orig_path: Path):
    content_type, _ = mimetypes.guess_type(orig_path.name, strict=False)
    if content_type is None:
        content_type = "application/octet-stream"
    responses.get(
        url,
        status=200,
        content_type=content_type,
        body=orig_path.read_bytes(),
        stream=True,
    )


def patch_file_post_resp(tmp_dir: Path):
    id = 1

    def file_post_callback(request):
        nonlocal id

        with _file_upload_lock:
            # Parse multipart form data
            content = request.body.read()
            content_type = request.body.content_type
            multipart = decoder.MultipartDecoder(content, content_type)

            part = multipart.parts[0]
            data = part.content

            # 'form-data; name="file"; filename="somefile"'
            content_decomposition = part.headers[b"Content-Disposition"].decode()
            content_type = part.headers[b"Content-Type"].decode()
            filename = removesuffix(
                removeprefix(content_decomposition, 'form-data; name="file"; filename="'), '"'
            )

            # Write file
            folder = uuid4().hex
            data_dir = tmp_dir / folder
            data_dir.mkdir()
            data_path = data_dir / filename
            data_path.write_bytes(data)

            # Prepare response
            serving_url = f"{PROJECT_FILES_BASE_URL}/{folder}/{filename}"
            resp_body = schemas.FileUploadResponse(
                id=id,
                size=len(data),
                content_type=content_type,
                serving_url=serving_url,
            )
            headers = {"content-type": "application/json"}

            patch_file_get_resp_by_bytes(serving_url, data, content_type)

            POSTED_FILE_ID_TO_PATH_MAPPING[id] = data_path
            id += 1

        return (200, headers, resp_body.json())

    responses.add_callback(
        responses.POST,
        PROJECT_FILE_UPLOAD_URL,
        callback=file_post_callback,
        content_type="application/json",
    )


def patch_file_get_resp_by_bytes(url: str, bytes_: bytes, content_type: str):
    responses.get(
        url,
        status=200,
        content_type=content_type,
        body=bytes_,
        stream=True,
    )


def patch_model_readme_file_get_resp(images: t.List[Path]):
    for im in images:
        patch_file_get_resp_by_path(MODEL_README_IMAGES_FOLDER_URL + "/" + im.name, im)


def patch_model_source_file_get_resp(source_files: t.Iterable[storables.SourceFile]):
    for f in source_files:
        if f.abs_path_in_host_fs:
            url = MODEL_SOURCE_FILES_BASE_URL + "/" + quote_plus(str(f.rel_path_in_model_fs))
            patch_file_get_resp_by_path(
                url,
                f.abs_path_in_host_fs,
            )


def patch_model_avatar_file_get_resp():
    patch_file_get_resp_by_bytes(PROJECT_AVATAR_URL, PROJECT_AVATAR_DATA_PNG, "image/png")


@contextmanager
def patch_dummy_model_data_in_image(dummy_model_data: storables.ModelData):
    model_data_in_image = storables.model._ModelDataInImage(
        module_name=dummy_model_data.module_name,
        class_name=dummy_model_data.class_name,
        docker_image_id=dummy_model_data.docker_image_id,
        batch_size=dummy_model_data.batch_size,
        device=dummy_model_data.device,
        gpu_mem_gb=dummy_model_data.gpu_mem_gb,
    )
    with patch.object(
        storables.model._ModelDataInImage, "from_image", return_value=model_data_in_image
    ):
        yield
