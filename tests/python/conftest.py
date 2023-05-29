import atexit
import os
import shutil
import tempfile

import pytest

# Prepare data dir
data_dir = tempfile.mkdtemp(prefix="tungstenkit-test-")
os.environ["TUNGSTEN_DATA_DIR"] = data_dir
atexit.register(shutil.rmtree, data_dir)


# Load fixtures
from .containerize.fixtures import *  # noqa
from .containers.fixtures import *  # noqa
from .demo_server.fixtures import *  # noqa
from .dummy_model_fixtures import *  # noqa
from .model_server.fixtures import *  # noqa
from .storables.fixtures import *  # noqa

if os.getenv("_PYTEST_RAISE", "0") != "0":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value
