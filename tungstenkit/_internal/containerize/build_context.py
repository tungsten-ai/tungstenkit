import os
import shutil
import subprocess
import time
import typing as t
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import attrs
from filelock import FileLock
from pathspec import PathSpec
from rich.progress import Progress, TextColumn

from tungstenkit import exceptions
from tungstenkit._internal import constants
from tungstenkit._internal.configs import BuildConfig
from tungstenkit._internal.logging import log_debug, log_info
from tungstenkit._internal.utils.context import hide_traceback
from tungstenkit._internal.utils.file import (
    format_file_size,
    get_tree_size_in_bytes,
    is_relative_to,
)

from .dockerfile_generators import BaseDockerfileGenerator, create_dockerfile_generator


def is_abs_path(instance, attribute, value: Path):
    return value.is_absolute()


@attrs.define
class BuildContext:
    # {build_dir}
    # ├─ .tungsten-build
    # │   ├─ Dockerfile
    # │   ├─ requirements.txt
    # │   ├─ small_files
    # │   │  └─ ...
    # │   └─ files_outside_build_dir
    # │      └─ {files added by --copy-files option}
    # ├─ {tungsten_module} (e.g. tungsten_model.py)
    # └─ ...

    build_config: BuildConfig = attrs.field(validator=[attrs.validators.instance_of(BuildConfig)])
    abs_path_to_build_dir: Path = attrs.field(
        validator=[attrs.validators.instance_of(Path), is_abs_path]
    )
    abs_path_to_tungsten_module: Path = attrs.field(
        validator=[attrs.validators.instance_of(Path), is_abs_path]
    )
    _dockerfile_generator: BaseDockerfileGenerator = attrs.field(init=False)

    # To handle race condition of .tungsten-build dir
    _filelock: FileLock = attrs.field(init=False)

    @property
    def _rel_path_to_tungsten_module(self):
        return self.abs_path_to_tungsten_module.relative_to(self.abs_path_to_build_dir)

    @property
    def _rel_path_to_tmp_dir(self):
        return Path(".tungsten-build")

    @property
    def _rel_path_to_build_filelock(self):
        return self._rel_path_to_tmp_dir.with_name(self._rel_path_to_tmp_dir.name + ".lock")

    @property
    def _rel_path_to_dockerfile(self):
        return self._rel_path_to_tmp_dir / "Dockerfile"

    @property
    def _rel_path_to_pip_requirements_txt(self):
        return self._rel_path_to_tmp_dir / "requirements.txt"

    @property
    def _rel_path_to_small_files_dir(self):
        return self._rel_path_to_tmp_dir / "small_files"

    @property
    def _rel_path_to_copy_files_dir(self):
        return self._rel_path_to_tmp_dir / "files_outside_build_dir"

    @property
    def _include_spec(self):
        return PathSpec.from_lines("gitwildmatch", self.build_config.include_files)

    @property
    def _exclude_spec(self):
        return PathSpec.from_lines(
            "gitwildmatch",
            self.build_config.exclude_files + [self._rel_path_to_tmp_dir.as_posix()],
        )

    @abs_path_to_tungsten_module.validator
    def _exists_in_build_dir(self, attribute, value: Path):
        try:
            value.relative_to(self.abs_path_to_build_dir)
        except ValueError:
            raise exceptions.BuildError(
                f"Python module '{self.abs_path_to_tungsten_module}' is outside build dir "
                f"at '{self.abs_path_to_build_dir}'"
            )

    def __attrs_post_init__(self):
        log_info(
            f"Add files from '{self.abs_path_to_build_dir.resolve()}' to container"
            f"\n include_files: {self.build_config.include_files}"
            f"\n exclude_files: {self.build_config.exclude_files}\n"
        )

        # Includes the tungsten module
        self.build_config.include_files.append(
            ("/" / self._rel_path_to_tungsten_module).as_posix()
        )

        # Create dockerfile generator
        self._dockerfile_generator = create_dockerfile_generator(self.build_config)

    def __enter__(self):
        # Prepare tmp dir
        abs_path_to_tmp_dir = self.abs_path_to_build_dir / self._rel_path_to_tmp_dir
        abs_path_to_filelock = self.abs_path_to_build_dir / self._rel_path_to_build_filelock
        if abs_path_to_filelock.exists() and FileLock(abs_path_to_filelock).is_locked:
            raise exceptions.BuildError(
                "A build is already in progress. Restart after the build in progress is complete."
            )
        if abs_path_to_tmp_dir.exists():
            shutil.rmtree(abs_path_to_tmp_dir)

        abs_path_to_tmp_dir.mkdir()

        # Acaquire filelock
        self._filelock = FileLock(abs_path_to_filelock)
        self._filelock.acquire()

        with ThreadPoolExecutor(max_workers=8) as executor:
            future_list: t.List[Future] = []

            # Copy files
            self._copy_small_files_to_tmp_dir(executor=executor, future_list=future_list)
            self._copy_files_outside_build_dir_to_tmp_dir(
                executor=executor,
                future_list=future_list,
            )
            self._show_progress_while_writing_files(
                future_list=future_list,
            )

            # Generate Dockerfile
            dockerfile = self._dockerfile_generator.generate(
                abs_path_to_build_dir=self.abs_path_to_build_dir,
                rel_path_to_pip_requirements_txt=self._rel_path_to_pip_requirements_txt,
                rel_paths_to_large_files=[
                    p.relative_to(self.abs_path_to_build_dir) for p in self._traverse_large_files()
                ],
                rel_path_to_smal_files_base_dir=self._rel_path_to_small_files_dir,
            )
            (self.abs_path_to_build_dir / self._rel_path_to_dockerfile).write_text(dockerfile)
            log_debug(
                "Dockerfile:\n"
                + "\n".join(["  " + line for line in dockerfile.strip().split("\n") if line]),
                pretty=False,
            )

        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._filelock.release()
        shutil.rmtree(self.abs_path_to_build_dir / self._rel_path_to_tmp_dir)

    def build(self, tag: str) -> None:
        subprocess_args = [
            "docker",
            "build",
            "--cache-to=type=inline",
            f"--tag={tag}",
            "--file=" + str(self._rel_path_to_dockerfile),
            "--output=type=docker,push=false",
        ]
        subprocess_args.append(str(self.abs_path_to_build_dir))
        log_debug(msg="$ " + " ".join(subprocess_args), pretty=False)
        res = subprocess.run(subprocess_args, check=False)

        if res.returncode != 0:
            with hide_traceback():
                raise exceptions.BuildError(
                    f"Failed to build {tag}. For the reason, refer to above build logs."
                )

    def _copy_small_files_to_tmp_dir(
        self, executor: ThreadPoolExecutor, future_list: t.List[Future]
    ) -> None:
        for p_src_abs in self._traverse_small_files():
            p_src_rel = p_src_abs.relative_to(self.abs_path_to_build_dir)
            p_src_rel_posix = p_src_rel.as_posix()

            p_dest = self.abs_path_to_build_dir / self._rel_path_to_small_files_dir / p_src_rel

            # Symlink with abs path & outside build dir -> append to copy_files
            # Symlink with abs path & inside build dir -> create symlink with rel path
            if p_src_abs.is_symlink():
                p_link_src = Path(os.readlink(str(p_src_abs)))
                if p_link_src.is_absolute():
                    if is_relative_to(p_link_src, start=self.abs_path_to_build_dir):
                        p_dest.parent.mkdir(exist_ok=True, parents=True)
                        os.symlink(
                            _convert_abs_link_src_to_rel(p_link_src, p_src_abs),
                            self.abs_path_to_build_dir
                            / self._rel_path_to_small_files_dir
                            / p_src_rel,
                        )
                    else:
                        self.build_config.copy_files.append(
                            (str(p_link_src.resolve()), p_src_rel_posix)
                        )
                    continue

            # Supports only regular files and symlinks
            if not p_src_abs.is_symlink() and not p_src_abs.is_file():
                raise exceptions.BuildError(f"Not file or symlink: {p_src_rel}")

            # Regular file or symlink with rel path -> copy to tmp dir
            p_dest.parent.mkdir(exist_ok=True, parents=True)
            future_list.append(
                executor.submit(
                    shutil.copy,
                    str(p_src_abs),
                    p_dest,
                    follow_symlinks=False,
                )
            )

    def _copy_files_outside_build_dir_to_tmp_dir(
        self,
        executor: ThreadPoolExecutor,
        future_list: t.List[Future],
    ):
        """Create tmp files for `build_config.copy_files` and update `build_config.copy_files`"""
        if len(self.build_config.copy_files) > 0:
            log_info("Copy extra files to container")

        p_dest_rel_and_p_container_pairs: t.List[t.Tuple[str, str]] = []
        for p_src_str, p_container_str in self.build_config.copy_files:
            p_src = Path(p_src_str)
            p_src_abs = p_src if p_src.is_absolute() else self.abs_path_to_build_dir / p_src

            # Check existence
            if not p_src_abs.is_symlink() and not p_src_abs.exists():
                raise exceptions.BuildError(
                    f"Failed to copy '{p_src_str}' to '{p_container_str}'. "
                    f"'{p_src_str}' does not exist."
                )

            # Check existence of symlink target and resolve
            if p_src_abs.is_symlink():
                p_src_link_target = p_src_abs.resolve()
                if not p_src_link_target.exists():
                    raise exceptions.BuildError(
                        f"Failed to copy '{p_src_str}' to '{p_container_str}'. "
                        f"Target '{p_src_link_target}' of symlink '{p_src_str}' does not exist."
                    )
                p_src = p_src_abs = p_src_link_target

            # Copy to tmp dir.
            log_info(f" '{p_src_str}' (host) -> '{p_container_str}' (container)")
            p_dest_abs = (
                self.abs_path_to_build_dir
                / self._rel_path_to_copy_files_dir
                / uuid4().hex
                / p_src_abs.name
            )
            p_dest_abs.parent.mkdir(parents=True, exist_ok=True)
            if p_src_abs.is_file():
                future_list.append(
                    executor.submit(
                        shutil.copy,
                        str(p_src_abs),
                        str(p_dest_abs),
                        follow_symlinks=False,
                    )
                )
            elif p_src_abs.is_dir():
                p_dest_abs.mkdir()
                for element in p_src_abs.iterdir():
                    if element.is_dir():
                        future_list.append(
                            executor.submit(
                                shutil.copytree,
                                str(element),
                                str(p_dest_abs / element.name),
                                symlinks=False,
                                ignore_dangling_symlinks=True,
                            )
                        )
                    else:
                        future_list.append(
                            executor.submit(
                                shutil.copy,
                                str(element),
                                str(p_dest_abs / Path(element).name),
                            )
                        )
            else:
                raise exceptions.BuildError(
                    f"'{p_src_str}' is not regular file, symlink, or directory"
                )

            p_dest_rel_and_p_container_pairs.append(
                (
                    p_dest_abs.relative_to(self.abs_path_to_build_dir).as_posix(),
                    p_container_str,
                )
            )

        log_info("")
        self.build_config.copy_files = p_dest_rel_and_p_container_pairs

    def _show_progress_while_writing_files(self, future_list: t.List[Future]):
        if not future_list:
            return

        progress = Progress(TextColumn("{task.description}"))
        large_files_size = sum([p.stat().st_size for p in self._traverse_large_files()])
        desc_prefix = "Build context size: "
        task = progress.add_task(desc_prefix + f"{large_files_size}B")

        def update_progress():
            size_in_bytes = (
                get_tree_size_in_bytes(
                    root_dir=self.abs_path_to_build_dir / self._rel_path_to_small_files_dir
                )
                + get_tree_size_in_bytes(
                    root_dir=self.abs_path_to_build_dir / self._rel_path_to_copy_files_dir
                )
                + large_files_size
            )
            human_readable_size = format_file_size(size_in_bytes)
            progress.update(task, description=desc_prefix + human_readable_size)

        with progress:
            while not all(fut.done() for fut in future_list):
                update_progress()
                time.sleep(0.1)

            update_progress()

        log_info("")

    def _traverse_files(
        self, cond: t.Optional[t.Callable[[Path], bool]] = None
    ) -> t.Generator[Path, t.Any, None]:
        for p_abs in list(self.abs_path_to_build_dir.rglob("*")):
            if p_abs.is_dir():
                continue

            p_rel = p_abs.relative_to(self.abs_path_to_build_dir)
            p_rel_posix = p_rel.as_posix()
            if (
                not self._include_spec.match_file(p_rel_posix)
                or self._exclude_spec.match_file(p_rel_posix)
                or (cond and not cond(p_abs))
            ):
                continue

            yield p_abs

    def _traverse_small_files(self) -> t.Generator[Path, t.Any, None]:
        return self._traverse_files(
            lambda p: p.stat(follow_symlinks=False).st_size
            < constants.MIN_LARGE_FILE_SIZE_ON_BUILD
        )

    def _traverse_large_files(self) -> t.Generator[Path, t.Any, None]:
        return self._traverse_files(
            lambda p: p.stat(follow_symlinks=False).st_size
            >= constants.MIN_LARGE_FILE_SIZE_ON_BUILD
        )


def _convert_abs_link_src_to_rel(abs_path_to_link_src: Path, abs_path_to_link: Path) -> Path:
    for parent in abs_path_to_link.parents:
        if is_relative_to(abs_path_to_link_src, start=parent):
            common_prefix = parent
            break

    pd_count = (
        len(abs_path_to_link.relative_to(common_prefix).parts) - len(common_prefix.parts) - 1
    )
    return Path(*([".."] * pd_count + list(abs_path_to_link_src.relative_to(common_prefix).parts)))
