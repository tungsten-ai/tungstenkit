import re

from tungstenkit import exceptions

############################################
# Docker
############################################
_DOCKER_TAG_DESC_URL = r"https://docs.docker.com/engine/reference/commandline/tag/#description"
_DOCKER_VAL_ERR_SUFFIX = f"Details can be found on {_DOCKER_TAG_DESC_URL}."

RE_DOCKER_REPO_NAME = (
    r"^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])"  # noqa: E501
    r"(?:/(?![._-])[a-z0-9._-]*(?<![._-]))*)$"
)
RE_DOCKER_TAG = r"^(?![.-])[a-zA-Z0-9_.-]{1,128}$"
RE_DOCKER_IMAGE_NAME = (
    r"^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])"  # noqa: E501
    r"(?:/(?![._-])[a-z0-9._-]*(?<![._-]))*)"
    r"(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$"
)
RE_DOCKER_IMAGE_FULL_NAME = (
    r"^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])"  # noqa: E501
    r"(?:/(?![._-])[a-z0-9._-]*(?<![._-]))*)"
    r"(?::(?![.-])[a-zA-Z0-9_.-]{1,128})$"
)


def validate_docker_image_name(name: str) -> str:
    path_components = name.split("/")
    last_component_splitted = path_components[-1].split(":")
    if len(last_component_splitted) > 2:
        raise exceptions.InvalidName(f"'{name}' (format: '<repo_name>[:<tag>]')")

    if re.match(RE_DOCKER_IMAGE_NAME, name):
        return name
    raise exceptions.InvalidName(
        f"'{name}' cannot be a docker image name. {_DOCKER_VAL_ERR_SUFFIX}"
    )


def validate_docker_image_full_name(name: str) -> str:
    path_components = name.split("/")
    last_component_splitted = path_components[-1].split(":")
    if len(last_component_splitted) > 2:
        raise exceptions.InvalidName(f"'{name}' (format: '<repo_name>:<tag>')")

    if re.match(RE_DOCKER_IMAGE_FULL_NAME, name):
        return name
    raise exceptions.InvalidName(
        f"'{name}' cannot be a docker image full name. {_DOCKER_VAL_ERR_SUFFIX}"
    )


############################################
# Tungsten server
############################################
RE_TUNGSTEN_PROJECT_SLUG = r"^[a-z0-9_-]+$"
RE_TUNGSTEN_NAMESPACE_SLUG = r"^[a-z0-9_-]+$"
RE_TUNGSTEN_FULL_SLUG = r"^[a-z0-9_-]+\\/[a-z0-9_-]+$"
RE_MODEL_VERSION = r"[\\x00-\\x7F]+"
