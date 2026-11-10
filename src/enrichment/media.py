"""Download and cache post images (pbs.twimg.com only), validating them as JPEG/PNG."""

from __future__ import annotations

import urllib.request
from pathlib import Path
from urllib.parse import urlparse

MEDIA_DIR = Path("data/raw/media")
MAX_BYTES = 8 * 1024 * 1024
ALLOWED_HOST = "pbs.twimg.com"
USER_AGENT = "Mozilla/5.0 (compatible; x-analysis/0.1)"  # the CDN rejects the default Python UA


def _sized(url: str) -> str:
    # `medium` is at most 1200px on the long side: inside Jev's 280-1568px range, no resizing.
    return f"{url}{'&' if '?' in url else '?'}name=medium"


def is_image(data: bytes) -> bool:
    return data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n"


def fetch_image(post_id: str, url: str, cache_dir: Path = MEDIA_DIR) -> bytes | None:
    """Return the image bytes, or None if the host is unexpected or the file is not an image."""
    if urlparse(url).hostname != ALLOWED_HOST:
        return None
    path = cache_dir / f"{post_id}.img"
    if path.exists():
        return path.read_bytes()
    try:
        req = urllib.request.Request(_sized(url), headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            data = resp.read(MAX_BYTES + 1)
    except OSError:
        return None
    if len(data) > MAX_BYTES or not is_image(data):
        return None
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data
