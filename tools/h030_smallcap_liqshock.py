#!/usr/bin/env python3
"""H-030 EQUITY small-cap liquidity-shock reversion — continuous-position research.

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, or any pick-generation / scoring path. It fetches free
yfinance data, runs the pre-registered signal through the edge-stability
harness, and writes a report — nothing else.

------------------------------------------------------------------------------
PRE-REGISTERED HYPOTHESIS (registry key local_harvest_2026_05_19, id H-030)
------------------------------------------------------------------------------
Fade a liquidity-shock day in liquid small-cap Russell-2000 names (price > $5).

SIGNAL DAY D qualifies when:
  (a) D's volume is > 3x its trailing 60-day mean volume (relative-volume shock,
      strictly past 60 days, D excluded), AND
  (b) D closes WEAK — close in the bottom 25% of D's high-low range.

ENTRY LONG at the open of D+1.
EXIT at +3 trading days, or +/-1 x ATR(14), whichever is hit first.

Continuous multi-asset LONG-only book over a fixed pre-registered basket of
liquid Russell-2000 small caps, yfinance daily bars. To give the harness the
density it needs (MIN_WINDOW_N=80 records / 14-day window) the book is
continuous: EVERY instrument-day is one resolved record. `signal_z` (the score
the harness reads) carries the liquidity-shock conviction — the trailing-60d
volume z-score, GATED so that only days clearing BOTH the >3x-volume and the
weak-close test carry their z; all other days carry 0. The harness verdict
then answers exactly the H-030 question: do the qualifying liquidity-shock
days separate winners from losers?

STRICT NO-LOOK-AHEAD: day-D qualification uses only bars strictly before D for
the 60-day volume baseline and ATR(14); the trade enters at the D+1 open and
its +3d / ATR exit uses only bars from D+1 onward.

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records are fed through tools/edge_stability_harness.evaluate() UNMODIFIED.
ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5 walk-forward 14-day windows.
A 30bps round-trip post-cost gate is applied: cost-survival = fraction of
QUALIFYING signal days whose |gross return| exceeds 30bps; verdict downgraded
if cost-survival < 60%. A gaudy in-sample WR is NOT a pass.

    python tools/h030_smallcap_liqshock.py [--quick] [--json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
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
CACHE_FILE = CACHE / "h030_smallcap_cache.json"

# ---------------------------------------------------------------------------
# Pre-registered tunables (signal family fixed — no per-window search).
# ---------------------------------------------------------------------------
VOL_LOOKBACK = 60          # trailing window for the relative-volume baseline
VOL_MULT = 3.0             # D's volume must exceed 3x the trailing mean
WEAK_CLOSE_PCT = 0.25      # close must be in the bottom 25% of D's H-L range
ATR_LEN = 14               # ATR length for the +/-1xATR exit
HOLD_DAYS = 3              # time-stop: exit at +3 trading days
MIN_PRICE = 5.0            # liquidity floor: price must exceed $5
WINDOW_DAYS = 14
HARNESS_FIELD = "signal_z"
POST_COST_BPS = 30
COST_SURVIVAL_MIN = 0.60

# Fixed pre-registered basket of liquid Russell-2000 small/mid-cap names.
# Chosen for liquid options/volume and long yfinance history; the basket is
# fixed in advance — no post-hoc survivorship selection.
BASKET_FULL = ["PLUG", "FUBO", "RIOT", "MARA", "SOFI", "CHPT", "RUN", "BBBY",
               "CLOV", "WKHS", "SPCE", "GME", "AMC", "BLNK", "FCEL", "OPEN",
               "UPST", "AFRM", "DKNG", "PTON", "LCID", "RIVN", "JOBY", "ROOT",
               "DNA", "BIGC", "SKLZ", "GOEV", "RKLB", "ASTS"]
BASKET_QUICK = ["PLUG", "RIOT", "SOFI", "GME", "AMC", "UPST", "DKNG", "RKLB"]


# ===========================================================================
# Data fetch — yfinance daily OHLCV
# ===========================================================================
def fetch_yf_ohlcv(ticker: str, period: str = "max") -> list[dict]:
    """yfinance daily OHLCV bars for `ticker`, ascending by date. [] on failure."""
    import warnings
    warnings.filterwarnings("ignore")
    try:
        import yfinance as yf
    except ImportError:
        return []
    df = None
    for _ in range(3):
        try:
            df = yf.download(ticker, period=period, interval="1d",
                             progress=False, auto_adjust=True)
        except Exception:  # noqa: BLE001
            df = None
        if df is not None and len(df) >= VOL_LOOKBACK + 30:
            break
        time.sleep(2)
    if df is None or len(df) < VOL_LOOKBACK + 30:
        return []
    out = []
    cols = {c[0] if isinstance(c, tuple) else c: c for c in df.columns}
    for idx, row in df.iterrows():
        try:
            d = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
            o = float(row[cols["Open"]]); h = float(row[cols["High"]])
            lo = float(row[cols["Low"]]); c = float(row[cols["Close"]])
            v = float(row[cols["Volume"]])
        except (KeyError, TypeError, ValueError):
            continue
        if o > 0 and h > 0 and lo > 0 and c > 0:
            out.append({"date": d, "open": o, "high": h, "low": lo,
                        "close": c, "volume": v})
    return out


def load_data(tickers: list[str], use_cache: bool = True) -> dict[str, list[dict]]:
    """Fetch OHLCV for all tickers, cache to tools/cache/."""
    cache: dict = {}
    if use_cache and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache = {}
    out: dict[str, list[dict]] = {}
    for tk in tickers:
        cached = cache.get(tk)
        if cached and len(cached) >= VOL_LOOKBACK + 30:
            out[tk] = cached
            print(f"#   {tk}: {len(cached)} bars (cache)", file=sys.stderr)
            continue
        print(f"# fetching {tk} ...", file=sys.stderr)
        bars = fetch_yf_ohlcv(tk)
        if bars:
            out[tk] = bars
            cache[tk] = bars
            print(f"#   {tk}: {len(bars)} bars", file=sys.stderr)
        else:
            print(f"#   {tk}: SKIP (fetch failed / thin)", file=sys.stderr)
        time.sleep(0.4)
    try:
        CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return out


# ===========================================================================
# Signal math (pure, network-free)
# ===========================================================================
def true_range(bar: dict, prev_close: float | None) -> float:
    hl = bar["high"] - bar["low"]
    if prev_close is None:
        return hl
    return max(hl, abs(bar["high"] - prev_close), abs(bar["low"] - prev_close))


def backtest_ticker(tk: str, bars: list[dict]) -> list[dict]:
    """Build the CONTINUOUS-POSITION resolved-record series for one ticker.

    For every day D (index i) with a 60-day past window and a D+HOLD_DAYS bar:
      * relative volume = volume(D) / trailing-60d mean volume (D excluded).
      * weak close = close(D) in the bottom 25% of D's high-low range.
      * the day QUALIFIES as an H-030 liquidity shock iff relvol > 3x AND the
        close is weak AND price(D) > $5.
      * the book is LONG-only (H-030 fades the panic by buying): direction = +1
        always. Entry = open(D+1). Exit = first of +HOLD_DAYS trading days or
        +/-1xATR(14) — evaluated bar-by-bar over [D+1, D+HOLD_DAYS].
      * signal_z = trailing-60d volume z-score on qualifying days, 0 otherwise.
        The harness eff measures whether the qualifying liquidity-shock days
        (high signal_z) separate winners from losers.

    STRICT NO-LOOK-AHEAD: the 60-day volume baseline and ATR(14) use bars
    i-60..i-1 (D excluded); entry is the D+1 open; the exit scan only looks at
    bars D+1..D+HOLD_DAYS.
    """
    records: list[dict] = []
    tr_series: list[float] = []
    for i, b in enumerate(bars):
        prev_close = bars[i - 1]["close"] if i > 0 else None
        tr_series.append(true_range(b, prev_close))

    for i in range(VOL_LOOKBACK, len(bars) - HOLD_DAYS):
        d_bar = bars[i]
        # ----- strictly-past volume baseline (D excluded) -----
        past_vol = [bars[j]["volume"] for j in range(i - VOL_LOOKBACK, i)]
        mean_vol = statistics.fmean(past_vol) if past_vol else 0.0
        if mean_vol <= 0:
            continue
        relvol = d_bar["volume"] / mean_vol
        rng = d_bar["high"] - d_bar["low"]
        if rng <= 0:
            continue
        close_pos = (d_bar["close"] - d_bar["low"]) / rng   # 0=low, 1=high
        # ----- H-030 qualification gate -----
        qualifies = (relvol > VOL_MULT
                     and close_pos <= WEAK_CLOSE_PCT
                     and d_bar["close"] > MIN_PRICE)
        # ----- ATR(14) strictly-past -----
        atr_window = tr_series[i - ATR_LEN:i]
        atr = statistics.fmean(atr_window) if atr_window else tr_series[i]
        # ----- LONG entry at D+1 open -----
        entry = bars[i + 1]["open"]
        if entry <= 0 or atr <= 0:
            continue
        atr_tp = entry + atr
        atr_sl = entry - atr
        exit_px = bars[i + HOLD_DAYS]["close"]   # default: +HOLD_DAYS time stop
        for k in range(i + 1, i + HOLD_DAYS + 1):
            b = bars[k]
            if b["low"] <= atr_sl:
                exit_px = atr_sl
                break
            if b["high"] >= atr_tp:
                exit_px = atr_tp
                break
        gross_ret = exit_px / entry - 1.0   # LONG-only, direction = +1
        # signal_z = liquidity-shock conviction (volume z), gated by qualification
        sd = statistics.pstdev(past_vol) or 1e-9
        vol_z = (d_bar["volume"] - mean_vol) / sd
        signal_z = abs(vol_z) if qualifies else 0.0
        status = "WON" if gross_ret > 0 else "LOST"
        records.append({
            "status": status,
            "resolved_at": bars[i + HOLD_DAYS]["date"],
            "entry_date": bars[i + 1]["date"],
            "timestamp": d_bar["date"],
            HARNESS_FIELD: signal_z,
            "gross_ret": round(gross_ret, 6),
            "direction": 1,
            "qualifies": qualifies,
            "instrument": tk,
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
    return round(sum(1 for r in sig
                     if abs(r.get("gross_ret", 0.0)) > thr) / len(sig), 4)


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
def render_report(res: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    v = res["verdict_block"]
    recs = res["records"]
    per_tk = res["per_tk"]
    effs = " ".join(f"{e:+.2f}" if e is not None else "n/a"
                    for e in v["per_window_eff"])
    next_step = {
        "ADMISSIBLE": "Re-test on a fresh out-of-sample equity period, add full "
                      "commission + bid-ask + small-cap slippage modelling, run "
                      "a deflated-Sharpe / SPA multiple-testing correction, then "
                      "operator review. Harness pass is necessary, not "
                      "sufficient. No wiring.",
        "REJECTED": "Clean kill. The small-cap liquidity-shock reversion signal "
                    "does not separate winners from losers with a stable sign "
                    "across enough 14-day windows (or fails the 30bps cost "
                    "gate). Do not wire or size. Archive as a tested failure.",
        "UNTESTED": "Honest non-verdict — the harness did not get >= 3 scored "
                    "14-day windows. Blocker is sample coverage, not design; a "
                    "larger fixed basket of long-history small caps would help.",
    }[v["verdict"]]
    out = [
        "# H-030 EQUITY small-cap liquidity-shock reversion — 2026-05-19",
        "",
        f"_Generated {ts} by `tools/h030_smallcap_liqshock.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in "
        "`quality_gates.py`, `dashboard_generator.py`, or any pick / scoring "
        "path. Fetches free yfinance data, runs the pre-registered signal "
        "through `edge_stability_harness` (imported unmodified), writes this "
        "report.",
        "",
        "## Pre-registered hypothesis (registry `local_harvest_2026_05_19` / H-030)",
        "",
        "Fade a liquidity-shock day in liquid small-cap Russell-2000 names "
        "(price > $5). Day D qualifies when its volume is **> 3x the trailing "
        "60-day mean volume** AND it **closes weak** (close in the bottom 25% "
        "of D's high-low range). Enter **LONG at the open of D+1**; exit at +3 "
        "trading days or +/-1xATR(14), whichever first. Continuous LONG-only "
        "multi-asset book over a fixed pre-registered basket, yfinance daily.",
        "",
        "**No-look-ahead:** day-D qualification uses only bars strictly before D "
        "for the 60-day volume baseline and ATR(14); entry is the D+1 open and "
        "the exit scan only reads bars D+1..D+3.",
        "",
        "## Data",
        "",
        "- yfinance daily OHLCV, free, no key. Cached to "
        "`tools/cache/h030_smallcap_cache.json`.",
        f"- Fixed basket tickers fetched: {len(per_tk)}.",
        f"- Continuous-book resolved records (every instrument-day): "
        f"**{len(recs)}**.",
        f"- Of which qualifying H-030 liquidity-shock signal days: "
        f"**{v['n_signal_days']}**.",
        "",
    ]
    if per_tk:
        out += ["| ticker | records | signal days | wins | WR |",
                "|---|---|---|---|---|"]
        for k, pv in per_tk.items():
            wr = f"{pv['wr']*100:.1f}%" if pv.get("wr") is not None else "n/a"
            out.append(f"| {k} | {pv['n']} | {pv['sig']} | {pv['wins']} | {wr} |")
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
        "## Edge & cost survival (over the qualifying H-030 signal days)",
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
    basket = BASKET_QUICK if quick else BASKET_FULL
    data = load_data(basket)
    records: list[dict] = []
    per_tk: dict[str, dict] = {}
    for tk, bars in data.items():
        trec = backtest_ticker(tk, bars)
        records.extend(trec)
        wins = sum(1 for r in trec if r["status"] == "WON")
        sig = sum(1 for r in trec if r.get("qualifies"))
        per_tk[tk] = {"n": len(trec), "sig": sig, "wins": wins,
                      "wr": round(wins / len(trec), 4) if trec else None}
    v = assemble_verdict(records)
    return {"records": records, "per_tk": per_tk, "verdict_block": v}


def json_summary(res: dict) -> dict:
    v = res["verdict_block"]
    return {
        "hypothesis": "H-030", "asset_class": "EQUITY",
        "family": "smallcap_liquidity_shock_reversion",
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
                    help="smaller basket for a fast smoke run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" / "h030_smallcap_liqshock_2026-05-19.md")
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
