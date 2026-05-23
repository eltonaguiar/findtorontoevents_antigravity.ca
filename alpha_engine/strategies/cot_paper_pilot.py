#!/usr/bin/env python3
"""COT Paper Pilot — SHADOW state tracker for cot_positioning + CT=F.

SUPREME EDGE 2026-05-12 — user accepted single-class deviation. This script
provides an isolated paper-pilot ledger for the DSR=1.0000 verified
cot_positioning + CT=F edge (n=100, WR 90%, Sharpe +1.377) ahead of any
real-money LIVE_EXECUTION decision.

## Architecture

Reads existing trading_picks rows WHERE strategy='cot_positioning' AND
symbol='CT=F' (no new pick emission — the strategy is already running per
Agent A DB probe). Computes rolling P&L at 1-contract notional ($5/tick × 50,000
lb cotton contract), compares to expected $3.40-$13.40 net per trade.

Output: audit_dashboard/data/cot_paper_pilot_status.json — consumed by
audit_dashboard/paper_pilot.html viewer.

## Codex SHADOW state advance

Per master plan governance:
  REHAB → OOS_READY (DSR>=0.95 + n>=100 + Tier-2 metrics) ← already verified
  OOS_READY → SHADOW (14-30d forward shadow tracking) ← THIS PILOT
  SHADOW → LIVE_ELIGIBLE (variance ±50% of expected for 4+ weeks)

## Graduation gate

After 4 weeks of paper tracking:
  - Net P&L within ±50% of expected $3.40-$13.40/trade × n_trades → READY
  - Net P&L outside band → FAIL (back to REHAB; re-investigate)
  - n_trades < 4 → INSUFFICIENT_DATA (extend window)

Usage:
    python alpha_engine/strategies/cot_paper_pilot.py            # default
    python alpha_engine/strategies/cot_paper_pilot.py --dry-run  # no JSON write
    python alpha_engine/strategies/cot_paper_pilot.py --window-days 60

NFA — paper pilot only. No real-money sizing without user explicit approval +
graduation gate clear.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, date, timezone, timedelta
from pathlib import Path

# --- OVER-EMISSION FALSIFICATION (2026-05-13) -------------------------------
# The COT paper pilot RE-EMITS the same weekly CFTC COT release every scanner
# cycle (hourly). Counting each re-emission as a separate trade inflates the
# headline: WR 90.1%->40%, PF 2.73->0.17, n=101->5 real releases once
# consolidated. The tier was falsely TIER_1_RENAISSANCE / DSR 1.0 on n=5.
# Falsified by:
#   reports/cot_paper_pilot_overemission_falsified_20260513.md  (over-emission)
#   reports/cot_timing_leakage_audit_2026-05-13.md              (look-ahead leak)
# Three independent AI audits (MiMo, Sauna) flagged the live status JSON.
# FIX: deduplicate trades by CFTC release week (one trade per unique weekly
# report period) before computing n_total / wr_pct / cum_pnl / tier / dsr.
FALSIFICATION_REFS = [
    "reports/cot_paper_pilot_overemission_falsified_20260513.md",
    "reports/cot_timing_leakage_audit_2026-05-13.md",
]
# CFTC publishes the COT report Friday ~3:30pm ET, covering positions as of the
# PRIOR Tuesday's settlement. One COT release == one Tuesday report period.
# Minimum unique releases before any institutional tier is allowed.
MIN_UNIQUE_RELEASES_FOR_TIER = 20
INSUFFICIENT_N_TIER = "SHADOW_INSUFFICIENT_N"

try:
    import pymysql
except ImportError:
    print("ERROR: pymysql not installed", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent.parent

# Contract spec
CONTRACT_NOTIONAL_LBS = 50_000
TICK_USD = 5.00   # $0.0001/lb × 50,000 lbs = $5
ROUND_TRIP_COST_USD = 10.00  # $5 commission + $5 slippage
EXPECTED_NET_PER_TRADE_USD_LOW = 3.40
EXPECTED_NET_PER_TRADE_USD_HIGH = 13.40


def connect():
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=os.environ.get("DB_STOCKS_PASSWORD", "stocks"),
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        connect_timeout=30,
        read_timeout=60,
    )


def fetch_cot_picks(cur, window_days: int):
    """Pull cot_positioning + CT=F closed picks within window_days."""
    cur.execute(f"""
        SELECT id, status, direction, entry_price, exit_price, pnl_pct,
               created_at, closed_at
        FROM trading_picks
        WHERE strategy = 'cot_positioning'
          AND symbol = 'CT=F'
          AND created_at >= NOW() - INTERVAL %s DAY
        ORDER BY created_at DESC
    """, (window_days,))
    return cur.fetchall()


def _parse_entry_dt(value) -> datetime | None:
    """Parse a pick entry timestamp (created_at) into a datetime, or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:len(fmt) + 2], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def cot_release_week_key(entry_dt: datetime | date) -> str:
    """Map a pick's entry timestamp to its CFTC COT release week.

    The CFTC COT report covers positions as of a TUESDAY settlement and is
    published the following Friday. Every pick that fires within the same
    publication week is a RE-EMISSION of one weekly release, not a new trade.

    Dedup key = ISO year-week of the Tuesday whose report period the pick
    belongs to. We snap the entry date back to the most recent Tuesday
    (Monday is treated as belonging to the prior week's Tuesday release,
    since the report is not refreshed until the next Friday). Returns a
    stable string like "2026-W18" so trades inside one Tue->Mon cycle
    collapse to a single release.
    """
    d = entry_dt.date() if isinstance(entry_dt, datetime) else entry_dt
    # weekday(): Mon=0 .. Sun=6 ; Tuesday=1. Snap back to the latest Tuesday.
    days_since_tuesday = (d.weekday() - 1) % 7
    release_tuesday = d - timedelta(days=days_since_tuesday)
    iso_year, iso_week, _ = release_tuesday.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def dedupe_by_release_week(closed_rows):
    """Collapse over-emitted picks to ONE trade per unique CFTC release week.

    Same weekly COT signal re-fires hourly across multiple days; only the
    FIRST chronological pick of each (release_week) cycle is the canonical
    trade. Returns the deduped list sorted oldest-first, each row annotated
    with its 'release_week' key.

    This is the over-emission fix from
    reports/cot_paper_pilot_overemission_falsified_20260513.md.
    """
    annotated = []
    for r in closed_rows:
        entry_dt = _parse_entry_dt(r.get("created_at"))
        if entry_dt is None:
            # No usable timestamp -> cannot assign a release week; keep as its
            # own singleton so it is neither dropped nor merged spuriously.
            week = f"UNKNOWN::{r.get('id')}"
        else:
            week = cot_release_week_key(entry_dt)
        annotated.append((entry_dt or datetime.max, week, r))
    # Sort oldest-first so "first chronological pick" is well-defined.
    annotated.sort(key=lambda t: t[0])
    seen = {}
    for entry_dt, week, r in annotated:
        if week not in seen:
            r = dict(r)
            r["release_week"] = week
            seen[week] = r
    # Return oldest-first.
    return sorted(seen.values(),
                  key=lambda r: _parse_entry_dt(r.get("created_at")) or datetime.max)


