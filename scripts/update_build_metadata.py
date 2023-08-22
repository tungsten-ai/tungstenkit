#!/usr/bin/env python3

import click

from tungstenkit._internal.containerize.base_images import BaseImageCollection
from tungstenkit._internal.containerize.gpu_pkg_collections import GPUPackageCollection
from tungstenkit._internal.containerize.metadata import (
    BASE_IMAGE_METADATA_DIR,
    GPU_PKG_METADATA_DIR,
    build_base_image_metadata_json_path,
    build_gpu_pkg_metadata_json_path,
)
from tungstenkit._internal.utils.serialize import save_attrs_as_json

# TODO multithreading


def update_base_image_metadata():
    for cls in BaseImageCollection.__subclasses__():
        typename = cls.typename()
        collection = cls.from_remote()
        BASE_IMAGE_METADATA_DIR.mkdir(exist_ok=True, parents=True)

        print(f"Updating {typename} base image metadata")
        save_attrs_as_json(collection, build_base_image_metadata_json_path(typename))
        print("Done", end="\n\n")


def update_gpu_package_metadata():
    for cls in GPUPackageCollection.__subclasses__():
        typename = cls.typename()
        collection = cls.from_remote()
        GPU_PKG_METADATA_DIR.mkdir(exist_ok=True, parents=True)

        print(f"Updating {typename} package metadata")
        save_attrs_as_json(collection, build_gpu_pkg_metadata_json_path(typename))
        print("Done", end="\n\n")


@click.command()
def update_build_metadata():
    """Update metadata of docker base images and GPU packages like torch and tensorflow"""
    update_base_image_metadata()
    update_gpu_package_metadata()


if __name__ == "__main__":
    update_build_metadata()
