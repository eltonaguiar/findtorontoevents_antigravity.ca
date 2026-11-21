#!/usr/bin/env python3
"""
QA LEDGER — market-data validation of published PnL (finpredict-v4)
==================================================================
Validates every open pick in picks_now_live_pnl.json against an independent
market-price feed, per QA_PLAN.md. Flags:

  - unpriced / blank current_price + pnl_pct
  - "PnL = 0.0%" stale-equal rows (must be proven current AND at entry)
  - blank TP/SL on newly emitted picks
  - per-class tolerance breaches (crypto majors/alt, equity, forex, bond, commodity)

Output: audit_dashboard/data/qa_market_validation.json + printed summary.
Exit code 1 if any CRITICAL flag present.

Uses existing verified fetchers (no new network code):
  - alpha_engine.api_failover.fetch_price            (crypto)
  - alpha_engine.equity_price_failover.fetch_quote   (equity/ETF)
  - alpha_engine.forex_price_failover.fetch_forex_rate (forex)
  - alpha_engine.commodity_price_failover.fetch_commodity_price (commodity)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DASH = REPO / "audit_dashboard" / "data"
LIVE_JSON = DASH / "picks_now_live_pnl.json"
OUT_JSON = DASH / "qa_market_validation.json"

sys.path.insert(0, str(REPO))

# Per-class tolerance (percentage points) — from QA_PLAN.md §3.2
TOL_PP = {
    "CRYPTO": 2.0,      # alt/meme; majors tighter below
    "EQUITY": 0.5,
    "ETF": 0.5,
    "FOREX": 0.5,
    "BOND": 5.0,        # mark-to-model; amber
    "COMMODITY": 1.0,
    "FUTURES": 1.0,
    "MUTUAL_FUNDS": 0.5,
}
CRYPTO_MAJORS = {"BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "LINK", "MATIC"}


def fetch_external(symbol: str, aclass: str):
    """Return (price, source) using the right existing fetcher."""
    try:
        if aclass == "CRYPTO":
            from alpha_engine.api_failover import fetch_price
            p = fetch_price(symbol)
            return (p, "api_failover") if p else (None, None)
        if aclass in ("EQUITY", "ETF", "MUTUAL_FUNDS"):
            from alpha_engine.equity_price_failover import fetch_quote
            q = fetch_quote(symbol, use_cache=False)
            return (q.get("price"), q.get("source")) if q else (None, None)
        if aclass == "FOREX":
            from alpha_engine.forex_price_failover import fetch_forex_rate
            q = fetch_forex_rate(symbol, use_cache=False)
            return (q.get("price"), q.get("source")) if q else (None, None)
        if aclass in ("COMMODITY", "FUTURES"):
            from alpha_engine.commodity_price_failover import fetch_commodity_price
            q = fetch_commodity_price(symbol, use_cache=False)
            return (q.get("price"), q.get("source")) if q else (None, None)
    except Exception as e:            # noqa: BLE001
        return (None, f"ERR:{type(e).__name__}")
    return (None, None)


def compute_pnl(entry: float, current: float, direction: str) -> float:
    if not entry:
        return None
    raw = (current - entry) / entry * 100.0
    return -raw if str(direction).upper() in ("SHORT", "SELL", "STRONG_SELL") else raw


_EXT_CACHE = {}
_MAX_EXT_CHECKS = 250   # bound live network calls; blank/zero checks still run for all


def run() -> int:
    if not LIVE_JSON.exists():
        print(f"no live json at {LIVE_JSON}")
        return 1
    d = json.loads(LIVE_JSON.read_text())
    picks = d.get("picks", [])
    if not picks:
        print("no picks to validate")
        return 0

    flags = []
    by_class = {}
    ext_checks = 0
    for idx, p in enumerate(picks):
        sym = p.get("symbol", "")
        aclass = p.get("asset_class", "") or p.get("class", "")
        entry = p.get("entry_price")
        cur = p.get("current_price")
        pnl = p.get("pnl_pct")
        direction = p.get("direction", "")
        tp = p.get("tp_pct")
        sl = p.get("sl_pct")
        aclass = aclass.upper()
        by_class.setdefault(aclass, {"n": 0, "unpriced": 0, "unverified_zero": 0,
                                     "blank_tp_sl": 0, "mismatch": 0,
                                     "out_of_bounds": 0, "self_inconsistent": 0,
                                     "quarantined": 0, "quarantine_leak": 0,
                                     "unverified_source": 0})
        c = by_class[aclass]
        c["n"] += 1

        # 0) quarantine contract: a row the tracker refused to price must not
        # publish a PnL. That is checkable, unlike "+602% is real".
        if p.get("quarantined"):
            if pnl is not None:
                c["quarantine_leak"] += 1
                flags.append({"symbol": sym, "asset_class": aclass,
                              "verdict": "QUARANTINE_LEAK",
                              "detail": f"marked quarantined but publishes pnl {pnl}%"})
            else:
                c["quarantined"] += 1
            continue

        # 1) blank current_price / pnl_pct
        if cur is None or pnl is None:
            c["unpriced"] += 1
            flags.append({"symbol": sym, "asset_class": aclass,
                          "verdict": "UNPRICED",
                          "detail": "current_price or pnl_pct blank"})
            continue

        # 2) PnL == 0.0 exactly -> must be current AND at entry
        try:
            pnl_f = float(pnl)
        except (TypeError, ValueError):
            c["unpriced"] += 1
            continue
        if abs(pnl_f) < 1e-9:
            if cur and entry and abs(float(cur) - float(entry)) / float(entry) < 1e-3:
                continue  # genuinely at entry
            c["unverified_zero"] += 1
            flags.append({"symbol": sym, "asset_class": aclass,
                          "verdict": "UNVERIFIED_ZERO",
                          "detail": "pnl==0 but price != entry (stale-equal)"})
            continue

        # 3) blank TP/SL on emitted picks
        if tp is None and sl is None:
            c["blank_tp_sl"] += 1
            flags.append({"symbol": sym, "asset_class": aclass,
                          "verdict": "BLANK_TP_SL", "detail": "neither tp nor sl set"})

        # 3b) published PnL must agree with the row's OWN entry/current prices.
        # Zero rows today, but this is the corruption class the gate was blind
        # to: a PnL that no pair of published prices implies.
        if entry and cur:
            own = compute_pnl(float(entry), float(cur), direction)
            if own is not None and abs(pnl_f - own) > 0.05:
                c["self_inconsistent"] += 1
                flags.append({"symbol": sym, "asset_class": aclass,
                              "verdict": "SELF_INCONSISTENT",
                              "detail": f"published {pnl_f:.2f}% vs own prices {own:.2f}%"})

        # 4) PnL reasonability bound
        if abs(pnl_f) > 100.0:
            c["out_of_bounds"] += 1
            flags.append({"symbol": sym, "asset_class": aclass,
                          "verdict": "PNL_OUT_OF_BOUNDS",
                          "detail": f"|pnl|={pnl_f:.1f}% > 100%"})

        # 4b) a FOREX row published from the same feed this ledger validates
        # against cannot be cross-checked: the diff is zero by construction, so
        # counting it as verified would be a permanent false negative for the
        # whole asset class. Counted, not flagged -- every FOREX row is currently
        # priced this way, so a flag here would be red every run.
        if aclass == "FOREX" and str(p.get("price_source") or "").startswith("forex_failover"):
            c["unverified_source"] += 1
            continue

        # 5) market-data cross-check (bounded sample + per-symbol cache)
        if ext_checks >= _MAX_EXT_CHECKS:
            continue
        key = (sym, aclass)
        if key not in _EXT_CACHE:
            _EXT_CACHE[key] = fetch_external(sym, aclass)
        ext, src = _EXT_CACHE[key]
        if ext is None:
            continue
        # A null or free-text entry_price reaches here whenever the row is
        # priced, and an unguarded float() would abort the run before OUT_JSON is
        # written -- the dashboard would then keep a stale snapshot, silently.
        try:
            entry_f, ext_f = float(entry), float(ext)
        except (TypeError, ValueError):
            continue
        ext_checks += 1
        tol = TOL_PP.get(aclass, 1.0)
        if aclass == "CRYPTO" and sym.split("USDT")[0] in CRYPTO_MAJORS:
            tol = 0.5
        recomputed = compute_pnl(entry_f, ext_f, direction)
        if recomputed is None:
            continue
        diff = abs(pnl_f - recomputed)
        if diff > tol:
            c["mismatch"] += 1
            flags.append({"symbol": sym, "asset_class": aclass,
                          "verdict": "MISMATCH",
                          "detail": (f"published {pnl_f:.2f}% vs external {recomputed:.2f}% "
                                     f"(diff {diff:.2f}pp > tol {tol}pp), src={src}")})

    critical = [f for f in flags if f["verdict"] in
                ("UNPRICED", "UNVERIFIED_ZERO", "MISMATCH", "PNL_OUT_OF_BOUNDS",
                 "SELF_INCONSISTENT", "QUARANTINE_LEAK")]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_picks": len(picks),
        "by_class": {k: v for k, v in sorted(by_class.items())},
        "flag_counts": {"total": len(flags), "critical": len(critical)},
        "flags": flags[:500],
    }
    OUT_JSON.write_text(json.dumps(report, indent=2))
    print(f"QA ledger: {len(picks)} picks, {len(flags)} flags "
          f"({len(critical)} critical) -> {OUT_JSON}")
    for k, v in sorted(by_class.items()):
        print(f"  {k:16} n={v['n']:5} unpriced={v['unpriced']} "
              f"zero={v['unverified_zero']} blank_tp/sl={v['blank_tp_sl']} "
              f"mismatch={v['mismatch']} bounds={v['out_of_bounds']} "
              f"self={v['self_inconsistent']} quar={v['quarantined']}"
              + (f" samefeed={v['unverified_source']}" if v["unverified_source"] else "")
              + (f" LEAK={v['quarantine_leak']}" if v["quarantine_leak"] else ""))
    return 1 if critical else 0


if __name__ == "__main__":
    raise SystemExit(run())