def compute_paper_pnl(rows, base_price_usd_per_lb: float = 0.70):
    """For each UNIQUE COT release compute paper-pilot P&L in USD per 1 contract.

    Approximation: pnl_pct × current price × contract_size.

    OVER-EMISSION FIX (2026-05-13): the raw rows over-count each weekly CFTC
    release ~20x (same signal re-fired hourly). We deduplicate to one trade
    per release week BEFORE computing n_total / wr_pct / cum_pnl so the
    headline reflects real signal cycles, not scanner cadence. See
    reports/cot_paper_pilot_overemission_falsified_20260513.md.
    """
    raw_closed = [r for r in rows if r["status"] in ("WON", "LOST", "WIN", "LOSS", "TP_HIT", "SL_HIT")]
    n_raw_emissions = len(raw_closed)

    # DEDUPE: one canonical trade per unique CFTC weekly release.
    closed = dedupe_by_release_week(raw_closed)

    notional_usd = base_price_usd_per_lb * CONTRACT_NOTIONAL_LBS  # ~$35,000

    trades = []
    cum_pnl = 0.0
    n_wins = 0
    n_losses = 0
    for r in closed:
        pnl_pct = float(r.get("pnl_pct") or 0.0)
        pnl_usd_gross = pnl_pct / 100.0 * notional_usd
        pnl_usd_net = pnl_usd_gross - ROUND_TRIP_COST_USD
        cum_pnl += pnl_usd_net
        if r["status"] in ("WON", "WIN", "TP_HIT"):
            n_wins += 1
        elif r["status"] in ("LOST", "LOSS", "SL_HIT"):
            n_losses += 1
        trades.append({
            "id": r.get("id"),
            "release_week": r.get("release_week"),
            "status": r["status"],
            "direction": r.get("direction"),
            "entry_price": float(r.get("entry_price") or 0.0),
            "exit_price": float(r.get("exit_price") or 0.0),
            "pnl_pct": pnl_pct,
            "pnl_usd_gross": round(pnl_usd_gross, 2),
            "pnl_usd_net": round(pnl_usd_net, 2),
            "cum_pnl_net": round(cum_pnl, 2),
            "created_at": str(r.get("created_at") or ""),
            "closed_at": str(r.get("closed_at") or ""),
        })

    n_total = len(closed)  # unique COT release weeks (deduped)
    wr = (n_wins * 100.0 / n_total) if n_total else 0.0
    avg_pnl_net = (cum_pnl / n_total) if n_total else 0.0

    return {
        "n_total": n_total,
        "n_wins": n_wins,
        "n_losses": n_losses,
        "wr_pct": round(wr, 2),
        "cum_pnl_usd": round(cum_pnl, 2),
        "avg_pnl_per_trade_usd": round(avg_pnl_net, 2),
        "expected_per_trade_low_usd": EXPECTED_NET_PER_TRADE_USD_LOW,
        "expected_per_trade_high_usd": EXPECTED_NET_PER_TRADE_USD_HIGH,
        # Over-emission accounting: n_total is unique releases; n_raw_emissions
        # is the pre-dedup re-emission count. ratio >> 1 == over-emission.
        "n_unique_releases": n_total,
        "n_raw_emissions": n_raw_emissions,
        "over_emission_ratio": round(n_raw_emissions / n_total, 2) if n_total else None,
        "dedup_basis": "one trade per unique CFTC COT release week (Tue report period)",
        "trades": trades,
    }


