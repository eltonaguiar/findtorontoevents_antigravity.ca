#!/usr/bin/env python3
"""H-038 CRYPTO mining-difficulty-lag — continuous-position research.

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, or any pick-generation / scoring path. It fetches free
market data, runs the pre-registered signal through the edge-stability harness,
and writes a report — nothing else.

------------------------------------------------------------------------------
PRE-REGISTERED HYPOTHESIS (registry key mining_difficulty_lag_2026_05_19, H-038)
------------------------------------------------------------------------------
BTC hash-rate vs the ~2-week difficulty-retarget lag.

Bitcoin difficulty re-targets every 2016 blocks (~14 days). Between retargets
the difficulty number is FROZEN while hash-rate drifts freely. The GAP between
current hash-rate and the hash-rate level the standing difficulty was set for
is a miner-economics signal:

  hashrate_gap_D = (avg_hashrate_D / hashrate_at_last_retarget) - 1

A large POSITIVE gap (hash-rate far above the retarget baseline) means blocks
are being found fast, miner revenue-per-hash is elevated, and the NEXT retarget
will RAISE difficulty — a forward cost shock that historically coincides with
miners selling BTC into strength -> SHORT BTC over the next 5 days. A large
NEGATIVE gap precedes a downward adjustment / capitulation -> LONG.

SIGNAL on day D: standardise hashrate_gap_D to a z-score against a strictly-past
trailing 180-day window of the same gap series (D excluded). Direction-signed:
gap_z > 0 -> SHORT, gap_z < 0 -> LONG. Continuous daily-position book on BTC.

STRICT NO-LOOK-AHEAD:
  * hashrate_at_last_retarget for day D is the hash-rate as of the most recent
    difficulty-retarget whose timestamp is STRICTLY BEFORE day D.
  * the 180-day z-score baseline uses gap values for days strictly before D.
  * the trade enters at the close of D and resolves at the close of D+5;
    nothing at or after the entry bar feeds the signal.

This is a DISTINCT mechanism from the killed H-014 on-chain family: H-014 used
unique-address / transaction COUNTS as a Metcalfe adoption proxy. H-038 uses
NO address or transaction data — it is a pure miner-supply / cost-shock timing
signal from the hash-rate-vs-difficulty retarget lag.

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records are fed through tools/edge_stability_harness.evaluate() UNMODIFIED.
ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of the scored 14-day windows.
A 30bps round-trip post-cost gate is then applied: cost-survival = fraction of
records whose |gross return| exceeds 30bps; verdict downgraded if < 60%.

A gaudy in-sample WR is NOT a pass. Only the honest harness verdict counts.

    python tools/h038_mining_difficulty_lag.py [--json]
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
CACHE_FILE = CACHE / "h038_mining_difficulty_cache.json"

# ---------------------------------------------------------------------------
# Pre-registered tunables (signal family fixed — no per-window search).
# ---------------------------------------------------------------------------
Z_LOOKBACK = 180          # trailing window for the hashrate-gap z-score baseline
HOLD_DAYS = 5             # forward holding horizon (close D -> close D+5)
WINDOW_DAYS = 14          # harness walk-forward window
HARNESS_FIELD = "signal_z"  # conviction magnitude the harness reads
POST_COST_BPS = 30        # round-trip cost gate
COST_SURVIVAL_MIN = 0.60

BINANCE_HOSTS = ["api.binance.com", "api1.binance.com",
                 "api2.binance.com", "api3.binance.com"]

# The BTC mining-difficulty-lag signal is a market-wide miner-supply / cost-
# shock regime signal: miner BTC treasury selling pressure hits the whole
# liquid-crypto complex, not BTC alone. The signal is computed ONCE from BTC
# hash-rate/difficulty (look-ahead-free) and resolved against a continuous
# multi-asset book — the same density construction the H-008/H-014 redesigns
# used so the harness 14-day windows (MIN_WINDOW_N=80) actually fill.
RESOLUTION_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                      "ADAUSDT", "DOGEUSDT", "LTCUSDT"]


# ===========================================================================
# Data fetch — all free, no API key
# ===========================================================================
def _http_json(url: str, timeout: int = 45):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 h038-research/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_hashrate() -> dict[str, float]:
    """Daily average BTC hash-rate from mempool.space, free, no key.

    Returns {date_iso: avg_hashrate}. mempool.space exposes 3y of daily history
    at /api/v1/mining/hashrate/3y; the `hashrates` array carries one entry per
    day as {timestamp, avgHashrate}.
    """
    data = _http_json("https://mempool.space/api/v1/mining/hashrate/3y")
    out: dict[str, float] = {}
    for row in data.get("hashrates", []):
        d = datetime.fromtimestamp(int(row["timestamp"]), timezone.utc).date()
        out[d.isoformat()] = float(row["avgHashrate"])
    return out


def fetch_difficulty_retargets() -> list[dict]:
    """BTC difficulty-retarget events from mempool.space, free, no key.

    Returns a list of {date, height, difficulty, change_ratio} ASCENDING by
    date. mempool.space /api/v1/mining/difficulty-adjustments/3y returns rows
    [timestamp, block_height, difficulty, change_ratio] — one per ~2016-block
    retarget. The timestamp is the moment the retarget took effect.
    """
    rows = _http_json(
        "https://mempool.space/api/v1/mining/difficulty-adjustments/3y")
    out: list[dict] = []
    for ts, height, difficulty, ratio in rows:
        d = datetime.fromtimestamp(int(ts), timezone.utc).date()
        out.append({"date": d.isoformat(), "height": int(height),
                    "difficulty": float(difficulty),
                    "change_ratio": float(ratio)})
    out.sort(key=lambda r: r["date"])
    return out


def fetch_close(symbol: str) -> dict[str, float]:
    """Daily close keyed by date for `symbol`, via the api-failover chain (free).

    Binance api/api1/api2/api3 daily klines first; CryptoCompare histoday as
    the fallback. Returns {date_iso: close}.
    """
    for host in BINANCE_HOSTS:
        url = (f"https://{host}/api/v3/klines?symbol={symbol}"
               f"&interval=1d&limit=1500")
        try:
            rows = _http_json(url)
            out = {}
            for k in rows:
                d = datetime.fromtimestamp(int(k[0]) // 1000,
                                           timezone.utc).date()
                out[d.isoformat()] = float(k[4])
            if len(out) >= 500:
                return out
        except Exception:  # noqa: BLE001
            continue
    # CryptoCompare fallback
    base = symbol[:-4] if symbol.endswith("USDT") else symbol
    try:
        data = _http_json("https://min-api.cryptocompare.com/data/v2/histoday"
                           f"?fsym={base}&tsym=USD&limit=1500")
        out = {}
        for k in data.get("Data", {}).get("Data", []):
            d = datetime.fromtimestamp(int(k["time"]), timezone.utc).date()
            out[d.isoformat()] = float(k["close"])
        if len(out) >= 500:
            return out
    except Exception:  # noqa: BLE001
        pass
    return {}


def load_data(use_cache: bool = True) -> dict:
    """Fetch hash-rate, difficulty retargets, and BTC close; cache to disk."""
    if use_cache and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if (cache.get("hashrate") and cache.get("retargets")
                    and cache.get("closes")):
                print("# using cached data", file=sys.stderr)
                return cache
        except Exception:  # noqa: BLE001
            pass
    print("# fetching hash-rate (mempool.space) ...", file=sys.stderr)
    hashrate = fetch_hashrate()
    time.sleep(0.3)
    print("# fetching difficulty retargets (mempool.space) ...", file=sys.stderr)
    retargets = fetch_difficulty_retargets()
    time.sleep(0.3)
    closes: dict[str, dict[str, float]] = {}
    for sym in RESOLUTION_SYMBOLS:
        print(f"# fetching {sym} daily close (api-failover) ...", file=sys.stderr)
        c = fetch_close(sym)
        if c:
            closes[sym] = c
            print(f"#   {sym}: {len(c)} days", file=sys.stderr)
        time.sleep(0.25)
    cache = {"fetched_at": datetime.now(timezone.utc).isoformat(),
             "hashrate": hashrate, "retargets": retargets, "closes": closes}
    try:
        CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    print(f"#   hash-rate days: {len(hashrate)}  retargets: {len(retargets)}  "
          f"symbols: {len(closes)}", file=sys.stderr)
    return cache


# ===========================================================================
# Signal math (pure, network-free) — STRICT no-look-ahead
# ===========================================================================
def hashrate_at_last_retarget(day: str, retargets: list[dict],
                              hashrate: dict[str, float]) -> float | None:
    """Hash-rate level as of the most recent retarget STRICTLY BEFORE `day`.

    The retarget event tells us a difficulty number took effect on its date;
    the hash-rate the new difficulty was calibrated against is the hash-rate
    around that retarget date. We use the hash-rate on the retarget date (or
    the nearest earlier day with hash-rate data). Returns None if no retarget
    precedes `day` or no hash-rate is available for it.
    """
    prior = [r for r in retargets if r["date"] < day]
    if not prior:
        return None
    rt_date = prior[-1]["date"]
    # nearest hash-rate value at-or-before the retarget date
    for back in range(0, 10):
        d = (datetime.fromisoformat(rt_date).date()
             - __import__("datetime").timedelta(days=back)).isoformat()
        if d in hashrate:
            return hashrate[d]
    return None


def build_gap_z_series(data: dict) -> dict[str, dict]:
    """Build the BTC hashrate-gap z-score series, one entry per day.

    Returns {date: {"gap_z": float}}. The signal is computed ONCE from BTC
    hash-rate / difficulty — it does NOT depend on the resolution asset.

    STRICT NO-LOOK-AHEAD: the gap on day D uses the retarget strictly before D;
    the z-score baseline uses gap values for days strictly before D.
    """
    hashrate = data["hashrate"]
    retargets = data["retargets"]

    gap_by_day: dict[str, float] = {}
    for d in sorted(hashrate):
        base = hashrate_at_last_retarget(d, retargets, hashrate)
        if base is None or base <= 0:
            continue
        gap_by_day[d] = hashrate[d] / base - 1.0

    gap_days = sorted(gap_by_day)
    series: dict[str, dict] = {}
    for idx, d in enumerate(gap_days):
        if idx < Z_LOOKBACK:
            continue
        past = [gap_by_day[gap_days[j]]
                for j in range(idx - Z_LOOKBACK, idx)]   # D excluded
        mean = statistics.fmean(past)
        sd = statistics.pstdev(past) or 1e-9
        series[d] = {"gap_z": (gap_by_day[d] - mean) / sd}
    return series


def build_records(data: dict) -> list[dict]:
    """Build the CONTINUOUS-POSITION multi-asset resolved-record series.

    The BTC mining-difficulty-lag signal (built once, look-ahead-free) is a
    market-wide miner-supply / cost-shock regime signal — miner BTC treasury
    selling pressure hits the whole liquid-crypto complex. It is resolved
    against a continuous multi-asset book over RESOLUTION_SYMBOLS so the
    harness 14-day windows (MIN_WINDOW_N=80) fill densely. This is the same
    construction the H-008 BOND and H-014 on-chain redesigns used.

    Every (resolution-symbol, day D) with (a) a gap_z for D, (b) a close on D
    and on D+HOLD_DAYS for that symbol — is one resolved record. Direction is
    the H-038 bet applied to every asset: gap_z>0 -> SHORT, gap_z<0 -> LONG.
    signal_z = |gap_z| is the conviction magnitude the harness reads.

    STRICT NO-LOOK-AHEAD: gap_z for D is built from data strictly before D;
    entry = close(D), exit = close(D+HOLD_DAYS).
    """
    gap_series = build_gap_z_series(data)
    closes = data["closes"]
    td = __import__("datetime").timedelta

    records: list[dict] = []
    for sym, px in closes.items():
        for d, sig in gap_series.items():
            gap_z = sig["gap_z"]
            if gap_z == 0:
                continue
            exit_d = (datetime.fromisoformat(d).date()
                      + td(days=HOLD_DAYS)).isoformat()
            if d not in px or exit_d not in px:
                continue
            entry, exit_px = px[d], px[exit_d]
            if entry <= 0:
                continue
            direction = -1 if gap_z > 0 else 1   # +gap -> SHORT, -gap -> LONG
            gross_ret = (exit_px / entry - 1.0) * direction
            records.append({
                "status": "WON" if gross_ret > 0 else "LOST",
                "resolved_at": exit_d,
                "entry_date": d,
                "timestamp": d,
                HARNESS_FIELD: abs(gap_z),
                "gross_ret": round(gross_ret, 6),
                "direction": direction,
                "gap_z": round(gap_z, 4),
                "instrument": sym,
            })
    records.sort(key=lambda r: (r["timestamp"], r["instrument"]))
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


def cost_survival(records: list[dict], bps: int = POST_COST_BPS) -> float:
    """Fraction of records whose |gross return| exceeds the round-trip cost."""
    if not records:
        return 0.0
    thr = bps / 10000.0
    survive = sum(1 for r in records if abs(r.get("gross_ret", 0.0)) > thr)
    return round(survive / len(records), 4)


def pooled_wr(records: list[dict]) -> float | None:
    res = [r for r in records if r["status"] in ("WON", "LOST")]
    if not res:
        return None
    return round(sum(1 for r in res if r["status"] == "WON") / len(res), 4)


def net_edge_summary(records: list[dict], bps: int = POST_COST_BPS) -> dict:
    if not records:
        return {"gross_mean_ret": None, "net_mean_ret": None}
    grs = [r.get("gross_ret", 0.0) for r in records]
    gross = statistics.fmean(grs)
    return {"gross_mean_ret": round(gross, 6),
            "net_mean_ret": round(gross - bps / 10000.0, 6)}


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
        "windows_scored": scored,
        "windows_strong": h.get("windows_strong"),
        "strong_positive": h.get("strong_positive"),
        "strong_negative": h.get("strong_negative"),
        "per_window_eff": [e["eff"] for e in h.get("per_window_eff", [])],
        "sign": h.get("sign"),
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
    effs = " ".join(f"{e:+.2f}" if e is not None else "n/a"
                    for e in v["per_window_eff"])
    next_step = {
        "ADMISSIBLE": "Harness + 30bps cost gate BOTH pass. Re-test on a fresh "
                      "out-of-sample crypto period, add deflated-Sharpe / SPA "
                      "multiple-testing correction, then operator review before "
                      "any sizing. Per TASK 3, integrate as a baby_strategies "
                      "pick-emitter.",
        "REJECTED": "Clean kill. The mining-difficulty-lag signal does not "
                    "separate winners from losers with a stable sign across "
                    "enough 14-day windows (or fails the 30bps cost gate). Do "
                    "NOT wire or size — wiring a non-admissible emitter pollutes "
                    "/audit. Archive as a tested failure.",
        "UNTESTED": "Honest non-verdict — the harness did not get >= 3 scored "
                    "14-day windows. Blocker is sample coverage, not design. Do "
                    "NOT wire.",
    }[v["verdict"]]
    out = [
        "# H-038 CRYPTO mining-difficulty-lag — 2026-05-19",
        "",
        f"_Generated {ts} by `tools/h038_mining_difficulty_lag.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR.** No caller in `quality_gates.py`, "
        "`dashboard_generator.py`, or any pick / scoring path at test time. "
        "Fetches free data, runs the pre-registered signal through "
        "`edge_stability_harness` (imported unmodified), writes this report.",
        "",
        "## Pre-registered hypothesis (registry `mining_difficulty_lag_2026_05_19` / H-038)",
        "",
        "BTC hash-rate vs the ~2-week difficulty-retarget lag. Difficulty "
        "re-targets every 2016 blocks (~14 days); between retargets the "
        "difficulty number is frozen while hash-rate drifts. The gap "
        "`hashrate_gap = hashrate_today / hashrate_at_last_retarget - 1` is a "
        "miner-economics signal: a large positive gap precedes an upward "
        "difficulty adjustment (a miner cost shock) -> SHORT BTC; a large "
        "negative gap precedes a downward adjustment -> LONG. The gap is "
        "z-scored against a strictly-past 180-day baseline; |gap_z| is the "
        "harness conviction field.",
        "",
        "**No-look-ahead:** the gap uses the retarget strictly before day D; "
        "the 180-day z-score baseline uses gap values strictly before D; the "
        f"trade enters at close(D) and resolves at close(D+{HOLD_DAYS}).",
        "",
        "**Distinct from killed H-014:** H-014 used unique-address / "
        "transaction COUNTS (Metcalfe adoption proxy). H-038 uses NO address or "
        "transaction data — it is a pure miner-supply / cost-shock timing "
        "signal from the hash-rate-vs-difficulty retarget lag.",
        "",
        "## Data (all free, no API key)",
        "",
        "- BTC daily hash-rate: mempool.space `/api/v1/mining/hashrate/3y`.",
        "- Difficulty-retarget history: mempool.space "
        "`/api/v1/mining/difficulty-adjustments/3y`.",
        "- Daily close for the resolution-asset book: api-failover chain "
        "(Binance api/api1/api2/api3 -> CryptoCompare).",
        f"- Resolution symbols (BTC signal resolved market-wide): "
        f"{', '.join(RESOLUTION_SYMBOLS)}.",
        f"- Continuous-position multi-asset resolved records: **{len(recs)}**.",
        "",
        "## Harness verdict (THE gate — harness imported UNMODIFIED)",
        "",
        f"- per-window eff (new->old): `{effs}`",
        f"- windows scored: {v['windows_scored']}  (strong: {v['windows_strong']}"
        f", +{v['strong_positive']}/-{v['strong_negative']})",
        f"- sign: `{v['sign']}`",
        f"- harness `is_admissible()`: {v['harness_admissible']}",
        f"- harness reason: {v['harness_reason']}",
        "",
        "## Edge & cost survival",
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
def run() -> dict:
    data = load_data()
    records = build_records(data)
    v = assemble_verdict(records)
    return {"records": records, "verdict_block": v}


def json_summary(res: dict) -> dict:
    v = res["verdict_block"]
    return {
        "hypothesis": "H-038", "asset_class": "CRYPTO",
        "family": "mining_difficulty_lag",
        "verdict": v["verdict"], "n": v["n"],
        "windows_scored": v["windows_scored"],
        "windows_strong": v["windows_strong"],
        "strong_positive": v["strong_positive"],
        "strong_negative": v["strong_negative"],
        "per_window_eff": v["per_window_eff"],
        "sign": v["sign"], "harness_admissible": v["harness_admissible"],
        "pooled_wr": v["pooled_wr"],
        "gross_mean_ret": v["gross_mean_ret"],
        "net_mean_ret": v["net_mean_ret"],
        "cost_survival": v["cost_survival"],
        "cost_survival_pass": v["cost_survival_pass"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports"
                    / "h038_mining_difficulty_lag_2026-05-19.md")
    args = ap.parse_args()

    res = run()
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
