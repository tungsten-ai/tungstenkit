import tempfile
import typing as t
from pathlib import Path

import attrs
from furl import furl

from tungstenkit import exceptions
from tungstenkit._internal.blob_store import Blob, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.utils.markdown import (
    apply_to_image_link_in_markdown,
    change_img_links_in_markdown,
    get_image_links,
)
from tungstenkit._internal.utils.requests import download_files_in_threadpool
from tungstenkit._internal.utils.uri import get_path_from_file_url

from .blob_container import BlobContainer


@attrs.define(kw_only=True)
class StoredMarkdownData:
    markdown: Blob
    images: t.List[Blob] = attrs.field(factory=list)


@attrs.define(kw_only=True)
class MarkdownData(BlobContainer[StoredMarkdownData]):
    content: str
    image_files: t.List[Path] = attrs.field(factory=list)

    def save_blobs(
        self,
        blob_store: BlobStore,
        file_blob_create_policy: FileBlobCreatePolicy = "copy",
    ) -> StoredMarkdownData:
        with tempfile.TemporaryDirectory() as download_dir_str:
            download_dir = Path(download_dir_str)
            content = _download_remote_images_in_readme(
                save_dir=download_dir, markdown_content=self.content
            )

            image_files = _list_image_files_in_readme(content)

            if file_blob_create_policy == "copy":
                image_blobs = blob_store.add_multiple_by_writing(*image_files)
            else:
                image_blobs = [blob_store.add_by_renaming(f) for f in image_files]

            content = _update_readme_image_files(content, image_files, image_blobs)

            blob = blob_store.add_by_writing((content.encode("utf-8"), "README.md"))
            return StoredMarkdownData(markdown=blob, images=image_blobs)

    @staticmethod
    def load_blobs(stored: StoredMarkdownData) -> "MarkdownData":
        return MarkdownData(
            content=stored.markdown.file_path.read_text(),
            image_files=[b.file_path for b in stored.images],
        )


def _download_remote_images_in_readme(save_dir: Path, markdown_content: str) -> str:
    to_be_downloaded = get_image_links(md=markdown_content, schemes=["http", "https"])
    downloaded = download_files_in_threadpool(*to_be_downloaded, download_dir=save_dir)
    return change_img_links_in_markdown(
        md=markdown_content, images=to_be_downloaded, updates=[str(p) for p in downloaded]
    )


def _list_image_files_in_readme(
    readme_content: str,
) -> t.List[Path]:
    image_set: t.Set[Path] = set()

    def add(path: str):
        parsed = furl(path)
        if parsed.scheme == "file":
            if parsed.netloc:
                raise exceptions.UnsupportedURL(
                    f"'{path}' in README: file-uri for a remote file is not supported"
                )
            pathlib_path = get_path_from_file_url(path)
        else:
            pathlib_path = Path(path)

        if pathlib_path.exists():
            resolved = pathlib_path.resolve()
            image_set.add(resolved)
            path = str(resolved)
        return path

    readme_content = apply_to_image_link_in_markdown(md=readme_content, fn=add)

    return list(image_set)


def _update_readme_image_files(
    readme_content: str,
    image_files: t.List[Path],
    image_blobs: t.List[Blob],
) -> str:
    def update(path: str):
        pathlib_path = Path(path)
        try:
            idx = image_files.index(pathlib_path)
            path = str(image_blobs[idx].file_path.resolve())
        except ValueError:
            pass

        return path

    readme_content = apply_to_image_link_in_markdown(
        md=readme_content, fn=update, ret_updated=True
    )
    return readme_content
