import typing as t

import pydantic

from tungstenkit import exceptions
from tungstenkit._internal.configs import BuildConfig
from tungstenkit._internal.io import BaseIO

InputType = t.TypeVar("InputType", bound=BaseIO)
OutputType = t.TypeVar("OutputType", bound=BaseIO)

EvalType = t.Callable[[t.Iterable[OutputType], t.Iterable[OutputType]], float]
TestCaseType = t.Callable[[InputType], InputType]


class Visualize:
    pass


# def _validate_io(instance: object, attribute: attrs.Attribute, value: t.Any):
#     if not issubclass(value, BaseIO):
#         raise exceptions.TungstenTaskError(
#             f"'{attribute.name}' should be a subclass of 'tungsten.BaseIO'"
#         )


class Eval(pydantic.BaseModel):
    module: str
    fn: str
    lower_is_better: bool


class TestCase(pydantic.BaseModel):
    module: str
    fn: str


# TODO docstrings
# @attrs.define(slots=False)
class TungstenTask(t.Generic[InputType, OutputType]):
    """
    Docstring
    """

    _input_type: t.Type[InputType]
    _output_type: t.Type[OutputType]
    _visualizer: t.Optional[Visualize]
    _evals: t.Dict[str, Eval]
    _test_cases: t.Dict[str, TestCase]
    _build_config: BuildConfig

    def __init__(
        self: "TungstenTask[InputType, OutputType]",
        input: t.Type[InputType],
        output: t.Type[OutputType],
        visualize: t.Optional[Visualize] = None,
        *,
        pip_packages: t.Optional[t.List[str]] = None,
        system_packages: t.Optional[t.List[str]] = None,
        shell_commands: t.Optional[t.List[str]] = None,
        include_files: t.Optional[t.List[str]] = None,
        exclude_files: t.Optional[t.List[str]] = None,
        python_version: t.Optional[str] = None,
        cuda_version: t.Optional[str] = None,
        base_image: t.Optional[str] = None,
    ):
        r"""Returns a class decorator that sets the model configuration.

        The base docker image, maybe a cuda image, and the python version can be inferred
        for following pip packages:

        ``torch``, ``torchvision``, ``torchaudio``, and ``tensorflow``.

        While inferring, the runtime python version is preferred.

        :param pip_packages: a list of pip requirements in ``<name>[==<version>]`` format.
            If ``None`` (default), no pip packages are added.

        :param system_packages: a list of system packages, which are installed
            by the system package manager (e.g. ``apt``).

            This argument will be ignored while using a custom base image in which
            the system package manager may not be available.

        :param shell_commands: a list of shell commands.

            Each command will be added to the ``dockerfile`` as the argument of a ``RUN`` command.

        :param include_files: a list of patterns as in ``.gitignore``.

            The file where this decorator is used and files passed in any other argument
            (e.g. ``readme_md`` and ``example_inputs``) are automatically included while building
            the container. So, explicitly including them is not necessary.

            If ``None`` (default), all python files in the working directory and its subdirectories
            are added, which is equivalent to ``[*.py]``.

        :param exclude_files: a list of patterns as in ``.gitignore`` for matching which files to
            exclude.

            If ``None`` (default), all hidden files in the working directory are ignored, which is
            equivalent to ``[.*/]``.

        :param python_version: python version to use in ``<major>[.<minor>[.<micro>]]`` format.

            If ``None`` (default), the python version will be automatically determined as
            compatible with pip packages while prefering the runtime python version. Otherwise,
            fix the python version as ``python_version``.

        :param cuda_version: cuda version in ``<major>[.<minor>[.<patch>]]`` format.

            If ``None`` (default), the cuda version will be automatically determined as compatible
            with pip packages. Otherwise, fix the CUDA version as ``cuda_version``.

        :param base_image: base docker image in ``<repository>[:<tag>]`` format.

            If ``None`` (default), the base image is automatically selected with respect to
            pip packages, the device, and the cuda version. Otherwise, the selected base image and
            ``system_packages`` will be ignored and use ``base_image``.
        """
        args = {
            name: value
            for name, value in locals().items()
            if value is not None
            and name not in ["include_files", "exclude_files", "input", "output", "visualize"]
        }
        if include_files is not None:
            args["include_files"] = (
                [include_files] if isinstance(include_files, str) else include_files
            )
        if exclude_files is not None:
            args["exclude_files"] = (
                [exclude_files] if isinstance(exclude_files, str) else exclude_files
            )
        self._build_config = BuildConfig(**args)

        if not issubclass(input, BaseIO):
            raise exceptions.TungstenTaskError(
                "Input type should be a subclass of 'tungsten.BaseIO'"
            )
        if not issubclass(output, BaseIO):
            raise exceptions.TungstenTaskError(
                "Input type should be a subclass of 'tungsten.BaseIO'"
            )

        self._input_type = input
        self._output_type = output
        self._visualizer = visualize
        self._evals = dict()
        self._test_cases = dict()

    # TODO eval fn without gt

    @t.overload
    def eval(
        self,
        _fn: None = None,
        *,
        lower_is_better: bool = False,
        name: t.Optional[str] = None,
    ) -> t.Callable[
        [t.Callable[[t.Iterable[OutputType], t.Iterable[OutputType]], float]],
        t.Callable[[t.Iterable[OutputType], t.Iterable[OutputType]], float],
    ]:
        ...

    @t.overload
    def eval(  # noqa: F811
        self,
        _fn: t.Callable[[t.Iterable[OutputType], t.Iterable[OutputType]], float],
        *,
        lower_is_better: bool = False,
        name: t.Optional[str] = None,
    ) -> t.Callable[[t.Iterable[OutputType], t.Iterable[OutputType]], float]:
        ...

    def eval(  # noqa: F811
        self,
        _fn=None,
        *,
        lower_is_better: bool = False,
        name: t.Optional[str] = None,
    ):
        """
        A decorator that sets an eval function of the task
        """

        def wrapper(
            fn: t.Callable[[t.Iterable[OutputType], t.Iterable[OutputType]], float]
        ) -> t.Callable[[t.Iterable[OutputType], t.Iterable[OutputType]], float]:
            fn_name = name if isinstance(name, str) else fn.__name__
            if fn_name in self._evals.keys():
                raise exceptions.TungstenTaskError(f"Duplicated name of eval functions: {fn_name}")
            self._evals[fn_name] = Eval(
                module=fn.__module__, fn=fn.__name__, lower_is_better=lower_is_better
            )
            return fn

        if _fn is None:
            return wrapper
        return wrapper(_fn)

    # TODO test case with an iteratable of inputs

    @t.overload
    def test_case(
        self,
        _fn: None = None,
        *,
        name: t.Optional[str] = None,
    ) -> t.Callable[[t.Callable[[InputType], InputType]], t.Callable[[InputType], InputType]]:
        ...

    @t.overload
    def test_case(  # noqa: F811
        self,
        _fn: t.Callable[[InputType], InputType],
        *,
        name: t.Optional[str] = None,
    ) -> t.Callable[[InputType], InputType]:
        ...

    def test_case(  # noqa: F811
        self,
        _fn=None,
        *,
        name: t.Optional[str] = None,
    ):
        def wrapper(fn: t.Callable[[InputType], InputType]) -> t.Callable[[InputType], InputType]:
            fn_name = name if isinstance(name, str) else fn.__name__
            if fn_name in self._test_cases.keys():
                raise exceptions.TungstenTaskError(
                    f"Duplicated name of test case functions: {fn_name}"
                )
            self._test_cases[fn_name] = TestCase(module=fn.__module__, fn=fn.__name__)
            return fn

        if _fn is None:
            return wrapper
        return wrapper(_fn)


class MyInput(BaseIO):
    pass


class MyOutput(BaseIO):
    pass


task = TungstenTask(MyInput, MyOutput)


@task.eval
def some_eval(a: t.Iterable[MyOutput], b: t.Iterable[MyOutput]) -> float:
    return 0.0


@task.eval(lower_is_better=True)
def some_eval_2(a: t.Iterable[MyOutput], b: t.Iterable[MyOutput]) -> float:
    return 0.0


@task.eval
def some_eval_3(a: t.Iterable[MyInput], b: t.Iterable[MyOutput]) -> float:
    return 0.0


@task.eval(lower_is_better=True)
def some_eval_4(a: t.Iterable[MyInput], b: t.Iterable[MyOutput]) -> float:
    return 0.0


@task.test_case
def some_test_case(inp: MyInput):
    return inp


@task.test_case(name="some-test")
def some_test_case_2(inp: MyInput):
    return inp


@task.test_case
def some_test_case_3(inp: MyOutput):
    return inp


@task.test_case(name="some-test-2")
def some_test_case_4(inp: MyOutput):
    return inp
