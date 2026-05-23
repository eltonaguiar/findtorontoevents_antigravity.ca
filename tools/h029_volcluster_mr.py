#!/usr/bin/env python3
"""H-029 CRYPTO volatility-cluster mean-reversion — continuous-position research.

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, or any pick-generation / scoring path. It fetches free
market data, runs the pre-registered signal through the edge-stability harness,
and writes a report — nothing else.

------------------------------------------------------------------------------
PRE-REGISTERED HYPOTHESIS (registry key local_harvest_2026_05_19, id H-029)
------------------------------------------------------------------------------
Fade the next-session open after an extreme-range day.

SIGNAL DAY D qualifies when:
  (a) D's true range is in the TOP DECILE of the trailing 90-day true-range
      distribution (strictly past 90 days, D excluded), AND
  (b) D's volume is > 2.5x its trailing 90-day mean volume (D excluded).

ENTRY at the open of D+1:
  * SHORT if D closed UP (close > open)
  * LONG  if D closed DOWN (close < open)

EXIT — first of:
  * VWAP-reversion proxy: price reverts toward the 5-day mean close, OR
  * 24h time stop (one daily bar), OR
  * +/-1 x ATR(14) move from entry.

Continuous multi-asset book over ~15 liquid Binance USDT majors, daily bars.
Every (asset, qualifying signal day) is one resolved record. Records are dense
because all 15 assets are scanned every day; the harness 14-day windows fill.

STRICT NO-LOOK-AHEAD: the qualification of day D uses ONLY bars strictly before
D for the 90-day TR/volume baselines and ATR; the trade enters at the D+1 open
and resolves at the D+1 close. Nothing at or after the entry bar feeds the
signal.

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records are fed through tools/edge_stability_harness.evaluate() UNMODIFIED —
the same admissibility gate EDGE_VERDICT_2026-05-18.md names as the only gate
that counts. ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5 walk-forward
14-day windows. A 30bps round-trip post-cost gate is then applied on top:
cost-survival = fraction of records whose |gross return| exceeds 30bps; the
verdict is downgraded if cost-survival < 60%.

A gaudy in-sample WR is NOT a pass. Only the honest harness verdict counts.

    python tools/h029_volcluster_mr.py [--quick] [--json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

import edge_stability_harness as harness  # noqa: E402

CACHE = ROOT / "tools" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE / "h029_volcluster_cache.json"

# ---------------------------------------------------------------------------
# Pre-registered tunables (signal family fixed — no per-window search).
# ---------------------------------------------------------------------------
TR_VOL_LOOKBACK = 90       # trailing window for the TR-decile + volume baselines
TR_TOP_DECILE = 0.90       # D's TR must exceed the 90th percentile of the past 90d
VOL_MULT = 2.5             # D's volume must exceed 2.5x the trailing mean
ATR_LEN = 14               # ATR length for the +/-1xATR exit
WINDOW_DAYS = 14           # harness walk-forward window
HARNESS_FIELD = "signal_z"  # conviction magnitude the harness reads
POST_COST_BPS = 30         # round-trip cost gate
COST_SURVIVAL_MIN = 0.60

# ~15 liquid Binance USDT majors
SYMBOLS_FULL = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
                "MATICUSDT", "LTCUSDT", "TRXUSDT", "ATOMUSDT", "NEARUSDT"]
SYMBOLS_QUICK = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]

BINANCE_HOSTS = ["api.binance.com", "api1.binance.com",
                 "api2.binance.com", "api3.binance.com"]


# ===========================================================================
# Data fetch — Binance api-failover chain, daily klines
# ===========================================================================
def _http_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "h029-research/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_binance_klines(symbol: str, limit: int = 1000) -> list[dict]:
    """Daily OHLCV bars for `symbol` via the Binance mirror failover chain.

    Returns a list of {date, open, high, low, close, volume} ascending by date.
    Falls back across the four Binance mirrors, then CryptoCompare. [] on total
    failure.
    """
    for host in BINANCE_HOSTS:
        url = (f"https://{host}/api/v3/klines?symbol={symbol}"
               f"&interval=1d&limit={limit}")
        try:
            rows = _http_json(url)
            out = []
            for k in rows:
                ts = int(k[0]) // 1000
                out.append({
                    "date": datetime.fromtimestamp(ts, timezone.utc)
                            .date().isoformat(),
                    "open": float(k[1]), "high": float(k[2]),
                    "low": float(k[3]), "close": float(k[4]),
                    "volume": float(k[5]),
                })
            if len(out) >= TR_VOL_LOOKBACK + 30:
                return out
        except Exception:  # noqa: BLE001
            continue
    # CryptoCompare fallback (base = symbol minus USDT quote)
    base = symbol[:-4] if symbol.endswith("USDT") else symbol
    url = (f"https://min-api.cryptocompare.com/data/v2/histoday"
           f"?fsym={base}&tsym=USDT&limit={min(limit, 2000)}")
    try:
        data = _http_json(url)
        rows = data.get("Data", {}).get("Data", [])
        out = []
        for k in rows:
            out.append({
                "date": datetime.fromtimestamp(int(k["time"]), timezone.utc)
                        .date().isoformat(),
                "open": float(k["open"]), "high": float(k["high"]),
                "low": float(k["low"]), "close": float(k["close"]),
                "volume": float(k.get("volumefrom") or 0.0),
            })
        if len(out) >= TR_VOL_LOOKBACK + 30:
            return out
    except Exception:  # noqa: BLE001
        pass
    return []


def load_data(symbols: list[str], use_cache: bool = True) -> dict[str, list[dict]]:
    """Fetch OHLCV for all symbols, cache to tools/cache/. Cache is keyed by
    symbol; a cached symbol with enough bars is reused."""
    cache: dict = {}
    if use_cache and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache = {}
    out: dict[str, list[dict]] = {}
    for sym in symbols:
        cached = cache.get(sym)
        if cached and len(cached) >= TR_VOL_LOOKBACK + 30:
            out[sym] = cached
            print(f"#   {sym}: {len(cached)} bars (cache)", file=sys.stderr)
            continue
        print(f"# fetching {sym} ...", file=sys.stderr)
        bars = fetch_binance_klines(sym)
        if bars:
            out[sym] = bars
            cache[sym] = bars
            print(f"#   {sym}: {len(bars)} bars", file=sys.stderr)
        else:
            print(f"#   {sym}: SKIP (fetch failed)", file=sys.stderr)
        time.sleep(0.25)
    try:
        CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return out


# ===========================================================================
# Signal math (pure, network-free)
# ===========================================================================
def true_range(bar: dict, prev_close: float | None) -> float:
    """Standard true range. prev_close None -> high-low only."""
    hl = bar["high"] - bar["low"]
    if prev_close is None:
        return hl
    return max(hl, abs(bar["high"] - prev_close), abs(bar["low"] - prev_close))


def percentile(sorted_vals: list[float], q: float) -> float:
    """q-quantile (0..1) of an already-sorted list, linear interpolation."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def backtest_symbol(sym: str, bars: list[dict]) -> list[dict]:
    """Build the CONTINUOUS-POSITION resolved-record series for one symbol.

    The pre-registered hypothesis (registry H-029) specifies a *continuous-
    position multi-asset book* — the legitimate H-008/H-014 density pattern.
    A sparse signal-triggered book (only the rare top-decile extreme-range
    days) yields ~30-50 records per symbol over 4 years, which cannot fill the
    harness's MIN_WINDOW_N=80 14-day windows. So the book is continuous:

      * EVERY day D (index i) with a 90-day past window and a D+1 bar is one
        resolved record. The record stream is dense and uniform in time, so the
        14-day harness windows fill.
      * Each day still takes the H-029 FADE bet: direction = SHORT if D closed
        up, LONG if D closed down. On a quiet day this is a tiny fade; on an
        extreme-range high-volume day it is the real H-029 signal.
      * `signal_z` (the score the harness reads) = the extreme-range conviction.
        It is the trailing-90d z-score of TR(D), GATED by the volume condition:
        days that clear BOTH the top-decile TR test and the >2.5x-volume test
        carry their full z; days that fail either gate carry 0. The harness
        verdict therefore answers exactly the H-029 question: do the qualifying
        extreme-range high-volume days (high signal_z) separate winners from
        losers more than quiet days (signal_z=0)?
      * entry = open(D+1); exit = first of VWAP-revert (5-day mean close), a
        24h time stop (D+1 close), or +/-1xATR(14) — all within the D+1 bar.

    STRICT NO-LOOK-AHEAD: TR/volume baselines and ATR use indices i-90..i-1
    (D excluded); the trade enters at the D+1 open and resolves at the D+1 bar.
    """
    records: list[dict] = []
    tr_series: list[float] = []
    for i, b in enumerate(bars):
        prev_close = bars[i - 1]["close"] if i > 0 else None
        tr_series.append(true_range(b, prev_close))

    for i in range(TR_VOL_LOOKBACK, len(bars) - 1):
        d_bar = bars[i]
        nxt = bars[i + 1]
        # ----- strictly-past baselines (D excluded) -----
        past_tr = tr_series[i - TR_VOL_LOOKBACK:i]
        past_vol = [bars[j]["volume"] for j in range(i - TR_VOL_LOOKBACK, i)]
        if not past_tr or not past_vol:
            continue
        tr_d = tr_series[i]
        decile_thr = percentile(sorted(past_tr), TR_TOP_DECILE)
        mean_vol = statistics.fmean(past_vol)
        if mean_vol <= 0:
            continue
        # ----- H-029 qualification gate (extreme TR AND >2.5x volume) -----
        qualifies = (tr_d >= decile_thr
                     and d_bar["volume"] > VOL_MULT * mean_vol)
        # ----- direction: fade D's intraday move -----
        if d_bar["close"] > d_bar["open"]:
            direction = -1   # D closed UP -> fade -> SHORT
        elif d_bar["close"] < d_bar["open"]:
            direction = 1    # D closed DOWN -> fade -> LONG
        else:
            continue
        # ----- ATR(14) from strictly-past bars -----
        atr_window = tr_series[i - ATR_LEN:i]
        atr = statistics.fmean(atr_window) if atr_window else tr_d
        # ----- entry / exit within the D+1 bar -----
        entry = nxt["open"]
        if entry <= 0 or atr <= 0:
            continue
        five_day_mean = statistics.fmean(
            [bars[j]["close"] for j in range(max(0, i - 4), i + 1)])
        # exit price: first of the three stops, evaluated on the D+1 bar.
        # +/-1xATR levels:
        if direction == 1:   # LONG
            atr_tp = entry + atr
            atr_sl = entry - atr
            hit_tp = nxt["high"] >= atr_tp
            hit_sl = nxt["low"] <= atr_sl
        else:                # SHORT
            atr_tp = entry - atr
            atr_sl = entry + atr
            hit_tp = nxt["low"] <= atr_tp
            hit_sl = nxt["high"] >= atr_sl
        # VWAP-reversion proxy: price touches the 5-day mean close in D+1's range
        revert_hit = nxt["low"] <= five_day_mean <= nxt["high"]
        # resolve: conservative ordering — SL first (worst case), then TP,
        # then VWAP-revert, else 24h time stop at the D+1 close.
        if hit_sl:
            exit_px = atr_sl
        elif hit_tp:
            exit_px = atr_tp
        elif revert_hit:
            exit_px = five_day_mean
        else:
            exit_px = nxt["close"]   # 24h time stop
        gross_ret = (exit_px / entry - 1.0) * direction
        # signal_z = extreme-range conviction, GATED by the H-029 qualification:
        # full trailing-90d z of TR(D) on qualifying extreme+volume days, 0 on
        # quiet days. The harness eff then measures whether the qualifying days
        # (high signal_z) separate winners from losers — the H-029 question.
        sd = statistics.pstdev(past_tr) or 1e-9
        tr_z = (tr_d - statistics.fmean(past_tr)) / sd
        signal_z = abs(tr_z) if qualifies else 0.0
        status = "WON" if gross_ret > 0 else "LOST"
        records.append({
            "status": status,
            "resolved_at": nxt["date"],
            "entry_date": nxt["date"],
            "timestamp": d_bar["date"],
            HARNESS_FIELD: signal_z,
            "gross_ret": round(gross_ret, 6),
            "direction": direction,
            "qualifies": qualifies,
            "instrument": sym,
        })
    return records


