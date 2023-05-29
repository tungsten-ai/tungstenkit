import typing as t

from pydantic import Field

from tungstenkit import Audio, BaseIO, Binary, Image, Video
from tungstenkit._internal.io import FileType
from tungstenkit._internal.io_schema import get_filetypes, validate_input_class


def test_default_field_description():
    class Input(BaseIO):
        my_string: str = "my string"
        this_is_an_image: Image = Image(__root__="http://localhost/image")
        field_with_desc: str = Field("field", description="desc")

    input_cls = validate_input_class(Input)
    schema = input_cls.schema()
    properties = schema["properties"]
    for field_name, field in input_cls.__fields__.items():
        if field_name == "my_string":
            assert field.field_info.description == "My String"
            assert properties[field_name]["description"] == "My String"
        elif field_name == "this_is_an_image":
            assert field.field_info.description == "This Is An Image"
            assert properties[field_name]["description"] == "This Is An Image"
        elif field_name == "field_with_desc":
            assert field.field_info.description == "desc"
            assert properties[field_name]["description"] == "desc"


def test_get_filetypes():
    class Nested(BaseIO):
        image: Image
        filedict: t.Dict[str, Image]

    class Output(BaseIO):
        string: str
        image: Image
        audio: Audio
        video: Video
        binary: Binary
        nested: Nested
        filedict: t.Dict[str, Image]
        filelist: t.List[Audio]
        somedict: t.Dict[str, float]
        somelist: t.List[int]

    filetypes = get_filetypes(Output)
    assert filetypes == {
        "image": FileType.image,
        "audio": FileType.audio,
        "video": FileType.video,
        "binary": FileType.binary,
        "filedict.$item": FileType.image,
        "filelist.$item": FileType.audio,
        "nested.image": FileType.image,
        "nested.filedict.$item": FileType.image,
    }
