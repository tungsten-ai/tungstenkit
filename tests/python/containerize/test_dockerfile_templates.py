import itertools
import os
import subprocess
import typing as t
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import docker
import jinja2
import pytest
from docker.errors import ImageNotFound
from packaging.version import Version

from tungstenkit._internal.containerize.dockerfiles import base_dockerfile
from tungstenkit._internal.utils.context import change_workingdir

UBUNTU_VERSIONS = ["18.04", "20.04", "22.04"]
PYTHON_VERSIONS = [f"3.{minor}" for minor in range(7, 12)]
DOCKERFILE_HEADER = """
FROM library/ubuntu:{ubuntu_version}
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive
"""


@pytest.mark.parametrize("py_ver,ubuntu_ver", itertools.product(PYTHON_VERSIONS, UBUNTU_VERSIONS))
def test_dockerfile_template_installing_python(
    tmp_path_factory: pytest.TempdirFactory, py_ver: str, ubuntu_ver: str
):
    print(f"Dockerfile for installing Python {py_ver} on Ubuntu {ubuntu_ver}:")
    j2_env = _build_jinja2_env()
    dockerfile_content = f"""
FROM library/ubuntu:{ubuntu_ver}
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked apt-get update
"""
    install_python_template = j2_env.get_template(name="install_python.j2")
    dockerfile_content += "\n" + install_python_template.render(python_version=Version(py_ver))
    dockerfile_content += """
CMD ["/bin/bash"]
"""
    print(dockerfile_content)
    build_dir = tmp_path_factory.mktemp(f"build-ubuntu{ubuntu_ver}-py3{py_ver}")
    with _build_docker_image(
        build_dir=build_dir, dockerfile_content=dockerfile_content
    ) as image_name:
        output = _run_command_in_container(image_name, command="python --version")
        assert output.startswith(f"Python {py_ver}")

    print("Done!\n")


def _build_jinja2_env():
    return jinja2.Environment(
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols", "jinja2.ext.debug"],
        trim_blocks=True,
        lstrip_blocks=True,
        loader=jinja2.FileSystemLoader(
            Path(base_dockerfile.__file__).parent / "templates", followlinks=True
        ),
    )


@contextmanager
def _build_docker_image(
    build_dir: Path, dockerfile_content: str, image_name: t.Optional[str] = None
) -> t.Generator[str, None, None]:
    image_name = image_name if image_name else "tungstenkit-test:" + uuid4().hex
    client = docker.from_env()
    with change_workingdir(build_dir):
        dockerfile_path = build_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        env = os.environ.copy()
        env["DOCKER_BUILDKIT"] = "1"

        subprocess_args = ["docker", "build", ".", "-t", image_name]
        try:
            subprocess.run(
                subprocess_args,
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            yield image_name
        finally:
            try:
                im = client.images.get(image_name)
                im.remove(force=True)
            except ImageNotFound:
                pass


def _run_command_in_container(image_name: str, command: str):
    subprocess_args = ["docker", "run", "--rm", image_name]
    subprocess_args.extend(command.split(" "))
    return subprocess.check_output(subprocess_args, encoding="utf-8", stderr=subprocess.PIPE)
