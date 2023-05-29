import typing as t

from tungstenkit._internal.storables.model_data import ModelData, StoredModelData

from .json_store import JSONStore

_store = JSONStore[StoredModelData](StoredModelData)


def get(name: str) -> ModelData:
    stored = _store.get(name)
    return ModelData.load_blobs(stored)


def list() -> t.List[ModelData]:
    stored = _store.list()
    return [ModelData.load_blobs(s) for s in stored]


def delete(name: str) -> None:
    _store.delete(name)


def clear_repo(repo_name: t.Optional[str] = None) -> t.List[str]:
    return _store.clear_repo(repo_name)
