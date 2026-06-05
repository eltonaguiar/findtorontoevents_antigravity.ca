#!/usr/bin/env python3
"""Track prediction_market_consensus paper pilot against live at_pick_outcomes.

Queries ejaguiar1_stocks.at_pick_outcomes for new resolved WON/LOST trades
since the pilot's enabled_at timestamp, updates forward statistics,
checks kill-switch criteria, and appends events to the log.

Dry-run by default; pass --execute to mutate state + log files.

Usage:
    DB_PASS_STOCKS=... python tools/track_pmc_paper_pilot.py
    DB_PASS_STOCKS=... python tools/track_pmc_paper_pilot.py --execute
"""
from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow running as script without package import boilerplate
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.db_env import get_stocks_creds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("track_pmc_paper_pilot")

# ── Paths ────────────────────────────────────────────────────────────────────
PILOT_DIR = Path("verified_strategies/paper_pilot")
STATE_PATH = PILOT_DIR / "prediction_market_consensus_state.json"
LOG_PATH = PILOT_DIR / "prediction_market_consensus_paper_log.jsonl"

# ── State helpers ────────────────────────────────────────────────────────────


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            log.error("State file corrupt (%s) — aborting.", exc)
            sys.exit(1)
    log.error("State file missing: %s", STATE_PATH)
    sys.exit(1)


