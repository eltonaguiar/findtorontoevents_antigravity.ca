#!/usr/bin/env python3
"""Reconcile the provenance ledger against the audit dashboard.

The ledger and `audit_dashboard/data/dashboard_data.json` are two populations of the
same thing: the picks this system emitted. Any divergence is a defect in one of them,
and the point of this tool is to name which one rather than to make the numbers agree.

WHY THIS EXISTS
    The provenance ledger only proves anything if it sees the same picks the rest of
    the system reports. A ledger that agrees with itself and disagrees with the
    dashboard measures a parallel universe. The first question is therefore not "is
    the chain valid" (that is `provenance_ledger.py --verify`) but "does the chain
    cover the same picks".

MATCHING
    Key = (normalised symbol, side, strategy) plus a time window. Symbols are
    normalised through provenance_resolver.resolve_symbol so BTCUSDT and BTC-USD
    compare equal. The window exists because the ledger records EMIT time and the
    dashboard records TRADE time; they are not the same instant.

CATEGORIES
    in_both              matched within the window
    ledger_only          emitted, never appeared on the dashboard
    dashboard_only       on the dashboard, never emitted through the hook
    symbol_mismatch      same strategy+side, different normalised symbol
    near_miss            same key, but timestamps further apart than the window

    `dashboard_only` is the survivorship category and the reason the tool exists: a
    pick that never passed through the emit hook is invisible to the ledger, so no
    forward credit can ever be assigned to it.

HONEST NO-DATA
    If either side is empty the tool reports NO DATA and exits 0. It never reports
    "100% coverage" from an empty intersection, and it never invents rows to make the
    reconciliation look tidy.

Usage:
    python3 tools/provenance_reconcile.py
    python3 tools/provenance_reconcile.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "reports/provenance/picks_provenance.jsonl"
DASH = REPO / "audit_dashboard/data/dashboard_data.json"
OUT = REPO / "reports/provenance/reconciliation.json"

MATCH_WINDOW_HOURS = 72      # emit time vs trade time
NEAR_MISS_HOURS = 720        # within 30 days = a near miss worth naming


def _dt(v):
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _norm_symbol(sym: str) -> str:
    try:
        if str(REPO / "tools") not in sys.path:
            sys.path.insert(0, str(REPO / "tools"))
        from provenance_resolver import resolve_symbol  # noqa: PLC0415
        return resolve_symbol(sym)[0]
    except Exception:  # noqa: BLE001
        return (sym or "").strip().upper()


def _side(v) -> str:
    s = (v or "").strip().upper()
    if s in ("LONG", "BUY", "BULL", "BULLISH"):
        return "LONG"
    if s in ("SHORT", "SELL", "BEAR", "BEARISH"):
        return "SHORT"
    return s or "?"


def load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.open():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def load_dashboard(p: Path = DASH) -> list[dict]:
    if not p.exists():
        return []
    try:
        d = json.load(p.open())
    except (json.JSONDecodeError, OSError):
        return []
    return (d.get("picks") or {}).get("recent_closed") or []


def _key(sym, side, strat) -> tuple[str, str, str]:
    return (_norm_symbol(sym), _side(side), (strat or "unknown").strip())


def reconcile(ledger: list[dict], dash: list[dict]) -> dict:
    """Pure: takes both populations, returns the reconciliation payload.

    Matching is PER ROW, not per key-group. Matching by key and then excluding every
    dashboard row sharing that key undercounts `dashboard_only` whenever a key appears
    more than once on the dashboard -- which it does: this dashboard carries repeated
    (symbol, side, strategy) rows, and an earlier round measured 1,864 duplicate
    signal-timestamp groups. So each dashboard row is consumed at most once, greedily
    nearest-timestamp-first.
    """
    lg = {}
    for r in ledger:
        k = _key(r.get("symbol"), r.get("side"), r.get("strategy"))
        lg.setdefault(k, []).append(r)
    dh = {}
    for i, p in enumerate(dash):
        k = _key(p.get("symbol"), p.get("direction"), p.get("strategy"))
        dh.setdefault(k, []).append((i, p))

    consumed: set[int] = set()
    in_both, near_miss, ledger_only = [], [], []
    for k, lrows in lg.items():
        cand = dh.get(k) or []
        for lr in lrows:
            lt = _dt(lr.get("created_at"))
            best_i, best_gap = None, None
            for i, dr in cand:
                if i in consumed:
                    continue
                dtp = _dt(dr.get("timestamp")) or _dt(dr.get("closed_at"))
                if not lt or not dtp:
                    continue
                gap = abs((dtp - lt).total_seconds()) / 3600.0
                if best_gap is None or gap < best_gap:
                    best_i, best_gap = i, gap
            if best_i is None:
                if cand:
                    near_miss.append({"reason": "no comparable timestamp",
                                      "ledger": _slim(lr)})
                else:
                    ledger_only.append(lr)
            elif best_gap is not None and best_gap <= MATCH_WINDOW_HOURS:
                consumed.add(best_i)
                in_both.append({"gap_hours": round(best_gap, 2),
                                "symbol": lr.get("symbol"),
                                "side": lr.get("side"), "strategy": lr.get("strategy")})
            else:
                # matched key but far apart: consumes nothing, so the dashboard row
                # stays available and correctly lands in dashboard_only too
                near_miss.append({"reason": f"timestamp gap {best_gap:.1f}h "
                                            f"(> {MATCH_WINDOW_HOURS}h window)",
                                  "ledger": _slim(lr)})

    dashboard_only = [p for i, p in enumerate(dash) if i not in consumed]

    # symbol_mismatch: same (side, strategy) present on both sides under DIFFERENT
    # normalised symbols. Named rather than silently counted as unmatched.
    lg_sym = {(_key(r.get("symbol"), r.get("side"), r.get("strategy"))[1],
               _key(r.get("symbol"), r.get("side"), r.get("strategy"))[2],
               _key(r.get("symbol"), r.get("side"), r.get("strategy"))[0])
              for r in ledger}
    dh_sym = {(_key(p.get("symbol"), p.get("direction"), p.get("strategy"))[1],
               _key(p.get("symbol"), p.get("direction"), p.get("strategy"))[2],
               _key(p.get("symbol"), p.get("direction"), p.get("strategy"))[0])
              for p in dash}
    mismatch = []
    for side, strat, sym in sorted(lg_sym - dh_sym):
        others = sorted(s for (s2, st2, s) in dh_sym
                        if s2 == side and st2 == strat and s != sym)
        if others:
            mismatch.append({"side": side, "strategy": strat,
                             "ledger_symbol": sym, "dashboard_symbols": others[:5]})

    def by_class(rows, getter):
        out: dict[str, int] = {}
        for r in rows:
            c = getter(r) or "UNKNOWN"
            out[c] = out.get(c, 0) + 1
        return dict(sorted(out.items()))

    n_led, n_dash = len(ledger), len(dash)
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {"ledger": str(LEDGER.relative_to(REPO)),
                    "dashboard": str(DASH.relative_to(REPO))},
        "match_window_hours": MATCH_WINDOW_HOURS,
        "counts": {
            "ledger_total": n_led,
            "dashboard_total": n_dash,
            "in_both": len(in_both),
            "ledger_only": len(ledger_only),
            "dashboard_only": len(dashboard_only),
            "near_miss": len(near_miss),
            "symbol_mismatch": len(mismatch),
        },
        "coverage": {
            "ledger_covered_pct": round(100 * len(in_both) / n_led, 1) if n_led else None,
            "dashboard_covered_pct": (round(100 * len(in_both) / n_dash, 1)
                                      if n_dash else None),
        },
        "by_asset_class": {
            "ledger_only": by_class(ledger_only, lambda r: r.get("asset_class")),
            "dashboard_only": by_class(dashboard_only, lambda p: p.get("asset_class")),
        },
        "examples": {
            "ledger_only": [_slim(r) for r in ledger_only[:5]],
            "dashboard_only": [_slim(p) for p in dashboard_only[:5]],
            "near_miss": near_miss[:5],
            "symbol_mismatch": mismatch[:5],
        },
    }
    if n_led == 0 and n_dash == 0:
        payload["status"] = "NO DATA"
        payload["explanation"] = ("both sides empty - nothing to reconcile. Not a "
                                  "pass: coverage is undefined, not 100%.")
    elif n_led == 0:
        payload["status"] = "NO DATA"
        payload["explanation"] = (
            f"ledger is EMPTY while the dashboard carries {n_dash} closed picks, so "
            f"0% of dashboard picks are forward-creditable. This is the survivorship "
            f"defect the ledger exists to close, not a reconciliation result.")
    elif n_dash == 0:
        payload["status"] = "NO DATA"
        payload["explanation"] = ("dashboard carries no closed picks - nothing to "
                                  "compare the ledger against.")
    else:
        payload["status"] = "OK"
        payload["explanation"] = (
            "dashboard_only is the survivorship count: those picks never passed "
            "through the emit hook, so no forward credit can be assigned to them. "
            "ledger_only means a hook fired for a pick the dashboard does not show. "
            "near_miss and symbol_mismatch are keying failures, not coverage failures.")
    return payload


def _slim(r: dict) -> dict:
    return {k: r.get(k) for k in ("symbol", "side", "direction", "strategy",
                                  "source_system", "asset_class", "created_at",
                                  "timestamp", "closed_at")
            if r.get(k) is not None}


def selftest() -> int:
    print("=" * 74)
    print("SELFTEST -- reconciliation counts exactly, and refuses to fake coverage")
    print("=" * 74)

    led = [
        {"symbol": "BTCUSDT", "side": "LONG", "strategy": "s1",
         "created_at": "2026-11-01T00:00:00+00:00"},
        {"symbol": "EURUSD", "side": "SHORT", "strategy": "s2",
         "created_at": "2026-11-01T00:00:00+00:00"},
        {"symbol": "SPY", "side": "LONG", "strategy": "s3",
         "created_at": "2026-11-01T00:00:00+00:00"},          # ledger only
    ]
    dash = [
        # BTC-USD normalises to the SAME symbol as BTCUSDT -> must match
        {"symbol": "BTC-USD", "direction": "LONG", "strategy": "s1",
         "timestamp": "2026-11-01T02:00:00+00:00", "asset_class": "CRYPTO"},
        {"symbol": "EUR/USD", "direction": "SHORT", "strategy": "s2",
         "timestamp": "2026-11-01T01:00:00+00:00", "asset_class": "FOREX"},
        {"symbol": "QQQ", "direction": "LONG", "strategy": "s4",
         "timestamp": "2026-11-01T00:00:00+00:00", "asset_class": "ETF"},
    ]                                                          # QQQ is dashboard only
    r = reconcile(led, dash)
    c = r["counts"]
    print(f"  counts: {c}")
    assert c["in_both"] == 2, f"expected 2 matches, got {c['in_both']}"
    assert c["ledger_only"] == 1, f"expected 1 ledger-only, got {c['ledger_only']}"
    assert c["dashboard_only"] == 1, "expected 1 dashboard-only"
    print("  symbol normalisation BTCUSDT == BTC-USD matched          ok")
    print("  EURUSD == EUR/USD matched                                ok")
    print("  unmatched counted once each side                         ok")
    assert r["coverage"]["ledger_covered_pct"] == round(200 / 3, 1)
    print(f"  coverage reported as a real fraction, not a pass: "
          f"{r['coverage']}")

    # empty ledger must NOT read as success
    r2 = reconcile([], dash)
    print(f"\n  empty ledger + {len(dash)} dashboard picks -> status={r2['status']}")
    assert r2["status"] == "NO DATA"
    assert r2["coverage"]["ledger_covered_pct"] is None
    print("  coverage is None (undefined), NOT 100%                 ok")

    r3 = reconcile([], [])
    print(f"  both empty -> status={r3['status']}, coverage="
          f"{r3['coverage']['ledger_covered_pct']}                  ok")
    assert r3["status"] == "NO DATA"

    # a far-out timestamp must be a near miss, not a match
    dash_far = [dict(dash[0], timestamp="2026-10-01T00:00:00+00:00")]
    r4 = reconcile([led[0]], dash_far)
    print(f"\n  same key, 744h apart -> in_both={r4['counts']['in_both']} "
          f"near_miss={r4['counts']['near_miss']}")
    assert r4["counts"]["in_both"] == 0 and r4["counts"]["near_miss"] == 1
    print("  outside the window is NOT counted as coverage              ok")

    print("\n  ALL RECONCILE SELFTESTS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    ledger = load_jsonl(LEDGER)
    dash = load_dashboard()
    print(f"ledger records: {len(ledger)}   dashboard closed picks: {len(dash)}")
    payload = reconcile(ledger, dash)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1))
    print(json.dumps({k: payload[k] for k in
                      ("status", "counts", "coverage", "explanation")}, indent=1))
    print(f"\nwrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
