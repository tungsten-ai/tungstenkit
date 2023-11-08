from pathlib import Path

from tungstenkit._internal.containerize.build_context import BuildContext
from tungstenkit._internal.model_def_loader import create_model_def_loader

from ..dummy_model import DUMMY_MODEL_BUILD_DIR, DUMMY_MODEL_MODULE_PATH, DummyModel

model_def_loader = create_model_def_loader(DummyModel.__module__, DummyModel.__name__)
model_build_config = model_def_loader.build_config


def test_copy_small_files_and_symlinks():
    with BuildContext(
        build_config=model_build_config,
        abs_path_to_build_dir=DUMMY_MODEL_BUILD_DIR,
        abs_path_to_tungsten_module=DUMMY_MODEL_MODULE_PATH,
    ) as build_ctx:
        content = "hello world"
        dummy_small_file_path = (
            build_ctx.abs_path_to_build_dir
            / build_ctx._rel_path_to_small_files_dir
            / "dummy_model_data"
            / "somedir"
            / "somefile"
        )
        symlink_rel_path = (
            build_ctx.abs_path_to_build_dir
            / build_ctx._rel_path_to_small_files_dir
            / "dummy_model_data"
            / "somedir"
            / "symlink_rel"
        )
        symlink_abs_in_build_dir_path = (
            build_ctx.abs_path_to_build_dir
            / build_ctx._rel_path_to_small_files_dir
            / "dummy_model_data"
            / "somedir"
            / "symlink_abs_in_build_dir"
        )

        assert dummy_small_file_path.read_text() == content
        assert symlink_rel_path.read_text() == content
        assert symlink_abs_in_build_dir_path.read_text() == content

        assert len(model_build_config.copy_files) == 1
        assert (
            build_ctx.abs_path_to_build_dir / Path(model_build_config.copy_files[0][0])
        ).read_text() == content
        assert Path(model_build_config.copy_files[0][1]) == Path(
            "dummy_model_data", "somedir", "symlink_abs_outside_build_dir"
        )
