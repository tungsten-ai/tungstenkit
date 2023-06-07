import shutil

import pynvml

from tungstenkit._internal.logging import log_debug

_IS_NV_DRIVER_AVAILABLE = shutil.which("nvidia-smi") is not None

GPU_COUNT = 0
GPU_KINDS = []
GPU_MEMORY_SIZES = []

if _IS_NV_DRIVER_AVAILABLE:
    log_debug("NVIDIA GPU driver detected.")
    pynvml.nvmlInit()
    GPU_COUNT = pynvml.nvmlDeviceGetCount()
    log_debug(f"Num GPUs: {GPU_COUNT}")
    for idx in range(GPU_COUNT):
        handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
        GPU_KINDS.append(pynvml.nvmlDeviceGetName(handle))
        GPU_MEMORY_SIZES.append(pynvml.nvmlDeviceGetMemoryInfo(handle).total)


IS_GPU_AVAILABLE = _IS_NV_DRIVER_AVAILABLE and GPU_COUNT > 0
