from typing import List

from PIL import ImageFilter

from tungstenkit import BaseIO, Field, Image, define_model


class Input(BaseIO):
    image: Image = Field(description="Image to blur")


class Output(BaseIO):
    blurred: Image


@define_model(
    input=Input,
    output=Output,
    gpu=False,
    python_packages=["pillow"],
)
class BlurBasic:
    def setup(self):
        self.image_filter = ImageFilter.GaussianBlur(radius=5)

    def predict(self, inputs: List[Input]) -> List[Output]:
        images = [inp.image.to_pil_image() for inp in inputs]
        converted = []
        for img in images:
            converted.append(img.filter(self.image_filter))
        return [Output(blurred=Image.from_pil_image(img)) for img in images]
