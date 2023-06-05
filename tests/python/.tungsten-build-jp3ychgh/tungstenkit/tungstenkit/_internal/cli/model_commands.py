import json
import tempfile
import typing as t
from datetime import timezone
from pathlib import Path

import click
import uvicorn
from fastapi.encoders import jsonable_encoder
from tabulate import tabulate

from tungstenkit._internal import model_store
from tungstenkit._internal.constants import (
    DEFAULT_MODEL_MODULE,
    TUNGSTEN_DIR_IN_CONTAINER,
    TUNGSTEN_LOGO,
)
from tungstenkit._internal.containerize import build_model
from tungstenkit._internal.containers import start_model_container
from tungstenkit._internal.demo_server import create_demo_app
from tungstenkit._internal.pred_interface.local_interface import LocalModel
from tungstenkit._internal.utils import docker

# from tungstenkit._internal.tungsten_clients import TungstenClient
from tungstenkit._internal.utils.console import print_pretty, print_success, yes_or_no_prompt
from tungstenkit._internal.utils.string import removeprefix

from .callbacks import (  # project_name_callback,; remote_model_name_callback,
    input_fields_callback,
    model_name_validator,
    stored_model_name_callback,
)
from .options import common_options


@click.group(hidden=True)
@common_options
def model(**kwargs):
    """
    Run model commands
    """
    pass


