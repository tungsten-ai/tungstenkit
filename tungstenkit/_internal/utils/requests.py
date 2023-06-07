import io
import mimetypes
import typing as t
from collections.abc import MutableMapping
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import ExitStack
from itertools import combinations
from pathlib import Path

import requests
from binaryornot.check import is_binary
from requests import Session
from requests_toolbelt.downloadutils.tee import tee
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
from typing_extensions import Literal

from tungstenkit import exceptions
from tungstenkit._internal.logging import log_debug
from tungstenkit.exceptions import ClientError

from .console import build_upload_and_download_progress
from .file import convert_to_unique_path
from .uri import get_filename_from_uri

if t.TYPE_CHECKING:
    from _typeshed import StrPath


CONNECTION_TIMEOUT = 10


def check_resp(
    resp: requests.Response,
    url: str,
    exc_type: t.Type[ClientError],
    err_msg_prefix: t.Optional[str] = None,
):
    if not resp.ok:
        raise exc_type(
            url=url,
            status_code=resp.status_code,
            reason=resp.reason,
            detail=resp.text,
            msg_prefix=err_msg_prefix,
        )


def log_request(
    url: str,
    method: str,
    data: t.Any = None,
    headers: t.Optional[t.Union[t.Dict, MutableMapping]] = None,
):
    msg = f"{method} {url}"
    if headers:
        msg += "\nHeaders: " + str(headers)
    if data:
        msg += "\nData: " + str(data)
    log_debug(msg, pretty=False)


def upload_multiple_form_data_by_paths(
    method: Literal["post", "put"],
    url: str,
    file_paths: t.List[Path],
    field: str = "file",
    headers: t.Optional[t.Dict[str, str]] = None,
    sess: t.Optional[Session] = None,
    progress_bar: bool = False,
    desc: t.Optional[str] = None,
) -> t.List[requests.Response]:
    if len(file_paths) == 0:
        return []

    with ExitStack() as exit_stack:
        create_callback = None
        if progress_bar:
            desc = desc if desc else f"Uploading {len(file_paths)}"
            total_bytes = sum(p.stat().st_size for p in file_paths)
            task, progress = exit_stack.enter_context(
                build_upload_and_download_progress(description=desc, total=total_bytes)
            )

            def create_callback(e: MultipartEncoder):
                last_uploaded_bytes = 0

                def callback(m: MultipartEncoderMonitor):
                    nonlocal last_uploaded_bytes
                    curr_uploaded_bytes = m.bytes_read
                    progress.update(task, advance=curr_uploaded_bytes - last_uploaded_bytes)
                    last_uploaded_bytes = m.bytes_read

                return callback

        executor = exit_stack.enter_context(ThreadPoolExecutor(max_workers=8))
        future_list: t.List[Future] = []
        for p in file_paths:
            fut = executor.submit(
                _upload_form_data_by_path,
                method=method,
                url=url,
                file_path=p,
                field=field,
                headers=headers,
                sess=sess,
                create_callback_fn=create_callback,
            )
            future_list.append(fut)

        responses: t.List[requests.Response] = []
        for fut in future_list:
            responses.append(fut.result())

    return responses


def upload_form_data_by_path(
    method: Literal["post", "put"],
    url: str,
    file_path: Path,
    field: str = "file",
    headers: t.Optional[t.Dict[str, str]] = None,
    sess: t.Optional[Session] = None,
    progress_bar: bool = False,
    desc: t.Optional[str] = None,
) -> requests.Response:
    with ExitStack() as exit_stack:
        create_callback = None
        if progress_bar:
            total_bytes = file_path.stat().st_size
            desc = f"Uploading {file_path.name}" if desc is None else desc
            task, progress = exit_stack.enter_context(
                build_upload_and_download_progress(total=total_bytes, description=desc)
            )

            def create_callback(e: MultipartEncoder):
                def callback(m: MultipartEncoderMonitor):
                    progress.update(task, completed=m.bytes_read)

                return callback

        resp = _upload_form_data_by_path(
            method=method,
            url=url,
            file_path=file_path,
            field=field,
            headers=headers,
            sess=sess,
            create_callback_fn=create_callback,
        )

    return resp


