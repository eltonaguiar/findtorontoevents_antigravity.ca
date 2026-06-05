#!/usr/bin/env python3
"""Clean ingest v2 — reject contaminated picks at write time (MASTERPLAN 2026-06-05).

Rejects rows when:
  - Entry price drift vs spot exceeds per-class threshold (price_tracker parity)
  - Reverse-split symbol with pre-split entry (no adjustment flag)
  - Resolver used TP_HIT_REPLAY-only intrabar wick fill (inflates WR)
  - Missing symbol / entry / asset_class

Read-only audit mode by default. Use --apply only with operator approval
(after ejaguiar1_backups snapshot).

Usage:
    python3 tools/clean_ingest_v2.py --sample 100
    python3 tools/clean_ingest_v2.py --json path/to/picks.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from audit_trail.reverse_split_symbols import (
    is_reverse_split_affected,
    should_adjust_for_split,
)

# Mirrors tools/ai_tournament/price_tracker.py (keep in sync)
_DRIFT_BY_CLASS: dict[str, float] = {
    "ETF": 7.0,
    "EQUITY": 10.0,
    "BOND": 5.0,
    "FOREX": 3.0,
    "COMMODITY": 12.0,
    "FUTURES": 12.0,
    "PENNY": 25.0,
    "PENNY_STOCK": 25.0,
    "CRYPTO": 25.0,
    "MEMECOIN": 25.0,
}
_DEFAULT_DRIFT = float(os.environ.get("RESOLVER_MAX_ENTRY_DRIFT_PCT", "50.0"))

REJECT_TP_HIT_REPLAY = os.environ.get("CLEAN_INGEST_REJECT_TP_HIT_REPLAY", "1") in (
    "1", "true", "TRUE", "yes",
)


@dataclass
class CleanIngestDecision:
    ok: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "reasons": self.reasons}


def _norm_class(ac: Any) -> str:
    return str(ac or "").strip().upper() or "UNKNOWN"


def _norm_dir(d: Any) -> str:
    s = str(d or "").strip().upper()
    if s in ("BUY", "LONG"):
        return "LONG"
    if s in ("SELL", "SHORT"):
        return "SHORT"
    return s


def entry_drift_pct(entry: float, spot: float) -> float | None:
    if not entry or not spot or spot <= 0:
        return None
    return abs(entry - spot) / spot * 100.0


def validate_pick_row(
    pick: dict[str, Any],
    *,
    spot_price: float | None = None,
    submitted_at: str | None = None,
) -> CleanIngestDecision:
    """Return whether a pick dict is admissible for trading_picks_v2 / production."""
    reasons: list[str] = []

    symbol = str(pick.get("symbol") or "").strip()
    if not symbol:
        reasons.append("missing_symbol")

    ac = _norm_class(pick.get("asset_class") or pick.get("category"))
    entry = pick.get("entry_price")
    try:
        entry_f = float(entry) if entry is not None else None
    except (TypeError, ValueError):
        entry_f = None
    if entry_f is None or entry_f <= 0:
        reasons.append("missing_or_invalid_entry_price")

    ts = (
        submitted_at
        or pick.get("submitted_at")
        or pick.get("created_at")
        or pick.get("signal_timestamp")
        or pick.get("recorded_at")
        or ""
    )

    if is_reverse_split_affected(symbol) and ts:
        adjust, _factor = should_adjust_for_split(symbol, str(ts))
        if adjust and not pick.get("reverse_split_adjusted"):
            reasons.append("reverse_split_unadjusted_entry")

    if spot_price is not None and entry_f is not None and spot_price > 0:
        drift = entry_drift_pct(entry_f, spot_price)
        cap = _DRIFT_BY_CLASS.get(ac, _DEFAULT_DRIFT)
        if drift is not None and drift > cap:
            reasons.append(f"entry_drift_{drift:.1f}pct_gt_{cap:.0f}")

    tp_method = str(pick.get("tp_fill_method") or pick.get("exit_reason") or "").upper()
    if REJECT_TP_HIT_REPLAY and "TP_HIT_REPLAY" in tp_method:
        reasons.append("tp_hit_replay_inflates_wr")

    if pick.get("was_mispriced") or pick.get("status") == "MISPRICED_ENTRY":
        reasons.append("mispriced_entry_status")

    return CleanIngestDecision(ok=len(reasons) == 0, reasons=reasons)


def audit_trading_picks_sample(n: int = 100) -> dict[str, Any]:
    """Pull last N closed trading_picks and summarize reject reasons."""
    import pymysql
    from tools.db_env import get_stocks_creds

    creds = get_stocks_creds()
    conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, symbol, direction, strategy, category, entry_price, exit_price,
               pnl_pct, status, tp_fill_method, created_at, closed_at
        FROM trading_picks
        WHERE closed_at IS NOT NULL
        ORDER BY closed_at DESC
        LIMIT %s
        """,
        (n,),
    )
    rows = cur.fetchall()
    conn.close()

    stats: dict[str, int] = {}
    rejected = 0
    samples: list[dict[str, Any]] = []
    for row in rows:
        pick = {
            "symbol": row["symbol"],
            "asset_class": (row.get("category") or "").upper(),
            "direction": row["direction"],
            "entry_price": row["entry_price"],
            "tp_fill_method": row.get("tp_fill_method"),
            "submitted_at": str(row.get("created_at") or ""),
        }
        dec = validate_pick_row(pick)
        if not dec.ok:
            rejected += 1
            for r in dec.reasons:
                stats[r] = stats.get(r, 0) + 1
            if len(samples) < 8:
                samples.append({"id": row["id"], "symbol": row["symbol"], "reasons": dec.reasons})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_n": len(rows),
        "rejected": rejected,
        "accepted": len(rows) - rejected,
        "reject_rate_pct": round(100 * rejected / max(len(rows), 1), 1),
        "reason_counts": stats,
        "sample_rejects": samples,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Clean ingest v2 validator")
    ap.add_argument("--sample", type=int, default=0, metavar="N", help="Audit N recent trading_picks")
    ap.add_argument("--json", type=Path, help="Validate picks from JSON list file")
    ap.add_argument("--out", type=Path, help="Write audit JSON here")
    args = ap.parse_args()

    if args.json:
        data = json.loads(args.json.read_text(encoding="utf-8"))
        picks = data if isinstance(data, list) else data.get("picks", [])
        rejected = sum(1 for p in picks if not validate_pick_row(p).ok)
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": str(args.json),
            "total": len(picks),
            "rejected": rejected,
            "accepted": len(picks) - rejected,
        }
    elif args.sample:
        report = audit_trading_picks_sample(args.sample)
    else:
        ap.print_help()
        return 1

    out = args.out or REPO_ROOT / "reports" / "clean_ingest_v2_audit_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())