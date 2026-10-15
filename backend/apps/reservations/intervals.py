from datetime import date

from rest_framework.exceptions import ValidationError


def validate_interval(start: date, end: date) -> None:
    if type(start) is not date or type(end) is not date or end <= start:
        raise ValidationError({"check_out": "La salida debe ser posterior a la entrada."})


def overlaps(start: date, end: date, other_start: date, other_end: date) -> bool:
    """Intervalos [entrada, salida): la salida puede coincidir con otra entrada."""
    validate_interval(start, end)
    validate_interval(other_start, other_end)
    return start < other_end and other_start < end
