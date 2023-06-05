import os
import sys
import typing as t
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

from tungstenkit._internal.utils.console import print_exception

if t.TYPE_CHECKING:
    from _typeshed import FileDescriptor, StrOrBytesPath, StrPath


class change_workingdir(AbstractContextManager):
    def __init__(self, path: "t.Union[FileDescriptor, StrOrBytesPath]"):
        self.path = path
        self._old_cwd: t.List[str] = []

    def __enter__(self):
        self._old_cwd.append(os.getcwd())
        os.chdir(self.path)

    def __exit__(self, *excinfo):
        if self._old_cwd:
            os.chdir(self._old_cwd.pop())


class change_syspath(AbstractContextManager):
    def __init__(self, path: "StrPath"):
        self.path = str(Path(path).resolve())
        self._old_cwd: t.List[str] = []

    def __enter__(self):
        cwd = os.getcwd()
        self._old_cwd.append(cwd)
        self._change(cwd, self.path)

    def __exit__(self, *excinfo):
        if self._old_cwd:
            self._change(self.path, self._old_cwd.pop())

    @staticmethod
    def _change(src: str, dest: str):
        if src != dest:
            while src in sys.path:
                idx = sys.path.index(src)
                sys.path.remove(src)
                sys.path.insert(idx, dest)


@contextmanager
def hide_traceback():
    def handler(type, value, traceback):
        print_exception(type, value)

    prev_excepthook = sys.excepthook
    try:
        sys.excepthook = handler
        yield
    finally:
        sys.excepthook = prev_excepthook
