from tungstenkit._internal import model_server
from tungstenkit._internal.configs import ModelBuildConfig

from .base_dockerfile import BaseDockerfile
from .scripts import post_model_build


class ModelDockerfile(BaseDockerfile):
    config: ModelBuildConfig

    def __init__(self, config: ModelBuildConfig, model_module: str, model_class: str):
        super().__init__(config)
        self.model_module = model_module
        self.model_class = model_class

    def build_template_args(self, *args, **kwargs):
        template_args = super().build_template_args(*args, **kwargs)
        template_args.tungsten_env_vars["TUNGSTEN_MAX_BATCH_SIZE"] = self.config.batch_size
        if self.config.has_post_build:
            template_args.dockerfile_commands.append(
                f"RUN python -m {post_model_build.__name__} "
                f"-m {self.model_module} -c {self.model_class}"
            )
        return template_args

    @classmethod
    def python_entrypoint(cls) -> str:
        mod = model_server.__name__
        return f"-m {mod}"
