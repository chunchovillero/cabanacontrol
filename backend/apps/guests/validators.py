import re
import unicodedata

from django.core.exceptions import ValidationError

RUT_FORMAT = re.compile(r"(?:[0-9]{1,8}|[0-9]{1,2}(?:\.[0-9]{3}){2}|[0-9]{1,3}\.[0-9]{3})-?[0-9Kk]")


def normalize_rut(value: str) -> str:
    if not isinstance(value, str) or not RUT_FORMAT.fullmatch(value.strip()):
        raise ValidationError("Ingresa un RUT válido con su dígito verificador.")
    compact = value.strip().replace(".", "").replace("-", "").upper()
    body, verifier = compact[:-1], compact[-1]
    body = str(int(body))
    if body == "0":
        raise ValidationError("Ingresa un RUT válido con su dígito verificador.")
    total = sum(int(digit) * (2 + index % 6) for index, digit in enumerate(reversed(body)))
    remainder = 11 - total % 11
    expected = "0" if remainder == 11 else "K" if remainder == 10 else str(remainder)
    if verifier != expected:
        raise ValidationError("El dígito verificador del RUT no es válido.")
    return f"{body}-{verifier}"


def normalize_document(document_type: str, value: str) -> str:
    if document_type == "rut":
        return normalize_rut(value)
    if document_type not in ("passport", "other") or not isinstance(value, str):
        raise ValidationError("Selecciona un tipo de documento válido.")
    value = unicodedata.normalize("NFKC", value).strip().upper()
    if not value or len(value) > 40 or not any(char.isalnum() for char in value):
        raise ValidationError("Ingresa un documento de hasta 40 caracteres.")
    if any(not (char.isalnum() or char in " .-/") for char in value):
        raise ValidationError("El documento contiene caracteres no permitidos.")
    return " ".join(value.split())


def normalize_phone(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("Ingresa un teléfono válido.")
    value = value.strip()
    if not value:
        return ""
    if not re.fullmatch(r"\+?[0-9 ()-]+", value):
        raise ValidationError("Ingresa un teléfono válido; puedes incluir prefijo internacional.")
    digits = re.sub(r"[^0-9]", "", value)
    if not 7 <= len(digits) <= 15:
        raise ValidationError("El teléfono debe tener entre 7 y 15 dígitos.")
    return ("+" if value.startswith("+") else "") + digits


def mask_document(value: str) -> str:
    # No mostrar completo un identificador corto.
    return "••••" if len(value) <= 4 else "••••" + value[-4:]
