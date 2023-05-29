import abc
import inspect
import typing as t

from tungstenkit import exceptions
from tungstenkit._internal import io
from tungstenkit._internal.io_schema import validate_input_class, validate_output_class
from tungstenkit._internal.utils import types as type_utils

InputType = t.TypeVar("InputType", bound=io.BaseIO)
OutputType = t.TypeVar("OutputType", bound=io.BaseIO)
M = t.TypeVar("M", bound="TungstenModel")

DEFINED_MODEL_SET: "t.Set[t.Type[TungstenModel]]" = set()


class _ModelMeta(abc.ABCMeta):
    def __new__(*args, **argv):
        cls = abc.ABCMeta.__new__(*args, **argv)
        return cls

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)

        # Validate only when cls is a strict subclass of TungstenModel.
        # The TungstenModel class cannot be instantiated itself since it is a abstract class.
        mro = inspect.getmro(cls)  # (..., TungstenModel, Generic, object)
        if len(mro) <= 3:
            return

        type_args = type_utils.get_superclass_type_args(cls, TungstenModel)

        check_if_input_determined(cls, type_args)
        check_if_output_determined(cls, type_args)

        num_type_args = len(type_args)
        setattr(cls, "__tungsten_config__", dict())
        if num_type_args > 0:
            validate_input_class(type_args[0])
            setattr(cls, "__tungsten_input__", type_args[0])
        if num_type_args > 1:
            validate_output_class(type_args[1])
            setattr(cls, "__tungsten_output__", type_args[1])

        validate_setup(cls)
        validate_predict(cls)
        validate_predict_demo(cls)
        validate_define_input(cls)
        validate_define_output(cls)

        DEFINED_MODEL_SET.add(cls)


class TungstenModel(t.Generic[InputType, OutputType], metaclass=_ModelMeta):
    """
    Base class for all Tungsten models.

    Your models should also subclass this class.

    This class should take two classes as type arguments,
    which define input and output types respectively.

    ```python
    from typing import List
    from tungstenkit import BaseIO, TungstenModel

    class Input(BaseIO):
        # Define your input fields
        pass

    class Output(BaseIO):
        # Define your output fields
        pass

    class Model(TungstenModel[Input, Output]):
        def setup(self):
            # Setup your model
            pass

        def predict(self, inputs: List[Input]) -> List[Output]:
            # Run a (batch) prediction
            pass
    ```
    """

    __tungsten_config__: t.Dict[str, t.Any]
    __tungsten_input__: InputType
    __tungsten_output__: OutputType

    # __model_config: t.Optional[ModelConfig] = None
    # _type_args: t.Tuple[InputType, OutputType]

    def setup(self) -> t.Any:
        pass

    @abc.abstractmethod
    def predict(self, inputs: t.List[InputType]) -> t.Sequence[OutputType]:
        pass

    def predict_demo(
        self, inputs: t.List[InputType]
    ) -> t.Tuple[t.Sequence[OutputType], t.Sequence[t.Union[t.Dict[str, t.Any], io.BaseIO]]]:
        outputs = self.predict(inputs)
        return outputs, outputs

    def define_input(self):
        return self.__tungsten_input__

    def define_output(self):
        return self.__tungsten_output__


# TODO Support TPU
# TODO Support multi-platform builds