def graduation_gate_verdict(stats: dict, min_trades: int = 4) -> dict:
    """Determine SHADOW → LIVE_ELIGIBLE gate state."""
    n = stats["n_total"]
    if n < min_trades:
        return {
            "verdict": "INSUFFICIENT_DATA",
            "detail": f"need {min_trades}+ trades, have {n}",
            "ready_for_live": False,
        }
    avg = stats["avg_pnl_per_trade_usd"]
    expected_low = stats["expected_per_trade_low_usd"]
    expected_high = stats["expected_per_trade_high_usd"]
    # Within ±50% of [expected_low, expected_high] midpoint
    mid = (expected_low + expected_high) / 2.0
    tol_low = mid * 0.5
    tol_high = mid * 1.5
    if tol_low <= avg <= tol_high:
        return {
            "verdict": "READY_FOR_LIVE",
            "detail": f"avg ${avg} within tolerance band [${tol_low:.2f}, ${tol_high:.2f}]",
            "ready_for_live": True,
        }
    if avg < tol_low:
        return {
            "verdict": "BELOW_EXPECTED",
            "detail": f"avg ${avg} below tolerance floor ${tol_low:.2f}; investigate before sizing",
            "ready_for_live": False,
        }
    return {
        "verdict": "ABOVE_EXPECTED",
        "detail": f"avg ${avg} above tolerance ceiling ${tol_high:.2f}; verify (possible regime tailwind)",
        "ready_for_live": False,
    }


