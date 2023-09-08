import typing as t

from tungstenkit import exceptions
from tungstenkit._internal.json_store import JSONStore
from tungstenkit._internal.storables.model import ModelData, StoredModelData

_store = JSONStore[StoredModelData](StoredModelData)


def add(model: ModelData) -> None:
    stored = model.save()
    _store.add(stored)


def get(name: str) -> ModelData:
    try:
        stored = _store.get(name)
    except exceptions.NotFound as e:
        raise exceptions.ModelNotFound(str(e))
    return ModelData.load_blobs(stored)


def list() -> t.List[ModelData]:
    list_stored_data = _store.list()
    list_loaded_data: t.List[ModelData] = []
    for stored_data in list_stored_data:
        try:
            loaded_data = ModelData.load_blobs(stored_data)
            list_loaded_data.append(loaded_data)
        except exceptions.NotFound:
            _store.delete(stored_data.name)

    return list_loaded_data


def delete(name: str) -> None:
    _store.delete(name)


def clear_repo(repo_name: t.Optional[str] = None) -> t.List[str]:
    return _store.clear_repo(repo_name)