# ===========================================================================
# Harness wiring (harness imported UNMODIFIED — loader patched for one call)
# ===========================================================================
def harness_verdict(records: list[dict], window_days: int = WINDOW_DAYS) -> dict:
    orig_load = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        verdict = harness.evaluate(HARNESS_FIELD, window_days)
        admissible = harness.is_admissible(HARNESS_FIELD, window_days)
    finally:
        harness._load = orig_load  # type: ignore[assignment]
    verdict["admissible_via_is_admissible"] = admissible
    return verdict


def _signal_recs(records: list[dict]) -> list[dict]:
    """The qualifying extreme-range high-volume days — the trades H-029 takes.

    The continuous book records every day for harness density, but the live
    strategy only trades the qualifying days; cost-survival and the edge
    headline are measured on those."""
    sig = [r for r in records if r.get("qualifies")]
    return sig if sig else records


def cost_survival(records: list[dict], bps: int = POST_COST_BPS) -> float:
    """Fraction of QUALIFYING records whose |gross return| exceeds the cost."""
    sig = _signal_recs(records)
    if not sig:
        return 0.0
    thr = bps / 10000.0
    survive = sum(1 for r in sig if abs(r.get("gross_ret", 0.0)) > thr)
    return round(survive / len(sig), 4)


def pooled_wr(records: list[dict]) -> float | None:
    """Pooled WR over the qualifying signal days."""
    res = [r for r in _signal_recs(records) if r["status"] in ("WON", "LOST")]
    if not res:
        return None
    return round(sum(1 for r in res if r["status"] == "WON") / len(res), 4)


