import os
import sys

import click
import urllib3

from tungstenkit._internal.logging import init_logger, log_exception
from tungstenkit._internal.utils.context import hide_traceback
from tungstenkit._internal.utils.docker import check_if_docker_available
from tungstenkit._versions import pkg_version

from .login_command import login
from .model_commands import list_models, model
from .options import common_options


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(
    str(pkg_version),
    prog_name="tungstenkit",
)
@common_options
def cli(**kwargs):
    # TODO link to docs
    """
    Command line tool for Tungsten entities.
    """
    with hide_traceback():
        check_if_docker_available()


def main():
    # TODO remove this
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    sys.excepthook = _excepthook
    sys.path.append(os.getcwd())
    init_logger("INFO")

    # TODO Split management commands like 'model' and 'task' in the help message
    cli.add_command(login, "login")
    cli.add_command(model, "model")
    for name, cmd in model.commands.items():
        if name == list_models.name:
            cli.add_command(cmd, "models")
        else:
            cli.add_command(cmd, name)
    cli()


def _excepthook(exctype, value, tb):
    log_exception(exctype=exctype, exc=value, tb=tb, show_tungsten_exc_tb=False)
