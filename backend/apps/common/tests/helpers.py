import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def image_bytes(fmt="PNG", size=(10, 10), mode="RGB"):
    buf = io.BytesIO()
    Image.new(mode, size).save(buf, fmt)
    return buf.getvalue()


def png_bytes(size=(10, 10)):
    return image_bytes("PNG", size)


def jpeg_bytes(size=(10, 10)):
    return image_bytes("JPEG", size)


def pdf_bytes(extra=0):
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n" + b"0" * extra


def mp4_bytes():
    return b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 64


def upload(name, content, content_type="application/octet-stream"):
    return SimpleUploadedFile(name, content, content_type=content_type)