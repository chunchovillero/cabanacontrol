from collections import defaultdict
from datetime import date


def occupied_nights(intervals: list[tuple[str, date, date]], start: date, end: date) -> int:
    """Contar noches por cabaña sin duplicar intervalos históricos superpuestos."""
    grouped = defaultdict(list)
    for property_id, check_in, check_out in intervals:
        left, right = max(start, check_in), min(end, check_out)
        if left < right:
            grouped[property_id].append((left, right))
    total = 0
    for ranges in grouped.values():
        merged = []
        for left, right in sorted(ranges):
            if merged and left <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], right))
            else:
                merged.append((left, right))
        total += sum((right - left).days for left, right in merged)
    return total
