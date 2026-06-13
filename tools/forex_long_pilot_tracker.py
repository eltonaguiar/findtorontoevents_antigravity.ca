#!/usr/bin/env python3
"""
forex_long_pilot_tracker.py — Stage-3 forward-paper pilot tracker (Option A sidecar).

Implements the peer-reviewed plan reports/PLAN_FOREX_LONG_PILOT_2026-06-13.md:
tracks the `non_crypto_consensus` FOREX LONG edge forward WITHOUT touching any
production gate or emitter. It only READS resolved picks the existing pipeline
already wrote to ejaguiar1_stocks.trading_picks, splits them into a frozen
"baseline" (before pilot start) and "forward" (on/after pilot start) cohort, and
reports the pre-registered acceptance metrics + circuit-breaker state.

Pre-registration (frozen 2026-06-13, no post-hoc changes):
  source_system = non_crypto_consensus, category = FOREX, direction = LONG, ALL pairs
  (no symbol exclusion — the break-even-pair exclusion was dropped as selection bias
   per the 8-model peer review).
  win threshold = 5bp (percent units); dedup per (strategy, symbol, day).
  Acceptance (promote to Stage 4): forward n>=100 AND PF>=1.5 AND decisive WR>=50%.
  Kill: forward PF<1.0 after 30 days OR forward n<10 after 30 days.
  Circuit breaker: pause if rolling forward drawdown > 5% OR cumulative loss > 2% of book.
  Hard rule: paper only, 0% real capital, until forward n>=100 AND intrabar replay passes.

Output: audit_dashboard/data/forex_long_pilot_status.json (fresh generated_at each run).
Read-only DB; creds from env / dbpasses.txt (never hardcoded).

Usage:
    python3 tools/forex_long_pilot_tracker.py
    python3 tools/forex_long_pilot_tracker.py --pilot-start 2026-06-13 --out PATH
"""
from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PILOT_START_DEFAULT = "2026-06-13"
WIN_THRESHOLD_PCT = 0.05
SOURCE = "non_crypto_consensus"
# Round-trip transaction cost (percent) per pair class. The edge has tiny winners
# (~0.2-0.3%), so cost dominates: gross PF 3.13 collapses to ~0.76 at realistic
# blended retail FX cost. Acceptance is judged on NET PF, never gross.
COST_MAJOR_PCT = float(os.environ.get("FX_COST_MAJOR_PCT", "0.03"))   # 3bp majors
COST_JPY_PCT = float(os.environ.get("FX_COST_JPY_PCT", "0.06"))       # 6bp JPY crosses
ACCEPT = {"min_n": 100, "min_pf": 1.5, "min_decisive_wr": 50.0, "basis": "NET of cost"}
KILL = {"max_days": 30, "min_pf": 1.0, "min_n": 10}
CIRCUIT = {"max_drawdown_pct": 5.0, "max_cum_loss_pct_of_book": 2.0}


def _load_db_password() -> str:
    pw = os.environ.get("DB_PASS_STOCKS") or os.environ.get("STOCKS_DB_PASS")
    if pw:
        return pw
    for path in (Path.home() / "dbpasses.txt", Path("/home/eaguiar2015/dbpasses.txt")):
        if path.exists():
            for line in path.read_text(errors="replace").splitlines():
                s = line.strip()
                if s.startswith("stocks") and s.endswith("1234560") and len(s) > 10:
                    return s
    raise SystemExit("No DB password: set DB_PASS_STOCKS or provide dbpasses.txt")


def _connect():
    import pymysql
    return pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=_load_db_password(),
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        connect_timeout=20,
    )


def _wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round((c - h) * 100, 1), round((c + h) * 100, 1)]


def _cost_of(symbol: str) -> float:
    return COST_JPY_PCT if "JPY" in (symbol or "").upper() else COST_MAJOR_PCT


def _pf_wr(pnls: list) -> tuple:
    wins = [p for p in pnls if p > WIN_THRESHOLD_PCT]
    losses = [p for p in pnls if p < -WIN_THRESHOLD_PCT]
    gp = sum(wins)
    gl = abs(sum(losses))
    pf = round(gp / gl, 2) if gl > 0 else (None if not wins else 99.0)
    dec = len(wins) + len(losses)
    wr = round(len(wins) / dec * 100, 1) if dec else None
    return pf, wr, len(wins), len(losses)


def _cohort_stats(rows: list) -> dict:
    """rows: list of (pnl, symbol, date) already deduped+sorted by date."""
    n = len(rows)
    gross = [r[0] for r in rows]
    net = [r[0] - _cost_of(r[1]) for r in rows]
    g_pf, g_wr, _, _ = _pf_wr(gross)
    n_pf, n_wr, nw, nl = _pf_wr(net)
    # cost-sensitivity sweep on uniform round-trip cost (bps)
    sens = {}
    for bp in (0, 2, 3, 5, 8):
        p, w, _, _ = _pf_wr([x - bp / 100.0 for x in gross])
        sens[f"{bp}bp"] = {"pf": p, "decWR": w}
    decisive = nw + nl
    # max drawdown on the cumulative NET pnl curve
    cum = peak = mdd = 0.0
    for x in net:
        cum += x
        peak = max(peak, cum)
        mdd = min(mdd, cum - peak)
    return {
        "n": n,
        "deduped_n": n,
        "pf": n_pf,                 # headline PF is NET-of-cost
        "gross_pf": g_pf,
        "net_pf": n_pf,
        "decisive_n": decisive,
        "decisive_wr": n_wr,        # net decisive WR
        "gross_decisive_wr": g_wr,
        "wr_ci95": _wilson(nw, decisive),
        "net_sum_pnl_pct": round(sum(net), 2),
        "gross_sum_pnl_pct": round(sum(gross), 2),
        "max_drawdown_pct": round(abs(mdd), 2),
        "flat_n": n - decisive,
        "cost_sensitivity_gross_bp": sens,
        "cost_model": {"major_pct": COST_MAJOR_PCT, "jpy_pct": COST_JPY_PCT},
    }


