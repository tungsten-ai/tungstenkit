import tempfile
import typing as t
from pathlib import Path

import attrs

from tungstenkit._internal.blob_store import Blob, BlobStorable, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.utils.markdown import (
    change_img_links_in_markdown,
    change_local_image_links_in_markdown,
    get_image_links,
    get_local_image_paths,
    resolve_local_image_paths,
)
from tungstenkit._internal.utils.requests import download_files_in_threadpool


@attrs.frozen(kw_only=True)
class StoredMarkdown:
    markdown: Blob
    images: t.List[Blob] = attrs.field(factory=list)


@attrs.frozen(kw_only=True)
class MarkdownData(BlobStorable[StoredMarkdown]):
    content: str
    image_files: t.List[Path] = attrs.field(factory=list)
    base_dir: t.Optional[Path] = None

    def save_blobs(
        self,
        blob_store: BlobStore,
        file_blob_create_policy: FileBlobCreatePolicy = "copy",
    ) -> StoredMarkdown:
        with tempfile.TemporaryDirectory() as download_dir_str:
            # Download remote image files
            download_dir = Path(download_dir_str)
            to_be_downloaded = get_image_links(md=self.content, schemes=["http", "https"])
            downloaded = download_files_in_threadpool(*to_be_downloaded, out=download_dir)
            content = change_img_links_in_markdown(
                md=self.content, images=to_be_downloaded, updates=[p.as_uri() for p in downloaded]
            )

            # Store image files to the blob store
            image_files = get_local_image_paths(content, base_dir=self.base_dir, resolve=True)

            if file_blob_create_policy == "copy":
                image_blobs = blob_store.add_multiple_by_writing(*image_files)
            else:
                image_blobs = [blob_store.add_by_renaming(f) for f in image_files]

            # Replace image links with blob paths
            stored_image_files = [b.file_path for b in image_blobs]
            content = change_local_image_links_in_markdown(
                content,
                image_files,
                [f.as_uri() for f in stored_image_files],
                resolve=True,
                base_dir=self.base_dir,
            )

            # Save markdown as a blob
            blob = blob_store.add_by_writing((content.encode("utf-8"), "README.md"))

            return StoredMarkdown(markdown=blob, images=image_blobs)

    @staticmethod
    def load_blobs(stored: StoredMarkdown) -> "MarkdownData":
        return MarkdownData(
            content=stored.markdown.file_path.read_text(),
            image_files=[b.file_path for b in stored.images],
        )

    @staticmethod
    def from_path(path: Path) -> "MarkdownData":
        base_dir = path.parent
        content = path.read_text()
        content = resolve_local_image_paths(content, base_dir)
        image_files = get_local_image_paths(content, base_dir=base_dir, resolve=True)
        content = change_local_image_links_in_markdown(
            content,
            image_files,
            [f.as_uri() for f in image_files],
            resolve=True,
            base_dir=base_dir,
        )
        return MarkdownData(content=content, image_files=image_files, base_dir=base_dir)
