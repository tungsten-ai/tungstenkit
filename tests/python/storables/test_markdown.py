from pathlib import Path

from tungstenkit._internal.blob_store import BlobStore
from tungstenkit._internal.storables import MarkdownData


def test_markdown_data():
    # TODO symlink
    markdown_path = Path(__file__).parent.resolve() / "fixtures" / "markdown" / "markdown.md"
    image1_path = markdown_path.with_name("tungsten.png")
    image2_path = markdown_path.parent / "somedir" / "tungsten.png"
    d = MarkdownData.from_path(markdown_path)
    assert d.content.startswith(
        f"""Hello
![image1]({image1_path.as_uri()})
![image2]({image2_path.as_uri()})
"""
    )

    blob_store = BlobStore()
    stored = d.save_blobs(blob_store)
    stored_image1_path = stored.images[0].file_path
    stored_image2_path = stored.images[1].file_path

    loaded = MarkdownData.load_blobs(stored)
    assert loaded.content.startswith(
        f"""Hello
![image1]({stored_image1_path.as_uri()})
![image2]({stored_image2_path.as_uri()})
"""
    )
