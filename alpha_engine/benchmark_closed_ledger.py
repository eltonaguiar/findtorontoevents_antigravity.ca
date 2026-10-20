"""benchmark_closed_ledger.py — Task 10 of the money-ready plan.

    "Benchmark every closed-pick ledger vs SPY buy-and-hold + random-entry MC.
     A 55% WR means nothing unless it lands in the top decile of its own
     permutation distribution."

For every (strategy, asset_class) closed ledger this module computes:

  1. Trade-level stats: n, WR (hidden below n=20 per Task 9 convention),
     profit factor, compounded cumulative return.
  2. Same-window benchmark returns: for each closed trade with usable
     timestamps, the benchmark instrument (SPY for EQUITY/ETF, BTC-USD for
     CRYPTO by default) bought on the entry date and sold on the exit date.
  3. A PAIRED bootstrap (10,000 seeded resamples of (trade, benchmark) pairs):
     CI on mean(trade - benchmark) and the fraction of resamples with a
     positive mean. `pass_95` requires frac >= 0.95 (plan C.3 Step 2 gate).
  4. A random-entry Monte-Carlo timing test: under the null of no timing
     skill each trade could have been opened on a random date with the same
     holding length; we rank the realized total against 10,000 such null
     portfolios. percentile ~1.0 => timing adds value; ~0.5 => coin flip.

Design rules
------------
* Self-contained (stdlib only for all statistics) so it cannot break or be
  broken by parallel edits to audit_trail/quality_gates.py or
  audit_dashboard/ueps_section_renderer.py, which already publish Wilson
  intervals on the card surface. The Wilson formula here is duplicated on
  purpose; cross-importing 577 KB of quality_gates for one formula would
  create coupling between two independently-evolving task branches.
* Fail-soft everywhere: ledgers without entry timestamps get trade-level
  stats only, with the reason recorded in `notes` — never an exception.
* The benchmark instrument is configurable per asset class; the mapping is
  an explicit constant, documented as a modelling choice (SPY is the
  benchmark the plan names; equity-linked classes share it).

Usage
-----
  python3 -m alpha_engine.benchmark_closed_ledger \
      --picks audit_dashboard/data/dashboard_data.json \
      --fetch BTC-USD SPY \
      --out reports/benchmark_ledger_proof_2026-10-19.json

  # or with a pre-downloaded prices file (JSON: {"SYM": {"YYYY-MM-DD": close}})
  python3 -m alpha_engine.benchmark_closed_ledger --picks ... --prices prices.json

Exit codes: 0 = report written (even if some ledgers were skipped — see
`notes`); 2 = inputs unusable (missing/empty picks file, no ledgers at all).
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import random
import sys
from datetime import datetime, timezone
from typing import Any, Iterable

Z95 = 1.959963984540054

# Benchmark instrument per asset class — a modelling choice, made explicit.
# Equity-linked classes share SPY (the benchmark named in the plan); CRYPTO
# uses BTC-USD as its market proxy; anything unmapped falls back to SPY with
# a note.
BENCHMARK_BY_CLASS = {
    "EQUITY": "SPY",
    "ETF": "SPY",
    "COMMODITY": "SPY",
    "FUTURES": "SPY",
    "BOND": "SPY",
    "MEME": "SPY",
    "PENNY_STOCK": "SPY",
    "CRYPTO": "BTC-USD",
    "FOREX": "SPY",  # quarantined class; benchmark only for completeness
}

WR_HIDE_BELOW_N = 20          # Task 9 convention: no WR claim below n=20
DEFAULT_N_PERM = 10_000
DEFAULT_N_BOOT = 10_000
DEFAULT_SEED = 42


# ────────────────────────────────────────────────────────── small statistics ──
def wilson_interval(wins: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion.

    2/2 reads (~0.206, 1.0) — never "100% with confidence". Duplicated from
    the Task 9 card-side implementation on purpose (see module docstring).
    """
    n = int(n)
    if n <= 0:
        return (0.0, 1.0)
    p = wins / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def profit_factor(returns: Iterable[float]) -> float | None:
    """Gross wins / |gross losses|.

    Returns None when undefined (no losses and no wins, or no losses at all —
    an all-win ledger has no finite PF and must not serialize as Infinity,
    which is invalid JSON).
    """
    gross = sum(r for r in returns if r > 0)
    loss = -sum(r for r in returns if r < 0)
    if loss <= 1e-12:
        return None
    return gross / loss


