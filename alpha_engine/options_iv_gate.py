#!/usr/bin/env python3
"""
options_iv_gate.py — opt-in CBOE IV/skew forward-collector + (future) equity-long gate
======================================================================================

WHY THIS EXISTS (2026-06-13 money-ready loop, operator question "can options/greeks help?").
The exhaustive hunt concluded the current pick book has no regime-controlled edge in any
class. Options-DERIVED signals are the one genuinely new, not-yet-refuted input — but with a
hard constraint verified live this session: our four paid market-data keys
(FINNHUB/FMP/ALPHAVANTAGE/TIINGO) return ZERO options data, and there is NO free historical
equity option-chain archive. The only usable equity feed is the FREE CBOE delayed-quote chain
(full greeks + iv30, but a point-in-time SNAPSHOT). So any equity options signal must be
FORWARD-COLLECTED before it can be honestly evaluated — you cannot backtest it.

This module is **Phase 0: the forward-collector** + a documented gate STUB.

  Phase 0 (this file, now): a read-only daily collector that snapshots, per equity/ETF symbol,
    the options-implied features we'd gate on — iv30, ATM IV, 25-delta skew (risk-reversal),
    put/call OI & volume ratios, and a dealer-gamma (GEX) proxy — appending one idempotent row
    per (date, symbol) to alpha_engine/data/options_iv_snapshots.jsonl. It emits NO picks,
    changes NO production behavior, and is not imported by any pick/score path. It exists to
    accumulate the history we cannot buy.

  Phase 1 (LATER, gated on data): once >=40-60 trading days are collected, wire
    passes_iv_gate(symbol, direction) into the production equity gate to suppress / down-size
    new LONGs when iv30 is bottom-decile (vol-expansion risk) AND 25-delta skew is in the crash
    zone. Keep the gate ONLY if the gated-long cohort beats the ungated cohort on NET-of-cost PF
    across >=3 consecutive 14-day walk-forward windows (reuse tools/edge_stability_harness.py).
    Given 8 prior options/flow harness kills, treat the base rate as "probably won't clear".

## Wiring Plan (CLAUDE.md Wire-Up Rule, clause 2 — opt-in sidecar)
- Target caller (Phase 1 only): the production equity gate that owns `passes_active_gate` /
  `passes_smart_gate` (audit_trail/quality_gates.py) — add a `passes_iv_gate()` call for
  category in (EQUITY, ETF), LONG only.
- Until Phase 1: this file has NO production caller by design. `passes_iv_gate()` is a
  documented no-op that returns (allow=True, reason="gate-inactive: insufficient IV history").
- Activation is double-gated: env OPTIONS_IV_GATE_ENABLED=1 AND the forward harness must have
  earned it. Neither is set today.

NOT VRP. NOT a vol trade. NOT a paid-data purchase. A defensive long-filter, forward-validated.

Usage (read-only; no DB writes; CBOE is keyless):
  python3 alpha_engine/options_iv_gate.py --collect --limit 40        # snapshot top-40 by stock_ohlcv coverage
  python3 alpha_engine/options_iv_gate.py --collect --symbols SPY QQQ AAPL NVDA
  python3 alpha_engine/options_iv_gate.py --status                    # summarize accumulated history
  python3 alpha_engine/options_iv_gate.py --self-test                 # no network

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DATA_DIR = REPO_ROOT / "alpha_engine" / "data"
SNAPSHOT_FILE = DATA_DIR / "options_iv_snapshots.jsonl"

# Phase-1 gate thresholds (NOT active until OPTIONS_IV_GATE_ENABLED=1 and the harness earns it).
MIN_HISTORY_DAYS = 40
IV30_BOTTOM_DECILE = None   # filled from accumulated history at activation
SKEW_CRASH_DECILE = None


# --------------------------------------------------------------------------- #
# OCC option-symbol parsing (root + YYMMDD + C/P + 8-digit strike, 3 implied decimals)
# --------------------------------------------------------------------------- #
def parse_occ(occ: str) -> dict | None:
    """'AAPL260612C00110000' -> {expiry:'2026-06-12', type:'C', strike:110.0}.
    Root is variable-length; the meaningful tail is always the last 15 chars."""
    if not occ or len(occ) < 16:
        return None
    tail = occ[-15:]
    yy, mm, dd = tail[0:2], tail[2:4], tail[4:6]
    cp = tail[6]
    try:
        strike = int(tail[7:]) / 1000.0
    except ValueError:
        return None
    if cp not in ("C", "P"):
        return None
    return {"expiry": f"20{yy}-{mm}-{dd}", "type": cp, "strike": strike}


def _f(x):
    try:
        v = float(x)
        return v
    except (TypeError, ValueError):
        return None


def _nearest_expiry(rows: list, asof: date, min_dte: int = 7) -> str | None:
    """Pick the nearest expiry that is at least `min_dte` days out (front-month, not 0DTE)."""
    exps = set()
    for r in rows:
        p = r.get("_p")
        if p:
            exps.add(p["expiry"])
    best = None
    for e in exps:
        try:
            dte = (date.fromisoformat(e) - asof).days
        except ValueError:
            continue
        if dte >= min_dte and (best is None or dte < best[1]):
            best = (e, dte)
    return best[0] if best else None


# --------------------------------------------------------------------------- #
# Feature extraction from one CBOE chain snapshot
# --------------------------------------------------------------------------- #
def compute_features(chain: dict, asof: date | None = None, min_dte: int = 7) -> dict | None:
    """Return per-symbol options features from a CBOE delayed_quotes chain dict."""
    data = (chain or {}).get("data") or {}
    opts = data.get("options") or []
    if not opts:
        return None
    asof = asof or date.today()
    spot = _f(data.get("current_price")) or _f(data.get("close"))
    iv30 = _f(data.get("iv30"))

    rows = []
    for o in opts:
        p = parse_occ(o.get("option", ""))
        if not p:
            continue
        o = dict(o)
        o["_p"] = p
        rows.append(o)
    if not rows:
        return None

    exp = _nearest_expiry(rows, asof, min_dte)
    front = [r for r in rows if r["_p"]["expiry"] == exp] if exp else rows

    # put/call ratios over the front-month
    call_oi = sum(_f(r.get("open_interest")) or 0 for r in front if r["_p"]["type"] == "C")
    put_oi = sum(_f(r.get("open_interest")) or 0 for r in front if r["_p"]["type"] == "P")
    call_vol = sum(_f(r.get("volume")) or 0 for r in front if r["_p"]["type"] == "C")
    put_vol = sum(_f(r.get("volume")) or 0 for r in front if r["_p"]["type"] == "P")

    # 25-delta risk reversal: iv(put @ delta=-0.25) - iv(call @ delta=+0.25)
    def closest(target_delta, typ):
        best = None
        for r in front:
            if r["_p"]["type"] != typ:
                continue
            d = _f(r.get("delta"))
            iv = _f(r.get("iv"))
            if d is None or iv is None or iv <= 0:
                continue
            dist = abs(d - target_delta)
            if best is None or dist < best[0]:
                best = (dist, iv, d)
        return best
    c25 = closest(0.25, "C")
    p25 = closest(-0.25, "P")
    skew_25d = (p25[1] - c25[1]) if (c25 and p25) else None
    call25_iv = c25[1] if c25 else None
    put25_iv = p25[1] if p25 else None

    # ATM IV: mean iv of the strikes nearest spot (calls+puts), front-month
    atm_iv = None
    if spot:
        near = sorted(front, key=lambda r: abs(r["_p"]["strike"] - spot))[:6]
        ivs = [_f(r.get("iv")) for r in near if _f(r.get("iv")) and _f(r.get("iv")) > 0]
        atm_iv = (sum(ivs) / len(ivs)) if ivs else None

    # Dealer-gamma proxy (GEX): sum(gamma*OI) calls minus puts (sign convention: dealers
    # typically short calls / long puts; this is a proxy, documented not load-bearing).
    call_gex = sum((_f(r.get("gamma")) or 0) * (_f(r.get("open_interest")) or 0)
                   for r in front if r["_p"]["type"] == "C")
    put_gex = sum((_f(r.get("gamma")) or 0) * (_f(r.get("open_interest")) or 0)
                  for r in front if r["_p"]["type"] == "P")
    gex_proxy = (call_gex - put_gex) * (spot or 1.0)

    return {
        "spot": round(spot, 4) if spot else None,
        "iv30": round(iv30, 4) if iv30 is not None else None,
        "front_expiry": exp,
        "atm_iv": round(atm_iv, 4) if atm_iv else None,
        "skew_25d": round(skew_25d, 4) if skew_25d is not None else None,
        "call25_iv": round(call25_iv, 4) if call25_iv else None,
        "put25_iv": round(put25_iv, 4) if put25_iv else None,
        "put_call_oi": round(put_oi / call_oi, 4) if call_oi else None,
        "put_call_vol": round(put_vol / call_vol, 4) if call_vol else None,
        "gex_proxy": round(gex_proxy, 2),
        "n_contracts": len(rows),
        "n_front": len(front),
    }


# --------------------------------------------------------------------------- #
# Phase-1 gate STUB (documented no-op until activated)
# --------------------------------------------------------------------------- #
def passes_iv_gate(symbol: str, direction: str) -> tuple[bool, str]:
    """Phase-1 equity-LONG IV/skew gate. INACTIVE until OPTIONS_IV_GATE_ENABLED=1 AND
    >=MIN_HISTORY_DAYS of snapshots exist AND the forward harness has earned it.
    Returns (allow, reason). Today: always allow (no-op)."""
    import os
    if os.environ.get("OPTIONS_IV_GATE_ENABLED", "0").strip().lower() not in ("1", "true", "yes", "on"):
        return True, "gate-inactive: OPTIONS_IV_GATE_ENABLED not set (Phase 0 collect-only)"
    # Activation path (only reached when explicitly enabled): require accumulated history.
    days = _distinct_dates()
    if days < MIN_HISTORY_DAYS:
        return True, f"gate-inactive: only {days}/{MIN_HISTORY_DAYS} history days collected"
    # Decile thresholds must be wired from history before this branch can veto; until then,
    # allow (fail-open) so an enabled-but-unfitted gate never silently blocks production.
    return True, "gate-active-but-unfitted: deciles not yet calibrated (fail-open)"


def _distinct_dates() -> int:
    if not SNAPSHOT_FILE.exists():
        return 0
    dates = set()
    with SNAPSHOT_FILE.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                dates.add(json.loads(line).get("date"))
            except Exception:
                continue
    return len({d for d in dates if d})


# --------------------------------------------------------------------------- #
# Collector
# --------------------------------------------------------------------------- #
def _universe_from_db(limit: int | None) -> list[str]:
    """Equity/ETF symbols from stock_ohlcv (exclude FX =X / futures =F), most-covered first."""
    import os
    os.environ.setdefault("DB_PASS_STOCKS", os.environ.get("DB_PASS_STOCKS", ""))
    import pymysql
    from tools.db_env import get_stocks_creds
    conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute("SELECT symbol, COUNT(*) c FROM stock_ohlcv GROUP BY symbol ORDER BY c DESC")
    syms = [r["symbol"] for r in cur.fetchall()
            if "=X" not in r["symbol"] and "=F" not in r["symbol"]]
    conn.close()
    return syms[:limit] if limit else syms


def _load_existing_keys() -> set:
    keys = set()
    if not SNAPSHOT_FILE.exists():
        return keys
    with SNAPSHOT_FILE.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                keys.add((r.get("date"), r.get("symbol")))
            except Exception:
                continue
    return keys


def collect(symbols: list[str]) -> int:
    from tools.options_flow_research import fetch_cboe_chain_snapshot
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    existing = _load_existing_keys()
    appended = 0
    with SNAPSHOT_FILE.open("a") as fh:
        for sym in symbols:
            if (today, sym) in existing:
                continue
            chain = fetch_cboe_chain_snapshot(sym)
            if not chain:
                print(f"  {sym}: no CBOE chain (likely no listed options)", file=sys.stderr)
                continue
            feat = compute_features(chain)
            if not feat:
                print(f"  {sym}: chain had no parseable options", file=sys.stderr)
                continue
            row = {"date": today, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "symbol": sym, **feat}
            fh.write(json.dumps(row) + "\n")
            existing.add((today, sym))
            appended += 1
            print(f"  {sym:6s} iv30={feat['iv30']} atm_iv={feat['atm_iv']} "
                  f"skew25={feat['skew_25d']} pc_oi={feat['put_call_oi']} exp={feat['front_expiry']}")
    print(f"\n[collect] appended {appended} new snapshots to {SNAPSHOT_FILE}")
    print(f"[collect] distinct history days now: {_distinct_dates()} "
          f"(gate needs {MIN_HISTORY_DAYS})")
    return appended


def status() -> int:
    if not SNAPSHOT_FILE.exists():
        print("no snapshots collected yet"); return 0
    n = sum(1 for _ in SNAPSHOT_FILE.open())
    print(f"snapshots: {n} rows, {_distinct_dates()} distinct dates (gate needs {MIN_HISTORY_DAYS})")
    return 0


# --------------------------------------------------------------------------- #
def _self_test() -> int:
    assert parse_occ("AAPL260612C00110000") == {"expiry": "2026-06-12", "type": "C", "strike": 110.0}
    assert parse_occ("SPY260920P00450000") == {"expiry": "2026-09-20", "type": "P", "strike": 450.0}
    assert parse_occ("") is None
    # synthetic chain: spot 100; put25 iv 0.30, call25 iv 0.20 -> skew +0.10
    chain = {"data": {"current_price": 100.0, "iv30": 25.0, "options": [
        {"option": "XYZ260920C00100000", "delta": 0.50, "iv": 0.22, "gamma": 0.05, "open_interest": 100, "volume": 10},
        {"option": "XYZ260920C00110000", "delta": 0.25, "iv": 0.20, "gamma": 0.03, "open_interest": 50, "volume": 5},
        {"option": "XYZ260920P00100000", "delta": -0.50, "iv": 0.24, "gamma": 0.05, "open_interest": 200, "volume": 40},
        {"option": "XYZ260920P00090000", "delta": -0.25, "iv": 0.30, "gamma": 0.03, "open_interest": 80, "volume": 8},
    ]}}
    f = compute_features(chain, asof=date(2026, 6, 13))
    assert f["front_expiry"] == "2026-09-20", f
    assert abs(f["skew_25d"] - 0.10) < 1e-6, f
    assert abs(f["put_call_oi"] - (280 / 150)) < 1e-3, f   # tool rounds to 4dp
    assert abs(f["put_call_vol"] - (48 / 15)) < 1e-3, f
    assert f["n_front"] == 4, f
    allow, reason = passes_iv_gate("AAPL", "LONG")
    assert allow and "inactive" in reason, (allow, reason)
    print("[self-test] all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--collect", action="store_true", help="fetch + append today's snapshots")
    ap.add_argument("--symbols", nargs="+", help="explicit symbol list (else stock_ohlcv universe)")
    ap.add_argument("--limit", type=int, default=40, help="cap universe size when --symbols absent")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if args.status:
        return status()
    if args.collect:
        syms = args.symbols or _universe_from_db(args.limit)
        print(f"[collect] {len(syms)} symbols (CBOE keyless, read-only)")
        return 0 if collect(syms) >= 0 else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
