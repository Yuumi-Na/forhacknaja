"""Prepare an uploaded photo for Bedrock: check type, fix orientation, strip metadata, shrink.

Bedrock accepts at most 3.75 MB and 8000 px per image. We stay under 2560 px and 3.5 MB.
Re-encoding with Pillow drops EXIF (including GPS position). No network.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_SIDE_PX = 2560
MAX_BYTES = int(3.5 * 1024 * 1024)
START_QUALITY = 85
MIN_QUALITY = 40
QUALITY_STEP = 10
SHRINK_FACTOR = 0.8
MIN_SIDE_PX = 200

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class ImageError(Exception):
    """The upload is not a usable JPEG or PNG image."""


@dataclass(frozen=True)
class PreparedImage:
    data: bytes
    format: Literal["jpeg", "png"]
    width: int
    height: int


def detect_format(data: bytes) -> Literal["jpeg", "png"]:
    if data.startswith(_JPEG_MAGIC):
        return "jpeg"
    if data.startswith(_PNG_MAGIC):
        return "png"
    raise ImageError("not a JPEG or PNG image")


def _encode_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _encode_jpeg(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _flatten(img: Image.Image) -> Image.Image:
    """JPEG has no alpha: paste transparent images on white."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.getchannel("A"))
        return bg
    return img.convert("RGB")


def prepare_image(data: bytes) -> PreparedImage:
    """Return a metadata-free JPEG or PNG of at most 2560 px and 3.5 MB."""
    fmt = detect_format(data)
    try:
        with Image.open(io.BytesIO(data)) as opened:
            img = ImageOps.exif_transpose(opened)
            img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageError("image cannot be decoded") from exc

    if max(img.size) > MAX_SIDE_PX:
        img.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX), Image.Resampling.LANCZOS)

    if fmt == "png":
        out = _encode_png(img)
        if len(out) <= MAX_BYTES:
            return PreparedImage(out, "png", *img.size)
        # Too big as PNG: continue as JPEG.

    rgb = _flatten(img)
    quality = START_QUALITY
    while True:
        out = _encode_jpeg(rgb, quality)
        if len(out) <= MAX_BYTES:
            return PreparedImage(out, "jpeg", *rgb.size)
        if quality - QUALITY_STEP >= MIN_QUALITY:
            quality -= QUALITY_STEP
            continue
        w, h = rgb.size
        if max(w, h) <= MIN_SIDE_PX:
            raise ImageError("image cannot be made small enough")
        rgb = rgb.resize(
            (max(1, int(w * SHRINK_FACTOR)), max(1, int(h * SHRINK_FACTOR))),
            Image.Resampling.LANCZOS,
        )
        quality = START_QUALITY
