#!/usr/bin/env python3
"""H-017 — Funding-Settlement Liquidation Cascade (CRYPTO, Binance perp free data).

Pre-registered 2026-05-18. Ring 2.6 1T review 2026-05-19 approved implementation:
"Different alpha source from H-035. Sign-flip is not transferable to cascade mechanics."

HYPOTHESIS
----------
At each 8h Binance USDT-perp funding settlement, when a *liquidation cascade* occurs
(proxied by: rapid price displacement > 1.5× 1h-ATR in the 15min around settlement
AND settlement-window volume > 2× rolling median), the displacement overshoots and
mean-reverts within 30 minutes. FADE the displacement: enter at settlement+1min,
exit at VWAP reversion or 30-min time stop, +/-15bps hard stop.

SEPARABILITY FROM H-035
  H-035 fired on EVERY settlement with extreme funding. H-017 fires only when a
  LIQUIDATION CASCADE is occurring (displacement + volume spike). The economic
  mechanism is forced-flow overshoot, not periodic payment mechanics. H-035 killed
  by sign-flip (periodic rebalancing). H-017 tests convexity events — path-dependent
  dislocations with endogenous directionality.

NOTE ON LIQUIDATION DATA
  Binance /fapi/v1/liquidationOrders only returns last 24h. Historical liquidation
  data is not freely available. This implementation uses a PROXY: price displacement
  > 1.5× ATR + volume spike > 2× median as a cascade proxy. This is a limitation —
  the proxy will capture real cascades plus some noise. If Coinalyze or other free
  historical liquidation data becomes available, replace with direct data.

ACCEPTANCE CRITERIA (pre-registered)
  * eff_floor = 0.30 (Spearman rank corr between |displacement| and |signed_ret|)
  * min_windows_admissible = 3 consecutive windows
  * cost_survival_min = 0.60 (net edge >= 60% gross after 30bps round-trip)
  * min_cascade_threshold: displacement > 1.5x ATR AND volume > 2x median

DATA
  Free: Binance USDT-perp klines + fundingRate (same as H-035).

USAGE
  python tools/h017_liquidation_cascade.py
  python tools/h017_liquidation_cascade.py --json

  # Daily shadow/paper accrual collector (Firing 13 / registry forward path for n>=50):
  python tools/h017_liquidation_cascade.py --collect
  python tools/h017_liquidation_cascade.py --collect --json
  python tools/h017_liquidation_cascade.py --collect --dry-run --json   # safe preview, no write

  Shadow log: alpha_engine/data/h017_liquidation_cascade_shadow.jsonl
  (idempotent append of resolved-style records using the exact proxy logic;
   deduped on symbol+entry_ts; compatible with validate_resolved_picks --input
   and edge_stability_harness after conversion or direct load.)

  Once n>=50 in shadow: run 6/8-gate via validate + harness (see Firing 13 sub-report).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "tools" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
REPORT_PATH = REPO_ROOT / "reports" / f"h017_liquidation_cascade_{REPORT_DATE}.json"

# Shadow accrual log for daily collector (M-107 / registry H-017 forward path)
SHADOW_LOG = REPO_ROOT / "alpha_engine" / "data" / "h017_liquidation_cascade_shadow.jsonl"

H017_ID = "H-017"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
FUNDING_WINDOW_H = 8
FUNDING_TOPN_PCT = 0.30        # Only trade when funding magnitude in top 30%
DISP_ATR_MULT = 1.5            # Displacement must exceed this × 1h ATR
VOLUME_MULT = 2.0              # Volume must exceed this × rolling median
CASCADE_WINDOW_MIN = 15        # Look-back window for cascade detection (minutes)
EXIT_WINDOW_MIN = 30           # Time stop at +30 min
COST_BPS = 30.0
EFF_FLOOR = 0.30
MIN_WINDOWS = 3
WINDOW_DAYS = 14

BASE_URL = "https://fapi.binance.com"
SEC_UA = "Mozilla/5.0 (antigravity-research/h017)"


def _http_json(url: str, timeout: int = 20) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": SEC_UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_funding_rates(symbol: str, limit: int = 1000) -> list[dict]:
    cache = CACHE_DIR / f"h017_funding_{symbol}.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < 3600:
        return json.loads(cache.read_text())
    url = f"{BASE_URL}/fapi/v1/fundingRate?symbol={symbol}&limit={limit}"
    data = _http_json(url)
    cache.write_text(json.dumps(data))
    return data


def fetch_klines_1m(symbol: str, n: int = 5000) -> list[list]:
    """Fetch recent 1-minute klines. Limit: ~3.5 days at 1m interval."""
    cache = CACHE_DIR / f"h017_klines1m_{symbol}.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < 900:
        return json.loads(cache.read_text())
    url = f"{BASE_URL}/fapi/v1/klines?symbol={symbol}&interval=1m&limit={min(n, 1500)}"
    data = _http_json(url)
    cache.write_text(json.dumps(data))
    return data


def fetch_klines_1h(symbol: str) -> list[list]:
    cache = CACHE_DIR / f"h017_klines1h_{symbol}.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < 3600:
        return json.loads(cache.read_text())
    url = f"{BASE_URL}/fapi/v1/klines?symbol={symbol}&interval=1h&limit=1000"
    data = _http_json(url)
    cache.write_text(json.dumps(data))
    return data


def _atr_map(klines_1h: list[list]) -> dict[int, float]:
    """Build {open_ts_ms: 14-period ATR} from hourly klines."""
    atr_map: dict[int, float] = {}
    n = len(klines_1h)
    for i in range(14, n):
        trs = []
        for j in range(i - 13, i + 1):
            h = float(klines_1h[j][2])
            lo = float(klines_1h[j][3])
            prev_c = float(klines_1h[j - 1][4]) if j > 0 else h
            trs.append(max(h - lo, abs(h - prev_c), abs(lo - prev_c)))
        atr = sum(trs) / len(trs)
        atr_map[int(klines_1h[i][0])] = atr
    return atr_map


def _volume_median(klines_1m: list[list]) -> float:
    vols = [float(k[5]) for k in klines_1m if float(k[5]) > 0]
    if not vols:
        return 1.0
    vols.sort()
    mid = len(vols) // 2
    return vols[mid]


def _vwap(klines_1m: list[list]) -> float:
    """Volume-weighted average price over the given 1-min bars."""
    tv, tpv = 0.0, 0.0
    for k in klines_1m:
        typ = (float(k[2]) + float(k[3]) + float(k[4])) / 3
        vol = float(k[5])
        tv += vol
        tpv += typ * vol
    return tpv / tv if tv > 0 else 0.0


def _spearman(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 4:
        return 0.0
    rx = [sorted(xs).index(x) for x in xs]
    ry = [sorted(ys).index(y) for y in ys]
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - 6 * d2 / (n * (n * n - 1))


def _walk_forward_eff(records: list[dict],
                      window_size: int = 100,
                      eff_floor: float = EFF_FLOOR,
                      min_windows: int = MIN_WINDOWS) -> dict:
    if not records:
        return {"admissible": 0, "total": 0, "mean_eff": None, "per_window": []}
    recs = sorted(records, key=lambda r: r["entry_ts"])
    n = len(recs)
    if n < window_size:
        windows = [recs]
    else:
        windows = [recs[i:i + window_size] for i in range(0, n - window_size + 1, window_size)]
    per_window = []
    for w in windows:
        scores = [r["displacement_atr"] for r in w]
        rets = [r["signed_ret"] for r in w]
        eff = _spearman(scores, rets)
        per_window.append({
            "n": len(w), "eff": round(eff, 4),
            "admissible": eff >= eff_floor,
            "date": w[0]["entry_ts_str"] + "→" + w[-1]["entry_ts_str"]
        })
    admissible = sum(1 for w in per_window if w["admissible"])
    mean_eff = round(sum(w["eff"] for w in per_window) / len(per_window), 4) if per_window else None
    return {
        "admissible": admissible,
        "total": len(per_window),
        "mean_eff": mean_eff,
        "per_window": per_window,
        "min_windows": min_windows,
    }


def _to_resolved_pick(rec: dict, run_ts: str) -> dict:
    """Convert internal cascade record to universal_resolved_picks-compatible schema.
    Used by --collect shadow mode. Adds H-017 specific meta for later analysis.
    """
    direction = rec["direction"]
    direction_str = "LONG" if direction > 0 else "SHORT"
    # Approx 15bps hard stop (per spec) for SL field; actual exit in run is VWAP or time
    sl_price = round(rec["entry_price"] * (1 - 0.0015 * direction), 6)
    # Exit reason heuristic from existing backtest fields
    exit_reason = "VWAP_REVERSION" if abs(rec["exit_price"] - rec["vwap_target"]) < 1e-5 else "TIME_STOP_30M"
    # Use gross signed_ret for pnl_pct (consistent with how harnesses see raw edge); net in meta
    pnl_pct = round(rec["signed_ret"] * 100.0, 4)
    entry_iso = rec.get("entry_ts_str", "")
    return {
        "id": f"h017_{rec['symbol']}_{rec['entry_ts']}",
        "symbol": rec["symbol"],
        "direction": direction_str,
        "entry_price": rec["entry_price"],
        "take_profit": rec["vwap_target"],
        "stop_loss": sl_price,
        "timestamp": f"{entry_iso}:00+00:00" if entry_iso else run_ts,
        "strategy": "funding_settlement_liquidation_cascade",
        "source_system": "h017_shadow_collector",
        "confidence": round(min(0.50 + (rec["displacement_atr"] * 0.12), 0.88), 3),
        "exit_price": rec["exit_price"],
        "pnl_pct": pnl_pct,
        "exit_reason": exit_reason,
        "status": "CLOSED",
        "resolved_at": run_ts,
        "current_price_at_resolve": rec["exit_price"],
        "asset_class": "CRYPTO",
        # H-017 specific (for regime splits, eff harness, post-gate analysis)
        "h017_displacement_atr": rec["displacement_atr"],
        "h017_volume_ratio": rec["volume_ratio"],
        "h017_funding_rate": rec["funding_rate"],
        "h017_net_ret_bps": round(rec["net_ret"] * 10000, 1),
        "h017_settlement_anchor": "8h_UTC",
    }


def _load_shadow_log() -> list[dict]:
    if not SHADOW_LOG.exists():
        return []
    out = []
    for line in SHADOW_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out


def _write_shadow_log_atomic(records: list[dict]) -> None:
    SHADOW_LOG.parent.mkdir(parents=True, exist_ok=True)
    tmp = SHADOW_LOG.with_suffix(SHADOW_LOG.suffix + ".tmp")
    body = "\n".join(json.dumps(r, separators=(",", ":")) for r in records)
    tmp.write_text(body + ("\n" if body else ""), encoding="utf-8")
    os.replace(tmp, SHADOW_LOG)


def collect_shadow(dry_run: bool = False, json_out: bool = False) -> int:
    """Daily shadow/paper accrual collector for H-017 (per registry forward_path).
    Re-uses the exact proxy cascade detection + resolution logic.
    Appends only *new* resolved-style records (dedup by id/symbol+ts).
    Target: accumulate n>=50 qualifying cascade trades over 30-60d of daily runs.
    Safe for CRYPTO even pre full hygiene (filter by asset_class later).
    """
    run_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print("# H-017 shadow collector (daily accrual)", file=sys.stderr)

    all_new_picks: list[dict] = []
    for sym in SYMBOLS:
        print(f"# {sym} (collect)...", file=sys.stderr, end=" ", flush=True)
        res = backtest_symbol(sym)
        n = len(res.get("records", []))
        err = res.get("error")
        print(f"raw_records={n}" + (f" ERR:{err}" if err else ""), file=sys.stderr)
        for rec in res.get("records", []):
            pick = _to_resolved_pick(rec, run_ts)
            all_new_picks.append(pick)

    # Load + dedup
    existing = _load_shadow_log()
    seen: set[tuple] = set()
    for e in existing:
        k = (e.get("symbol"), e.get("id") or e.get("timestamp", ""))
        seen.add(k)

    new_unique = []
    for p in all_new_picks:
        k = (p.get("symbol"), p.get("id") or p.get("timestamp", ""))
        if k not in seen:
            seen.add(k)
            new_unique.append(p)

    print(f"# new_unique_resolved={len(new_unique)} (total_existing_before={len(existing)})", file=sys.stderr)

    if not dry_run and new_unique:
        merged = existing + new_unique
        _write_shadow_log_atomic(merged)
        print(f"# wrote {len(new_unique)} new → {SHADOW_LOG} (total now {len(merged)})", file=sys.stderr)
    elif dry_run:
        print("# dry-run: no write performed", file=sys.stderr)
    else:
        print("# no new unique cascade events today; log unchanged", file=sys.stderr)

    # Also write a daily snapshot report (same dir as backtest reports) for audit
    daily_report = REPO_ROOT / "reports" / f"h017_shadow_collect_{REPORT_DATE}.json"
    daily_report.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "hypothesis_id": H017_ID,
        "run_mode": "collect",
        "run_ts": run_ts,
        "new_resolved": len(new_unique),
        "total_in_shadow": len(existing) + len(new_unique),
        "new_records": new_unique,
        "data_note": "Proxy cascade (displ>1.5xATR + vol>2x); 30m resolution; 15bps modeled SL. M-107 pre-reg.",
        "next": "When total_in_shadow >=50: convert jsonl to list and feed validate_resolved_picks.py --by-asset-class CRYPTO --strategy-filter 'funding_settlement_liquidation_cascade' --input ...",
    }
    daily_report.write_text(json.dumps(snapshot, indent=2))
    print(f"# daily snapshot → {daily_report}", file=sys.stderr)

    if json_out:
        print(json.dumps({"new": len(new_unique), "total": len(existing)+len(new_unique), "records": new_unique[:20]}, indent=2))

    return 0


def backtest_symbol(symbol: str) -> dict:
    try:
        funding_rates = fetch_funding_rates(symbol)
        klines_1h = fetch_klines_1h(symbol)
        klines_1m = fetch_klines_1m(symbol)
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "records": []}

    atr_map = _atr_map(klines_1h)
    vol_median = _volume_median(klines_1m)

    # Build 1-min price/volume lookup
    min_map: dict[int, dict] = {}
    for k in klines_1m:
        ts = int(k[0])
        min_map[ts] = {
            "open": float(k[1]), "high": float(k[2]),
            "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])
        }
    min_ts_sorted = sorted(min_map)

    # Funding rate threshold (top FUNDING_TOPN_PCT by magnitude)
    abs_rates = sorted([abs(float(f["fundingRate"])) for f in funding_rates], reverse=True)
    n_top = max(1, int(len(abs_rates) * FUNDING_TOPN_PCT))
    funding_threshold = abs_rates[n_top - 1] if abs_rates else 0.0

    records: list[dict] = []
    for fr in funding_rates:
        settle_ts_ms = int(fr["fundingTime"])
        rate = float(fr["fundingRate"])
        if abs(rate) < funding_threshold:
            continue

        # Settlement 1h bucket for ATR lookup (find closest)
        settle_h = settle_ts_ms // (3600_000) * 3600_000
        atr = atr_map.get(settle_h)
        if atr is None:
            # Try adjacent hour
            atr = atr_map.get(settle_h - 3600_000) or atr_map.get(settle_h + 3600_000)
        if atr is None or atr <= 0:
            continue

        # Find 1-min bars in [-CASCADE_WINDOW_MIN, +1] around settlement
        cascade_start = settle_ts_ms - CASCADE_WINDOW_MIN * 60_000
        cascade_end = settle_ts_ms + 60_000  # up to +1min for entry

        cascade_bars = [min_map[t] for t in min_ts_sorted
                        if cascade_start <= t <= cascade_end and t in min_map]
        if len(cascade_bars) < 5:
            continue

        # Measure displacement in cascade window
        prices_in_window = [b["close"] for b in cascade_bars]
        p_start = cascade_bars[0]["open"]
        p_settle_1m = cascade_bars[-1]["close"]
        displacement_raw = abs(p_settle_1m - p_start)
        displacement_atr = displacement_raw / atr

        # Volume spike check
        window_vol = sum(b["volume"] for b in cascade_bars) / len(cascade_bars)
        volume_ratio = window_vol / vol_median if vol_median > 0 else 0.0

        # Cascade condition: displacement > DISP_ATR_MULT × ATR AND volume spike
        if displacement_atr < DISP_ATR_MULT or volume_ratio < VOLUME_MULT:
            continue

        # Direction: FADE the displacement (mean-reversion)
        direction = -1 if p_settle_1m > p_start else +1

        # Entry: first 1-min bar after settlement+1min
        entry_ts = settle_ts_ms + 60_000
        entry_bar = min_map.get(entry_ts) or min_map.get(entry_ts + 60_000)
        if entry_bar is None:
            continue
        entry_price = entry_bar["close"]
        entry_ts_str = datetime.utcfromtimestamp(entry_ts / 1000).strftime("%Y-%m-%dT%H:%M")

        # VWAP target: compute VWAP of cascade window as mean-reversion target
        vwap_target = _vwap(cascade_bars)

        # Exit: find first 1-min bar where price crosses VWAP, or time stop at +EXIT_WINDOW_MIN
        exit_deadline = entry_ts + EXIT_WINDOW_MIN * 60_000
        exit_price = None
        for t in min_ts_sorted:
            if t <= entry_ts:
                continue
            if t > exit_deadline:
                break
            bar = min_map.get(t)
            if bar is None:
                continue
            if direction == +1 and bar["high"] >= vwap_target:
                exit_price = vwap_target
                break
            elif direction == -1 and bar["low"] <= vwap_target:
                exit_price = vwap_target
                break

        # Time-stop fallback
        if exit_price is None:
            stop_bar = min_map.get(exit_deadline)
            if stop_bar is None:
                # Find nearest
                for t in min_ts_sorted:
                    if t >= exit_deadline:
                        stop_bar = min_map.get(t)
                        break
            if stop_bar is None:
                continue
            exit_price = stop_bar["close"]

        if entry_price <= 0:
            continue

        raw_ret = exit_price / entry_price - 1.0
        signed_ret = raw_ret * direction
        cost_frac = COST_BPS / 10_000
        net_ret = signed_ret - cost_frac

        records.append({
            "symbol": symbol,
            "entry_ts": entry_ts,
            "entry_ts_str": entry_ts_str,
            "direction": direction,
            "funding_rate": round(rate, 6),
            "displacement_atr": round(displacement_atr, 4),
            "volume_ratio": round(volume_ratio, 3),
            "entry_price": round(entry_price, 6),
            "vwap_target": round(vwap_target, 6),
            "exit_price": round(exit_price, 6),
            "signed_ret": round(signed_ret, 8),
            "net_ret": round(net_ret, 8),
            "status": "WON" if signed_ret > 0 else "LOST",
        })

    return {"symbol": symbol, "records": records, "error": None}


def main() -> int:
    parser = argparse.ArgumentParser(description="H-017 liquidation cascade backtest / shadow collector")
    parser.add_argument("--json", dest="json_out", action="store_true", help="Emit JSON to stdout (verdict or collect summary)")
    parser.add_argument("--collect", action="store_true", help="Daily shadow/paper accrual mode: append recent resolved picks to shadow log (build n>=50)")
    parser.add_argument("--dry-run", action="store_true", help="With --collect: preview only, do not persist to shadow log")
    args = parser.parse_args()

    if args.collect:
        return collect_shadow(dry_run=args.dry_run, json_out=args.json_out)

    # --- original backtest / full-harness mode (for when longer history or verification) ---
    print("# H-017 Liquidation Cascade backtest", file=sys.stderr)

    all_records: list[dict] = []
    for sym in SYMBOLS:
        print(f"# {sym}...", file=sys.stderr, end=" ", flush=True)
        res = backtest_symbol(sym)
        n = len(res.get("records", []))
        err = res.get("error")
        print(f"n={n}" + (f" ERR:{err}" if err else ""), file=sys.stderr)
        all_records.extend(res.get("records", []))

    n = len(all_records)
    if n < 10:
        verdict = {
            "hypothesis_id": H017_ID,
            "verdict": "INSUFFICIENT_DATA",
            "n_trades": n,
            "reason": "< 10 cascade trades found — free 1-min API only covers ~3.5 days; insufficient window",
            "data_limitation": "Binance free API: /fapi/v1/liquidationOrders covers 24h; 1-min klines ~3.5 days. Full backtest requires historical data.",
            "run_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    else:
        wins = sum(1 for r in all_records if r["status"] == "WON")
        wr = wins / n
        gross_rets = [r["signed_ret"] for r in all_records]
        net_rets = [r["net_ret"] for r in all_records]
        mean_gross_bps = sum(gross_rets) / n * 10_000
        mean_net_bps = sum(net_rets) / n * 10_000

        gross_profit = sum(r for r in gross_rets if r > 0)
        gross_loss = abs(sum(r for r in gross_rets if r < 0)) or 1e-9
        pf = gross_profit / gross_loss

        cost_survival = (mean_net_bps / mean_gross_bps) if mean_gross_bps > 0 else 0.0

        harness = _walk_forward_eff(all_records)
        admissible = harness["admissible"]

        passed = (
            n >= 50
            and admissible >= MIN_WINDOWS
            and wr >= 0.50
            and cost_survival >= 0.6
        )

        verdict = {
            "hypothesis_id": H017_ID,
            "verdict": "HARNESS_PASS" if passed else "HARNESS_REJECTED",
            "n_trades": n,
            "win_rate": round(wr, 4),
            "profit_factor": round(pf, 4),
            "gross_edge_bps": round(mean_gross_bps, 3),
            "net_edge_bps": round(mean_net_bps, 3),
            "cost_survival_pct": round(cost_survival * 100, 2),
            "harness_admissible": admissible,
            "harness_total": harness["total"],
            "harness_mean_eff": harness["mean_eff"],
            "per_window": harness["per_window"],
            "acceptance_criteria": {
                "eff_floor": EFF_FLOOR,
                "min_windows": MIN_WINDOWS,
                "cost_survival_min": 0.6,
                "disp_atr_mult": DISP_ATR_MULT,
                "volume_mult": VOLUME_MULT,
            },
            "data_limitation": "Proxy-based cascade detection (displacement+volume spike). No real liquidation order data.",
            "ring_recommendation": "Implement: different alpha source from H-035 (cascade convexity vs periodic settlement). Ring 2.6 1T 2026-05-19.",
            "run_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(verdict, indent=2))
    print(f"# report → {REPORT_PATH}", file=sys.stderr)

    if args.json_out:
        print(json.dumps(verdict, indent=2))
    else:
        v = verdict.get("verdict", "?")
        n = verdict.get("n_trades", 0)
        wr = verdict.get("win_rate", 0)
        adm = verdict.get("harness_admissible", 0)
        tot = verdict.get("harness_total", 0)
        print(f"\n{'='*55}")
        print(f"H-017 VERDICT: {v}")
        print(f"  n={n}  WR={wr:.1%}  admissible_windows={adm}/{tot}")
        print(f"  gross={verdict.get('gross_edge_bps')} bps  net={verdict.get('net_edge_bps')} bps")
        print(f"  cost_survival={verdict.get('cost_survival_pct')}%")
        if verdict.get("data_limitation"):
            print(f"  NOTE: {verdict['data_limitation']}")
        print(f"{'='*55}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
