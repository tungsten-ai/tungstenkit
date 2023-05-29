"""
A module for defining Tungsten models without inheritance.

The update will be applied after mypy class decorator issue is resolved (#3135)
Reference: https://github.com/python/mypy/issues/3135
"""

import inspect
import typing as t

from typing_extensions import Protocol

from tungstenkit import exceptions
from tungstenkit._internal.utils import types as type_utils
from tungstenkit.io import BaseIO

DEFINED_MODEL_SET: t.Set[type] = set()


C = t.TypeVar("C", bound=type)


class TungstenModel(Protocol):
    __tungsten_config__: t.Dict[str, t.Any]
    __tungsten_input__: t.Optional[BaseIO]
    __tungsten_output__: t.Optional[BaseIO]

    def predict(self, inputs):
        ...

    def predict_demo(self, inputs):
        ...

    def define_input(self):
        ...

    def define_output(self):
        ...

    def train(self):
        ...

    @classmethod
    def derivate(
        cls,
        maybe_cls: t.Optional[type] = None,
        *,
        input: "t.Optional[t.Type[BaseIO]]" = None,
        output: "t.Optional[t.Type[BaseIO]]" = None,
        name: t.Optional[str] = None,
        gpu: bool = False,
        description: t.Optional[str] = None,
        python_packages: t.Optional[t.List[str]] = None,
        python_version: t.Optional[str] = None,
        system_packages: t.Optional[t.List[str]] = None,
        cuda_version: t.Optional[str] = None,
        readme_md: t.Optional[str] = None,
        batch_size: int = 1,
        gpu_mem_gb: int = 16,
        mem_gb: int = 8,
        include_files: t.Optional[t.List[str]] = None,
        exclude_files: t.Optional[t.List[str]] = None,
        dockerfile_commands: t.Optional[t.List[str]] = None,
        base_image: t.Optional[str] = None,
    ):
        ...


@t.overload
@t.data
def define(
    maybe_cls: None = None,
    *,
    input: t.Type[BaseIO],
    output: t.Type[BaseIO],
    gpu: bool = False,
    description: t.Optional[str] = None,
    python_packages: t.Optional[t.List[str]] = None,
    python_version: t.Optional[str] = None,
    system_packages: t.Optional[t.List[str]] = None,
    cuda_version: t.Optional[str] = None,
    readme_md: t.Optional[str] = None,
    batch_size: int = 1,
    gpu_mem_gb: int = 16,
    mem_gb: int = 8,
    include_files: t.Optional[t.List[str]] = None,
    exclude_files: t.Optional[t.List[str]] = None,
    dockerfile_commands: t.Optional[t.List[str]] = None,
    base_image: t.Optional[str] = None,
) -> t.Callable[[C], t.Type[TungstenModel]]:
    ...


@t.overload
def define(
    maybe_cls: C,
    *,
    input: t.Type[BaseIO],
    output: t.Type[BaseIO],
    gpu: bool = False,
    description: t.Optional[str] = None,
    python_packages: t.Optional[t.List[str]] = None,
    python_version: t.Optional[str] = None,
    system_packages: t.Optional[t.List[str]] = None,
    cuda_version: t.Optional[str] = None,
    readme_md: t.Optional[str] = None,
    batch_size: int = 1,
    gpu_mem_gb: int = 16,
    mem_gb: int = 8,
    include_files: t.Optional[t.List[str]] = None,
    exclude_files: t.Optional[t.List[str]] = None,
    dockerfile_commands: t.Optional[t.List[str]] = None,
    base_image: t.Optional[str] = None,
) -> t.Type[TungstenModel]:
    ...


