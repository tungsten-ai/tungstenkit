import base64
import hashlib
import io
import json
import mimetypes
import re
import typing as t
from enum import Enum
from io import BufferedIOBase, TextIOBase
from pathlib import Path

from binaryornot.check import is_binary
from fastapi.encoders import jsonable_encoder
from furl import furl
from PIL import Image as PILImage
from pydantic import BaseModel
from pydantic import Field as PydanticField
from pydantic.fields import ModelField, Undefined
from typing_extensions import Literal
from w3lib.url import parse_data_uri

from tungstenkit._internal import contexts
from tungstenkit._internal.utils.requests import download_file
from tungstenkit._internal.utils.string import camel_to_snake
from tungstenkit._internal.utils.uri import get_path_from_file_url, get_uri_scheme, save_data_url

F = t.TypeVar("F", bound="File")

RE_BASE64 = "^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)?$"
SUPPORTED_URL_SCHEMES_FOR_FILES = ["http", "https", "data", "file"]
IMAGE_MODES_IN_PILLOW = ["RGB", "RGBA", "CMYK", "YCbCr", "LAB", "HSV", "1", "L", "P", "I", "F"]
BUFFER_SIZE = 4 * 1024 * 1024


class FileType(str, Enum):
    image = "image"
    video = "video"
    audio = "audio"
    binary = "binary"


class URIForFile(str):
    validate_always = True

    def get_scheme(self):
        return get_uri_scheme(self)

    def to_file_uri(self) -> "URIForFile":
        scheme = self.get_scheme()

        if scheme == "data":
            path = save_data_url(self, ".")
            return URIForFile(Path(path).as_uri())

        if scheme == "http" or scheme == "https":
            return URIForFile(download_file(url=self, out_path=".").as_uri())

        return self

    def to_data_uri(self) -> "URIForFile":
        scheme = self.get_scheme()

        if scheme == "data":
            return self

        file_uri = self.to_file_uri()
        path = get_path_from_file_url(file_uri)
        mimetype = mimetypes.guess_type(url=file_uri, strict=False)[0]
        if mimetype is None:
            mimetype = "application/octet-stream" if is_binary(str(path)) else "text/plain"
        return URIForFile(
            f"data:{mimetype};base64,{base64.b64encode(path.read_bytes()).decode('utf-8')}"
        )

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: t.Any):
        if not isinstance(v, str):
            raise ValueError(f"Type of uri should be 'str', not '{type(v)}'.")

        if isinstance(v, URIForFile):
            return cls(v)

        scheme = get_uri_scheme(v)
        if not scheme:
            if (
                contexts.APP == contexts.Application.MODEL_SERVER
                or contexts.APP == contexts.Application.TASK_SERVER  # noqa: W503
            ):
                is_base64 = _check_base64(v)
                if not is_base64:
                    raise ValueError(
                        "Invalid file input. File input should be either an url or "
                        "a base64-encoded string"
                    )
                return cls.from_b64str(v)
            else:
                return Path(v).resolve().as_uri()

        if scheme not in SUPPORTED_URL_SCHEMES_FOR_FILES:
            raise ValueError(
                f"Unsupported URI scheme: '{scheme}'. "
                f"Supported schemes: {', '.join(SUPPORTED_URL_SCHEMES_FOR_FILES)}"
            )
        if scheme == "file":
            parsed = furl(v)
            if parsed.netloc:
                raise ValueError("Remote files are not supported")

        return cls(v)

    @classmethod
    def from_b64str(cls, base64_str: str):
        try:
            data_uri_header = "data:application/octet-stream;base64"
            return cls(data_uri_header + "," + base64_str)
        except Exception:
            raise ValueError(f"Not a valid base64-encoded string: '{base64_str[:100]}...'")

    @classmethod
    def __modify_schema__(cls, field_schema: t.Dict[str, t.Any]) -> None:
        field_schema["format"] = "uri"


# TODO remove inheritance from BaseModel and __root__
class File(BaseModel):
    _schema_prefix: t.ClassVar[str] = "#/tungsten/"
    __root__: URIForFile

    @classmethod
    def from_url(cls: t.Type[F], url: str) -> F:
        if not isinstance(url, str):
            raise TypeError(f"expected 'str' for url, not {type(url)}")
        scheme = get_uri_scheme(url)
        if not scheme:
            raise ValueError(f"cannot determine url scheme in '{url}'")
        return cls.parse_obj(url)

    @classmethod
    def from_path(cls: t.Type[F], path: t.Union[str, Path]) -> F:
        if not isinstance(path, str) and not isinstance(path, Path):
            raise TypeError(f"expected 'str' or 'pathlib.Path' for path, not {type(path)}")
        p = Path(path)
        file_url = p.resolve().as_uri()
        return cls.parse_obj(file_url)

    @classmethod
    def from_bytes(cls: t.Type[F], data: bytes) -> F:
        if not isinstance(data, bytes):
            raise TypeError(f"expected 'bytes' for data, not {type(data)}")

        return cls.parse_obj(_build_data_url(data))

    @classmethod
    def from_buffer(cls: t.Type[F], buffer: t.Union[BufferedIOBase, TextIOBase]) -> F:
        if not isinstance(buffer, BufferedIOBase) and not isinstance(buffer, TextIOBase):
            raise TypeError(f"Not a buffer: {type(buffer)}")

        if hasattr(buffer, "name"):
            p = Path(buffer.name)
            if p.exists() and p.is_file():
                return cls.from_path(p)

        raw = buffer.read()
        if isinstance(raw, str):
            raw = raw.encode()
        return cls.parse_obj(_build_data_url(raw))

    @property
    def path(self) -> Path:
        self.__root__ = self.__root__.to_file_uri()
        return get_path_from_file_url(self.__root__)

    @classmethod
    def __modify_schema__(
        cls, field_schema: t.Dict[str, t.Any], field: t.Optional[ModelField]
    ) -> None:
        field_schema["type"] = "string"
        field_schema["format"] = "uri"

        default = field.default if field else None
        if isinstance(default, File):
            field_schema["default"] = default.__root__

    @classmethod
    def _get_typeenum(cls) -> FileType:
        return FileType(camel_to_snake(cls.__name__))