def model_config(
    *,
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
) -> t.Callable[[t.Type[M]], t.Type[M]]:
    r"""Returns a class decorator that sets the model configuration.

    The base docker image, maybe a cuda image, and the python version can be inferred
    for following pip packages:

    ``torch``, ``torchvision``, ``torchaudio``, and ``tensorflow``.

    While inferring, the runtime python version is preferred.

    Args:
        gpu: Indicates if the model requires GPUs.

        description (str | None): A text explaining the model.

        python_packages (list[str] | None): A list of pip requirements in ``<name>[==<version>]``
            format. If ``None`` (default), no python packages are added.

        python_version (str | None): Python version to use in ``<major>[.<minor>[.<micro>]]``
            format.
            If ``None`` (default), the python version will be automatically determined
            as compatible with pip packages while prefering the runtime python version.
            Otherwise, fix the python version as ``python_version``.

        system_packages (list[str] | None): A list of system packages, which are installed
            by the system package manager (e.g. ``apt``). This argument will be ignored while
            using a custom base image with which tungstenkit cannot decide which package manager to
            use.

        cuda_version (str | None): CUDA version in ``<major>[.<minor>[.<patch>]]`` format.
            If ``None`` (default), the cuda version will be automatically determined as compatible
            with pip packages. Otherwise, fix the CUDA version as ``cuda_version``. Raises
            ValueError if ``gpu`` is ``False`` but ``cuda_version`` is not None.

        readme_md (str | None): Path to the ``README.md`` file.

        batch_size (int): Max batch size for adaptive batching.

        gpu_mem_gb (int): Minimum GPU memory size required to run the model. This argument will be
            ignored if ``gpu==False``.

        mem_gb (int): Minimum memory size required to run the model.

        include_files (list[str] | None): A list of patterns as in ``.gitignore``.
            If ``None`` (default), all files in the working directory and its subdirectories
            are added, which is equivalent to ``[*]``.

        exclude_files (list[str] | None): A list of patterns as in ``.gitignore`` for matching
            which files to exclude.
            If ``None`` (default), all hidden files and Python bytecodes are ignored,
            which is equivalent to ``[".*/", "__pycache__/", "*.pyc", "*.pyo", "*.pyd"]``.

        dockerfile_commands (list[str] | None): A list of dockerfile commands. The commands will
            be executed *before* setting up python packages.

        base_image (str | None): Base docker image in ``<repository>[:<tag>]`` format.
            If ``None`` (default), the base image is automatically selected with respect to
            pip packages, the gpu flag, and the CUDA version. Otherwise, use it as the base image
            and ``system_packages`` will be ignored.
    """
    args = {name: value for name, value in locals().items() if value is not None}

    def wrap(cls: t.Type[M]) -> t.Type[M]:
        for key, value in args.items():
            cls.__tungsten_config__[key] = value
        return cls

    return wrap


def _validate_num_args(fn: t.Callable, arg_names: t.List[str]):
    args = inspect.getfullargspec(fn).args
    desired_num_args = len(arg_names)
    fn_name = type_utils.get_qualname(fn)
    err_msg_suffix = f"It should have {desired_num_args} arguments: {', '.join(arg_names)}."
    if len(args) > desired_num_args:
        raise exceptions.TungstenModelError(f"Too many args for '{fn_name}'. {err_msg_suffix}")
    elif len(args) < desired_num_args:
        raise exceptions.TungstenModelError(f"Too few args for '{fn_name}'. {err_msg_suffix}")


def validate_setup(cls: t.Type[TungstenModel]):
    _validate_num_args(cls.setup, ["self"])


def validate_predict(cls: t.Type[TungstenModel]):
    _validate_num_args(cls.predict, ["self", "inputs"])


def validate_predict_demo(cls: t.Type[TungstenModel]):
    _validate_num_args(cls.predict_demo, ["self", "inputs"])


def validate_define_input(cls: t.Type[TungstenModel]):
    _validate_num_args(cls.define_input, ["self"])


def validate_define_output(cls: t.Type[TungstenModel]):
    _validate_num_args(cls.define_output, ["self"])


def check_if_input_determined(
    cls: t.Type[TungstenModel],
    type_args: t.Tuple[type, ...],
):
    # Input class is not given. ``define_input`` should be overriden.
    if len(type_args) < 1:
        if cls.define_input == TungstenModel.define_input:
            raise exceptions.TungstenModelError(
                f"Type argument of {type_utils.get_qualname(TungstenModel)} is not given, "
                f"but 'define_input' method is not overriden "
                f"in class '{type_utils.get_qualname(cls)}'."
            )


def check_if_output_determined(
    cls: t.Type[TungstenModel],
    type_args: t.Tuple[type, ...],
):
    # Output class is not given. ``define_output`` should be overriden.
    if len(type_args) < 2:
        if cls.define_output == TungstenModel.define_output:
            raise exceptions.TungstenModelError(
                f"Type argument of {type_utils.get_qualname(TungstenModel)} is not given, "
                f"but 'define_input' method is not overriden "
                f"in class '{type_utils.get_qualname(cls)}'."
            )
