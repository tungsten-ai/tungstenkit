import os
import typing as t
from pathlib import Path

from rich import print as rprint

from tungstenkit import exceptions
from tungstenkit._internal import model_store
from tungstenkit._internal.constants import default_model_repo


def project_name_callback(ctx, param, project_name: str) -> str:
    slash_separated = project_name.split("/")
    if len(slash_separated) != 2:
        raise exceptions.InvalidName(
            f"Invalid project name: {project_name}\nFormat: <namespace slug>/<project slug> "
            "(e.g., exampleuser/exampleproject)"
        )
    return project_name


def remote_model_name_callback(ctx, param, model_name: str) -> str:
    format_help_msg = (
        "Format of remote model name: <namespace slug>/<project slug>:<model version>"
    )
    invalid_format_msg = f"Invalid remote model name: {model_name}\n" + format_help_msg
    colon_separated = model_name.split(":")
    if len(colon_separated) != 2:
        raise exceptions.InvalidName(invalid_format_msg)

    full_slug = colon_separated[0]
    slash_separated = full_slug.split("/")
    if len(slash_separated) != 2:
        raise exceptions.InvalidName(invalid_format_msg)

    return model_name


def stored_model_name_callback(ctx, param, model_name: t.Optional[str]) -> str:
    """
    Parse a model name or set the default.

    Raise an exception if the model is not found.
    """

    if model_name:
        try:
            m = model_store.get(model_name)
        except exceptions.NotFound:
            raise exceptions.NotFound(f"model '{model_name}'")
        return m.name

    wd = Path(os.getcwd()).resolve().parts[-1]

    try:
        default_repo = default_model_repo()
        rprint(
            f"Finding the latest model image built in the directory '{wd}' "
            f"(tag: '{default_repo}:latest')... ",
            end="",
        )

        model_store.get(f"{default_repo}:latest")
        rprint("[bold green]succeeded[/bold green]")
        return f"{default_repo}:latest"

    except exceptions.NotFound:
        rprint("[bold red]failed[/bold red]")

    # TODO prompt to request to ask whether to use the latest model or not
    rprint("Finding the latest model image... ", end="")
    models = sorted(model_store.list(), key=lambda m: m.created_at, reverse=True)

    if len(models) == 0:
        raise exceptions.NotFound("No available models. Please build or pull first.")

    m = models[0]
    for _m in models:
        if _m.id == m.id and _m.name == "latest":
            m = _m

    rprint("[bold green]succeeded[/bold green]")
    rprint(f"Use model {m.name}")
    return m.name


def input_fields_callback(ctx, param, input_fields: t.Tuple[str]) -> t.List[t.Tuple[str, str]]:
    fields = []
    for field in input_fields:
        splitted = field.split("=")
        if len(splitted) != 2:
            raise exceptions.InvalidInput("Format: <field_name>:<value>")
        fields.append((splitted[0], splitted[1]))

    return fields