class Image(File):
    @staticmethod
    def from_pil_image(pil_image: PILImage.Image) -> "Image":
        # TODO log warning when this is called while building
        if not isinstance(pil_image, PILImage.Image):
            raise TypeError(f"Invalid type for 'pil_image': {type(pil_image)}")
        try:
            mime_type: str = pil_image.get_format_mimetype()
            fmt = pil_image.format
        except AttributeError:
            mime_type = "image/png"
            fmt = "PNG"

        data_uri_header = f"data:{mime_type};base64"
        bytes_io = io.BytesIO()
        pil_image.save(bytes_io, format=fmt)
        image_bytes = bytes_io.getvalue()
        image_b64_str = base64.b64encode(image_bytes).decode()
        bytes_io.close()
        return Image(__root__=URIForFile(data_uri_header + "," + image_b64_str))

    def to_pil_image(
        self,
        mode: Literal[
            "RGB", "RGBA", "CMYK", "YCbCr", "LAB", "HSV", "1", "L", "P", "I", "F"
        ] = "RGB",
    ) -> PILImage.Image:
        """
        Convert to PIL Image.
        """
        if mode not in IMAGE_MODES_IN_PILLOW:
            raise ValueError("Unsupported image mode: '{}'")

        scheme = get_uri_scheme(self.__root__)
        if scheme == "data":
            try:
                data = parse_data_uri(self.__root__).data
            except Exception:
                err_msg = f"Invalid data uri: '{self.__root__[:100]}'"
                if len(self.__root__) > 100:
                    err_msg += "..."
                raise ValueError(err_msg)
            pil_image = PILImage.open(io.BytesIO(data))
        else:
            pil_image = PILImage.open(self.path)

        return pil_image.convert(mode)

    class Config:
        schema_extra = {"example": "https://picsum.photos/200.jpg"}


class Binary(File):
    class Config:
        schema_extra = {"example": "data:text/plain;base64,aGVsbG8gd29ybGQ="}


class Video(File):
    class Config:
        schema_extra = {
            "example": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"  # noqa
        }


class Audio(File):
    class Config:
        schema_extra = {"example": "https://download.samplelib.com/mp3/sample-3s.mp3"}


class BaseIO(BaseModel):
    def _hash_for_batching(self):
        m = hashlib.sha256()
        to_be_hashsed = ""
        for field_name, field in self.__fields__.items():
            if not field.required:
                serialized_field_value = json.dumps(
                    jsonable_encoder(getattr(self, field_name))
                ).replace("\n", "")
                to_be_hashsed += field_name + ":" + serialized_field_value + "\n"

        m.update(to_be_hashsed.encode("utf-8"))
        return "sha256:" + m.hexdigest()

    class Config:
        validate_assignment = True
        validate_all = True
        arbitrary_types_allowed = True


def filetype_to_cls(filetype: FileType) -> t.Type[File]:
    for cls in File.__subclasses__():
        if cls._get_typeenum() == filetype:
            return cls
    raise NotImplementedError(filetype)


def Field(
    *,
    description: t.Optional[str] = None,
    choices: t.Optional[t.Sequence[t.Union[str, int]]] = None,
    ge: t.Optional[float] = None,
    le: t.Optional[float] = None,
    min_length: t.Optional[int] = None,
    max_length: t.Optional[int] = None,
):
    extras: t.Dict[str, t.Any] = dict()
    if choices is not None:
        extras.update(choices=choices)
    return PydanticField(
        default=Undefined,
        description=description,
        ge=ge,
        le=le,
        min_length=min_length,
        max_length=max_length,
        **extras,
    )


def Option(
    default: t.Any,
    *,
    description: t.Optional[str] = None,
    choices: t.Optional[t.Sequence[t.Union[str, int]]] = None,
    ge: t.Optional[float] = None,
    le: t.Optional[float] = None,
    min_length: t.Optional[int] = None,
    max_length: t.Optional[int] = None,
):
    extras: t.Dict[str, t.Any] = dict()
    if choices is not None:
        extras.update(choices=choices)
    return PydanticField(
        default=default,
        description=description,
        ge=ge,
        le=le,
        min_length=min_length,
        max_length=max_length,
        **extras,
    )


def build_uri_for_file(file: t.Any) -> URIForFile:
    """Convert url/path/buffer in input to uri."""

    if isinstance(file, Path):
        return File.from_path(file).__root__

    if isinstance(file, str):
        # If file type is ``str``, it can be both url and path
        return File.parse_obj(file).__root__

    if isinstance(file, File):
        return file.__root__

    if isinstance(file, bytes):
        return File.from_bytes(file).__root__

    if isinstance(file, BufferedIOBase) or isinstance(file, TextIOBase):
        return File.from_buffer(file).__root__

    raise TypeError(
        f"Unsupported file type in input: '{type(file)}'. It should be path, url, or buffer."
    )


def _check_base64(s: str) -> bool:
    return False if s is None or not re.search(RE_BASE64, s) else True


def _build_data_url(data: bytes) -> URIForFile:
    return URIForFile.from_b64str(base64.b64encode(data).decode())
