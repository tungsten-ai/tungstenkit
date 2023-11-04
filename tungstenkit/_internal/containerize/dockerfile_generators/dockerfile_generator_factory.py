from tungstenkit._internal.configs import BuildConfig, ModelBuildConfig

from .model_dockerfile_generator import ModelDockerfileGenerator


def create_dockerfile_generator(config: BuildConfig):
    if isinstance(config, ModelBuildConfig):
        return ModelDockerfileGenerator(config)

    raise NotImplementedError(type(config))