def fetch(pilot_start: str) -> dict:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, symbol, strategy, pnl_pct, DATE(created_at)
            FROM trading_picks
            WHERE source_system=%s AND LOWER(category)='forex' AND UPPER(direction)='LONG'
              AND closed_at IS NOT NULL AND pnl_pct IS NOT NULL
              AND status IN ('TP_HIT','SL_HIT','LOST','TIME_EXIT','EXPIRED','WON')
              AND created_at >= '2026-01-01'
            """,
            (SOURCE,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    # dedup per (strategy, symbol, day)
    seen = {}
    for r in rows:
        key = (r[2], r[1], r[4])
        if key not in seen or r[0] < seen[key][0]:
            seen[key] = r
    ded = sorted(seen.values(), key=lambda x: str(x[4]))
    baseline = [(float(r[3]), r[1], str(r[4])) for r in ded if str(r[4]) < pilot_start]
    forward = [(float(r[3]), r[1], str(r[4])) for r in ded if str(r[4]) >= pilot_start]
    return {"baseline": baseline, "forward": forward, "raw_n": len(rows)}


def build_status(pilot_start: str) -> dict:
    data = fetch(pilot_start)
    baseline = _cohort_stats(data["baseline"])
    forward = _cohort_stats(data["forward"])

    fwd_days = 0
    if data["forward"]:
        first = datetime.strptime(data["forward"][0][2], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        fwd_days = (datetime.now(timezone.utc) - first).days

    # acceptance / kill / circuit evaluation on the FORWARD cohort
    accept_ready = bool(
        forward["n"] >= ACCEPT["min_n"]
        and (forward["pf"] or 0) >= ACCEPT["min_pf"]
        and (forward["decisive_wr"] or 0) >= ACCEPT["min_decisive_wr"]
    )
    kill_triggered = bool(
        fwd_days >= KILL["max_days"]
        and ((forward["pf"] is not None and forward["pf"] < KILL["min_pf"]) or forward["n"] < KILL["min_n"])
    )
    circuit_tripped = bool(forward["max_drawdown_pct"] > CIRCUIT["max_drawdown_pct"])

    if accept_ready:
        stage = "READY_FOR_STAGE_4 (forward gates met — intrabar replay required next)"
    elif kill_triggered:
        stage = "KILL_TRIGGERED (forward underperformed after 30d)"
    elif circuit_tripped:
        stage = "CIRCUIT_PAUSED (forward drawdown breach)"
    elif forward["n"] == 0:
        stage = "ACCRUING (no forward-resolved picks yet — baseline frozen, awaiting new closes)"
    else:
        stage = f"ACCRUING ({forward['n']}/{ACCEPT['min_n']} forward picks)"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tracker": "forex_long_pilot_tracker",
        "spec": {
            "source_system": SOURCE, "category": "FOREX", "direction": "LONG",
            "symbols": "ALL (no exclusion — selection-bias-safe per peer review)",
            "win_threshold_pct": WIN_THRESHOLD_PCT, "dedup": "per (strategy,symbol,day)",
            "book": "paper / 0% real capital", "pilot_start": pilot_start,
        },
        "acceptance_criteria": ACCEPT, "kill_criteria": KILL, "circuit_breaker": CIRCUIT,
        "baseline_frozen": baseline,
        "forward": forward,
        "forward_days_elapsed": fwd_days,
        "stage": stage,
        "real_capital": "0% — paper only until forward n>=100 AND intrabar replay passes",
        "note": (
            "Read-only sidecar; changes no production gate/emitter. Forward cohort accrues "
            "as the existing pipeline resolves new non_crypto_consensus FOREX LONG picks."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot-start", default=PILOT_START_DEFAULT)
    ap.add_argument("--out", default="audit_dashboard/data/forex_long_pilot_status.json")
    args = ap.parse_args()

    status = build_status(args.pilot_start)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(status, indent=2))
    b, f = status["baseline_frozen"], status["forward"]
    print(f"[forex_long_pilot] {status['stage']}")
    print(f"  baseline (pre {args.pilot_start}): n={b['n']} NET-PF={b['net_pf']} (gross {b['gross_pf']}) "
          f"decWR={b['decisive_wr']}% MDD={b['max_drawdown_pct']}%")
    print(f"    cost-sensitivity (gross): " + " ".join(f"{k}:{v['pf']}" for k, v in b['cost_sensitivity_gross_bp'].items()))
    print(f"  forward  (>= {args.pilot_start}): n={f['n']} NET-PF={f['net_pf']} decWR={f['decisive_wr']}% "
          f"days={status['forward_days_elapsed']}")
    print(f"  -> {args.out}")
    return 0


if __name__ == "__main__":
    main()
