from pathlib import Path

METADATA_DIR = Path(__file__).parent
BASE_IMAGE_METADATA_DIR = METADATA_DIR / "base_images"
GPU_PKG_METADATA_DIR = METADATA_DIR / "gpu_pkgs"
METADATA_REFRESH_INTERVAL_DAYS = 15
FILELOCK_TIMEOUT = 180.0


def build_base_image_metadata_json_path(typename: str):
    return BASE_IMAGE_METADATA_DIR / (typename + "-base-images.json")


def build_gpu_pkg_metadata_json_path(typename: str):
    return GPU_PKG_METADATA_DIR / (typename + "-packages.json")
