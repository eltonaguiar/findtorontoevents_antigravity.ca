# -*- coding: utf-8 -*-
"""Revision marker — tracks when a system received a significant code change.

When a system is significantly revised, its forward-test performance should be
tracked fresh (pre-revision data is archived, not mixed with post-revision).

Usage in scanner:
    from shared.revision_marker import check_revision
    check_revision("system_a_filter", "2026-02-25", data_dir)
"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime, timezone

log = logging.getLogger(__name__)

# Map system_id -> revision date (YYYY-MM-DD) and reason.
# When you make a significant code change to a system, add an entry here.
REVISIONS = {
    "system_a_filter": {
        "date": "2026-02-25",
        "reason": "PANIC_SELL killed, threshold 0.50->0.75, min() replaces max(), capitulation guard added",
    },
    "system_b_regime": {
        "date": "2026-02-25",
        "reason": "PANIC_SELL killed, threshold 0.50->0.75, min() replaces max(), capitulation guard added",
    },
    "system_c_deeplearn": {
        "date": "2026-02-25",
        "reason": "PANIC_SELL killed, threshold 0.50->0.75, min() replaces max(), capitulation guard added",
    },
    "ensemble": {
        "date": "2026-02-25",
        "reason": "Inherits PANIC_SELL fix from subsystems",
    },
    "system_d_carry": {
        "date": "2026-02-25",
        "reason": "scipy dependency fix — system was non-functional before this date",
    },
    "system_e_momentum": {
        "date": "2026-02-25",
        "reason": "scipy dependency fix — system was non-functional before this date",
    },
}


def check_revision(system_id: str, data_dir: Path) -> bool:
    """Check if this system has a pending revision reset.

    If the system was revised and the marker file doesn't exist yet,
    archive old closed_picks.json and create the marker.
    Returns True if a reset was performed.
    """
    if system_id not in REVISIONS:
        return False

    rev = REVISIONS[system_id]
    marker_file = data_dir / "revision_marker.json"

    # Already processed this revision
    if marker_file.exists():
        try:
            existing = json.loads(marker_file.read_text())
            if existing.get("revision_date") == rev["date"]:
                return False
        except (json.JSONDecodeError, KeyError):
            pass

    # Archive existing closed picks
    closed_file = data_dir / "closed_picks.json"
    if closed_file.exists():
        archive_name = f"closed_picks_pre_{rev['date'].replace('-', '')}.json"
        archive_path = data_dir / archive_name
        if not archive_path.exists():
            shutil.copy2(closed_file, archive_path)
            log.info(f"  Archived pre-revision closed picks to {archive_name}")

        # Reset closed picks to empty
        closed_file.write_text("[]")
        log.info(f"  Reset closed_picks.json for fresh tracking (revision {rev['date']})")

    # Ensure data directory exists
    data_dir.mkdir(parents=True, exist_ok=True)

    # Write marker
    marker = {
        "system_id": system_id,
        "revision_date": rev["date"],
        "reason": rev["reason"],
        "reset_at": datetime.now(timezone.utc).isoformat(),
    }
    marker_file.write_text(json.dumps(marker, indent=2))
    log.info(f"  Revision marker written: {system_id} revised on {rev['date']}")
    return True
