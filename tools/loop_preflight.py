#!/usr/bin/env python3
"""loop_preflight.py — the FAIL-CLOSED admission gate for the Master Loop.

GROK4_3 review P0 (docs/GROK4_3_JUNE112026.MD, 2026-06-11): "the
self-correcting properties live mostly in prose and opt-in sidecars... the
highest-leverage missing piece is a single executable admission/preflight gate
that actually refuses to run or publish when H1 is red, pre-registration is
absent, or a family is closed."

This is that gate. Run it BEFORE any replay batch, promotion, or weekly
scorecard publish:

    python3 tools/loop_preflight.py --asset-class CRYPTO --family my_new_family
    # exit 0 = GO; exit 1 = BLOCKED (reasons on stdout). ANY check error = BLOCKED.

Checks (each independently fail-closed):
  H1     measurement-integrity guards green (sign-coherence flips == 0;
         terminal NULL-pnl below threshold; recent dup-rate sane)
  PREREG an ACTIVE entry for --family exists in reports/hypothesis_registry.json
         with a non-empty falsification clause (M-107)
  FAMILY the registry entry is not closed / comparisons-exhausted
  DNR    the family does not match the do-not-relitigate list

Skip individual checks only with an explicit --skip (logged loudly) — the
default is everything on.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

REGISTRY = REPO / "reports" / "hypothesis_registry.json"

# Master loop §8 — refuted families. Substring match, case-insensitive.
DO_NOT_RELITIGATE = [
    "stocks_rsi2_pullback", "direction_flip", "direction-flip",
    "futures_momentum", "forex_rsi2", "luxalgo_best", "meanreversionbb",
    "trust7", "trust_7", "kimi_ultimate_proven_edge", "vrp_pilot",
    "myfxbook", "ig_contrarian",
]

NULL_PNL_MAX = 200          # terminal NULL-pnl rows; was 737 pre-fix, ~125 healthy
DUP_RATE_MAX = 0.45         # 7d share of rows beyond (sym,strat,dir,day) keys


def _fail(reasons: list[str]) -> None:
    print("PREFLIGHT: BLOCKED")
    for r in reasons:
        print(f"  - {r}")
    sys.exit(1)


def check_h1() -> list[str]:
    """Measurement-integrity guards. Any DB/tool error = fail closed."""
    problems: list[str] = []
    try:
        from tools.db_env import get_stocks_creds
        import pymysql
        keep = ("host", "user", "password", "database", "port", "connect_timeout")
        conn = pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})
        cur = conn.cursor()
        # sign-coherence: WON/TP_HIT rows with negative pnl must be 0
        cur.execute(
            "SELECT COUNT(*) FROM trading_picks WHERE status IN ('WON','TP_HIT') "
            "AND pnl_pct < -0.01 AND exit_price IS NOT NULL")
        flips = cur.fetchone()[0]
        if flips:
            problems.append(f"H1: {flips} sign-incoherent WON rows (must be 0)")
        # terminal NULL-pnl regrowth
        cur.execute(
            "SELECT COUNT(*) FROM trading_picks WHERE status IN "
            "('TP_HIT','SL_HIT','LOST','TIME_EXIT') AND pnl_pct IS NULL")
        nulls = cur.fetchone()[0]
        if nulls > NULL_PNL_MAX:
            problems.append(f"H1: terminal NULL-pnl regrew to {nulls} (>{NULL_PNL_MAX})")
        # 7d duplicate-emission rate — WARNING only: replay batches dedup
        # internally (per-symbol-day), so emission dups cannot contaminate a
        # replay; they DO affect forward-lane n quality, so surface loudly.
        cur.execute(
            "SELECT COUNT(*), COUNT(DISTINCT CONCAT(symbol,'|',COALESCE(strategy,''),"
            "'|',COALESCE(direction,''),'|',DATE(created_at))) FROM trading_picks "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
        total, uniq = cur.fetchone()
        if total and (1 - uniq / total) > DUP_RATE_MAX:
            print(f"PREFLIGHT WARNING: 7d emission dup-rate "
                  f"{(1 - uniq / total):.0%} (>{DUP_RATE_MAX:.0%}) — forward-lane "
                  f"n quality degraded; emission hygiene item, not a replay blocker")
        conn.close()
    except Exception as exc:  # fail CLOSED
        problems.append(f"H1: check errored ({exc}) — failing closed")
    return problems


def check_prereg(family: str) -> list[str]:
    """M-107: an ACTIVE registry entry with a falsification clause must exist."""
    try:
        data = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
        entries = data.get("hypotheses") or data.get("entries") or (
            data if isinstance(data, list) else [])
        for e in entries:
            if not isinstance(e, dict):
                continue
            name = str(e.get("family") or e.get("name") or e.get("id") or "")
            if family.lower() in name.lower() or name.lower() in family.lower():
                status = str(e.get("status") or "").upper()
                if status in ("CLOSED", "EXHAUSTED", "REFUTED"):
                    return [f"FAMILY: '{name}' is {status} — no further comparisons (anti-circling)"]
                if not (e.get("falsification") or e.get("kill_criteria")):
                    return [f"PREREG: entry '{name}' lacks a falsification clause (M-107)"]
                return []  # active + falsifiable -> pass
        return [f"PREREG: no registry entry matches family '{family}' — "
                f"pre-register in {REGISTRY.relative_to(REPO)} before running (M-107)"]
    except Exception as exc:
        return [f"PREREG: check errored ({exc}) — failing closed"]


def check_dnr(family: str) -> list[str]:
    fam = family.lower().replace("-", "_")
    hits = [b for b in DO_NOT_RELITIGATE if b.replace("-", "_") in fam]
    return [f"DNR: family matches do-not-relitigate entry '{h}'" for h in hits]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--asset-class", required=True)
    ap.add_argument("--family", required=True,
                    help="tuning-family / hypothesis name being run")
    ap.add_argument("--skip", default="",
                    help="comma list of checks to skip (h1,prereg,dnr) — logged loudly")
    args = ap.parse_args()

    skips = {s.strip().lower() for s in args.skip.split(",") if s.strip()}
    for s in skips:
        print(f"PREFLIGHT WARNING: check '{s}' explicitly skipped by operator flag")

    problems: list[str] = []
    if "h1" not in skips:
        problems += check_h1()
    if "dnr" not in skips:
        problems += check_dnr(args.family)
    if "prereg" not in skips:
        problems += check_prereg(args.family)

    if problems:
        _fail(problems)
    print(f"PREFLIGHT: GO  (class={args.asset_class} family={args.family}; "
          f"checks: h1{'(skip)' if 'h1' in skips else ''} prereg"
          f"{'(skip)' if 'prereg' in skips else ''} dnr{'(skip)' if 'dnr' in skips else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
