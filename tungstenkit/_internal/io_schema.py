import inspect
import typing as t

from pydantic import create_model as create_pydantic_model
from pydantic.fields import FieldInfo
from pydantic.typing import is_none_type, is_union

from tungstenkit._internal import io
from tungstenkit._internal.utils.string import camel_to_snake
from tungstenkit._internal.utils.types import get_type_args, get_type_origin

SUPPORTED_INPUT_TYPES: t.List[t.Type] = [
    int,
    float,
    str,
    bool,
    io.Image,
    io.Video,
    io.Audio,
    io.Binary,
]
SUPPORTED_OUTPUT_COMPOSITE_TYPES: t.List[t.Type] = [io.BaseIO, list, dict]
SUPPORTED_OUTPUT_TERMINAL_TYPES = SUPPORTED_INPUT_TYPES
SUPPORTED_DICT_KEY_TYPES: t.List[t.Type] = [str, bool, int]
SUPPORTED_OUTPUT_TYPES = SUPPORTED_OUTPUT_TERMINAL_TYPES + SUPPORTED_OUTPUT_COMPOSITE_TYPES


def build_field_type_err_msg(invalid_fields: t.Dict[str, t.Type]):
    err_msg = ""
    for name, type_ in invalid_fields.items():
        err_msg += f" - '{name}': {type_}"
    return err_msg


def validate_input_class(input_cls: t.Type):
    if not issubclass(input_cls, io.BaseIO):
        raise TypeError(f"Input type {input_cls} is not a subclass of {io.BaseIO}")

    invalid_types: t.Dict[str, t.Type] = dict()
    type_hints = t.get_type_hints(input_cls)
    fields = input_cls.__fields__
    for name, type_ in type_hints.items():
        field = fields[name]
        origin = get_type_origin(type_)
        type_args = get_type_args(type_)
        valid = False

        if (
            not field.required
            and is_union(origin)
            and sum(is_none_type(arg) for arg in type_args) == 1
            and len(type_args) == 2
        ):
            type_idx = [is_none_type(arg) for arg in type_args].index(False)

            valid = inspect.isclass(type_args[type_idx]) and any(
                issubclass(type_args[type_idx], supported_input_type)
                for supported_input_type in SUPPORTED_INPUT_TYPES
            )
        elif inspect.isclass(origin):
            valid = any(
                issubclass(origin, supported_input_type)
                for supported_input_type in SUPPORTED_INPUT_TYPES
            )

        if not valid:
            invalid_types[input_cls.__name__ + "." + name] = type_

    if len(invalid_types) > 0:
        err_msg = "Invalid input types:\n"
        for name, type_ in invalid_types.items():
            err_msg += f' - "{name}": "{type_}" (unsupported input type)\n'
        err_msg += "Supported input types: " + ", ".join(
            [
                "'" + "tungstenkit." + type_.__name__ + "'"
                if type_.__module__ == io.__name__
                else f"'{type_.__name__}'"
                for type_ in SUPPORTED_INPUT_TYPES
            ]
        )
        raise TypeError(err_msg)

    # Set the default description on input fields if not set
    updated_fields: t.Dict[str, t.Tuple[t.Type, FieldInfo]] = dict()
    for name, type_ in type_hints.items():
        field = fields[name]
        field_info = fields[name].field_info
        if not field_info.description:
            field_info.description = _build_default_description(field_name=name)
            updated_fields[name] = (type_, field_info)

    if len(updated_fields) > 0:
        input_cls = create_pydantic_model(  # type: ignore
            input_cls.__name__,
            __base__=input_cls,
            **updated_fields,
        )

    return input_cls


