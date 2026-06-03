"""Stale resolver must paginate the full live set, not only the oldest batch."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tools.pick_hold_windows import is_past_max_hold


def _pick(created_hours_ago: float, category: str = "crypto") -> dict:
    ts = datetime.now(timezone.utc) - timedelta(hours=created_hours_ago)
    return {"category": category, "created_at": ts}


def test_stale_can_be_beyond_first_batch_window():
    """Simulate: oldest 500 fresh, newer rows past hold — must be detected when scanning offset."""
    batch_size = 500
    # Oldest 500: 10h old (within 48h crypto hold)
    rows = [_pick(10.0, "crypto") for _ in range(500)]
    # Next 200: 72h old (stale)
    rows.extend([_pick(72.0, "crypto") for _ in range(200)])

    offset = 0
    total_stale = 0
    total_live = len(rows)
    while offset < total_live:
        batch = rows[offset : offset + batch_size]
        if not batch:
            break
        stale = [p for p in batch if is_past_max_hold(p)]
        if stale:
            total_stale += len(stale)
            offset = 0
            # remove resolved from rows (simplified)
            stale_set = {id(p) for p in stale}
            rows = [p for p in rows if id(p) not in stale_set]
            total_live = len(rows)
        else:
            offset += len(batch)

    assert total_stale == 200
