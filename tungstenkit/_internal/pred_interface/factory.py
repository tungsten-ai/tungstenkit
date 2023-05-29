from furl import furl

from tungstenkit import exceptions

from .abstract_interface import PredInterface
from .api_interface import ModelAPI
from .local_interface import LocalModel


def get(name_or_url: str) -> PredInterface:
    f = furl(name_or_url)
    if not f.scheme:
        model: PredInterface = LocalModel(name_or_url)
        return model

    elif f.scheme != "http" and f.scheme != "https":
        raise exceptions.InvalidURL(f"expected http or https url, not {f.scheme}")

    else:
        model = ModelAPI(name_or_url)
        try:
            model._client.get_metadata()
            return model
        except exceptions.ModelClientError:
            raise exceptions.NotFound(f"no model server running at {name_or_url}")
