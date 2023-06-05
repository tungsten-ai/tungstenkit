import atexit
import multiprocessing as mp
import os
import shutil
import sys
import tempfile

import click
import uvicorn
from loguru import logger

from .config import MODE_TO_SETTING_MAPPING
from .enums import ModelServerMode
from .http_server import create_app
from .prediction_worker import PredictionWorker


@click.command()
@click.option(
    "--http-port",
    "-p",
    default=3000,
    type=int,
    show_default=True,
    help="Port to listen http requests on",
)
@click.option(
    "--mode",
    "-m",
    default="standalone",
    type=click.Choice(
        [ModelServerMode.STANDALONE, ModelServerMode.FILE_TUNNEL], case_sensitive=False
    ),
    show_default=True,
    help="Cache type",
    callback=lambda _, __, v: ModelServerMode(v.lower()),
)
@click.option(
    "--max-batch-size",
    "-b",
    default=int(os.environ.get("TUNGSTEN_MAX_BATCH_SIZE", "1")),
    type=int,
    show_default=True,
    help="Max batch size",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(["trace", "debug", "info", "warning", "error"], case_sensitive=False),
    help="Log level",
    show_default=True,
    callback=lambda _, __, v: v.upper(),
)
def serve(
    http_port: int,
    mode: ModelServerMode,
    max_batch_size: int,
    log_level: str,
):
    """Run tungsten model server."""
    from tungstenkit._internal import contexts
    from tungstenkit._internal.io import SUPPORTED_URL_SCHEMES_FOR_FILES
    from tungstenkit._internal.model_def_loader import create_model_def_loader

    mp.set_start_method("spawn")  # For CUDA
    contexts.APP = contexts.Application.MODEL_SERVER

    path = tempfile.mkdtemp()
    tempfile.tempdir = path
    atexit.register(shutil.rmtree, path)

    logger.remove()
    logger.add(sys.stderr, level=log_level)

    if mode == ModelServerMode.FILE_TUNNEL:
        SUPPORTED_URL_SCHEMES_FOR_FILES.clear()
        SUPPORTED_URL_SCHEMES_FOR_FILES.extend(["data", "file"])

    settings = MODE_TO_SETTING_MAPPING[mode]()  # type: ignore
    # TODO Load user codes only in subprocess
    worker = PredictionWorker(
        model_def_loader=create_model_def_loader(
            settings.TUNGSTEN_MODEL_MODULE, settings.TUNGSTEN_MODEL_CLASS
        ),
        cache_config=settings.cache_config,
        storage_config=settings.storage_config,
        max_batch_size=max_batch_size,
        setup_timeout=settings.SETUP_TIMEOUT,
        prediction_timeout=settings.PREDICTION_TIMEOUT,
    )
    worker.start()
    logger.info("Setting up the model")
    worker.wait_for_setup()

    logger.info("Starting the prediction service")
    app = create_app(
        prediction_worker=worker,
        model_loader=create_model_def_loader(
            settings.TUNGSTEN_MODEL_MODULE, settings.TUNGSTEN_MODEL_CLASS
        ),
    )
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=http_port,
        workers=1,
    )
