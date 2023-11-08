import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Prepare app dirs
data_dir = tempfile.mkdtemp(prefix="tungstenkit-test-")
config_dir = tempfile.mkdtemp(prefix="tungstenkit-test-")
os.environ["TUNGSTEN_DATA_DIR"] = data_dir
os.environ["TUNGSTEN_CONFIG_DIR"] = config_dir
atexit.register(shutil.rmtree, data_dir)
atexit.register(shutil.rmtree, config_dir)

# Prepare temporary files for building dummy model
path_to_link_src_in_build_dir = Path(__file__).parent / "dummy_model_data" / "somedir" / "somefile"
path_to_link_src_outside_build_dir = Path(tempfile.mkstemp()[1])
path_to_link_src_outside_build_dir.write_text("hello world")
path_to_link_in_build_dir = (
    Path(__file__).parent / "dummy_model_data" / "somedir" / "symlink_abs_in_build_dir"
)
path_to_link_outside_build_dir = (
    Path(__file__).parent / "dummy_model_data" / "somedir" / "symlink_abs_outside_build_dir"
)
if not path_to_link_in_build_dir.exists():
    os.symlink(path_to_link_src_in_build_dir, path_to_link_in_build_dir)
if path_to_link_outside_build_dir.exists():
    os.remove(path_to_link_outside_build_dir)
os.symlink(path_to_link_src_outside_build_dir, path_to_link_outside_build_dir)
atexit.register(os.remove, path_to_link_src_outside_build_dir)
atexit.register(os.remove, path_to_link_in_build_dir)
atexit.register(os.remove, path_to_link_outside_build_dir)

# Patch file size thresholds
from tungstenkit._internal import constants  # noqa

constants.MAX_SOURCE_FILE_SIZE = 10 * 1024
constants.MIN_LARGE_FILE_SIZE_ON_BUILD = 10 * 1024


# Load fixtures
from .containerize.fixtures import *  # noqa
from .containers.fixtures import *  # noqa
from .demo_server.fixtures import *  # noqa
from .dummy_model_fixtures import *  # noqa
from .model_server.fixtures import *  # noqa
from .storables.fixtures import *  # noqa
from .tungsten_clients.fixtures import *  # noqa
from .utils.fixtures import *  # noqa

# Enable vscode debugger to catch exc
if os.getenv("_PYTEST_RAISE", "0") != "0":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value
