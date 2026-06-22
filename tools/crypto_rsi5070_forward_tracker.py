#!/usr/bin/env python3
"""Forward-test tracker for the crypto_rsi5070_us entry-condition lead (READ-ONLY sidecar).

Why this exists
---------------
`crypto_rsi5070_us` (CRYPTO ∧ Wilder RSI(14,1h)∈[50,70] ∧ US session) is the project's
strongest HONEST money-ready lead (honest intrabar first-touch, not a daily-resolution
artifact — cf. reports/CRYPTO_RSI5070_US_LEAD_CANDIDATE_2026-06-13.md). It is already
counted in entry_conditions_forward.json, but only with GROSS PF. The actual promotion
gate is the cluster-bootstrap **net-of-cost PF CI-LB** (tools/pf_ci_lower.py). This sidecar
recomputes that gate-relevant number every run and writes a status JSON the /audit
dashboard reads, so the lead accrues forward n under a CONDITIONAL TRACKING EXCEPTION —
forward-shadow only, never sized, auto-eligible for probation ONLY when it clears the bar.

It is opt-in / read-only (Wire-Up Rule sidecar): it queries the DB and writes ONE data
JSON. It changes NO production pick/score behavior. It NEVER runs a dashboard generator.

Promotion gate (all required, on the FORWARD honest-intrabar cohort, net of cost):
  net PF CI-LB > 1.15  AND  n_eff >= 80  AND  n >= 150  AND  OOS-half net PF >= 1.0
  AND  top-symbol concentration < 35%.
Anything short → status SHADOW_TRACKING with the failing gates listed. Do NOT size.

Usage:
  python3 tools/crypto_rsi5070_forward_tracker.py            # write status JSON
  python3 tools/crypto_rsi5070_forward_tracker.py --stdout   # print, do not write
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import tools.stamp_entry_conditions as S  # noqa: E402  (fetch_cohort/fetch_bars/features)
from tools.pf_ci_lower import effective_n, pf_ci_lower  # noqa: E402

OUT_PATH = os.path.join(REPO, "audit_dashboard", "data", "crypto_rsi5070_us_forward_status.json")
CRYPTO_RT_BP = 16.0          # crypto round-trip cost convention (master loop §0)
N_GATE = 150                 # pre-registered honest-n gate (~2026-06-25 ETA)
CI_LB_BAR = 1.15
NEFF_BAR = 80
CONC_BAR = 0.35


def _build_conditioned_subset(limit: int = 4000):
    """Reconstruct the crypto_rsi5070_us honest-intrabar cohort via the canonical tool."""
    cohort = S.fetch_cohort(limit)
    by_table = {"crypto_ohlcv": {}, "stock_ohlcv": {}}
    for p in cohort:
        p["_cls"] = (p["asset_class"] or "UNKNOWN").upper()
        is_crypto = p["_cls"] in ("CRYPTO", "MEMECOIN")
        tbl = "crypto_ohlcv" if is_crypto else "stock_ohlcv"
        cands = [p["symbol"]]
        if is_crypto:
            alt = p["symbol"].upper().replace("-", "").replace("/", "")
            if alt.endswith("USD") and not alt.endswith("USDT"):
                alt += "T"
            if alt != p["symbol"]:
                cands.append(alt)
        p["_barsyms"] = cands
        entry_ms = int(p["opened_at"].replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
        for s in cands:
            lo, hi = by_table[tbl].get(s, (entry_ms, entry_ms))
            by_table[tbl][s] = (min(lo, entry_ms), max(hi, entry_ms))
    bars = S.fetch_bars(by_table)
    skips: dict[str, int] = {}
    sub = []
    for p in cohort:
        sym_bars = next((bars[s] for s in p["_barsyms"] if bars.get(s)), [])
        f = S.features(p, sym_bars, skips)
        if f is None:
            continue
        if p["_cls"] == "CRYPTO" and f["F3"] == "50-70" and f["F5"] == "US":
            sub.append(p)
    return sub


def _pf(pnls):
    gp = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p < 0))
    return round(gp / gl, 3) if gl > 0 else (999.0 if gp > 0 else 0.0)


def compute_status(limit: int = 4000) -> dict:
    sub = _build_conditioned_subset(limit)
    rows = [p for p in sub if p.get("intrabar_pnl_pct") is not None]
    n = len(rows)
    now = dt.datetime.now(dt.timezone.utc)
    base = {
        "condition": "crypto_rsi5070_us",
        "definition": "CRYPTO AND Wilder RSI(14,1h) in [50,70] AND US session (13:30-21:00 UTC)",
        "generated_at": now.isoformat(),
        "read_only": True,
        "source": "at_signal_outcomes intrabar first-touch (honest), via tools/stamp_entry_conditions.py",
        "cost_assumption_bp_rt": CRYPTO_RT_BP,
        "n": n,
        "n_gate": N_GATE,
        "gate_eta": "~2026-06-25",
    }
    if n < 20:
        base.update({"status": "INSUFFICIENT_N", "note": f"n={n} too small to score"})
        return base

    pnls = [float(p["intrabar_pnl_pct"]) for p in rows]
    clusters = [f'{p["symbol"]}|{p["opened_at"].date()}' for p in rows]
    net = [x - CRYPTO_RT_BP * 0.01 for x in pnls]
    gross_ci = pf_ci_lower(pnls, clusters=clusters)
    net_ci = pf_ci_lower(net, clusters=clusters)
    ne = effective_n(net, clusters)
    wr = round(100.0 * sum(1 for x in pnls if x > 0) / n, 1)
    # LAST-30D WR + n slices for the daily-snapshot /audit panel
    # (mirrors tools/stamp_entry_conditions.py:313-314 cutoff pattern).
    # Trim-only of the dedup'd cohort (no double dedup); recency drift signal.
    cutoff_30d = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(days=30)
    last30 = [r for r in rows if r["opened_at"] >= cutoff_30d]
    n_last30 = len(last30)
    wr_last30 = (round(100.0 * sum(1 for r in last30 if float(r["intrabar_pnl_pct"]) > 0) / n_last30, 1)
                 if n_last30 else None)

    rows_sorted = sorted(rows, key=lambda p: p["opened_at"])
    mid = n // 2
    is_net = [float(p["intrabar_pnl_pct"]) - CRYPTO_RT_BP * 0.01 for p in rows_sorted[:mid]]
    oos_net = [float(p["intrabar_pnl_pct"]) - CRYPTO_RT_BP * 0.01 for p in rows_sorted[mid:]]
    is_pf, oos_pf = _pf(is_net), _pf(oos_net)
    split_date = str(rows_sorted[mid]["opened_at"].date()) if mid < n else None

    # concentration (top symbol share)
    counts: dict[str, int] = {}
    for p in rows:
        counts[p["symbol"]] = counts.get(p["symbol"], 0) + 1
    top_sym, top_cnt = max(counts.items(), key=lambda kv: kv[1])
    conc = round(top_cnt / n, 3)

    net_lb = net_ci["pf_ci_lower"]
    neff = ne["n_eff"]
    gates = {
        "net_ci_lb_gt_1.15": bool(net_lb is not None and net_lb > CI_LB_BAR),
        "n_eff_ge_80": bool(neff >= NEFF_BAR),
        "n_ge_150": bool(n >= N_GATE),
        "oos_net_pf_ge_1.0": bool(oos_pf >= 1.0),
        "concentration_lt_0.35": bool(conc < CONC_BAR),
    }
    failing = [k for k, ok in gates.items() if not ok]
    promotable = not failing
    status = "PROMOTABLE_PROBATION" if promotable else "SHADOW_TRACKING"

    base.update({
        "status": status,
        "promotable": promotable,
        "wr_pct": wr,
        "wr_pct_last30d": wr_last30,
        "n_last30d": n_last30,
        "avg_pnl_pct": round(sum(pnls) / n, 4),
        "gross_pf": gross_ci["pf"],
        "gross_ci_lb": gross_ci["pf_ci_lower"],
        "net_pf": net_ci["pf"],
        "net_ci_lb": net_lb,
        "n_eff": neff,
        "is_net_pf": is_pf,
        "oos_net_pf": oos_pf,
        "is_oos_split_date": split_date,
        "top_symbol": top_sym,
        "top_symbol_pct": round(conc * 100, 1),
        "gates": gates,
        "failing_gates": failing,
        "verdict": (
            "CONDITIONAL TRACKING EXCEPTION — forward-shadow only, NEVER sized. "
            f"net PF {net_ci['pf']} (CI-LB {net_lb}) on n={n} honest intrabar trades, "
            f"IS/OOS {is_pf}/{oos_pf}, top-symbol {top_sym} {round(conc*100,1)}%. "
            + ("Clears the promotion gate." if promotable
               else "Below the promotion bar (net CI-LB>1.15 AND n_eff>=80 AND n>=150 AND OOS>=1.0 AND conc<35%); "
                    f"failing: {', '.join(failing)}. Re-run at the n>=150 gate (~2026-06-25).")
        ),
    })
    return base


def main() -> int:
    ap = argparse.ArgumentParser(description="crypto_rsi5070_us forward-test tracker (read-only sidecar)")
    ap.add_argument("--stdout", action="store_true", help="print JSON instead of writing the status file")
    ap.add_argument("--limit", type=int, default=4000, help="max cohort rows (newest first)")
    args = ap.parse_args()
    doc = compute_status(args.limit)
    payload = json.dumps(doc, indent=2, default=str)
    if args.stdout:
        print(payload)
    else:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w") as fh:
            fh.write(payload + "\n")
        print(f"wrote {OUT_PATH}: status={doc.get('status')} n={doc.get('n')} "
              f"net_ci_lb={doc.get('net_ci_lb')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
