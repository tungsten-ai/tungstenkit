import io
import typing as t
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import requests
from furl import furl

from tungstenkit import exceptions
from tungstenkit._internal import storables
from tungstenkit._internal.logging import log_debug
from tungstenkit._internal.utils.json import change_strings_in_jsonable, get_uris_in_jsonable
from tungstenkit._internal.utils.markdown import (
    change_img_links_in_markdown,
    change_local_image_links_in_markdown,
    get_image_links,
)
from tungstenkit._internal.utils.requests import (
    check_resp,
    download_file,
    download_files_in_threadpool,
    log_request,
    upload_form_data_by_buffer,
    upload_form_data_by_path,
    upload_multiple_form_data_by_paths,
)

from . import schemas

if t.TYPE_CHECKING:
    from _typeshed import StrPath

API_BASE_STR = "/api/v1"
CONNECTION_TINEOUT = 10


class TungstenAPIClient:
    def __init__(self, base_url: str, access_token: t.Optional[str] = None) -> None:
        self.base_url = base_url
        self.sess = requests.Session()
        # FIXME cert
        self.sess.verify = False

        if access_token:
            self._set_auth_header(access_token)

    def get_access_token(self, username: str, password: str) -> schemas.AccessToken:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "user" / "access_token"
        data = {"username": username, "password": password}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        log_request(url=f.url, method="POST", data=data)
        raw_resp = self.sess.post(
            f.url,
            data=data,
            headers=headers,
            timeout=CONNECTION_TINEOUT,
        )
        _check_resp(raw_resp, f.url, "Failed to log in")
        resp = schemas.AccessToken.parse_raw(raw_resp.text)
        self._set_auth_header(resp.access_token)
        return resp

    def get_current_user(self) -> schemas.User:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "user"
        log_request(url=f.url, method="GET")
        resp = self.sess.get(f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(resp, f.url, "Failed to fetch user info")
        return schemas.User.parse_raw(resp.text)

    def check_if_project_exists(self, project: str):
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "exists"
        log_request(url=f.url, method="GET")
        resp = self.sess.get(f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(resp, f.url, f"Failed to check existence of project '{project}'")
        parsed = schemas.Existence.parse_raw(resp.text)
        if not parsed.exists:
            raise exceptions.NotFound(f"No project '{project}' in {self.base_url}")

    def get_project_avatar(self, project: str) -> t.Optional[storables.AvatarData]:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "avatar"
        log_request(url=f.url, method="GET")
        resp = self.sess.get(f.url, timeout=CONNECTION_TINEOUT)
        if resp.status_code == 404:
            return None

        _check_resp(resp, f.url, f"Failed to fetch the avatar of project '{project}'")
        return storables.AvatarData(bytes_=resp.content, extension=".png")

    def get_model(self, project: str, version: str) -> schemas.Model:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "models" / version
        log_request(url=f.url, method="GET")
        resp = self.sess.get(f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(resp, f.url, f"Failed to fetch info of model '{project}:{version}'")
        return schemas.Model.parse_raw(resp.text)

    def create_model(self, project: str, req: schemas.ModelCreate) -> schemas.Model:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "models"
        data = req.json()
        log_request(url=f.url, method="POST", data=data)
        resp = self.sess.post(f.url, data=data, timeout=CONNECTION_TINEOUT)
        _check_resp(resp, f.url, f"Failed to create a model in project '{project}'")
        return schemas.Model.parse_raw(resp.text)

    def create_model_prediction_examples(
        self, project: str, version: str, examples: t.List[storables.PredExampleData]
    ) -> t.List[schemas.ModelPredictionExample]:
        examples_count = len(examples)
        if examples_count == 0:
            return []

        # file_paths_per_example[i]: (input_file_paths, output_file_paths)
        file_paths_per_example: t.List[t.Tuple[t.List[Path], t.List[Path]]] = []
        for e in examples:
            file_paths_per_example.append(
                ([f for f in e.input_files], [f for f in e.output_files])
            )
        # file_counts_per_example[i]: (input_files_count, output_files_count)
        file_counts_per_example: t.List[t.Tuple[int, int]] = []
        file_paths: t.List[Path] = []
        for input_files, output_files in file_paths_per_example:
            file_counts_per_example.append((len(input_files), len(output_files)))
            file_paths.extend(input_files)
            file_paths.extend(output_files)
        file_uris = [p.as_uri() for p in file_paths]
        file_serving_urls = self.upload_multiple_files_by_paths(
            project=project,
            paths=file_paths,
            desc="Uploading files in example predictions",
        )
        # file_serving_urls_per_example[i]: (input_file_serving_urls, output_file_serving_urls)
        file_serving_urls_per_example: t.List[t.Tuple[t.List[str], t.List[str]]] = []
        start_idx = 0
        for input_files_count, output_files_count in file_counts_per_example:
            input_file_serving_urls = file_serving_urls[start_idx : start_idx + input_files_count]
            start_idx += input_files_count
            output_file_serving_urls = file_serving_urls[
                start_idx : start_idx + output_files_count
            ]
            start_idx += output_files_count
            file_serving_urls_per_example.append(
                (input_file_serving_urls, output_file_serving_urls)
            )

        jsonables_per_example = []
        for e in examples:
            input = e.input
            output = e.output
            demo_output = e.demo_output
            jsonables_per_example.append([input, output, demo_output])

        jsonables_per_example = change_strings_in_jsonable(
            jsonable=jsonables_per_example,
            values=file_uris,
            updates=file_serving_urls,
        )

        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "models" / version / "examples"
        url = f.url

        def create(example_idx: int):
            _input, _output, _demo_output = jsonables_per_example[example_idx]
            _input_file_serving_urls, _output_file_serving_urls = file_serving_urls_per_example[
                example_idx
            ]

            req = schemas.ModelPredictionExampleCreate(
                input=_input,
                output=_output,
                demo_output=_demo_output,
                input_files=_input_file_serving_urls,
                output_files=_output_file_serving_urls,
            )
            data = req.json()
            log_request(url=url, method="POST", data=data)
            resp = self.sess.post(url, data=data, timeout=CONNECTION_TINEOUT)
            _check_resp(
                resp, url, f"Failed to create a prediction example for model '{project}:{version}'"
            )
            parsed = schemas.ModelPredictionExample.parse_raw(resp.text)
            log_debug("Response: " + str(parsed), pretty=False)

        fut_list: t.List[Future] = []
        responses: t.List[schemas.ModelPredictionExample] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            for i in range(examples_count):
                fut_list.append(executor.submit(create, i))

            for fut in fut_list:
                responses.append(fut.result())

        return responses

    def get_model_file_tree(
        self, project: str, version: str, path: t.Optional[str] = None
    ) -> schemas.FileTree:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "models" / version / "tree"
        if path:
            f.args["path"] = path
        log_request(url=f.url, method="GET")
        resp = self.sess.get(f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(resp, f.url, f"Failed to list files of model {project}:{version}")
        return schemas.FileTree.parse_raw(resp.text)

    def update_model_readme(
        self, project: str, version: str, readme: storables.MarkdownData
    ) -> None:
        if len(readme.image_files) > 0:
            image_file_serving_urls = self.upload_multiple_files_by_paths(
                project=project, paths=readme.image_files, desc="Uploading image files in README"
            )
            readme_content = change_local_image_links_in_markdown(
                md=readme.content,
                local_img_paths=readme.image_files,
                updates=image_file_serving_urls,
            )

        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "models" / version / "readme"
        log_request(url=f.url, method="PUT")
        data = schemas.ModelReadmeUpdate(content=readme_content).json()
        resp = self.sess.put(f.url, data=data, timeout=CONNECTION_TINEOUT)
        _check_resp(
            resp, url=f.url, err_msg_prefix=f"Failed to upload README of model {project}:{version}"
        )

    def get_model_source_tree(self, project: str, version: str) -> schemas.SourceTreeFolder:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "models" / version / "tree"
        log_request(url=f.url, method="GET")
        resp = self.sess.get(f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(
            resp,
            url=f.url,
            err_msg_prefix=f"Failed to get the source tree of model {project}:{version}",
        )
        parsed = schemas.SourceTreeFolder.parse_raw(resp.text)
        return parsed

    def download_model_source_file(
        self, project: str, version: str, path: str, download_dir: Path
    ) -> Path:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "models" / version / "files"
        f.path.segments += [path]  # For url encoding
        log_request(url=f.url, method="GET")
        return download_file(url=f.url, out_path=download_dir, sess=self.sess)

    def get_model_readme(
        self, project: str, version: str, image_download_dir: Path
    ) -> storables.MarkdownData:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "models" / version / "readme"
        log_request(url=f.url, method="GET")
        resp = self.sess.get(url=f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(resp, f.url, f"Failed to get the README of model {project}:{version}")

        md = resp.text
        image_http_links = get_image_links(md, schemes=["http", "https"])
        if len(image_http_links) > 0:
            downloaded = self.download_multiple_files(
                image_http_links,
                download_dir=image_download_dir,
                desc="Downloading images in README",
            )
            md = change_img_links_in_markdown(
                md, images=image_http_links, updates=[str(p) for p in downloaded]
            )
            return storables.MarkdownData(content=md, image_files=downloaded)
        return storables.MarkdownData(content=md)

    def list_examples(
        self, project: str, version: str, file_download_dir: Path
    ) -> t.List[storables.PredExampleData]:
        # Get examples in db
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "models" / version / "examples"
        log_request(url=f.url, method="GET")
        resp = self.sess.get(url=f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(resp, f.url, f"Failed to get the README of model {project}:{version}")
        examples_in_server = schemas.ListModelPredictionExamples.parse_raw(resp.text).__root__

        # Download files in examples
        input_file_serving_urls_per_example = [
            get_uris_in_jsonable(e.input, schemes=["http", "https"]) for e in examples_in_server
        ]
        output_file_serving_urls_per_example = [
            get_uris_in_jsonable([e.output, e.demo_output], schemes=["http", "https"])
            for e in examples_in_server
        ]
        file_serving_urls: t.List[str] = []
        for urls in input_file_serving_urls_per_example:
            file_serving_urls.extend(urls)
        for urls in output_file_serving_urls_per_example:
            file_serving_urls.extend(urls)

        downloaded_paths = (
            self.download_multiple_files(
                file_serving_urls,
                file_download_dir,
                desc="Downloading files in prediction examples",
            )
            if len(file_serving_urls) > 0
            else []
        )

        start_idx = 0
        input_file_paths_per_example: t.List[t.List[Path]] = list()
        output_file_paths_per_example: t.List[t.List[Path]] = list()
        for urls in input_file_serving_urls_per_example:
            count = len(urls)
            input_file_paths_per_example.append(downloaded_paths[start_idx : start_idx + count])
            start_idx += count
        for urls in output_file_serving_urls_per_example:
            count = len(urls)
            output_file_paths_per_example.append(downloaded_paths[start_idx : start_idx + count])
            start_idx += count

        # Update inputs, outputs, and demo outputs
        downloaded_examples = [
            storables.PredExampleData(
                input=e.input,
                output=e.output,
                demo_output=e.demo_output,
                input_files=input_file_paths_per_example[i],
                output_files=output_file_paths_per_example[i],
            )
            for i, e in enumerate(examples_in_server)
        ]
        for i, e in enumerate(downloaded_examples):
            e.input = change_strings_in_jsonable(
                e.input,
                values=input_file_serving_urls_per_example[i],
                updates=[p.as_uri() for p in e.input_files],
            )
            e.output = change_strings_in_jsonable(
                e.output,
                values=output_file_serving_urls_per_example[i],
                updates=[p.as_uri() for p in e.output_files],
            )
            e.demo_output = change_strings_in_jsonable(
                e.demo_output,
                values=output_file_serving_urls_per_example[i],
                updates=[p.as_uri() for p in e.output_files],
            )
        return downloaded_examples

    def get_server_metadata(self) -> schemas.ServerMetadata:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "application"
        log_request(url=f.url, method="GET")
        resp = self.sess.get(url=f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(
            resp,
            f.url,
            err_msg_prefix="Failed to get metadata of the tungsten instance",
        )
        return schemas.ServerMetadata.parse_raw(resp.text)

    def upload_file_by_path(self, project: str, path: Path, desc: t.Optional[str] = None) -> str:
        url = self.build_upload_url(project=project)
        log_request(url=url, method="POST")
        resp = upload_form_data_by_path(
            method="post",
            url=url,
            file_path=path,
            field="file",
            sess=self.sess,
            progress_bar=True,
            desc=desc,
        )
        _check_resp(resp, url, f"Failed to upload file '{path}'")
        parsed = schemas.FileUploadResponse.parse_raw(resp.text)
        return parsed.serving_url

    def upload_file_by_buffer(
        self,
        project: str,
        buffer: io.BufferedIOBase,
        file_name: str,
        content_type: str,
        desc: t.Optional[str] = None,
    ) -> str:
        url = self.build_upload_url(project=project)
        log_request(url=url, method="POST")
        resp = upload_form_data_by_buffer(
            method="post",
            url=url,
            buffer=buffer,
            file_name=file_name,
            content_type=content_type,
            field="file",
            sess=self.sess,
            progress_bar=True,
            desc=desc,
        )
        _check_resp(resp, url, f"Failed to upload file '{file_name}'")
        parsed = schemas.FileUploadResponse.parse_raw(resp.text)
        return parsed.serving_url

    def upload_multiple_files_by_paths(
        self, project: str, paths: t.List[Path], desc: t.Optional[str] = None
    ) -> t.List[str]:
        if len(paths) == 0:
            return []

        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "uploads"
        log_request(url=f.url, method="POST")
        responses = upload_multiple_form_data_by_paths(
            method="post",
            url=f.url,
            file_paths=paths,
            field="file",
            sess=self.sess,
            progress_bar=True,
            desc=desc,
        )
        serving_urls: t.List[str] = []
        for p, resp in zip(paths, responses):
            _check_resp(resp, f.url, f"Failed to upload file '{p}'")
            parsed = schemas.FileUploadResponse.parse_raw(resp.text)
            log_debug(f"Response of uploading {p}: {parsed}", pretty=False)
            serving_urls.append(parsed.serving_url)

        return serving_urls

    def download_file(
        self,
        url: str,
        out_path: "t.Optional[StrPath]" = None,
        progress_bar: bool = True,
        desc: t.Optional[str] = None,
    ) -> Path:
        return download_file(
            url=url, out_path=out_path, sess=self.sess, progress_bar=progress_bar, desc=desc
        )

    def download_multiple_files(
        self,
        urls: t.List[str],
        download_dir: Path,
        progress_bar: bool = True,
        desc: t.Optional[str] = None,
    ) -> t.List[Path]:
        return download_files_in_threadpool(
            *urls, download_dir=download_dir, sess=self.sess, progress_bar=progress_bar, desc=desc
        )

    def build_upload_url(self, project: str) -> str:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "uploads"
        return f.url

    def _set_auth_header(self, access_token: str):
        self.sess.headers.update(Authorization="Bearer " + access_token)


def _check_resp(resp: requests.Response, url: str, err_msg_prefix: t.Optional[str] = None):
    check_resp(
        resp=resp, url=url, exc_type=exceptions.TungstenClientError, err_msg_prefix=err_msg_prefix
    )
