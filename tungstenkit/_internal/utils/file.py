import os
import shutil
import tempfile
import typing as t
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path, PurePath

from pathspec import PathSpec

if t.TYPE_CHECKING:
    from _typeshed import StrPath


def format_file_size(size_in_bytes: int, suffix="B"):
    num = float(size_in_bytes)
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"


def list_files(dir: Path) -> t.List[Path]:
    return [p for p in dir.iterdir() if p.is_file()]


def list_dirs(dir: Path) -> t.List[Path]:
    return [p for p in dir.iterdir() if p.is_dir()]


def convert_to_unique_path(path: Path) -> Path:
    parent = path.parent
    file_name = path.name
    ret_path = path
    while ret_path.exists():
        splitted_by_dot = file_name.split(".")
        splitted_by_dash = file_name.split("-")
        if len(splitted_by_dot) > 2 and splitted_by_dot[-2].isdigit():
            splitted_by_dot[-2] = str(int(splitted_by_dot[-2]) + 1)
            ret_path = parent / ".".join(splitted_by_dot)
        elif len(splitted_by_dot) > 1:
            splitted_by_dot[-1] = f"1.{splitted_by_dot[-1]}"
            ret_path = parent / ".".join(splitted_by_dot)
        elif len(splitted_by_dash) > 1 and splitted_by_dash[-1].isdigit():
            splitted_by_dash[-1] = str(int(splitted_by_dash[-1]) + 1)
            ret_path = parent / "-".join(splitted_by_dash)
        else:
            ret_path = Path(str(ret_path) + "-1")
        file_name = ret_path.name
    return ret_path


def get_tree_size_in_bytes(root_dir: Path, ignore_patterns: t.Optional[t.List[str]] = None) -> int:
    ignore_spec = PathSpec.from_lines("gitwildmatch", ignore_patterns) if ignore_patterns else None
    return sum(
        (f.stat().st_size if f.is_file() else f.lstat().st_size)
        for f in root_dir.glob("**/*")
        if (f.is_symlink() or f.is_file())
        and (ignore_spec is None or not ignore_spec.match_file(f.as_posix()))
    )


def is_relative_to(path: PurePath, start: "StrPath"):
    try:
        path.relative_to(start)
        return True
    except ValueError:
        return False


def write_safely(path: Path, content: t.Union[str, bytes]) -> None:
    """
    Write to a temporary file and replace
    """
    directory = path.parent
    fd, tmp_path_str = tempfile.mkstemp(prefix=".tungsten-", suffix=path.name, dir=directory)
    try:
        tmp_path = Path(tmp_path_str)
        if isinstance(content, str):
            tmp_path.write_text(content)
        else:
            tmp_path.write_bytes(content)
        os.close(fd)
        os.replace(tmp_path, path)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        tmp_paths = [
            directory / p for p in directory.glob(".tungsten-*" + path.name) if p.name != path.name
        ]
        for tmp_path in tmp_paths:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass


def copy_multiple_files(files: t.List[Path], directory: Path) -> t.List[Path]:
    if len(files) == 0:
        return []

    ret: t.List[Path] = []
    fut_list: t.List[Future] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for src in files:
            dest = directory / src.name
            dest = convert_to_unique_path(dest)
            fut_list.append(executor.submit(shutil.copy, str(src.resolve()), str(dest.resolve())))
        for fut in fut_list:
            ret.append(Path(fut.result()))

    return ret
