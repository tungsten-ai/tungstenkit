import inspect
import typing as t

from typing_extensions import Protocol

from tungstenkit import BaseIO
from tungstenkit._internal.constants import DEFAULT_GPU_MEM_GB
from tungstenkit._internal.io_schema import (
    validate_demo_output_class,
    validate_input_class,
    validate_output_class,
)
from tungstenkit._internal.utils import types as type_utils

DEFINED_MODEL_SET: t.Set[type] = set()


C = t.TypeVar("C", bound=type)


class TungstenModel(Protocol):
    __tungsten_config__: t.Dict[str, t.Any]
    __tungsten_input__: t.Type[BaseIO]
    __tungsten_output__: t.Type[BaseIO]
    __tungsten_demo_output__: t.Type[BaseIO]
    __has_post_build__: bool

    def post_build(self):
        ...

    def setup(self):
        ...

    def predict(self, inputs):
        ...

    def predict_demo(self, inputs):
        ...


@t.overload
def define_model(
    maybe_cls: None = None,
    *,
    input: t.Type[BaseIO],
    output: t.Type[BaseIO],
    demo_output: t.Optional[t.Type[BaseIO]] = None,
    gpu: bool = False,
    python_packages: t.Optional[t.List[str]] = None,
    python_version: t.Optional[str] = None,
    system_packages: t.Optional[t.List[str]] = None,
    cuda_version: t.Optional[str] = None,
    cudnn_version: t.Optional[str] = None,
    force_install_system_cuda: bool = False,
    readme_md: t.Optional[str] = None,
    batch_size: int = 1,
    gpu_mem_gb: float = DEFAULT_GPU_MEM_GB,
    mem_gb: float = 8.0,
    include_files: t.Optional[t.List[str]] = None,
    exclude_files: t.Optional[t.List[str]] = None,
    dockerfile_commands: t.Optional[t.List[str]] = None,
    base_image: t.Optional[str] = None,
) -> t.Callable[[C], t.Type[C]]:
    ...


@t.overload
def define_model(
    maybe_cls: C,
    *,
    input: t.Type[BaseIO],
    output: t.Type[BaseIO],
    demo_output: t.Optional[t.Type[BaseIO]] = None,
    gpu: bool = False,
    python_packages: t.Optional[t.List[str]] = None,
    python_version: t.Optional[str] = None,
    system_packages: t.Optional[t.List[str]] = None,
    cuda_version: t.Optional[str] = None,
    cudnn_version: t.Optional[str] = None,
    force_install_system_cuda: bool = False,
    readme_md: t.Optional[str] = None,
    batch_size: int = 1,
    gpu_mem_gb: float = DEFAULT_GPU_MEM_GB,
    mem_gb: float = 8.0,
    include_files: t.Optional[t.List[str]] = None,
    exclude_files: t.Optional[t.List[str]] = None,
    dockerfile_commands: t.Optional[t.List[str]] = None,
    base_image: t.Optional[str] = None,
) -> t.Type[C]:
    ...


def define_model(
    maybe_cls=None,
    *,
    input: t.Type[BaseIO],
    output: t.Type[BaseIO],
    demo_output: t.Optional[t.Type[BaseIO]] = None,
    gpu: bool = False,
    python_packages: t.Optional[t.List[str]] = None,
    python_version: t.Optional[str] = None,
    system_packages: t.Optional[t.List[str]] = None,
    cuda_version: t.Optional[str] = None,
    cudnn_version: t.Optional[str] = None,
    force_install_system_cuda: bool = False,
    readme_md: t.Optional[str] = None,
    batch_size: int = 1,
    gpu_mem_gb: float = DEFAULT_GPU_MEM_GB,
    mem_gb: float = 8.0,
    include_files: t.Optional[t.List[str]] = None,
    exclude_files: t.Optional[t.List[str]] = None,
    dockerfile_commands: t.Optional[t.List[str]] = None,
    base_image: t.Optional[str] = None,
):
    r"""Returns a class decorator that sets the model configuration.

    The base docker image, maybe a cuda image, and the python version can be inferred
    for following pip packages:

    ``torch``, ``torchvision``, ``torchaudio``, and ``tensorflow``.

    While inferring, the runtime python version is preferred.

    Args:
        input (BaseIO): The input class.

        output (BaseIO): The output class.

        demo_output (BaseIO | None): The demo output class. It is required only when the
            ``predict_demo`` method is defined.

        gpu: Indicates if the model requires GPUs.

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
            python packages, the gpu flag, and the CUDA version. Otherwise, use it as the base
            image and ``system_packages`` will be ignored.
    """

    kwargs = {key: value for key, value in locals().items() if key != "maybe_cls"}

    def wrap(cls_):
        cls_builder = _ClassBuilder(cls=cls_, **kwargs)
        wrapped = cls_builder.build_class()
        DEFINED_MODEL_SET.add(wrapped)
        return wrapped

    # ``maybe_cls`` will be a class if it is used as ``@define_model``
    # but ``None`` if used as ``@define_model()``.
    if maybe_cls is None:
        return wrap
    else:
        return wrap(maybe_cls)


