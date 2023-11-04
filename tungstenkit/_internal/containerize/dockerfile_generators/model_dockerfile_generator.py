from tungstenkit._internal import model_server
from tungstenkit._internal.configs import ModelBuildConfig

from .base_dockerfile_generator import BaseDockerfileGenerator
from .scripts import post_model_build


class ModelDockerfileGenerator(BaseDockerfileGenerator):
    config: ModelBuildConfig

    def _build_template_args(self, *args, **kwargs):
        template_args = super()._build_template_args(*args, **kwargs)
        template_args.tungsten_env_vars["TUNGSTEN_MAX_BATCH_SIZE"] = self.config.batch_size
        if self.config.has_post_build:
            template_args.dockerfile_commands.append(
                f"RUN python -m {post_model_build.__name__} "
                f"-m {self.config.model_module_ref} -c {self.config.model_class_name}"
            )
        return template_args

    @classmethod
    def python_entrypoint(cls) -> str:
        mod = model_server.__name__
        return f"-m {mod}"
