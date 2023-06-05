import os
import shutil
import subprocess
import tempfile
import time
import typing as t
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from uuid import uuid4

import attrs
from pathspec import PathSpec
from rich.progress import Progress, TextColumn

import tungstenkit
from tungstenkit import exceptions
from tungstenkit._internal.configs import BuildConfig
from tungstenkit._internal.logging import log_debug, log_info, log_warning
from tungstenkit._internal.utils.context import change_workingdir, hide_traceback
from tungstenkit._internal.utils.file import (
    format_file_size,
    get_tree_size_in_bytes,
    is_relative_to,
)

from .dockerfiles import BaseDockerfile

TMP_DIR_PREFIX = ".tungsten-build-"


@attrs.frozen(kw_only=True)
class SourceFile:
    abs_path_in_host_fs: Path
    rel_path_in_model_fs: PurePosixPath


@attrs.define
class BuildContext:
    config: BuildConfig
    root_dir: Path
    dockerfile_path: Path

    @property
    def files(self) -> t.Generator[SourceFile, None, None]:
        abs_root_dir = self.root_dir.resolve()
        include_spec = PathSpec.from_lines("gitwildmatch", self.config.include_files)
        exclude_spec = PathSpec.from_lines(
            "gitwildmatch", self.config.exclude_files + [TMP_DIR_PREFIX + "*/"]
        )

        for rel_path_str in include_spec.match_tree(self.root_dir, follow_links=False):
            posix_rel_path_str = Path(rel_path_str).as_posix()
            if not exclude_spec.match_file(posix_rel_path_str):
                yield SourceFile(
                    abs_path_in_host_fs=abs_root_dir / rel_path_str,
                    rel_path_in_model_fs=PurePosixPath(posix_rel_path_str),
                )
        if self.config.copy_files:
            for pathstr_in_host_fs, pathstr_in_model_fs in self.config.copy_files:
                path_in_host_fs = Path(pathstr_in_host_fs)
                if not path_in_host_fs.is_absolute():
                    path_in_host_fs = abs_root_dir / path_in_host_fs

    def build(self, tags: t.List[str]) -> None:
        subprocess_args = [
            "docker",
            "buildx",
            "build",
            "--load",
            "--file=" + str(self.dockerfile_path.relative_to(self.root_dir)),
        ]
        for tag in tags:
            subprocess_args.append(f"--tag={tag}")
        subprocess_args.append(str(self.root_dir))
        log_debug(msg="$ " + " ".join(subprocess_args), pretty=False)
        res = subprocess.run(subprocess_args, check=False)

        if res.returncode != 0:
            with hide_traceback():
                tags_str = ", ".join(tags)
                raise exceptions.BuildError(
                    f"Failed to build {tags_str}. For the reason, refer to above build logs."
                )


