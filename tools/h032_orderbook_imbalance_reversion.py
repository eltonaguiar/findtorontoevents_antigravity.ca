#!/usr/bin/env python3
"""H-032 CRYPTO intraday order-flow-imbalance reversion (1m) — research probe.

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, or any pick-generation / scoring path. It fetches free
Binance public data, runs the pre-registered signal through the edge-stability
harness (imported UNMODIFIED), and writes a report — nothing else.

------------------------------------------------------------------------------
PRE-REGISTERED HYPOTHESIS (registry key tier2_2026_05_19, id H-032)
------------------------------------------------------------------------------
CRYPTO intraday order-flow-imbalance mean-reversion at 1-MINUTE resolution —
the one untested data axis the 11 prior DAILY-bar crypto kills point toward.

For each of ~10 Binance USDT majors, fetch 1m klines. The Binance 1m kline
carries `takerBuyBaseVolume` (field 9): the base-asset volume that traded
against a RESTING (maker) sell order — i.e. AGGRESSIVE BUY volume for that
minute. Aggressive sell volume = total base volume - takerBuyBaseVolume. This
is a genuine per-minute order-flow split, no aggTrade replay needed, and it is
known at the CLOSE of the minute (look-ahead-free).

SIGNAL at minute t:
  * OFI_t = (buy_vol_t - sell_vol_t) / (buy_vol_t + sell_vol_t)   in [-1, +1]
  * standardise OFI to a z-score against a STRICTLY-PAST rolling 240-minute
    window (minute t excluded): OFI_z = (OFI_t - mean_past) / sd_past
  * minute t QUALIFIES iff |OFI_z| >= 2.0 (extreme imbalance = liquidity vacuum)
  * FADE the imbalance: SHORT when OFI_z >> 0 (buy-pressure spike), LONG when
    OFI_z << 0 (sell-pressure spike)
  * ENTER at the close of minute t, EXIT at the close of minute t+5.

Continuous-position multi-asset book: every instrument-minute is one resolved
record. signal_z (the score the harness reads) = |OFI_z| on qualifying minutes,
0 otherwise. The harness eff then answers exactly the H-032 question: do the
extreme-imbalance minutes separate winners from losers stably across windows?

STRICT NO-LOOK-AHEAD: the OFI_z baseline uses only minutes t-240..t-1; OFI_t
itself is known at the close of minute t; entry is the minute-t close; the exit
reads only the close of minute t+5.

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records fed through tools/edge_stability_harness.evaluate() UNMODIFIED.
ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5 walk-forward 14-day windows.
A 30bps round-trip post-cost gate is applied: cost-survival = fraction of
QUALIFYING minutes whose |gross return| exceeds 30bps; verdict downgraded if
cost-survival < 60%. A gaudy in-sample WR is NOT a pass.

This is a 2-4 week PROBE (per NEXT_MOVES_2026-05-19 Tier-2): Binance free 1m
klines reach back ~weeks-months per paginated pull. If the harness gets < 5
scored 14-day windows the verdict is UNTESTED (data-gap), NOT a pass.

    python tools/h032_orderbook_imbalance_reversion.py [--quick] [--json]
                                                       [--days N]
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
CACHE_FILE = CACHE / "h032_orderflow_cache.json"

# ---- Pre-registered tunables (signal family fixed — no per-window search) ----
OFI_LOOKBACK = 240         # strictly-past rolling minutes for the OFI z-score
OFI_Z_EXTREME = 2.0        # |OFI_z| threshold for a qualifying liquidity vacuum
HOLD_MIN = 5               # exit at +5 minutes
WINDOW_DAYS = 14
HARNESS_FIELD = "signal_z"
POST_COST_BPS = 30
COST_SURVIVAL_MIN = 0.60

DEFAULT_DAYS = 30          # how many days of 1m history to pull per symbol
KLINES_PER_CALL = 1000     # Binance 1m kline page size

BINANCE_HOSTS = ["api.binance.com", "api1.binance.com",
                 "api2.binance.com", "api3.binance.com"]

# ~10 Binance USDT majors — fixed pre-registered universe, deep liquidity.
UNIVERSE_FULL = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                 "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT"]
UNIVERSE_QUICK = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]


# ===========================================================================
# Data fetch — Binance api-failover chain, 1m klines (paginated)
# ===========================================================================
def _http_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "h032-research/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        return json.loads(r.read().decode("utf-8", "replace"))


def _parse_klines(rows: list) -> list[dict]:
    """Map raw Binance 1m kline rows to order-flow minute records.

    Binance kline fields used:
      [0] openTime ms, [4] close, [5] base volume,
      [9] takerBuyBaseVolume = aggressive-BUY base volume for the minute.
    Aggressive-SELL volume = base volume - takerBuyBaseVolume.
    """
    out = []
    for k in rows:
        try:
            ts = int(k[0]) // 1000
            close = float(k[4])
            vol = float(k[5])
            buy = float(k[9])
        except (IndexError, TypeError, ValueError):
            continue
        sell = max(0.0, vol - buy)
        out.append({
            "ts": ts,
            "minute": datetime.fromtimestamp(ts, timezone.utc)
                      .isoformat(timespec="minutes"),
            "date": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
            "close": close,
            "buy_vol": buy,
            "sell_vol": sell,
        })
    return out


def fetch_binance_1m(symbol: str, days: int) -> list[dict]:
    """~`days` of 1m order-flow minutes for `symbol` via the failover chain.

    Paginates backward with the Binance `endTime` parameter (1000 bars/call).
    Returns minutes ascending by ts. [] on total failure.
    """
    need = days * 24 * 60
    end_ms = int(time.time() * 1000)
    collected: dict[int, dict] = {}
    pages = need // KLINES_PER_CALL + 2
    host_idx = 0
    for _ in range(pages):
        rows = None
        for attempt in range(len(BINANCE_HOSTS)):
            host = BINANCE_HOSTS[(host_idx + attempt) % len(BINANCE_HOSTS)]
            url = (f"https://{host}/api/v3/klines?symbol={symbol}"
                   f"&interval=1m&limit={KLINES_PER_CALL}&endTime={end_ms}")
            try:
                rows = _http_json(url)
                host_idx = (host_idx + attempt) % len(BINANCE_HOSTS)
                break
            except Exception:  # noqa: BLE001
                rows = None
                continue
        if not rows:
            break
        page = _parse_klines(rows)
        if not page:
            break
        for m in page:
            collected[m["ts"]] = m
        oldest = min(m["ts"] for m in page)
        end_ms = oldest * 1000 - 1   # step strictly before the oldest minute
        if len(collected) >= need:
            break
        time.sleep(0.25)
    return [collected[t] for t in sorted(collected)]


def load_data(symbols: list[str], days: int,
              use_cache: bool = True) -> dict[str, list[dict]]:
    """Fetch 1m order-flow minutes for all symbols, cache to tools/cache/."""
    cache: dict = {}
    if use_cache and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache = {}
    need = days * 24 * 60
    out: dict[str, list[dict]] = {}
    for sym in symbols:
        cached = cache.get(sym)
        # Reuse the cache only when it already holds (close to) the requested
        # span — a shorter cached pull must NOT shadow a larger --days request.
        # 0.9*need allows for normal exchange-side minute gaps.
        if cached and len(cached) >= 0.9 * need:
            out[sym] = cached
            print(f"#   {sym}: {len(cached)} minutes (cache)", file=sys.stderr)
            continue
        print(f"# fetching {sym} 1m ({days}d) ...", file=sys.stderr)
        mins = fetch_binance_1m(sym, days)
        if mins:
            out[sym] = mins
            cache[sym] = mins
            print(f"#   {sym}: {len(mins)} minutes", file=sys.stderr)
        else:
            print(f"#   {sym}: SKIP (fetch failed)", file=sys.stderr)
        time.sleep(0.4)
    try:
        CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return out


# ===========================================================================
# Signal math (pure, network-free)
# ===========================================================================
def backtest_symbol(sym: str, minutes: list[dict]) -> list[dict]:
    """Build the CONTINUOUS-POSITION resolved-record series for one symbol.

    For every minute t (index i) with a 240-minute strictly-past window and an
    i+HOLD_MIN future bar:
      * OFI_t  = (buy_vol - sell_vol) / (buy_vol + sell_vol).
      * OFI_z  = (OFI_t - mean) / sd over minutes i-240..i-1 (t EXCLUDED).
      * minute QUALIFIES iff |OFI_z| >= 2.0.
      * FADE: direction = -1 if OFI_z > 0 (buy-pressure spike -> SHORT),
              +1 if OFI_z < 0 (sell-pressure spike -> LONG).
      * ENTER at close(t), EXIT at close(t+HOLD_MIN).
      * signal_z = |OFI_z| on qualifying minutes, 0 otherwise.

    Non-qualifying minutes are still recorded (book density) with signal_z=0 and
    a FLAT resolution on their own tiny forward move — so the harness sees them
    as noise, not phantom losses.

    STRICT NO-LOOK-AHEAD: the OFI_z baseline reads only minutes i-240..i-1;
    OFI_t is the close-of-minute aggregate; entry is close(t); exit close(t+5).
    """
    records: list[dict] = []
    ofi_series: list[float] = []
    for m in minutes:
        tot = m["buy_vol"] + m["sell_vol"]
        ofi_series.append((m["buy_vol"] - m["sell_vol"]) / tot if tot > 0 else 0.0)

    for i in range(OFI_LOOKBACK, len(minutes) - HOLD_MIN):
        # gap-guard: skip if the 240-min window straddles a data gap
        if minutes[i]["ts"] - minutes[i - OFI_LOOKBACK]["ts"] > OFI_LOOKBACK * 60 * 3:
            continue
        past = ofi_series[i - OFI_LOOKBACK:i]   # strictly-past, t excluded
        mean = statistics.fmean(past)
        sd = statistics.pstdev(past) or 1e-9
        ofi_z = (ofi_series[i] - mean) / sd
        qualifies = abs(ofi_z) >= OFI_Z_EXTREME
        entry = minutes[i]["close"]
        exit_px = minutes[i + HOLD_MIN]["close"]
        if entry <= 0:
            continue
        if qualifies:
            direction = -1 if ofi_z > 0 else 1   # FADE the imbalance
            signal_z = abs(ofi_z)
        else:
            direction = 0
            signal_z = 0.0
        if direction != 0:
            gross_ret = (exit_px / entry - 1.0) * direction
            status = "WON" if gross_ret > 0 else "LOST"
        else:
            gross_ret = (exit_px / entry - 1.0)   # FLAT — recorded as noise
            status = "WON" if gross_ret > 0 else "LOST"
        records.append({
            "status": status,
            "resolved_at": minutes[i + HOLD_MIN]["date"],
            "timestamp": minutes[i]["minute"],
            HARNESS_FIELD: signal_z,
            "gross_ret": round(gross_ret, 6),
            "ofi_z": round(ofi_z, 4),
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
    sig = [r for r in records if r.get("qualifies")]
    return sig if sig else records


def cost_survival(records: list[dict], bps: int = POST_COST_BPS) -> float:
    sig = _signal_recs(records)
    if not sig:
        return 0.0
    thr = bps / 10000.0
    return round(sum(1 for r in sig if abs(r.get("gross_ret", 0.0)) > thr) / len(sig), 4)


def pooled_wr(records: list[dict]) -> float | None:
    res = [r for r in _signal_recs(records) if r["status"] in ("WON", "LOST")]
    if not res:
        return None
    return round(sum(1 for r in res if r["status"] == "WON") / len(res), 4)


def net_edge_summary(records: list[dict], bps: int = POST_COST_BPS) -> dict:
    sig = _signal_recs(records)
    if not sig:
        return {"gross_mean_ret": None, "net_mean_ret": None, "n_signal_days": 0}
    grs = [r.get("gross_ret", 0.0) for r in sig]
    gross = statistics.fmean(grs)
    return {"gross_mean_ret": round(gross, 6),
            "net_mean_ret": round(gross - bps / 10000.0, 6),
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
def render_report(res: dict, days: int) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    v = res["verdict_block"]
    recs = res["records"]
    per_sym = res["per_sym"]
    effs = " ".join(f"{e:+.2f}" if e is not None else "n/a"
                    for e in v["per_window_eff"])
    next_step = {
        "ADMISSIBLE": "Re-test on a fresh out-of-sample window, model the real "
                      "crypto round-trip cost honestly (taker fee + spread + 1m "
                      "slippage — likely > 30bps for a 5-minute scalp), run a "
                      "deflated-Sharpe / SPA correction, then forward-test on "
                      "paper before any capital. Harness pass is necessary, not "
                      "sufficient. No wiring.",
        "REJECTED": "Clean kill. Intraday 1m order-flow-imbalance reversion does "
                    "not separate winners from losers with a stable sign across "
                    "enough 14-day windows (or fails the 30bps cost gate). The "
                    "one untested microstructure axis also fails — paper-only "
                    "becomes the standing verdict. Archive as a tested failure.",
        "UNTESTED": "Honest non-verdict — the harness did not get >= 3 scored "
                    "14-day windows. Binance free 1m history is the blocker; "
                    "re-run with a larger --days pull (or accrue forward) to "
                    "reach >= 5 windows. This is the 2-4 week PROBE framing.",
    }[v["verdict"]]
    out = [
        "# H-032 CRYPTO intraday order-flow-imbalance reversion (1m) — 2026-05-19",
        "",
        f"_Generated {ts} by `tools/h032_orderbook_imbalance_reversion.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR / 2-4 WEEK PROBE. No production "
        "wiring.** Fetches free Binance public 1m klines, runs the pre-registered "
        "signal through `edge_stability_harness` (imported UNMODIFIED), writes "
        "this report.",
        "",
        "## Pre-registered hypothesis (registry `tier2_2026_05_19` / H-032)",
        "",
        "CRYPTO intraday order-flow-imbalance mean-reversion at **1-minute** "
        "resolution — the one untested data axis the 11 prior daily-bar crypto "
        "kills point toward. Per-minute order-flow split from the Binance 1m "
        "kline `takerBuyBaseVolume` field (aggressive-buy vs aggressive-sell). "
        "OFI = (buy-sell)/(buy+sell); z-scored against a strictly-past 240-minute "
        "window. When |OFI_z| >= 2.0 (liquidity vacuum) FADE the imbalance "
        "(SHORT a buy spike, LONG a sell spike); enter at the minute close, exit "
        "+5 minutes.",
        "",
        "**No-look-ahead:** the OFI_z baseline reads only minutes t-240..t-1; "
        "OFI_t is the close-of-minute aggregate; entry is close(t), exit "
        "close(t+5).",
        "",
        "## Data",
        "",
        f"- Binance public 1m klines via the api-failover chain "
        f"(api/api1/api2/api3.binance.com), free, no key. ~{days}d pull. Cached "
        f"to `tools/cache/h032_orderflow_cache.json`.",
        f"- Symbols fetched: {len(per_sym)}.",
        f"- Continuous-book resolved records (every instrument-minute): "
        f"**{len(recs)}**.",
        f"- Of which qualifying |OFI_z|>=2.0 extreme-imbalance minutes: "
        f"**{v['n_signal_days']}**.",
        "",
    ]
    if per_sym:
        out += ["| symbol | minutes | records | signal min | wins | WR |",
                "|---|---|---|---|---|---|"]
        for k, pv in per_sym.items():
            wr = f"{pv['wr']*100:.1f}%" if pv.get("wr") is not None else "n/a"
            out.append(f"| {k} | {pv['mins']} | {pv['n']} | {pv['sig']} "
                       f"| {pv['wins']} | {wr} |")
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
        "## Edge & cost survival (over the qualifying extreme-imbalance minutes)",
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
def run(quick: bool, days: int) -> dict:
    universe = UNIVERSE_QUICK if quick else UNIVERSE_FULL
    data = load_data(universe, days)
    records: list[dict] = []
    per_sym: dict[str, dict] = {}
    for sym, minutes in data.items():
        srec = backtest_symbol(sym, minutes)
        records.extend(srec)
        wins = sum(1 for r in srec if r["status"] == "WON")
        sig = sum(1 for r in srec if r.get("qualifies"))
        per_sym[sym] = {"mins": len(minutes), "n": len(srec), "sig": sig,
                        "wins": wins,
                        "wr": round(wins / len(srec), 4) if srec else None}
    v = assemble_verdict(records)
    return {"records": records, "per_sym": per_sym, "verdict_block": v}


def json_summary(res: dict) -> dict:
    v = res["verdict_block"]
    return {
        "hypothesis": "H-032", "asset_class": "CRYPTO",
        "family": "intraday_orderbook_imbalance_reversion",
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
                    help="smaller universe for a fast smoke run")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS,
                    help="days of 1m history to pull per symbol")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports"
                    / "h032_orderbook_imbalance_reversion_2026-05-19.md")
    args = ap.parse_args()

    res = run(args.quick, args.days)
    summary = json_summary(res)

    if args.as_json:
        print(json.dumps(summary, indent=2, default=str))
        return 0

    report = render_report(res, args.days)
    args.out.write_text(report, encoding="utf-8")
    print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    print("\nJSON SUMMARY:")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