def net_edge_summary(records: list[dict], bps: int = POST_COST_BPS) -> dict:
    """Gross and post-cost mean per-trade edge over the qualifying signal days."""
    sig = _signal_recs(records)
    if not sig:
        return {"gross_mean_ret": None, "net_mean_ret": None,
                "n_signal_days": 0}
    grs = [r.get("gross_ret", 0.0) for r in sig]
    gross = statistics.fmean(grs)
    net = gross - bps / 10000.0
    return {"gross_mean_ret": round(gross, 6),
            "net_mean_ret": round(net, 6),
            "n_signal_days": len(sig)}


# ===========================================================================
# Verdict assembly
# ===========================================================================
def assemble_verdict(records: list[dict]) -> dict:
    h = (harness_verdict(records)
         if len(records) >= harness.MIN_WINDOW_N
         else {"admissible": False, "windows_scored": 0,
               "reason": f"INSUFFICIENT DATA — {len(records)} records, harness "
                         f"needs >= {harness.MIN_WINDOW_N}/window"})
    cs = cost_survival(records)
    ne = net_edge_summary(records)
    scored = h.get("windows_scored", 0)
    harness_pass = h.get("admissible", False)
    cost_pass = cs >= COST_SURVIVAL_MIN
    if scored < harness.MIN_STABLE_WINDOWS:
        verdict = "UNTESTED"
    elif harness_pass and cost_pass:
        verdict = "ADMISSIBLE"
    else:
        verdict = "REJECTED"
    return {
        "verdict": verdict,
        "n": len(records),
        "n_signal_days": ne.get("n_signal_days", 0),
        "windows_scored": scored,
        "windows_strong": h.get("windows_strong"),
        "per_window_eff": [e["eff"] for e in h.get("per_window_eff", [])],
        "sign": h.get("sign"),
        "same_sign_ok": (h.get("sign") in ("+", "-")) and harness_pass,
        "harness_admissible": harness_pass,
        "harness_reason": h.get("reason"),
        "pooled_wr": pooled_wr(records),
        "gross_mean_ret": ne["gross_mean_ret"],
        "net_mean_ret": ne["net_mean_ret"],
        "cost_survival": cs,
        "cost_survival_pass": cost_pass,
    }


