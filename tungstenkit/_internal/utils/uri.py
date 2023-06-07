import mimetypes
import os
import tempfile
from pathlib import Path, PurePath, PurePosixPath
from typing import TYPE_CHECKING, List, TypeVar
from urllib.parse import unquote
from uuid import uuid4

from furl import furl
from w3lib.url import parse_data_uri

from .string import removeprefix

if TYPE_CHECKING:
    from _typeshed import StrPath

T = TypeVar("T", bound=PurePath)


def get_uri_scheme(uri_str: str) -> str:
    return furl(uri_str[:50]).scheme


def check_if_uri_in_allowed_schemes(obj, allowed_schemes: List[str]) -> bool:
    if isinstance(obj, str):
        for scheme in allowed_schemes:
            if get_uri_scheme(obj) == scheme:
                return True
    return False


def check_if_file_uri(obj) -> bool:
    return check_if_uri_in_allowed_schemes(obj, ["file"])


def check_if_data_uri(obj) -> bool:
    return check_if_uri_in_allowed_schemes(obj, ["data"])


def check_if_http_or_https_uri(obj) -> bool:
    return check_if_uri_in_allowed_schemes(obj, ["http", "https"])


def get_path_from_file_url(file_uri: str) -> Path:
    segments = _parse_file_url_segments(file_uri)
    if os.name == "nt" and segments[0].endswith(":"):
        segments[0] += "\\"
    return "/" / Path(*segments)


def get_pure_posix_path_from_file_uri(file_uri: str) -> PurePosixPath:
    segments = _parse_file_url_segments(file_uri)
    return "/" / PurePosixPath(*segments)


def get_filename_from_uri(url: str) -> str:
    f = furl(url)
    if f.scheme == "http" or f.scheme == "https":
        filename = f.path.segments[-1] if len(f.path.segments) > 1 else None
        if not filename:
            filename = uuid4().hex
    elif f.scheme == "data":
        ext = mimetypes.guess_extension(
            parse_data_uri(url.split(",", maxsplit=1)[0] + ",").media_type
        )
        filename = uuid4().hex + (ext if ext else "")
    else:
        raise ValueError(f"Unsupported scheme {f.scheme}")

    # For the case where filename include directory separators
    filename = Path(filename).name
    return filename


def save_data_url(data_url: str, directory: "StrPath") -> Path:
    try:
        parsed_data_uri = parse_data_uri(data_url)
    except Exception:
        err_msg = f"Invalid data uri: '{data_url[:100]}'"
        if len(data_url) > 100:
            err_msg += "..."
        raise ValueError(err_msg)
    mime_type = parsed_data_uri.media_type
    ext = mimetypes.guess_extension(type=mime_type)
    fd, path = tempfile.mkstemp(suffix=ext, dir=str(directory))
    with os.fdopen(fd, mode="wb") as f:
        f.write(parsed_data_uri.data)
    return Path(path).resolve()


def strip_scheme_in_http_url(http_url: str) -> str:
    f = furl(http_url)
    if f.scheme == "http" or f.scheme == "https":
        return removeprefix(http_url, f.scheme + "://")
    else:
        raise NotImplementedError("Unsupported scheme: " + f.scheme)


def _parse_file_url_segments(file_url: str) -> List[str]:
    assert file_url.startswith("file:///"), f"Invalid file uri: {file_url}"
    return [unquote(s) for s in removeprefix(file_url, "file:///").split("/")]
