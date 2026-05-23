"""Shadow performance tracker for new-strategies-scanner picks (M-075).

Reads alpha_engine/data/scanner_output/new_strategies_picks.json (daily emitter),
resolves closed picks using live yfinance OHLC data, and writes a shadow log at:
  alpha_engine/data/scanner_output/new_strategies_shadow_log.json

Shadow mode runs from 2026-05-17 to 2026-05-31. On 2026-05-31, the log provides
WR/PF/n data to make the gate-promotion decision for the 20 new strategies.

Outcome resolution:
  - If current price >= take_profit (LONG) or <= take_profit (SHORT) → WIN
  - If current price <= stop_loss (LONG) or >= stop_loss (SHORT) → LOSS
  - If max_hold_bars elapsed from entry_time → EXPIRED (neutral, not counted)
  - Otherwise → OPEN (still in progress)

Run:
    python tools/new_strategies_shadow_tracker.py [--dry-run]

Called by: .github/workflows/new-strategies-scanner.yml (after emitter step)
Kill-switch: NEW_STRATS_SHADOW_DISABLED=1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PICKS_PATH = ROOT / "alpha_engine" / "data" / "scanner_output" / "new_strategies_picks.json"
LOG_PATH = ROOT / "alpha_engine" / "data" / "scanner_output" / "new_strategies_shadow_log.json"
SHADOW_END = datetime(2026, 5, 31, tzinfo=timezone.utc)


def _resolve_pick(pick: dict, now: datetime) -> dict:
    """Attempt to resolve a single pick using live OHLC. Returns updated pick dict."""
    try:
        import yfinance as yf
    except ImportError:
        return pick

    symbol = str(pick.get("symbol") or "").strip()
    entry_time_str = pick.get("entry_time") or pick.get("timestamp") or ""
    direction = str(pick.get("direction") or pick.get("signal_type") or "LONG").upper()
    is_long = direction in ("LONG", "BUY")

    try:
        entry_dt = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
        if entry_dt.tzinfo is None:
            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return pick

    tp = float(pick.get("take_profit") or 0)
    sl = float(pick.get("stop_loss") or 0)
    max_hold = int(pick.get("max_hold_bars") or 30)

    # Check expiry (max_hold_bars × 1 calendar day approximation)
    age_days = (now - entry_dt).days
    if age_days >= max_hold:
        pick = {**pick, "shadow_outcome": "EXPIRED", "shadow_resolved_at": now.isoformat()}
        return pick

    # Fetch recent OHLC
    try:
        hist = yf.Ticker(symbol).history(period="5d", interval="1d")
        if hist.empty:
            return pick
        latest_close = float(hist["Close"].iloc[-1])
        latest_high = float(hist["High"].iloc[-1])
        latest_low = float(hist["Low"].iloc[-1])
    except Exception:
        return pick

    # Resolve
    if is_long:
        if tp > 0 and latest_high >= tp:
            outcome = "WIN"
        elif sl > 0 and latest_low <= sl:
            outcome = "LOSS"
        else:
            return pick  # still OPEN
    else:
        if tp > 0 and latest_low <= tp:
            outcome = "WIN"
        elif sl > 0 and latest_high >= sl:
            outcome = "LOSS"
        else:
            return pick

    entry_price = float(pick.get("entry_price") or latest_close)
    exit_price = tp if outcome == "WIN" else sl
    pnl_pct = ((exit_price - entry_price) / entry_price * 100) if is_long else ((entry_price - exit_price) / entry_price * 100)

    return {
        **pick,
        "shadow_outcome": outcome,
        "shadow_exit_price": round(exit_price, 4),
        "shadow_pnl_pct": round(pnl_pct, 4),
        "shadow_resolved_at": now.isoformat(),
    }


def _compute_summary(picks: list[dict]) -> dict:
    closed = [p for p in picks if p.get("shadow_outcome") in ("WIN", "LOSS")]
    wins = [p for p in closed if p.get("shadow_outcome") == "WIN"]
    losses = [p for p in closed if p.get("shadow_outcome") == "LOSS"]
    pnl_list = [p.get("shadow_pnl_pct", 0.0) for p in closed if p.get("shadow_pnl_pct") is not None]
    gross_win = sum(p for p in pnl_list if p > 0)
    gross_loss = abs(sum(p for p in pnl_list if p < 0))
    pf = round(gross_win / gross_loss, 4) if gross_loss > 0 else (None if not gross_win else 9999.0)
    wr = round(len(wins) / len(closed), 4) if closed else None

    # Per-strategy breakdown
    by_strategy: dict[str, dict] = {}
    for p in closed:
        strat = str(p.get("strategy") or "unknown")
        s = by_strategy.setdefault(strat, {"wins": 0, "losses": 0, "pnl_pct_sum": 0.0})
        if p.get("shadow_outcome") == "WIN":
            s["wins"] += 1
        else:
            s["losses"] += 1
        s["pnl_pct_sum"] = round(s["pnl_pct_sum"] + (p.get("shadow_pnl_pct") or 0.0), 4)

    # Promotion verdict (2026-05-31 decision criteria)
    promotion_ready = (
        len(closed) >= 10 and
        wr is not None and wr >= 0.50 and
        pf is not None and pf >= 1.5
    )

    return {
        "n_total": len(picks),
        "n_open": len([p for p in picks if not p.get("shadow_outcome")]),
        "n_closed": len(closed),
        "n_expired": len([p for p in picks if p.get("shadow_outcome") == "EXPIRED"]),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": wr,
        "profit_factor": pf,
        "avg_pnl_pct": round(sum(pnl_list) / len(pnl_list), 4) if pnl_list else None,
        "promotion_criteria": {"n_closed_min": 10, "wr_min": 0.50, "pf_min": 1.5},
        "promotion_ready": promotion_ready,
        "by_strategy": {
            k: {
                "wins": v["wins"],
                "losses": v["losses"],
                "wr": round(v["wins"] / (v["wins"] + v["losses"]), 4) if (v["wins"] + v["losses"]) > 0 else None,
                "avg_pnl_pct": round(v["pnl_pct_sum"] / (v["wins"] + v["losses"]), 4) if (v["wins"] + v["losses"]) > 0 else None,
            }
            for k, v in by_strategy.items()
        },
    }


def run_shadow_tracker(dry_run: bool = False) -> int:
    if os.environ.get("NEW_STRATS_SHADOW_DISABLED", "0") in ("1", "true", "True", "TRUE"):
        print("[shadow-tracker] disabled via NEW_STRATS_SHADOW_DISABLED — skipping")
        return 0

    now = datetime.now(timezone.utc)

    if not PICKS_PATH.exists():
        print(f"[shadow-tracker] picks file not found: {PICKS_PATH}", file=sys.stderr)
        return 1

    current_picks = json.loads(PICKS_PATH.read_text(encoding="utf-8"))
    if not isinstance(current_picks, list):
        current_picks = current_picks.get("picks", [])

    # Load existing log
    log: dict = {}
    if LOG_PATH.exists():
        try:
            log = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log = {}

    # Merge existing tracked picks (keyed by stable_id — symbol+strategy+entry_date,
    # not full timestamp, so IDs survive timestamp precision changes between runs).
    def _stable_id(p: dict) -> str:
        sym = str(p.get("symbol") or "").upper()
        strat = str(p.get("strategy") or "")
        # Normalize timestamp to date only for stability
        ts = str(p.get("entry_time") or p.get("timestamp") or "")[:10]
        return p.get("id") or f"{sym}:{strat}:{ts}"

    tracked: dict[str, dict] = {}
    for p in log.get("picks", []):
        sid = _stable_id(p)
        tracked[sid] = {**p, "id": sid}

    # Add new picks not yet tracked; re-resolve OPEN ones
    for pick in current_picks:
        pid = _stable_id(pick)
        pick = {**pick, "id": pid}
        if pid not in tracked:
            tracked[pid] = pick  # new — not yet resolved

    # Resolve all OPEN picks
    n_resolved = 0
    for pid, pick in list(tracked.items()):
        if not pick.get("shadow_outcome"):
            resolved = _resolve_pick(pick, now)
            if resolved.get("shadow_outcome"):
                n_resolved += 1
            tracked[pid] = resolved

    picks_list = list(tracked.values())
    summary = _compute_summary(picks_list)

    result = {
        "shadow_mode": True,
        "shadow_start": "2026-05-17",
        "shadow_end": SHADOW_END.isoformat(),
        "promotion_decision_date": "2026-05-31",
        "generated_at": now.isoformat(),
        "n_newly_resolved": n_resolved,
        "summary": summary,
        "picks": picks_list,
    }

    status_line = (
        f"[shadow-tracker] n={summary['n_total']} open={summary['n_open']} "
        f"closed={summary['n_closed']} WR={summary['win_rate']} PF={summary['profit_factor']} "
        f"newly_resolved={n_resolved}"
    )
    print(status_line)

    if dry_run:
        print("[shadow-tracker] DRY-RUN — not writing log")
        print(json.dumps({k: v for k, v in result.items() if k != "picks"}, indent=2))
        return 0

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[shadow-tracker] Wrote {LOG_PATH}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="New-strategies shadow performance tracker")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        return run_shadow_tracker(dry_run=args.dry_run)
    except Exception as exc:
        print(f"[shadow-tracker] ERROR: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