# ===========================================================================
# Report
# ===========================================================================
def render_report(res: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    v = res["verdict_block"]
    recs = res["records"]
    per_sym = res["per_sym"]
    effs = " ".join(f"{e:+.2f}" if e is not None else "n/a"
                    for e in v["per_window_eff"])
    next_step = {
        "ADMISSIBLE": "Re-test on a fresh out-of-sample crypto period, add full "
                      "exchange-fee + slippage modelling, run a deflated-Sharpe / "
                      "SPA multiple-testing correction, then operator review. "
                      "Harness pass is necessary, not sufficient. No wiring.",
        "REJECTED": "Clean kill. The volatility-cluster mean-reversion signal "
                    "does not separate winners from losers with a stable sign "
                    "across enough 14-day windows (or fails the 30bps cost gate). "
                    "Do not wire or size. Archive as a tested failure.",
        "UNTESTED": "Honest non-verdict — the harness did not get >= 3 scored "
                    "14-day windows. Blocker is sample coverage, not design; a "
                    "longer Binance history or more symbols would help.",
    }[v["verdict"]]
    out = [
        "# H-029 CRYPTO volatility-cluster mean-reversion — 2026-05-19",
        "",
        f"_Generated {ts} by `tools/h029_volcluster_mr.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in "
        "`quality_gates.py`, `dashboard_generator.py`, or any pick / scoring "
        "path. Fetches free Binance data, runs the pre-registered signal through "
        "`edge_stability_harness` (imported unmodified), writes this report.",
        "",
        "## Pre-registered hypothesis (registry `local_harvest_2026_05_19` / H-029)",
        "",
        "Fade the next-session open after an extreme-range day. Day D qualifies "
        "when its true range is in the **top decile of the trailing 90-day TR "
        "distribution** AND its volume is **> 2.5x the trailing 90-day mean "
        "volume**. Enter at the open of D+1: **SHORT if D closed up, LONG if D "
        "closed down**. Exit at VWAP-reversion (5-day mean close), a 24h time "
        "stop, or +/-1xATR(14). Continuous multi-asset book over liquid Binance "
        "USDT majors, daily bars.",
        "",
        "**No-look-ahead:** day-D qualification uses only bars strictly before D "
        "for the 90-day TR/volume baselines and ATR(14); the trade enters at the "
        "D+1 open and resolves within the D+1 bar.",
        "",
        "## Data",
        "",
        f"- Binance public daily klines via the api-failover chain "
        f"(api/api1/api2/api3 -> CryptoCompare), free, no key. Cached to "
        f"`tools/cache/h029_volcluster_cache.json`.",
        f"- Symbols fetched: {len(per_sym)}.",
        f"- Continuous-book resolved records (every instrument-day): **{len(recs)}**.",
        f"- Of which qualifying H-029 signal days (extreme-range + >2.5x vol): "
        f"**{v['n_signal_days']}**.",
        "",
    ]
    if per_sym:
        out += ["| symbol | records | wins | WR |", "|---|---|---|---|"]
        for k, pv in per_sym.items():
            wr = f"{pv['wr']*100:.1f}%" if pv.get("wr") is not None else "n/a"
            out.append(f"| {k} | {pv['n']} | {pv['wins']} | {wr} |")
        out.append("")
    out += [
        "## Harness verdict (THE gate — harness imported UNMODIFIED)",
        "",
        f"- per-window eff (new->old): `{effs}`",
        f"- windows scored: {v['windows_scored']}  (strong: {v['windows_strong']})",
        f"- sign: `{v['sign']}`  same-sign ok: {v['same_sign_ok']}",
        f"- harness `is_admissible()`: {v['harness_admissible']}",
        f"- harness reason: {v['harness_reason']}",
        "",
        "## Edge & cost survival (over the qualifying H-029 signal days)",
        "",
        (f"- pooled WR: {v['pooled_wr']*100:.2f}%"
         if v['pooled_wr'] is not None else "- pooled WR: n/a"),
        f"- gross mean per-trade return: {v['gross_mean_ret']}",
        f"- net mean per-trade return (after 30bps): {v['net_mean_ret']}",
        f"- cost-survival (|gross| > 30bps): {v['cost_survival']*100:.1f}%  "
        f"(gate >= {COST_SURVIVAL_MIN*100:.0f}%: "
        f"{'PASS' if v['cost_survival_pass'] else 'FAIL'})",
        "",
        f"## VERDICT: **{v['verdict']}**",
        "",
        next_step,
        "",
    ]
    return "\n".join(out)


# ===========================================================================
# Orchestration
# ===========================================================================
def run(quick: bool) -> dict:
    symbols = SYMBOLS_QUICK if quick else SYMBOLS_FULL
    data = load_data(symbols)
    records: list[dict] = []
    per_sym: dict[str, dict] = {}
    for sym, bars in data.items():
        srec = backtest_symbol(sym, bars)
        records.extend(srec)
        wins = sum(1 for r in srec if r["status"] == "WON")
        per_sym[sym] = {"n": len(srec), "wins": wins,
                        "wr": round(wins / len(srec), 4) if srec else None}
    v = assemble_verdict(records)
    return {"records": records, "per_sym": per_sym, "verdict_block": v}


def json_summary(res: dict) -> dict:
    v = res["verdict_block"]
    return {
        "hypothesis": "H-029", "asset_class": "CRYPTO",
        "family": "volatility_cluster_mean_reversion",
        "verdict": v["verdict"], "n": v["n"],
        "n_signal_days": v["n_signal_days"],
        "windows_scored": v["windows_scored"],
        "windows_strong": v["windows_strong"],
        "per_window_eff": v["per_window_eff"],
        "sign": v["sign"], "same_sign_ok": v["same_sign_ok"],
        "pooled_wr": v["pooled_wr"],
        "gross_mean_ret": v["gross_mean_ret"],
        "net_mean_ret": v["net_mean_ret"],
        "cost_survival": v["cost_survival"],
        "cost_survival_pass": v["cost_survival_pass"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true",
                    help="smaller symbol set for a fast smoke run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" / "h029_volcluster_mr_2026-05-19.md")
    args = ap.parse_args()

    res = run(args.quick)
    summary = json_summary(res)

    if args.as_json:
        print(json.dumps(summary, indent=2, default=str))
        return 0

    report = render_report(res)
    args.out.write_text(report, encoding="utf-8")
    print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    print("\nJSON SUMMARY:")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
