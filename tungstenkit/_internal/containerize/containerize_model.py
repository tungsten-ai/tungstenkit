import inspect
import sys
import typing as t
from pathlib import Path

from rich.prompt import Confirm

from tungstenkit import exceptions
from tungstenkit._internal import model_store, storables
from tungstenkit._internal.constants import DEFAULT_MODEL_MODULE, default_model_repo
from tungstenkit._internal.model_def_loader import create_model_def_loader
from tungstenkit._internal.utils.context import change_syspath, change_workingdir
from tungstenkit._internal.utils.docker_client import parse_docker_image_name

from .build_context import BuildContext

if t.TYPE_CHECKING:
    from _typeshed import StrPath


def containerize_model(
    build_dir: "StrPath" = ".",
    module_ref: str = DEFAULT_MODEL_MODULE,
    class_name: t.Optional[str] = None,
    copy_files: t.Optional[t.List[t.Tuple[str, str]]] = None,
    name: t.Optional[str] = None,
) -> storables.ModelData:
    abs_path_to_build_dir = Path(build_dir).resolve()
    with change_syspath(build_dir):
        with change_workingdir(abs_path_to_build_dir):
            # Determine the model name
            model_name = default_model_repo() if name is None else name
            repo_name, tag = parse_docker_image_name(model_name)

            # Generate model id
            existing_model_data = None
            try:
                if tag:
                    existing_model_data = model_store.get(model_name)
                    id = existing_model_data.id
                else:
                    id = storables.ModelData.generate_id()
            except exceptions.ModelNotFound:
                id = storables.ModelData.generate_id()

            # Handle duplication
            if existing_model_data:
                update_existing_data = Confirm.ask(
                    f"Model '{existing_model_data.name}' already exists. Remove and replace it?"
                )
                if update_existing_data:
                    model_store.delete(existing_model_data.name)
                else:
                    sys.exit(0)

            # Set tag if not set
            if tag is None:
                tag = id[:7]
            model_name = f"{repo_name}:{tag}"

            # Load model definition
            model_loader = create_model_def_loader(module_ref, class_name, lazy_import=True)
            input_schema = model_loader.input_class.schema()
            output_schema = model_loader.output_class.schema()
            demo_output_schema = model_loader.demo_output_class.schema()
            model_build_config = model_loader.build_config
            model_class = model_loader.model_class
            if copy_files is not None:
                model_build_config.copy_files.extend(copy_files)

            model_module_path = Path(inspect.getfile(model_class)).resolve()
            with BuildContext(
                build_config=model_build_config,
                abs_path_to_build_dir=abs_path_to_build_dir,
                abs_path_to_tungsten_module=model_module_path,
            ) as build_ctx:
                # Build
                build_ctx.build(tag=model_name)

                # Add to the local store
                io_schema = storables.ModelIOData(
                    input_schema=input_schema,
                    output_schema=output_schema,
                    demo_output_schema=demo_output_schema,
                    input_filetypes=model_build_config.input_filetypes,
                    output_filetypes=model_build_config.output_filetypes,
                    demo_output_filetypes=model_build_config.demo_output_filetypes,
                )
                avatar = storables.AvatarData.fetch_default(hash_key=model_name)
                if model_build_config.readme_md:
                    readme = storables.MarkdownData.from_path(model_build_config.readme_md)
                else:
                    readme = None

                model_data = storables.ModelData(
                    name=model_name,
                    io_data=io_schema,
                    avatar=avatar,
                    readme=readme,
                    id=id,
                )
                model_data.save()
                return storables.ModelData.load(model_name)
