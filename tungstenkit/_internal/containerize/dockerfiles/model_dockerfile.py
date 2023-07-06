from tungstenkit._internal import model_server
from tungstenkit._internal.configs import ModelConfig

from .base_dockerfile import BaseDockerfile


class ModelDockerfile(BaseDockerfile):
    config: ModelConfig

    def __init__(self, config: ModelConfig):
        super().__init__(config)

    def build_template_args(self, *args, **kwargs):
        template_args = super().build_template_args(*args, **kwargs)
        template_args.tungsten_env_vars["TUNGSTEN_MAX_BATCH_SIZE"] = self.config.batch_size
        return template_args

    @classmethod
    def python_entrypoint(cls) -> str:
        mod = model_server.__name__
        return f"-m {mod}"
