import warnings
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}


def normalize_photo(upload):
    if upload.size > settings.PROPERTY_PHOTO_MAX_BYTES:
        raise ValidationError({"file": "La imagen no puede superar 5 MB."})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            # Limitar los decodificadores usados, independientemente del nombre/MIME.
            with Image.open(upload, formats=list(FORMATS)) as image:
                image_format = image.format
                if image_format not in FORMATS or getattr(image, "is_animated", False):
                    raise ValidationError({"file": "Usa una imagen estática JPG, PNG o WebP."})
                if max(image.size) > settings.PROPERTY_PHOTO_MAX_DIMENSION:
                    raise ValidationError(
                        {"file": "La imagen no puede superar 4096 píxeles por lado."}
                    )
                image.verify()
            upload.seek(0)
            with Image.open(upload, formats=list(FORMATS)) as image:
                image.load()
                oriented = ImageOps.exif_transpose(image)
                converted = oriented.convert("RGB" if image_format == "JPEG" else "RGBA")
                # Copiar solo píxeles: no conservar EXIF, GPS, ICC ni texto del original.
                clean = Image.new(converted.mode, converted.size)
                clean.paste(converted)
                output = BytesIO()
                clean.save(output, format=image_format)
                if output.tell() > settings.PROPERTY_PHOTO_MAX_BYTES:
                    raise ValidationError({"file": "La imagen procesada supera el límite de 5 MB."})
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ValidationError(
            {"file": "El archivo no es una imagen válida JPG, PNG o WebP."}
        ) from exc
    extension, content_type = FORMATS[image_format]
    return ContentFile(output.getvalue(), name=f"photo.{extension}"), content_type
