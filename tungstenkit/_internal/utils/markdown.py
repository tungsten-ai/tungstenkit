import typing as t
from pathlib import Path

from markdown import Markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import IMAGE_LINK_RE, ImageInlineProcessor
from markdownify import markdownify

from .context import change_workingdir
from .uri import check_if_uri_in_allowed_schemes, get_path_from_file_url


def apply_to_image_link_in_markdown(
    md: str, fn: t.Callable[[str], str], ret_updated: bool = True
) -> str:
    """
    Apply a function to markdown image links
    """

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
    """
    Returns image links in a markdown
    """
    image_links: t.Set[str] = set()

    def fn(img_link: str):
        if schemes is None:
            image_links.add(img_link)
        else:
            if check_if_uri_in_allowed_schemes(img_link, schemes):
                image_links.add(img_link)
        return img_link

    apply_to_image_link_in_markdown(md=md, fn=fn, ret_updated=False)
    return list(image_links)


def get_local_image_paths(
    md: str, *, resolve: bool = True, base_dir: t.Optional[Path] = None
) -> t.List[Path]:
    """
    Returns paths from image links to local files
    """
    paths: t.List[Path] = list()

    base_dir = base_dir.resolve() if base_dir else Path.cwd()
    with change_workingdir(base_dir):

        def fn(img_link: str):
            if img_link.startswith("file:///"):
                paths.append(get_path_from_file_url(img_link))

            else:
                p = Path(img_link)
                if resolve:
                    try:
                        p = p.resolve()
                    except OSError:
                        return img_link
                try:
                    if p.exists():
                        paths.append(p)
                except OSError:
                    return img_link

            return img_link

        apply_to_image_link_in_markdown(md=md, fn=fn, ret_updated=False)
    return paths


def change_img_links_in_markdown(md: str, images: t.List[str], updates: t.List[str]):
    """
    Change image links
    """
    assert len(images) == len(updates)

    def fn(img_link: str):
        if img_link in images:
            return updates[images.index(img_link)]
        return img_link

    return apply_to_image_link_in_markdown(md=md, fn=fn, ret_updated=True)


def change_local_image_links_in_markdown(
    md: str,
    local_img_paths: t.List[Path],
    updates: t.List[str],
    *,
    resolve: bool = True,
    base_dir: t.Optional[Path] = None,
) -> str:
    assert len(local_img_paths) == len(updates)

    base_dir = base_dir.resolve() if base_dir else Path.cwd()
    with change_workingdir(base_dir):
        if resolve:
            local_img_paths = [p.resolve() for p in local_img_paths]

        def fn(img_link: str):
            updated: t.Optional[str] = None
            if img_link.startswith("file:///"):
                try:
                    idx = local_img_paths.index(get_path_from_file_url(img_link))
                except ValueError:
                    return img_link

                updated = updates[idx]

            else:
                try:
                    p = Path(img_link)
                    if resolve:
                        try:
                            p = p.resolve()
                        except OSError:
                            return img_link
                    idx = local_img_paths.index(p)
                except ValueError:
                    return img_link

                updated = updates[idx]

            if updated:
                return updated
            return img_link

        return apply_to_image_link_in_markdown(md=md, fn=fn, ret_updated=True)


def resolve_local_image_paths(md: str, base_dir: Path):
    base_dir = base_dir.resolve()

    with change_workingdir(base_dir):

        def fn(img_link: str):
            p = Path(img_link)
            try:
                if p.exists():
                    return p.resolve().as_uri()
                else:
                    return img_link
            except OSError:
                return img_link

        return apply_to_image_link_in_markdown(md=md, fn=fn, ret_updated=True)
