import random
import typing as t
from datetime import datetime
from pathlib import PurePosixPath
from uuid import uuid4

import pytest

from tungstenkit._internal import constants, storables
from tungstenkit._internal.tungsten_clients import schemas
from tungstenkit._internal.tungsten_clients.api_client import API_BASE_STR
from tungstenkit._internal.utils import avatar, markdown

from ..dummy_model import DUMMY_MODEL_DATA_DIR

BASE_URL = "https://example.tungsten-ai.com"
ACCESS_TOKEN = "exampletoken"
DOCKER_REPOSITORY = "tstn.io"
DOCKER_REGISTRY_URL = f"https://{DOCKER_REPOSITORY}"

SERVER_METADATA_URL = f"{BASE_URL}{API_BASE_STR}/application"

USER_ID = random.randint(0, 10000)
USER_NAME = "exampleuser"
USER_FULLNAME = "Example User"
USER_EMAIL = "exampleuser@example.tungsten-ai.com"
USER_PASSWORD = "user"
USER_GET_URL = f"{BASE_URL}{API_BASE_STR}/user"

PROJECT_ID = random.randint(0, 10000)
PROJECT_NAME = "exampleproject"
PROJECT_FULLNAME = f"{USER_NAME}/exampleproject"
PROJECT_GET_URL = f"{BASE_URL}{API_BASE_STR}/projects/{PROJECT_FULLNAME}"
PROJECT_FILES_BASE_URL = f"{BASE_URL}{API_BASE_STR}/files/{PROJECT_ID}"
PROJECT_FILE_UPLOAD_URL = f"{PROJECT_GET_URL}/uploads"
PROJECT_AVATAR_URL = f"{PROJECT_GET_URL}/avatar"
PROJECT_AVATAR_DATA_PNG = avatar.fetch_default_avatar_png("exampleproject@example.tungsten-ai.com")

MODEL_ID = random.randint(0, 10000)
MODEL_VERSION = "exampleversion"
MODEL_CREATED_AT = datetime.utcnow()
MODEL_POST_URL = f"{PROJECT_GET_URL}/models"
MODEL_GET_URL = f"{MODEL_POST_URL}/{MODEL_VERSION}"
MODEL_README_URL = f"{MODEL_GET_URL}/readme"
MODEL_README_IMAGES_FOLDER = uuid4().hex
MODEL_README_IMAGES_FOLDER_URL = f"{PROJECT_FILES_BASE_URL}/{MODEL_README_IMAGES_FOLDER}"
MODEL_SOURCE_TREE_URL = f"{MODEL_GET_URL}/tree"
MODEL_SOURCE_FILES_BASE_URL = f"{MODEL_GET_URL}/files"


@pytest.fixture(scope="session")
def user_in_server() -> schemas.User:
    return schemas.User(id=USER_ID, username=USER_NAME, email=USER_EMAIL, name=USER_FULLNAME)


@pytest.fixture(scope="session")
def dummy_model_in_server(
    dummy_model_data: storables.ModelData, user_in_server: schemas.User
) -> schemas.Model:
    # TODO test auth
    image_size = int(10 * 1e9)
    examples_count = 10
    body = schemas.Model(
        id=MODEL_ID,
        project_id=PROJECT_ID,
        project_full_slug=PROJECT_FULLNAME,
        version=MODEL_VERSION,
        docker_image=PROJECT_FULLNAME + ":" + MODEL_VERSION,
        docker_image_size=image_size,
        input_filetypes=dummy_model_data.io.input_schema,
        output_schema=dummy_model_data.io.output_schema,
        demo_output_schema=dummy_model_data.io.demo_output_schema,
        input_filetypes=dummy_model_data.io.input_filetypes,
        output_filetypes=dummy_model_data.io.output_filetypes,
        demo_output_filetypes=dummy_model_data.io.demo_output_filetypes,
        os="linux",
        architecture="amd64",
        gpu_memory=dummy_model_data.gpu_mem_gb
        if dummy_model_data.gpu and dummy_model_data.gpu_mem_gb
        else 0,
        readme_url=MODEL_README_URL,
        source_files_count=len(dummy_model_data.source_files.files)
        if dummy_model_data.source_files
        else 0,
        created_at=dummy_model_data.created_at,
        creator=user_in_server,
        examples_count=examples_count,
    )
    return body


@pytest.fixture(scope="session")
def dummy_model_readme_in_server() -> str:
    orig_readme_path = DUMMY_MODEL_DATA_DIR / "markdown.md"
    orig_readme = orig_readme_path.read_text()
    orig_readme_images = markdown.get_local_image_paths(orig_readme)
    images_in_server = [f"{MODEL_README_IMAGES_FOLDER_URL}/{im.name}" for im in orig_readme_images]
    readme_in_server = markdown.change_local_image_links_in_markdown(
        orig_readme, orig_readme_images, images_in_server
    )
    return readme_in_server


@pytest.fixture(scope="session")
def dummy_model_source_tree_in_server(
    dummy_model_all_source_files_dict: t.Dict[PurePosixPath, storables.SourceFile]
) -> schemas.SourceTreeFolder:
    root = schemas.SourceTreeFolder(name="root")

    for file in dummy_model_all_source_files_dict.values():
        folder = root
        for part in file.rel_path_in_model_fs.parts[:-1]:
            folder_exists = False
            for c in folder.contents:
                if c.name == part and c.type == "folder":
                    folder = c
                    folder_exists = True
            if not folder_exists:
                new_folder = schemas.SourceTreeFolder(name=part)
                folder.contents.append(new_folder)
                folder = new_folder

        skipped = file.size > constants.MAX_SOURCE_FILE_SIZE
        folder.contents.append(
            schemas.SourceTreeFile(
                name=file.rel_path_in_model_fs.name, size=file.size, skipped=skipped
            )
        )

    return root


__all__ = [
    "user_in_server",
    "dummy_model_in_server",
    "dummy_model_readme_in_server",
    "dummy_model_source_tree_in_server",
]