@contextmanager
def setup_build_ctx(
    build_config: BuildConfig,
    build_dir: Path,
    module_path: Path,
    dockerfile_generator: BaseDockerfile,
):
    abs_path_to_build_dir = build_dir.resolve()
    module_path = module_path.resolve()
    try:
        rel_path_to_module = module_path.relative_to(abs_path_to_build_dir)
    except ValueError:
        raise exceptions.BuildError(
            f"Python module '{module_path}' is outside build dir at '{abs_path_to_build_dir}'"
        )

    log_info(
        f"Add files from '{build_dir.resolve()}' to container"
        f"\n include_files: {build_config.include_files}"
        f"\n exclude_files: {build_config.exclude_files}\n"
    )
    build_config.include_files.append(("/" / rel_path_to_module).as_posix())
    with change_workingdir(build_dir):
        with tempfile.TemporaryDirectory(prefix=".tungsten-build-", dir=build_dir) as tmp_dir_str:
            with ThreadPoolExecutor(max_workers=8) as executor:
                rel_path_to_tmp_dir = (
                    Path(tmp_dir_str).resolve().relative_to(abs_path_to_build_dir)
                )
                rel_path_to_dockerfile = rel_path_to_tmp_dir / "Dockerfile"
                rel_path_to_dockerignore = rel_path_to_tmp_dir / "Dockerfile.dockerignore"
                rel_path_to_tungstenkit = rel_path_to_tmp_dir / "tungstenkit"
                rel_path_to_tungstenkit.mkdir()
                future_list: t.List[Future] = []

                dockerignore = _generate_dockerignore(
                    build_dir=build_dir,
                    include_patterns=build_config.include_files,
                    exclude_patterns=build_config.exclude_files,
                )
                dockerignore_path = build_dir / rel_path_to_dockerignore
                dockerignore_path.write_text(dockerignore)
                _copy_tungstenkit(
                    build_dir=build_dir,
                    rel_path_to_tungstenkit=rel_path_to_tungstenkit,
                    executor=executor,
                    future_list=future_list,
                )
                build_config.copy_files.extend(
                    _convert_abs_symlinks_to_rel(
                        abs_path_to_build_dir,
                        include_patterns=build_config.include_files,
                        exclude_patterns=build_config.exclude_files,
                        rel_path_to_tmp_dir=rel_path_to_tmp_dir,
                    )
                )
                if build_config.copy_files:
                    build_config.copy_files = _copy_files(
                        abs_path_to_build_dir=abs_path_to_build_dir,
                        rel_path_to_tmp_dir=rel_path_to_tmp_dir,
                        include_with_dest=build_config.copy_files,
                        executor=executor,
                        future_list=future_list,
                    )
                    _show_progress_while_copying_files(
                        copy_dir=rel_path_to_tmp_dir,
                        future_list=future_list,
                        ignore_patterns=["tungstenkit"],
                    )

                dockerfile = dockerfile_generator.generate(
                    tmp_dir_in_build_ctx=rel_path_to_tmp_dir,
                    tungstenkit_dir_in_build_ctx=rel_path_to_tungstenkit,
                )
                dockerfile_path = build_dir / rel_path_to_dockerfile
                dockerfile_path.write_text(dockerfile)
                log_debug(
                    "Dockerfile:\n"
                    + "\n".join(["  " + line for line in dockerfile.strip().split("\n") if line]),
                    pretty=False,
                )
                log_debug(
                    ".dockerignore:\n"
                    + "\n".join(
                        ["  " + line for line in dockerignore.strip().split("\n") if line]
                    ),
                    pretty=False,
                )

                yield BuildContext(
                    config=build_config, root_dir=build_dir, dockerfile_path=dockerfile_path
                )


def _generate_dockerignore(
    build_dir: Path,
    include_patterns: t.List[str],
    exclude_patterns: t.List[str],
) -> str:
    if len(include_patterns) == 0:
        return ""

    # Copy files matched against include_files and not against exclude_files
    dockerignore_lines = []

    base_spec = PathSpec.from_lines("gitwildmatch", ["*"])
    include_spec = PathSpec.from_lines("gitwildmatch", include_patterns)
    exclude_spec = PathSpec.from_lines("gitwildmatch", exclude_patterns)
    for _rel_path_str in base_spec.match_tree(build_dir, follow_links=False):
        rel_path_str = Path(_rel_path_str).as_posix()
        if not include_spec.match_file(rel_path_str) or exclude_spec.match_file(rel_path_str):
            dockerignore_lines.append(rel_path_str)

    return "\n".join(dockerignore_lines) + "\n"


def _convert_abs_symlinks_to_rel(
    abs_path_to_build_dir: Path,
    include_patterns: t.List[str],
    exclude_patterns: t.List[str],
    rel_path_to_tmp_dir: Path,
) -> t.List[t.Tuple[str, str]]:
    link_and_target_pairs: t.List[t.Tuple[str, str]] = []
    include_spec = PathSpec.from_lines("gitwildmatch", include_patterns)
    exclude_spec = PathSpec.from_lines("gitwildmatch", exclude_patterns)
    for link_path in list(abs_path_to_build_dir.rglob("*")):
        if not link_path.is_symlink():
            continue

        pattern = link_path.relative_to(abs_path_to_build_dir).as_posix()
        if include_spec.match_file(pattern) and not exclude_spec.match_file(pattern):
            orig_target = Path(os.readlink(str(link_path)))
            if not orig_target.exists():
                log_warning(f"Target of symbolic link '{link_path}' does not exist")
                continue

            if orig_target.is_absolute():
                try:
                    orig_target.relative_to(abs_path_to_build_dir)
                except ValueError:
                    raise exceptions.BuildError(
                        f"Target '{orig_target}' of link '{link_path}' is outside build dir at "
                        f"'{abs_path_to_build_dir}'"
                    )
                tmp_link_path = (
                    abs_path_to_build_dir
                    / rel_path_to_tmp_dir
                    / "symlinks"
                    / link_path.relative_to(abs_path_to_build_dir)
                )
                new_target = os.path.relpath(orig_target, start=tmp_link_path)
                tmp_link_path.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(new_target, tmp_link_path)
                log_debug(
                    f"Change target of link '{link_path}': '{orig_target}' -> '{new_target}'"
                )
                link_and_target_pairs.append(
                    (
                        str(tmp_link_path),
                        link_path.relative_to(abs_path_to_build_dir).as_posix(),
                    )
                )

    return link_and_target_pairs


