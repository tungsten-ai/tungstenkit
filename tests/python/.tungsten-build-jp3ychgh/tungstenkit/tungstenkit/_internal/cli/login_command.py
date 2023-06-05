import re

import click
from furl import furl

from tungstenkit._internal.configs import TungstenClientConfig
from tungstenkit._internal.constants import DEFAULT_TUNGSTEN_SERVER_URL
from tungstenkit._internal.tungsten_clients import TungstenAPIClient, TungstenClient

from .options import common_options


def _check_email(email: str):
    return bool(re.findall(r"^\w+[@]\w+[.]\w+$", email))


def _check_username(username: str):
    return bool(re.findall(r"^\w+$", username))


def _validate_user(ctx, param, user: str):
    if not _check_username(user) and not _check_email(user):
        raise click.BadOptionUsage(
            option_name="--user",
            message=f'Invalid user "{user}": Should be either username or email.',
        )
    return user


def _validate_url(ctx, param, url: str):
    try:
        parsed = furl(url)
    except Exception:
        raise click.BadArgumentUsage(f"Invalid http(s) url: {url}")
    if not parsed.scheme or parsed.scheme not in url:
        raise click.BadArgumentUsage(f"Invalid http(s) url: {url}")
    return url


@click.command(
    help=(
        "Login to a Tungsten server\n\n"
        "SERVER should be an http(s) url\n"
        f"(Default: {DEFAULT_TUNGSTEN_SERVER_URL})"
    )
)
@click.argument(
    "server",
    default=DEFAULT_TUNGSTEN_SERVER_URL,
    envvar="TUNGSTEN_SERVER_URL",
    callback=_validate_url,
)
@click.option(
    "--user",
    "-u",
    prompt="User (username or email)",
    envvar="TUNGSTEN_USER",
    help="Username",
    show_envvar=True,
    callback=_validate_user,
)
@click.option(
    "--password",
    "-p",
    prompt="Password",
    envvar="TUNGSTEN_PASSWORD",
    help="Password",
    hide_input=True,
)
@common_options
def login(server: str, user: str, password: str, **kwargs):
    api = TungstenAPIClient(base_url=server)
    token = api.get_access_token(user, password)
    user_info = api.get_current_user()
    # TODO expire
    config = TungstenClientConfig(
        url=server,  # type: ignore
        access_token=token.access_token,
    )
    config.save()

    client = TungstenClient(url=config.url, access_token=config.access_token)
    client._login_to_docker_registry(
        auth_config={"username": user_info.username, "password": password}
    )
    click.echo("Login Success!")
