import re


def mask_text(value):
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[correo omitido]", value)
    value = re.sub(r"(?<!\w)\d{1,2}(?:\.?\d{3}){2}-[0-9kK](?!\w)", "[documento omitido]", value)
    value = re.sub(r"(?<!\w)\d{7,8}[kK](?!\w)", "[documento omitido]", value)

    def phone(match):
        candidate = match.group()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate):
            return candidate
        return "[número omitido]"

    value = re.sub(r"\b\d{4}-\d{2}-\d{2}\b|(?<!\w)\+?\d[\d ()-]{6,}\d(?!\w)", phone, value)
    return value
