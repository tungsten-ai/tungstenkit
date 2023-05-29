import typing as t
from uuid import UUID, uuid4

import attrs


@attrs.define(kw_only=True)
class MockDockerImage:
    uuid: UUID = attrs.field(factory=uuid4)
    tags: t.List[str] = attrs.field(factory=list)
    envs: t.List[t.Tuple[str, str]] = attrs.field(factory=list)
    labels: t.List[t.Tuple[str, str]] = attrs.field(factory=list)

    @property
    def id(self) -> str:
        return self.uuid.hex

    @property
    def attrs(self) -> t.Dict[str, t.Any]:
        config: t.Dict[str, t.Any] = dict()
        config.update(Env={f"{key}={value}" for key, value in self.envs})
        config.update(Labels={key: value for key, value in self.labels})
        return {"Config": config}


@attrs.define
class ImageCollection:
    _images: t.List[MockDockerImage] = attrs.field(factory=list)

    def get(self, image: str):
        for img in self._images:
            if img.id == image:
                return img
            elif image in img.tags:
                return img

    def remove(self, image: str, force: bool, noprune: bool):
        to_be_removed = []
        for img in self._images:
            if img.id == image:
                to_be_removed.append(img)
            elif image in img.tags:
                to_be_removed.append(img)

    def _add(self, image: MockDockerImage):
        self._images.append(image)


@attrs.define
class MockDockerClient:
    images = attrs.field(factory=ImageCollection)
