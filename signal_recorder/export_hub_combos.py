"""Export winning combos as a JSON file for the Hub dashboard to display."""
import json
from datetime import datetime, timezone
from pathlib import Path
from signal_recorder.db import get_db

OUTPUT_PATH = Path(__file__).parent / "data" / "winning_combos.json"
HUB_OUTPUT = Path(__file__).parent.parent / "hub" / "data" / "winning_combos.json"


def export_for_hub():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM combo_results
        WHERE p_value < 0.05 AND win_rate > 0.55 AND total_trades >= 5
        ORDER BY p_value ASC
        LIMIT 50
    """).fetchall()
    conn.close()

    combos = [dict(r) for r in rows]
    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "winning_combos": combos,
        "total_found": len(combos),
    }

    for path in (OUTPUT_PATH, HUB_OUTPUT):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(output, indent=2, default=str))

    print(f"Exported {len(combos)} winning combos to hub")


if __name__ == "__main__":
    export_for_hub()
