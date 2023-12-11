from tungstenkit._internal.io import FieldAnnotation
from tungstenkit._internal.storables import ModelData
from tungstenkit.exceptions import UnsupportedModel

SUPPORTED_ANNOTATIONS = [
    FieldAnnotation.image.value,
    FieldAnnotation.audio.value,
    FieldAnnotation.binary.value,
    FieldAnnotation.video.value,
]


def validate_model(model_data: ModelData):
    all_annotations = (
        list(model_data.io.input_annotations.values())
        + list(model_data.io.output_annotations.values())
        + list(model_data.io.demo_output_annotations.values())
    )
    for anno in all_annotations:
        if anno not in SUPPORTED_ANNOTATIONS:
            raise UnsupportedModel(
                f"Model '{model_data.name}' contains unsupported field type: {anno}. To run demo, push to tungsten.run (`tungsten push`) or update tungstenkit."  # noqa: E501
            )
