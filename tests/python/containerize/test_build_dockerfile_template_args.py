from tungstenkit._internal.configs import BuildConfig
from tungstenkit._internal.containerize.dockerfile_generators import BaseDockerfileGenerator
from tungstenkit._internal.utils.context import change_workingdir
from tungstenkit._versions import py_version


class TestDockerfile(BaseDockerfileGenerator):
    @classmethod
    def python_entrypoint(cls) -> str:
        return "python"


def test_dockerfile_template_args_without_gpu_pkgs(tmp_path):
    config = BuildConfig(gpu=False, python_packages=["requests", "urllib3==2.0.2"])
    dockerfile = TestDockerfile(config)
    args = dockerfile._build_template_args(
        tmp_path / "requirements.txt", [], tmp_path / "small_files"
    )
    base_image = args.image
    with change_workingdir(tmp_path):
        requirements_txt = args.pip_requirements_txt_in_build_ctx.read_text().split("\n")
    assert "requests" in requirements_txt
    assert "urllib3==2.0.2" in requirements_txt
    assert args.device == "cpu"
    assert base_image.type() == "python"
    assert base_image.get_tag().startswith(f"{py_version.major}.{py_version.minor}")


def test_dockerfile_template_args_given_python_version(tmp_path):
    config = BuildConfig(gpu=False, python_packages=["requests"], python_version="3.7")
    dockerfile = TestDockerfile(config)
    args = dockerfile._build_template_args(
        tmp_path / "requirements.txt", [], tmp_path / "small_files"
    )
    base_image = args.image
    assert args.device == "cpu"
    assert base_image.type() == "python"
    assert base_image.get_tag().startswith("3.7")


def test_dockerfile_template_args_given_cuda_version(tmp_path):
    config = BuildConfig(gpu=True, cuda_version="11.6")
    dockerfile = TestDockerfile(config)
    args = dockerfile._build_template_args(
        tmp_path / "requirements.txt", [], tmp_path / "small_files"
    )
    base_image = args.image
    assert args.device == "gpu"
    assert base_image.type() == "cuda"
    assert base_image.get_tag().startswith("11.6")


def test_dockerfile_template_args_with_torch_cpu(tmp_path):
    config = BuildConfig(gpu=False, python_packages=["torch==1.13.0"])
    dockerfile = TestDockerfile(config)
    args = dockerfile._build_template_args(
        tmp_path / "requirements.txt", [], tmp_path / "small_files"
    )
    base_image = args.image
    pip_install_args = args.list_pip_install_args[0]
    assert pip_install_args[0] == "torch==1.13.0+cpu"
    assert pip_install_args[1] == "--extra-index-url"
    assert pip_install_args[2] == "https://download.pytorch.org/whl/cpu"
    assert args.device == "cpu"
    assert base_image.type() == "python"
    assert base_image.get_tag().startswith(f"{py_version.major}.{py_version.minor}")


def test_dockerfile_template_args_with_tf_cpu(tmp_path):
    config = BuildConfig(gpu=False, python_packages=["tensorflow==2.11.0"])
    dockerfile = TestDockerfile(config)
    args = dockerfile._build_template_args(
        tmp_path / "requirements.txt", [], tmp_path / "small_files"
    )
    base_image = args.image
    pip_install_args = args.list_pip_install_args[0]
    assert pip_install_args[0] == "tensorflow==2.11.0"
    assert args.device == "cpu"
    assert base_image.type() == "python"
    assert base_image.get_tag().startswith(f"{py_version.major}.{py_version.minor}")


def test_dockerfile_template_args_with_torch_gpu(tmp_path):
    config = BuildConfig(gpu=True, python_packages=["torch==1.13.0"])
    dockerfile = TestDockerfile(config)
    args = dockerfile._build_template_args(
        tmp_path / "requirements.txt", [], tmp_path / "small_files"
    )
    base_image = args.image
    pip_install_args = args.list_pip_install_args[0]
    assert pip_install_args[0].startswith("torch==1.13.0+cu")
    assert pip_install_args[1] == "--extra-index-url"
    assert pip_install_args[2].startswith("https://download.pytorch.org/whl/cu")
    assert base_image.type() == "cuda"
    assert args.device == "gpu"


def test_dockerfile_template_args_with_tf_gpu(tmp_path):
    config = BuildConfig(gpu=True, python_packages=["tensorflow==2.11.0"])
    dockerfile = TestDockerfile(config)
    args = dockerfile._build_template_args(
        tmp_path / "requirements.txt", [], tmp_path / "small_files"
    )
    base_image = args.image
    pip_install_args = args.list_pip_install_args[0]
    assert pip_install_args[0] == "tensorflow==2.11.0"
    assert args.device == "gpu"
    assert base_image.type() == "cuda"
