import abc
import typing as t
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import attrs
import cattrs
from filelock import FileLock

from tungstenkit import exceptions
from tungstenkit._internal.blob_store import Blob, BlobStorable, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.constants import DATA_DIR, LOCK_DIR
from tungstenkit._internal.logging import log_debug
from tungstenkit._internal.utils.docker import parse_docker_image_name
from tungstenkit._internal.utils.file import write_safely
from tungstenkit._internal.utils.serialize import convert_attrs_to_json, load_attrs_from_json
from tungstenkit._internal.utils.string import camel_to_snake
from tungstenkit._internal.utils.types import get_superclass_type_args

StorableType = t.TypeVar("StorableType", bound="JSONStorable")
ItemType = t.TypeVar("ItemType", bound="JSONItem")
CollectionType = t.TypeVar("CollectionType", bound="_JSONCollection")

DEFAULT_TAG = "latest"


class JSONStorable(BlobStorable[ItemType]):
    _store: "JSONStore[ItemType]"

    def save(self, file_blob_create_policy: FileBlobCreatePolicy = "copy") -> ItemType:
        blob_store = BlobStore()
        with blob_store.prevent_deletion():
            data = self.save_blobs(blob_store, file_blob_create_policy)
            store = self._get_store()
            store.add(data)
        return data

    @classmethod
    def load(cls: t.Type[StorableType], name: str) -> StorableType:
        data = cls._get_store().get(name)
        return cls.load_blobs(data)

    @staticmethod
    def generate_id() -> str:
        return uuid4().hex

    @staticmethod
    def parse_name(name: str) -> t.Tuple[str, t.Optional[str]]:
        return parse_docker_image_name(name)

    @classmethod
    def _get_store(cls: t.Type[StorableType]) -> "JSONStore[ItemType]":
        if not hasattr(cls, "_store"):
            args = get_superclass_type_args(cls, JSONStorable)
            if len(args) == 0:
                raise RuntimeError("Type argument is not set")
            data_cls: t.Type[ItemType] = args[0]
            cls._store = JSONStore[data_cls](data_cls)  # type: ignore
        return cls._store


