#!/usr/bin/env python3
"""Systematic honest sub-condition edge-miner (READ-ONLY, EXPLORATORY).

Why
---
crypto_rsi5070_us (net PF ~1.34) is a winning *sub-condition* inside a *losing* class
(CRYPTO overall intrabar PF ~0.79). That pattern — a profitable pocket hidden in a
class baseline — is exactly what we want to find more of. Instead of hand-guessing one
predicate at a time (variant-fishing), enumerate ALL cells at once and FDR-correct.

Pre-registration (M-107)
------------------------
Family = every (class x RSI-band x session x direction) cell over the honest intrabar
cohort with n >= MIN_N, plus the coarser (class x dir x RSI) and (class x dir x session)
roll-ups. Ranked by net_PF. Benjamini-Hochberg FDR at q=0.10 on the per-cell two-sided
binomial p (realized WR vs 0.5). Hypothesis: at least one cell beyond crypto_rsi5070_us
shows a real net edge worth FORWARD pre-registration.

Discipline
----------
- Output is EXPLORATORY: candidates for forward pre-registration, NEVER for sizing.
- Cells at different granularities OVERLAP (same picks counted in roll-ups) -> FDR here is
  a screening heuristic, not a clean independent test. A surfaced cell must still pass a
  fresh single-hypothesis forward gate (n>=80 fwd, net-PF CI-LB>1.15, time-split, conc<35%).
- Reuses fetch_cohort/fetch_bars/features/stats from stamp_entry_conditions.py verbatim
  (the validated honest-intrabar code) — no re-implementation of resolution or features.
"""
from __future__ import annotations
import sys, os, json, math, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.stamp_entry_conditions import fetch_cohort, fetch_bars, features, stats  # noqa: E402

MIN_N = 30
Q = 0.10


def _norm_dir(p: dict) -> str:
    return "LONG" if str(p.get("direction", "")).upper() in ("LONG", "BUY") else "SHORT"


def build_stamped(limit: int = 4000):
    cohort = fetch_cohort(limit)
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
    bars = fetch_bars(by_table)
    skips: dict[str, int] = {}
    stamped = []
    for p in cohort:
        sym_bars = next((bars[s] for s in p["_barsyms"] if bars.get(s)), [])
        f = features(p, sym_bars, skips)
        if f is not None:
            stamped.append((p, f))
    return cohort, stamped, skips


def binom_p_two_sided(wins: int, n: int, p0: float = 0.5) -> float:
    if n == 0:
        return 1.0
    mu = p0 * n
    sd = math.sqrt(n * p0 * (1 - p0))
    if sd == 0:
        return 1.0
    z = abs(wins - mu) / sd
    return max(0.0, min(1.0, 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))))


def _netpnl(rows) -> float:
    return sum(float(p.get("intrabar_pnl_pct") or 0) for p in rows)


def _ex_topk_netpf(rows, k: int = 3):
    """net_PF after removing the k symbols with the largest net P&L (fat-tail robustness)."""
    from collections import defaultdict
    bysym = defaultdict(list)
    for p in rows:
        bysym[p["symbol"]].append(p)
    top = set(sorted(bysym, key=lambda s: -_netpnl(bysym[s]))[:k])
    rest = [p for p in rows if p["symbol"] not in top]
    if len(rest) < 10:
        return None, len(bysym)
    return stats(rest).get("net_pf"), len(bysym)


def btc_monthly_direction() -> dict:
    """{YYYY-MM: 'UP'|'DOWN'} from BTCUSDT monthly return (regime labels)."""
    try:
        from tools.db_env import get_stocks_creds
        import pymysql
        keep = ("host", "user", "password", "database", "port", "connect_timeout")
        c = pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})
        cur = c.cursor()
        cur.execute("""SELECT DATE_FORMAT(FROM_UNIXTIME(timestamp/1000),'%Y-%m') mo,
            (SUBSTRING_INDEX(GROUP_CONCAT(close ORDER BY timestamp DESC),',',1)/
             SUBSTRING_INDEX(GROUP_CONCAT(close ORDER BY timestamp ASC),',',1)-1) ret
            FROM crypto_ohlcv WHERE symbol='BTCUSDT' GROUP BY mo""")
        out = {mo: ("UP" if (r or 0) > 0 else "DOWN") for mo, r in cur.fetchall()}
        c.close()
        return out
    except Exception:
        return {}


def _regime_both(rows, btcdir: dict) -> bool:
    """True if the cell is net-positive in BOTH a BTC-up and a BTC-down month-bucket."""
    up = [p for p in rows if btcdir.get(str(p["opened_at"])[:7]) == "UP"]
    dn = [p for p in rows if btcdir.get(str(p["opened_at"])[:7]) == "DOWN"]
    return len(up) >= 5 and len(dn) >= 5 and _netpnl(up) > 0 and _netpnl(dn) > 0


