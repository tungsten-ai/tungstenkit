import os
import re
import tempfile
from pathlib import Path, PurePosixPath

from appdirs import AppDirs
from packaging.version import Version

appdirs = AppDirs(appname="tungstenkit", appauthor="tungsten")


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
DEFAULT_TUNGSTEN_SERVER_URL = "https://api.tungsten-ai.com"

DATA_DIR = Path(os.getenv("TUNGSTEN_DATA_DIR", Path(appdirs.user_data_dir)))
DATA_DIR = DATA_DIR.resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_DIR = Path(os.getenv("TUNGSTEN_CONFIG_DIR", Path(appdirs.user_config_dir)))
CONFIG_DIR = CONFIG_DIR.resolve()
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

LOCK_DIR = Path(tempfile.gettempdir()) / "tungsten" / "locks"
LOCK_DIR.mkdir(parents=True, exist_ok=True)

TUNGSTEN_DIR_IN_CONTAINER = PurePosixPath("/etc/tungsten")
WORKING_DIR_IN_CONTAINER = PurePosixPath("/tungsten")

MIN_SUPPORTED_PYTHON_VER = Version("3.7")
MAX_SUPPORTED_PYTHON_VER = Version("3.11")
MAX_SOURCE_FILE_SIZE = 10 * 1024 * 1024
