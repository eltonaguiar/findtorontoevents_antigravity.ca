"""Per-class edge harness — pre-registered mechanisms scored under G0-G8 statistics.

Every cell here was registered in reports/hypothesis_registry.json (H-200..H-213)
BEFORE the first run, with frozen parameters and costs, so the trial count used by
the Deflated Sharpe Ratio is honest (M-107).

What it measures per cell
  n_trades, win rate, profit factor, mean trade return (net)
  daily Sharpe, block-bootstrap 95% CI of the mean daily return
  the same CI at 2x cost (G3), chronological split-half means (G5)
  DSR against the expected maximum of `--n-trials` zero-skill trials (G4)
  minimum track-record length needed to certify the observed Sharpe
  equal-weight universe buy-and-hold over the same window (the beta leg)

Usage:
  python3 tools/per_class_edge_harness.py --out reports/per_class_edge_2026-11-22.json \
      --md reports/per_class_edge_2026-11-22.md --n-trials 14
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

START = "2012-01-01"
CACHE = Path("data/research_cache")

UNIVERSES = {
    "EQUITY": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "XOM", "UNH", "JNJ"],
    "ETF": ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "XLE", "XLF", "SMH"],
    "CRYPTO": ["BTC-USD", "ETH-USD", "SOL-USD", "LINK-USD", "AVAX-USD", "ADA-USD"],
    "FOREX": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"],
    "COMMODITY": ["GC=F", "CL=F", "SI=F", "NG=F", "ZC=F", "HG=F"],
    "BOND": ["TLT", "IEF", "LQD", "HYG", "SHY"],
    # Added 2026-11-22: a class with 4 rows must appear labelled INSUFFICIENT_N,
    # not vanish from the sweep.
    "FUTURES": ["ES=F", "NQ=F", "YM=F", "RTY=F", "ZB=F", "ZN=F", "6E=F", "6J=F"],
    "PENNY_STOCK": ["PLUG", "FCEL", "GNUS", "SHIP", "TOPS", "NOK", "CTRM", "SNDL"],
    "MUTUAL_FUND": ["VFIAX", "VTSAX", "AGTHX", "DODGX", "PRGFX", "VBMFX", "VEMAX"],
    "INDEX": ["^GSPC", "^NDX", "^DJI", "^RUT", "^FTSE", "^N225"],
}
BENCH_SYMBOL = {"EQUITY": "SPY", "ETF": "SPY", "BOND": "SPY",
                "CRYPTO": "BTC-USD", "FOREX": "UUP", "COMMODITY": "DBC",
                # added with the four classes that were being skipped
                "FUTURES": "ES=F", "PENNY_STOCK": "IWM",
                "MUTUAL_FUND": "SPY", "INDEX": "SPY"}

# Commodity FUTURES series from Yahoo carry unadjusted contract rolls: ZC=F
# prints -23.6 % on July 15 of three separate years and CL=F closed NEGATIVE on
# 2020-04-20, which makes pct_change meaningless. An ETF is the instrument this
# desk can actually hold, and its NAV absorbs the roll, so the price series has
# no roll gap. H-223/H-224 (pre-registered) measure the class here instead.
COMMODITY_INVESTABLE = ["GLD", "SLV", "CPER", "DBA", "USO", "UNG", "CORN", "WEAT"]
MAX_LEVERAGE = 4.0   # cap on vol-matching; beyond this the comparison is fiction


def fetch(sym: str) -> pd.DataFrame | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    safe = sym.replace("=", "_").replace("-", "_").replace("^", "")
    p = CACHE / f"{safe}.csv"
    if p.exists():
        try:
            df = pd.read_csv(p, index_col=0, parse_dates=True)
            if len(df) > 200 and "close" in df.columns:
                return df
        except Exception:
            pass
    try:
        import yfinance as yf
        df = yf.download(sym, start=START, progress=False, auto_adjust=True)
    except Exception as exc:  # network / ticker problems must not kill the run
        print(f"  ! fetch {sym}: {exc}")
        return None
    if df is None or len(df) == 0:
        print(f"  ! fetch {sym}: empty")
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]).lower() for c in df.columns]
    else:
        df.columns = [str(c).lower() for c in df.columns]
    keep = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    df = df[keep].dropna(subset=["close"])
    df.to_csv(p)
    return df


# ---------------------------------------------------------------- strategies
def tsmom(df: pd.DataFrame, lookback: int, skip: int, cost_bps: float,
          long_short: bool = False) -> tuple[pd.Series, pd.Series]:
    px = df["close"].astype(float)
    ret = px.pct_change(fill_method=None)
    mom = px.shift(skip) / px.shift(skip + lookback) - 1.0
    pos = np.sign(mom) if long_short else (mom > 0).astype(float)
    pos = pos.fillna(0.0)
    gross = pos.shift(1) * ret
    turn = (pos - pos.shift(1)).abs()
    return (gross - turn * cost_bps / 1e4).fillna(0.0), pos


def xsmom(closes: pd.DataFrame, lookback: int, top_k: int, cost_bps: float,
          rebal_days: int = 21,
          abs_filter: bool = False) -> tuple[pd.Series, pd.DataFrame]:
    rets = closes.pct_change(fill_method=None)
    mom = closes.pct_change(lookback, fill_method=None)
    # NaN = "carry the previous weight"; an explicit 0.0 = "not selected now".
    # The earlier version replaced 0.0 with NaN before ffill, so a name that
    # dropped out of the top-k KEPT ITS WEIGHT FOREVER: exposure drifted above 1,
    # positions never closed, and the reported edge was an accounting artifact.
    w = pd.DataFrame(np.nan, index=closes.index, columns=closes.columns)
    for i in range(lookback + 1, len(closes), rebal_days):
        row = mom.iloc[i].dropna()
        if abs_filter:
            row = row[row > 0]     # absolute momentum: a falling name is not held
        if len(row) < top_k:
            continue
        w.iloc[i, :] = 0.0                     # every non-selected name goes flat
        for c in row.nlargest(top_k).index:
            w.iloc[i, w.columns.get_loc(c)] = 1.0 / top_k
    w = w.ffill().fillna(0.0)
    exposure = w.sum(axis=1)
    if float(exposure.max()) > 1.0001:
        raise AssertionError(
            f"xsmom exposure {float(exposure.max()):.4f} > 1 — weights leaked "
            "instead of going flat")
    gross = (w.shift(1) * rets).sum(axis=1)
    turn = (w - w.shift(1)).abs().sum(axis=1)
    return (gross - turn * cost_bps / 1e4).fillna(0.0), w


def xsmom_ls(closes: pd.DataFrame, lookback: int, top_k: int, cost_bps: float,
             rebal_days: int = 21) -> tuple[pd.Series, pd.DataFrame]:
    """Dollar-neutral cross-sectional momentum: long top_k, short bottom_k.

    Long-only cross-sectional momentum cannot beat buy-and-hold of a rising
    universe -- it is beta plus extra trading -- which is why every long-only
    cell outside EQUITY died on the benchmark gate. Removing the market leg
    turns the cell into a factor bet: gross exposure 1, net exposure 0, so
    `excess_vs_bench_bps` measures the factor instead of leverage.
    """
    rets = closes.pct_change(fill_method=None)
    mom = closes.pct_change(lookback, fill_method=None)
    w = pd.DataFrame(np.nan, index=closes.index, columns=closes.columns)
    for i in range(lookback + 1, len(closes), rebal_days):
        row = mom.iloc[i].dropna()
        if len(row) < 2 * top_k:
            continue
        w.iloc[i, :] = 0.0
        for c in row.nlargest(top_k).index:
            w.iloc[i, w.columns.get_loc(c)] = 0.5 / top_k
        for c in row.nsmallest(top_k).index:
            w.iloc[i, w.columns.get_loc(c)] = -0.5 / top_k
    w = w.ffill().fillna(0.0)
    gross = w.abs().sum(axis=1)
    if float(gross.max()) > 1.0001:
        raise AssertionError(f"xsmom_ls gross {float(gross.max()):.4f} > 1")
    if float(w.sum(axis=1).abs().max()) > 1e-9:
        raise AssertionError("xsmom_ls is not dollar-neutral")
    gross_ret = (w.shift(1) * rets).sum(axis=1)
    turn = (w - w.shift(1)).abs().sum(axis=1)
    return (gross_ret - turn * cost_bps / 1e4).fillna(0.0), w


def funding_carry_daily(path: Path | None = None,
                        daily_drag_bps: float = 1.0) -> pd.Series:
    """Daily return of a delta-neutral perp/spot funding-carry book.

    A delta-neutral book earns the funding print every settlement and carries
    ~no price exposure, so its return IS the funding it collects. Measured from
    the archived prints (data/funding_rate_archive/*.jsonl), not synthesised.
    `daily_drag_bps` covers margin rebalancing, which a hedged book must do; it
    is the only honest recurring cost, and the 2x variant doubles it.
    """
    frames = {}
    # Prefer the deep ccxt archive when it exists (years of history beats the
    # 9-month OKX snapshot, which cannot score a carry cell at all).
    if path is None:
        for cand in (Path("data/funding_rate_archive_ccxt"),
                     Path("data/funding_rate_archive")):
            if list(cand.glob("*.jsonl")):
                path = cand
                break
        path = path or Path("data/funding_rate_archive")
    for p in sorted(Path(path).glob("*.jsonl")):
        rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        if not rows:
            continue
        frames[p.stem] = pd.Series(
            {pd.Timestamp(int(r["funding_time_ms"]), unit="ms"): float(r["funding_rate"])
             for r in rows}).sort_index()
    if not frames:
        return pd.Series(dtype=float)
    df = pd.concat(frames, axis=1).sort_index()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    daily = df.groupby(df.index.normalize()).sum().mean(axis=1)   # equal-weight book
    return (daily - daily_drag_bps / 1e4).dropna()


def reversal(df: pd.DataFrame, drop_pct: float = -0.03, hold: int = 5,
             cost_bps: float = 10) -> tuple[pd.Series, pd.Series]:
    px = df["close"].astype(float)
    ret = px.pct_change(fill_method=None)
    move5 = px.pct_change(5)
    pos = pd.Series(0.0, index=px.index)
    held = 0
    for i in range(6, len(px)):
        if held > 0:
            pos.iloc[i] = 1.0
            held -= 1
        elif move5.iloc[i] <= drop_pct:
            pos.iloc[i] = 1.0
            held = hold - 1
    gross = pos.shift(1) * ret
    turn = (pos - pos.shift(1)).abs()
    return (gross - turn * cost_bps / 1e4).fillna(0.0), pos


def pead_trades(sym: str, df: pd.DataFrame, cost_bps: float = 10,
                min_surprise: float = 5.0, hold: int = 20) -> list[float]:
    """Long after a positive earnings surprise, hold N sessions. Real event dates."""
    try:
        import yfinance as yf
        ed = yf.Ticker(sym).earnings_dates
    except Exception:
        return []
    if ed is None or len(ed) == 0:
        return []
    col = next((c for c in ed.columns if "Surprise" in str(c)), None)
    if col is None:
        return []
    surprises = ed[col].dropna()
    px = df["close"].astype(float)
    open_px = df["open"].astype(float) if "open" in df else px
    idx = px.index
    out: list[float] = []
    for dt, surp in surprises.items():
        if surp is None or float(surp) < min_surprise:
            continue
        naive = pd.Timestamp(dt)
        naive = naive.tz_localize(None) if naive.tzinfo else naive
        after = idx[idx > naive]
        if len(after) < hold + 2:
            continue
        entry_t = after[0]
        entry_i = idx.get_loc(entry_t)
        exit_i = entry_i + hold
        if exit_i >= len(idx):
            continue
        entry = float(open_px.iloc[entry_i])
        exit_ = float(px.iloc[exit_i])
        if entry <= 0:
            continue
        out.append(exit_ / entry - 1.0 - 2 * cost_bps / 1e4)
    return out


# ------------------------------------------------------------------ statistics
def segment_trades(pos: pd.Series, px: pd.Series, cost_bps: float) -> list[float]:
    trades, side, entry, in_pos = [], 0.0, 0.0, False
    for i in range(len(pos)):
        p = float(pos.iloc[i])
        price = float(px.iloc[i])
        if p != 0 and not in_pos:
            in_pos, entry, side = True, price, np.sign(p)
        elif in_pos and (p == 0 or np.sign(p) != side):
            trades.append(side * (price / entry - 1.0) - 2 * cost_bps / 1e4)
            if p == 0:
                in_pos = False
            else:
                entry, side = price, np.sign(p)
    if in_pos:
        trades.append(side * (float(px.iloc[-1]) / entry - 1.0) - 2 * cost_bps / 1e4)
    return trades



def monthly_trades(net: pd.Series) -> list[float]:
    """Trades for an always-invested portfolio: one bucket per calendar month.

    A portfolio that rebalances but never goes flat produces exactly one
    segment-trade for its whole life, which makes PF meaningless (n=1, PF=inf).
    Monthly buckets keep the same idea -- win/loss ratio of held periods -- with
    an honest n.
    """
    # groupby on the period instead of resample("ME"): the "ME" alias only
    # exists in pandas >= 2.2, and CI installs an older pandas where it raises
    # "Invalid frequency: ME". to_period("M") is stable across both.
    m = (1.0 + net.fillna(0.0)).groupby(net.index.to_period("M")).prod() - 1.0
    return [float(x) for x in m.dropna().to_numpy()]


def classify(c: dict) -> str:
    """Gate label. A low-n cell is labelled, never dropped."""
    if c.get("n_trades") is not None and c["n_trades"] < 30:
        return "INSUFFICIENT_N"
    h = c["split_half_bps"]
    ex = c.get("excess_vs_bench_bps")
    if (c["boot_ci_lb_bps"] > 0 and c["boot_ci_lb_2x_cost_bps"] > 0
            and h[0] > 0 and h[1] > 0 and (ex is None or ex > 0)):
        return "PASSES_G2_G3_G5"
    if c["boot_ci_lb_bps"] > 0:
        return "FAILS_COST_OR_STABILITY"
    return "REFUTED_OR_WEAK"


def sue12_trades(sym: str, df: pd.DataFrame, cost_bps: float = 10,
                 min_sue: float = 1.0, hold: int = 20, min_history: int = 8):
    """PEAD scored on multi-quarter surprise history (SUE), not one print.

    Kaczmarek & Zaremba (2025) find the drift revives when 12 quarters of
    standardized unexpected earnings are used, with the largest gains in large
    caps where the latest print is priced instantly and older ones are not.
    yfinance exposes ~24 quarters, so each surprise is z-scored against all PRIOR
    surprises (never future ones) and entries need sue >= min_sue.
    """
    try:
        import yfinance as yf
        ed = yf.Ticker(sym).earnings_dates
    except Exception:
        return []
    if ed is None or len(ed) == 0:
        return []
    col = next((c for c in ed.columns if "Surprise" in str(c)), None)
    if col is None:
        return []
    ser = ed[col].dropna()
    if len(ser) == 0:
        return []
    ser = ser.sort_index()
    px = df["close"].astype(float)
    open_px = df["open"].astype(float) if "open" in df else px
    idx = px.index
    out = []
    for i in range(min_history, len(ser)):
        prior = ser.iloc[:i]
        sd = float(prior.std(ddof=1))
        if not sd or sd <= 0:
            continue
        sue = (float(ser.iloc[i]) - float(prior.mean())) / sd
        if sue < min_sue:
            continue
        dt_ = pd.Timestamp(ser.index[i])
        dt_ = dt_.tz_localize(None) if dt_.tzinfo else dt_
        after = idx[idx > dt_]
        if len(after) < hold + 2:
            continue
        entry_i = idx.get_loc(after[0])
        exit_i = entry_i + hold
        if exit_i >= len(idx):
            continue
        entry = float(open_px.iloc[entry_i])
        if entry <= 0:
            continue
        ret = float(px.iloc[exit_i]) / entry - 1.0 - 2 * cost_bps / 1e4
        out.append((ret, idx[entry_i], idx[exit_i], sue))
    return out


def record_trades(cell_id, cls, name, trades, trades_2x, bench,
                  cells, event_returns):
    """Stats for an event-driven cell: one observation per trade, T = n_trades."""
    if len(trades) < 5:
        print(f"  - {cell_id} {name}: only {len(trades)} events, skipped")
        return
    v = np.asarray(trades, dtype=float)
    v2 = np.asarray(trades_2x, dtype=float)
    lo, hi = block_bootstrap(v, block=1)
    h = len(v) // 2
    rec = {"id": cell_id, "asset_class": cls, "name": name,
           "basis": "per_trade", "n_days": int(len(v)), "n_trades": int(len(v)),
           "win_rate": round(100 * float((v > 0).mean()), 2),
           "profit_factor": round(profit_factor(list(v)), 4),
           "mean_trade_pct": round(float(v.mean()), 4),
           "mean_daily_bps": round(1e4 * float(v.mean()), 3),
           "ann_sharpe": None,
           "boot_ci_lb_bps": round(1e4 * lo, 3),
           "boot_ci_ub_bps": round(1e4 * hi, 3),
           "boot_ci_lb_2x_cost_bps": round(1e4 * float(block_bootstrap(v2, block=1)[0]), 3),
           "split_half_bps": [round(1e4 * float(v[:h].mean()), 3),
                              round(1e4 * float(v[h:].mean()), 3)],
           "bench_mean_bps": round(1e4 * float(np.mean(bench)), 3) if bench else None,
           "excess_vs_bench_bps": round(1e4 * float(np.mean(v - np.asarray(bench))), 3) if bench else None,
           "sr_daily": round(sharpe(v), 5)}
    rec["status"] = classify(rec)
    cells.append(rec)
    event_returns[cell_id] = v   # NOT ret_series: event rows have no daily index
    print(f"  + {cell_id} {cls:9s} {name:22s} events={rec['n_trades']:4d} "
          f"PF={rec['profit_factor']} ci_lb={rec['boot_ci_lb_bps']}bps")


def profit_factor(trades: list[float]) -> float:
    gains = sum(t for t in trades if t > 0)
    losses = -sum(t for t in trades if t < 0)
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def block_bootstrap(x: np.ndarray, n: int = 2000, block: int = 5, seed: int = 7,
                    q: float = 0.05) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    T = len(x)
    if T < block * 4:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    k = max(1, T // block)
    means = np.empty(n)
    for j in range(n):
        starts = rng.integers(0, T - block, size=k)
        means[j] = np.concatenate([x[s:s + block] for s in starts])[:T].mean()
    return float(np.quantile(means, q / 2)), float(np.quantile(means, 1 - q / 2))


def sharpe(x: np.ndarray) -> float:
    sd = float(np.std(x, ddof=1))
    return 0.0 if sd == 0 else float(np.mean(x) / sd)


def expected_max_sr(n_trials: int, var_sr: float) -> float:
    if n_trials < 2 or var_sr <= 0:
        return 0.0
    g = 0.5772156649
    return math.sqrt(var_sr) * ((1 - g) * sps.norm.ppf(1 - 1.0 / n_trials)
                                + g * sps.norm.ppf(1 - 1.0 / (n_trials * math.e)))


def dsr(x: np.ndarray, sr0: float) -> tuple[float, float, float, float]:
    T = len(x)
    sr = sharpe(x)
    sk = float(sps.skew(x))
    ku = float(sps.kurtosis(x, fisher=False))
    denom = math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4.0 * sr * sr))
    val = float(sps.norm.cdf((sr - sr0) * math.sqrt(max(1, T - 1)) / denom))
    return val, sr, sk, ku


def min_trl(x: np.ndarray, sr0: float, conf: float = 0.95) -> float:
    sr = sharpe(x)
    sk = float(sps.skew(x))
    ku = float(sps.kurtosis(x, fisher=False))
    var = max(1e-12, 1 - sk * sr + (ku - 1) / 4.0 * sr * sr)
    edge = sr - sr0
    if edge <= 0:
        return float("inf")
    return 1.0 + var * (sps.norm.ppf(conf) / edge) ** 2


def pbo_cscv(mat: np.ndarray, s_blocks: int = 16, trials: int = 200,
             seed: int = 11) -> float:
    """Probability of backtest overfitting (Bailey et al.) via CSCV on a T x N matrix."""
    T, N = mat.shape
    if N < 2 or T < s_blocks * 4:
        return float("nan")
    edges = np.linspace(0, T, s_blocks + 1).astype(int)
    blocks = [mat[edges[i]:edges[i + 1]] for i in range(s_blocks)]
    rng = np.random.default_rng(seed)
    half = s_blocks // 2
    lambdas = []
    for _ in range(trials):
        pick = rng.permutation(s_blocks)[:half]
        is_mat = np.concatenate([blocks[i] for i in pick])
        oos_mat = np.concatenate([blocks[i] for i in range(s_blocks) if i not in pick])
        is_sr = np.array([sharpe(is_mat[:, j]) for j in range(N)])
        oos_sr = np.array([sharpe(oos_mat[:, j]) for j in range(N)])
        best = int(np.argmax(is_sr))
        rank = int((oos_sr <= oos_sr[best]).sum())
        w = rank / (N + 1.0)
        lambdas.append(math.log(w / (1 - w)) if 0 < w < 1 else -10.0)
    return float(np.mean(np.array(lambdas) <= 0))


def commodity_integrity(threshold: float = 0.08) -> list[dict]:
    """Flag roll/pricing artefacts that make a commodity series unmeasurable.

    Found on 2026-11-22: ZC=F prints -23.6/-17.4/-16.8/-13.1 % on July 15/17 of
    four different years (contract roll), and CL=F carried a NEGATIVE close
    (-37.63 on 2020-04-20) which makes pct_change meaningless. A series like that
    cannot refute or confirm a strategy; it has to be repaired first.
    """
    out = []
    for sym in UNIVERSES.get("COMMODITY", []):
        safe = sym.replace("=", "_").replace("-", "_")
        path = CACHE / f"{safe}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        if "close" not in df:
            continue
        c = df["close"].astype(float)
        r = c.pct_change(fill_method=None)
        spikes = r[r.abs() > threshold]
        by_md: dict[tuple[int, int], list[int]] = {}
        for d in spikes.index:
            by_md.setdefault((d.month, d.day), []).append(d.year)
        recurring = {f"{m:02d}-{day:02d}": sorted({y for y in ys})
                     for (m, day), ys in by_md.items() if len({y for y in ys}) > 1}
        out.append({"symbol": sym, "rows": int(len(c)),
                    "negative_prices": int((c <= 0).sum()),
                    "spikes_gt_threshold": int(len(spikes)),
                    "max_abs_ret_pct": round(float(r.abs().max() * 100), 1),
                    "recurring_month_day_spikes": recurring,
                    "usable": not ((c <= 0).any() or recurring)})
    return out


def mdd(x) -> float:
    """Max drawdown of a daily return series (negative fraction)."""
    eq = np.cumprod(1.0 + np.asarray(x, dtype=float))
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def cagr(x) -> float:
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return float("nan")
    return float(np.prod(1.0 + x) ** (252.0 / len(x)) - 1.0)


def matched_vol_block(x: np.ndarray, b: np.ndarray,
                      max_lev: float = MAX_LEVERAGE) -> dict:
    """Benchmark excess once the strategy is levered to the benchmark's own vol.

    G6 as first written compares raw mean daily return against buy-and-hold of
    the same universe. That yardstick cannot be passed by any de-risking rule:
    holding cash part of the time must lower the mean return even when it
    improves return per unit of risk. This block reports the other comparison a
    fund manager actually uses -- scale the strategy to the benchmark's ex-post
    volatility (capped at MAX_LEVERAGE so the result stays reachable), then
    compare. It is labelled G6b and kept separate from the strict gate: nothing
    is promoted to 'passes' on G6b alone.
    """
    s_vol = float(np.std(x, ddof=1) * math.sqrt(252))
    b_vol = float(np.std(b, ddof=1) * math.sqrt(252))
    lev = 0.0 if s_vol <= 0 else min(b_vol / s_vol, max_lev)
    matched = lev * x - b
    lo, _hi = block_bootstrap(matched)
    h = len(matched) // 2
    return {
        "strategy_vol_pct": round(100 * s_vol, 2),
        "bench_vol_pct": round(100 * b_vol, 2),
        "leverage_to_match": round(lev, 3),
        "matched_excess_bps": round(1e4 * float(matched.mean()), 3),
        "matched_ci_lb_bps": round(1e4 * lo, 3),
        "matched_halves_bps": [round(1e4 * float(matched[:h].mean()), 3),
                               round(1e4 * float(matched[h:].mean()), 3)],
        "cagr_pct": round(100 * cagr(x), 2),
        "bench_cagr_pct": round(100 * cagr(b), 2),
        "levered_cagr_pct": round(100 * cagr(lev * x), 2),
        "mdd_pct": round(100 * mdd(x), 2),
        "bench_mdd_pct": round(100 * mdd(b), 2),
        "levered_mdd_pct": round(100 * mdd(lev * x), 2),
        "risk_adj_pass": bool(matched.mean() > 0 and lo > 0
                              and matched[:h].mean() > 0
                              and matched[h:].mean() > 0),
    }


# ------------------------------------------------------------------------ run
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/per_class_edge_2026-11-22.json")
    ap.add_argument("--md", default="reports/per_class_edge_2026-11-22.md")
    ap.add_argument("--n-trials", type=int, default=26)
    args = ap.parse_args()

    print("fetching universes...")
    data: dict[str, dict[str, pd.DataFrame]] = {}
    for cls, syms in UNIVERSES.items():
        data[cls] = {}
        for s in syms:
            df = fetch(s)
            if df is not None and len(df) > 200:
                data[cls][s] = df
        print(f"  {cls}: {len(data[cls])}/{len(syms)} symbols")

    cells: list[dict] = []
    ret_series: dict[str, pd.Series] = {}
    event_returns: dict[str, np.ndarray] = {}

    def record(cell_id, cls, name, net: pd.Series, net2x: pd.Series,
               trades: list[float], pos: pd.Series, px: pd.Series,
               bench: pd.Series, extra: dict | None = None):
        arr = net.to_numpy(dtype=float)
        barr = bench.reindex(net.index).fillna(0.0).to_numpy(dtype=float)
        keep = ~np.isnan(arr)          # x and b must stay row-aligned
        x, b = arr[keep], barr[keep]
        if len(x) < 60:
            print(f"  - {cell_id} {name}: too few days ({len(x)}), skipped")
            return
        lo, hi = block_bootstrap(x)
        rec = {
            "id": cell_id, "asset_class": cls, "name": name,
            "n_days": int(len(x)), "n_trades": len(trades),
            "win_rate": round(100 * sum(1 for t in trades if t > 0) / len(trades), 2) if trades else None,
            "profit_factor": round(profit_factor(trades), 4) if trades else None,
            "mean_trade_pct": round(100 * float(np.mean(trades)), 4) if trades else None,
            "mean_daily_bps": round(1e4 * float(np.mean(x)), 3),
            "ann_sharpe": round(sharpe(x) * math.sqrt(252), 3),
            "boot_ci_lb_bps": round(1e4 * lo, 3),
            "boot_ci_ub_bps": round(1e4 * hi, 3),
            "boot_ci_lb_2x_cost_bps": round(1e4 * block_bootstrap(
                net2x.to_numpy(dtype=float)[~np.isnan(net2x.to_numpy(dtype=float))])[0], 3),
            "split_half_bps": [
                round(1e4 * float(np.mean(x[: len(x) // 2])), 3),
                round(1e4 * float(np.mean(x[len(x) // 2:])), 3),
            ],
            "bench_mean_bps": round(1e4 * float(np.mean(b)), 3),
            "excess_vs_bench_bps": round(1e4 * float(np.mean(x - b)), 3),
        }
        rec["status"] = classify(rec)
        rec.update(matched_vol_block(x, b))   # G6b, reported separately
        if extra:
            rec.update(extra)
        cells.append(rec)
        ret_series[cell_id] = net
        print(f"  + {cell_id} {cls:9s} {name:22s} n={rec['n_trades']:4d} "
              f"PF={rec['profit_factor']} ci_lb={rec['boot_ci_lb_bps']}bps")

    for cls in ("EQUITY", "ETF", "CRYPTO", "FOREX", "COMMODITY", "BOND",
            "FUTURES", "PENNY_STOCK", "MUTUAL_FUND", "INDEX"):
        syms = [s for s in data[cls]]
        if not syms:
            continue
        closes = pd.concat({s: data[cls][s]["close"] for s in syms}, axis=1).dropna(how="all")
        bench_sym = BENCH_SYMBOL[cls]
        bdf = fetch(bench_sym)
        if bdf is None and bench_sym in data[cls]:
            bdf = data[cls][bench_sym]
        bench_ret = (bdf["close"].pct_change().fillna(0.0)
                     if bdf is not None else pd.Series(0.0, index=closes.index))

        if cls == "EQUITY":
            cell_id, name = "H-200", "tsmom_12_1_long_flat"
            net, pos = tsmom(data[cls][syms[0]], 252, 21, 10)
            net2, _ = tsmom(data[cls][syms[0]], 252, 21, 20)
            record(cell_id, cls, name, net, net2,
                   segment_trades(pos, data[cls][syms[0]]["close"], 10), pos,
                   data[cls][syms[0]]["close"], bench_ret)
            for s in syms[1:]:
                n2, p2 = tsmom(data[cls][s], 252, 21, 10)
                n2x, _ = tsmom(data[cls][s], 252, 21, 20)
                record(f"H-200:{s}", cls, f"tsmom_12_1 [{s}]", n2, n2x,
                       segment_trades(p2, data[cls][s]["close"], 10), p2,
                       data[cls][s]["close"], bench_ret)

            pead, pead2, pead_bench = [], [], []
            for s in syms:
                for ret, d_in, d_out, _sue in sue12_trades(s, data[cls][s], cost_bps=10):
                    pead.append(ret * 100.0)
                    pead2.append(ret * 100.0 - 0.20)   # +10 bps each way
                    try:
                        seg = bench_ret.loc[(bench_ret.index > d_in) & (bench_ret.index <= d_out)]
                        pead_bench.append(float((1.0 + seg).prod() - 1.0) * 100.0)
                    except Exception:
                        pead_bench.append(0.0)
            record_trades("H-222", cls, "pead_sue12_20d", pead, pead2, pead_bench,
                          cells, event_returns)

        if cls in ("EQUITY", "ETF"):
            net, w = xsmom(closes, 126, 3, 10)
            net2, _ = xsmom(closes, 126, 3, 20)
            agg_pos = (w.sum(axis=1) > 0).astype(float)
            record("H-201" if cls == "EQUITY" else "H-205", cls,
                   "xsmom_top3_6m", net, net2,
                   monthly_trades(net), agg_pos,
                   closes.mean(axis=1), bench_ret)

        if cls == "ETF":
            # H-225 (pre-registered): dual momentum across stock/bond/gold.
            gem = {s: fetch(s) for s in ("SPY", "QQQ", "IWM", "EFA",
                                        "EEM", "TLT", "GLD")}
            gem = {s: d for s, d in gem.items() if d is not None and len(d) > 200}
            if len(gem) >= 5:
                gc = pd.concat({s: d["close"] for s, d in gem.items()},
                               axis=1).dropna(how="all")
                g1, _ = xsmom(gc, 252, 2, 10, abs_filter=True)
                g2, _ = xsmom(gc, 252, 2, 20, abs_filter=True)
                record("H-225", cls, "dual_momentum_top2_12m", g1, g2,
                       monthly_trades(g1), (g1 > 0).astype(float),
                       gc.mean(axis=1), bench_ret,
                       extra={"instruments": sorted(gem)})

        if cls == "EQUITY":
            # H-226 (pre-registered): the same momentum signal with the market
            # leg stripped out, so a pass means factor, not beta.
            nls, wls = xsmom_ls(closes, 126, 3, 10)
            nls2, _ = xsmom_ls(closes, 126, 3, 20)
            record("H-226", cls, "xsmom_ls_top3_bottom3_6m", nls, nls2,
                   monthly_trades(nls), (wls > 0).sum(axis=1).astype(float),
                   closes.mean(axis=1), bench_ret)

        if cls == "CRYPTO":
            net, pos = tsmom(data[cls]["BTC-USD"], 126, 7, 20)
            net2, _ = tsmom(data[cls]["BTC-USD"], 126, 7, 40)
            record("H-206", cls, "tsmom_6m_long_flat", net, net2,
                   segment_trades(pos, data[cls]["BTC-USD"]["close"], 20), pos,
                   data[cls]["BTC-USD"]["close"], bench_ret)
            net, w = xsmom(closes, 63, 3, 20)
            net2, _ = xsmom(closes, 63, 3, 40)
            agg_pos = (w.sum(axis=1) > 0).astype(float)
            record("H-207", cls, "xsmom_top3_3m", net, net2,
                   monthly_trades(net), agg_pos,
                   closes.mean(axis=1), bench_ret)

            # H-227 (pre-registered): dollar-neutral crypto momentum.
            nls, wls = xsmom_ls(closes, 63, 2, 20)
            nls2, _ = xsmom_ls(closes, 63, 2, 40)
            record("H-227", cls, "xsmom_ls_top2_bottom2_3m", nls, nls2,
                   monthly_trades(nls), (wls > 0).sum(axis=1).astype(float),
                   closes.mean(axis=1), bench_ret)

            # H-228 (pre-registered): funding carry, the only non-beta crypto
            # return stream available from local data.
            fc = funding_carry_daily()
            if len(fc) > 60:
                btc = fetch("BTC-USD")
                bret_fc = (btc["close"].pct_change().fillna(0.0)
                           if btc is not None else pd.Series(0.0, index=fc.index))
                fc2 = fc - 1e-4      # 2x-cost variant: +1 bps/day extra drag
                record("H-228", cls, "funding_carry_delta_neutral", fc, fc2,
                       monthly_trades(fc), (fc > 0).astype(float), fc, bret_fc,
                       extra={"instrument": "perp/spot delta-neutral",
                              "funding_days": int(len(fc)),
                              "source": "data/funding_rate_archive/*.jsonl"})
            else:
                print(f"  - H-228: funding archive too short ({len(fc)} days)")

        if cls == "FOREX":
            nets = []
            for s in syms:
                n, p = tsmom(data[cls][s], 252, 21, 5, long_short=True)
                n2, _ = tsmom(data[cls][s], 252, 21, 10, long_short=True)
                record(f"H-208:{s}", cls, f"tsmom_ls [{s}]", n, n2,
                       segment_trades(p, data[cls][s]["close"], 5), p,
                       data[cls][s]["close"], bench_ret)
                nets.append(n)
            if nets:
                port = pd.concat(nets, axis=1).mean(axis=1)
                port2 = port  # 2x cost already carried by the 10bps variants above
                record("H-208", cls, "tsmom_ls_portfolio", port, port2,
                       segment_trades((port > 0).astype(float), closes.mean(axis=1), 5),
                       (port > 0).astype(float), closes.mean(axis=1), bench_ret)
            net, w = xsmom(closes, 63, 2, 5)
            net2, _ = xsmom(closes, 63, 2, 10)
            agg_pos = (w.sum(axis=1) > 0).astype(float)
            record("H-209", cls, "xsmom_top2_3m", net, net2,
                   monthly_trades(net), agg_pos,
                   closes.mean(axis=1), bench_ret)

        if cls == "COMMODITY":
            net, pos = tsmom(data[cls][syms[0]], 252, 21, 15)
            net2, _ = tsmom(data[cls][syms[0]], 252, 21, 30)
            record("H-210", cls, f"tsmom_12_1 [{syms[0]}]", net, net2,
                   segment_trades(pos, data[cls][syms[0]]["close"], 15), pos,
                   data[cls][syms[0]]["close"], bench_ret)
            net, w = xsmom(closes, 126, 2, 15)
            net2, _ = xsmom(closes, 126, 2, 30)
            agg_pos = (w.sum(axis=1) > 0).astype(float)
            record("H-211", cls, "xsmom_top2_6m", net, net2,
                   monthly_trades(net), agg_pos,
                   closes.mean(axis=1), bench_ret)

            # ---- repaired measurement (H-223/H-224): investable ETFs, no roll gap
            etfs = {s: fetch(s) for s in COMMODITY_INVESTABLE}
            etfs = {s: d for s, d in etfs.items() if d is not None and len(d) > 200}
            print(f"  COMMODITY investable ETFs: {len(etfs)}/{len(COMMODITY_INVESTABLE)}")
            if len(etfs) >= 5:
                n1s, n2s = [], []
                for s, d in etfs.items():
                    a, _ = tsmom(d, 252, 21, 15)
                    a2, _ = tsmom(d, 252, 21, 30)
                    n1s.append(a)
                    n2s.append(a2)
                port = pd.concat(n1s, axis=1).mean(axis=1).dropna()
                port2 = pd.concat(n2s, axis=1).mean(axis=1).dropna()
                record("H-223", cls, "tsmom_12_1_etf_basket", port, port2,
                       monthly_trades(port), (port > 0).astype(float),
                       port, bench_ret,
                       extra={"instruments": sorted(etfs)})
                ecl = pd.concat({s: d["close"] for s, d in etfs.items()},
                                axis=1).dropna(how="all")
                nx, wx = xsmom(ecl, 126, 3, 15)
                nx2, _ = xsmom(ecl, 126, 3, 30)
                record("H-224", cls, "xsmom_top3_6m_etf", nx, nx2,
                       monthly_trades(nx), (wx.sum(axis=1) > 0).astype(float),
                       ecl.mean(axis=1), bench_ret,
                       extra={"instruments": sorted(etfs)})

        if cls == "BOND":
            net, pos = tsmom(data[cls]["TLT"], 252, 21, 10)
            net2, _ = tsmom(data[cls]["TLT"], 252, 21, 20)
            record("H-212", cls, "tsmom_12_1 [TLT]", net, net2,
                   segment_trades(pos, data[cls]["TLT"]["close"], 10), pos,
                   data[cls]["TLT"]["close"], bench_ret)
            net, w = xsmom(closes, 126, 2, 10)
            net2, _ = xsmom(closes, 126, 2, 20)
            agg_pos = (w.sum(axis=1) > 0).astype(float)
            record("H-213", cls, "xsmom_top2_6m", net, net2,
                   monthly_trades(net), agg_pos,
                   closes.mean(axis=1), bench_ret)

        if cls in ("FUTURES", "PENNY_STOCK", "MUTUAL_FUND", "INDEX"):
            tsmom_ids = {"FUTURES": "H-214", "PENNY_STOCK": "H-215",
                         "MUTUAL_FUND": "H-216", "INDEX": "H-217"}
            xsmom_ids = {"FUTURES": "H-218", "PENNY_STOCK": "H-219",
                         "MUTUAL_FUND": "H-220", "INDEX": "H-221"}
            sym = syms[0]
            lb = 126 if cls == "FUTURES" else 252
            net, pos = tsmom(data[cls][sym], lb, 21, 10)
            net2, _ = tsmom(data[cls][sym], lb, 21, 20)
            record(tsmom_ids[cls], cls, f"tsmom_12_1 [{sym}]", net, net2,
                   segment_trades(pos, data[cls][sym]["close"], 10), pos,
                   data[cls][sym]["close"], bench_ret)
            net, w = xsmom(closes, 126, 2, 10)
            net2, _ = xsmom(closes, 126, 2, 20)
            agg_pos = (w.sum(axis=1) > 0).astype(float)
            record(xsmom_ids[cls], cls, "xsmom_top2_6m", net, net2,
                   monthly_trades(net), agg_pos, closes.mean(axis=1), bench_ret)

    # ---- multiplicity: DSR needs the scatter of all trials' Sharpes
    if not cells:
        print("no cells produced; nothing to score")
        return 1
    def series_for(c):
        return (ret_series[c["id"]].to_numpy(dtype=float)
                if c["id"] in ret_series else event_returns[c["id"]])

    srs = np.array([sharpe(np.asarray(series_for(c), dtype=float)) for c in cells])
    sr0 = expected_max_sr(args.n_trials, float(np.var(srs, ddof=1)) if len(srs) > 1 else 0.0)
    # PBO is computed on the daily-return cells only; an event cell has no shared
    # time axis, so including it would silently align unrelated observations.
    mat = pd.concat(list(ret_series.values()), axis=1).fillna(0.0).to_numpy(dtype=float)
    pbo = pbo_cscv(mat)

    for c in cells:
        x = np.asarray(series_for(c), dtype=float)
        x = x[~np.isnan(x)]
        d, sr, sk, ku = dsr(x, sr0)
        c.update({"dsr": round(d, 4), "sr_daily": round(sr, 5),
                  "min_trl_days": (None if math.isinf(min_trl(x, sr0))
                                   else round(min_trl(x, sr0), 1))})

    integrity = commodity_integrity()
    bad = {r["symbol"] for r in integrity if not r["usable"]}
    # Only the cells built ON the contaminated futures series are flagged. The
    # ETF cells (H-223/H-224) must not inherit a failure they do not have.
    futures_cells = {"H-210", "H-211"}
    for c in cells:
        if c["asset_class"] == "COMMODITY":
            c["integrity_flag"] = bool(c["id"] in futures_cells and bad)
    out = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "data_integrity": {"commodity": integrity,
                           "unusable_symbols": sorted(bad)},
        "window": {"start": str(min(r.index.min() for r in ret_series.values()).date()),
                   "end": str(max(r.index.max() for r in ret_series.values()).date())},
        "n_trials_declared": args.n_trials,
        "expected_max_sharpe_daily": round(sr0, 5),
        "pbo_cscv": None if math.isnan(pbo) else round(pbo, 4),
        "cost_model_bps_round_trip": {"EQUITY": 20, "ETF": 20, "CRYPTO": 40,
                                      "FOREX": 10, "COMMODITY": 30, "BOND": 20},
        "cells": sorted(cells, key=lambda r: -(r.get("mean_daily_bps") or -1)),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))

    # ---- markdown
    lines = ["# Per-class edge evidence, 2026-11-22",
             "",
             f"Window {out['window']['start']} → {out['window']['end']} · "
             f"declared trials {args.n_trials} · expected-max daily Sharpe {sr0:.5f} · "
             f"PBO(CSCV) {out['pbo_cscv']}",
             "",
             "| id | class | cell | gate | n trades | PF | mean trade % | daily bps | CI-LB bps | CI-LB @2x | halves bps | excess vs bench | DSR |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in out["cells"]:
        lines.append(
            f"| {c['id']} | {c['asset_class']} | {c['name']} | {c.get('status')} | {c['n_trades']} | "
            f"{c['profit_factor']} | {c['mean_trade_pct']} | {c['mean_daily_bps']} | "
            f"{c['boot_ci_lb_bps']} | {c['boot_ci_lb_2x_cost_bps']} | "
            f"{c['split_half_bps']} | {c['excess_vs_bench_bps']} | {c['dsr']} |")
    lines += ["", "A cell is only evidence of an edge when CI-LB > 0, CI-LB@2x > 0, "
              "both halves > 0, DSR >= 0.95, and excess-vs-bench > 0. "
              "Nothing else counts, whatever the PF looks like."]
    Path(args.md).write_text("\n".join(lines) + "\n")
    print(f"\nwrote {args.out} and {args.md} ({len(cells)} cells, PBO={out['pbo_cscv']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
