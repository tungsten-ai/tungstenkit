import attrs

from .base_image import BaseImage


@attrs.frozen
class CustomImage(BaseImage):
    name: str

    def get_repository(self):
        return self.name.split(":", maxsplit=1)[0]

    def get_tag(self):
        splitted = self.name.split(":", maxsplit=1)
        if len(splitted) > 1:
            return splitted[1]
        else:
            return "latest"
