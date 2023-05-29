import logging
import traceback
import typing as t
from typing import Any, Dict

from rich.logging import RichHandler

from tungstenkit.exceptions import TungstenException

if t.TYPE_CHECKING:
    from types import TracebackType

LOG_LEVELS = ["trace", "debug", "info", "warning", "error"]
FORMAT = "%(message)s"


logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(level="INFO", show_level=False, show_path=False, show_time=False)],
)
logger = logging.getLogger("rich")


def init_logger(level: str):
    global logger

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=level,
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler(level=level, show_level=False, show_path=False, show_time=False)],
    )
    logger = logging.getLogger("rich")


def log_info(msg: str, pretty: bool = True):
    global logger
    extras: Dict[str, Any] = {"markup": pretty}
    if not pretty:
        extras["highlighter"] = None
    logger.info(msg, extra=extras)


def log_debug(msg: str, pretty: bool = True):
    global logger
    extras: Dict[str, Any] = {"markup": pretty}
    if not pretty:
        extras["highlighter"] = None
    logger.debug(msg, extra=extras)


def log_warning(msg: str, format: bool = True, pretty: bool = True):
    global logger
    if format:
        if pretty:
            msg = "[bold yellow]Warning:[/bold yellow] " + msg
        else:
            msg = "Warning: " + msg

    extras: Dict[str, Any] = {"markup": pretty}
    if not pretty:
        extras["highlighter"] = None

    logger.warning(msg, extra=extras)


def log_error(msg: str, format: bool = True, pretty: bool = True):
    global logger
    if format:
        if pretty:
            msg = "[bold red]Error:[/bold red] " + msg
        else:
            msg = "Error: " + msg

    logger.error(msg, extra={"markup": pretty})


def log_exception(
    exctype: t.Type[BaseException],
    exc: BaseException,
    tb: "TracebackType",
    show_tungsten_exc_tb: bool,
):
    logger.error("")
    if not isinstance(exc, TungstenException) or show_tungsten_exc_tb:
        logger.error("Traceback:")
        formatted_tb = "".join(traceback.format_tb(tb))
        logger.error(formatted_tb, extra={"markup": False, "highlighter": None})

    displayed_cls_name = (
        exctype.__name__
        if exctype.__module__ == "builtins" or isinstance(exc, TungstenException)
        else f"{exctype.__module__}.{exctype.__name__}"
    )
    exc_msg = str(exc)
    exc_info_str = f"[bold red]{displayed_cls_name}[/bold red]"
    if exc_msg:
        exc_info_str += ": " + str(exc)
    logger.error(exc_info_str, extra={"markup": True, "highlighter": None})


def log_success(msg: str, format: bool = True, pretty: bool = True):
    if format:
        if pretty:
            msg = ":white_check_mark: " + msg
    logger.info(msg)
