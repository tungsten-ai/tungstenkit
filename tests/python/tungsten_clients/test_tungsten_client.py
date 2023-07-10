import re
import typing as t
from pathlib import Path, PurePosixPath
from unittest.mock import patch

import responses
from requests import PreparedRequest

from tungstenkit._internal import storables
from tungstenkit._internal.blob_store import BlobStore
from tungstenkit._internal.tungsten_clients import TungstenClient, schemas
from tungstenkit._internal.utils import markdown

from .fixtures import (
    ACCESS_TOKEN,
    BASE_URL,
    DOCKER_REGISTRY_URL,
    DOCKER_REPOSITORY,
    MODEL_GET_URL,
    MODEL_POST_URL,
    MODEL_README_URL,
    MODEL_SOURCE_TREE_URL,
    MODEL_VERSION,
    PROJECT_AVATAR_DATA_PNG,
    PROJECT_FULLNAME,
    PROJECT_GET_URL,
    SERVER_METADATA_URL,
    USER_GET_URL,
)
from .patches import (
    POSTED_FILE_ID_TO_PATH_MAPPING,
    patch_dummy_model_data_in_image,
    patch_file_post_resp,
    patch_model_avatar_file_get_resp,
    patch_model_readme_file_get_resp,
    patch_model_source_file_get_resp,
)


@responses.activate
def test_pull_model(
    dummy_model_data: storables.ModelData,
    dummy_model_in_server: schemas.Model,
    dummy_model_readme_in_server: str,
    dummy_model_source_tree_in_server: schemas.SourceTreeFolder,
):
    # TODO test auth
    responses.add_passthru(re.compile(r"http\+docker://.*"))
    responses.get(
        PROJECT_GET_URL,
        status=200,
        content_type="application/json",
        body=r"{}",
    )
    responses.get(
        SERVER_METADATA_URL,
        status=200,
        content_type="application/json",
        body=schemas.ServerMetadata(
            version="0.0.1",
            registry_url=DOCKER_REGISTRY_URL,  # type: ignore
        ).json(),
    )
    responses.get(
        MODEL_GET_URL,
        status=200,
        content_type="application/json",
        body=dummy_model_in_server.json(),
    )
    responses.get(
        MODEL_README_URL,
        status=200,
        content_type="text/plain",
        body=dummy_model_readme_in_server,
    )
    responses.get(
        MODEL_SOURCE_TREE_URL,
        status=200,
        content_type="application/json",
        body=dummy_model_source_tree_in_server.json(),
    )
    patch_model_avatar_file_get_resp()
    if dummy_model_data.readme:
        patch_model_readme_file_get_resp(dummy_model_data.readme.image_files)
    if dummy_model_data.source_files:
        patch_model_source_file_get_resp(dummy_model_data.source_files.files)

    with patch_dummy_model_data_in_image(dummy_model_data):
        with patch.object(TungstenClient, "_pull_from_docker_registry", return_value=None):
            client = TungstenClient(url=BASE_URL, access_token=ACCESS_TOKEN)
            loaded_model_data = client.pull_model(PROJECT_FULLNAME, MODEL_VERSION)

    assert loaded_model_data.name == f"{DOCKER_REPOSITORY}/{PROJECT_FULLNAME}:{MODEL_VERSION}"
    assert loaded_model_data.device == dummy_model_data.device
    assert loaded_model_data.gpu_mem_gb == dummy_model_data.gpu_mem_gb
    assert loaded_model_data.avatar.bytes_ == PROJECT_AVATAR_DATA_PNG
    assert loaded_model_data.source_files == dummy_model_data.source_files
    assert loaded_model_data.readme == dummy_model_data.readme


@responses.activate
def test_push_model(
    dummy_model_data: storables.ModelData,
    dummy_model_in_server: schemas.Model,
    dummy_model_readme_in_server: str,
    user_in_server: schemas.User,
    tmp_path: Path,
):
    # TODO test auth
    responses.add_passthru(re.compile(r"http\+docker://.*"))
    responses.get(
        USER_GET_URL,
        status=200,
        content_type="application/json",
        body=user_in_server.json(),
    )
    responses.get(
        PROJECT_GET_URL,
        status=200,
        content_type="application/json",
        body=r"{}",
    )
    responses.get(
        SERVER_METADATA_URL,
        status=200,
        content_type="application/json",
        body=schemas.ServerMetadata(
            version="0.0.1",
            registry_url=DOCKER_REGISTRY_URL,  # type: ignore
        ).json(),
    )

    patch_file_post_resp(tmp_path)

    def check_source_file(f: t.Union[schemas.SourceFileDecl, schemas.SkippedSourceFileDecl]):
        p = PurePosixPath(f.path)
        exists = False
        gt = None
        assert dummy_model_data.source_files
        for sf in dummy_model_data.source_files.files:
            if sf.rel_path_in_model_fs == p:
                exists = True
                gt = sf.abs_path_in_host_fs

        assert exists

        if isinstance(f, schemas.SourceFileDecl):
            assert gt is not None
            assert gt.read_bytes() == POSTED_FILE_ID_TO_PATH_MAPPING[f.upload_id].read_bytes()
        else:
            assert gt is None

    def model_post_callback(request: PreparedRequest):
        assert request.body is not None
        serialized = request.body
        model_create_req = schemas.ModelCreate.parse_raw(serialized)
        if dummy_model_data.gpu:
            model_create_req.gpu_memory == dummy_model_data.gpu_mem_gb
        else:
            model_create_req.gpu_memory == 0
        assert model_create_req.input_schema == dummy_model_data.io.input_schema
        assert model_create_req.output_schema == dummy_model_data.io.output_schema
        assert model_create_req.demo_output_schema == dummy_model_data.io.demo_output_schema
        assert model_create_req.input_filetypes == dummy_model_data.io.input_filetypes
        assert model_create_req.output_filetypes == dummy_model_data.io.output_filetypes
        assert model_create_req.demo_output_filetypes == dummy_model_data.io.demo_output_filetypes
        if dummy_model_data.source_files:
            assert len(model_create_req.source_files) + len(
                model_create_req.skipped_source_files
            ) == len(dummy_model_data.source_files.files)
            for f in model_create_req.source_files:
                check_source_file(f)

        return (200, dict(), dummy_model_in_server.json())

    responses.add_callback(
        responses.POST,
        MODEL_POST_URL,
        callback=model_post_callback,
        content_type="application/json",
    )

    def readme_put_callback(request: PreparedRequest):
        assert request.body is not None
        content = schemas.ModelReadmeUpdate.parse_raw(request.body).content
        assert isinstance(content, str)
        local_image_paths = markdown.get_local_image_paths(content)
        assert len(local_image_paths) == 0
        blob_store = BlobStore()
        stored_markdown_data = storables.MarkdownData(content=content).save_blobs(blob_store)
        markdown_data = storables.MarkdownData.load_blobs(stored_markdown_data)
        assert markdown_data == dummy_model_data.readme
        return (200, dict(), dummy_model_readme_in_server)

    responses.add_callback(
        responses.PUT,
        MODEL_README_URL,
        callback=readme_put_callback,
        content_type="text/plain",
    )

    with patch.object(TungstenClient, "_push_to_docker_registry", return_value=None):
        client = TungstenClient(url=BASE_URL, access_token=ACCESS_TOKEN)
        client.push_model(dummy_model_data.name, project_full_slug=PROJECT_FULLNAME)
