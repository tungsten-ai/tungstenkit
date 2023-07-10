import tempfile
import typing as t
from pathlib import Path

from docker.client import DockerClient
from docker.models.images import Image as DockerImage
from rich.prompt import Prompt

from tungstenkit import exceptions
from tungstenkit._internal import storables
from tungstenkit._internal.configs import TungstenClientConfig
from tungstenkit._internal.logging import log_debug, log_info
from tungstenkit._internal.utils.console import print_success
from tungstenkit._internal.utils.docker import (
    PullPushFailureReason,
    get_docker_client,
    login_to_docker_registry,
    pull_from_docker_registry,
    push_to_docker_registry,
)
from tungstenkit._internal.utils.uri import strip_scheme_in_http_url

from . import schemas
from .api_client import TungstenAPIClient

DOCKER_CLIENT_TIMEOUT = 10


class TungstenClient:
    def __init__(self, url: str, access_token: str) -> None:
        self.api = TungstenAPIClient(base_url=url, access_token=access_token)

        self._url = url
        self._access_token = access_token
        self._server_metadata: t.Optional[schemas.ServerMetadata] = None
        self._user_info: t.Optional[schemas.User] = None

    @staticmethod
    def from_env() -> "TungstenClient":
        client_config = TungstenClientConfig.from_env()
        access_token = client_config.access_token
        url = str(client_config.url)
        return TungstenClient(url=url, access_token=access_token)

    @property
    def url(self) -> str:
        return self._url

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def username(self) -> str:
        if self._user_info is None:
            self._user_info = self.api.get_current_user()
        return self._user_info.username

    @property
    def server_metadata(self) -> schemas.ServerMetadata:
        if self._server_metadata is None:
            self._server_metadata = self.api.get_server_metadata()
        return self._server_metadata

    @property
    def docker_registry(self) -> str:
        if self._server_metadata is None:
            self._server_metadata = self.api.get_server_metadata()
        return strip_scheme_in_http_url(self._server_metadata.registry_url)

    def push_model(
        self,
        model_name: str,
        project_full_slug: str,
        version: t.Optional[str] = None,
    ) -> schemas.Model:
        project_in_server = self.api.get_project(project_full_slug)
        if project_in_server is None:
            raise exceptions.NotFound(f"No project '{project_full_slug}' in {self.api.base_url}")

        if version:
            try:
                self.api.get_model(project_full_slug, version)
                raise exceptions.Conflict(
                    f"Version '{version}' already exists in project '{project_full_slug}'. "
                    "Please retry after removing the model."
                )
            except exceptions.TungstenClientError as e:
                if e.status_code != 404:
                    raise e

        model = storables.ModelData.load(model_name)
        docker_image_id = model.docker_image_id

        docker_client = get_docker_client(timeout=DOCKER_CLIENT_TIMEOUT)
        docker_image: DockerImage = docker_client.images.get(docker_image_id)

        remote_docker_repo = f"{self.docker_registry}/{self.username}"
        remote_docker_tag = model.id
        docker_image.tag(repository=remote_docker_repo, tag=remote_docker_tag)
        try:
            log_info("Pushing the model image")
            self._push_to_docker_registry(
                repo=remote_docker_repo, tag=remote_docker_tag, docker_client=docker_client
            )
            log_info("")

            # if model.source_files and model.source_files.files:
            #     source_files, skipped_source_files = self.api.upload_model_source_files(
            #         project=project, files=model.source_files.files
            #     )
            # else:
            #     source_files, skipped_source_files = [], []

            log_info(f"Creating a model in {self.api.base_url}")
            req = schemas.ModelCreate(
                docker_image=f'{remote_docker_repo.split("/")[-1]}:{remote_docker_tag}',
                input_schema=model.io.input_schema,
                output_schema=model.io.output_schema,
                demo_output_schema=model.io.demo_output_schema,
                input_filetypes=model.io.input_filetypes,
                output_filetypes=model.io.output_filetypes,
                demo_output_filetypes=model.io.demo_output_filetypes,
                gpu_memory=model.gpu_mem_gb * 1024 * 1024 if model.gpu and model.gpu_mem_gb else 0,
                version=version,
                # source_files=source_files,
                # skipped_source_files=skipped_source_files,
            )

            model_in_server = self.api.create_model(project_full_slug=project_full_slug, req=req)
            log_debug("Response: " + str(model_in_server), pretty=False)

            # if model.readme:
            #     log_info("Updating the README")
            #     self.api.update_model_readme(
            #         project=project, version=model_in_server.version, readme=model.readme
            #     )
            #     log_info("")

        finally:
            docker_client.images.remove(image=f"{remote_docker_repo}:{remote_docker_tag}")

        log_info("")
        print_success(
            f"Successfully pushed '{model.name}' to '{self.api.base_url}'\n"
            f" - project: [green]{project_full_slug}[/green]\n"
            f" - version: [green]{model_in_server.version}[/green]"
        )
        return model_in_server

    def pull_model(
        self, project_full_slug: str, model_version: t.Optional[str] = None
    ) -> storables.ModelData:
        project_in_server = self.api.get_project(project_full_slug)
        if project_in_server is None:
            raise exceptions.NotFound(f"No project '{project_full_slug}' in {self.api.base_url}")

        if model_version:
            model_in_server = self.api.get_model(
                project_full_slug=project_full_slug, version=model_version
            )
        else:
            latest_model = self.api.get_latest_model(project_full_slug=project_full_slug)
            if latest_model is None:
                raise exceptions.NotFound(f"No model in project '{project_full_slug}'")
            model_in_server = latest_model
            model_version = model_in_server.version

        repo_name, tag = model_in_server.docker_image.split(":", maxsplit=1)
        remote_docker_repo = f"{self.docker_registry}/{repo_name}"
        local_model_name = f"{project_full_slug}:{model_version}"

        docker_client = get_docker_client(timeout=DOCKER_CLIENT_TIMEOUT)
        log_info("Pulling the model image")
        self._pull_from_docker_registry(remote_docker_repo, tag, docker_client=docker_client)

        image = docker_client.images.get(remote_docker_repo + ":" + tag)
        image.tag(project_full_slug, model_version)
        docker_client.images.remove(remote_docker_repo + ":" + tag)

        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)

            # if model_in_server.readme_url:
            #     readme_image_dir = tmp_dir / "readme_images"
            #     readme_image_dir.mkdir()
            #     log_info("Fetching the README")
            #     readme = self.api.get_model_readme(
            #         project=project, version=model_version, image_download_dir=tmp_dir
            #     )
            #     log_info("")
            # else:
            #     readme = None

            # if model_in_server.source_files_count > 0:
            #     source_files_dir = tmp_dir / "source_files"
            #     source_files_dir.mkdir()
            #     log_info("Fetching source files")
            #     source_files = self.api.download_model_source_tree(
            #         project=project, version=model_version, root_dir=source_files_dir
            #     )
            # else:
            #     source_files = []

            readme, source_files = None, []

            avatar = self.api.fetch_project_avatar(project_full_slug, project_in_server.avatar_url)
            io_data = storables.ModelIOData(
                input_schema=model_in_server.input_schema,
                output_schema=model_in_server.output_schema,
                demo_output_schema=model_in_server.demo_output_schema,
                input_filetypes=model_in_server.input_filetypes,
                output_filetypes=model_in_server.output_filetypes,
                demo_output_filetypes=model_in_server.demo_output_filetypes,
            )
            m = storables.ModelData(
                name=local_model_name,
                io_data=io_data,
                avatar=avatar,
                readme=readme,
                source_files=source_files,
            )
            m.save(file_blob_create_policy="rename")

            log_info("")
            print_success(f"Successfully pulled '{project_full_slug}:{model_version}'")
            return storables.ModelData.load(local_model_name)

    def _push_to_docker_registry(self, repo: str, tag: str, docker_client: DockerClient):
        result = push_to_docker_registry(repo=repo, tag=tag, docker_client=docker_client)

        if not result.is_success and result.failure_reason == PullPushFailureReason.UNAUTHORIZED:
            auth_config = _input_auth(
                server=self.api.base_url,
                default_name=self.username,
            )
            result = push_to_docker_registry(
                repo=repo,
                tag=tag,
                auth_config=auth_config,
                docker_client=docker_client,
            )
            self._login_to_docker_registry(auth_config)

        result.raise_on_error()

    def _pull_from_docker_registry(self, repo: str, tag: str, docker_client: DockerClient):
        result = pull_from_docker_registry(repo=repo, tag=tag, docker_client=docker_client)

        if not result.is_success and result.failure_reason == PullPushFailureReason.UNAUTHORIZED:
            auth_config = _input_auth(
                server=self.api.base_url,
                default_name=self.username,
            )
            result = pull_from_docker_registry(
                repo=repo,
                tag=tag,
                auth_config=auth_config,
                docker_client=docker_client,
            )
            self._login_to_docker_registry(auth_config)

        result.raise_on_error()

    def _login_to_docker_registry(self, auth_config: t.Optional[t.Dict[str, str]] = None):
        if auth_config is None:
            auth_config = _input_auth(self._url, self.username)

        login_to_docker_registry(self.docker_registry, auth_config)


def _input_auth(server: str, default_name: t.Optional[str] = None) -> t.Dict[str, str]:
    username = Prompt.ask(f"Username for '{server}'", default=default_name, show_default=True)
    password = Prompt.ask(f"Password for '{server}'", password=True)
    if not username:
        raise RuntimeError("Username is not entered")
    if not password:
        raise RuntimeError("Password is not entered")
    return {"username": username, "password": password}
