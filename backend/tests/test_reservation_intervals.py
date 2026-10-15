from datetime import date, datetime

import pytest
from rest_framework.exceptions import ValidationError

from apps.reservations.intervals import overlaps, validate_interval


@pytest.mark.parametrize(
    ("other_start", "other_end", "expected"),
    [
        (10, 12, True),
        (9, 11, True),
        (11, 12, True),
        (9, 13, True),
        (12, 14, False),
        (8, 10, False),
        (13, 14, False),
    ],
)
def test_exclusive_intervals(other_start, other_end, expected):
    assert (
        overlaps(
            date(2026, 10, 10),
            date(2026, 10, 12),
            date(2026, 10, other_start),
            date(2026, 10, other_end),
        )
        is expected
    )


@pytest.mark.parametrize(
    "end", [date(2026, 10, 10), date(2026, 10, 9), None, datetime(2026, 10, 12)]
)
def test_invalid_intervals(end):
    with pytest.raises(ValidationError):
        validate_interval(date(2026, 10, 10), end)


def test_daylight_saving_does_not_change_nights():
    # Fechas locales, sin convertir las medianoches a UTC.
    assert (date(2026, 9, 7) - date(2026, 9, 5)).days == 2
    assert overlaps(date(2026, 9, 5), date(2026, 9, 7), date(2026, 9, 6), date(2026, 9, 8))
