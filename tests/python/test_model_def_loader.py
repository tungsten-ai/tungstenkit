from fastapi.encoders import jsonable_encoder

from tungstenkit._internal.configs import ModelConfig
from tungstenkit._internal.model_def_loader import ModelModuleLoader

from . import dummy_model


def test_model_module_loader():
    loader = ModelModuleLoader(
        module_ref=dummy_model.__name__, class_name=dummy_model.DummyModel.__name__
    )
    assert loader.model_class == dummy_model.DummyModel
    assert isinstance(loader.model, dummy_model.DummyModel)
    assert loader.input_class == dummy_model.DummyInput
    assert loader.output_class == dummy_model.DummyOutput
    config = ModelConfig.with_types(
        input_cls=dummy_model.DummyInput, output_cls=dummy_model.DummyOutput
    )(**dummy_model.DummyModel.__tungsten_config__)
    config.environment_variables["TUNGSTEN_MODEL_MODULE"] = dummy_model.__name__
    config.environment_variables["TUNGSTEN_MODEL_CLASS"] = dummy_model.DummyModel.__name__

    loaded_config = jsonable_encoder(loader.config)
    for key, val in jsonable_encoder(config).items():
        assert loaded_config[key] == val