def _copy_files(
    abs_path_to_build_dir: Path,
    rel_path_to_tmp_dir: Path,
    include_with_dest: t.List[t.Tuple[str, str]],
    executor: ThreadPoolExecutor,
    future_list: t.List[Future],
) -> t.List[t.Tuple[str, str]]:
    if len(include_with_dest) > 0:
        log_info("Copy extra files to container")

    files_with_dest: t.List[t.Tuple[str, str]] = []
    for src_str, dest_str in include_with_dest:
        src_in_host = Path(src_str)
        src_in_host = (
            src_in_host if src_in_host.is_absolute() else abs_path_to_build_dir / src_in_host
        )
        if not src_in_host.is_symlink() and not src_in_host.exists():
            raise exceptions.BuildError(
                f"Failed to copy '{src_str}' to '{dest_str}'. '{src_str}' does not exist."
            )
        tmp_dir = abs_path_to_build_dir / rel_path_to_tmp_dir
        if is_relative_to(src_in_host, tmp_dir):
            src_in_build_ctx = src_in_host
        else:
            log_info(f" '{src_str}' (host) -> '{dest_str}' (container)")
            src_in_build_ctx = (
                abs_path_to_build_dir / rel_path_to_tmp_dir / uuid4().hex / src_in_host.name
            )
            if src_in_host.is_symlink() or src_in_host.is_file():
                future_list.append(
                    executor.submit(
                        shutil.copy, str(src_in_host), str(src_in_build_ctx), follow_symlinks=False
                    )
                )
            else:
                src_in_build_ctx.mkdir(exist_ok=True, parents=True)
                for element in src_in_host.iterdir():
                    if element.is_dir():
                        future_list.append(
                            executor.submit(
                                shutil.copytree,
                                str(element),
                                str(src_in_build_ctx / element.name),
                                symlinks=False,
                                ignore_dangling_symlinks=True,
                            )
                        )
                    else:
                        future_list.append(
                            executor.submit(
                                shutil.copy,
                                str(element),
                                str(src_in_build_ctx / Path(element).name),
                            )
                        )
        files_with_dest.append(
            (src_in_build_ctx.relative_to(abs_path_to_build_dir).as_posix(), dest_str)
        )

    log_info("")
    return files_with_dest


def _copy_tungstenkit(
    build_dir: Path,
    rel_path_to_tungstenkit: Path,
    executor: ThreadPoolExecutor,
    future_list: t.List[Future],
):
    requirements_txt_path = Path(__file__).parent / "metadata" / "tungstenkit" / "requirements.txt"
    pyproject_toml_path = requirements_txt_path.with_name("pyproject.toml")
    tungstenkit_dir_in_build_ctx = build_dir / rel_path_to_tungstenkit
    requirements_txt_path_in_build_ctx = tungstenkit_dir_in_build_ctx / requirements_txt_path.name
    pyproject_toml_path_in_build_ctx = tungstenkit_dir_in_build_ctx / pyproject_toml_path.name

    src_dir = Path(tungstenkit.__file__).parent
    shutil.copy(str(requirements_txt_path), str(requirements_txt_path_in_build_ctx))
    shutil.copy(str(pyproject_toml_path), str(pyproject_toml_path_in_build_ctx))
    future_list.append(
        executor.submit(
            shutil.copytree,
            str(src_dir),
            str(tungstenkit_dir_in_build_ctx / "tungstenkit"),
            ignore=shutil.ignore_patterns("*.pyc"),  # TODO add more
        )
    )


def _show_progress_while_copying_files(
    copy_dir: Path, future_list: t.List[Future], ignore_patterns: t.Optional[t.List[str]] = None
):
    progress = Progress(TextColumn("{task.description}"))
    desc_prefix = "Copied: "
    task = progress.add_task(desc_prefix + "0B")
    with progress:
        while not all(fut.done() for fut in future_list):
            size_in_bytes = get_tree_size_in_bytes(
                root_dir=copy_dir, ignore_patterns=ignore_patterns
            )
            human_readable_size = format_file_size(size_in_bytes)
            progress.update(task, description=desc_prefix + human_readable_size)
            time.sleep(0.1)

        size_in_bytes = get_tree_size_in_bytes(root_dir=copy_dir, ignore_patterns=["tungstenkit"])
        human_readable_size = format_file_size(size_in_bytes)
        progress.update(task, description=desc_prefix + human_readable_size)

    log_info("")