def _save_state(state: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(row: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


# ── DB ───────────────────────────────────────────────────────────────────────


def _connect() -> Any:
    import pymysql

    creds = get_stocks_creds(raise_on_missing=True)
    return pymysql.connect(
        host=creds["host"],
        user=creds["user"],
        password=creds["password"],
        database=creds["database"],
        port=creds["port"],
        connect_timeout=creds["connect_timeout"],
        read_timeout=creds["read_timeout"],
        cursorclass=pymysql.cursors.DictCursor,
    )


def fetch_forward_outcomes(enabled_at: str) -> List[Dict[str, Any]]:
    """Return resolved WON/LOST rows for prediction_market_consensus since enabled_at."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT status, pnl_pct, resolved_at
        FROM at_pick_outcomes
        WHERE strategy = 'prediction_market_consensus'
          AND status IN ('WON', 'LOST')
          AND resolved_at >= %s
        ORDER BY resolved_at ASC
        """,
        (enabled_at,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ── Stats ────────────────────────────────────────────────────────────────────


def compute_forward_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute n, wr, pf, drawdown_pct from ordered outcome rows."""
    n = len(rows)
    if n == 0:
        return {"n": 0, "wr": None, "pf": None, "drawdown_pct": 0.0}

    wins = 0
    gross_profit = 0.0
    gross_loss = 0.0
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    consecutive_losses = 0
    max_consecutive_losses = 0

    for r in rows:
        try:
            pnl = float(r.get("pnl_pct") or 0)
        except (TypeError, ValueError):
            pnl = 0.0

        cumulative += pnl
        peak = max(peak, cumulative)
        dd = peak - cumulative
        max_dd = max(max_dd, dd)

        if pnl > 0:
            wins += 1
            gross_profit += pnl
            consecutive_losses = 0
        elif pnl < 0:
            gross_loss += abs(pnl)
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            # zero PnL — use status label
            status = str(r.get("status") or "").upper()
            if status == "WON":
                wins += 1
                consecutive_losses = 0
            else:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

    wr = round(100.0 * wins / n, 2) if n else 0.0
    pf = round(gross_profit / gross_loss, 3) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    drawdown_pct = round(max_dd, 3)

    return {
        "n": n,
        "wr": wr,
        "pf": pf,
        "drawdown_pct": drawdown_pct,
        "max_consecutive_losses": max_consecutive_losses,
    }


# ── Kill switch ──────────────────────────────────────────────────────────────


def check_kill_switch(stats: Dict[str, Any], state: dict) -> List[str]:
    """Return list of triggered kill reasons (empty if none)."""
    ks = state.get("kill_switch", {})
    reasons = []

    forward_wr_below = ks.get("forward_wr_below")
    if forward_wr_below is not None and stats["n"] > 0 and stats["wr"] is not None:
        if stats["wr"] < forward_wr_below:
            reasons.append(f"forward_wr_below_{forward_wr_below}")

    max_dd = ks.get("max_drawdown_pct")
    if max_dd is not None and stats["drawdown_pct"] > max_dd:
        reasons.append(f"max_drawdown_pct_above_{max_dd}")

    consec = ks.get("consecutive_losses")
    if consec is not None and stats.get("max_consecutive_losses", 0) >= consec:
        reasons.append(f"consecutive_losses_{consec}")

    return reasons


def check_promotion(stats: Dict[str, Any], state: dict) -> List[str]:
    """Return list of satisfied promotion criteria (empty if not all met)."""
    pc = state.get("promotion_criteria", {})
    satisfied = []

    min_n = pc.get("min_forward_n")
    if min_n is not None and stats["n"] >= min_n:
        satisfied.append("min_forward_n")
    elif min_n is not None:
        return []  # hard gate — need enough sample first

    min_wr = pc.get("min_wr")
    if min_wr is not None and stats["wr"] is not None and stats["wr"] >= min_wr:
        satisfied.append("min_wr")
    elif min_wr is not None:
        return []

    min_pf = pc.get("min_pf")
    if min_pf is not None and stats["pf"] is not None and stats["pf"] >= min_pf:
        satisfied.append("min_pf")
    elif min_pf is not None:
        return []

    max_dd = pc.get("max_drawdown_pct")
    if max_dd is not None and stats["drawdown_pct"] <= max_dd:
        satisfied.append("max_drawdown")
    elif max_dd is not None:
        return []

    return satisfied


# ── Main ─────────────────────────────────────────────────────────────────────


def build_status_report(state: dict, stats: Dict[str, Any], kill_reasons: List[str], promo_reasons: List[str]) -> Dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy": state["strategy"],
        "asset_class": state["asset_class"],
        "status": state["status"],
        "enabled_at": state["enabled_at"],
        "forward_stats": stats,
        "kill_switch": {
            "active": bool(kill_reasons),
            "reasons": kill_reasons,
        },
        "promotion": {
            "eligible": bool(promo_reasons),
            "satisfied_criteria": promo_reasons,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write updated state + log. Default is dry run.",
    )
    parser.add_argument(
        "--db-host", type=str, default=None, help="MySQL host override."
    )
    parser.add_argument(
        "--db-user", type=str, default=None, help="MySQL user override."
    )
    parser.add_argument(
        "--db-pass", type=str, default=None, help="MySQL password override."
    )
    parser.add_argument(
        "--db-name", type=str, default=None, help="MySQL database override."
    )
    args = parser.parse_args()

    # Override DB env for this run if explicitly passed
    if args.db_host:
        os.environ["DB_HOST_STOCKS"] = args.db_host
    if args.db_user:
        os.environ["DB_USER_STOCKS"] = args.db_user
    if args.db_pass:
        os.environ["DB_PASS_STOCKS"] = args.db_pass
    if args.db_name:
        os.environ["DB_NAME_STOCKS"] = args.db_name

    state = _load_state()
    enabled_at = state["enabled_at"]

    log.info("Fetching forward outcomes for strategy=%s since %s", state["strategy"], enabled_at)
    rows = fetch_forward_outcomes(enabled_at)
    log.info("Found %d new resolved trades", len(rows))

    stats = compute_forward_stats(rows)
    log.info("Forward stats: n=%d wr=%s pf=%s drawdown=%s%%", stats["n"], stats["wr"], stats["pf"], stats["drawdown_pct"])

    kill_reasons = check_kill_switch(stats, state)
    promo_reasons = check_promotion(stats, state)

    report = build_status_report(state, stats, kill_reasons, promo_reasons)
    print(json.dumps(report, indent=2, default=str))

    # Event log entry
    event: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "FORWARD_TICK",
        "forward_n": stats["n"],
        "forward_wr": stats["wr"],
        "forward_pf": stats["pf"],
        "drawdown_pct": stats["drawdown_pct"],
        "kill_reasons": kill_reasons,
        "promo_satisfied": promo_reasons,
    }

    if kill_reasons:
        event["event"] = "KILL_SWITCH_TRIGGERED"
        log.warning("KILL SWITCH TRIGGERED: %s", kill_reasons)
    elif promo_reasons:
        event["event"] = "PROMOTION_ELIGIBLE"
        log.info("Promotion criteria satisfied: %s", promo_reasons)

    if args.execute:
        new_state = copy.deepcopy(state)
        new_state["current_forward_stats"] = {
            "n": stats["n"],
            "wr": stats["wr"],
            "pf": stats["pf"],
            "drawdown_pct": stats["drawdown_pct"],
        }
        if kill_reasons:
            new_state["status"] = "KILLED"
            new_state["killed_at"] = datetime.now(timezone.utc).isoformat()
            new_state["kill_reasons"] = kill_reasons
        elif promo_reasons and state.get("status") == "ACTIVE_PAPER_PILOT":
            new_state["status"] = "PROMOTION_ELIGIBLE"

        _save_state(new_state)
        _append_log(event)
        log.info("State + log updated (execute mode).")
    else:
        log.info("Dry run — no files modified. Pass --execute to persist.")

    return 0 if not kill_reasons else 1


if __name__ == "__main__":
    sys.exit(main())
