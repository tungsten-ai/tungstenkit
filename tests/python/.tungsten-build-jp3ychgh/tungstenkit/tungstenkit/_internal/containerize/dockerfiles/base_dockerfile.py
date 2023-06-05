import abc
import typing as t
from pathlib import Path

import attrs
import jinja2
from packaging.version import Version

from tungstenkit._internal.configs import BuildConfig
from tungstenkit._internal.logging import log_debug, log_info, log_warning
from tungstenkit._internal.utils.version import NotRequired

from ..base_images import BaseImage, CUDAImageCollection, CustomImage, PythonImageCollection
from ..gpu_pkg_collections import supported_gpu_pkg_names
from ..pkg_manager import PythonPackageManager, RequirementsTxt
from .template_args import TemplateArgs


class BaseDockerfile(metaclass=abc.ABCMeta):
    def __init__(
        self,
        config: BuildConfig,
    ):
        self.config = config

    def generate(
        self,
        tmp_dir_in_build_ctx: Path,
        tungstenkit_dir_in_build_ctx: Path,
    ):
        template_args = self.build_template_args(
            tmp_dir_in_build_ctx=tmp_dir_in_build_ctx,
            tungstenkit_dir_in_build_ctx=tungstenkit_dir_in_build_ctx,
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

    def build_template_args(self, tmp_dir_in_build_ctx: Path, tungstenkit_dir_in_build_ctx: Path):
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
            if r.pip_index_url:
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
        elif not isinstance(cuda_ver, NotRequired):
            log_info("Fetching the list of cuda base images")
            cuda_image_collection = CUDAImageCollection.from_docker_hub()
            # Infered successfully but got None -> any version is ok
            if cuda_ver is None:
                image = cuda_image_collection.get_latest_image()
            else:
                image = cuda_image_collection.get_cuda_image_by_cuda_cudnn_ver(cuda_ver, cudnn_ver)
        else:
            log_info("Fetching the list of python base images")
            python_image_collection = PythonImageCollection.from_docker_hub()
            image = python_image_collection.get_py_image_by_ver(py_ver)

        template_args = TemplateArgs(
            image=image,
            python_version=py_ver,
            python_entrypoint=self.python_entrypoint(),
            pip_requirements_txt_in_build_ctx=pip_requirements_txt_path,
            list_pip_install_args=list_pip_install_args,
            system_packages=self.config.system_packages,
            pip_wheels_in_build_ctx=self.config.pip_wheels,
            env_vars=self.config.environment_variables,
            copy_files=self.config.copy_files,
            description=self.config.description,
            device="gpu" if self.config.gpu else "cpu",
            tungstenkit_dir_in_build_ctx=tungstenkit_dir_in_build_ctx,
        )

        return template_args

    @classmethod
    @abc.abstractmethod
    def python_entrypoint(cls) -> str:
        pass