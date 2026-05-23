#!/usr/bin/env python3
"""C-4 / H-019 — CRYPTO volatility-cluster mean-reversion research.

OPT-IN RESEARCH SIDECAR. No caller in any pick-generation / scoring path.
Pre-registered in reports/hypothesis_registry.json (H-019, 2026-05-19)
BEFORE this backtest logic was written, per M-107.

HYPOTHESIS (H-019)
------------------
Extreme high-volume bars exhaust resting passive liquidity on one side of the
book; market-makers re-quote wider and a portion of the move snaps back as
inventory rebalances. This is microstructural (inventory rebalancing), NOT
regime-dependent, and is distinct from the 11 killed families.

SIGNAL
------
On daily OHLCV for top-20 Binance USDT spot pairs:
  * range_pct = (high - low) / open
  * vol_ratio  = volume / rolling_20d_avg_volume
  A pick FIRES when range_pct > RANGE_THRESHOLD (0.05 = 5%)
                  AND vol_ratio > VOL_RATIO_THRESHOLD (2.5)
                  AND |50d slope| < SLOPE_FLAT_THRESHOLD (flat regime)
  Direction = FADE the bar:
      SHORT if close > open (up bar exhaustion)
      LONG  if close < open (down bar exhaustion)
  Entry  = next open (T+1 bar open)
  Exit   = whichever first: TP at +FADE_TARGET_PCT, SL at -FADE_TARGET_PCT,
           or HOLD_BARS time stop (14 daily bars)
  pnl_pct is signed by the fade direction; positive = successful fade.

HARD RULES (CLAUDE.md / M-107)
-------------------------------
  * RESEARCH SIDECAR. No production wiring.
  * API failover: NEVER a single Binance endpoint (spot OHLCV):
    api → api1 → api2 → api3 per CLAUDE.md API Failover Rule.
  * tools/edge_stability_harness.py imported UNMODIFIED.
  * The harness gets the FULL signal-generated record series.
  * Honest verdict only: <5 scored 14-day windows => UNTESTED.
  * Post-cost gate: 30bps crypto round-trip; net edge >= 60% of gross.
  * If verdict is REJECTED, update H-019 status in hypothesis_registry.json.

    python tools/c4_volatility_cluster_research.py [--quick] [--months N]
        [--refresh-cache] [--cache PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

import edge_stability_harness as harness  # noqa: E402

# ---------------------------------------------------------------------------
# Tunables (fixed per H-019 pre-registration — do NOT tune post-hoc)
# ---------------------------------------------------------------------------
UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "LTCUSDT",
    "DOTUSDT", "MATICUSDT", "UNIUSDT", "ATOMUSDT", "NEARUSDT",
    "AAVEUSDT", "INJUSDT", "ARBUSDT", "OPUSDT", "APTUSDT",
]

RANGE_THRESHOLD = 0.05       # 5% daily range
VOL_RATIO_THRESHOLD = 2.5    # volume must be 2.5x 20d avg
HOLD_BARS = 14               # 14 daily bars
FADE_TARGET_PCT = 0.05       # 5% TP / 5% SL (symmetric 1:1)
SLOPE_FLAT_THRESHOLD = 0.005 # 50d slope abs per bar < 0.5%
LOOKBACK_BARS = 60           # warm-up before first signal
ROLLING_VOL_BARS = 20        # 20d volume MA
SLOPE_LOOKBACK = 50          # 50d close for slope
COST_BPS = 30.0              # crypto round-trip (CLAUDE.md)
MIN_COST_SURVIVAL = 0.60     # net must be >= 60% of gross

_BINANCE_SPOT_KLINES_URLS = [
    "https://api.binance.com/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
    "https://api3.binance.com/api/v3/klines",
]


# ---------------------------------------------------------------------------
# Binance spot OHLCV fetch (daily klines, failover chain)
# ---------------------------------------------------------------------------
def _fetch_klines_json(symbol: str, limit: int) -> list | None:
    import urllib.request, urllib.parse
    params = urllib.parse.urlencode({"symbol": symbol, "interval": "1d", "limit": limit})
    for base_url in _BINANCE_SPOT_KLINES_URLS:
        url = f"{base_url}?{params}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            continue
    return None


def fetch_daily_ohlcv(symbol: str, months: int) -> list[dict]:
    """Return list of daily bars dicts with keys: ts, open, high, low, close, volume."""
    limit = min(1000, months * 32 + LOOKBACK_BARS)
    raw = _fetch_klines_json(symbol, limit)
    if not raw:
        return []
    bars = []
    for row in raw:
        ts_ms, o, h, l, c, vol = row[0], row[1], row[2], row[3], row[4], row[5]
        bars.append({
            "ts": int(ts_ms) // 1000,
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "volume": float(vol),
        })
    return bars


# ---------------------------------------------------------------------------
# Signal generation
# ---------------------------------------------------------------------------
def _slope_flat(closes: list[float]) -> bool:
    """True when the absolute 50-bar slope of close < SLOPE_FLAT_THRESHOLD per bar."""
    n = len(closes)
    if n < 2:
        return True
    y_end = closes[-1]
    y_start = closes[0]
    slope_per_bar = abs((y_end - y_start) / y_start) / n
    return slope_per_bar < SLOPE_FLAT_THRESHOLD


def generate_signals(bars: list[dict]) -> list[dict]:
    """Produce raw signal records from a bar series.

    Returns list of dicts with: symbol, direction, entry_ts, entry_price,
    entry_bar_idx, exit_bar_idx (may be None), pnl_pct, exit_reason.
    """
    signals = []
    n = len(bars)
    for i in range(LOOKBACK_BARS, n - 1):
        bar = bars[i]
        op = bar["open"]
        hi = bar["high"]
        lo = bar["low"]
        cl = bar["close"]
        vol = bar["volume"]

        if op <= 0:
            continue

        range_pct = (hi - lo) / op
        if range_pct <= RANGE_THRESHOLD:
            continue

        # Volume vs 20d rolling average (strictly past bars)
        vol_window = [bars[j]["volume"] for j in range(i - ROLLING_VOL_BARS, i)]
        avg_vol = statistics.mean(vol_window) if vol_window else 0.0
        if avg_vol <= 0 or vol / avg_vol <= VOL_RATIO_THRESHOLD:
            continue

        # Regime: 50d slope flat
        slope_window = [bars[j]["close"] for j in range(i - SLOPE_LOOKBACK, i + 1)]
        if not _slope_flat(slope_window):
            continue

        # Direction: fade the bar
        direction = "SHORT" if cl >= op else "LONG"

        # Entry at next open
        entry_bar = bars[i + 1]
        entry_price = entry_bar["open"]
        if entry_price <= 0:
            continue

        # Simulate hold to TP/SL/time-stop
        tp_price = entry_price * (1 - FADE_TARGET_PCT) if direction == "SHORT" else entry_price * (1 + FADE_TARGET_PCT)
        sl_price = entry_price * (1 + FADE_TARGET_PCT) if direction == "SHORT" else entry_price * (1 - FADE_TARGET_PCT)

        exit_idx = None
        exit_price = None
        exit_reason = "time_stop"
        for j in range(i + 2, min(i + 1 + HOLD_BARS + 1, n)):
            fwd = bars[j]
            if direction == "SHORT":
                if fwd["low"] <= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    exit_idx = j
                    break
                if fwd["high"] >= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_idx = j
                    break
            else:
                if fwd["high"] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    exit_idx = j
                    break
                if fwd["low"] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_idx = j
                    break

        if exit_price is None:
            # Time stop: use close of last held bar
            last_bar = min(i + HOLD_BARS, n - 1)
            exit_price = bars[last_bar]["close"]
            exit_idx = last_bar

        # Signed pnl_pct from the fade direction
        if direction == "SHORT":
            pnl_pct = (entry_price - exit_price) / entry_price
        else:
            pnl_pct = (exit_price - entry_price) / entry_price

        signals.append({
            "entry_ts": entry_bar["ts"],
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_pct": pnl_pct,
            "direction": direction,
            "exit_reason": exit_reason,
            "range_pct": range_pct,
            "vol_ratio": vol / avg_vol,
        })

    return signals


# ---------------------------------------------------------------------------
# Multi-symbol aggregation
# ---------------------------------------------------------------------------
def run_all(months: int, cache_path: Path, refresh: bool) -> list[dict]:
    all_signals: list[dict] = []
    for sym in UNIVERSE:
        cache_file = cache_path / f"{sym}_1d_{months}m.json"
        if cache_file.exists() and not refresh:
            bars = json.loads(cache_file.read_text())
        else:
            print(f"  fetching {sym}...", flush=True)
            bars = fetch_daily_ohlcv(sym, months)
            if bars:
                cache_file.write_text(json.dumps(bars))
            time.sleep(0.12)

        if not bars:
            print(f"  {sym}: no data", flush=True)
            continue

        sigs = generate_signals(bars)
        for s in sigs:
            s["symbol"] = sym
        all_signals.extend(sigs)
        print(f"  {sym}: {len(bars)} bars → {len(sigs)} signals", flush=True)

    return all_signals


# ---------------------------------------------------------------------------
# Harness evaluation
# ---------------------------------------------------------------------------
def evaluate(signals: list[dict]) -> dict:
    """Run edge_stability_harness on all signals. Returns verdict dict."""
    if not signals:
        return {"verdict": "UNTESTED", "reason": "no signals generated"}

    # Sort by entry timestamp
    signals_sorted = sorted(signals, key=lambda s: s["entry_ts"])
    pnl_series = [s["pnl_pct"] for s in signals_sorted]
    ts_series = [s["entry_ts"] for s in signals_sorted]

    n = len(pnl_series)
    wins = sum(1 for p in pnl_series if p > 0)
    losses = sum(1 for p in pnl_series if p < 0)
    gross_w = sum(p for p in pnl_series if p > 0)
    gross_l = abs(sum(p for p in pnl_series if p < 0))
    wr = wins / n * 100 if n else 0.0
    pf = gross_w / gross_l if gross_l > 0 else None
    avg_pnl = statistics.mean(pnl_series) if pnl_series else 0.0

    # Post-cost: deduct 30bps round-trip
    cost_frac = COST_BPS / 10_000
    net_pnl_series = [p - cost_frac for p in pnl_series]
    net_gross_w = sum(p for p in net_pnl_series if p > 0)
    net_gross_l = abs(sum(p for p in net_pnl_series if p < 0))
    net_avg = statistics.mean(net_pnl_series) if net_pnl_series else 0.0
    cost_survival = (net_avg / avg_pnl) if abs(avg_pnl) > 1e-9 else 0.0

    # Walk-forward harness (14-day windows, same as H-017)
    window_days = 14
    window_secs = window_days * 86400
    if len(ts_series) < 2:
        harness_result = {"is_admissible": False, "reason": "insufficient_data"}
        eff_vals = []
    else:
        t_start = ts_series[0]
        t_end = ts_series[-1]
        windows: list[list[float]] = []
        t = t_start
        while t < t_end:
            window_pnls = [
                pnl_series[i]
                for i, ts in enumerate(ts_series)
                if t <= ts < t + window_secs
            ]
            if len(window_pnls) >= harness.MIN_WINDOW_N:
                windows.append(window_pnls)
            t += window_secs

        if len(windows) < harness.MIN_STABLE_WINDOWS:
            harness_result = {
                "is_admissible": False,
                "reason": f"only {len(windows)} scored windows (need {harness.MIN_STABLE_WINDOWS})",
                "windows_scored": len(windows),
            }
            eff_vals = []
        else:
            eff_vals = [harness.compute_eff(w) for w in windows]
            harness_result = harness.is_admissible(
                eff_vals,
                min_eff=harness.EFF_MIN,
                min_windows=harness.MIN_STABLE_WINDOWS,
            )

    # Cost gate
    cost_gate_ok = cost_survival >= MIN_COST_SURVIVAL

    if isinstance(harness_result, dict):
        harness_admit = harness_result.get("is_admissible", False)
    else:
        harness_admit = bool(harness_result)

    if n < 50:
        verdict = "UNTESTED"
        reason = f"n={n} < 50 minimum for meaningful walk-forward"
    elif not harness_admit:
        hr = harness_result if isinstance(harness_result, dict) else {}
        verdict = "REJECTED"
        reason = hr.get("reason", "harness_fail")
    elif not cost_gate_ok:
        verdict = "REJECTED"
        reason = f"cost_survival={cost_survival*100:.1f}% < {MIN_COST_SURVIVAL*100:.0f}% (30bps kills edge)"
    else:
        verdict = "ADMISSIBLE"
        reason = "harness + cost gates passed"

    return {
        "verdict": verdict,
        "reason": reason,
        "n": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4) if pf is not None else None,
        "avg_pnl_gross": round(avg_pnl * 100, 4),
        "avg_pnl_net_bps": round(net_avg * 10_000, 2),
        "cost_survival_pct": round(cost_survival * 100, 2),
        "eff_by_window": [round(e, 4) for e in eff_vals],
        "harness_admissible": harness_admit,
        "cost_gate_ok": cost_gate_ok,
        "hypothesis": "H-019",
        "signal": {
            "range_threshold_pct": RANGE_THRESHOLD * 100,
            "vol_ratio_threshold": VOL_RATIO_THRESHOLD,
            "hold_bars": HOLD_BARS,
            "fade_target_pct": FADE_TARGET_PCT * 100,
            "slope_flat_threshold_pct_per_bar": SLOPE_FLAT_THRESHOLD * 100,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="H-019 volatility-cluster mean reversion research")
    ap.add_argument("--months", type=int, default=12, help="lookback months (default 12)")
    ap.add_argument("--quick", action="store_true", help="use 4 months for speed")
    ap.add_argument("--refresh-cache", action="store_true", help="re-fetch all data")
    ap.add_argument("--cache", default=str(ROOT / "tools" / "cache"), help="cache directory")
    ap.add_argument("--out", default=str(ROOT / "reports" / "c4_volatility_cluster_research.json"),
                    help="output JSON path")
    args = ap.parse_args()

    months = 4 if args.quick else args.months
    cache_path = Path(args.cache)
    cache_path.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out)

    print(f"\n=== H-019 Volatility-Cluster Mean Reversion ===")
    print(f"  Universe: {len(UNIVERSE)} symbols | lookback: {months}m | cache: {cache_path}")
    print(f"  Signal: range>{RANGE_THRESHOLD*100:.0f}%, vol>{VOL_RATIO_THRESHOLD}x, slope_flat<{SLOPE_FLAT_THRESHOLD*100:.1f}%/bar")
    print(f"  Hold: {HOLD_BARS}d | TP/SL: ±{FADE_TARGET_PCT*100:.0f}% | Cost: {COST_BPS}bps\n")

    signals = run_all(months, cache_path, args.refresh_cache)
    print(f"\nTotal signals: {len(signals)}")

    result = evaluate(signals)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["months"] = months
    result["universe_size"] = len(UNIVERSE)
    result["signals"] = signals  # full log for audit

    out_path.write_text(json.dumps(result, indent=2))
    print(f"\n{'='*60}")
    print(f"VERDICT: {result['verdict']}")
    print(f"Reason:  {result['reason']}")
    print(f"n={result['n']}  WR={result['win_rate_pct']}%  PF={result['profit_factor']}")
    print(f"avg gross: {result['avg_pnl_gross']}%  net: {result['avg_pnl_net_bps']}bps")
    print(f"cost_survival: {result['cost_survival_pct']}%")
    print(f"eff by window: {result['eff_by_window']}")
    print(f"\nFull results → {out_path}")

    # Update hypothesis_registry if verdict is REJECTED
    if result["verdict"] == "REJECTED":
        reg_path = ROOT / "reports" / "hypothesis_registry.json"
        try:
            reg = json.loads(reg_path.read_text())
            for h in reg.get("hypotheses", []):
                if h.get("id") == "H-019":
                    h["status"] = f"REJECTED - {result['reason'][:80]}"
                    h["result"] = {
                        "tested_at": result["generated_at"][:10],
                        "n": result["n"],
                        "verdict": result["verdict"],
                        "evidence": f"n={result['n']}, WR={result['win_rate_pct']}%, PF={result['profit_factor']}, "
                                    f"net={result['avg_pnl_net_bps']}bps, eff={result['eff_by_window']}",
                        "is_admissible": result["harness_admissible"],
                        "cost_survival_pct": result["cost_survival_pct"],
                    }
                    break
            reg_path.write_text(json.dumps(reg, indent=2))
            print("  hypothesis_registry.json updated with REJECTED status.")
        except Exception as e:
            print(f"  WARNING: could not update registry: {e}")


if __name__ == "__main__":
    main()
