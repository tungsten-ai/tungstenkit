import typing as t
from datetime import datetime

import attrs

from tungstenkit import exceptions
from tungstenkit._internal.blob_store import Blob, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.constants import DEFAULT_GPU_MEM_GB
from tungstenkit._internal.json_store import JSONItem, JSONStorable
from tungstenkit._internal.utils.docker import (
    get_docker_client,
    parse_docker_image_name,
    remove_docker_image,
)
from tungstenkit._internal.utils.serialize import load_attrs_from_json

from .avatar_data import AvatarData, StoredAvatar
from .markdown_data import MarkdownData, StoredMarkdown
from .model_io_data import ModelIOData, StoredModelIOData
from .source_file_data import (
    SerializedSourceFileCollection,
    SourceFile,
    SourceFileCollection,
    StoredSourceFileCollection,
)


@attrs.define(kw_only=True)
class _ModelDataInImage:
    module_name: str
    class_name: str
    docker_image_id: str
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
                if label_name == "device":
                    device = label_value
                elif label_name == "gpu_mem_gb":
                    gpu_mem_gb = int(label_value)
                    if device == "gpu" and gpu_mem_gb == 0:
                        gpu_mem_gb = DEFAULT_GPU_MEM_GB

        return _ModelDataInImage(
            module_name=module_name,
            class_name=class_name,
            docker_image_id=docker_image_id,
            batch_size=batch_size,
            device=device,
            gpu_mem_gb=gpu_mem_gb,
        )


@attrs.frozen(kw_only=True)
class StoredModelData(JSONItem):
    id: str
    repo_name: str
    tag: str

    io: StoredModelIOData
    avatar: StoredAvatar
    readme: t.Optional[StoredMarkdown] = None
    source_files: t.Optional[SerializedSourceFileCollection] = None

    created_at: datetime = attrs.field(factory=datetime.utcnow)

    @property
    def blobs(self) -> t.Set[Blob]:
        blob_set: t.Set[Blob] = set()

        blob_set.add(self.io.blob)

        blob_set.add(self.avatar.blob)

        if self.readme is not None:
            blob_set.add(self.readme.markdown)
            for b in self.readme.images:
                blob_set.add(b)
        if self.source_files is not None:
            blob_set.add(self.source_files.blob)
            source_files = load_attrs_from_json(
                StoredSourceFileCollection, self.source_files.blob.file_path
            )
            for f in source_files.files:
                if f.blob is not None:
                    blob_set.add(f.blob)

        return blob_set

    def cleanup(self):
        remove_docker_image(self.name)

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

    io: ModelIOData
    avatar: AvatarData
    readme: t.Optional[MarkdownData] = None
    source_files: t.Optional[SourceFileCollection] = None

    _created_at: t.Optional[datetime] = attrs.field(default=None, alias="created_at")

    def __init__(
        self,
        *,
        name: str,
        io_data: ModelIOData,
        avatar: AvatarData,
        readme: t.Optional[MarkdownData] = None,
        source_files: t.Optional[t.Iterable[SourceFile]] = None,
        id: t.Optional[str] = None,
        created_at: t.Optional[datetime] = None,
    ):
        self.id = self.generate_id() if id is None else id
        self.name = name
        self.repo_name, _tag = StoredModelData.parse_name(name)
        tag = self.id if _tag is None else _tag
        self.tag = tag

        self.io = io_data
        self.avatar = avatar
        self.readme = readme
        self.source_files = SourceFileCollection(source_files) if source_files else None
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

    @property
    def short_name(self) -> str:
        return self.repo_name.split("/")[-1]

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

        stored_schema = self.io.save_blobs(
            blob_store=blob_store, file_blob_create_policy=file_blob_create_policy
        )

        stored_avatar = self.avatar.save_blobs(
            blob_store=blob_store, file_blob_create_policy=file_blob_create_policy
        )

        if self.source_files:
            stored_source_files = self.source_files.save_blobs(
                blob_store=blob_store, file_blob_create_policy=file_blob_create_policy
            )
        else:
            stored_source_files = None

        extra_kwargs = dict()
        if self._created_at:
            extra_kwargs["created_at"] = self._created_at

        return StoredModelData(
            id=self.id,
            repo_name=self.repo_name,
            tag=self.tag,
            io=stored_schema,
            avatar=stored_avatar,
            readme=stored_readme,
            source_files=stored_source_files,
            **extra_kwargs,
        )

    @classmethod
    def load_blobs(cls, data: StoredModelData) -> "ModelData":
        return ModelData(
            name=data.name,
            created_at=data.created_at,
            io_data=ModelIOData.load_blobs(data.io),
            avatar=AvatarData.load_blobs(data.avatar),
            readme=MarkdownData.load_blobs(data.readme) if data.readme else None,
            source_files=SourceFileCollection.load_blobs(data.source_files).files
            if data.source_files
            else None,
        )