def validate_output_class(output_cls: t.Type):
    if not inspect.isclass(output_cls) or not issubclass(output_cls, io.BaseIO):
        raise TypeError(f"Output type '{output_cls}' is not a subclass of '{io.BaseIO}'")

    invalid_types_and_reasons: t.Dict[str, t.Tuple[t.Type, str]] = dict()

    unsupported_field = False
    unsupported_dict_key = False

    def validate_type(type_: t.Type, field_name: str):
        nonlocal unsupported_field, unsupported_dict_key

        origin = get_type_origin(type_)
        type_args = get_type_args(type_)

        if not inspect.isclass(origin):
            unsupported_field = True
            invalid_types_and_reasons[field_name] = (type_, "unsupported output type")
            return

        for supported_output_type in SUPPORTED_OUTPUT_TERMINAL_TYPES:
            if issubclass(origin, supported_output_type):
                return

        def set_no_type_args_err():
            invalid_types_and_reasons[field_name] = (
                type_,
                "no type argument",
            )

        if issubclass(origin, list):
            if len(type_args) == 0:
                set_no_type_args_err()
            else:
                validate_type(type_args[0], field_name + ".<'item'>")

        elif issubclass(origin, dict):
            if len(type_args) < 2:
                invalid_types_and_reasons[field_name] = (
                    type_,
                    f"too few type arguments; actual {len(type_args)}, expected 2",
                )
            else:
                if type_args[0] not in SUPPORTED_DICT_KEY_TYPES:
                    invalid_types_and_reasons[field_name + ".<'key'>"] = (
                        type_args[0],
                        "unsupported type for dictionary keys.",
                    )
                    unsupported_dict_key = True
                validate_type(type_args[1], field_name + ".<'value'>")

        elif issubclass(origin, io.BaseIO):
            if any(not field.required for field in origin.__fields__.values()):
                invalid_types_and_reasons[field_name] = (type_, "output cannot have an option")
            else:
                for name, type_ in t.get_type_hints(origin).items():
                    validate_type(type_, field_name + "." + name)

        else:
            unsupported_field = True
            invalid_types_and_reasons[field_name] = (type_, "unsupported output type")

    validate_type(output_cls, output_cls.__name__)

    if len(invalid_types_and_reasons) > 0:
        err_msg = "Invalid output types:\n"
        for name, (type_, reason) in invalid_types_and_reasons.items():
            err_msg += f' - "{name}": "{type_}" ({reason})\n'
        if unsupported_field:
            err_msg += "Supported output types: " + ", ".join(
                [
                    "'" + "tungstenkit." + type_.__name__ + "'"
                    if type_.__module__ == io.__name__
                    else f"'{type_.__name__}'"
                    for type_ in SUPPORTED_OUTPUT_TYPES
                ]
            )
        if unsupported_dict_key:
            err_msg += "Supported types for dict keys: " ", ".join(
                [f"'{type_.__name__}'" for type_ in SUPPORTED_DICT_KEY_TYPES]
            )
        raise TypeError(err_msg)

    return output_cls


validate_demo_output_class = validate_output_class


def get_filetypes(io_cls: t.Type[io.BaseIO]) -> t.Dict[str, io.FileType]:
    """
    Returns a dict mapping from "json index" to ``FileType``.
    For example,
    ```
    {
        "image": FileType.Image,
        "nested.image": Filetype.Image,
        "somedict.$item": FileType.Image,
        "somelist.$item": FileType.Image,
    }
    ```
    """

    ret: t.Dict[str, io.FileType] = dict()

    def _get_filetypes(type_: type, json_index: str):
        origin = get_type_origin(type_)
        type_args = get_type_args(type_)

        if is_union(origin):
            is_type_arg_none = [is_none_type(arg) for arg in type_args]
            if sum(is_type_arg_none) != 1 or len(type_args) != 2:
                return

            type_idx = is_type_arg_none.index(False)
            type_ = type_args[type_idx]
            origin = get_type_origin(type_)
            type_args = get_type_args(type_)

        if not inspect.isclass(origin):
            return

        if issubclass(origin, io.File):
            ret[json_index] = origin._get_typeenum()

        elif issubclass(origin, list):
            _get_filetypes(type_args[0], json_index=json_index + ".$item")

        elif issubclass(origin, dict):
            _get_filetypes(type_args[1], json_index=json_index + ".$item")

        elif issubclass(origin, io.BaseIO):
            for field_name, type_ in t.get_type_hints(origin).items():
                field_index = json_index + "." + field_name if json_index else field_name
                _get_filetypes(type_, field_index)

    _get_filetypes(io_cls, "")
    return ret


def get_files_in_input_json(input_json: t.Dict, filefield_names: t.List[str]) -> t.Dict:
    ret = dict()
    for k, v in input_json.items():
        if k in filefield_names:
            ret[k] = v
    return ret


def _build_default_description(field_name: str):
    snake_name = camel_to_snake(field_name)
    name_segments = snake_name.split("_")
    desc = " ".join(name_segments).title()
    return desc
