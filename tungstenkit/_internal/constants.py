import os
import re
import tempfile
from pathlib import Path, PurePosixPath

from packaging.version import Version


def default_model_repo() -> str:
    wd_name = (
        re.sub(r"[^A-Za-z0-9_-]+", "", Path(os.getcwd()).resolve().parts[-1])
        .lower()
        .replace("_", "-")
    )
    if wd_name:
        repo = "tungsten-" + wd_name
    else:
        repo = "tungsten"
    return repo


TUNGSTEN_LOGO = r"""

████████╗██╗   ██╗███╗   ██╗ ██████╗ ███████╗████████╗███████╗███╗   ██╗
╚══██╔══╝██║   ██║████╗  ██║██╔════╝ ██╔════╝╚══██╔══╝██╔════╝████╗  ██║
   ██║   ██║   ██║██╔██╗ ██║██║  ███╗███████╗   ██║   █████╗  ██╔██╗ ██║
   ██║   ██║   ██║██║╚██╗██║██║   ██║╚════██║   ██║   ██╔══╝  ██║╚██╗██║
   ██║   ╚██████╔╝██║ ╚████║╚██████╔╝███████║   ██║   ███████╗██║ ╚████║
   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝
                                                                        

"""

DEFAULT_MODEL_MODULE = "tungsten_model"
DEFAULT_TUNGSTEN_SERVER_URL = "https://server.tungsten-ai.com"

DATA_DIR = Path(os.getenv("TUNGSTEN_DATA_DIR", Path.home() / ".tungsten"))
DATA_DIR = DATA_DIR.resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOCK_DIR = Path(tempfile.gettempdir()) / "tungsten" / "locks"
LOCK_DIR.mkdir(parents=True, exist_ok=True)

WORKING_DIR_IN_CONTAINER = PurePosixPath("/tungsten")
TUNGSTEN_DIR_IN_CONTAINER = PurePosixPath("/etc/tungsten")

MAX_SIZE_EACH_EXAMPLE_INPUT_FILE_MB = 50
MAX_SIZE_ALL_EXAMPLE_INPUTS_MB = 512
MAX_SIZE_STORED_SOURCE_FILE_MB = 5

MIN_PYTHON_VER_FOR_TUNGSTENKIT = Version("3.7")
