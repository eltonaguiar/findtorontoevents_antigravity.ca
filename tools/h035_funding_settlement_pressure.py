#!/usr/bin/env python3
"""
H-035: Crypto 8h Funding-Settlement Pressure Timing
Pre-registered 2026-05-19 per M-107 gate.

Tests whether the mechanical longs→shorts payment at each 8h Binance settlement
creates a predictable SHORT pressure (T-4h to T+0) and/or LONG rebound (T+0 to T+4h).

Run:
    python tools/h035_funding_settlement_pressure.py
    python tools/h035_funding_settlement_pressure.py --symbols BTCUSDT ETHUSDT --min-n 5
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "tools" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = REPO_ROOT / "reports" / "h035_funding_settlement_2026-05-19.md"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
FUNDING_WINDOW_H = 8       # Binance perp funding interval
PRE_SETTLE_H = 4           # Enter SHORT this many hours before settlement
POST_SETTLE_H = 4          # LONG rebound window after settlement
FUNDING_TOPN_PCT = 0.30    # Trade only top-30% funding rate magnitudes
WINDOW_DAYS = 14
MIN_N = 10                 # Lowered from harness default 20 (sparse events)
EFF_FLOOR = 0.30
MIN_WINDOWS = 3
COST_BPS = 30              # Round-trip cost budget

BASE_URL = "https://fapi.binance.com"
SEC_UA = "Mozilla/5.0 (antigravity-research/h035)"


def _http_json(url: str, timeout: int = 20) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": SEC_UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_funding_rates(symbol: str, limit: int = 1000) -> list[dict]:
    cache_path = CACHE_DIR / f"h035_funding_{symbol}.json"
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < 3600:
        return json.loads(cache_path.read_text())
    url = f"{BASE_URL}/fapi/v1/fundingRate?symbol={symbol}&limit={limit}"
    data = _http_json(url)
    cache_path.write_text(json.dumps(data))
    return data


def fetch_klines(symbol: str, interval: str = "1h", n_batches: int = 6) -> list[list]:
    """Fetch up to n_batches × 1000 hourly klines (default = 6000h ≈ 250 days)."""
    cache_path = CACHE_DIR / f"h035_klines_{symbol}_{interval}_v2.json"
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < 3600:
        return json.loads(cache_path.read_text())
    all_klines: list[list] = []
    end_time: int | None = None
    for _ in range(n_batches):
        url = f"{BASE_URL}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit=1000"
        if end_time is not None:
            url += f"&endTime={end_time}"
        batch = _http_json(url)
        if not batch:
            break
        all_klines = batch + all_klines  # prepend older data
        end_time = int(batch[0][0]) - 1  # go further back
        time.sleep(0.2)
    cache_path.write_text(json.dumps(all_klines))
    return all_klines


def build_price_map(klines: list[list]) -> dict[int, float]:
    """Map open_time_ms → close_price."""
    return {int(k[0]): float(k[4]) for k in klines}


def compute_pnl(entry_price: float, exit_price: float, direction: str) -> float:
    if entry_price <= 0 or exit_price <= 0:
        return 0.0
    raw = (exit_price - entry_price) / entry_price
    return raw if direction == "LONG" else -raw


def _eff(scores_won: list[float], scores_lost: list[float]) -> float:
    if len(scores_won) < 2 or len(scores_lost) < 2:
        return 0.0
    n1, n2 = len(scores_won), len(scores_lost)
    m1 = sum(scores_won) / n1
    m2 = sum(scores_lost) / n2
    s1 = math.sqrt(sum((x - m1) ** 2 for x in scores_won) / (n1 - 1))
    s2 = math.sqrt(sum((x - m2) ** 2 for x in scores_lost) / (n2 - 1))
    pooled = math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2)) if (n1 + n2 > 2) else 0
    return (m1 - m2) / pooled if pooled > 0 else 0.0


def build_records(symbol: str, funding_rates: list[dict], price_map: dict[int, float]) -> list[dict]:
    """Build one record per settlement event."""
    records = []
    # Compute funding rate percentile threshold
    rates = [abs(float(f["fundingRate"])) for f in funding_rates]
    if not rates:
        return []
    threshold = sorted(rates)[int(len(rates) * (1 - FUNDING_TOPN_PCT))]

    for fr in funding_rates:
        settle_ms = int(fr["fundingTime"])
        rate = float(fr["fundingRate"])
        abs_rate = abs(rate)

        # Need price at T-4h (entry), T+0 (settlement), T+4h (exit rebound)
        pre_ms = settle_ms - PRE_SETTLE_H * 3600 * 1000
        post_ms = settle_ms + POST_SETTLE_H * 3600 * 1000

        # Find nearest kline prices (±30min tolerance)
        def get_price(target_ms: int) -> float | None:
            for delta in [0, 30 * 60000, -30 * 60000, 60 * 60000, -60 * 60000]:
                p = price_map.get(target_ms + delta)
                if p:
                    return p
            return None

        p_pre = get_price(pre_ms)
        p_settle = get_price(settle_ms)
        p_post = get_price(post_ms)

        if p_pre is None or p_settle is None or p_post is None:
            continue

        # SHORT leg: enter T-4h, exit T+0 (expecting dip at settlement)
        short_pnl = compute_pnl(p_pre, p_settle, "SHORT")
        short_net = short_pnl - COST_BPS / 10000

        # LONG leg: enter T+0, exit T+4h (expecting rebound)
        long_pnl = compute_pnl(p_settle, p_post, "LONG")
        long_net = long_pnl - COST_BPS / 10000

        settle_dt = datetime.fromtimestamp(settle_ms / 1000, tz=timezone.utc)

        records.append({
            "symbol": symbol,
            "settle_dt": settle_dt.isoformat(),
            "settle_ms": settle_ms,
            "funding_rate": rate,
            "abs_rate": abs_rate,
            "above_threshold": abs_rate >= threshold,
            "short_pnl": short_pnl,
            "short_net": short_net,
            "short_won": short_net > 0,
            "long_pnl": long_pnl,
            "long_net": long_net,
            "long_won": long_net > 0,
            "p_pre": p_pre,
            "p_settle": p_settle,
            "p_post": p_post,
        })
    return records


def run_walk_forward(records: list[dict], leg: str = "short") -> dict:
    if not records:
        return {"verdict": "NO_DATA", "windows": []}

    won_key = f"{leg}_won"
    net_key = f"{leg}_net"
    score_key = "abs_rate"

    records_sorted = sorted(records, key=lambda r: r["settle_ms"])
    if not records_sorted:
        return {"verdict": "NO_DATA", "windows": []}

    start_ms = records_sorted[0]["settle_ms"]
    end_ms = records_sorted[-1]["settle_ms"]
    window_ms = WINDOW_DAYS * 24 * 3600 * 1000

    windows = []
    t = start_ms
    while t + window_ms <= end_ms + 1:
        w_end = t + window_ms
        w_recs = [r for r in records_sorted if t <= r["settle_ms"] < w_end]
        qualified = [r for r in w_recs if r["above_threshold"]]
        if len(qualified) >= MIN_N:
            won = [r for r in qualified if r[won_key]]
            lost = [r for r in qualified if not r[won_key]]
            wr = len(won) / len(qualified)
            avg_net = sum(r[net_key] for r in qualified) / len(qualified)
            e = _eff([r[score_key] for r in won], [r[score_key] for r in lost])
            windows.append({
                "start": datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "n": len(qualified),
                "wr": wr,
                "avg_net": avg_net,
                "eff": e,
                "admissible": abs(e) >= EFF_FLOOR,
                "sign": "+" if e > 0 else "-",
            })
        t += window_ms

    if not windows:
        return {"verdict": "INSUFFICIENT_DATA", "windows": windows, "n_windows": 0}

    n_admissible = sum(1 for w in windows if w["admissible"])
    signs = [w["sign"] for w in windows if w["admissible"]]
    same_sign = len(set(signs)) <= 1 if signs else False

    if n_admissible >= MIN_WINDOWS and same_sign:
        verdict = "ADMISSIBLE"
    elif n_admissible > 0:
        verdict = "WEAK"
    else:
        verdict = "UNSTABLE"

    effs = [w["eff"] for w in windows]
    return {
        "verdict": verdict,
        "n_windows": len(windows),
        "n_admissible": n_admissible,
        "same_sign": same_sign,
        "effs": effs,
        "min_eff": min(effs) if effs else 0,
        "max_eff": max(effs) if effs else 0,
        "pooled_wr": sum(w["wr"] for w in windows) / len(windows) if windows else 0,
        "windows": windows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="H-035: 8h funding settlement pressure harness")
    parser.add_argument("--symbols", nargs="*", default=SYMBOLS)
    parser.add_argument("--min-n", type=int, default=MIN_N)
    parser.add_argument("--leg", choices=["short", "long", "both"], default="both")
    args = parser.parse_args()

    all_records: list[dict] = []
    print(f"\nH-035: Crypto 8h Funding-Settlement Pressure Timing")
    print(f"Symbols: {args.symbols}\n")

    for sym in args.symbols:
        print(f"  Fetching {sym}...", end="", flush=True)
        try:
            funding = fetch_funding_rates(sym)
            klines = fetch_klines(sym, "1h", 1000)
            price_map = build_price_map(klines)
            recs = build_records(sym, funding, price_map)
            print(f" {len(recs)} settlement records")
            all_records.extend(recs)
            time.sleep(0.3)
        except Exception as e:
            print(f" ERROR: {e}")

    print(f"\nTotal records: {len(all_records)} settlement events across {len(args.symbols)} symbols")

    results = {}
    for leg in (["short", "long"] if args.leg == "both" else [args.leg]):
        print(f"\n{'='*60}")
        print(f"LEG: {leg.upper()} (T-4h→T+0 for short, T+0→T+4h for long)")
        result = run_walk_forward(all_records, leg)
        results[leg] = result
        print(f"Verdict: {result['verdict']}")
        print(f"Windows scored: {result.get('n_windows', 0)}, admissible: {result.get('n_admissible', 0)}")
        print(f"Same sign: {result.get('same_sign', False)}")
        if result.get("effs"):
            print(f"Effs: {[round(e, 3) for e in result['effs']]}")
            print(f"Pooled WR: {result.get('pooled_wr', 0):.1%}")

    # Write report
    lines = [
        "# H-035: Crypto 8h Funding-Settlement Pressure Timing",
        f"\n**Tested:** 2026-05-19  ",
        f"**Symbols:** {args.symbols}  ",
        f"**Records:** {len(all_records)} settlement events  ",
        f"**Harness:** eff≥{EFF_FLOOR}, ≥{MIN_WINDOWS} windows, min_n={args.min_n}/window, net of {COST_BPS}bps\n",
    ]
    for leg, result in results.items():
        lines.append(f"\n## {leg.upper()} Leg Result\n")
        lines.append(f"- **Verdict:** {result['verdict']}")
        lines.append(f"- **Windows scored:** {result.get('n_windows', 0)}")
        lines.append(f"- **Admissible windows:** {result.get('n_admissible', 0)}")
        lines.append(f"- **Same sign:** {result.get('same_sign', False)}")
        lines.append(f"- **Effs:** {[round(e, 3) for e in result.get('effs', [])]}")
        lines.append(f"- **Pooled WR:** {result.get('pooled_wr', 0):.1%}\n")
        if result.get("windows"):
            lines.append("| Window | N | WR | Avg Net | Eff | Admissible |")
            lines.append("|--------|---|-----|---------|-----|------------|")
            for w in result["windows"]:
                lines.append(
                    f"| {w['start']} | {w['n']} | {w['wr']:.1%} | "
                    f"{w['avg_net']*100:.2f}% | {w['eff']:.3f} | {'✅' if w['admissible'] else '❌'} |"
                )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {OUTPUT_PATH}")

    # Update hypothesis registry
    reg_path = REPO_ROOT / "reports" / "hypothesis_registry.json"
    if reg_path.exists():
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        for h in reg.get("hypotheses", []):
            if h.get("id") == "H-035":
                short_r = results.get("short", {})
                long_r = results.get("long", {})
                both_verdict = "ADMISSIBLE" if "ADMISSIBLE" in [short_r.get("verdict"), long_r.get("verdict")] else \
                               "WEAK" if "WEAK" in [short_r.get("verdict"), long_r.get("verdict")] else \
                               "INSUFFICIENT_DATA" if all(r.get("verdict") == "INSUFFICIENT_DATA" for r in [short_r, long_r]) else \
                               "TESTED_KILL"
                h["status"] = "TESTED_KILL" if both_verdict == "TESTED_KILL" else \
                              ("NEAR_ADMISSIBLE" if both_verdict == "WEAK" else \
                               ("ADMISSIBLE" if both_verdict == "ADMISSIBLE" else "UNTESTED_DATA_GAP"))
                h["result"] = {
                    "tested_at": datetime.now(timezone.utc).isoformat(),
                    "n_records": len(all_records),
                    "short_verdict": short_r.get("verdict"),
                    "short_n_admissible": short_r.get("n_admissible", 0),
                    "short_effs": [round(e, 3) for e in short_r.get("effs", [])],
                    "long_verdict": long_r.get("verdict"),
                    "long_n_admissible": long_r.get("n_admissible", 0),
                    "long_effs": [round(e, 3) for e in long_r.get("effs", [])],
                }
                break
        reg_path.write_text(json.dumps(reg, indent=2), encoding="utf-8")
        print("Hypothesis registry updated.")


if __name__ == "__main__":
    main()
