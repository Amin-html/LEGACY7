import io
import os
import re
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from rest_framework import serializers

MAX_IMAGE_PIXELS = 40_000_000  # защита от «бомб»: огромная картинка в крошечном файле

# тип -> (расширение, MIME). Расширение и MIME ставим мы сами, а не берём у пользователя
KINDS = {
    "png": (".png", "image/png"),
    "jpeg": (".jpg", "image/jpeg"),
    "webp": (".webp", "image/webp"),
    "pdf": (".pdf", "application/pdf"),
    "mp4": (".mp4", "video/mp4"),
}
LABELS = {"png": "PNG", "jpeg": "JPEG", "webp": "WebP", "pdf": "PDF", "mp4": "MP4"}
IMAGE_KINDS = ("png", "jpeg", "webp")
SUBMISSION_KINDS = ("png", "jpeg", "webp", "pdf", "mp4")
PILLOW_FORMATS = {"png": "PNG", "jpeg": "JPEG", "webp": "WEBP"}


def max_bytes(setting_name):
    return int(getattr(settings, setting_name)) * 1024 * 1024


def sniff_kind(head):
    """Определяет тип по первым байтам файла. Расширение и Content-Type не учитываются."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head.startswith(b"%PDF-"):
        return "pdf"
    if head[4:8] == b"ftyp":
        return "mp4"
    return None


def _check_image(upload, kind):
    try:
        with Image.open(upload) as img:
            if img.format != PILLOW_FORMATS[kind]:
                raise ValueError("format mismatch")
            width, height = img.size
            if width * height > MAX_IMAGE_PIXELS:
                raise serializers.ValidationError("Изображение слишком большое по размерам.")
            img.verify()
    except serializers.ValidationError:
        raise
    except Exception:
        raise serializers.ValidationError("Файл повреждён или не является изображением.")
    finally:
        upload.seek(0)


def inspect_upload(upload, allowed, max_size):
    """Проверяет файл по содержимому. Возвращает тип ('png', 'pdf', ...) или бросает ValidationError."""
    if upload.size == 0:
        raise serializers.ValidationError("Файл пустой.")
    if upload.size > max_size:
        raise serializers.ValidationError(f"Файл больше {max_size // (1024 * 1024)} МБ.")
    upload.seek(0)
    head = upload.read(16)
    upload.seek(0)
    kind = sniff_kind(head)
    if kind not in allowed:
        raise serializers.ValidationError(
            "Недопустимый тип файла. Разрешены: " + ", ".join(LABELS[k] for k in allowed) + "."
        )
    if kind in IMAGE_KINDS:
        _check_image(upload, kind)
    return kind


def random_name(kind):
    return uuid.uuid4().hex + KINDS[kind][0]


def display_name(original, kind):
    """Имя для показа пользователю: без путей и управляющих символов, расширение по типу."""
    name = os.path.basename((original or "").replace("\\", "/"))
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    stem = os.path.splitext(name)[0][:100].strip(" .") or "file"
    return stem + KINDS[kind][0]


def to_webp(upload, max_side=1600):
    """Перекодирует картинку в WebP: убирает EXIF и любой «хвост» внутри файла."""
    upload.seek(0)
    with Image.open(upload) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((max_side, max_side))
        has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        img = img.convert("RGBA" if has_alpha else "RGB")
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=85)
    return ContentFile(buf.getvalue())