def define(
    maybe_cls=None,
    *,
    input: t.Type[BaseIO],
    output: t.Type[BaseIO],
    gpu: bool = False,
    description: t.Optional[str] = None,
    python_packages: t.Optional[t.List[str]] = None,
    python_version: t.Optional[str] = None,
    system_packages: t.Optional[t.List[str]] = None,
    cuda_version: t.Optional[str] = None,
    readme_md: t.Optional[str] = None,
    batch_size: int = 1,
    gpu_mem_gb: int = 16,
    mem_gb: int = 8,
    include_files: t.Optional[t.List[str]] = None,
    exclude_files: t.Optional[t.List[str]] = None,
    dockerfile_commands: t.Optional[t.List[str]] = None,
    base_image: t.Optional[str] = None,
):
    kwargs = {key: value for key, value in locals().items() if key != "maybe_cls"}

    def wrap(cls_):
        cls_builder = _ClassBuilder(cls=cls_, **kwargs)
        wrapped = cls_builder.build_class()
        DEFINED_MODEL_SET.add(wrapped)
        return wrapped

    # ``maybe_cls`` will be a class if it is used as ``@define``
    # but ``None`` if used as ``@define()``.
    if maybe_cls is None:
        return wrap
    else:
        return wrap(maybe_cls)


class _ClassBuilder:
    """
    Tungsten model class builder.

    A Tungstne model class has:
    - ``__tungsten_config__`` attribute
    - ``__tungsten_input__`` attribute if the input class is given
    - ``__tungsten_output__`` attribute if the output class is given
    - ``predict`` method
    - ``predict_demo`` method
    - ``setup`` method
    - ``define_input`` method
    - ``define_output`` method
    - ``train`` method if defined in the original class
    """

    def __init__(
        self,
        cls,
        input: t.Optional[type] = None,
        output: t.Optional[type] = None,
        **config_kwargs,
    ):
        self._cls: TungstenModel = cls
        self._cls_qualname = type_utils.get_qualname(cls)

        # ``input`` and ``output`` should be a subclass of ``BaseIO``
        if input is not None and not issubclass(input, BaseIO):
            raise exceptions.TungstenModelError(
                f"'input' should be a subclass of {type_utils.get_qualname(BaseIO)}"
            )
        if output is not None and not issubclass(output, BaseIO):
            raise exceptions.TungstenModelError(
                f"'output' should be a subclass of {type_utils.get_qualname(BaseIO)}"
            )
        self._input = input
        self._output = output
        self._config = config_kwargs

        # ``predict`` method is required.
        if not hasattr(cls, "predict"):
            raise exceptions.TungstenModelError(
                f"'predict' method not found in class '{self._cls_qualname}'"
            )
        self._has_setup = bool(getattr(cls, "setup", False))
        self._has_predict_demo = bool(getattr(cls, "predict_demo", False))
        self._has_define_input = bool(getattr(cls, "define_input", False))
        self._has_define_output = bool(getattr(cls, "define_output", False))
        self._has_train = bool(getattr(cls, "train", False))

        # One among ``input`` and ``define_input`` should be defined.
        if not self._has_define_input and input is None:
            raise exceptions.TungstenModelError(
                f"'input' in '{type_utils.get_qualname(define)}' is None, "
                f"but 'define_input' method is not defined in class '{self._cls_qualname}'."
            )
        # One among ``output`` and ``define_output`` should be defined
        if not self._has_define_output and output is None:
            raise exceptions.TungstenModelError(
                f"'output' in '{type_utils.get_qualname(define)}' is None, "
                f"but 'define_output' method is not defined in class '{self._cls_qualname}'."
            )

        # Validate user-defined methods
        _validate_predict_def(getattr(cls, "predict"))
        if self._has_setup:
            _validate_setup_def(getattr(cls, "setup"))
        if self._has_predict_demo:
            _validate_predict_demo_def(getattr(cls, "predict_demo"))
        if self._has_define_input:
            _validate_define_input_def(getattr(cls, "define_input"))
        if self._has_define_output:
            _validate_define_output_def(getattr(cls, "define_output"))
        if self._has_train:
            _validate_train_def(getattr(cls, "train"))

    def build_class(self) -> TungstenModel:
        # Set private variables
        setattr(self._cls, "__tungsten_config__", self._config)
        if self._input is not None:
            setattr(self._cls, "__tungsten_input__", self._input)
        if self._output is not None:
            setattr(self._cls, "__tungsten_output__", self._output)

        # Set methods
        self._set_derivate()
        if not self._has_setup:
            self._set_default_setup()
        if not self._has_predict_demo:
            self._set_default_predict_demo()
        if not self._has_define_input:
            self._set_default_define_input()
        if not self._has_define_output:
            self._set_default_define_output()

        return self._cls

    def _set_default_setup(self):
        def setup(self):
            pass

        self._set_method(setup)

    def _set_default_predict_demo(self):
        def predict_demo(self, inputs):
            outputs = self.predict(inputs)
            return outputs, outputs

        self._set_method(predict_demo)

    def _set_default_define_input(self):
        def define_input(self):
            return self.__tungsten_input__

        self._set_method(define_input)

    def _set_default_define_output(self):
        def define_output(self):
            return self.__tungsten_output__

        self._set_method(define_output)

    def _set_derivate(self):
        def derivate(
            maybe_cls: t.Optional[type] = None,
            *,
            input: "t.Optional[t.Type[BaseIO]]" = None,
            output: "t.Optional[t.Type[BaseIO]]" = None,
            name: t.Optional[str] = None,
            gpu: bool = False,
            description: t.Optional[str] = None,
            python_packages: t.Optional[t.List[str]] = None,
            python_version: t.Optional[str] = None,
            system_packages: t.Optional[t.List[str]] = None,
            cuda_version: t.Optional[str] = None,
            readme_md: t.Optional[str] = None,
            batch_size: int = 1,
            gpu_mem_gb: int = 16,
            mem_gb: int = 8,
            include_files: t.Optional[t.List[str]] = None,
            exclude_files: t.Optional[t.List[str]] = None,
            dockerfile_commands: t.Optional[t.List[str]] = None,
            base_image: t.Optional[str] = None,
        ):
            kwargs = {key: value for key, value in locals().items() if key != "maybe_cls"}

            def wrap(cls):
                if not hasattr(cls, "train"):
                    raise exceptions.TungstenModelError(
                        f"'train' method not found in class '{type_utils.get_qualname(cls)}'"
                    )
                cls_builder = _ClassBuilder(cls=cls, **kwargs)
                wrapped = cls_builder.build_class()
                return wrapped

            # ``maybe_cls`` will be a class if it is used as ``@define``
            # but ``None`` if used as ``@define()``.
            if maybe_cls is None:
                return wrap
            else:
                return wrap(maybe_cls)

        self._set_method(derivate)

    def _set_method(self, method: t.Callable):
        setattr(self._cls, method.__name__, self._add_method_dunders(method))

    def _add_method_dunders(self, method):
        """
        Add __module__ and __qualname__ to a method if possible.
        """
        try:
            method.__module__ = self._cls.__module__
        except AttributeError:
            pass

        try:
            method.__qualname__ = ".".join((self._cls.__qualname__, method.__name__))
        except AttributeError:
            pass

        try:
            method.__doc__ = (
                "Method generated by tungstenkit for class " f"{self._cls.__qualname__}."
            )
        except AttributeError:
            pass

        return method


