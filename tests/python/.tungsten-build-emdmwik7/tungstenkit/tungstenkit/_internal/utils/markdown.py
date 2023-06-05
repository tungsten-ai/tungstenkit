import typing as t
from pathlib import Path

from furl import furl
from markdown import Markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import IMAGE_LINK_RE, ImageInlineProcessor
from markdownify import markdownify

from .uri import check_if_uri_in_allowed_schemes, get_path_from_file_url


def apply_to_image_link_in_markdown(
    md: str, fn: t.Callable[[str], str], ret_updated: bool = True
) -> str:
    class _ImageInlineProcessor(ImageInlineProcessor):
        def handleMatch(self, m, data):
            el, start, index = super().handleMatch(m, data)
            if el is None:
                return el, start, index

            src = el.get("src", default="")
            if not src:
                return el, start, index

            transformed = fn(src)
            el.set("src", transformed)
            return el, start, index

    class ImageExtension(Extension):
        def extendMarkdown(self, md):
            md.inlinePatterns.register(_ImageInlineProcessor(IMAGE_LINK_RE, md), "image", 200)

    markdown = Markdown(extensions=[ImageExtension()])
    html = markdown.convert(md)
    if ret_updated:
        return markdownify(html)
    return md


def get_image_links(md: str, schemes: t.Optional[t.List[str]] = None) -> t.List[str]:
    image_links: t.List[str] = []

    def fn(img_link: str):
        if schemes is None:
            image_links.append(img_link)
        else:
            if check_if_uri_in_allowed_schemes(img_link, schemes):
                image_links.append(img_link)
        return img_link

    apply_to_image_link_in_markdown(md=md, fn=fn, ret_updated=False)
    return image_links


def get_local_image_paths(md: str) -> t.List[Path]:
    paths: t.List[Path] = list()

    def fn(img_link: str):
        f = furl(img_link)

        if f.scheme == "file":
            paths.append(get_path_from_file_url(f.url))

        elif f.scheme is None:
            paths.append(Path(img_link))

        return img_link

    apply_to_image_link_in_markdown(md=md, fn=fn, ret_updated=False)
    return paths


def change_img_links_in_markdown(md: str, images: t.List[str], updates: t.List[str]):
    assert len(images) == len(updates)

    def fn(img_link: str):
        if img_link in images:
            return updates[images.index(img_link)]
        return img_link

    return apply_to_image_link_in_markdown(md=md, fn=fn, ret_updated=True)


def change_local_image_links_in_markdown(
    md: str, local_img_paths: t.List[Path], updates: t.List[str]
) -> str:
    assert len(local_img_paths) == len(updates)

    def fn(img_link: str):
        f = furl(img_link)

        updated: t.Optional[str] = None
        if f.scheme == "file":
            try:
                idx = local_img_paths.index(get_path_from_file_url(f.url))
            except ValueError:
                return img_link

            updated = updates[idx]

        elif f.scheme is None:
            try:
                idx = local_img_paths.index(Path(img_link))
            except ValueError:
                return img_link

            updated = updates[idx]

        if updated:
            return updated
        return img_link

    return apply_to_image_link_in_markdown(md=md, fn=fn, ret_updated=True)


def convert_local_image_paths_to_absolute(md: str, base_dir: Path):
    assert base_dir.is_absolute()

    def fn(img_link: str):
        f = furl(img_link)
        if f.scheme:
            return img_link

        p = Path(img_link)
        if not p.is_absolute():
            p = base_dir / p
        return str(p.resolve())

    return apply_to_image_link_in_markdown(md=md, fn=fn, ret_updated=True)
