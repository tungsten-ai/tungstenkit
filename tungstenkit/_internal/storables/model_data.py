import typing as t
from datetime import datetime

import attrs

from tungstenkit._internal.blob_store import Blob, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.container_metadata_store import StoredContainerMetadata
from tungstenkit._internal.utils.docker import get_docker_client, parse_docker_image_name

from .avatar_data import AvatarData, StoredAvatarData
from .io_schema_data import IOSchemaData, StoredIOSchemaData
from .json_storable import JSONStorable
from .markdown_data import MarkdownData, StoredMarkdownData
from .pred_example_data import PredExampleData, StoredPredExampleData


@attrs.define(kw_only=True)
class _ModelDataInImage:
    module_name: str
    class_name: str
    docker_image_id: str
    description: str
    batch_size: int
    device: str
    gpu_mem_gb: t.Optional[int]

    @property
    def gpu(self) -> bool:
        return self.device == "gpu"

    @staticmethod
    def from_image(docker_image_name: str):
        docker_client = get_docker_client()
        docker_image = docker_client.images.get(docker_image_name)
        docker_image_id = docker_image.id

        env_vars: t.Optional[t.List[str]] = docker_image.attrs["Config"]["Env"]
        labels: t.Optional[t.Dict[str, str]] = docker_image.attrs["Config"]["Labels"]
        module_name = "tungsten_model"
        class_name = "Model"
        description = "Model"
        batch_size = 1
        device = "cpu"
        gpu_mem_gb = None
        if env_vars:
            for e in env_vars:
                try:
                    key, val = e.split("=", maxsplit=1)
                except ValueError:
                    continue
                if key == "TUNGSTEN_MODEL_MODULE":
                    module_name = val
                elif key == "TUNGSTEN_MODEL_CLASS":
                    class_name = val
                elif key == "TUNGSTEN_MAX_BATCH_SIZE":
                    batch_size = int(val)
        if labels:
            for label_name, label_value in labels.items():
                if label_name == "description":
                    description = label_value
                elif label_name == "device":
                    device = label_value
                elif label_name == "gpu_mem_gb":
                    gpu_mem_gb = int(label_value)

        return _ModelDataInImage(
            module_name=module_name,
            class_name=class_name,
            docker_image_id=docker_image_id,
            description=description,
            batch_size=batch_size,
            device=device,
            gpu_mem_gb=gpu_mem_gb,
        )


@attrs.frozen(kw_only=True)
class StoredModelData(_ModelDataInImage, StoredContainerMetadata):
    id: str
    repo_name: str
    tag: str

    io_schema: StoredIOSchemaData
    avatar: StoredAvatarData
    readme: t.Optional[StoredMarkdownData] = None
    examples: t.Dict[str, StoredPredExampleData] = attrs.field(factory=dict)

    created_at: datetime = attrs.field(factory=datetime.utcnow)

    @property
    def blobs(self) -> t.Set[Blob]:
        blob_set: t.Set[Blob] = set()

        # io schema
        blob_set.add(self.io_schema.input)
        blob_set.add(self.io_schema.output)
        blob_set.add(self.avatar.blob)
        if self.readme is not None:
            blob_set.add(self.readme.markdown)
            for b in self.readme.images:
                blob_set.add(b)
        if self.examples is not None:
            for example in self.examples.values():
                blob_set.add(example.input)
                blob_set.add(example.output)
                blob_set.add(example.demo_output)
                if example.logs:
                    blob_set.add(example.logs)
                for b in example.files:
                    blob_set.add(b)

        return blob_set

    def cleanup(self):
        docker_client = get_docker_client(timeout=None)
        docker_client.images.remove(image=self.docker_image_id, force=True)

    @staticmethod
    def parse_name(name: str) -> t.Tuple[str, str]:
        repo, tag = parse_docker_image_name(name)
        if tag:
            return repo, tag
        return repo, "latest"


@attrs.define(kw_only=True, init=False)
class ModelData(_ModelDataInImage, JSONStorable[StoredModelData]):
    id: str
    name: str
    repo_name: str
    tag: str

    io_schema: IOSchemaData
    avatar: AvatarData
    readme: t.Optional[MarkdownData] = None
    examples: t.List[PredExampleData] = attrs.field(factory=list)

    _created_at: t.Optional[datetime] = attrs.field(default=None, alias="created_at")

    def __init__(
        self,
        *,
        name: str,
        io_schema: IOSchemaData,
        avatar: AvatarData,
        readme: t.Optional[MarkdownData] = None,
        examples: t.Optional[t.List[PredExampleData]] = None,
        id: t.Optional[str] = None,
        created_at: t.Optional[datetime] = None,
    ):
        self.id = self.generate_id() if id is None else id
        self.name = name
        self.repo_name, _tag = StoredModelData.parse_name(name)
        tag = self.id if _tag is None else _tag
        self.tag = tag

        self.io_schema = io_schema
        self.avatar = avatar
        self.readme = readme
        self.examples = examples if examples else []
        self._created_at = created_at

        attributes_from_image = attrs.asdict(
            _ModelDataInImage.from_image(self.name), recurse=False
        )
        for key, value in attributes_from_image.items():
            setattr(self, key, value)

    @property
    def created_at(self) -> datetime:
        if self._created_at is None:
            self._created_at = datetime.utcnow()
        return self._created_at

    def save_blobs(
        self,
        blob_store: BlobStore,
        file_blob_create_policy: FileBlobCreatePolicy = "copy",
    ) -> StoredModelData:
        if self.readme:
            stored_readme = self.readme.save_blobs(
                blob_store=blob_store, file_blob_create_policy=file_blob_create_policy
            )
        else:
            stored_readme = None

        stored_schema = self.io_schema.save_blobs(blob_store=blob_store)
        stored_avatar = self.avatar.save_blobs(blob_store=blob_store)
        stored_examples = dict()
        for example in self.examples:
            e = example.save_blobs(
                blob_store=blob_store, file_blob_create_policy=file_blob_create_policy
            )
            stored_examples[e.id] = e

        extra_kwargs = dict()
        if self._created_at:
            extra_kwargs["created_at"] = self._created_at

        return StoredModelData(
            id=self.id,
            repo_name=self.repo_name,
            tag=self.tag,
            readme=stored_readme,
            io_schema=stored_schema,
            avatar=stored_avatar,
            examples=stored_examples,
            module_name=self.module_name,
            class_name=self.class_name,
            docker_image_id=self.docker_image_id,
            description=self.description,
            batch_size=self.batch_size,
            device=self.device,
            gpu_mem_gb=self.gpu_mem_gb,
            **extra_kwargs,
        )

    @classmethod
    def load_blobs(cls, data: StoredModelData) -> "ModelData":
        return ModelData(
            name=data.name,
            created_at=data.created_at,
            io_schema=IOSchemaData.load_blobs(data.io_schema),
            avatar=AvatarData.load_blobs(data.avatar),
            readme=MarkdownData.load_blobs(data.readme) if data.readme else None,
            examples=[PredExampleData.load_blobs(e) for e in data.examples.values()]
            if data.examples
            else None,
        )