def compound_return(returns: Iterable[float]) -> float:
    """Compounded total return from a sequence of per-trade fractional returns."""
    total = 1.0
    for r in returns:
        total *= 1.0 + r
    return total - 1.0


def paired_bootstrap(
    trade_rets: list[float],
    bench_rets: list[float],
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Paired bootstrap of mean(trade - benchmark) over (trade, bench) pairs.

    Returns ci_lo/ci_hi (percentile 95% CI, in fractional return units),
    frac_positive (fraction of resamples with positive mean excess), and
    pass_95 (frac_positive >= 0.95 — plan C.3 Step 2's publish gate).
    """
    assert len(trade_rets) == len(bench_rets) and trade_rets, "paired input"
    diffs = [t - b for t, b in zip(trade_rets, bench_rets)]
    n = len(diffs)
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += diffs[rng.randrange(n)]
        means.append(s / n)
    means.sort()
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot)]
    frac_pos = sum(1 for m in means if m > 0) / n_boot
    return {
        "mean_excess": sum(diffs) / n,
        "ci_lo": lo,
        "ci_hi": hi,
        "frac_positive": frac_pos,
        "pass_95": frac_pos >= 0.95,
        "n_boot": n_boot,
    }


def random_entry_mc(
    series_by_sym: dict[str, list[float]],
    trades: list[tuple[str, int, int, float, int]],
    n_perm: int = DEFAULT_N_PERM,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any] | None:
    """Random-entry Monte-Carlo timing test (same-asset, window-matched null).

    trades: list of (symbol, entry_idx, exit_idx, realized_fractional_return,
    direction_sign) with indices into series_by_sym[symbol]; direction_sign
    is +1 for longs and -1 for shorts (null returns are negated for shorts).

    Null hypothesis: every trade could have been opened at a random date
    INSIDE THE LEDGER'S OWN TRADING WINDOW for that symbol, with the same
    holding length, on THE SAME ASSET the trade actually traded, in the same
    direction.

    Fixes (2026-10-19, after external review):
      * v1 sampled nulls on the BENCHMARK price path across FULL history —
        a no-skill ledger trading one strong regime pinned at percentile 1.0
        (luxalgo_confluence: PF 1.03, WR 42% -> 1.0).
      * v2 window-matched the null but still used the benchmark path; a
        heavy-tail check ruled out outlier capture (top trade = 4% of the
        observed total) and exposed the residual bias: cross-asset scale —
        altcoin/penny-stock trade returns ranked against BTC/SPY paths.
      * v3 (this): per-symbol own-price nulls + direction-aware signs.

    Skips trades whose symbol series is missing or that cannot be simulated
    on daily closes (same-day round trips collapse to hold=0 bars; exits
    beyond the series end). Skips are reported; obs_total is computed on
    exactly the simulatable subset so the ranking stays like-for-like.

    Null trades are frictionless while realized returns are net of costs —
    a deliberately conservative bias against the observed percentile.

    Returns None when fewer than one trade is simulatable.

    percentile ~1.0 => timing adds value; ~0.5 => coin flip. This is the
    Task 10 `random_entry_mc_pctile` column.
    """
    by_sym: dict[str, list[tuple[int, int, float, int]]] = {}
    for sym, ei, xi, r, sign in trades:
        px = series_by_sym.get(sym)
        if px is None or not (0 <= ei < xi < len(px) and xi - ei >= 1):
            continue
        by_sym.setdefault(sym, []).append((ei, xi, r, sign))
    if not by_sym:
        return None
    obs_total = sum(r for ts in by_sym.values() for _, _, r, _ in ts)
    rng = random.Random(seed)
    totals: list[float] = []
    for _ in range(n_perm):
        tot = 0.0
        for sym, ts in by_sym.items():
            px = series_by_sym[sym]
            # window-matched per symbol: never outside the span it traded
            lo = min(ei for ei, _, _, _ in ts)
            hi = max(xi for _, xi, _, _ in ts)
            for ei, xi, _r, sign in ts:
                hold = xi - ei
                last_start = hi - hold
                start = rng.randrange(lo, last_start + 1) if last_start > lo else lo
                tot += sign * (px[start + hold] / px[start] - 1.0)
        totals.append(tot)
    totals.sort()
    pctile = bisect.bisect_left(totals, obs_total) / n_perm
    n_sim = sum(len(ts) for ts in by_sym.values())
    return {
        "obs_total": obs_total,
        "percentile": pctile,
        "n_perm": n_perm,
        "n_simulated": n_sim,
        "n_skipped": len(trades) - n_sim,
        "n_symbols": len(by_sym),
    }


# ────────────────────────────────────────────────────────────────── loading ──
def _to_dt(value: Any) -> datetime | None:
    """Parse the timestamp dialects found in the repo ledgers.

    Handles trailing 'Z', '+00:00' offsets, and naive strings (assumed UTC).
    """
    if not isinstance(value, str) or not value:
        return None
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_closed_picks(path: str) -> list[dict]:
    """Load closed pick rows from a repo JSON feed.

    Accepts: a flat list; {"picks": [...]} / {"candidates": [...]} / and the
    dashboard_data.json shape {"picks": {"recent_closed": [...]}}. Rows
    without a numeric pnl_pct are dropped (they cannot contribute to any
    ledger statistic).
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows: Any = None
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for key_path in (("picks", "recent_closed"), ("picks",), ("candidates",),
                         ("records",), ("_records",)):
            cur: Any = data
            for k in key_path:
                cur = cur.get(k) if isinstance(cur, dict) else None
                if cur is None:
                    break
            if isinstance(cur, list):
                rows = cur
                break
    if not rows:
        raise ValueError(f"no closed-pick list found in {path}")
    clean = [r for r in rows
             if isinstance(r, dict) and isinstance(r.get("pnl_pct"), (int, float))]
    if not clean:
        raise ValueError(f"{path}: found {len(rows)} rows, none with numeric pnl_pct")
    return clean


MAX_OWN_FETCH = 400  # cap for --fetch-picks own-symbol series


def _yf_ticker(sym: str) -> str:
    """Map a repo symbol to its yfinance ticker (crypto USDT/PERP -> USD)."""
    s = sym.strip().upper()
    for suffix in ("USDT", "PERP"):
        if s.endswith(suffix):
            return s[:-len(suffix)] + "-USD"
    return sym


def load_prices(path: str) -> dict[str, dict[str, float]]:
    """Load a prices file: {"SYM": {"YYYY-MM-DD": close, ...}, ...}."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out: dict[str, dict[str, float]] = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected object of symbol->series")
    for sym, series in data.items():
        if isinstance(series, dict):
            out[sym] = {d: float(c) for d, c in series.items()
                        if isinstance(c, (int, float))}
    if not out:
        raise ValueError(f"{path}: no usable price series")
    return out


def fetch_prices_yf(symbols: list[str], start: str, end: str | None = None
                    ) -> dict[str, dict[str, float]]:
    """Fetch daily closes via yfinance (already a repo dependency).

    Fail-soft: any symbol that cannot be fetched is simply absent from the
    result; callers degrade that ledger to trade-level stats with a note.
    """
    try:
        import yfinance as yf  # noqa: PLC0411 — optional dependency
    except ImportError:
        return {}
    out: dict[str, dict[str, float]] = {}
    for sym in symbols:
        try:
            hist = yf.Ticker(sym).history(start=start, end=end, auto_adjust=True)
            series = {}
            for idx, row in hist.iterrows():
                close = row.get("Close")
                if close is not None and close == close:  # NaN guard
                    series[idx.strftime("%Y-%m-%d")] = float(close)
            if series:
                out[sym] = series
        except Exception:
            continue
    return out


def _series_to_indexed(series: dict[str, float]) -> tuple[list[str], list[float]]:
    """Sorted (dates, closes) for bisect-based as-of lookups."""
    dates = sorted(series)
    return dates, [series[d] for d in dates]


def _asof_close(dates: list[str], closes: list[float], day: str) -> float | None:
    """Close on `day`, or the most recent earlier close (as-of semantics)."""
    i = bisect.bisect_right(dates, day) - 1
    return closes[i] if i >= 0 else None


# ──────────────────────────────────────────────────────────────── per ledger ──
def benchmark_ledger(
    rows: list[dict],
    prices_by_sym: dict[str, dict[str, float]],
    benchmark: str,
    n_boot: int = DEFAULT_N_BOOT,
    n_perm: int = DEFAULT_N_PERM,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Benchmark one (strategy, asset_class) closed ledger. Never raises."""
    notes: list[str] = []
    rets = [float(r["pnl_pct"]) / 100.0 for r in rows]
    n = len(rets)
    wins = sum(1 for r in rets if r > 0)
    out: dict[str, Any] = {
        "benchmark": benchmark,
        "n": n,
        "wins": wins,
        # Task 9 convention: no WR claim below n=20.
        "wr": (wins / n) if n >= WR_HIDE_BELOW_N else None,
        "wr_published": n >= WR_HIDE_BELOW_N,
        "pf": profit_factor(rets),
        "cum_return": compound_return(rets),
        "paired_bootstrap": None,
        "random_entry_mc": None,
        "notes": notes,
    }
    if n >= WR_HIDE_BELOW_N:
        lo, hi = wilson_interval(wins, n)
        out["wilson_ci"] = [lo, hi]
    else:
        out["wilson_ci"] = None
        notes.append(f"n<{WR_HIDE_BELOW_N}: WR/wilson hidden (insufficient sample)")

    bench_series = prices_by_sym.get(benchmark)
    if not bench_series:
        notes.append(f"no price series for benchmark {benchmark}: timing tests skipped")
        return out
    bdates, bcloses = _series_to_indexed(bench_series)

    # Pair each timestamped trade with its same-window benchmark return.
    trade_rets: list[float] = []
    bench_rets: list[float] = []
    # MC (2026-10-19, v3): same-asset nulls — indices are per-symbol; trades
    # without an own-symbol series fall back to the benchmark path and are
    # counted/reported as n_benchmark_fallback.
    mc_series: dict[str, list[float]] = {"__bench__": bcloses}
    mc_trades: list[tuple[str, int, int, float, int]] = []
    _own_cache: dict[str, tuple[list[str], list[float]] | None] = {}

    def _own_series(sym: str) -> tuple[list[str], list[float]] | None:
        if sym not in _own_cache:
            s = prices_by_sym.get(sym)
            _own_cache[sym] = _series_to_indexed(s) if s else None
        return _own_cache[sym]

    n_mc_fallback = 0
    for r in rows:
        entry_dt = _to_dt(r.get("entry_time") or r.get("timestamp"))
        exit_dt = _to_dt(r.get("closed_at") or r.get("timestamp"))
        if entry_dt is None or exit_dt is None or exit_dt < entry_dt:
            continue
        d0, d1 = entry_dt.strftime("%Y-%m-%d"), exit_dt.strftime("%Y-%m-%d")
        p0 = _asof_close(bdates, bcloses, d0)
        p1 = _asof_close(bdates, bcloses, d1)
        if p0 is None or p1 is None or p0 <= 0:
            continue
        fr = float(r["pnl_pct"]) / 100.0
        trade_rets.append(fr)
        bench_rets.append(p1 / p0 - 1.0)
        ei = bisect.bisect_left(bdates, d0)
        xi = bisect.bisect_left(bdates, d1)
        sign = -1 if str(r.get("direction") or "").upper().startswith("S") else 1
        sym = str(r.get("symbol") or "")
        ser = _own_series(sym) if sym else None
        if ser is not None:
            sdates, scloses = ser
            si = bisect.bisect_left(sdates, d0)
            sj = bisect.bisect_left(sdates, d1)
            mc_series[sym] = scloses
            mc_trades.append((sym, si, sj, fr, sign))
        else:
            n_mc_fallback += 1
            mc_trades.append(("__bench__", ei, xi, fr, sign))

    n_paired = len(trade_rets)
    out["n_paired"] = n_paired
    if n_paired < 5:
        notes.append(
            f"only {n_paired} trades had usable timestamps/benchmark prices "
            "(<5): paired bootstrap skipped")
    else:
        out["paired_bootstrap"] = paired_bootstrap(trade_rets, bench_rets,
                                                   n_boot=n_boot, seed=seed)
        out["bench_cum_return_same_windows"] = compound_return(bench_rets)
        out["cum_return_vs_benchmark_pp"] = (
            (out["cum_return"] - out["bench_cum_return_same_windows"]) * 100.0)
    mc = random_entry_mc(mc_series, mc_trades, n_perm=n_perm, seed=seed) \
        if mc_trades else None
    if mc is None:
        notes.append("no simulatable trades for random-entry MC")
    else:
        if n_mc_fallback:
            mc["n_benchmark_fallback"] = n_mc_fallback
            notes.append(
                f"{n_mc_fallback} MC trades null-sampled on the {benchmark} "
                "benchmark path (own-symbol series unavailable)")
        out["random_entry_mc"] = mc
    return out


def _group_ledgers(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = (str(r.get("strategy") or "(unattributed)"),
               str(r.get("asset_class") or "UNKNOWN"))
        groups.setdefault(key, []).append(r)
    return groups


def build_report(
    rows: list[dict],
    prices_by_sym: dict[str, dict[str, float]],
    n_boot: int = DEFAULT_N_BOOT,
    n_perm: int = DEFAULT_N_PERM,
    seed: int = DEFAULT_SEED,
    min_n_for_timing: int = 5,
) -> dict[str, Any]:
    """Benchmark every closed ledger; assemble the Task 10 report."""
    ledgers = []
    for (strategy, asset_class), group in sorted(
            _group_ledgers(rows).items(), key=lambda kv: -len(kv[1])):
        benchmark = BENCHMARK_BY_CLASS.get(asset_class, "SPY")
        if asset_class not in BENCHMARK_BY_CLASS:
            note_extra = f"unmapped asset class {asset_class}: used SPY fallback"
        else:
            note_extra = None
        entry = {"strategy": strategy, "asset_class": asset_class}
        entry.update(benchmark_ledger(group, prices_by_sym, benchmark,
                                      n_boot=n_boot, n_perm=n_perm, seed=seed))
        if note_extra:
            entry["notes"].append(note_extra)
        if entry["n"] < min_n_for_timing and not entry["notes"]:
            entry["notes"].append(f"n<{min_n_for_timing}: timing tests unreliable")
        ledgers.append(entry)

    full_proof = [l for l in ledgers
                  if l.get("paired_bootstrap") and l.get("random_entry_mc")]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "alpha_engine/benchmark_closed_ledger.py (Task 10)",
        "n_boot": n_boot,
        "n_perm": n_perm,
        "seed": seed,
        "conventions": {
            "wr_hidden_below_n": WR_HIDE_BELOW_N,
            "pass_95_rule": "paired bootstrap frac_positive >= 0.95",
            "mc_reading": "percentile ~1.0 timing edge; ~0.5 coin flip; nulls window-matched to the ledger's own trading span (fixed 2026-10-19 — full-history nulls overstated timing)",
        },
        "ledgers": ledgers,
        "summary": {
            "n_ledgers": len(ledgers),
            "n_full_proof": len(full_proof),
            "n_pass_95": sum(1 for l in full_proof
                             if l["paired_bootstrap"]["pass_95"]),
            "n_mc_top_decile": sum(1 for l in full_proof
                                   if l["random_entry_mc"]["percentile"] >= 0.90),
        },
    }


# ─────────────────────────────────────────────────────────────────────── CLI ──
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--picks", required=True,
                    help="closed-picks JSON (dashboard_data.json or flat list)")
    ap.add_argument("--prices", help="pre-downloaded prices JSON "
                                     '{"SYM": {"YYYY-MM-DD": close}}')
    ap.add_argument("--fetch", nargs="*", default=None,
                    help="symbols to fetch via yfinance (e.g. SPY BTC-USD)")
    ap.add_argument("--fetch-start", default="2026-05-01",
                    help="history start for --fetch (default 2026-05-01)")
    ap.add_argument("--fetch-picks", action="store_true",
                    help="also fetch one yfinance series per distinct pick "
                         "symbol (required for same-asset MC nulls)")
    ap.add_argument("--out", help="write full JSON report here (else stdout)")
    ap.add_argument("--n-perm", type=int, default=DEFAULT_N_PERM)
    ap.add_argument("--n-boot", type=int, default=DEFAULT_N_BOOT)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args(argv)

    try:
        rows = load_closed_picks(args.picks)
    except (OSError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    prices: dict[str, dict[str, float]] = {}
    if args.prices:
        try:
            prices.update(load_prices(args.prices))
        except (OSError, ValueError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
    if args.fetch:
        prices.update(fetch_prices_yf(args.fetch, args.fetch_start))
    if args.fetch_picks:
        syms = sorted({str(r.get("symbol") or "") for r in rows} - {""})
        tickers = sorted({_yf_ticker(s) for s in syms})[:MAX_OWN_FETCH]
        print(f"fetching {len(tickers)} own-symbol series for same-asset MC nulls...")
        own = fetch_prices_yf(tickers, args.fetch_start)
        for s in syms:
            t = _yf_ticker(s)
            if t in own and s not in prices:
                prices[s] = own[t]

    report = build_report(rows, prices, n_boot=args.n_boot,
                          n_perm=args.n_perm, seed=args.seed)
    payload = json.dumps(report, indent=1, allow_nan=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
        print(f"wrote {args.out}: {report['summary']}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