def upload_form_data_by_buffer(
    method: Literal["post", "put"],
    url: str,
    buffer: io.BufferedIOBase,
    file_name: str,
    content_type: str,
    field: str = "file",
    size: t.Optional[int] = None,
    headers: t.Optional[t.Dict[str, str]] = None,
    sess: t.Optional[Session] = None,
    progress_bar: bool = False,
    desc: t.Optional[str] = None,
) -> requests.Response:
    with ExitStack() as exit_stack:
        create_callback = None
        if progress_bar:
            desc = f"Uploading {file_name}" if desc is None else desc
            task, progress = exit_stack.enter_context(
                build_upload_and_download_progress(total=size, description=desc)
            )

            def create_callback(e: MultipartEncoder):
                def callback(m: MultipartEncoderMonitor):
                    progress.update(task, completed=m.bytes_read)

                return callback

        resp = _upload_form_data_by_buffer(
            method=method,
            url=url,
            buffer=buffer,
            file_name=file_name,
            content_type=content_type,
            field=field,
            headers=headers,
            sess=sess,
            create_callback_fn=create_callback,
        )

    return resp


def download_files_in_threadpool(
    *urls: str,
    out: t.Union[Path, t.List[Path]],
    sess: t.Optional[requests.Session] = None,
    headers: t.Optional[t.Dict[str, str]] = None,
    progress_bar: bool = False,
    desc: t.Optional[str] = None,
) -> t.List[Path]:
    if len(urls) == 0:
        return []

    if isinstance(out, Path):
        download_paths = []
        # Download all files in out_path
        if out.exists() and not out.is_dir():
            raise ValueError(f"Not a directory: {out}")
        out.mkdir(exist_ok=True, parents=True)
        for filename in [get_filename_from_uri(url) for url in urls]:
            filepath = (out / filename).resolve()
            if filepath.exists():
                filepath = convert_to_unique_path(filepath)
            filepath.touch()
            download_paths.append(filepath)
    else:
        download_paths = [d.resolve() for d in out]
        assert len(download_paths) == len(urls), "# urls != # download paths"
        path_pairs = combinations(out, 2)
        for p1, p2 in path_pairs:
            assert p1 != p2, f"Path duplication: {p1}"

    with ExitStack() as exit_stack:
        if progress_bar:
            desc = f"Downloading {len(urls)} files" if desc is None else desc
            task, progress = exit_stack.enter_context(
                build_upload_and_download_progress(description=desc)
            )

        def create_callback(p: Path, r: requests.Response):
            def callback_fn(b: bytes):
                if progress_bar:
                    progress.update(task, advance=len(b))

            return callback_fn

        fut_list: t.List[Future] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            for url, download_path in zip(urls, download_paths):
                fut = executor.submit(
                    _download_file,
                    url=url,
                    out_path=download_path,
                    sess=sess,
                    headers=headers,
                    create_callback_fn=create_callback,
                )
                fut_list.append(fut)

            for fut in fut_list:
                fut.result()

    return download_paths


def download_file(
    url: str,
    out_path: "t.Optional[StrPath]" = None,
    sess: t.Optional[requests.Session] = None,
    headers: t.Optional[t.Dict[str, str]] = None,
    progress_bar: bool = False,
    desc: t.Optional[str] = None,
) -> Path:
    with ExitStack() as exit_stack:

        def create_callback(p: Path, r: requests.Response):
            nonlocal desc
            if progress_bar:
                desc = f"Downloading {p.name}" if desc is None else desc
                total = int(r.headers["content-length"]) if "content-length" in r.headers else None
                task, progress = exit_stack.enter_context(
                    build_upload_and_download_progress(total=total, description=desc)
                )

            def callback_fn(b: bytes):
                if progress_bar:
                    progress.update(task, advance=len(b))

            return callback_fn

        downloaded = _download_file(
            url=url,
            out_path=out_path,
            sess=sess,
            headers=headers,
            create_callback_fn=create_callback,
        )

    return downloaded


