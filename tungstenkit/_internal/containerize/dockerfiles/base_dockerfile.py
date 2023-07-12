import abc
import typing as t
from pathlib import Path

import attrs
import jinja2
from packaging.version import Version
from pathspec import PathSpec

import tungstenkit
from tungstenkit._internal.configs import BuildConfig
from tungstenkit._internal.logging import log_debug, log_info, log_warning
from tungstenkit._internal.utils.version import NotRequired

from ..base_images import BaseImage, CUDAImageCollection, CustomImage, PythonImageCollection
from ..gpu_pkg_collections import supported_gpu_pkg_names
from ..pkg_manager import PythonPackageManager, RequirementsTxt
from .template_args import TemplateArgs

LARGE_FILE_THRESHOLD = 100 * 1024**2


class BaseDockerfile(metaclass=abc.ABCMeta):
    def __init__(
        self,
        config: BuildConfig,
    ):
        self.config = config

    def generate(
        self,
        tmp_dir_in_build_ctx: Path,
    ):
        template_args = self.build_template_args(
            tmp_dir_in_build_ctx=tmp_dir_in_build_ctx,
        )
        log_debug("Dockerfile template args:\n" + str(template_args))
        log_info("\n")
        log_info(f"[bold]Use GPU: {template_args.device == 'gpu'}[/bold]")
        log_info(f"[bold]Base image: [green]{template_args.image.name}[/green][/bold]")
        log_info(
            f"[bold]Python version: [green]{str(template_args.python_version)}[/green][/bold]"
        )
        log_info("\n")
        # Render Dockerfile from template
        j2_env = jinja2.Environment(
            extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols", "jinja2.ext.debug"],
            trim_blocks=True,
            lstrip_blocks=True,
            loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates", followlinks=True),
        )
        template = j2_env.get_template(name="debian.j2")
        dockerfile = template.render(**attrs.asdict(template_args, recurse=False))

        return dockerfile

    def build_template_args(
        self,
        tmp_dir_in_build_ctx: Path,
    ):
        # TODO perfer cuda version available in docker hub
        # TODO check py vers compatible with miniforge3
        # TODO don't use cuda base image if python package already includes cuda (e.g. torch)

        cuda_ver: t.Optional[t.Union[Version, NotRequired]] = (
            self.config.cuda_version if self.config.gpu else NotRequired()
        )
        py_ver: t.Optional[Version] = self.config.python_version
        cudnn_ver: t.Optional[Version] = None
        if py_ver and py_ver.micro:
            py_ver = Version(f"{py_ver.major}.{py_ver.minor}")

        # Add pip requirements
        py_pkg_manager = PythonPackageManager()
        for requirement_str in self.config.python_packages:
            # TODO requirement_str -> requirement
            py_pkg_manager.add_requirement_str(requirement_str)

        py_pkg_manager.add_requirement_str(tungstenkit.__name__ + "==" + tungstenkit.__version__)

        # Set user-defined CUDA & Python versions
        py_pkg_manager.set_gpu(self.config.gpu)

        # Infer CUDA, CuDNN and Python versions if requested
        if self.config.gpu:
            if cuda_ver is None:
                cuda_ver = py_pkg_manager.infer_cuda_ver()
            else:
                log_info("CUDA version inference is disabled.")

            if isinstance(cuda_ver, NotRequired):
                log_warning(
                    "CUDA will not be added to the container, "
                    "although the container uses GPU, "
                    "since no known GPU package was given. "
                    "To prevent this, you can set 'cuda_version' explicitly. "
                    "Python packages for which CUDA version inference is supported are: "
                    f"{', '.join(supported_gpu_pkg_names)}"
                )
            elif cuda_ver is not None:
                py_pkg_manager.set_cuda_equal_to(cuda_ver)
                cudnn_ver = py_pkg_manager.infer_cudnn_ver()

        py_ver = py_ver if py_ver else py_pkg_manager.infer_python_ver()
        py_pkg_manager.set_python_equal_to(py_ver)

        # Prepare requirements.txt and pip install commands
        list_pip_install_args = []
        requirements_txt = RequirementsTxt()
        pip_requirements_txt_path = tmp_dir_in_build_ctx / "requirements.txt"

        gpu_pkg_requirements = py_pkg_manager.list_gpu_pkg_pip_requirements()
        for r in gpu_pkg_requirements:
            list_pip_install_args.append(r.to_str().split(" "))

        extra_pkg_requirements = py_pkg_manager.list_extra_pkg_pip_requirements()
        for r in extra_pkg_requirements:
            if r.index_url:
                list_pip_install_args.append(r.to_str().split(" "))
            else:
                requirements_txt.add_requirement(r)

        requirements_txt_content = requirements_txt.build()
        pip_requirements_txt_path.write_text(requirements_txt_content)
        log_debug("pip install args: " + str(list_pip_install_args), pretty=False)
        log_debug("python requirements.txt:\n" + requirements_txt_content, pretty=False)

        # Set base image
        if self.config.base_image:
            image: BaseImage = CustomImage(self.config.base_image)
        elif not isinstance(cuda_ver, NotRequired) and py_pkg_manager.requires_system_cuda():
            log_info("Fetching the list of cuda base images")
            cuda_image_collection = CUDAImageCollection.from_docker_hub()
            if cuda_ver is None:  # Requires CUDA but any version is okay
                image = cuda_image_collection.get_latest_image()
            else:
                image = cuda_image_collection.get_cuda_image_by_cuda_cudnn_ver(cuda_ver, cudnn_ver)
        else:
            log_info("Fetching the list of python base images")
            python_image_collection = PythonImageCollection.from_docker_hub()
            image = python_image_collection.get_py_image_by_ver(py_ver)

        large_files, small_files = self.split_large_and_small_files(
            Path("."), tmp_dir_in_build_ctx
        )

        template_args = TemplateArgs(
            image=image,
            python_version=py_ver,
            python_entrypoint=self.python_entrypoint(),
            pip_requirements_txt_in_build_ctx=pip_requirements_txt_path,
            list_pip_install_args=list_pip_install_args,
            system_packages=self.config.system_packages,
            pip_wheels_in_build_ctx=self.config.pip_wheels,
            env_vars=self.config.environment_variables,
            tungsten_env_vars=self.config.tungsten_environment_variables,
            copy_files=self.config.copy_files,
            device="gpu" if self.config.gpu else "cpu",
            large_files=large_files,
            small_files=small_files,
            gpu_mem_gb=self.config.gpu_mem_gb,
        )

        return template_args

    def split_large_and_small_files(
        self,
        curr_dir: Path,
        tmp_dir_in_build_ctx: Path,
    ) -> t.Tuple[t.List[Path], t.List[Path]]:
        """
        Returns large file paths and small file paths as lists.
        If there is no large files, returns ``None``.
        """
        include_spec = PathSpec.from_lines("gitwildmatch", self.config.include_files)
        exclude_spec = PathSpec.from_lines(
            "gitwildmatch", self.config.exclude_files + [tmp_dir_in_build_ctx.as_posix()]
        )

        def split(curr_dir: Path) -> t.Tuple[t.List[Path], t.List[Path]]:
            large_files, small_files = [], []
            for path in curr_dir.iterdir():
                if not include_spec.match_file(path.as_posix()) or exclude_spec.match_file(
                    path.as_posix()
                ):
                    continue

                if path.is_dir():
                    ret = split(path)
                    large_files.extend(ret[0])
                    small_files.extend(ret[1])

                else:
                    size = path.stat(follow_symlinks=False).st_size
                    if size > LARGE_FILE_THRESHOLD:
                        large_files.append(path)
                    else:
                        small_files.append(path)

            if len(large_files) == 0:
                return [], [curr_dir]

            return large_files, small_files

        large_files, small_files = split(curr_dir)
        large_files = sorted(
            large_files,
            key=lambda path: (_get_size_of_copy_target(path), path.name),
            reverse=True,
        )
        small_files = sorted(
            small_files,
            key=lambda path: (_get_size_of_copy_target(path), path.name),
            reverse=True,
        )
        return large_files, small_files

    @classmethod
    @abc.abstractmethod
    def python_entrypoint(cls) -> str:
        pass


def _get_size_of_copy_target(path: Path):
    if path.is_dir():
        size = sum(f.stat().st_size for f in path.glob("**/*") if f.is_file())
    else:
        size = path.stat(follow_symlinks=False).st_size
    return size