class _ClassBuilder:
    """
    Tungsten model class builder.

    A Tungsten model class has:
    - ``__tungsten_config__`` attribute
    - ``__tungsten_input__`` attribute
    - ``__tungsten_output__`` attribute
    - ``__tungsten_demo_output__`` attribute
    - ``__has_post_build__`` attribute
    - ``post_build`` method
    - ``predict`` method
    - ``predict_demo`` method
    - ``setup`` method
    """

    def __init__(
        self,
        cls,
        input: t.Type[BaseIO],
        output: t.Type[BaseIO],
        demo_output: t.Optional[t.Type[BaseIO]] = None,
        **config_kwargs,
    ):
        self._cls: TungstenModel = cls
        self._cls_qualname = type_utils.get_qualname(cls)

        # ``predict`` method is required.
        if not hasattr(cls, "predict"):
            raise TypeError(f"'predict' method not found in class '{self._cls_qualname}'")
        self._has_post_build = hasattr(cls, "post_build")
        self._has_setup = hasattr(cls, "setup")
        self._has_predict_demo = hasattr(cls, "predict_demo")

        # ``predict_demo`` method is required if ``demo_output`` is given.
        if not self._has_predict_demo and demo_output:
            raise TypeError(f"'predict_demo' method not found in class '{self._cls_qualname}'")
        # `demo_output`` should be given if ``predict_demo`` method is defined`.
        if not demo_output and self._has_predict_demo:
            raise ValueError("'predict_demo' method is defined, but 'demo_output' is not set.")

        self._input = input
        self._output = output
        self._demo_output = demo_output if demo_output else output
        self._config = config_kwargs

        # Validate io classes
        validate_input_class(self._input)
        validate_output_class(self._output)
        validate_demo_output_class(self._demo_output)

        # Validate user-defined methods
        _validate_predict_def(getattr(cls, "predict"))
        if self._has_setup:
            _validate_setup_def(getattr(cls, "setup"))
        if self._has_predict_demo:
            _validate_predict_demo_def(getattr(cls, "predict_demo"))

    def build_class(self) -> TungstenModel:
        # Set private variables
        setattr(self._cls, "__tungsten_config__", self._config)
        setattr(self._cls, "__tungsten_input__", self._input)
        setattr(self._cls, "__tungsten_output__", self._output)
        setattr(self._cls, "__tungsten_demo_output__", self._demo_output)
        setattr(self._cls, "__has_post_build__", self._has_post_build)

        # Set methods
        if not self._has_post_build:
            self._set_default_post_build()
        if not self._has_setup:
            self._set_default_setup()
        if not self._has_predict_demo:
            self._set_default_predict_demo()

        return self._cls

    def _set_default_post_build(self):
        @staticmethod
        def post_build():
            pass

        self._set_method(post_build)

    def _set_default_setup(self):
        def setup(self):
            pass

        self._set_method(setup)

    def _set_default_predict_demo(self):
        def predict_demo(self, inputs):
            outputs = self.predict(inputs)
            return outputs, outputs

        self._set_method(predict_demo)

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


def _validate_num_args(fn: t.Callable, arg_names: t.List[str]):
    args = inspect.getfullargspec(fn).args
    desired_num_args = len(arg_names)
    fn_name = type_utils.get_qualname(fn)
    err_msg_suffix = f"It should have {desired_num_args} arguments: {', '.join(arg_names)}."
    if len(args) > desired_num_args:
        raise TypeError(f"Too many args for '{fn_name}'. {err_msg_suffix}")
    elif len(args) < desired_num_args:
        raise TypeError(f"Too few args for '{fn_name}'. {err_msg_suffix}")
