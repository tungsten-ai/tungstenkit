import inspect
import typing as t
from pathlib import Path

from tungstenkit._internal import storables
from tungstenkit._internal.constants import DEFAULT_MODEL_MODULE, default_model_repo
from tungstenkit._internal.model_def_loader import create_model_def_loader
from tungstenkit._internal.utils.context import change_syspath, change_workingdir
from tungstenkit._internal.utils.docker import parse_docker_image_name

from .build_context import setup_build_ctx
from .dockerfiles import ModelDockerfile

if t.TYPE_CHECKING:
    from _typeshed import StrPath


def build_model(
    build_dir: "StrPath" = ".",
    module_ref: str = DEFAULT_MODEL_MODULE,
    class_name: t.Optional[str] = None,
    copy_files: t.Optional[t.List[t.Tuple[str, str]]] = None,
    name: t.Optional[str] = None,
) -> storables.ModelData:
    abs_path_to_build_dir = Path(build_dir).resolve()
    with change_syspath(build_dir):
        with change_workingdir(abs_path_to_build_dir):
            # Load model definition
            model_loader = create_model_def_loader(module_ref, class_name, lazy_import=True)
            input_schema = model_loader.input_class.schema()
            output_schema = model_loader.output_class.schema()
            demo_output_schema = model_loader.demo_output_class.schema()
            model_config = model_loader.config
            model_class = model_loader.model_class
            if copy_files is not None:
                model_config.copy_files.extend(copy_files)

            model_module_path = Path(inspect.getfile(model_class)).resolve()
            dockerfile_generator = ModelDockerfile(config=model_config)
            with setup_build_ctx(
                build_config=model_config,
                build_dir=abs_path_to_build_dir,
                module_path=model_module_path,
                dockerfile_generator=dockerfile_generator,
            ) as build_ctx:
                # Determine the model name
                model_name = default_model_repo() if name is None else name
                repo_name, tag = parse_docker_image_name(model_name)
                id = None
                if tag is None:
                    tag = storables.ModelData.generate_id()
                    id = tag
                model_name = f"{repo_name}:{tag}"

                # Build
                names = [model_name] if tag == "latest" else [model_name, f"{repo_name}:latest"]
                build_ctx.build(tags=names)

                # Add to the local store
                io_schema = storables.ModelIOData(
                    input_schema=input_schema,
                    output_schema=output_schema,
                    demo_output_schema=demo_output_schema,
                    input_filetypes=model_config.input_filetypes,
                    output_filetypes=model_config.output_filetypes,
                    demo_output_filetypes=model_config.demo_output_filetypes,
                )
                avatar = storables.AvatarData.fetch_default(hash_key=model_name)
                if model_config.readme_md:
                    readme = storables.MarkdownData.from_path(model_config.readme_md)
                else:
                    readme = None

                for name in names:
                    model_data = storables.ModelData(
                        name=name,
                        io_data=io_schema,
                        avatar=avatar,
                        readme=readme,
                        id=id,
                        source_files=build_ctx.walk_fs(),
                    )
                    model_data.save()
                return storables.ModelData.load(model_name)