def gate_tier_and_dsr(stats: dict) -> dict:
    """Gate the institutional tier + DSR on the DEDUPED unique-release count.

    The headline TIER_1_RENAISSANCE / DSR 1.0 was an over-emission artifact:
    it was computed on ~101 re-emissions of only 5 real CFTC releases. A tier
    that strong (and DSR=1.0) MUST NOT be emitted on n<20 unique releases.

    Returns the tier string, dsr value (null on insufficient n), and a
    self-documenting note pointing at the falsification reports.
    """
    n = stats["n_total"]  # unique COT release weeks
    if n < MIN_UNIQUE_RELEASES_FOR_TIER:
        return {
            "tier": INSUFFICIENT_N_TIER,
            "dsr": None,
            "dsr_note": (
                f"DSR withheld: only {n} unique CFTC COT releases (need "
                f">={MIN_UNIQUE_RELEASES_FOR_TIER}). The prior DSR=1.0 / "
                "TIER_1_RENAISSANCE headline was an over-emission artifact "
                "(~20x re-emission of the same weekly release inflated n and "
                "WR). DSR=1.0 cannot be honestly emitted on this sample. See "
                + " ; ".join(FALSIFICATION_REFS) + "."
            ),
            "tier_note": (
                f"Tier downgraded to {INSUFFICIENT_N_TIER}: deduped "
                f"n={n} < {MIN_UNIQUE_RELEASES_FOR_TIER} unique releases."
            ),
        }
    # n>=20 unique releases: a tier may be assigned, but DSR still requires an
    # honest recomputation on the deduped series (out of scope for this
    # paper-pilot tracker), so emit null until that is wired.
    return {
        "tier": "TIER_PENDING_DEDUPED_DSR",
        "dsr": None,
        "dsr_note": (
            f"{n} unique releases meets the n-floor; DSR must be recomputed "
            "on the deduped release series before a tier is asserted. Prior "
            "DSR=1.0 was computed on over-emitted data and is void. See "
            + " ; ".join(FALSIFICATION_REFS) + "."
        ),
        "tier_note": (
            f"n={n} unique releases >= floor; tier held PENDING honest "
            "deduped DSR/PF/Sharpe recompute."
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--window-days", type=int, default=28,
                   help="Lookback window in days (default 28 = 4 weeks for SHADOW gate)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out", default="audit_dashboard/data/cot_paper_pilot_status.json")
    p.add_argument("--base-price", type=float, default=0.70,
                   help="Reference cotton price USD/lb for notional sizing")
    args = p.parse_args()

    print(f"# COT Paper Pilot — cot_positioning + CT=F", file=sys.stderr)
    print(f"# Window: {args.window_days} days  Base price: ${args.base_price}/lb", file=sys.stderr)

    try:
        conn = connect()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor(pymysql.cursors.DictCursor)
    rows = fetch_cot_picks(cur, args.window_days)
    cur.close()
    conn.close()

    stats = compute_paper_pnl(rows, args.base_price)
    gate = graduation_gate_verdict(stats)
    tier_gate = gate_tier_and_dsr(stats)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy_name": "cot_positioning",
        "symbol": "CT=F",
        "asset_class": "COMMODITY",
        # tier + dsr are GATED on deduped unique-release count. The historical
        # TIER_1_RENAISSANCE / DSR 1.0 headline was an over-emission artifact;
        # see falsification_refs below.
        "tier": tier_gate["tier"],
        "dsr": tier_gate["dsr"],
        "dsr_note": tier_gate["dsr_note"],
        "tier_note": tier_gate["tier_note"],
        "falsification_refs": FALSIFICATION_REFS,
        "evidence_source": "deduped paper-pilot ledger (one trade per CFTC COT release week)",
        "contract_spec": {
            "exchange": "ICE Futures US",
            "size_lbs": CONTRACT_NOTIONAL_LBS,
            "tick_usd": TICK_USD,
            "round_trip_cost_usd": ROUND_TRIP_COST_USD,
            "base_price_usd_per_lb": args.base_price,
            "notional_usd": round(args.base_price * CONTRACT_NOTIONAL_LBS, 2),
            "micro_contract_available": False,
        },
        "window_days": args.window_days,
        "stats": stats,
        "graduation_gate": gate,
        "codex_state_machine": {
            "current_state": "OOS_READY" if stats["n_total"] >= 4 else "REHAB",
            "next_state": "SHADOW" if gate["ready_for_live"] else "OOS_READY",
            "target_state": "LIVE_ELIGIBLE",
            "global_blockers": [
                "all-classes-first per Codex governance (currently 0/6 SHADOW)",
                "user single-class deviation accepted 2026-05-12",
            ],
        },
        "nfa": "Research surface only. No real-money sizing without explicit user approval + graduation gate clear.",
    }

    print(f"# n_trades={stats['n_total']}  WR={stats['wr_pct']}%  cum_pnl=${stats['cum_pnl_usd']}  avg=${stats['avg_pnl_per_trade_usd']}", file=sys.stderr)
    print(f"# Graduation: {gate['verdict']}  ready_for_live={gate['ready_for_live']}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"# wrote {out_path}  ({out_path.stat().st_size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