def _validate_setup_def(setup_method: t.Callable):
    _validate_num_args(setup_method, ["self"])


def _validate_predict_def(predict_method: t.Callable):
    _validate_num_args(predict_method, ["self", "inputs"])


def _validate_predict_demo_def(predict_demo_method: t.Callable):
    _validate_num_args(predict_demo_method, ["self", "inputs"])


def _validate_train_def(train_method: t.Callable):
    _validate_num_args(train_method, ["self"])


def _validate_define_input_def(define_input_method: t.Callable):
    _validate_num_args(define_input_method, ["self"])


def _validate_define_output_def(define_output_method: t.Callable):
    _validate_num_args(define_output_method, ["self"])


def _validate_num_args(fn: t.Callable, arg_names: t.List[str]):
    args = inspect.getfullargspec(fn).args
    desired_num_args = len(arg_names)
    fn_name = type_utils.get_qualname(fn)
    err_msg_suffix = f"It should have {desired_num_args} arguments: {', '.join(arg_names)}."
    if len(args) > desired_num_args:
        raise exceptions.TungstenModelError(f"Too many args for '{fn_name}'. {err_msg_suffix}")
    elif len(args) < desired_num_args:
        raise exceptions.TungstenModelError(f"Too few args for '{fn_name}'. {err_msg_suffix}")


# if __name__ == "__main__":

#     class Input(BaseIO):
#         pass

#     class Output(BaseIO):
#         pass

#     @define(input=Input, output=Output)
#     class A:
#         def some(self):
#             pass

#     a = A()

#     a.train()  # mypy error

#     @A.derivate
#     class B:
#         pass
