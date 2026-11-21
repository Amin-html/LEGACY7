import re

import pytest
from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.common.uploads import (
    IMAGE_KINDS,
    SUBMISSION_KINDS,
    display_name,
    inspect_upload,
    random_name,
    sniff_kind,
    to_webp,
)

from .helpers import image_bytes, jpeg_bytes, mp4_bytes, pdf_bytes, png_bytes, upload

MB = 1024 * 1024


@pytest.mark.parametrize(
    "head,expected",
    [
        (png_bytes()[:16], "png"),
        (jpeg_bytes()[:16], "jpeg"),
        (image_bytes("WEBP")[:16], "webp"),
        (pdf_bytes()[:16], "pdf"),
        (mp4_bytes()[:16], "mp4"),
        (b"<html><script>", None),
        (b"<svg xmlns=", None),
        (b"MZ\x90\x00" + b"\x00" * 12, None),
        (b"GIF89a" + b"\x00" * 10, None),
        (b"", None),
    ],
)
def test_sniff_kind_looks_at_content(head, expected):
    assert sniff_kind(head) == expected


@pytest.mark.parametrize(
    "original,kind,expected",
    [
        ("photo.png", "png", "photo.png"),
        ("../../evil.php", "png", "evil.png"),
        ("C:\\Users\\x\\отчёт.pdf", "pdf", "отчёт.pdf"),
        ("a\x00b\n.png", "png", "ab.png"),
        ("", "pdf", "file.pdf"),
        (None, "mp4", "file.mp4"),
        ("report.exe", "pdf", "report.pdf"),  # расширение всегда по реальному типу
    ],
)
def test_display_name_is_sanitized(original, kind, expected):
    assert display_name(original, kind) == expected


def test_display_name_is_truncated():
    assert len(display_name("a" * 500 + ".png", "png")) <= 104


def test_random_name_is_random_hex():
    first, second = random_name("png"), random_name("png")
    assert re.fullmatch(r"[0-9a-f]{32}\.png", first)
    assert first != second


def test_inspect_rejects_kind_that_is_not_allowed():
    with pytest.raises(ValidationError):
        inspect_upload(upload("a.pdf", pdf_bytes()), IMAGE_KINDS, 10 * MB)


def test_inspect_accepts_allowed_kind():
    assert inspect_upload(upload("x", png_bytes()), SUBMISSION_KINDS, 10 * MB) == "png"


def test_to_webp_shrinks_and_reencodes(tmp_path):
    result = to_webp(upload("big.png", png_bytes((3000, 2000))))
    path = tmp_path / "out.webp"
    path.write_bytes(result.read())
    with Image.open(path) as img:
        assert img.format == "WEBP"
        assert max(img.size) == 1600