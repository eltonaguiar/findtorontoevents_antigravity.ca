#!/usr/bin/env python3
"""Strategy Kill Switch — auto-disable toxic strategies from live MySQL performance data.

Connects to ejaguiar1_stocks, queries at_pick_outcomes for resolved (WON/LOST)
trades, and identifies strategies that breach safety thresholds.  In dry-run mode
(the default) it reports what WOULD be killed.  With --execute it persists the
report and appends newly killed strategies to alpha_engine/strategy_blocklist.py
so they are blocked on the next process start.

Usage:
    DB_PASS_STOCKS=... python tools/strategy_kill_switch.py
    DB_PASS_STOCKS=... python tools/strategy_kill_switch.py --execute
    DB_PASS_STOCKS=... python tools/strategy_kill_switch.py --execute --output-json audit_dashboard/data/strategy_kill_switch.json
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
log = logging.getLogger("strategy_kill_switch")

# ── Constants ────────────────────────────────────────────────────────────────
_CLASS_MAP = {
    "STOCKS": "EQUITY",
    "STOCK": "EQUITY",
    "MEME": "MEMECOIN",
    "PENNY": "PENNY_STOCK",
    "PENNYSTOCK": "PENNY_STOCK",
    "": "UNKNOWN",
}

_BLOCKLIST_PATH = Path("alpha_engine/strategy_blocklist.py")
_DEFAULT_OUTPUT_JSON = Path("audit_dashboard/data/strategy_kill_switch.json")
_AUDIT_JSONL = Path("audit_trail/data/strategy_kill_audit.jsonl")


def normalize_class(ac: str) -> str:
    ac = str(ac or "").upper().strip()
    return _CLASS_MAP.get(ac, ac or "UNKNOWN")


# ── DB ───────────────────────────────────────────────────────────────────────
def _connect(
    host: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
) -> Any:
    import pymysql

    if host and user and password and database:
        return pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=3306,
            connect_timeout=30,
            read_timeout=60,
            cursorclass=pymysql.cursors.DictCursor,
        )

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


def fetch_strategy_stats(
    min_trades: int,
    host: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Aggregate per-(asset_class, strategy) from at_pick_outcomes (WON/LOST only)."""
    conn = _connect(host=host, user=user, password=password, database=database)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT asset_class, strategy, status, pnl_pct
        FROM at_pick_outcomes
        WHERE status IN ('WON', 'LOST')
        """
    )
    rows = cur.fetchall()
    conn.close()

    buckets: Dict[Tuple[str, str], Dict[str, float]] = {}
    for r in rows:
        ac = normalize_class(r.get("asset_class"))
        strat = str(r.get("strategy") or "").strip() or "(unattributed)"
        key = (ac, strat)
        if key not in buckets:
            buckets[key] = {"n": 0, "wins": 0, "sum": 0.0}
        b = buckets[key]
        try:
            pnl = float(r.get("pnl_pct") or 0)
        except (TypeError, ValueError):
            pnl = 0.0
        b["n"] += 1
        b["sum"] += pnl
        if pnl > 0:
            b["wins"] += 1
        elif pnl == 0:
            # zero-pnl resolved: count by status label
            if str(r.get("status") or "").upper() == "WON":
                b["wins"] += 1

    out = []
    for (ac, strat), b in buckets.items():
        n = b["n"]
        if n < min_trades:
            continue
        wr = round(100.0 * b["wins"] / n, 2) if n else 0.0
        avg_pnl = round(b["sum"] / n, 6) if n else 0.0
        total_pnl = round(b["sum"], 4)
        out.append(
            {
                "asset_class": ac,
                "strategy": strat,
                "n": n,
                "wins": b["wins"],
                "losses": n - b["wins"],
                "wr": wr,
                "avg_pnl": avg_pnl,
                "total_pnl": total_pnl,
            }
        )
    out.sort(key=lambda x: (x["asset_class"], -x["n"]))
    return out


# ── Kill logic ───────────────────────────────────────────────────────────────
def evaluate_kills(
    stats: List[Dict[str, Any]],
    wr_floor: float,
    avg_pnl_floor: float,
    total_pnl_floor: float,
) -> List[Dict[str, Any]]:
    """Return strategies that breach one or more kill thresholds."""
    killed = []
    for s in stats:
        reasons = []
        if s["wr"] < wr_floor:
            reasons.append("wr_below_floor")
        if s["avg_pnl"] < avg_pnl_floor:
            reasons.append("avg_pnl_below_floor")
        if s["total_pnl"] < total_pnl_floor:
            reasons.append("total_pnl_destroyed")
        if reasons:
            row = copy.deepcopy(s)
            row["kill_reason"] = reasons
            row["kill_reason_human"] = ", ".join(reasons)
            killed.append(row)
    return killed


# ── Blocklist mutation (execute mode only) ───────────────────────────────────
def _already_in_blocklist(strategy_name: str, text: str) -> bool:
    """Check whether strategy_name already appears in _RETIRED_STRATEGIES (case-insensitive)."""
    target = strategy_name.casefold()
    start_marker = "_RETIRED_STRATEGIES = frozenset({"
    start_idx = text.find(start_marker)
    if start_idx == -1:
        return False
    # Find the end of _RETIRED_STRATEGIES block
    depth = 0
    end_idx = -1
    for i, ch in enumerate(text[start_idx + len(start_marker) :]):
        if ch == "{":
            depth += 1
        elif ch == "}":
            if depth == 0:
                end_idx = start_idx + len(start_marker) + i
                break
            depth -= 1
    if end_idx == -1:
        return False
    block = text[start_idx:end_idx]
    for match in re.finditer(r'"([^"]+)"', block):
        if match.group(1).casefold() == target:
            return True
    return False


def append_to_blocklist(
    new_kills: List[Dict[str, Any]], blocklist_path: Path = _BLOCKLIST_PATH
) -> Tuple[bool, List[str]]:
    """Safely append newly killed strategies to _RETIRED_STRATEGIES in blocklist.py.

    Returns (any_changes_made, list_of_added_strategies).
    """
    if not blocklist_path.exists():
        log.warning("Blocklist file not found: %s — skipping append", blocklist_path)
        return False, []

    src = blocklist_path.read_text(encoding="utf-8")

    # Determine which strategies are truly new
    to_add = []
    for k in new_kills:
        name = k["strategy"]
        if not _already_in_blocklist(name, src):
            to_add.append(k)

    if not to_add:
        log.info("All killed strategies already present in blocklist — nothing to append.")
        return False, []

    # Find the closing of _RETIRED_STRATEGIES = frozenset({ ... })
    # We locate the first `})` that appears after `_RETIRED_STRATEGIES = frozenset({`
    # and before the next top-level assignment.
    start_marker = "_RETIRED_STRATEGIES = frozenset({"
    start_idx = src.find(start_marker)
    if start_idx == -1:
        log.error("Could not find _RETIRED_STRATEGIES in blocklist — aborting append.")
        return False, []

    # Search forward for the closing `})` of this frozenset
    depth = 0
    close_idx = -1
    for i, ch in enumerate(src[start_idx + len(start_marker) :]):
        if ch == "{":
            depth += 1
        elif ch == "}":
            if depth == 0:
                close_idx = start_idx + len(start_marker) + i
                break
            depth -= 1

    if close_idx == -1:
        log.error("Could not find closing of _RETIRED_STRATEGIES — aborting append.")
        return False, []

    # Build insertion text
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    lines = [f"    # {now}: auto-killed by strategy_kill_switch.py"]
    for k in to_add:
        reasons = ", ".join(k["kill_reason"])
        lines.append(
            f'    # n={k["n"]} WR={k["wr"]}% avg_pnl={k["avg_pnl"]}% '
            f'total_pnl={k["total_pnl"]}%  reasons={reasons}'
        )
        lines.append(f'    "{k["strategy"]}",')
    insertion = "\n".join(lines) + "\n"

    # Splice
    new_src = src[:close_idx] + insertion + src[close_idx:]

    # Backup
    bak = blocklist_path.with_suffix(".py.bak")
    blocklist_path.rename(bak)
    log.info("Blocklist backup created: %s", bak)

    blocklist_path.write_text(new_src, encoding="utf-8")
    log.info("Appended %d strategies to %s", len(to_add), blocklist_path)
    return True, [k["strategy"] for k in to_add]


# ── Audit logging ────────────────────────────────────────────────────────────
def log_kills_to_audit(killed: List[Dict[str, Any]], audit_path: Path = _AUDIT_JSONL) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with audit_path.open("a", encoding="utf-8") as fh:
        for k in killed:
            entry = {
                "timestamp": now,
                "event": "STRATEGY_KILLED",
                "strategy": k["strategy"],
                "asset_class": k["asset_class"],
                "n": k["n"],
                "wr": k["wr"],
                "avg_pnl": k["avg_pnl"],
                "total_pnl": k["total_pnl"],
                "kill_reason": k["kill_reason"],
            }
            fh.write(json.dumps(entry, default=str) + "\n")
    log.info("Logged %d kill events to %s", len(killed), audit_path)


# ── Main ─────────────────────────────────────────────────────────────────────
def build_report(
    killed: List[Dict[str, Any]],
    evaluated: int,
    args: argparse.Namespace,
    started_at: str,
) -> Dict[str, Any]:
    return {
        "generated_at": started_at,
        "run_mode": "execute" if args.execute else "dry_run",
        "thresholds": {
            "min_trades": args.min_trades,
            "wr_floor": args.wr_floor,
            "avg_pnl_floor": args.avg_pnl_floor,
            "total_pnl_floor": args.total_pnl_floor,
        },
        "evaluated_strategies": evaluated,
        "killed_count": len(killed),
        "killed": killed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-disable toxic strategies based on live at_pick_outcomes performance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually append kills to blocklist and write persistent JSON. Default is dry run.",
    )
    parser.add_argument(
        "--min-trades",
        type=int,
        default=50,
        help="Minimum resolved trades for a strategy to be eligible for kill evaluation (default: 50).",
    )
    parser.add_argument(
        "--wr-floor",
        type=float,
        default=40.0,
        help="Win-rate floor %% — strategies below this are killed (default: 40).",
    )
    parser.add_argument(
        "--avg-pnl-floor",
        type=float,
        default=-2.0,
        help="Average PnL floor %% — strategies below this are killed (default: -2.0).",
    )
    parser.add_argument(
        "--total-pnl-floor",
        type=float,
        default=-100.0,
        help="Total cumulative PnL floor %% — strategies below this are killed (default: -100).",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Path to write JSON report (default: audit_dashboard/data/strategy_kill_switch.json).",
    )
    parser.add_argument(
        "--skip-blocklist",
        action="store_true",
        help="Even with --execute, skip mutating alpha_engine/strategy_blocklist.py.",
    )
    parser.add_argument(
        "--db-host",
        type=str,
        default=None,
        help="MySQL host (default: from env / mysql.50webs.com).",
    )
    parser.add_argument(
        "--db-user",
        type=str,
        default=None,
        help="MySQL user (default: from env / ejaguiar1_stocks).",
    )
    parser.add_argument(
        "--db-pass",
        type=str,
        default=None,
        help="MySQL password (default: from env vars like DB_PASS_STOCKS).",
    )
    parser.add_argument(
        "--db-name",
        type=str,
        default=None,
        help="MySQL database name (default: from env / ejaguiar1_stocks).",
    )

    args = parser.parse_args()

    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    log.info("Strategy Kill Switch starting — mode=%s", "EXECUTE" if args.execute else "DRY_RUN")
    log.info(
        "Thresholds: min_trades=%d wr_floor=%.1f%% avg_pnl_floor=%.2f%% total_pnl_floor=%.1f%%",
        args.min_trades,
        args.wr_floor,
        args.avg_pnl_floor,
        args.total_pnl_floor,
    )

    # Fetch
    log.info("Fetching resolved trades from at_pick_outcomes (min_trades=%d)...", args.min_trades)
    stats = fetch_strategy_stats(
        args.min_trades,
        host=args.db_host,
        user=args.db_user,
        password=args.db_pass,
        database=args.db_name,
    )
    log.info("Evaluated %d strategy buckets with n>=%d", len(stats), args.min_trades)

    # Evaluate
    killed = evaluate_kills(
        stats,
        wr_floor=args.wr_floor,
        avg_pnl_floor=args.avg_pnl_floor,
        total_pnl_floor=args.total_pnl_floor,
    )
    log.info("Killed strategies: %d", len(killed))

    # Report
    report = build_report(killed, len(stats), args, started_at)

    # Stdout (always)
    print(json.dumps(report, indent=2, default=str))

    # Execute actions
    if args.execute:
        output_path = Path(args.output_json) if args.output_json else _DEFAULT_OUTPUT_JSON
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
        log.info("Report written to %s", output_path)

        log_kills_to_audit(killed)

        if not args.skip_blocklist:
            changed, added = append_to_blocklist(killed)
            if changed:
                log.warning("Blocklist updated with %d new strategies: %s", len(added), added)
            else:
                log.info("No blocklist changes required.")
        else:
            log.info("--skip-blocklist set; blocklist.py left untouched.")
    else:
        log.info("Dry run complete — no persistent changes made.")
        if killed:
            log.warning(
                "Re-run with --execute to retire these strategies: %s",
                [k["strategy"] for k in killed],
            )


if __name__ == "__main__":  # pragma: no cover
    main()
