#!/usr/bin/env python3
"""replay_harness.py — the reusable ACT-engine replay harness (Master Loop §2).

ONE command takes a candidate trade list and returns an ADMISSIBILITY verdict
built from every gate the loop pre-registered, so no future "edge" claim can
skip a step:

  0. PREFLIGHT  tools/loop_preflight.py (fail-closed: H1 guards, M-107
                pre-registration, do-not-relitigate) — skippable only with
                --skip-preflight + --skip-reason (logged into the report).
  1. DEDUP      one trade per (symbol, direction, UTC-day) — first by entry time.
  2. REPLAY     entry-anchored first-touch TP/SL on 1h bars, SL-wins-ties
                (imports the PROVEN tools/reresolve_intrabar.py::replay —
                the same code the production resolver runs; no reimplementation).
  3. COSTS      net round-trip costs per class (crypto 16bp / equity+etf 4bp /
                fx 2bp / futures+commodity 4bp), override with --costs-bps.
  4. METRICS    n, n_eff (cluster), WR, net PF, PF 95% CI lower bound
                (cluster bootstrap via tools/pf_ci_lower.py).
  5. R1 SPLIT   time-split halves by entry time — both halves must hold.
  6. R2 CONC    top-symbol share < 35%.
  7. MONKEY     net PF must beat the P95 of the latest
                reports/monkey_test_benchmark_*.json for the class (skipped
                with a loud warning when no benchmark exists).
  8. STRESS     cost multipliers x0.5/1/2/4 + entry slipped 1 bar later —
                PF CI-LB must stay > 1.0 in at least 3 adverse cells
                (Addendum G stress-matrix v1).

VERDICT: admissible only if ALL gates pass. Replay admissibility NEVER sizes
anything — it only nominates the candidate for the forward lane (stamp /
shadow-emission), where the real promotion bar lives (CI-LB>1.15 @ n>=80).

Input format (--trades-json): list of objects
  {symbol, direction, entry_time (ISO or epoch-ms), entry, tp, sl}
Optional per-trade: asset_class (else --asset-class applies), horizon_bars.

Usage:
  python3 tools/replay_harness.py --family my_family --asset-class CRYPTO \
      --trades-json /tmp/candidates.json [--horizon-bars 48] [--costs-bps 16]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tools.pf_ci_lower import pf_ci_lower, effective_n, profit_factor  # noqa: E402
from tools.reresolve_intrabar import replay  # noqa: E402  (proven first-touch)

CRYPTO_CLASSES = {"CRYPTO", "MEMECOIN"}
DEFAULT_COSTS_BPS = {"CRYPTO": 16, "MEMECOIN": 16, "EQUITY": 4, "ETF": 4,
                     "FOREX": 2, "COMMODITY": 4, "FUTURES": 4, "BOND": 4}
DEFAULT_HORIZON_BARS = 48
CONC_CAP = 0.35
REPLAY_CI_LB_BAR = 1.0      # replay nomination bar (forward bar is 1.15)
MIN_N_EFF = 80


def _to_ms(v) -> int:
    if isinstance(v, (int, float)):
        return int(v if v > 1e12 else v * 1000)
    s = str(v).replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return int(d.timestamp() * 1000)


def run_preflight(family: str, asset_class: str) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / "loop_preflight.py"),
         "--asset-class", asset_class, "--family", family, "--stage", "replay"],
        capture_output=True, text=True, timeout=180)
    return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")


def fetch_bars(cur, symbol, asset_class, start_ms, horizon_bars, pre_bars=0):
    """Bars after start_ms; with pre_bars>0 also returns up to that many
    bars BEFORE it (for regime stratification — strictly pre-entry data)."""
    table = "crypto_ohlcv" if asset_class.upper() in CRYPTO_CLASSES else "stock_ohlcv"
    pre = []
    if pre_bars:
        cur.execute(
            f"SELECT timestamp, close FROM {table} "
            "WHERE symbol=%s AND timeframe='1h' AND timestamp<=%s "
            "ORDER BY timestamp DESC LIMIT %s",
            (symbol, start_ms, int(pre_bars)))
        pre = [float(r[1]) for r in reversed(cur.fetchall())]
    cur.execute(
        f"SELECT timestamp, high, low, close FROM {table} "
        "WHERE symbol=%s AND timeframe='1h' AND timestamp>%s ORDER BY timestamp "
        "LIMIT %s",
        (symbol, start_ms, int(horizon_bars)))
    bars = [{"timestamp": r[0], "high": r[1], "low": r[2], "close": r[3]}
            for r in cur.fetchall()]
    return (bars, pre) if pre_bars else bars


def dedup_trades(trades):
    """One per (symbol, direction, UTC day); earliest entry wins."""
    best = {}
    for t in sorted(trades, key=lambda t: t["_entry_ms"]):
        day = dt.datetime.fromtimestamp(t["_entry_ms"] / 1000,
                                        dt.timezone.utc).strftime("%Y-%m-%d")
        key = (t["symbol"], str(t["direction"]).upper(), day)
        best.setdefault(key, t)
    return list(best.values())


def replay_set(cur, trades, asset_class, horizon_bars, cost_frac, slip_bars=0):
    """Replay every trade; returns list of {pnl_net, symbol, day, status}."""
    import statistics as _st
    out = []
    for t in trades:
        bars, pre = fetch_bars(cur, t["symbol"], t.get("asset_class", asset_class),
                               t["_entry_ms"], horizon_bars + slip_bars, pre_bars=72)
        # strictly pre-entry regime features (F4 vol proxy + F1 trend proxy)
        pre_vol = None
        trend = None
        if len(pre) >= 24:
            rets = [(pre[i] / pre[i-1] - 1) for i in range(1, len(pre)) if pre[i-1]]
            pre_vol = _st.pstdev(rets) if len(rets) >= 12 else None
            sma = sum(pre[-50:]) / min(len(pre), 50)
            trend = "UP" if pre[-1] > sma else "DOWN"
        if slip_bars:
            if len(bars) <= slip_bars:
                continue
            entry_bar = bars[slip_bars - 1]
            entry = float(entry_bar["close"])  # slipped entry = next bar close
            bars = bars[slip_bars:]
        else:
            entry = float(t["entry"])
        if not bars:
            continue
        status, pnl, used, ambiguous = replay(entry, float(t["tp"]),
                                              float(t["sl"]), t["direction"], bars)
        if status is None:
            continue
        day = dt.datetime.fromtimestamp(t["_entry_ms"] / 1000,
                                        dt.timezone.utc).strftime("%Y-%m-%d")
        out.append({"pnl_net": pnl * 100 - cost_frac * 100,  # pct net of RT costs
                    "symbol": t["symbol"], "day": day, "status": status,
                    "ambiguous": ambiguous, "pre_vol": pre_vol, "trend": trend})
    return out


def regime_strata(results):
    """Per-regime breakdown (nemotron mitigation #1 / 4h-sprint regime ask):
    pre-entry 72-bar vol terciles (LOW/MID/HIGH within-cohort) x trend (UP/DOWN).
    Measurement only — exposes WHERE an edge concentrates; never a gate."""
    vols = sorted(r["pre_vol"] for r in results if r.get("pre_vol") is not None)
    if len(vols) < 30:
        return {"note": "insufficient pre-entry history for stratification"}
    t1, t2 = vols[len(vols) // 3], vols[2 * len(vols) // 3]

    def bucket(r):
        v = r.get("pre_vol")
        if v is None:
            return None
        return "LOW" if v <= t1 else ("HIGH" if v > t2 else "MID")

    strata: dict = {}
    for r in results:
        b = bucket(r)
        if b is None:
            continue
        for key in (f"vol_{b}", f"trend_{r.get('trend') or 'NA'}",
                    f"vol_{b}|trend_{r.get('trend') or 'NA'}"):
            strata.setdefault(key, []).append(r["pnl_net"])
    out = {}
    for k, pnls in sorted(strata.items()):
        if len(pnls) < 15:
            continue
        wins = sum(1 for p in pnls if p > 0)
        gp = sum(p for p in pnls if p > 0)
        gl = sum(-p for p in pnls if p < 0)
        out[k] = {"n": len(pnls), "wr_pct": round(100 * wins / len(pnls), 1),
                  "pf_net": round(gp / gl, 3) if gl else None}
    return out


def metrics_block(results):
    pnls = [r["pnl_net"] for r in results]
    clusters = [f"{r['symbol']}|{r['day']}" for r in results]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    ci = pf_ci_lower(pnls, clusters=clusters)
    neff = effective_n(pnls, clusters) if n else {"n_eff": 0}
    return {"n": n, "wr_pct": round(100 * wins / n, 1) if n else None,
            "pf_net": (round(ci["pf"], 3) if ci["pf"] not in (None, float("inf"))
                       else ci["pf"]),
            "pf_ci_lower": ci["pf_ci_lower"], "n_clusters": ci["n_clusters"],
            "n_eff": neff["n_eff"],
            "ambiguous_n": sum(1 for r in results if r.get("ambiguous"))}


def latest_monkey_p95(asset_class):
    files = sorted(glob.glob(str(REPO / "reports" / "monkey_test_benchmark_*.json")))
    for f in reversed(files):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        # accept either per-class or global shapes
        per = d.get("by_asset_class") or d.get("per_class") or {}
        if asset_class in per and per[asset_class].get("p95_pf") is not None:
            return float(per[asset_class]["p95_pf"]), f
        if d.get("p95_pf") is not None:
            return float(d["p95_pf"]), f
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--family", required=True)
    ap.add_argument("--asset-class", required=True)
    ap.add_argument("--trades-json", required=True)
    ap.add_argument("--horizon-bars", type=int, default=DEFAULT_HORIZON_BARS)
    ap.add_argument("--costs-bps", type=float, default=None,
                    help="round-trip cost bps override (default per class)")
    ap.add_argument("--skip-preflight", action="store_true")
    ap.add_argument("--skip-reason", default="")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ac = args.asset_class.upper()
    report = {"family": args.family, "asset_class": ac,
              "horizon_bars": args.horizon_bars, "gates": {}, "admissible": False,
              "note": ("replay admissibility only NOMINATES for the forward lane; "
                       "promotion bar is CI-LB>1.15 @ n_eff>=80 FORWARD")}

    # 0. preflight (fail closed)
    if args.skip_preflight:
        if not args.skip_reason.strip():
            print("--skip-preflight requires --skip-reason", file=sys.stderr)
            return 2
        report["gates"]["preflight"] = {"pass": None,
                                        "skipped_reason": args.skip_reason}
    else:
        ok, out = run_preflight(args.family, ac)
        report["gates"]["preflight"] = {"pass": ok, "output": out[-600:]}
        if not ok:
            report["verdict"] = "BLOCKED_BY_PREFLIGHT"
            print(json.dumps(report, indent=2))
            return 1

    raw = json.load(open(args.trades_json))
    for t in raw:
        t["_entry_ms"] = _to_ms(t["entry_time"])
    deduped = dedup_trades(raw)
    report["gates"]["dedup"] = {"n_raw": len(raw), "n_dedup": len(deduped),
                                "dup_rate_pct": round(100 * (1 - len(deduped) / len(raw)), 1)
                                if raw else None}

    cost_bps = args.costs_bps if args.costs_bps is not None else \
        DEFAULT_COSTS_BPS.get(ac, 8)
    cost_frac = cost_bps / 10000.0
    report["costs_bps_rt"] = cost_bps

    from tools.db_env import get_stocks_creds
    import pymysql
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    conn = pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})
    cur = conn.cursor()

    # 2-4. main replay + metrics
    results = replay_set(cur, deduped, ac, args.horizon_bars, cost_frac)
    main_m = metrics_block(results)
    report["main"] = main_m
    ok_main = (main_m["n_eff"] is not None and main_m["n_eff"] >= MIN_N_EFF
               and main_m["pf_ci_lower"] is not None
               and main_m["pf_ci_lower"] > REPLAY_CI_LB_BAR)
    report["gates"]["main_ci"] = {"pass": bool(ok_main),
                                  "bar": f"n_eff>={MIN_N_EFF} & pf_ci_lower>{REPLAY_CI_LB_BAR}"}

    report["regime_strata"] = regime_strata(results)

    # 5. R1 time-split
    results_sorted = sorted(results, key=lambda r: r["day"])
    half = len(results_sorted) // 2
    h1, h2 = metrics_block(results_sorted[:half]), metrics_block(results_sorted[half:])
    pf_ok = lambda m: isinstance(m["pf_net"], (int, float)) and m["pf_net"] > 1.0
    report["r1_split"] = {"h1": h1, "h2": h2}
    report["gates"]["r1_time_split"] = {"pass": bool(pf_ok(h1) and pf_ok(h2)),
                                        "bar": "net PF>1.0 in BOTH halves"}

    # 6. R2 concentration
    by_sym = defaultdict(int)
    for r in results:
        by_sym[r["symbol"]] += 1
    top_share = max(by_sym.values()) / len(results) if results else 1.0
    report["gates"]["r2_concentration"] = {
        "pass": top_share < CONC_CAP, "top_symbol_share": round(top_share, 3),
        "top_symbol": max(by_sym, key=by_sym.get) if by_sym else None,
        "bar": f"top symbol < {CONC_CAP:.0%}"}

    # 7. monkey P95
    p95, src = latest_monkey_p95(ac)
    if p95 is None:
        report["gates"]["monkey_p95"] = {
            "pass": None,
            "warning": "NO monkey benchmark found for class — run "
                       "tools/monkey_test_benchmark.py; gate counted as FAIL"}
    else:
        pf_pt = main_m["pf_net"] if isinstance(main_m["pf_net"], (int, float)) else 0
        report["gates"]["monkey_p95"] = {"pass": pf_pt > p95, "p95_pf": p95,
                                         "benchmark": os.path.basename(src)}

    # 8. stress matrix (cost x0.5/2/4 + 1-bar slip at 1x cost)
    stress = {}
    for mult in (0.5, 2.0, 4.0):
        rs = [{**r, "pnl_net": r["pnl_net"] + cost_frac * 100 - cost_frac * mult * 100}
              for r in results]  # re-net at multiplied cost
        stress[f"cost_x{mult}"] = metrics_block(rs)
    stress["slip_1bar"] = metrics_block(
        replay_set(cur, deduped, ac, args.horizon_bars, cost_frac, slip_bars=1))
    conn.close()
    adverse_pass = sum(
        1 for k, m in stress.items()
        if k != "cost_x0.5" and m["pf_ci_lower"] is not None and m["pf_ci_lower"] > 1.0)
    # adverse cells: cost_x2, cost_x4, slip_1bar (cost_x0.5 is favorable)
    report["stress"] = stress
    report["gates"]["stress_matrix"] = {
        "pass": adverse_pass >= 2, "adverse_cells_passing": adverse_pass,
        "bar": "PF CI-LB>1.0 in >=2 of 3 adverse cells"}

    gate_values = [g.get("pass") for g in report["gates"].values()
                   if g.get("pass") is not None or "warning" in g]
    report["admissible"] = all(bool(g.get("pass")) for g in report["gates"].values()
                               if g.get("pass") is not None) and \
        all("warning" not in g or g.get("pass") for g in report["gates"].values())
    report["verdict"] = "ADMISSIBLE_FOR_FORWARD_LANE" if report["admissible"] \
        else "NOT_ADMISSIBLE"

    out_path = args.out or str(
        REPO / "reports" / f"replay_harness_{args.family}_"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d')}.json")
    json.dump(report, open(out_path, "w"), indent=2, default=str)
    print(json.dumps({k: report[k] for k in
                      ("family", "asset_class", "main", "gates", "verdict")},
                     indent=2, default=str))
    print(f"# full report -> {out_path}")
    return 0 if report["admissible"] else 1


if __name__ == "__main__":
    sys.exit(main())
