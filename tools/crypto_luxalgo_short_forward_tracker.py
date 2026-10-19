#!/usr/bin/env python3
"""crypto_luxalgo_short_forward_tracker.py

!!! ENTRY_PRICE_CAVEAT (2026-07-03) — this tracker reads the honest ledger's
intrabar_pnl_pct, which is resolved off `entry_price`. That column mismatches
the OHLCV bar by ~2.9% median for luxalgo SHORT (9.9% for volume_spike). A
correct-bar-entry replay across all TP/SL bands LOSES (netPF 0.51-0.89) and does
NOT beat random shorts (regime control). See reports/FALSIFICATION_luxalgo_short_2026-07-03.md.
This status is therefore an UPPER BOUND, not a promotion verdict. Do NOT size on
PROMOTABLE_PROBATION until the ledger is re-resolved from correct bar-aligned entries.
 — forward-shadow gate tracker for the
program's strongest honest candidate: luxalgo_confluence SHORT (CRYPTO).

Pre-registered as H-20260612-luxalgo_confluence_v2_short (registered 2026-06-12,
FORWARD_OBSERVATION). This sidecar recomputes the PROMOTION-GATE-relevant numbers
on the pre-registered FORWARD window (created_at > 2026-06-12 only — zero
look-ahead, zero selection bias) every run and writes a status JSON the /audit
surface can read.

Honest methodology (matches reports/EDGE_HUNT_* discipline):
  - honest intrabar first-touch pnl (`intrabar_pnl_pct`, SL-wins-ties), non-ambiguous only
  - per-symbol-day dedup (one pick per symbol per UTC day)
  - net of 16bp crypto round-trip cost (pnl_pct is in PERCENT units -> subtract 0.16)
  - symbol-CLUSTER bootstrap net-PF CI-LB (5th pct, B=2000) — the gate number
  - time-split both-halves, single-name HHI, win-day concentration (crash-fade guard)

Promotion gate (ALL required, FORWARD cohort, net of cost):
  n_eff >= 80  AND  net-PF CI-LB > 1.15  AND  both time-halves net-PF > 1
  AND  single-name HHI < 0.15  AND  top-winning-day profit share < 0.50
Anything short -> status SHADOW_TRACKING with the failing gates listed. Do NOT size.

Opt-in / read-only sidecar (Wire-Up Rule): queries the DB, writes ONE status JSON.
It changes no production pick/score path.

    python3 tools/crypto_luxalgo_short_forward_tracker.py            # write status JSON
    python3 tools/crypto_luxalgo_short_forward_tracker.py --stdout   # print, no write
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools.db_env import get_stocks_creds  # noqa: E402
import pymysql  # noqa: E402

OUT_PATH = os.path.join(REPO, "audit_dashboard", "data", "crypto_luxalgo_short_forward_status.json")

FORWARD_START = "2026-06-12"   # pre-registration lock (H-20260612-luxalgo_confluence_v2_short)
COST_PCT = 0.16                # crypto 16bp round-trip, pnl in percent units
N_GATE = 80                    # pre-registered honest-n gate
CI_LB_GATE = 1.15
B = 2000
random.seed(42)


def _get_db():
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    return pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})


def _net_pf(rows):
    g = sum(max(e["pnl"] - COST_PCT, 0) for e in rows)
    l = sum(max(COST_PCT - e["pnl"], 0) for e in rows)
    return (g / l) if l > 0 else float("inf")


def _wr(rows):
    return 100 * sum(1 for e in rows if e["pnl"] - COST_PCT > 0) / len(rows) if rows else 0.0


def _cluster_ci_lb(rows):
    by_sym = defaultdict(list)
    for e in rows:
        by_sym[e["sym"]].append(e)
    keys = list(by_sym)
    if len(keys) < 2:
        return float("nan"), float("nan")
    pfs = []
    for _ in range(B):
        samp = []
        for _ in range(len(keys)):
            samp.extend(by_sym[keys[random.randrange(len(keys))]])
        pf = _net_pf(samp)
        if pf != float("inf"):
            pfs.append(pf)
    pfs.sort()
    if not pfs:
        return float("nan"), float("nan")
    return pfs[int(0.05 * len(pfs))], pfs[int(0.5 * len(pfs))]


def _dedup_symbol_day(rows):
    seen, out = set(), []
    for e in sorted(rows, key=lambda x: x["ts"]):
        k = (e["sym"], e["day"])
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out


def compute_status():
    now = datetime.now(timezone.utc)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT symbol, UNIX_TIMESTAMP(created_at)*1000, intrabar_pnl_pct, DATE(created_at)
                     FROM at_signal_outcomes
                    WHERE asset_class='CRYPTO' AND COALESCE(intrabar_ambiguous,0)=0
                      AND intrabar_pnl_pct IS NOT NULL AND direction='SHORT'
                      AND strategy='luxalgo_confluence'
                      AND created_at > %s AND created_at IS NOT NULL""",
                (FORWARD_START,),
            )
            raw = [dict(sym=r[0], ts=int(r[1]), pnl=float(r[2]), day=str(r[3])) for r in cur.fetchall()]
    finally:
        conn.close()

    ded = _dedup_symbol_day(raw)
    base = {
        "candidate": "luxalgo_confluence SHORT (CRYPTO)",
        "hypothesis_id": "H-20260612-luxalgo_confluence_v2_short",
        "generated_at": now.isoformat(),
        "forward_start": FORWARD_START,
        "cost_pct_rt": COST_PCT,
        "n_gate": N_GATE,
        "ci_lb_gate": CI_LB_GATE,
        "n": len(ded),
        "n_raw": len(raw),
    }
    if len(ded) < 20:
        base.update({"status": "INSUFFICIENT_N", "note": f"forward n={len(ded)} too small to score"})
        return base

    cnt = Counter(e["sym"] for e in ded)
    n = len(ded)
    hhi = sum((v / n) ** 2 for v in cnt.values())
    lb, med = _cluster_ci_lb(ded)
    rs = sorted(ded, key=lambda x: x["ts"])
    m = len(rs) // 2
    ha, hb = _net_pf(rs[:m]), _net_pf(rs[m:])
    byd = defaultdict(float)
    for e in ded:
        if e["pnl"] - COST_PCT > 0:
            byd[e["day"]] += e["pnl"] - COST_PCT
    top_day_share = (max(byd.values()) / sum(byd.values())) if byd else 1.0

    gates = {
        "n_ge_80": n >= N_GATE,
        "ci_lb_gt_1_15": (lb == lb and lb > CI_LB_GATE),  # NaN-safe
        "both_halves_gt_1": ha > 1 and hb > 1,
        "hhi_lt_0_15": hhi < 0.15,
        "top_day_lt_0_50": top_day_share < 0.50,
    }
    failing = [k for k, ok in gates.items() if not ok]
    promotable = not failing
    base.update(
        {
            "status": "PROMOTABLE_PROBATION" if promotable else "SHADOW_TRACKING",
            "n_symbols": len(cnt),
            "wr_pct": round(_wr(ded), 1),
            "net_pf": round(_net_pf(ded), 3),
            "net_pf_ci_lb": round(lb, 3) if lb == lb else None,
            "net_pf_boot_median": round(med, 3) if med == med else None,
            "half_a_pf": round(ha, 3) if ha != float("inf") else None,
            "half_b_pf": round(hb, 3) if hb != float("inf") else None,
            "symbol_hhi": round(hhi, 4),
            "top_winday_profit_share": round(top_day_share, 3),
            "top5_symbols": cnt.most_common(5),
            "gates": gates,
            "failing_gates": failing,
            "note": (
                "FORWARD-CONFIRMED — promote to real paper pilot" if promotable
                else f"forward-track: {len(failing)} gate(s) short ({', '.join(failing)}); do NOT size"
            ),
        }
    )
    return base


def main() -> int:
    ap = argparse.ArgumentParser(description="Forward-shadow gate tracker for luxalgo_confluence SHORT (CRYPTO)")
    ap.add_argument("--stdout", action="store_true", help="Print status JSON; do not write the file")
    args = ap.parse_args()
    status = compute_status()
    if args.stdout:
        print(json.dumps(status, indent=2, default=str))
        return 0
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(status, f, indent=2, default=str)
    print(f"wrote {OUT_PATH} | status={status.get('status')} n={status.get('n')} "
          f"ci_lb={status.get('net_pf_ci_lb')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
