import io

import pytest
from PIL import Image

from mordin.vision.image import MAX_BYTES, MAX_SIDE_PX, ImageError, prepare_image


def _jpeg(size=(100, 60), exif_orientation=None, color=(200, 30, 30)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    kwargs = {}
    if exif_orientation:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        exif[0x010F] = "TestMaker"
        kwargs["exif"] = exif
    img.save(buf, format="JPEG", **kwargs)
    return buf.getvalue()


def _png(size=(50, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", size, (0, 128, 0, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_rejects_non_image_bytes():
    with pytest.raises(ImageError):
        prepare_image(b"GIF89a....")
    with pytest.raises(ImageError):
        prepare_image(b"")


def test_rejects_corrupt_jpeg():
    with pytest.raises(ImageError):
        prepare_image(b"\xff\xd8\xff\x00broken")


def test_png_stays_png():
    out = prepare_image(_png())
    assert out.format == "png"
    assert out.data.startswith(b"\x89PNG")
    assert (out.width, out.height) == (50, 40)


def test_exif_orientation_applied_and_metadata_removed():
    out = prepare_image(_jpeg(size=(100, 60), exif_orientation=6))
    assert out.format == "jpeg"
    assert (out.width, out.height) == (60, 100)
    with Image.open(io.BytesIO(out.data)) as img:
        assert len(img.getexif()) == 0
        assert "exif" not in img.info


def test_large_image_downscaled_to_max_side():
    out = prepare_image(_jpeg(size=(4000, 3000)))
    assert max(out.width, out.height) == MAX_SIDE_PX
    assert len(out.data) <= MAX_BYTES


def test_noisy_image_fits_byte_limit(monkeypatch):
    import os

    import mordin.vision.image as mod

    noise = Image.frombytes("RGB", (900, 900), os.urandom(900 * 900 * 3))
    buf = io.BytesIO()
    noise.save(buf, format="PNG")
    monkeypatch.setattr(mod, "MAX_BYTES", 150_000)
    out = prepare_image(buf.getvalue())
    assert out.format == "jpeg"
    assert len(out.data) <= 150_000
