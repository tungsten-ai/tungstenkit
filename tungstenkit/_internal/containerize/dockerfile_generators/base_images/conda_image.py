import attrs

from .base_image import BaseImage


@attrs.frozen
class CondaImage(BaseImage):
    @staticmethod
    def get_repository():
        return "condaforge/miniforge3"

    @staticmethod
    def get_tag():
        return "latest"
