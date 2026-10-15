from datetime import date

import pytest

from apps.insights.intervals import occupied_nights


@pytest.mark.parametrize(
    "ranges,expected",
    [
        ([], 0),
        ([("a", 1, 3)], 2),
        ([("a", 1, 3), ("a", 3, 5)], 4),
        ([("a", 1, 4), ("a", 2, 5)], 4),
        ([("a", 1, 3), ("b", 1, 3)], 4),
        ([("a", 1, 3), ("a", 1, 3)], 2),
        ([("a", 1, 2), ("a", 5, 6)], 2),
        ([("a", 1, 10)], 8),
    ],
)
def test_unique_nights_per_property(ranges, expected):
    values = [(key, date(2026, 10, start), date(2026, 10, end)) for key, start, end in ranges]
    assert occupied_nights(values, date(2026, 10, 1), date(2026, 10, 9)) == expected