def main() -> int:
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 4000
    cohort, stamped, skips = build_stamped(limit)
    btcdir = btc_monthly_direction()

    cells: dict[str, list] = {}
    for p, f in stamped:
        cls, F3, F5, d = p["_cls"], f["F3"], f["F5"], _norm_dir(p)
        for k in (f"{cls}|{d}|RSI{F3}|{F5}", f"{cls}|{d}|RSI{F3}", f"{cls}|{d}|{F5}"):
            cells.setdefault(k, []).append(p)

    results = []
    for k, rows in cells.items():
        if len(rows) < MIN_N:
            continue
        s = stats(rows)
        n = s["n"]
        wr = s["wr"] or 0.0
        wins = int(round(wr / 100.0 * n))
        net_pf = s.get("net_pf")
        ex3_netpf, n_syms = _ex_topk_netpf(rows, 3)
        regime_both = _regime_both(rows, btcdir) if btcdir else None
        # ROBUST = real net edge that survives removing its 3 biggest-P&L symbols AND wins in
        # both BTC regimes (the two failure modes that killed crypto_short_rsi5070 + rsi5070-LONG).
        robust = bool(
            (net_pf or 0) >= 1.3 and n >= 40 and (ex3_netpf or 0) >= 1.0
            and (regime_both is True)
        )
        results.append({
            "cell": k, "n": n, "wr": wr, "pf": s["pf"], "net_pf": net_pf,
            "avg_pnl": s.get("avg_pnl"), "p": binom_p_two_sided(wins, n),
            "ex_top3_netpf": ex3_netpf, "n_symbols": n_syms,
            "regime_both": regime_both, "robust": robust,
        })

    # Benjamini-Hochberg
    results.sort(key=lambda r: r["p"])
    m = len(results)
    max_k = 0
    for i, r in enumerate(results, 1):
        r["bh_thresh"] = round(i / m * Q, 5) if m else 1.0
        if r["p"] <= r["bh_thresh"]:
            max_k = i
    for i, r in enumerate(results, 1):
        r["fdr_pass"] = i <= max_k

    robust = [r for r in results if r["robust"]]
    robust.sort(key=lambda r: (-(r["net_pf"] or 0), -r["n"]))

    print(f"cohort={len(cohort)} stamped={len(stamped)} cells_tested={m} bh_rejected={max_k} "
          f"ROBUST={len(robust)} btc_months={len(btcdir)} skips={skips}", file=sys.stderr)
    print(f"\n=== TOP CELLS by net_PF (n>={MIN_N}) — robust gate: netPF>=1.3 & ex-top3>=1.0 & n>=40 & wins both regimes ===", file=sys.stderr)
    hdr = f"{'cell':<28}{'n':>4}{'WR%':>6}{'netPF':>7}{'exTop3':>7}{'nSym':>5}{'reg2':>5}{'ROBUST':>7}"
    print(hdr, file=sys.stderr)
    print("-" * len(hdr), file=sys.stderr)
    for r in sorted(results, key=lambda x: -(x["net_pf"] or 0))[:25]:
        print(f"{r['cell']:<28}{r['n']:>4}{r['wr']:>6}{str(r['net_pf']):>7}"
              f"{str(r['ex_top3_netpf']):>7}{str(r['n_symbols']):>5}"
              f"{('Y' if r['regime_both'] else 'n'):>5}{('ROBUST' if r['robust'] else '·'):>7}", file=sys.stderr)
    if robust:
        print(f"\n*** {len(robust)} ROBUST CANDIDATE(S) — survive ex-top3 + both regimes ***", file=sys.stderr)
        for r in robust:
            print(f"    {r['cell']}  n={r['n']} netPF={r['net_pf']} exTop3={r['ex_top3_netpf']} WR={r['wr']}", file=sys.stderr)
    else:
        print("\n*** 0 ROBUST CANDIDATES — every cell fails ex-top3 and/or regime (consistent with 0/9 T2) ***", file=sys.stderr)

    doc = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "read_only": True, "exploratory": True, "min_n": MIN_N, "fdr_q": Q,
        "preregistration": "all (class x dir x RSI-band x session) cells + roll-ups; BH-FDR; "
                           "hypothesis: a cell beyond crypto_rsi5070_us has a real net edge",
        "caveat": "overlapping cells -> FDR is a screen; survivors need a fresh forward gate "
                  "(n>=80 fwd, net-PF CI-LB>1.15, time-split, concentration<35%)",
        "robust_gate": "netPF>=1.3 AND ex_top3_netpf>=1.0 AND n>=40 AND wins in both BTC regimes",
        "cohort_n": len(cohort), "stamped_n": len(stamped),
        "cells_tested": m, "bh_rejected": max_k, "btc_months": len(btcdir),
        "robust_candidates": robust,
        "all_cells_ranked": sorted(results, key=lambda x: -(x["net_pf"] or 0)),
    }
    print(json.dumps(doc, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
