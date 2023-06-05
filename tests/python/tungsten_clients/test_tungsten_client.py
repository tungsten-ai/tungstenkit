from pathlib import Path
from unittest.mock import MagicMock, patch

import responses
from requests import PreparedRequest
from responses import matchers

from tungstenkit._internal import storables
from tungstenkit._internal.tungsten_clients import TungstenClient, schemas
from tungstenkit._internal.utils import docker

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
    PROJECT_EXISTENCE_URL,
    PROJECT_FULLNAME,
    SERVER_METADATA_URL,
    USER_GET_URL,
)
from .patches import (
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
    responses.add_passthru("http+docker://localhost")
    responses.get(
        PROJECT_EXISTENCE_URL,
        status=200,
        content_type="application/json",
        body=schemas.Existence(exists=True).json(),
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


# TODO test push model
# @responses.activate
# def test_push_model(
#     dummy_model_data: storables.ModelData,
#     dummy_model_in_server: schemas.Model,
#     dummy_model_readme_in_server: str,
#     user_in_server: schemas.User,
#     tmp_path: Path,
# ):
#     # TODO test auth
#     responses.add_passthru("http+docker://localhost")
#     responses.get(
#         USER_GET_URL,
#         status=200,
#         content_type="application/json",
#         body=user_in_server.json(),
#     )
#     responses.get(
#         PROJECT_EXISTENCE_URL,
#         status=200,
#         content_type="application/json",
#         body=schemas.Existence(exists=True).json(),
#     )
#     responses.get(
#         SERVER_METADATA_URL,
#         status=200,
#         content_type="application/json",
#         body=schemas.ServerMetadata(
#             version="0.0.1",
#             registry_url=DOCKER_REGISTRY_URL,  # type: ignore
#         ).json(),
#     )
#     responses.post(
#         MODEL_POST_URL,
#         status=200,
#         content_type="application/json",
#         body=dummy_model_in_server.json(),
#     )
#     def readme_put_callback(request: PreparedRequest):
#         assert request.body == dummy_model_readme_in_server
#         payload = json.loads(request.body)
#         resp_body = {"value": sum(payload["numbers"])}
#         headers = {"request-id": "728d329e-0e86-11e4-a748-0c84dc037c13"}
#         return (200, headers, json.dumps(resp_body))

#     responses.put(
#         MODEL_README_URL,
#         status=200,
#         content_type="text/plain",
#         body=dummy_model_readme_in_server,
#         match=[matchers.],
#     )
#     patch_file_post_resp(tmp_path)

#     with patch.object(TungstenClient, "_push_to_docker_registry", return_value=None):
#         client = TungstenClient(url=BASE_URL, access_token=ACCESS_TOKEN)
#         model_data_in_server = client.push_model(dummy_model_data.name, project=PROJECT_FULLNAME)
