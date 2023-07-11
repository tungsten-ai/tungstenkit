import io
import typing as t
from pathlib import Path, PurePosixPath

import requests
from furl import furl

from tungstenkit import exceptions
from tungstenkit._internal import storables
from tungstenkit._internal.logging import log_debug
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

API_BASE_STR = "/v1"
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

    def get_project(self, project_full_slug: str) -> t.Optional[schemas.Project]:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project_full_slug
        log_request(url=f.url, method="GET")
        resp = self.sess.get(f.url, timeout=CONNECTION_TINEOUT)
        if resp.status_code == 404:
            return None

        _check_resp(resp, f.url, f"Project not found: '{project_full_slug}'")
        return schemas.Project.parse_raw(resp.text)

    def fetch_project_avatar(
        self, project_full_slug: str, avatar_url: t.Optional[str] = None
    ) -> storables.AvatarData:
        resp = None
        if avatar_url:
            log_request(url=avatar_url, method="GET")
            resp = self.sess.get(avatar_url, timeout=CONNECTION_TINEOUT)
        if resp is None or resp.status_code == 404:
            return storables.AvatarData.fetch_default(
                project_full_slug + " avatar", avatar_domain=self.base_url
            )
        if avatar_url:
            _check_resp(
                resp, avatar_url, f"Failed to fetch the avatar of project '{project_full_slug}'"
            )
        return storables.AvatarData(bytes_=resp.content, extension=".png")

    def get_model(self, project_full_slug: str, version: str) -> schemas.Model:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project_full_slug / "models" / version
        log_request(url=f.url, method="GET")
        resp = self.sess.get(f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(resp, f.url, f"Failed to fetch info of model '{project_full_slug}:{version}'")
        return schemas.Model.parse_raw(resp.text)

    def get_latest_model(self, project_full_slug: str) -> t.Optional[schemas.Model]:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project_full_slug / "models"
        f.args["per_page"] = str(1)
        f.args["page"] = str(1)
        f.args["order_by"] = "created_at"
        f.args["sort"] = "desc"
        log_request(url=f.url, method="GET")
        resp = self.sess.get(f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(resp, f.url, f"Failed to fetch model list in project '{project_full_slug}'")
        model_list = schemas.ModelList.parse_raw(resp.text)
        if len(model_list.__root__) == 0:
            return None
        return model_list.__root__[0]

    def create_model(self, project_full_slug: str, req: schemas.ModelCreate) -> schemas.Model:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project_full_slug / "models"
        data = req.json()
        log_request(url=f.url, method="POST", data=data)
        resp = self.sess.post(f.url, data=data, timeout=CONNECTION_TINEOUT)
        _check_resp(resp, f.url, f"Failed to create a model in project '{project_full_slug}'")
        return schemas.Model.parse_raw(resp.text)

    def update_model_readme(
        self, project_full_slug: str, version: str, readme: storables.MarkdownData
    ) -> None:
        if len(readme.image_files) > 0:
            resps = self.upload_multiple_files_by_paths(
                project_full_slug=project_full_slug,
                paths=readme.image_files,
                desc="Uploading image files in README",
            )
            image_file_serving_urls = [r.serving_url for r in resps]
            readme_content = change_local_image_links_in_markdown(
                md=readme.content,
                local_img_paths=readme.image_files,
                updates=image_file_serving_urls,
            )

        f = furl(self.base_url)
        f.path = (
            f.path / API_BASE_STR / "projects" / project_full_slug / "models" / version / "readme"
        )
        log_request(url=f.url, method="PUT")
        data = schemas.ModelReadmeUpdate(content=readme_content).json()
        resp = self.sess.put(f.url, data=data, timeout=CONNECTION_TINEOUT)
        _check_resp(
            resp,
            url=f.url,
            err_msg_prefix=f"Failed to upload README of model {project_full_slug}:{version}",
        )

    def get_model_readme(
        self, project_full_slug: str, version: str, image_download_dir: Path
    ) -> storables.MarkdownData:
        f = furl(self.base_url)
        f.path = (
            f.path / API_BASE_STR / "projects" / project_full_slug / "models" / version / "readme"
        )
        log_request(url=f.url, method="GET")
        resp = self.sess.get(url=f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(
            resp, f.url, f"Failed to get the README of model {project_full_slug}:{version}"
        )

        md = resp.text
        image_http_links = get_image_links(md, schemes=["http", "https"])
        if len(image_http_links) > 0:
            downloaded = self.download_multiple_files(
                image_http_links,
                out=image_download_dir,
                desc="Downloading images in README",
            )
            md = change_img_links_in_markdown(
                md, images=image_http_links, updates=[p.as_uri() for p in downloaded]
            )
            return storables.MarkdownData(content=md, image_files=downloaded)
        return storables.MarkdownData(content=md)

    def get_model_source_tree(
        self, project_full_slug: str, version: str
    ) -> schemas.SourceTreeFolder:
        f = furl(self.base_url)
        f.path = (
            f.path / API_BASE_STR / "projects" / project_full_slug / "models" / version / "tree"
        )
        log_request(url=f.url, method="GET")
        resp = self.sess.get(f.url, timeout=CONNECTION_TINEOUT)
        _check_resp(
            resp,
            url=f.url,
            err_msg_prefix=f"Failed to get the source tree of model {project_full_slug}:{version}",
        )
        parsed = schemas.SourceTreeFolder.parse_raw(resp.text)
        return parsed

    def download_model_source_file(
        self, project_full_slug: str, version: str, path: str, root_dir: Path
    ) -> Path:
        download_dir = (root_dir / path).parent
        download_dir.mkdir(exist_ok=True, parents=True)

        f = furl(self.base_url)
        f.path = (
            f.path / API_BASE_STR / "projects" / project_full_slug / "models" / version / "files"
        )
        f.path.segments += [path]  # For url encoding
        log_request(url=f.url, method="GET")
        return download_file(url=f.url, out_path=download_dir, sess=self.sess)

    def download_model_source_tree(
        self, project_full_slug: str, version: str, root_dir: Path
    ) -> t.List[storables.SourceFile]:
        root = self.get_model_source_tree(project_full_slug=project_full_slug, version=version)
        urls: t.List[str] = []
        download_paths: t.List[Path] = []
        ret: t.List[storables.SourceFile] = []

        def _add(path: t.Optional[PurePosixPath], folder: schemas.SourceTreeFolder):
            contents = folder.contents
            for c in contents:
                p = path / c.name if path else PurePosixPath(c.name)
                if c.type == "file":
                    if c.skipped:
                        downloaded = None
                    else:
                        if path is None:
                            downloaded = root_dir / c.name
                        else:
                            downloaded = root_dir / path / c.name

                        urls.append(
                            self._build_source_file_url(project_full_slug, version, str(p))
                        )
                        download_paths.append(downloaded)

                    ret.append(
                        storables.SourceFile(
                            rel_path_in_model_fs=p,
                            abs_path_in_host_fs=downloaded,
                            size=c.size,
                        )
                    )
                else:
                    _add(p, c)

        _add(None, root)
        self.download_multiple_files(urls, download_paths)
        return ret

    def upload_model_source_files(
        self, project_full_slug: str, files: t.Iterable[storables.SourceFile]
    ) -> t.Tuple[t.List[schemas.SourceFileDecl], t.List[schemas.SkippedSourceFileDecl]]:
        source_files, skipped_source_files = [], []
        upload_path_dict = {f: f.abs_path_in_host_fs for f in files if f.abs_path_in_host_fs}
        upload_resps = self.upload_multiple_files_by_paths(
            project_full_slug=project_full_slug,
            paths=list(upload_path_dict.values()),
            desc="Uploading source files",
        )
        upload_resp_dict = {f: url for f, url in zip(upload_path_dict.keys(), upload_resps)}
        for f in files:
            p = str(f.rel_path_in_model_fs)
            if f in upload_resp_dict:
                source_files.append(
                    schemas.SourceFileDecl(path=p, upload_id=upload_resp_dict[f].id)
                )
            else:
                skipped_source_files.append(schemas.SkippedSourceFileDecl(path=p, size=f.size))

        return source_files, skipped_source_files

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

    def upload_file_by_path(
        self, project_full_slug: str, path: Path, desc: t.Optional[str] = None
    ) -> str:
        url = self.build_upload_url(project_full_slug=project_full_slug)
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
        project_full_slug: str,
        buffer: io.BufferedIOBase,
        file_name: str,
        content_type: str,
        desc: t.Optional[str] = None,
    ) -> str:
        url = self.build_upload_url(project_full_slug=project_full_slug)
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
        self, project_full_slug: str, paths: t.List[Path], desc: t.Optional[str] = None
    ) -> t.List[schemas.FileUploadResponse]:
        if len(paths) == 0:
            return []

        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project_full_slug / "uploads"
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
        ret = []
        for p, resp in zip(paths, responses):
            _check_resp(resp, f.url, f"Failed to upload file '{p}'")
            parsed = schemas.FileUploadResponse.parse_raw(resp.text)
            log_debug(f"Response of uploading {p}: {parsed}", pretty=False)
            ret.append(parsed)

        return ret

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
        out: t.Union[Path, t.List[Path]],
        progress_bar: bool = True,
        desc: t.Optional[str] = None,
    ) -> t.List[Path]:
        return download_files_in_threadpool(
            *urls, out=out, sess=self.sess, progress_bar=progress_bar, desc=desc
        )

    def build_upload_url(self, project_full_slug: str) -> str:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project_full_slug / "uploads"
        return f.url

    def _set_auth_header(self, access_token: str):
        self.sess.headers.update(Authorization="Bearer " + access_token)

    def _build_source_file_url(self, project: str, version: str, path: str) -> str:
        f = furl(self.base_url)
        f.path = f.path / API_BASE_STR / "projects" / project / "models" / version / "files"
        f.path.segments += [path]  # For url encoding
        return f.url


def _check_resp(resp: requests.Response, url: str, err_msg_prefix: t.Optional[str] = None):
    check_resp(
        resp=resp, url=url, exc_type=exceptions.TungstenClientError, err_msg_prefix=err_msg_prefix
    )