@model.command()
@click.argument(
    "dir",
    default=".",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
@click.option(
    "--name",
    "-n",
    help="Name of the model in '<repo name>[:<tag>]' format",
    callback=model_name_validator,
)
@click.option(
    "--model-module",
    "-m",
    help="Model module (e.g., some.example.module)",
    default=DEFAULT_MODEL_MODULE,
    show_default=True,
)
@click.option(
    "--model-class",
    "-c",
    type=str,
    default=None,
    help="Model class (e.g., MyModel)",
)
@click.option(
    "--copy-files",
    help="Copy files to the container (format: <src in host>:<dest in container>)",
    multiple=True,
)
@common_options
def build(
    dir: str,
    name: t.Optional[str],
    model_module: str,
    model_class: t.Optional[str],
    copy_files: t.Iterable[str],
    **kwargs,
):
    """
    Build a docker image of a tungsten model

    DIR: Build root directory
    (default: '.')
    """

    _copy_files: t.List[t.Tuple[str, str]] = []
    for f in copy_files:
        if ":" in f:
            splitted = f.split(":", maxsplit=1)
            _copy_files.append((splitted[0], splitted[1]))
        else:
            raise click.BadOptionUsage(
                "--copy_files",
                message=f"'{f}' is not in the format of '<src_in_host>:<dest_in_container>'",
            )

    # Start to build
    print(TUNGSTEN_LOGO)
    model_data = build_model(
        module_ref=model_module,
        class_name=model_class,
        copy_files=_copy_files,
        name=name,
        build_dir=dir,
    )
    print()
    success_msg = f"Successfully built tungsten model: '{model_data.repo_name}:{model_data.tag}' "
    if model_data.tag != "latest":
        success_msg += f"(also tagged as '{model_data.repo_name}:latest')"
    print_success(success_msg)
    print("\n- Run demo service:")
    print_pretty(f"  $ tungsten demo [green]{model_data.repo_name}:latest[/green]")
    print("\n- Run prediction service:")
    print_pretty(f"  $ tungsten serve [green]{model_data.repo_name}:latest[/green]")


@model.command()
@click.argument("model_name", default="", callback=stored_model_name_callback)
@click.option("--host", default="localhost", help="The host on which the demo server will listen")
@click.option(
    "--port", "-p", default=3300, help="The port on which the demo server will listen", type=int
)
@common_options
def demo(model_name: str, host: str, port: int, **kwargs):
    """
    Start a demo service for a model

    \b
    'MODEL_NAME' should be in the '<repo name>[:<tag>]' format.
    If not set, the latest model is selected.
    """
    print_pretty(f"Start demo for model '{model_name}'\n")

    model = model_store.get(model_name)

    # Start demo app
    # NOTE We create tempdir in current directory since docker desktop doesn't allow
    # to bind host dirs outside the user home directory
    with tempfile.TemporaryDirectory(
        prefix=".tungsten-container-volume-",
        dir=".",
    ) as container_tmp_dir:
        with start_model_container(model, bind_dir_in_host=Path(container_tmp_dir)) as container:
            with tempfile.TemporaryDirectory() as server_tmp_dir:
                app = create_demo_app(
                    model_container=container,
                    tmp_dir=Path(server_tmp_dir),
                )
                print(TUNGSTEN_LOGO)
                uvicorn.run(app, host=host, port=port)


@model.command()
@common_options
def list_models(**kwargs):
    """
    List models
    """
    table_headers = [
        "Repository",
        "Tag",
        "Description",
        "Model Class",
        "Created",
        "Docker Image ID",
    ]
    table = []
    for m in model_store.list():
        table.append(
            [
                m.repo_name,
                m.tag,
                m.description,
                f"{m.module_name}:{m.class_name}",
                m.created_at.replace(tzinfo=timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
                f"{removeprefix(m.docker_image_id, 'sha256:')[:12]}",
            ]
        )
    # TODO sort table (repo_name -> latest tag first -> created)
    print(tabulate(table, headers=table_headers))


@model.command()
@click.argument("model_name", type=str)
@common_options
def remove(model_name: str, **kwargs):
    """
    Remove a model

    'MODEL_NAME' should be in the '<repo name>[:<tag>]' format
    """
    model_store.delete(model_name)
    print_pretty(f"Removed: '{model_name}'")


@model.command()
@click.argument("repo_name", default="")
@common_options
def clear(repo_name: str, **kwargs):
    """
    Remove all models in a repository

    If 'REPO_NAME' is not set, try to remove all models.
    """
    if not repo_name and not yes_or_no_prompt("Remove all models?"):
        return

    removed_model_names = model_store.clear_repo(repo_name if repo_name else None)
    if len(removed_model_names) == 0:
        return

    print_pretty("Removed: " + ", ".join([f"'{n}'" for n in removed_model_names]))


@model.command
@click.argument("model_name", default="", callback=stored_model_name_callback)
@click.option("--port", "-p", default=3000, type=int)
@click.option("--batch-size", default=None, type=int, help="Max batch size for adaptive batching")
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(["trace", "debug", "info", "warning", "error"], case_sensitive=False),
    help="Log level",
    show_default=True,
    callback=lambda _, __, v: v.upper(),
)
@common_options
def serve(model_name: str, port: int, batch_size: t.Optional[int], log_level: str, **kwargs):
    """
    Start a prediction service for a model

    \b
    'MODEL_NAME' should be in the '<repo name>[:<tag>]' format.
    If not set, the latest model is selected.
    """
    model_data = model_store.get(model_name)
    docker_run_args = [
        "-it",
        "--rm",
        "-p",
        f"{port}:{port}",
    ]
    if model_data.gpu:
        docker_run_args += ["--gpus", "all"]
    docker_run_args += [
        model_data.docker_image_id,
    ]

    model_container_args = [
        "--http-port",
        str(port),
        "--log-level",
        log_level,
    ]
    if batch_size:
        docker_run_args += ["--batch-size", str(batch_size)]
    print(TUNGSTEN_LOGO)
    docker.run(*(docker_run_args + model_container_args))


@model.command()
@click.argument("model_name", default="", callback=stored_model_name_callback)
@click.option(
    "--input",
    "-i",
    multiple=True,
    help="Input field in the format of '<name>=<value>''",
    callback=input_fields_callback,
)
@click.option(
    "--output-file-dir",
    default=".",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
)
@common_options
def predict(model_name: str, input: t.Iterable[t.Tuple[str, str]], output_file_dir: str, **kwargs):
    """
    Run a prediction with a model

    'MODEL_NAME' should be in the '<repo name>[:<tag>]' format
    """
    model = LocalModel(model_name)
    output = model.predict(
        {field[0]: field[1] for field in input},
        output_file_dir=output_file_dir,
    )
    print(json.dumps(jsonable_encoder(output), indent=2))


@model.command()
@click.argument("model_name", default="", callback=stored_model_name_callback)
@click.option(
    "--save_dir",
    "-d",
    default=".",
    show_default=True,
    type=click.Path(exists=True, dir_okay=True, file_okay=False, writable=True),
    help="Directory to save files",
)
@common_options
def extract(model_name: str, save_dir: str, **kwargs):
    """
    Save model files to a directory

    'MODEL_NAME' should be in the '<repo name>[:<tag>]' format
    """
    model_data = model_store.get(model_name)
    docker.copy_from_image(
        model_data.id, TUNGSTEN_DIR_IN_CONTAINER, Path(save_dir), image_desc=model_data.name
    )


# @model.command()
# @click.argument("project", callback=project_name_callback)
# @click.option(
#     "--model-name",
#     "-n",
#     help="Name of the model in '<repo name>[:<tag>]' format",
#     callback=stored_model_name_callback,
# )
# @common_options
# def push(project: str, model_name: str, **kwargs):
#     """
#     Push a model

#     'PROJECT' should be in the '<namespace slug>/<project slug>' format
#     """
#     # TODO validate project
#     # TODO print the pushed model in server
#     tungsten_client = TungstenClient.from_env()
#     print(TUNGSTEN_LOGO)
#     tungsten_client.push_model(model_name=model_name, project=project)


# @model.command()
# @click.argument("remote_model", callback=remote_model_name_callback)
# @common_options
# def pull(remote_model: str, **kwargs):
#     """
#     Pull a model

#     'REMOTE_MODEL' should be in the '<repo name>[:<tag>]' format
#     """
#     project, version = remote_model.split(":", maxsplit=1)
#     tungsten_client = TungstenClient.from_env()
#     print(TUNGSTEN_LOGO)
#     tungsten_client.pull_model(project=project, model_version=version)