class JSONItem(abc.ABC):
    @property
    @abc.abstractmethod
    def id(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def repo_name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def tag(self) -> str:
        pass

    @property
    def name(self) -> str:
        return self.repo_name + ":" + self.tag

    @property
    @abc.abstractmethod
    def blobs(self) -> t.Set[Blob]:
        pass

    @property
    @abc.abstractmethod
    def created_at(self) -> datetime:
        pass

    @abc.abstractmethod
    def cleanup(self):
        pass

    @classmethod
    def get_typename(cls) -> str:
        return camel_to_snake(cls.__name__)


# TODO encapsulate JSONCollection
class JSONStore(t.Generic[ItemType]):
    _item_type: t.Type[ItemType]
    _collection_type: "t.Type[_JSONCollection[ItemType]]"

    def __init__(self, item_type: t.Type[ItemType]):
        self._item_type = item_type
        self._collection_type = _JSONCollection[item_type]  # type: ignore
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._filelock = FileLock(self.lock_path, timeout=180.0)
        self._blob_store = BlobStore()

    @property
    def base_dir(self) -> Path:
        return DATA_DIR / self._item_type.get_typename()

    @property
    def lock_path(self) -> Path:
        return LOCK_DIR / (self._item_type.get_typename() + "_collection.lock")

    @property
    def collection_path(self) -> Path:
        return self.base_dir / "collection.json"

    def add(self, item: ItemType):
        """Add to the colleciton and prune dangling items"""
        with self._filelock:
            col = self._collection_type.load(self._item_type, self.collection_path)
            col.add_item(item)
            self._gc(col)
            col.save(self.collection_path)

    def tag(self, src_name: str, dest_name: str) -> str:
        src_repo, _src_tag = JSONStorable.parse_name(src_name)
        src_tag = _src_tag if _src_tag else DEFAULT_TAG

        dest_repo, _dest_tag = JSONStorable.parse_name(dest_name)
        dest_tag = _dest_tag if _dest_tag else src_tag

        with self._filelock:
            col = self._collection_type.load(self._item_type, self.collection_path)
            src = col.get_item_by_tag(src_repo, src_tag)
            if src is None:
                raise exceptions.NotFound(self._build_not_found_err_msg(src_name))
            col.tag_item(dest_repo, dest_tag, src.id)
            col.save(self.collection_path)

        return dest_repo + ":" + dest_tag

    def update(self, item: ItemType) -> None:
        with self._filelock:
            col = self._collection_type.load(self._item_type, self.collection_path)
            orig = col.get_item_by_id(item.id)
            if orig is None:
                raise exceptions.NotFound(self._build_not_found_err_msg(item.name))
            col.update_item(item)
            col.save(self.collection_path)

    def get(self, name: str) -> ItemType:
        repo, _tag = JSONStorable.parse_name(name)

        with self._filelock:
            col = self._collection_type.load(self._item_type, self.collection_path)

        if not col.check_repo_exsistence(repo):
            raise exceptions.NotFound(self._build_not_found_err_msg(name))

        if _tag is None:
            if col.check_tag_exsistence_in_repo(repo, DEFAULT_TAG):
                tag = DEFAULT_TAG
            else:
                _tag = col.get_latest_tag_in_repo(repo_name=name)
                if _tag is None:
                    raise exceptions.NotFound(self._build_not_found_err_msg(name))
                else:
                    tag = _tag
        else:
            tag = _tag

        item = col.get_item_by_tag(repo, tag)
        if item is None:
            raise exceptions.NotFound(self._build_not_found_err_msg(name))
        attrs_kwargs = {k: v for k, v in attrs.asdict(item, recurse=False).items() if k != "tag"}
        return self._item_type(tag=tag, **attrs_kwargs)  # type: ignore

    # TODO Take fields argument
    def list(self) -> t.List[ItemType]:
        ret: t.List[ItemType] = []
        with self._filelock:
            col = self._collection_type.load(self._item_type, self.collection_path)

        items = col.list_items()
        for _, tag, item in items:
            attrs_kwargs = {
                k: v for k, v in attrs.asdict(item, recurse=False).items() if k != "tag"
            }
            ret.append(self._item_type(tag=tag, **attrs_kwargs))  # type: ignore

        return ret

    def delete(self, name: str):
        repo, _tag = JSONStorable.parse_name(name)
        tag = _tag if _tag else DEFAULT_TAG

        with self._filelock:
            col = self._collection_type.load(self._item_type, self.collection_path)
            if tag not in col.repositories[repo]:
                raise exceptions.NotFound(self._build_not_found_err_msg(name))

            del col.repositories[repo][tag]
            if len(col.repositories[repo]) == 0:
                del col.repositories[repo]

            self._gc(col)
            self._delete_unused_blobs()
            col.save(self.collection_path)

    def clear_repo(self, repo: t.Optional[str]) -> t.List[str]:
        removed = []
        for m in self.list():
            if repo is None or m.repo_name == repo:
                self.delete(name=m.name)
                removed.append(m.name)

        return removed

    def _gc(
        self,
        col: "_JSONCollection[ItemType]",
    ):
        removed_id_and_data = col.prune()
        if len(removed_id_and_data) == 0:
            return

        for _, item in removed_id_and_data:
            item.cleanup()

    def _delete_unused_blobs(self):
        self._blob_store.delete_unused(self._collect_blobs())

    def _collect_blobs(self) -> t.Set[Blob]:
        blobs: t.Set[Blob] = set()
        for m in self.list():
            blobs = blobs.union(m.blobs)
        return blobs

    def _build_not_found_err_msg(self, name: str):
        return f"{self._item_type.get_typename()} '{name}'"


@attrs.frozen
class _JSONCollection(t.Generic[ItemType]):
    repositories: t.Dict[str, t.Dict[str, str]] = attrs.field(factory=dict)
    items: t.Dict[str, ItemType] = attrs.field(factory=dict)

    def tag_item(self, repo_name: str, tag: str, id: str):
        if repo_name not in self.repositories.keys():
            self.repositories[repo_name] = dict()
        self.repositories[repo_name][tag] = id
        return id

    def add_item(
        self,
        item: ItemType,
    ):
        if item.repo_name not in self.repositories.keys():
            self.repositories[item.repo_name] = dict()
        self.items[item.id] = item
        self.tag_item(item.repo_name, item.tag, item.id)

    def update_item(self, item: ItemType):
        orig = self.items[item.id]
        assert orig.id == item.id
        self.items[item.id] = item

    def get_item_by_tag(self, repo_name: str, tag: str) -> t.Optional[ItemType]:
        if repo_name not in self.repositories or tag not in self.repositories[repo_name]:
            return None
        item = self.items[self.repositories[repo_name][tag]]
        return item

    def get_item_by_id(self, id: str) -> t.Optional[ItemType]:
        if id not in self.items:
            return None
        return self.items[id]

    def get_latest_tag_in_repo(self, repo_name: str) -> t.Optional[str]:
        if len(self.repositories[repo_name]) == 0:
            return None
        return sorted(
            self.repositories[repo_name].keys(),
            key=lambda key: self.items[self.repositories[repo_name][key]].created_at,
            reverse=True,
        )[0]

    def list_items(self) -> t.List[t.Tuple[str, str, ItemType]]:
        ret: t.List[t.Tuple[str, str, ItemType]] = []
        for repo_name in self.repositories.keys():
            for tag, id in self.repositories[repo_name].items():
                item = self.items[id]
                ret.append((repo_name, tag, item))
        return sorted(ret, key=lambda val: (val[0], datetime.utcnow() - val[2].created_at))

    def list_items_in_repo(self, repo_name: str) -> t.List[t.Tuple[str, ItemType]]:
        ret: t.List[t.Tuple[str, ItemType]] = []
        for tag, id in self.repositories[repo_name].items():
            item = self.items[id]
            ret.append((tag, item))
        return sorted(ret, key=lambda val: val[1].created_at, reverse=True)

    def prune(
        self, candidate_ids: t.Optional[t.Iterable[str]] = None
    ) -> t.List[t.Tuple[str, ItemType]]:
        if candidate_ids is None:
            candidate_ids = [id for id in self.items.keys()]
        else:
            candidate_ids = [id for id in candidate_ids if id in self.items.keys()]

        deleted: t.List[t.Tuple[str, ItemType]] = list()
        for id in set(candidate_ids):
            is_removed = not self.check_item_exsistence(id)
            if is_removed:
                deleted.append((id, self.items[id]))
                del self.items[id]

        return deleted

    def check_tag_exsistence_in_repo(self, repo_name: str, tag: str) -> bool:
        return repo_name in self.repositories and tag in self.repositories[repo_name]

    def check_repo_exsistence(self, repo_name: str) -> bool:
        return repo_name in self.repositories

    def check_item_exsistence(self, id: str) -> bool:
        return any(
            id in self.repositories[repo_name].values() for repo_name in self.repositories.keys()
        )

    def save(self, path: Path):
        log_debug(f"Save JSON collection to '{path}'")
        serialized = convert_attrs_to_json(self)
        write_safely(path, serialized)

    @classmethod
    def load(
        cls: t.Type[CollectionType], item_type: t.Type[ItemType], path: Path
    ) -> CollectionType:
        if not path.exists():
            return cls()

        try:
            col = load_attrs_from_json(cls[item_type], path)  # type: ignore
        except cattrs.errors.ClassValidationError:
            cls._raise_data_parse_error(path)
        log_debug(f"Load JSON collection from '{path}'")
        return col

    @classmethod
    def _raise_data_parse_error(cls, path: Path):
        raise exceptions.StoredDataError(
            "Failed to parse stored data. "
            "The reason might be that an old version of data still remains.\n"
            f"Please remove the directory '{path.parent}' and retry."
        )
