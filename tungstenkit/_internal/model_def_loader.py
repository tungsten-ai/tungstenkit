import abc
import importlib
import os
import typing as t
from pathlib import Path, PurePath

import attrs
import dill
import pydantic

from tungstenkit import exceptions
from tungstenkit._internal import io
from tungstenkit._internal.configs import ModelConfig
from tungstenkit._internal.constants import DEFAULT_MODEL_MODULE, TUNGSTEN_DIR_IN_CONTAINER
from tungstenkit._internal.model_def import DEFINED_MODEL_SET, TungstenModel
from tungstenkit._internal.utils.imports import check_module, import_module_in_lazy_import_ctx
from tungstenkit._internal.utils.types import get_qualname

if t.TYPE_CHECKING:
    from types import ModuleType

MODEL_BINARY_PATH = Path(
    os.getenv("TUNGSTEN_MODEL_BINARY_PATH", TUNGSTEN_DIR_IN_CONTAINER / ".tungsten-model")
)


@attrs.define(kw_only=True, init=False)
class ModelDefLoader(abc.ABC):
    _cls: t.Type[TungstenModel] = attrs.field(init=False)
    _obj: t.Optional[t.Any] = attrs.field(default=None, init=False)

    def __attrs_post_init__(self):
        self._load()
        assert hasattr(self, "_cls")

    @property
    def model_class(self) -> t.Type[TungstenModel]:
        return self._cls

    @property
    def model(self) -> TungstenModel:
        if self._obj is None:
            self._obj = self.model_class()
        return self._obj

    @property
    def input_class(self) -> t.Type[io.BaseIO]:
        return self.model.__tungsten_input__

    @property
    def output_class(self) -> t.Type[io.BaseIO]:
        return self.model.__tungsten_output__

    @property
    def demo_output_class(self) -> t.Type[io.BaseIO]:
        return self.model.__tungsten_demo_output__

    @property
    def config(self) -> ModelConfig:
        try:
            config_dict = {
                k: v for k, v in self.model_class.__tungsten_config__.items() if v is not None
            }
            c = ModelConfig.with_types(
                input_cls=self.input_class,
                output_cls=self.output_class,
                demo_output_cls=self.demo_output_class,
            )(**config_dict)
        except pydantic.ValidationError as e:
            raise exceptions.ModelConfigError(
                str(e).replace(
                    f"for {ModelConfig.__name__}",
                    f"in '{get_qualname(self._cls)}'",
                    1,
                )
            )

        c.tungsten_environment_variables["TUNGSTEN_MODEL_MODULE"] = self.model_class.__module__
        c.tungsten_environment_variables["TUNGSTEN_MODEL_CLASS"] = self.model_class.__name__
        return c

    @abc.abstractmethod
    def _load(self):
        pass


@attrs.define(kw_only=True)
class ModelModuleLoader(ModelDefLoader):
    module_ref: str
    class_name: t.Optional[str] = None
    lazy_import: bool = False

    def _load(self) -> None:
        if not check_module(self.module_ref):
            raise exceptions.TungstenModelError(f"Module not found: {self.module_ref}")
        tungsten_model_module = _import_module(self.module_ref, self.lazy_import)

        if self.class_name is None:
            cls = _find_model_class(self.module_ref)
        else:
            if not hasattr(tungsten_model_module, self.class_name):
                raise exceptions.TungstenModelError(
                    f"Class '{self.class_name}' is not defined in module '{self.module_ref}'"
                )
            cls = getattr(tungsten_model_module, self.class_name)

        self._cls = cls


@attrs.define(kw_only=True)
class ModelBinaryLoader(ModelDefLoader):
    path: PurePath

    def _load(self) -> None:
        with open(self.path, "rb") as f:
            obj = dill.load(f)

        self._cls = obj.__class__
        self._obj = obj


def create_model_def_loader(
    module_ref: t.Optional[str] = None,
    class_name: t.Optional[str] = None,
    lazy_import: bool = False,
) -> ModelDefLoader:
    if MODEL_BINARY_PATH.exists():
        return ModelBinaryLoader(path=MODEL_BINARY_PATH)
    module_ref = module_ref if module_ref else DEFAULT_MODEL_MODULE
    return ModelModuleLoader(module_ref=module_ref, class_name=class_name, lazy_import=lazy_import)


def _find_model_class(module_ref: str) -> type:
    if len(DEFINED_MODEL_SET) > 1:
        raise exceptions.TungstenModelError(
            f"Multiple models are defined while loading '{module_ref}'. "
            "Please set the '--class-name' option to resolve the ambiguity."
        )
    if len(DEFINED_MODEL_SET) == 0:
        raise exceptions.TungstenModelError(f"No defined model in {module_ref}")

    cls = DEFINED_MODEL_SET.pop()
    return cls


def _import_module(module_ref: str, lazy_import: bool) -> "ModuleType":
    if lazy_import:
        help_msg_on_lazy_import_err = (
            "Please don't execute modules that specific models depend on, "
            "either globally or within IO definitions. "
        )
        tungsten_model_module = import_module_in_lazy_import_ctx(
            module_ref,
            help_msg_on_lazy_import_err,
        )
    else:
        tungsten_model_module = importlib.import_module(module_ref)
    return tungsten_model_module