def _upload_form_data_by_path(
    method: Literal["post", "put"],
    url: str,
    file_path: Path,
    field: str = "file",
    headers: t.Optional[t.Dict[str, str]] = None,
    sess: t.Optional[Session] = None,
    create_callback_fn: t.Optional[
        t.Callable[[MultipartEncoder], t.Callable[[MultipartEncoderMonitor], t.Any]]
    ] = None,
) -> requests.Response:
    file_name, content_type, _ = _get_file_metadata(file_path)
    with open(file_path, "rb") as f:
        return _upload_form_data_by_buffer(
            method=method,
            url=url,
            buffer=f,
            file_name=file_name,
            content_type=content_type,
            field=field,
            headers=headers,
            sess=sess,
            create_callback_fn=create_callback_fn,
        )


def _upload_form_data_by_buffer(
    method: Literal["post", "put"],
    url: str,
    buffer: io.BufferedIOBase,
    file_name: str,
    content_type: str,
    field: str = "file",
    headers: t.Optional[t.Dict[str, str]] = None,
    sess: t.Optional[Session] = None,
    create_callback_fn: t.Optional[
        t.Callable[[MultipartEncoder], t.Callable[[MultipartEncoderMonitor], t.Any]]
    ] = None,
) -> requests.Response:
    e = MultipartEncoder(fields={field: (file_name, buffer, content_type)})
    m = MultipartEncoderMonitor(e, create_callback_fn(e) if create_callback_fn else None)
    headers = headers if headers else dict()
    if "content-type" not in [k.lower() for k in headers.keys()]:
        headers["Content-Type"] = e.content_type

    sess = requests.Session() if sess is None else sess
    resp = sess.request(
        method=method, url=url, headers=headers, data=m, timeout=CONNECTION_TIMEOUT
    )
    return resp


def _download_file(
    url: str,
    out_path: "t.Optional[StrPath]" = None,
    sess: t.Optional[requests.Session] = None,
    headers: t.Optional[t.Dict[str, str]] = None,
    create_callback_fn: t.Optional[
        t.Callable[[Path, requests.Response], t.Callable[[bytes], None]]
    ] = None,
) -> Path:
    sess = sess if sess else requests.Session()
    headers = dict() if headers is None else headers
    headers.update(
        {
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate, br",
        }
    )
    out_path = Path() if out_path is None else Path(out_path)
    out_path = out_path.resolve()

    if out_path.is_dir():
        filename_in_url = get_filename_from_uri(url)
        file_path = out_path / Path(filename_in_url).name
        file_path = convert_to_unique_path(file_path)
    else:
        if not out_path.parent.exists():
            out_path.parent.mkdir(parents=True, exist_ok=True)
        file_path = out_path

    try:
        r = sess.get(
            url,
            headers=headers,
            stream=True,
            timeout=CONNECTION_TIMEOUT,
        )
    except requests.exceptions.ConnectionError:
        raise exceptions.DownloadError(f"Failed to connect to {url}")

    callback_fn = create_callback_fn(file_path, r) if create_callback_fn else None
    _save_file_from_http_resp(response=r, file_path=file_path, callback_fn=callback_fn)

    return file_path.resolve()


def _save_file_from_http_resp(
    response: requests.Response,
    file_path: Path,
    callback_fn: t.Optional[t.Callable[[bytes], None]] = None,
) -> None:
    try:
        if not response.ok:
            raise exceptions.DownloadError(
                (f"Failed to download from {response.url}\nResponse: {response.text}")
            )
        with open(file_path, "wb") as f:
            for chunk in tee(response, f, decode_content=True):
                if callback_fn:
                    callback_fn(chunk)
    finally:
        response.close()


def _get_file_metadata(file_path: Path):
    file_name = file_path.name
    content_type = mimetypes.guess_type(str(file_path), strict=False)[0]
    size = file_path.stat().st_size
    if content_type is None:
        content_type = "application/octet-stream" if is_binary(str(file_path)) else "text/plain"

    return file_name, content_type, size
