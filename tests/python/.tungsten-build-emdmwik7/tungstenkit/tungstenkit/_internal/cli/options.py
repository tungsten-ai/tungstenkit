import functools
import logging
import sys

import click

from tungstenkit._internal.logging import init_logger


def common_options(f):
    options = [
        click.option(
            "--debug",
            is_flag=True,
            default=False,
            help="Show logs for debugging.",
            callback=_debug_flag_callback,
        ),
    ]
    return functools.reduce(lambda x, opt: opt(x), options, f)


def _debug_flag_callback(ctx, param, debug: bool):
    logging.getLogger("urllib3").setLevel(logging.INFO)
    if debug:
        init_logger("DEBUG")
        sys.excepthook = sys.__excepthook__
    else:
        init_logger("INFO")
