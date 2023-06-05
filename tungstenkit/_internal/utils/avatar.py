import hashlib
import io

import requests
from furl import furl
from PIL import Image

from tungstenkit._internal.logging import log_debug, log_info

GRAVATAR_BASE_URL = "https://www.gravatar.com/avatar"
CONNECTION_TINEOUT = 10


def fetch_default_avatar_png(hash_key: str, size: int = 80, default: str = "retro") -> bytes:
    digest = hashlib.md5(hash_key.encode("utf-8")).hexdigest()
    f = furl(GRAVATAR_BASE_URL)
    f.path = f.path / (digest + ".png")
    f.args["d"] = default
    f.args["s"] = str(size)
    log_debug(f"Get an avatar from '{f.url}'")
    try:
        r = requests.get(f.url)
        r.raise_for_status()
        avatar = r.content
    except requests.RequestException as e:
        log_info(f"Failed to get avatar: {type(e)}: {str(e)}", pretty=False)
        log_info(f"Set an empty image as avatar for {hash_key}")

        img = Image.new("RGB", (size, size), color=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        avatar = buf.getvalue()

    return avatar
