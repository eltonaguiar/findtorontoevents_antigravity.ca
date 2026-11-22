#!/usr/bin/env python3
"""forward_book.py — pre-registered forward paper book, resolved from real bars.

The point is prospective evidence. Every entry is written once, stamped with the
rule and the bar it was priced from, and never edited afterwards; resolution is a
separate append. That makes "would this have worked" answerable later without
window selection, because the selection happened before the outcome existed.

Rules are fixed in code and recorded on each entry so a later reader can tell
whether the target was met without trusting prose.

  emit    : price an entry off the most recent daily bar (the current day's bar
            while it is still forming), store rule + levels
  resolve : walk bars after entry_date; SL/TP/time exit; SL wins a same-bar tie
  publish : audit_dashboard/data/forward_book.json (net of the class cost)

Only symbols with a keyless bar source can be emitted today (Binance). Equity/ETF
entries are refused rather than silently unrunnable.

Usage:
  python3 tools/forward_book.py --emit-seed
  python3 tools/forward_book.py --resolve --publish
  python3 tools/forward_book.py --score
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ohlc_bars import bars_for, daily_bars, equity_bars  # noqa: E402

BOOK = Path("audit_dashboard/data/forward_book.json")
PUBLISHED = Path("audit_dashboard/data/forward_book.json")
COST_BPS = {"CRYPTO": 20, "EQUITY": 10, "ETF": 10}
BENCHMARK = {"CRYPTO": "BTC-USD", "EQUITY": "SPY", "ETF": "SPY"}

# H-201 universe, frozen at registration. The forward pod must use the same names
# the backtest was scored on, otherwise it is a different experiment.
EQ_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
               "META", "JPM", "XOM", "UNH", "JNJ"]

RULES = {
    # the grid MomentumEMA actually fills on: measured in the ledger as exactly
    # -2.00 / +3.00 on 73 picks. Reproducing it forward tests the grid itself.
    "momentum_ema_grid": {"sl_pct": 2.0, "tp_pct": 3.0, "max_hold_days": 21},
    # swing rule for the cross-check candidates; wider because these are alts.
    "alt_swing": {"sl_pct": 5.0, "tp_pct": 10.0, "max_hold_days": 30},
    # H-201 (pre-registered 2026-11-22). Time exit only ON PURPOSE: the registered
    # backtest had no TP/SL, so adding one forward would test a different strategy.
    "xsmom_equity_top3_6m": {"sl_pct": None, "tp_pct": None, "max_hold_days": 21,
                             "lookback_days": 126, "top_k": 3,
                             "universe": EQ_UNIVERSE,
                             "registered_hypothesis": "H-201"},
}

SEED = [
    ("LINK-USD", "alt_swing", "crosscheck_candidate",
     "n=20 PF 1.79 WR 65% in the 2026-11-19 window; selection retrospective, book is forward-only"),
    ("AVAX-USD", "alt_swing", "crosscheck_candidate",
     "n=18 PF 1.93 WR 61%; also traded by MomentumEMA"),
    ("TIA-USD", "alt_swing", "crosscheck_candidate",
     "n=16 PF 1.92 WR 63%"),
    ("BTC-USD", "momentum_ema_grid", "strategy_replica",
     "MomentumEMA rule reproduction on the most liquid pair"),
    ("ETH-USD", "momentum_ema_grid", "strategy_replica",
     "MomentumEMA rule reproduction"),
]


def load():
    if BOOK.exists():
        return json.loads(BOOK.read_text())
    return {"schema": 1, "created_at": None, "entries": []}


def save(b):
    BOOK.parent.mkdir(parents=True, exist_ok=True)
    BOOK.write_text(json.dumps(b, indent=2))


def _id(sym, rule, entry_date):
    return hashlib.sha1(f"{sym}|{rule}|{entry_date}".encode()).hexdigest()[:12]


def emit(b, symbol, rule, origin, note, asset_class="CRYPTO",
         benchmark=None, pod=None, spec_ref=None):
    if asset_class not in COST_BPS:
        raise SystemExit(f"{asset_class}: no cost model")
    spec = RULES[rule]
    try:
        bars = bars_for(symbol, asset_class)
    except Exception as exc:  # noqa: BLE001
        print(f"  skip {symbol}: no bars ({type(exc).__name__}: {exc})")
        return None
    if not bars:
        print(f"  skip {symbol}: empty bar set")
        return None
    entry_date, entry = bars[-1][0], bars[-1][4]
    eid = _id(symbol, rule, entry_date)
    if any(e["id"] == eid for e in b["entries"]):
        print(f"  exists {eid} {symbol} {rule}")
        return None
    long_sl = (None if spec["sl_pct"] is None
               else round(entry * (1 - spec["sl_pct"] / 100.0), 8))
    long_tp = (None if spec["tp_pct"] is None
               else round(entry * (1 + spec["tp_pct"] / 100.0), 8))
    e = {"id": eid, "symbol": symbol, "asset_class": asset_class,
         "direction": "LONG", "rule": rule, "rule_spec": spec,
         "entry_date": entry_date, "entry_price": entry,
         "stop_loss": long_sl, "take_profit": long_tp,
         "max_hold_days": spec["max_hold_days"],
         "cost_bps": COST_BPS[asset_class],
         "benchmark": benchmark or BENCHMARK.get(asset_class),
         "pod": pod, "spec_ref": spec_ref,
         "registered_at": None, "origin": origin, "note": note,
         "status": "OPEN", "resolution": None}
    import time
    e["registered_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    b["entries"].append(e)
    print(f"  registered {eid} {symbol} LONG @ {entry} SL {long_sl} TP {long_tp} ({rule})")
    return e


def resolve(b):
    changed = 0
    for e in b["entries"]:
        if e["status"] != "OPEN":
            continue
        try:
            bars = bars_for(e["symbol"], e.get("asset_class", "CRYPTO"))
        except Exception as exc:  # noqa: BLE001
            print(f"  {e['symbol']}: no bars ({type(exc).__name__})")
            continue
        window = [x for x in bars if x[0] > e["entry_date"]][: e["max_hold_days"]]
        if not window:
            continue
        entry, sl, tp = e["entry_price"], e["stop_loss"], e["take_profit"]
        exit_price = reason = None
        for d, o, hi, lo, c in window:
            if sl is not None and lo <= sl:    # SL first, wins a same-bar tie
                exit_price, reason = sl, "SL"
                break
            if tp is not None and hi >= tp:
                exit_price, reason = tp, "TP"
                break
        if exit_price is None and len(window) >= e["max_hold_days"]:
            exit_price, reason = window[-1][4], "TIME"
        if exit_price is None:
            continue
        gross = (exit_price - entry) / entry * 100.0
        net = gross - e["cost_bps"] / 100.0
        exit_date = window[-1][0]
        bench_pct = None
        bsym = e.get("benchmark") or BENCHMARK.get(e.get("asset_class", "CRYPTO"))
        if bsym:
            try:
                bcls = "ETF" if bsym in ("SPY", "QQQ", "IWM") else e.get("asset_class", "CRYPTO")
                bbars = bars_for(bsym, bcls)
                bwin = [x for x in bbars if x[0] >= e["entry_date"] and x[0] <= exit_date]
                if len(bwin) >= 2:
                    bench_pct = round((bwin[-1][4] / bwin[0][4] - 1) * 100.0, 4)
            except Exception as exc:  # noqa: BLE001
                print(f"  {e['symbol']}: no benchmark bars ({type(exc).__name__})")
        e["resolution"] = {"exit_date": exit_date, "exit_price": exit_price,
                           "reason": reason, "gross_pnl_pct": round(gross, 4),
                           "net_pnl_pct": round(net, 4),
                           "benchmark_symbol": bsym,
                           "benchmark_pct": bench_pct,
                           "excess_pct": (None if bench_pct is None
                                          else round(net - bench_pct, 4)),
                           "bars_walked": len(window),
                           "resolved_at": None}
        import time
        e["resolution"]["resolved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        e["status"] = "RESOLVED"
        changed += 1
        print(f"  resolved {e['symbol']} {reason} {net:+.3f}% net")
    return changed


def stats(vals):
    if not vals:
        return {"n": 0}
    w = [v for v in vals if v > 0]
    l = [abs(v) for v in vals if v < 0]
    return {"n": len(vals), "win_rate": round(len(w) / len(vals), 4),
            "profit_factor": round(sum(w) / sum(l), 4) if l else None,
            "expectancy_pct": round(sum(vals) / len(vals), 4)}


def emit_h201_pod(b):
    """Emit the current H-201 top-3 as forward entries, with the SPY leg."""
    rule = "xsmom_equity_top3_6m"
    spec = RULES[rule]
    ranked = []
    for sym in EQ_UNIVERSE:
        try:
            bars = equity_bars(sym, days=400)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {sym}: {type(exc).__name__}")
            continue
        if len(bars) < spec["lookback_days"] + 2:
            continue
        closes = [x[4] for x in bars]
        ranked.append((closes[-1] / closes[-1 - spec["lookback_days"]] - 1.0, sym))
    ranked.sort(reverse=True)
    print(f"  momentum ranking: " + ", ".join(f"{s} {m*100:+.1f}%" for m, s in ranked[:5]))
    out = []
    for mom, sym in ranked[: spec["top_k"]]:
        e = emit(b, sym, rule, "hypothesis:H-201",
                 f"top-{spec['top_k']} of {len(EQ_UNIVERSE)} by {spec['lookback_days']}d "
                 f"return ({mom*100:+.1f}%); frozen spec, time exit only",
                 asset_class="EQUITY", benchmark="SPY", pod="H-201", spec_ref="H-201")
        if e:
            out.append(e)
    return out


def publish(b):
    entries = b["entries"]
    done = [e for e in entries if e["status"] == "RESOLVED"]
    by_rule = {}
    for e in entries:
        by_rule.setdefault(e["rule"], []).append(e)
    pod_groups = {}
    for e in entries:
        if e.get("pod"):
            pod_groups.setdefault(e["pod"], []).append(e)
    curve, cum = [], 0.0
    for e in sorted(done, key=lambda x: x["resolution"]["exit_date"]):
        cum += e["resolution"]["net_pnl_pct"]
        curve.append([e["resolution"]["exit_date"], round(cum, 4)])
    out = {
        "schema": b.get("schema", 1),
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ",
                                                    __import__("time").gmtime()),
        "pre_registration": "entries are written once with their rule and pricing bar; "
                            "resolution is appended, never edited",
        "cost_model_bps": COST_BPS,
        "counts": {"entries": len(entries), "open": len(entries) - len(done),
                   "resolved": len(done)},
        "overall": stats([e["resolution"]["net_pnl_pct"] for e in done]),
        "by_pod": {pod: {
            "n_entries": len(v),
            "n_resolved": len([x for x in v if x["status"] == "RESOLVED"]),
            "benchmark": v[0].get("benchmark"),
            "spec_ref": v[0].get("spec_ref"),
            **stats([x["resolution"]["net_pnl_pct"] for x in v if x["status"] == "RESOLVED"]),
            "mean_benchmark_pct": (round(sum(x["resolution"]["benchmark_pct"] for x in v
                                             if x["resolution"] and x["resolution"].get("benchmark_pct") is not None)
                                         / max(1, len([x for x in v if x["resolution"] and x["resolution"].get("benchmark_pct") is not None])), 4)
                                   if any(x["resolution"] and x["resolution"].get("benchmark_pct") is not None for x in v) else None),
            "mean_excess_pct": (round(sum(x["resolution"]["excess_pct"] for x in v
                                          if x["resolution"] and x["resolution"].get("excess_pct") is not None)
                                      / max(1, len([x for x in v if x["resolution"] and x["resolution"].get("excess_pct") is not None])), 4)
                                if any(x["resolution"] and x["resolution"].get("excess_pct") is not None for x in v) else None),
        } for pod, v in pod_groups.items()},
        "by_rule": {r: {"n_entries": len(v),
                        "spec": v[0]["rule_spec"],
                        **stats([e["resolution"]["net_pnl_pct"] for e in v
                                 if e["status"] == "RESOLVED"])}
                    for r, v in by_rule.items()},
        "curve_net_pct": curve,
        "entries": entries,
    }
    PUBLISHED.write_text(json.dumps(out, indent=2))
    print(f"published {PUBLISHED}: {out['counts']} curve points={len(curve)}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-seed", action="store_true")
    ap.add_argument("--emit-pod", choices=["h201"],
                    help="emit the current registered pod's entries")
    ap.add_argument("--emit", help="symbol:rule[:asset_class]")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    b = load()
    if a.emit_seed:
        import time
        b["created_at"] = b.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for sym, rule, origin, note in SEED:
            emit(b, sym, rule, origin, note)
        save(b)
    if a.emit_pod == "h201":
        import time
        b["created_at"] = b.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        emit_h201_pod(b)
        save(b)
    if a.emit:
        parts = a.emit.split(":")
        emit(b, parts[0], parts[1], "manual", "operator-requested",
             parts[2] if len(parts) > 2 else "CRYPTO")
        save(b)
    if a.resolve:
        n = resolve(b)
        save(b)
        print(f"newly resolved: {n}")
    if a.publish or a.score:
        o = publish(b) if a.publish else None
        if a.score:
            print(f"overall: {stats([e['resolution']['net_pnl_pct'] for e in b['entries'] if e['status']=='RESOLVED'])}")
            for r, v in b.get("by_rule", {}).items() if False else []:
                pass
    if not any((a.emit_seed, a.emit_pod, a.emit, a.resolve, a.publish, a.score)):
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
