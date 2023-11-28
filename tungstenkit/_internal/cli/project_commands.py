import click

from tungstenkit._internal.tungsten_clients import TungstenClient

from .callbacks import project_slug_validator
from .options import common_options


@click.group()
@common_options
def project(**kwargs):
    """
    Run project commands
    """
    pass


@project.command()
@click.argument("name", type=str, callback=project_slug_validator)
@click.option(
    "--description",
    "-d",
    help="Project discription",
    type=str,
    default=None,
    show_default=False,
)
@click.option(
    "--nsfw",
    help="NSFW flag",
    is_flag=True,
    default=False,
    show_default=False,
)
@click.option(
    "--private",
    help="Private project flag",
    is_flag=True,
    default=False,
    show_default=False,
)
@click.option(
    "--exists-ok",
    help="Skip raising error when conflicted",
    is_flag=True,
    default=False,
    show_default=False,
)
@common_options
def create(name: str, description: str, nsfw: bool, private: bool, exists_ok: bool, **kwargs):
    """
    Create a project
    """
    client = TungstenClient.from_env()
    if client.create_project(
        name, description=description, nsfw=nsfw, private=private, exists_ok=exists_ok
    ):
        click.echo(f"Project '{client.username}/{name}'sucessfully created")
