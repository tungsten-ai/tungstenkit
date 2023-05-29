import ast
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
import types
from collections import namedtuple
from contextlib import contextmanager
from types import ModuleType
from typing import Dict, List, Optional, Set

Import = namedtuple("Import", ["module", "name", "alias"])


def _raise_module_not_found(exc_msg):
    exc = ModuleNotFoundError(exc_msg)
    try:
        raise exc

    # Re-raise after manipulating traceback
    except ModuleNotFoundError:
        tb = sys.exc_info()[2]
        back_frame = tb.tb_frame.f_back.f_back

    back_tb = types.TracebackType(
        tb_next=None,
        tb_frame=back_frame,
        tb_lasti=back_frame.f_lasti,
        tb_lineno=back_frame.f_lineno,
    )
    raise exc.with_traceback(back_tb)


class UnknownModuleObject(object):
    """
    An object loaded from dummy module by import-from statement.

    Raises an error if it is called or an attr is accessed.
    """

    def __init__(
        self,
        exc_msg: str,
    ) -> None:
        self.__exc_msg = exc_msg

    # TODO set this for all magic methods
    def __call__(self, *args, **kwds):
        _raise_module_not_found(self.__exc_msg)

    def __getattr__(self, name):
        _raise_module_not_found(self.__exc_msg)


class UnknownModule(ModuleType):
    """
    A lazily imported, but not found module
    """

    def __init__(self, name: str, help_msg_on_err: Optional[str] = None) -> None:
        super().__init__(name)
        self.__help_msg_on_err = help_msg_on_err
        self.__path__ = []
        self.__attr_names: Set[str] = set()

    def __getattr__(self, name):
        if name in self.__attr_names:
            return UnknownModuleObject(
                exc_msg=self._build_exc_msg(),
            )
        _raise_module_not_found(self._build_exc_msg())

    def _add(self, name):
        self.__attr_names.add(name)

    def _build_exc_msg(self):
        exc_msg = f"Module '{self.__name__}' not found."
        if self.__help_msg_on_err:
            exc_msg += "\n" + self.__help_msg_on_err
        return exc_msg


class UnknownModuleFinder(importlib.abc.MetaPathFinder):
    def __init__(self, loader: "UnknownModuleLazyLoader"):
        self._loader = loader

    def find_spec(self, fullname, path, target=None):
        if self._loader.is_registered(fullname):
            return self._gen_spec(fullname)

    def _gen_spec(self, fullname):
        spec = importlib.machinery.ModuleSpec(fullname, self._loader)
        return spec


class UnknownModuleLazyLoader(importlib.abc.Loader):
    def __init__(self, help_msg_on_err: Optional[str] = None):
        self._help_msg_on_err = help_msg_on_err
        self._registered: Dict[str, UnknownModule] = dict()

    def register(self, fullname: str, module_attr: Optional[str] = None):
        dot_separated = fullname.split(".")
        for i in range(len(dot_separated)):
            name = ".".join(dot_separated[: i + 1])
            if importlib.util.find_spec(name) is None:
                self._registered[name] = UnknownModule(name, self._help_msg_on_err)
        if fullname in self._registered and module_attr:
            self._registered[fullname]._add(module_attr)

    def is_registered(self, fullname: str):
        return fullname in self._registered

    def create_module(self, spec):
        if spec.name in self._registered:
            return self._registered[spec.name]

    def exec_module(self, module):
        pass


def get_imports(path):
    """
    Read all imports in path by 'import' and 'import-from'

    Example:
        example.py:
            from a import b
            from a.b import c
            from d import e as f
            import aa
            import aa.bb
            import aa as bb
            import aa, bb

        >>> get_imports("example.py")
        Import(module=['a'], name=['b'], alias=None)
        Import(module=['a', 'b'], name=['c'], alias=None)
        Import(module=['d'], name=['e'], alias='f')
        Import(module=[], name=['aa'], alias=None)
        Import(module=[], name=['aa', 'bb'], alias=None)
        Import(module=[], name=['aa'], alias='bb')
        Import(module=[], name=['aa'], alias=None)
        Import(module=[], name=['bb'], alias=None)

    """
    with open(path) as fh:
        root = ast.parse(fh.read(), path)

    for node in ast.iter_child_nodes(root):
        if isinstance(node, ast.Import):
            module = []
        elif isinstance(node, ast.ImportFrom):
            module = node.module.split(".")
        else:
            continue

        for n in node.names:
            yield Import(module, n.name.split("."), n.asname)


@contextmanager
def lazy_import_ctx(imports: List[Import], help_msg_on_err: Optional[str] = None):
    loader = UnknownModuleLazyLoader(help_msg_on_err)
    finder = UnknownModuleFinder(loader)
    try:
        sys.meta_path.append(finder)
        for imp in imports:
            if imp.module:
                attr_name = ".".join(imp.name)
                loader.register(".".join(imp.module), attr_name if attr_name else None)
            else:
                loader.register(".".join(imp.name))
        yield
    finally:
        for module_name in loader._registered.keys():
            if module_name in sys.modules:
                del sys.modules[module_name]
        sys.meta_path.remove(finder)


def import_module_in_lazy_import_ctx(
    module: str,
    help_msg_on_unknown_module_exec: Optional[str] = None,
) -> ModuleType:
    # TODO Lazy import existing but not loaded modules
    spec = importlib.util.find_spec(module)
    if spec is None:
        raise ModuleNotFoundError(module)
    if spec.origin is None:
        raise ModuleNotFoundError(
            f"Failed to initialize module '{module}'. Is it a Python module?"
        )
    imports = get_imports(spec.origin)
    with lazy_import_ctx(imports, help_msg_on_unknown_module_exec):
        mod = importlib.import_module(module)
        return mod


def check_module(module: str) -> bool:
    try:
        spec = importlib.util.find_spec(module)
        return spec is not None and spec.origin is not None
    except ModuleNotFoundError:
        return False
