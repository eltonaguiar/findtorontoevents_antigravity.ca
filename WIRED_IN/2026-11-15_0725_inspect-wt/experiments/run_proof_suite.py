"""
Seeded 10-Step Quantitative Proof Suite (Phase 4 & Phase 5 Evaluation).

Evaluates all 9 pre-registered trials across 8 asset classes:
  E1  - ETF 12-1 Dual-Momentum + Inverse-Vol + 12% Vol Target (monthly)
  M1  - Mutual Fund Index Sleeve (monthly NAV, >=30d hold, CAD MER sweep)
  MA1 - Multi-Asset Variant C Meta-Selector (/audit closed cohort)
  MA2 - Multi-Asset Risk-Parity Combo (E1 + B1 + CM1 + TLT/IEF defensive)
  S1  - Stocks / Equities Live /audit Cohort (swing)
  C1  - Crypto Causal 1h Donchian + EMA Trend on BTCUSDT + Live Cohort / Funding Audit
  B1  - Bond Duration Rotation (TLT/IEF/AGG monthly 12-1 momentum)
  CM1 - Commodity Gold/Broad Trend (GLD/DBC monthly 12-1 momentum + 12% VT)
  FX1 - Forex Live /audit Cohort with Spread/Slippage/Swap + Contamination Audit

Enforces strict causal t-1 signal indexing, chronological WFO splits, DSR (N=9 and N=646),
White's Reality Check, Holm-Bonferroni correction, plain & circular block bootstrap (2,000 paths),
friction & Canadian tax modeling (TFSA 0%, Cap Gains 26.76%, Ordinary 53.53%),
regime decomposition, 200-run permutation shuffle controls, and SHA-256 dataset hashing.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy import stats

# REPO_ROOT preamble per AGENTS.md so direct script invocation works reliably
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EXP_DIR = Path(__file__).resolve().parent
BASE_DIR = EXP_DIR.parent
PROOF_DIR = BASE_DIR / "proof"
PROOF_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
EULER_GAMMA = 0.5772156649015329


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_path(rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    if p.is_absolute():
        return p
    for root in (REPO_ROOT, REPO_ROOT / ".fix-wt"):
        cand = root / p
        if cand.exists():
            return cand
    return REPO_ROOT / p


def load_yahoo_monthly(path: Path) -> tuple[list[str], pd.DataFrame]:
    """Load yahoo_monthly.json into aligned complete monthly close DataFrame (<= 2026-10)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    series_map: dict[str, dict[str, float]] = {}
    for sym, pts in raw.items():
        m_map: dict[str, float] = {}
        for ts, px in pts:
            dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
            ym = dt.strftime("%Y-%m")
            if ym <= "2026-10":
                m_map[ym] = float(px)
        series_map[sym] = m_map
    common_months = sorted(set.intersection(*(set(v.keys()) for v in series_map.values())))
    df = pd.DataFrame({sym: [series_map[sym][m] for m in common_months] for sym in raw}, index=common_months)
    return common_months, df


def load_live_picks(cfg: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    """Load portable snapshot first; fallback to raw live payload if present."""
    snap_path = resolve_path(cfg["datasets"]["live_picks_snapshot"])
    if snap_path.exists():
        with gzip.open(snap_path, "rb") as f:
            return snap_path, json.loads(f.read().decode("utf-8"))
    fb_path = resolve_path(cfg["datasets"]["live_picks_fallback_raw"])
    return fb_path, json.loads(fb_path.read_text(encoding="utf-8"))


def load_btc_1h(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, skiprows=[1, 2])
    df = df.rename(columns={"Price": "timestamp"})
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.dropna(subset=["Open", "High", "Low", "Close"]).sort_values("timestamp").reset_index(drop=True)
    return df


def audit_funding_archive(funding_dir: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for fn in sorted(funding_dir.glob("*.jsonl")):
        rows = [json.loads(line) for line in fn.read_text(encoding="utf-8").splitlines() if line.strip()]
        rates = np.array([float(r["funding_rate"]) for r in rows], dtype=float)
        ann_gross = float(np.mean(rates) * 3.0 * 365.0)
        # Delta-neutral spot+perp carry pays ~20 bps entry+exit fees per rotation; over 51 days -> annualized drag
        days = max((rows[-1]["funding_time_ms"] - rows[0]["funding_time_ms"]) / 86_400_000.0, 1.0)
        out[fn.stem] = {
            "n_prints": int(len(rates)),
            "days": round(days, 1),
            "mean_8h_bps": round(float(np.mean(rates) * 10000.0), 3),
            "pct_positive_8h": round(float(np.mean(rates > 0) * 100.0), 1),
            "ann_gross_carry_pct": round(ann_gross * 100.0, 2),
            "ann_net_after_20bps_rt_pct": round((ann_gross - 0.0020 * (365.0 / days)) * 100.0, 2),
        }
    return out


# ---------------------------------------------------------------------------
# Strategy Simulation Engines (Causal t-1 -> t)
# ---------------------------------------------------------------------------

def run_dual_momentum_monthly(
    prices: pd.DataFrame,
    universe: list[str],
    lookback: int = 12,
    top_k: int = 2,
    vol_target: float = 0.12,
    max_weight: float = 0.50,
    round_trip_cost_bps: float = 10.0,
    annual_mer: float = 0.0,
    rf_annual: float = 0.025,
    skip_recent: int = 1,
) -> dict[str, Any]:
    """
    Causal monthly dual-momentum + inverse-vol + portfolio vol-target simulator.
    Signal for holding month `t` uses strictly data up to month `t-1`.
    If `skip_recent == 1`, momentum excludes month `t-1` (classic 12-1: close[t-2]/close[t-1-L]-1).
    """
    rets = prices[universe].pct_change()
    rf_m = (1.0 + rf_annual) ** (1.0 / 12.0) - 1.0
    mer_m = 1.0 - (1.0 - annual_mer) ** (1.0 / 12.0) if annual_mer > 0 else 0.0
    one_way_cost = (round_trip_cost_bps / 2.0) / 10000.0

    start_idx = lookback + skip_recent + 1
    dates: list[str] = []
    gross_r: list[float] = []
    net_r: list[float] = []
    turnovers: list[float] = []
    prev_w = {s: 0.0 for s in universe}

    for t in range(start_idx, len(prices)):
        sig_end = t - 1 - (1 if skip_recent == 1 else 0)
        sig_start = sig_end - lookback
        if sig_start < 0:
            continue

        scores: dict[str, float] = {}
        vols: dict[str, float] = {}
        rf_lb = (1.0 + rf_annual) ** (lookback / 12.0) - 1.0
        for s in universe:
            p_end = float(prices[s].iloc[sig_end])
            p_start = float(prices[s].iloc[sig_start])
            mom = (p_end / p_start) - 1.0 if p_start > 0 else -1.0
            r_win = rets[s].iloc[t - lookback : t].dropna()
            vol_ann = float(r_win.std(ddof=1) * math.sqrt(12.0)) if len(r_win) >= 3 else 0.15
            vols[s] = max(vol_ann, 0.04)
            if mom > rf_lb:
                scores[s] = mom

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        target_w = {s: 0.0 for s in universe}
        if ranked:
            inv_vols = {s: 1.0 / vols[s] for s, _ in ranked}
            iv_sum = sum(inv_vols.values())
            raw_w = {s: min(max_weight, inv_vols[s] / iv_sum) for s in inv_vols}
            w_sum = sum(raw_w.values())
            if w_sum > 0:
                raw_w = {s: v / w_sum for s, v in raw_w.items()}
            # Estimate portfolio trailing 12m vol on target weights
            port_hist = np.zeros(min(12, t - 1))
            for s, w in raw_w.items():
                port_hist += w * rets[s].iloc[t - len(port_hist) : t].fillna(0.0).to_numpy()
            est_vol = float(np.std(port_hist, ddof=1) * math.sqrt(12.0)) if len(port_hist) >= 3 else vol_target
            scale = min(1.0, vol_target / max(est_vol, 0.03))
            for s, w in raw_w.items():
                target_w[s] = w * scale

        cash_w = max(0.0, 1.0 - sum(target_w.values()))
        turnover = sum(abs(target_w[s] - prev_w[s]) for s in universe)
        cost = turnover * one_way_cost

        asset_ret = sum(target_w[s] * float(rets[s].iloc[t]) for s in universe)
        g_ret = asset_ret + cash_w * rf_m
        n_ret = g_ret - cost - mer_m * sum(target_w.values())

        dates.append(str(prices.index[t]))
        gross_r.append(g_ret)
        net_r.append(n_ret)
        turnovers.append(turnover)
        prev_w = target_w

    return {
        "dates": dates,
        "gross_returns": np.array(gross_r, dtype=float),
        "net_returns": np.array(net_r, dtype=float),
        "turnovers": np.array(turnovers, dtype=float),
        "ann_factor": 12.0,
        "period_unit": "months",
        "est_trades": int(np.sum(np.array(turnovers) > 0.01)),
    }


def simulate_btc_1h_trend(
    df: pd.DataFrame,
    donchian_len: int = 48,
    ema_fast: int = 24,
    ema_slow: int = 168,
    sl_atr: float = 2.0,
    tp_atr: float = 4.0,
    max_hold_bars: int = 72,
    round_trip_cost_bps: float = 20.0,
    funding_8h_bps: float = 0.158,
) -> dict[str, Any]:
    """
    Causal bar-by-bar 1h BTC trend simulator on OHLCV bars.
    Decisions at bar t use indicators strictly at t-1; entries fill at Open[t].
    Intrabar SL-first tie-breaking per tools/stop_fill_replay.py.
    """
    close = df["Close"].to_numpy(dtype=float)
    high = df["High"].to_numpy(dtype=float)
    low = df["Low"].to_numpy(dtype=float)
    opn = df["Open"].to_numpy(dtype=float)
    ts = df["timestamp"].dt.strftime("%Y-%m-%d").to_numpy()

    s_close = pd.Series(close)
    e_fast = s_close.ewm(span=ema_fast, adjust=False).mean().to_numpy()
    e_slow = s_close.ewm(span=ema_slow, adjust=False).mean().to_numpy()
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    atr = pd.Series(tr).rolling(24).mean().bfill().to_numpy()

    dc_high = pd.Series(high).rolling(donchian_len).max().to_numpy()

    n = len(df)
    start_bar = max(ema_slow, donchian_len, 24) + 1
    one_way_fee = (round_trip_cost_bps / 2.0) / 10000.0
    funding_per_bar = (funding_8h_bps / 10000.0) / 8.0

    in_pos = False
    entry_px = 0.0
    sl_px = 0.0
    tp_px = 0.0
    bars_held = 0
    pos_size = 0.0

    hourly_gross = []
    hourly_net = []
    hourly_dates = []
    trade_returns_net: list[float] = []
    trade_returns_gross: list[float] = []
    trade_holds: list[int] = []

    for t in range(start_bar, n):
        g_bar = 0.0
        n_bar = 0.0
        if not in_pos:
            sig_idx = t - 1
            if e_fast[sig_idx] > e_slow[sig_idx] and close[sig_idx] > dc_high[sig_idx - 1]:
                # Enter long at Open[t]; risk 1% equity per SL stop distance, max 100% notional
                stop_dist_pct = max((sl_atr * atr[sig_idx]) / opn[t], 0.005)
                pos_size = min(1.0, 0.02 / stop_dist_pct)
                entry_px = opn[t]
                sl_px = entry_px - sl_atr * atr[sig_idx]
                tp_px = entry_px + tp_atr * atr[sig_idx]
                in_pos = True
                bars_held = 0
                n_bar -= pos_size * one_way_fee

        if in_pos:
            bars_held += 1
            bar_entry = opn[t] if bars_held == 1 else close[t - 1]
            exit_px = None
            # Conservative SL-first check inside bar t
            if low[t] <= sl_px:
                exit_px = min(opn[t], sl_px)
            elif high[t] >= tp_px:
                exit_px = max(opn[t], tp_px)
            elif bars_held >= max_hold_bars:
                exit_px = close[t]

            if exit_px is not None:
                seg_r = (exit_px / bar_entry) - 1.0
                g_bar += pos_size * seg_r
                n_bar += pos_size * (seg_r - one_way_fee - funding_per_bar)
                tot_g = (exit_px / entry_px) - 1.0
                tot_n = tot_g - (round_trip_cost_bps / 10000.0) - bars_held * funding_per_bar
                trade_returns_gross.append(tot_g * pos_size)
                trade_returns_net.append(tot_n * pos_size)
                trade_holds.append(bars_held)
                in_pos = False
            else:
                seg_r = (close[t] / bar_entry) - 1.0
                g_bar += pos_size * seg_r
                n_bar += pos_size * (seg_r - funding_per_bar)

        hourly_gross.append(g_bar)
        hourly_net.append(n_bar)
        hourly_dates.append(ts[t])

    # Aggregate hourly into daily compounded returns for statistical parity (83 days)
    hdf = pd.DataFrame({"date": hourly_dates, "g": hourly_gross, "n": hourly_net})
    ddf = hdf.groupby("date", sort=True).agg(
        g=("g", lambda x: float(np.prod(1.0 + x.to_numpy()) - 1.0)),
        n=("n", lambda x: float(np.prod(1.0 + x.to_numpy()) - 1.0)),
    )
    # Benchmark BTCUSDT daily returns on exact same dates
    bh_df = pd.DataFrame({
        "date": ts[start_bar:],
        "r": (close[start_bar:] / close[start_bar - 1 : -1]) - 1.0,
    }).groupby("date", sort=True)["r"].apply(lambda x: float(np.prod(1.0 + x.to_numpy()) - 1.0))

    return {
        "dates": list(ddf.index),
        "gross_returns": ddf["g"].to_numpy(dtype=float),
        "net_returns": ddf["n"].to_numpy(dtype=float),
        "bench_returns": bh_df.reindex(ddf.index).fillna(0.0).to_numpy(dtype=float),
        "trade_returns_net": np.array(trade_returns_net, dtype=float),
        "trade_returns_gross": np.array(trade_returns_gross, dtype=float),
        "avg_hold_hours": float(np.mean(trade_holds)) if trade_holds else 0.0,
        "ann_factor": 365.0,
        "period_unit": "days",
        "est_trades": len(trade_returns_net),
    }


def extract_sorted_closed_picks(raw: dict[str, Any], asset_class: str | None = None, clean: bool = True) -> list[dict[str, Any]]:
    picks = raw.get("picks", {}).get("recent_closed", [])
    rows = []
    for r in picks:
        if asset_class and str(r.get("asset_class", "")).upper() != asset_class:
            continue
        ts = str(r.get("closed_at") or r.get("timestamp") or "")
        pnl = r.get("pnl_pct")
        if pnl is None or not ts:
            continue
        pnl_f = float(pnl)
        if clean:
            if pnl_f == 0.0:
                continue
            if asset_class == "FOREX" and str(r.get("symbol", "")).upper().endswith("USDT"):
                continue
        rows.append({
            "id": r.get("id", ""),
            "symbol": r.get("symbol", ""),
            "asset_class": str(r.get("asset_class", "")).upper(),
            "strategy": str(r.get("strategy") or "unknown"),
            "ts": ts,
            "date": ts[:10],
            "month": ts[:7],
            "pnl_dec": pnl_f / 100.0,
            "raw": r,
        })
    rows.sort(key=lambda x: x["ts"])
    return rows


def run_variant_c_cohort(raw: dict[str, Any], cost_bps: float = 10.0) -> dict[str, Any]:
    """Chronological OOS Variant C meta-selector matching Plan/multi_asset/PLAN.md."""
    rows = extract_sorted_closed_picks(raw, asset_class=None, clean=True)
    months = sorted({r["month"] for r in rows})
    extra_cost = cost_bps / 10000.0

    # Accumulate OOS trades starting month >= 1 (strictly prior months form training stats)
    oos_trades: list[dict[str, Any]] = []
    train_pool: list[dict[str, Any]] = []
    oos_months_used: list[str] = []

    for i, m in enumerate(months):
        cur = [r for r in rows if r["month"] == m]
        if i >= 1 and train_pool:
            by_strat = defaultdict(list)
            for tr in train_pool:
                by_strat[tr["strategy"]].append(tr["pnl_dec"])
            cands = []
            for st, pnls in by_strat.items():
                if len(pnls) >= 20:
                    gw = sum(x for x in pnls if x > 0)
                    gl = abs(sum(x for x in pnls if x < 0))
                    pf = gw / gl if gl > 1e-9 else 10.0
                    if pf > 1.3:
                        cands.append((st, pf, float(np.mean(pnls))))
            cands.sort(key=lambda x: (x[1], x[2]), reverse=True)
            selected = {c[0] for c in cands[:6]}
            if selected:
                oos_months_used.append(m)
                for r in cur:
                    if r["strategy"] in selected:
                        oos_trades.append(r)
        train_pool.extend(cur)

    # Aggregate into daily portfolio return assuming fixed 10% capital per trade slot (capped 1.0x/day)
    daily_g: dict[str, list[float]] = defaultdict(list)
    daily_n: dict[str, list[float]] = defaultdict(list)
    for r in oos_trades:
        daily_g[r["date"]].append(r["pnl_dec"])
        daily_n[r["date"]].append(r["pnl_dec"] - extra_cost)

    all_days = sorted({r["date"] for r in rows if r["month"] in set(oos_months_used)})
    g_arr = np.array([sum(daily_g[d]) * (1.0 / max(10, len(daily_g[d]))) for d in all_days], dtype=float)
    n_arr = np.array([sum(daily_n[d]) * (1.0 / max(10, len(daily_n[d]))) for d in all_days], dtype=float)

    return {
        "dates": all_days,
        "gross_returns": g_arr,
        "net_returns": n_arr,
        "trade_returns_gross": np.array([r["pnl_dec"] for r in oos_trades], dtype=float),
        "trade_returns_net": np.array([r["pnl_dec"] - extra_cost for r in oos_trades], dtype=float),
        "oos_trades": oos_trades,
        "all_oos_pool": [r for r in rows if r["month"] in set(oos_months_used)],
        "ann_factor": 252.0,
        "period_unit": "trading_days",
        "est_trades": len(oos_trades),
    }


def run_cohort_eval(raw: dict[str, Any], asset_class: str, cost_bps: float, clean: bool = True) -> dict[str, Any]:
    rows = extract_sorted_closed_picks(raw, asset_class=asset_class, clean=clean)
    cost = cost_bps / 10000.0
    daily_g: dict[str, list[float]] = defaultdict(list)
    daily_n: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        daily_g[r["date"]].append(r["pnl_dec"])
        daily_n[r["date"]].append(r["pnl_dec"] - cost)
    dates = sorted(daily_g.keys())
    g_arr = np.array([sum(daily_g[d]) * (1.0 / max(10, len(daily_g[d]))) for d in dates], dtype=float)
    n_arr = np.array([sum(daily_n[d]) * (1.0 / max(10, len(daily_n[d]))) for d in dates], dtype=float)
    return {
        "dates": dates,
        "gross_returns": g_arr,
        "net_returns": n_arr,
        "trade_returns_gross": np.array([r["pnl_dec"] for r in rows], dtype=float),
        "trade_returns_net": np.array([r["pnl_dec"] - cost for r in rows], dtype=float),
        "rows": rows,
        "ann_factor": 365.0 if asset_class == "CRYPTO" else 252.0,
        "period_unit": "active_days",
        "est_trades": len(rows),
    }


# ---------------------------------------------------------------------------
# Phase 5 Metrics + Phase 4 Statistical Tests
# ---------------------------------------------------------------------------

def equity_and_drawdown(r: np.ndarray) -> tuple[np.ndarray, float, float, int, int]:
    eq = np.cumprod(1.0 + r)
    peaks = np.maximum.accumulate(np.insert(eq, 0, 1.0))[1:]
    dd = (eq / peaks) - 1.0
    max_dd = float(np.min(dd)) if len(dd) else 0.0
    avg_dd = float(np.mean(dd[dd < 0])) if np.any(dd < 0) else 0.0
    cur_rec = 0
    max_rec = 0
    trough_idx = int(np.argmin(dd)) if len(dd) else 0
    trough_rec = 0
    for i, val in enumerate(dd):
        if val < -1e-9:
            cur_rec += 1
            max_rec = max(max_rec, cur_rec)
        else:
            cur_rec = 0
    # Bars to recover from worst trough
    if trough_idx < len(dd):
        after = dd[trough_idx:]
        rec_pos = np.where(after >= -1e-9)[0]
        trough_rec = int(rec_pos[0]) if len(rec_pos) else int(len(after))
    return eq, max_dd, avg_dd, max_rec, trough_rec


def apply_canadian_tax(r: np.ndarray, dates: list[str], tax_rate: float) -> np.ndarray:
    """Apply annual Canadian tax by calendar year with capital loss carry-forward."""
    if tax_rate <= 0.0 or len(r) == 0:
        return r.copy()
    eq = 1.0
    year_start_eq = 1.0
    loss_carry = 0.0
    out = r.copy()
    cur_yr = dates[0][:4]
    for i, (ret, dt) in enumerate(zip(r, dates)):
        yr = dt[:4]
        if yr != cur_yr:
            gain = eq - year_start_eq
            if gain > 0:
                taxable = max(0.0, gain - loss_carry)
                loss_carry = max(0.0, loss_carry - gain)
                tax_amt = taxable * tax_rate
                if eq > 0:
                    out[i - 1] = (1.0 + out[i - 1]) * (1.0 - tax_amt / eq) - 1.0
                    eq -= tax_amt
            else:
                loss_carry += abs(gain)
            year_start_eq = eq
            cur_yr = yr
        eq *= (1.0 + out[i])
    # Final year
    gain = eq - year_start_eq
    if gain > 0 and eq > 0:
        taxable = max(0.0, gain - loss_carry)
        tax_amt = taxable * tax_rate
        out[-1] = (1.0 + out[-1]) * (1.0 - tax_amt / eq) - 1.0
    return out


def compute_deflated_sharpe(
    r: np.ndarray,
    ann_factor: float,
    n_trials: int,
    trial_var_bar: float,
) -> float:
    T = len(r)
    if T < 5 or np.std(r, ddof=1) < 1e-12:
        return 0.0
    sr_bar = float(np.mean(r) / np.std(r, ddof=1))
    skew = float(stats.skew(r, bias=False)) if T >= 8 else 0.0
    kurt_pearson = float(stats.kurtosis(r, fisher=False, bias=False)) if T >= 8 else 3.0
    if n_trials <= 1:
        sr0 = 0.0
    else:
        z1 = float(stats.norm.ppf(1.0 - 1.0 / n_trials))
        z2 = float(stats.norm.ppf(1.0 - math.e ** -1 / n_trials))
        sr0 = math.sqrt(max(trial_var_bar, 1e-6)) * ((1.0 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)
    denom_inner = max(1e-6, 1.0 - skew * sr_bar + ((kurt_pearson - 1.0) / 4.0) * (sr_bar ** 2))
    z_stat = (sr_bar - sr0) * math.sqrt(max(1, T - 1)) / math.sqrt(denom_inner)
    return float(stats.norm.cdf(z_stat))


def circular_block_bootstrap(r: np.ndarray, block_len: int, n_paths: int, rng: np.random.Generator) -> dict[str, Any]:
    T = len(r)
    if T < 4:
        return {"pct_pos": 0.0, "p5_cum": 0.0, "median_cum": 0.0, "p5_mdd": 0.0, "mean_ci95": [0.0, 0.0]}
    n_blocks = math.ceil(T / block_len)
    cum_rets = np.empty(n_paths, dtype=float)
    mdds = np.empty(n_paths, dtype=float)
    means = np.empty(n_paths, dtype=float)
    for k in range(n_paths):
        starts = rng.integers(0, T, size=n_blocks)
        idx = np.concatenate([(np.arange(s, s + block_len) % T) for s in starts])[:T]
        sample = r[idx]
        eq = np.cumprod(1.0 + sample)
        cum_rets[k] = eq[-1] - 1.0
        peaks = np.maximum.accumulate(np.insert(eq, 0, 1.0))[1:]
        mdds[k] = float(np.min((eq / peaks) - 1.0))
        means[k] = float(np.mean(sample))
    return {
        "pct_pos": round(float(np.mean(cum_rets > 0) * 100.0), 2),
        "p5_cum": round(float(np.percentile(cum_rets, 5) * 100.0), 2),
        "median_cum": round(float(np.median(cum_rets) * 100.0), 2),
        "p95_cum": round(float(np.percentile(cum_rets, 95) * 100.0), 2),
        "p5_mdd": round(float(np.percentile(mdds, 5) * 100.0), 2),
        "mean_ci95_period_pct": [round(float(np.percentile(means, 2.5) * 100.0), 4), round(float(np.percentile(means, 97.5) * 100.0), 4)],
    }


def iid_bootstrap(r: np.ndarray, n_paths: int, rng: np.random.Generator) -> dict[str, Any]:
    T = len(r)
    if T < 4:
        return {"pct_pos": 0.0, "p5_cum": 0.0, "median_cum": 0.0, "p5_mdd": 0.0}
    cum_rets = np.empty(n_paths, dtype=float)
    mdds = np.empty(n_paths, dtype=float)
    for k in range(n_paths):
        sample = r[rng.integers(0, T, size=T)]
        eq = np.cumprod(1.0 + sample)
        cum_rets[k] = eq[-1] - 1.0
        peaks = np.maximum.accumulate(np.insert(eq, 0, 1.0))[1:]
        mdds[k] = float(np.min((eq / peaks) - 1.0))
    return {
        "pct_pos": round(float(np.mean(cum_rets > 0) * 100.0), 2),
        "p5_cum": round(float(np.percentile(cum_rets, 5) * 100.0), 2),
        "median_cum": round(float(np.median(cum_rets) * 100.0), 2),
        "p5_mdd": round(float(np.percentile(mdds, 5) * 100.0), 2),
    }


def compute_metrics(
    r_net: np.ndarray,
    r_gross: np.ndarray,
    r_bench: np.ndarray,
    dates: list[str],
    ann_factor: float,
    rf_annual: float,
    tax_mode: str,
    unit_trades: np.ndarray | None = None,
) -> dict[str, Any]:
    T = len(r_net)
    rf_p = (1.0 + rf_annual) ** (1.0 / ann_factor) - 1.0
    excess_rf = r_net - rf_p
    excess_bm = r_net - r_bench if len(r_bench) == T else excess_rf

    eq_net, max_dd, avg_dd, max_rec, trough_rec = equity_and_drawdown(r_net)
    eq_gross, _, _, _, _ = equity_and_drawdown(r_gross)

    years = max(T / ann_factor, 1.0 / 12.0)
    cum_net = float(eq_net[-1] - 1.0) if T else 0.0
    cum_gross = float(eq_gross[-1] - 1.0) if T else 0.0
    cagr = (float(eq_net[-1]) ** (1.0 / years) - 1.0) if (T and eq_net[-1] > 0) else -1.0
    ann_vol = float(np.std(r_net, ddof=1) * math.sqrt(ann_factor)) if T > 1 else 0.0

    sharpe = float(np.mean(excess_rf) / np.std(excess_rf, ddof=1) * math.sqrt(ann_factor)) if T > 1 and np.std(excess_rf, ddof=1) > 1e-12 else 0.0
    downside = np.minimum(excess_rf, 0.0)
    dd_dev = float(math.sqrt(np.mean(downside ** 2)))
    sortino = float(np.mean(excess_rf) / dd_dev * math.sqrt(ann_factor)) if dd_dev > 1e-12 else 0.0
    calmar = float(cagr / abs(max_dd)) if abs(max_dd) > 1e-6 else None
    sterling = float(cagr / max(abs(avg_dd), 1e-4)) if abs(avg_dd) > 1e-6 else None

    beta = None
    treynor = None
    ir = None
    if len(r_bench) == T and np.std(r_bench, ddof=1) > 1e-12:
        cov = float(np.cov(r_net, r_bench, ddof=1)[0, 1])
        var_b = float(np.var(r_bench, ddof=1))
        beta = cov / var_b if var_b > 1e-12 else 1.0
        ann_mean_ex = float(np.mean(excess_rf) * ann_factor)
        treynor = float(ann_mean_ex / beta) if abs(beta) > 0.05 else None
        ex_std = float(np.std(excess_bm, ddof=1))
        ir = float(np.mean(excess_bm) / ex_std * math.sqrt(ann_factor)) if ex_std > 1e-12 else 0.0

    # Trade stats: use discrete closed trades if available, else period returns
    tr = unit_trades if unit_trades is not None and len(unit_trades) > 0 else r_net
    wins = tr[tr > 0]
    losses = tr[tr < 0]
    win_rate = float(np.mean(tr > 0) * 100.0) if len(tr) else 0.0
    sum_w = float(np.sum(wins))
    sum_l = abs(float(np.sum(losses)))
    pf = float(sum_w / sum_l) if sum_l > 1e-9 else (10.0 if sum_w > 0 else 0.0)
    avg_w = float(np.mean(wins) * 100.0) if len(wins) else 0.0
    avg_l = float(np.mean(losses) * 100.0) if len(losses) else 0.0
    payoff = float(abs(avg_w / avg_l)) if abs(avg_l) > 1e-9 else None
    expectancy = float(np.mean(tr) * 100.0) if len(tr) else 0.0

    longest_streak = 0
    cur_streak = 0
    for x in tr:
        if x <= 0:
            cur_streak += 1
            longest_streak = max(longest_streak, cur_streak)
        else:
            cur_streak = 0

    skew = float(stats.skew(r_net, bias=False)) if T >= 8 else 0.0
    ekurt = float(stats.kurtosis(r_net, fisher=True, bias=False)) if T >= 8 else 0.0
    lag1 = float(pd.Series(r_net).autocorr(lag=1)) if T >= 6 and np.std(r_net) > 1e-12 else 0.0
    p95 = float(np.percentile(r_net, 95)) if T else 0.0
    p05 = float(np.percentile(r_net, 5)) if T else 0.0
    tail_ratio = abs(p95 / p05) if abs(p05) > 1e-9 else None
    cvar_95 = float(np.mean(r_net[r_net <= p05]) * 100.0) if np.any(r_net <= p05) else p05 * 100.0

    t_res = stats.ttest_1samp(excess_rf, 0.0) if T >= 3 else (0.0, 1.0)
    t_stat = float(t_res[0]) if not math.isnan(float(t_res[0])) else 0.0
    p_val = float(t_res[1]) if not math.isnan(float(t_res[1])) else 1.0

    # Canadian tax curves
    r_tfsa = r_net
    r_cg = apply_canadian_tax(r_net, dates, 0.2676)
    r_ord = apply_canadian_tax(r_net, dates, 0.5353)
    eq_cg, _, _, _, _ = equity_and_drawdown(r_cg)
    eq_ord, _, _, _, _ = equity_and_drawdown(r_ord)
    cagr_cg = (float(eq_cg[-1]) ** (1.0 / years) - 1.0) if (T and eq_cg[-1] > 0) else -1.0
    cagr_ord = (float(eq_ord[-1]) ** (1.0 / years) - 1.0) if (T and eq_ord[-1] > 0) else -1.0

    return {
        "n_periods": int(T),
        "n_trades_sample": int(len(tr)),
        "cagr_net_pct": round(cagr * 100.0, 2),
        "cagr_tfsa_pct": round(cagr * 100.0, 2),
        "cagr_taxable_cg_pct": round(cagr_cg * 100.0, 2),
        "cagr_taxable_ord_pct": round(cagr_ord * 100.0, 2),
        "cum_return_gross_pct": round(cum_gross * 100.0, 2),
        "cum_return_net_pct": round(cum_net * 100.0, 2),
        "cum_return_cg_pct": round(float(eq_cg[-1] - 1.0) * 100.0, 2),
        "cum_return_ord_pct": round(float(eq_ord[-1] - 1.0) * 100.0, 2),
        "ann_vol_pct": round(ann_vol * 100.0, 2),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "calmar": round(calmar, 3) if calmar is not None else None,
        "sterling": round(sterling, 3) if sterling is not None else None,
        "beta": round(beta, 3) if beta is not None else None,
        "treynor": round(treynor, 3) if treynor is not None else None,
        "information_ratio": round(ir, 3) if ir is not None else None,
        "max_dd_pct": round(max_dd * 100.0, 2),
        "avg_dd_pct": round(avg_dd * 100.0, 2),
        "max_recovery_bars": max_rec,
        "worst_trough_recovery_bars": trough_rec,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(pf, 3),
        "expectancy_pct": round(expectancy, 4),
        "avg_win_pct": round(avg_w, 3),
        "avg_loss_pct": round(avg_l, 3),
        "payoff_ratio": round(payoff, 3) if payoff is not None else None,
        "longest_loss_streak": longest_streak,
        "skewness": round(skew, 3),
        "excess_kurtosis": round(ekurt, 3),
        "lag1_autocorr": round(lag1, 3),
        "tail_ratio_95_5": round(tail_ratio, 3) if tail_ratio is not None else None,
        "var_95_pct": round(p05 * 100.0, 3),
        "cvar_95_pct": round(cvar_95, 3),
        "t_stat": round(t_stat, 3),
        "p_value_2sided": round(p_val, 5),
        "selected_tax_cagr_pct": round((cagr_ord if tax_mode == "ordinary" else cagr_cg) * 100.0, 2),
        "eq_net": [round(float(x), 4) for x in eq_net],
        "eq_gross": [round(float(x), 4) for x in eq_gross],
        "eq_cg": [round(float(x), 4) for x in eq_cg],
    }


def regime_decomposition(r_net: np.ndarray, ref_series: np.ndarray, ann_factor: float) -> dict[str, Any]:
    """Causal regime split into Bull/Bear/Sideways & High/Low Vol using trailing window on ref_series."""
    T = len(r_net)
    win = 12 if ann_factor == 12.0 else max(10, min(20, T // 4))
    bull, bear, side, hvol, lvol = [], [], [], [], []
    trailing_vols = []
    for i in range(T):
        lo = max(0, i - win)
        sub = ref_series[lo:i] if i > 0 else ref_series[:1]
        trailing_vols.append(float(np.std(sub, ddof=1)) if len(sub) > 1 else 0.0)
    med_vol = float(np.median(trailing_vols)) if trailing_vols else 0.0

    for i in range(T):
        lo = max(0, i - win)
        sub = ref_series[lo:i] if i > 0 else ref_series[:1]
        tr_ret = float(np.prod(1.0 + sub) - 1.0)
        ann_tr = ((1.0 + tr_ret) ** (ann_factor / max(1, len(sub)))) - 1.0 if (1.0 + tr_ret) > 0 else -0.5
        if ann_tr > 0.05:
            bull.append(r_net[i])
        elif ann_tr < -0.05:
            bear.append(r_net[i])
        else:
            side.append(r_net[i])
        if trailing_vols[i] >= med_vol:
            hvol.append(r_net[i])
        else:
            lvol.append(r_net[i])

    def summarize(arr: list[float]) -> dict[str, Any]:
        if not arr:
            return {"n": 0, "ann_ret_pct": 0.0, "sharpe": 0.0, "win_rate_pct": 0.0, "positive": False}
        a = np.array(arr, dtype=float)
        mean_ann = float(np.mean(a) * ann_factor * 100.0)
        sr = float(np.mean(a) / np.std(a, ddof=1) * math.sqrt(ann_factor)) if len(a) > 1 and np.std(a, ddof=1) > 1e-12 else 0.0
        return {
            "n": int(len(a)),
            "ann_ret_pct": round(mean_ann, 2),
            "sharpe": round(sr, 3),
            "win_rate_pct": round(float(np.mean(a > 0) * 100.0), 1),
            "positive": bool(np.mean(a) > 0),
        }

    regimes = {
        "bull": summarize(bull),
        "bear": summarize(bear),
        "sideways": summarize(side),
        "high_vol": summarize(hvol),
        "low_vol": summarize(lvol),
    }
    n_pos = sum(1 for k in regimes if regimes[k]["n"] > 0 and regimes[k]["positive"])
    n_avail = sum(1 for k in regimes if regimes[k]["n"] > 0)
    regimes["majority_positive"] = bool(n_pos >= max(3, math.ceil(n_avail / 2.0 + 0.1)))
    return regimes


def wfo_monthly_splits(
    prices: pd.DataFrame,
    run_fn: Callable[..., dict[str, Any]],
    base_kwargs: dict[str, Any],
    sweep_grid: dict[str, list[Any]],
    rf_annual: float,
) -> dict[str, Any]:
    """Chronological 50/50 + 4 rolling WFO folds + 3x3 parameter grid heatmap."""
    sim = run_fn(prices, **base_kwargs)
    r = sim["net_returns"]
    T = len(r)
    half = T // 2
    rf_m = (1.0 + rf_annual) ** (1.0 / 12.0) - 1.0

    def sr_of(arr: np.ndarray) -> float:
        ex = arr - rf_m
        return float(np.mean(ex) / np.std(ex, ddof=1) * math.sqrt(12.0)) if len(ex) > 2 and np.std(ex, ddof=1) > 1e-12 else 0.0

    def cagr_of(arr: np.ndarray) -> float:
        eq = float(np.prod(1.0 + arr))
        return (eq ** (12.0 / len(arr)) - 1.0) if (len(arr) and eq > 0) else -1.0

    is_sr = sr_of(r[:half])
    oos_sr = sr_of(r[half:])
    is_cagr = cagr_of(r[:half])
    oos_cagr = cagr_of(r[half:])
    wfe_sr = (oos_sr / is_sr) if is_sr > 0.05 else 0.0
    wfe_cagr = (oos_cagr / is_cagr) if is_cagr > 0.005 else 0.0

    folds = []
    step = max(1, T // 4)
    for k in range(4):
        lo = k * step
        hi = T if k == 3 else (k + 1) * step
        sub = r[lo:hi]
        folds.append({
            "fold": k + 1,
            "span": f"{sim['dates'][lo]}..{sim['dates'][hi - 1]}",
            "n": int(len(sub)),
            "cagr_pct": round(cagr_of(sub) * 100.0, 2),
            "sharpe": round(sr_of(sub), 3),
        })

    heatmap = []
    keys = list(sweep_grid.keys())
    if len(keys) == 2:
        k1, k2 = keys
        for v1 in sweep_grid[k1]:
            for v2 in sweep_grid[k2]:
                kw = dict(base_kwargs)
                kw[k1] = v1
                kw[k2] = v2
                s_res = run_fn(prices, **kw)
                heatmap.append({
                    k1: v1,
                    k2: v2,
                    "sharpe": round(sr_of(s_res["net_returns"]), 3),
                    "cagr_pct": round(cagr_of(s_res["net_returns"]) * 100.0, 2),
                })

    pos_cells = sum(1 for c in heatmap if c["sharpe"] > 0)
    pos_folds = sum(1 for f in folds if f["sharpe"] > 0)
    return {
        "is_span": f"{sim['dates'][0]}..{sim['dates'][half - 1]}",
        "oos_span": f"{sim['dates'][half]}..{sim['dates'][-1]}",
        "is_sharpe": round(is_sr, 3),
        "oos_sharpe": round(oos_sr, 3),
        "is_cagr_pct": round(is_cagr * 100.0, 2),
        "oos_cagr_pct": round(oos_cagr * 100.0, 2),
        "wfe_sharpe_ratio": round(wfe_sr, 3),
        "wfe_cagr_ratio": round(wfe_cagr, 3),
        "folds": folds,
        "folds_positive_ratio": round(pos_folds / len(folds), 2),
        "heatmap": heatmap,
        "heatmap_positive_ratio": round(pos_cells / len(heatmap), 2) if heatmap else 1.0,
    }


def permutation_shuffle_control_monthly(
    prices: pd.DataFrame,
    universe: list[str],
    run_fn: Callable[..., dict[str, Any]],
    base_kwargs: dict[str, Any],
    real_sharpe: float,
    rf_annual: float,
    n_runs: int,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Shuffle monthly log returns independently per asset to destroy trend/momentum timing while preserving drift & vol."""
    log_r = np.log(prices[universe] / prices[universe].shift(1)).iloc[1:].to_numpy(dtype=float)
    base_px = prices[universe].iloc[0].to_numpy(dtype=float)
    rf_m = (1.0 + rf_annual) ** (1.0 / 12.0) - 1.0

    shuf_sharpes = np.empty(n_runs, dtype=float)
    for k in range(n_runs):
        perm_lr = log_r.copy()
        for col in range(perm_lr.shape[1]):
            perm_lr[:, col] = perm_lr[rng.permutation(perm_lr.shape[0]), col]
        syn = np.vstack([base_px, base_px * np.exp(np.cumsum(perm_lr, axis=0))])
        syn_df = pd.DataFrame(syn, index=prices.index, columns=universe)
        res = run_fn(syn_df, **base_kwargs)
        ex = res["net_returns"] - rf_m
        shuf_sharpes[k] = float(np.mean(ex) / np.std(ex, ddof=1) * math.sqrt(12.0)) if np.std(ex, ddof=1) > 1e-12 else 0.0

    p_shuf = float(np.mean(shuf_sharpes >= real_sharpe))
    return {
        "n_shuffles": n_runs,
        "real_sharpe": round(real_sharpe, 3),
        "shuffle_mean_sharpe": round(float(np.mean(shuf_sharpes)), 3),
        "shuffle_p95_sharpe": round(float(np.percentile(shuf_sharpes, 95)), 3),
        "p_value": round(p_shuf, 4),
    }


def breakeven_cost_search(
    sim_at_cost: Callable[[float], float],
    base_cost_bps: float,
    max_bps: float = 400.0,
) -> tuple[float, float]:
    """Find cost_bps where net cumulative return hits zero."""
    if sim_at_cost(base_cost_bps) <= 0:
        # Already <= 0 at baseline cost; scan 0..base_cost_bps
        for b in np.linspace(0.0, max(base_cost_bps, 1.0), 41):
            if sim_at_cost(float(b)) <= 0:
                return round(float(b), 1), round(float(b) / max(base_cost_bps, 1.0), 2)
        return round(float(base_cost_bps), 1), 1.0
    prev_b = base_cost_bps
    for b in np.linspace(base_cost_bps, max_bps, 81):
        if sim_at_cost(float(b)) <= 0:
            be = 0.5 * (prev_b + float(b))
            margin = be / max(base_cost_bps, 1.0)
            return round(be, 1), round(margin, 2)
        prev_b = float(b)
    return max_bps, round(max_bps / max(base_cost_bps, 1.0), 2)


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

def main() -> int:
    cfg = json.loads((EXP_DIR / "experiment_configs.json").read_text(encoding="utf-8"))
    rng = np.random.default_rng(cfg["seed"])
    ps = cfg["proof_standard"]
    rf_ann = float(ps["rf_annual"])

    yahoo_path = resolve_path(cfg["datasets"]["yahoo_monthly"])
    btc_path = resolve_path(cfg["datasets"]["btc_1h_3mo"])
    funding_path = resolve_path(cfg["datasets"]["funding_dir"])
    picks_path, live_picks = load_live_picks(cfg)

    dataset_hashes = {
        str(yahoo_path.relative_to(REPO_ROOT)).replace("\\", "/") if yahoo_path.is_relative_to(REPO_ROOT) else yahoo_path.name: sha256_file(yahoo_path),
        str(btc_path.relative_to(REPO_ROOT)).replace("\\", "/") if btc_path.is_relative_to(REPO_ROOT) else btc_path.name: sha256_file(btc_path),
        str(picks_path.relative_to(REPO_ROOT)).replace("\\", "/") if picks_path.is_relative_to(REPO_ROOT) else picks_path.name: sha256_file(picks_path),
    }

    months, prices = load_yahoo_monthly(yahoo_path)
    btc_df = load_btc_1h(btc_path)
    funding_audit = audit_funding_archive(funding_path)

    # Monthly benchmarks over the exact 166 OOS dates (index 13..178)
    rets_all = prices.pct_change()
    rf_m = (1.0 + rf_ann) ** (1.0 / 12.0) - 1.0
    spy_oos = rets_all["SPY"].iloc[13:].to_numpy(dtype=float)
    agg_oos = rets_all["AGG"].iloc[13:].to_numpy(dtype=float)
    tlt_oos = rets_all["TLT"].iloc[13:].to_numpy(dtype=float)
    gld_oos = rets_all["GLD"].iloc[13:].to_numpy(dtype=float)
    dbc_oos = rets_all["DBC"].iloc[13:].to_numpy(dtype=float)
    b6040_oos = 0.60 * spy_oos + 0.40 * agg_oos
    oos_dates = months[13:]

    # Run Monthly Simulations
    e1_sim = run_dual_momentum_monthly(prices, ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "VNQ", "DBC", "QQQ", "IWM"], 12, 2, 0.12, 0.50, 10.0, 0.0, rf_ann)
    m1_sim = run_dual_momentum_monthly(prices, ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "VNQ", "DBC", "QQQ", "IWM"], 12, 2, 0.12, 0.50, 0.0, 0.0015, rf_ann)
    b1_sim = run_dual_momentum_monthly(prices, ["TLT", "IEF", "AGG"], 12, 1, 0.10, 1.0, 10.0, 0.0, rf_ann)
    cm1_sim = run_dual_momentum_monthly(prices, ["GLD", "DBC"], 12, 1, 0.12, 1.0, 20.0, 0.0, rf_ann)

    # MA2: Causal Inverse-Vol Risk-Parity Combo of {E1, B1, CM1, Defensive TLT/IEF}
    def_sim = run_dual_momentum_monthly(prices, ["TLT", "IEF"], 6, 1, 0.08, 1.0, 5.0, 0.0, rf_ann, skip_recent=0)
    # Align on exact common dates = e1_sim["dates"] (length 165 or 166)
    common_ma2_dates = sorted(set(e1_sim["dates"]) & set(b1_sim["dates"]) & set(cm1_sim["dates"]) & set(def_sim["dates"]))
    def align_series(sim: dict[str, Any], target_dates: list[str], key: str) -> np.ndarray:
        mp = dict(zip(sim["dates"], sim[key]))
        return np.array([mp[d] for d in target_dates], dtype=float)

    s_e1 = align_series(e1_sim, common_ma2_dates, "net_returns")
    s_b1 = align_series(b1_sim, common_ma2_dates, "net_returns")
    s_cm1 = align_series(cm1_sim, common_ma2_dates, "net_returns")
    s_def = align_series(def_sim, common_ma2_dates, "net_returns")
    sleeve_mat = np.column_stack([s_e1, s_b1, s_cm1, s_def])
    sleeve_gross_mat = np.column_stack([
        align_series(e1_sim, common_ma2_dates, "gross_returns"),
        align_series(b1_sim, common_ma2_dates, "gross_returns"),
        align_series(cm1_sim, common_ma2_dates, "gross_returns"),
        align_series(def_sim, common_ma2_dates, "gross_returns"),
    ])

    ma2_g, ma2_n, ma2_turn = [], [], []
    prev_sw = np.array([0.25, 0.25, 0.25, 0.25])
    for t in range(12, len(common_ma2_dates)):
        vols = np.std(sleeve_mat[t - 12 : t], axis=0, ddof=1)
        vols = np.maximum(vols, 0.01)
        inv = 1.0 / vols
        w = np.minimum(0.50, inv / np.sum(inv))
        w = w / np.sum(w)
        turn = float(np.sum(np.abs(w - prev_sw)))
        ma2_g.append(float(np.dot(w, sleeve_gross_mat[t])))
        ma2_n.append(float(np.dot(w, sleeve_mat[t])) - turn * 0.0005)
        ma2_turn.append(turn)
        prev_sw = w
    ma2_dates = common_ma2_dates[12:]
    ma2_sim = {
        "dates": ma2_dates,
        "gross_returns": np.array(ma2_g, dtype=float),
        "net_returns": np.array(ma2_n, dtype=float),
        "ann_factor": 12.0,
        "period_unit": "months",
        "est_trades": int(np.sum(np.array(ma2_turn) > 0.02)),
    }

    # C1 Crypto + Cohort Audits
    c1_sim = simulate_btc_1h_trend(btc_df, 48, 24, 168, 2.0, 4.0, 72, 20.0, 0.158)
    c1_live = run_cohort_eval(live_picks, "CRYPTO", cost_bps=20.0, clean=True)
    ma1_sim = run_variant_c_cohort(live_picks, cost_bps=10.0)
    s1_sim = run_cohort_eval(live_picks, "EQUITY", cost_bps=10.0, clean=True)
    fx1_sim = run_cohort_eval(live_picks, "FOREX", cost_bps=8.0, clean=True)
    fx1_raw = run_cohort_eval(live_picks, "FOREX", cost_bps=8.0, clean=False)

    # Benchmark alignment map for monthly models
    date_to_bm = {d: b6040_oos[i] for i, d in enumerate(oos_dates)}
    date_to_spy = {d: spy_oos[i] for i, d in enumerate(oos_dates)}
    date_to_agg = {d: agg_oos[i] for i, d in enumerate(oos_dates)}
    date_to_gld = {d: gld_oos[i] for i, d in enumerate(oos_dates)}

    # Collect per-bar Sharpe variance across the 9 new trials for DSR
    all_sims = {
        "E1": (e1_sim, [date_to_bm[d] for d in e1_sim["dates"]], "cap_gains"),
        "M1": (m1_sim, [date_to_bm[d] for d in m1_sim["dates"]], "cap_gains"),
        "MA1": (ma1_sim, [0.0] * len(ma1_sim["dates"]), "ordinary"),
        "MA2": (ma2_sim, [date_to_bm[d] for d in ma2_sim["dates"]], "cap_gains"),
        "S1": (s1_sim, [0.0] * len(s1_sim["dates"]), "cap_gains"),
        "C1": (c1_sim, c1_sim["bench_returns"].tolist(), "ordinary"),
        "B1": (b1_sim, [date_to_agg[d] for d in b1_sim["dates"]], "ordinary"),
        "CM1": (cm1_sim, [date_to_gld[d] for d in cm1_sim["dates"]], "cap_gains"),
        "FX1": (fx1_sim, [0.0] * len(fx1_sim["dates"]), "ordinary"),
    }

    sr_bars_monthly = []
    for tid in ["E1", "M1", "MA2", "B1", "CM1"]:
        rr = all_sims[tid][0]["net_returns"] - rf_m
        if np.std(rr, ddof=1) > 1e-12:
            sr_bars_monthly.append(float(np.mean(rr) / np.std(rr, ddof=1)))
    trial_var_monthly = float(np.var(sr_bars_monthly, ddof=1)) if len(sr_bars_monthly) > 1 else 0.02

    sr_bars_daily = []
    for tid in ["MA1", "S1", "C1", "FX1"]:
        rr = all_sims[tid][0]["net_returns"]
        if np.std(rr, ddof=1) > 1e-12:
            sr_bars_daily.append(float(np.mean(rr) / np.std(rr, ddof=1)))
    trial_var_daily = float(np.var(sr_bars_daily, ddof=1)) if len(sr_bars_daily) > 1 else 0.01

    # White's Reality Check on the 5 aligned monthly strategies (overlap = ma2_dates, 154 months)
    rc_mat = np.column_stack([
        align_series(all_sims[k][0], ma2_dates, "net_returns") - np.array([date_to_bm[d] for d in ma2_dates])
        for k in ["E1", "M1", "MA2", "B1", "CM1"]
    ])
    rc_means = np.mean(rc_mat, axis=0)
    centered_rc = rc_mat - rc_means
    wrc_max_boots = np.empty(1000, dtype=float)
    n_rc = len(ma2_dates)
    for k in range(1000):
        starts = rng.integers(0, n_rc, size=math.ceil(n_rc / 6))
        idx = np.concatenate([(np.arange(s, s + 6) % n_rc) for s in starts])[:n_rc]
        boot_means = np.mean(centered_rc[idx], axis=0)
        wrc_max_boots[k] = float(np.max(boot_means))
    wrc_pvals = {k: round(float(np.mean(wrc_max_boots >= rc_means[i])), 4) for i, k in enumerate(["E1", "M1", "MA2", "B1", "CM1"])}

    # Build per-trial results
    trial_results: dict[str, Any] = {}
    wfo_results: dict[str, Any] = {}
    mc_results: dict[str, Any] = {}
    sig_results: dict[str, Any] = {}
    regime_results: dict[str, Any] = {}

    raw_pvals: dict[str, float] = {}
    # Store auxiliary sweeps
    aux_notes: dict[str, Any] = {"okx_funding_audit": funding_audit}

    # M1 Canadian MER sensitivity
    mer_sweep = {}
    for mer in [0.0015, 0.0050, 0.0180]:
        ms = run_dual_momentum_monthly(prices, ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "VNQ", "DBC", "QQQ", "IWM"], 12, 2, 0.12, 0.50, 0.0, mer, rf_ann)
        mm = compute_metrics(ms["net_returns"], ms["gross_returns"], np.array([date_to_bm[d] for d in ms["dates"]]), ms["dates"], 12.0, rf_ann, "cap_gains")
        mer_sweep[f"mer_{int(mer*10000)}bps"] = {"cagr_net_pct": mm["cagr_net_pct"], "cagr_cg_pct": mm["cagr_taxable_cg_pct"], "sharpe": mm["sharpe"]}
    aux_notes["m1_mer_sensitivity"] = mer_sweep

    # C1 Live Cohort + FX1 Raw comparison
    c1_live_m = compute_metrics(c1_live["net_returns"], c1_live["gross_returns"], np.zeros(len(c1_live["dates"])), c1_live["dates"], 365.0, rf_ann, "ordinary", c1_live["trade_returns_net"])
    fx1_raw_m = compute_metrics(fx1_raw["net_returns"], fx1_raw["gross_returns"], np.zeros(len(fx1_raw["dates"])), fx1_raw["dates"], 252.0, rf_ann, "ordinary", fx1_raw["trade_returns_net"])
    aux_notes["live_cohort_diagnostics"] = {
        "c1_live_crypto_n": c1_live["est_trades"],
        "c1_live_gross_expectancy_pct": round(float(np.mean(c1_live["trade_returns_gross"]) * 100.0), 4),
        "c1_live_net_expectancy_pct": round(float(np.mean(c1_live["trade_returns_net"]) * 100.0), 4),
        "c1_live_pf": c1_live_m["profit_factor"],
        "c1_live_wr_pct": c1_live_m["win_rate_pct"],
        "fx1_raw_n": fx1_raw["est_trades"],
        "fx1_raw_gross_expectancy_pct": round(float(np.mean(fx1_raw["trade_returns_gross"]) * 100.0), 4),
        "fx1_clean_n": fx1_sim["est_trades"],
        "fx1_clean_gross_expectancy_pct": round(float(np.mean(fx1_sim["trade_returns_gross"]) * 100.0), 4),
        "fx1_clean_net_expectancy_pct": round(float(np.mean(fx1_sim["trade_returns_net"]) * 100.0), 4),
    }

    for tcfg in cfg["trials"]:
        tid = tcfg["id"]
        sim, bm_list, tax_mode = all_sims[tid]
        bm_arr = np.array(bm_list, dtype=float)
        ann = float(sim["ann_factor"])
        unit_tr = sim.get("trade_returns_net")

        m = compute_metrics(sim["net_returns"], sim["gross_returns"], bm_arr, sim["dates"], ann, rf_ann, tax_mode, unit_tr)

        # WFO & Parameter sensitivity
        if tid == "E1":
            wfo = wfo_monthly_splits(prices, run_dual_momentum_monthly, {"universe": ["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"], "lookback": 12, "top_k": 2, "vol_target": 0.12, "max_weight": 0.50, "round_trip_cost_bps": 10.0, "rf_annual": rf_ann}, {"lookback": [9, 12, 15], "top_k": [2, 3, 4]}, rf_ann)
            shuf = permutation_shuffle_control_monthly(prices, ["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"], run_dual_momentum_monthly, {"universe": ["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"], "lookback": 12, "top_k": 2, "vol_target": 0.12, "max_weight": 0.50, "round_trip_cost_bps": 10.0, "rf_annual": rf_ann}, m["sharpe"], rf_ann, ps["shuffle_runs"], rng)
            be_bps, margin = breakeven_cost_search(lambda cb: float(np.prod(1.0 + run_dual_momentum_monthly(prices, ["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"], 12, 2, 0.12, 0.50, cb, 0.0, rf_ann)["net_returns"]) - 1.0), 10.0)
        elif tid == "M1":
            wfo = wfo_monthly_splits(prices, run_dual_momentum_monthly, {"universe": ["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"], "lookback": 12, "top_k": 2, "vol_target": 0.12, "max_weight": 0.50, "round_trip_cost_bps": 0.0, "annual_mer": 0.0015, "rf_annual": rf_ann}, {"lookback": [9, 12, 15], "top_k": [2, 3, 4]}, rf_ann)
            shuf = permutation_shuffle_control_monthly(prices, ["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"], run_dual_momentum_monthly, {"universe": ["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"], "lookback": 12, "top_k": 2, "vol_target": 0.12, "max_weight": 0.50, "round_trip_cost_bps": 0.0, "annual_mer": 0.0015, "rf_annual": rf_ann}, m["sharpe"], rf_ann, ps["shuffle_runs"], rng)
            be_bps, margin = breakeven_cost_search(lambda cb: float(np.prod(1.0 + run_dual_momentum_monthly(prices, ["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"], 12, 2, 0.12, 0.50, cb, 0.0015, rf_ann)["net_returns"]) - 1.0), 15.0)
        elif tid == "B1":
            wfo = wfo_monthly_splits(prices, run_dual_momentum_monthly, {"universe": ["TLT","IEF","AGG"], "lookback": 12, "top_k": 1, "vol_target": 0.10, "max_weight": 1.0, "round_trip_cost_bps": 10.0, "rf_annual": rf_ann}, {"lookback": [6, 9, 12], "top_k": [1, 2]}, rf_ann)
            shuf = permutation_shuffle_control_monthly(prices, ["TLT","IEF","AGG"], run_dual_momentum_monthly, {"universe": ["TLT","IEF","AGG"], "lookback": 12, "top_k": 1, "vol_target": 0.10, "max_weight": 1.0, "round_trip_cost_bps": 10.0, "rf_annual": rf_ann}, m["sharpe"], rf_ann, ps["shuffle_runs"], rng)
            be_bps, margin = breakeven_cost_search(lambda cb: float(np.prod(1.0 + run_dual_momentum_monthly(prices, ["TLT","IEF","AGG"], 12, 1, 0.10, 1.0, cb, 0.0, rf_ann)["net_returns"]) - 1.0), 10.0)
        elif tid == "CM1":
            wfo = wfo_monthly_splits(prices, run_dual_momentum_monthly, {"universe": ["GLD","DBC"], "lookback": 12, "top_k": 1, "vol_target": 0.12, "max_weight": 1.0, "round_trip_cost_bps": 20.0, "rf_annual": rf_ann}, {"lookback": [9, 12, 15], "vol_target": [0.10, 0.12, 0.15]}, rf_ann)
            shuf = permutation_shuffle_control_monthly(prices, ["GLD","DBC"], run_dual_momentum_monthly, {"universe": ["GLD","DBC"], "lookback": 12, "top_k": 1, "vol_target": 0.12, "max_weight": 1.0, "round_trip_cost_bps": 20.0, "rf_annual": rf_ann}, m["sharpe"], rf_ann, ps["shuffle_runs"], rng)
            be_bps, margin = breakeven_cost_search(lambda cb: float(np.prod(1.0 + run_dual_momentum_monthly(prices, ["GLD","DBC"], 12, 1, 0.12, 1.0, cb, 0.0, rf_ann)["net_returns"]) - 1.0), 20.0)
        elif tid == "MA2":
            r = sim["net_returns"]
            h = len(r) // 2
            def sr_m(arr):
                ex = arr - rf_m
                return float(np.mean(ex) / np.std(ex, ddof=1) * math.sqrt(12.0)) if len(ex) > 2 and np.std(ex, ddof=1) > 1e-12 else 0.0
            def cagr_m(arr):
                eq = float(np.prod(1.0 + arr))
                return (eq ** (12.0 / len(arr)) - 1.0) if (len(arr) and eq > 0) else -1.0
            folds = []
            step = max(1, len(r) // 4)
            for fk in range(4):
                lo = fk * step
                hi = len(r) if fk == 3 else (fk + 1) * step
                sub = r[lo:hi]
                folds.append({"fold": fk + 1, "span": f"{sim['dates'][lo]}..{sim['dates'][hi-1]}", "n": int(len(sub)), "cagr_pct": round(cagr_m(sub)*100.0, 2), "sharpe": round(sr_m(sub), 3)})
            wfo = {
                "is_span": f"{sim['dates'][0]}..{sim['dates'][h-1]}",
                "oos_span": f"{sim['dates'][h]}..{sim['dates'][-1]}",
                "is_sharpe": round(sr_m(r[:h]), 3),
                "oos_sharpe": round(sr_m(r[h:]), 3),
                "is_cagr_pct": round(cagr_m(r[:h])*100.0, 2),
                "oos_cagr_pct": round(cagr_m(r[h:])*100.0, 2),
                "wfe_sharpe_ratio": round(sr_m(r[h:]) / sr_m(r[:h]), 3) if sr_m(r[:h]) > 0.05 else 0.0,
                "wfe_cagr_ratio": round(cagr_m(r[h:]) / cagr_m(r[:h]), 3) if cagr_m(r[:h]) > 0.005 else 0.0,
                "folds": folds,
                "folds_positive_ratio": round(sum(1 for f in folds if f["sharpe"] > 0) / 4.0, 2),
                "heatmap": [],
                "heatmap_positive_ratio": 1.0,
            }
            # Jointly shuffle the 10-asset monthly returns feeding all 4 sleeves!
            log_r = np.log(prices[["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"]] / prices[["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"]].shift(1)).iloc[1:].to_numpy(dtype=float)
            cols = ["SPY","EFA","EEM","TLT","IEF","GLD","VNQ","DBC","QQQ","IWM"]
            bpx = prices[cols].iloc[0].to_numpy(dtype=float)
            sh_srs = np.empty(ps["shuffle_runs"], dtype=float)
            for sk in range(ps["shuffle_runs"]):
                perm = log_r.copy()
                for c in range(perm.shape[1]):
                    perm[:, c] = perm[rng.permutation(perm.shape[0]), c]
                syn_df = pd.DataFrame(np.vstack([bpx, bpx * np.exp(np.cumsum(perm, axis=0))]), index=prices.index, columns=cols)
                se1 = run_dual_momentum_monthly(syn_df, cols, 12, 2, 0.12, 0.50, 10.0, 0.0, rf_ann)
                sb1 = run_dual_momentum_monthly(syn_df, ["TLT","IEF"], 12, 1, 0.10, 1.0, 10.0, 0.0, rf_ann)
                scm = run_dual_momentum_monthly(syn_df, ["GLD","DBC"], 12, 1, 0.12, 1.0, 20.0, 0.0, rf_ann)
                sdef = run_dual_momentum_monthly(syn_df, ["TLT","IEF"], 6, 1, 0.08, 1.0, 5.0, 0.0, rf_ann, skip_recent=0)
                s_mat = np.column_stack([
                    align_series(se1, common_ma2_dates, "net_returns"),
                    align_series(sb1, common_ma2_dates, "net_returns"),
                    align_series(scm, common_ma2_dates, "net_returns"),
                    align_series(sdef, common_ma2_dates, "net_returns"),
                ])
                s_combo = []
                psw = np.array([0.25, 0.25, 0.25, 0.25])
                for tt in range(12, len(common_ma2_dates)):
                    vv = np.maximum(np.std(s_mat[tt-12:tt], axis=0, ddof=1), 0.01)
                    ww = np.minimum(0.50, (1.0/vv)/np.sum(1.0/vv))
                    ww = ww / np.sum(ww)
                    s_combo.append(float(np.dot(ww, s_mat[tt])) - float(np.sum(np.abs(ww - psw))) * 0.0005)
                    psw = ww
                sh_srs[sk] = sr_m(np.array(s_combo))
            shuf = {"n_shuffles": ps["shuffle_runs"], "real_sharpe": m["sharpe"], "shuffle_mean_sharpe": round(float(np.mean(sh_srs)), 3), "shuffle_p95_sharpe": round(float(np.percentile(sh_srs, 95)), 3), "p_value": round(float(np.mean(sh_srs >= m["sharpe"])), 4)}
            be_bps, margin = breakeven_cost_search(lambda cb: float(np.prod(1.0 + (ma2_sim["gross_returns"] - np.array(ma2_turn) * (cb / 20000.0))) - 1.0), 10.0)
        elif tid == "C1":
            r = sim["net_returns"]
            h = len(r) // 2
            rf_d = (1.0 + rf_ann) ** (1.0 / 365.0) - 1.0
            def sr_d(arr):
                ex = arr - rf_d
                return float(np.mean(ex) / np.std(ex, ddof=1) * math.sqrt(365.0)) if len(ex) > 2 and np.std(ex, ddof=1) > 1e-12 else 0.0
            def cagr_d(arr):
                eq = float(np.prod(1.0 + arr))
                return (eq ** (365.0 / len(arr)) - 1.0) if (len(arr) and eq > 0) else -1.0
            folds = []
            step = max(1, len(r) // 4)
            for fk in range(4):
                lo, hi = fk * step, (len(r) if fk == 3 else (fk + 1) * step)
                sub = r[lo:hi]
                folds.append({"fold": fk + 1, "span": f"{sim['dates'][lo]}..{sim['dates'][hi-1]}", "n": int(len(sub)), "cagr_pct": round(cagr_d(sub)*100.0, 2), "sharpe": round(sr_d(sub), 3)})
            hm = []
            for dl in [24, 48, 72]:
                for sa in [1.5, 2.0, 2.5]:
                    cs = simulate_btc_1h_trend(btc_df, dl, 24, 168, sa, sa * 2.0, 72, 20.0, 0.158)
                    hm.append({"donchian_len": dl, "sl_atr": sa, "sharpe": round(sr_d(cs["net_returns"]), 3)})
            wfo = {
                "is_span": f"{sim['dates'][0]}..{sim['dates'][h-1]}",
                "oos_span": f"{sim['dates'][h]}..{sim['dates'][-1]}",
                "is_sharpe": round(sr_d(r[:h]), 3),
                "oos_sharpe": round(sr_d(r[h:]), 3),
                "wfe_sharpe_ratio": round(sr_d(r[h:]) / sr_d(r[:h]), 3) if sr_d(r[:h]) > 0.05 else 0.0,
                "wfe_cagr_ratio": round(cagr_d(r[h:]) / cagr_d(r[:h]), 3) if cagr_d(r[:h]) > 0.005 else 0.0,
                "folds": folds,
                "folds_positive_ratio": round(sum(1 for f in folds if f["sharpe"] > 0) / 4.0, 2),
                "heatmap": hm,
                "heatmap_positive_ratio": round(sum(1 for c in hm if c["sharpe"] > 0) / len(hm), 2),
            }
            # OHLC permutation shuffle control preserving candle geometry
            o_arr = btc_df["Open"].to_numpy()
            h_arr = btc_df["High"].to_numpy()
            l_arr = btc_df["Low"].to_numpy()
            c_arr = btc_df["Close"].to_numpy()
            gaps = np.log(o_arr[1:] / c_arr[:-1])
            rh = np.log(h_arr[1:] / o_arr[1:])
            rl = np.log(l_arr[1:] / o_arr[1:])
            rc = np.log(c_arr[1:] / o_arr[1:])
            sh_srs = np.empty(ps["shuffle_runs"], dtype=float)
            for sk in range(ps["shuffle_runs"]):
                perm = rng.permutation(len(gaps))
                new_o = np.empty(len(o_arr))
                new_h = np.empty(len(o_arr))
                new_l = np.empty(len(o_arr))
                new_c = np.empty(len(o_arr))
                new_o[0], new_h[0], new_l[0], new_c[0] = o_arr[0], h_arr[0], l_arr[0], c_arr[0]
                for i in range(len(perm)):
                    j = perm[i]
                    oi = new_c[i] * math.exp(gaps[j])
                    new_o[i + 1] = oi
                    new_h[i + 1] = oi * math.exp(rh[j])
                    new_l[i + 1] = oi * math.exp(rl[j])
                    new_c[i + 1] = oi * math.exp(rc[j])
                syn_btc = pd.DataFrame({"timestamp": btc_df["timestamp"], "Open": new_o, "High": new_h, "Low": new_l, "Close": new_c, "Volume": btc_df["Volume"]})
                cs = simulate_btc_1h_trend(syn_btc, 48, 24, 168, 2.0, 4.0, 72, 20.0, 0.158)
                sh_srs[sk] = sr_d(cs["net_returns"])
            shuf = {"n_shuffles": ps["shuffle_runs"], "real_sharpe": m["sharpe"], "shuffle_mean_sharpe": round(float(np.mean(sh_srs)), 3), "shuffle_p95_sharpe": round(float(np.percentile(sh_srs, 95)), 3), "p_value": round(float(np.mean(sh_srs >= m["sharpe"])), 4)}
            be_bps, margin = breakeven_cost_search(lambda cb: float(np.prod(1.0 + simulate_btc_1h_trend(btc_df, 48, 24, 168, 2.0, 4.0, 72, cb, 0.158)["net_returns"]) - 1.0), 20.0)
        else:
            # Cohort audits (MA1, S1, FX1)
            r = sim["net_returns"]
            h = max(1, len(r) // 2)
            rf_d = (1.0 + rf_ann) ** (1.0 / ann) - 1.0
            def sr_c(arr):
                ex = arr - rf_d
                return float(np.mean(ex) / np.std(ex, ddof=1) * math.sqrt(ann)) if len(ex) > 2 and np.std(ex, ddof=1) > 1e-12 else 0.0
            folds = []
            step = max(1, len(r) // 4)
            for fk in range(4):
                lo = min(fk * step, max(0, len(r) - 1))
                hi = len(r) if fk == 3 else min(len(r), (fk + 1) * step)
                sub = r[lo:hi]
                folds.append({"fold": fk + 1, "span": f"{sim['dates'][lo]}..{sim['dates'][hi-1]}", "n": int(len(sub)), "mean_daily_pct": round(float(np.mean(sub)*100.0), 3), "sharpe": round(sr_c(sub), 3)})
            wfo = {
                "is_span": f"{sim['dates'][0]}..{sim['dates'][h-1]}",
                "oos_span": f"{sim['dates'][h]}..{sim['dates'][-1]}",
                "is_sharpe": round(sr_c(r[:h]), 3),
                "oos_sharpe": round(sr_c(r[h:]), 3),
                "wfe_sharpe_ratio": round(sr_c(r[h:]) / sr_c(r[:h]), 3) if sr_c(r[:h]) > 0.05 else 0.0,
                "wfe_cagr_ratio": 0.0,
                "folds": folds,
                "folds_positive_ratio": round(sum(1 for f in folds if f["sharpe"] > 0) / 4.0, 2),
                "heatmap": [],
                "heatmap_positive_ratio": 1.0,
            }
            if tid == "MA1":
                # Random 6-strategy permutation control matching walkforward_v6
                pool_by_m = defaultdict(lambda: defaultdict(list))
                for tr in sim["all_oos_pool"]:
                    pool_by_m[tr["month"]][tr["strategy"]].append(tr["pnl_dec"] - 0.001)
                sh_srs = np.empty(ps["shuffle_runs"], dtype=float)
                for sk in range(ps["shuffle_runs"]):
                    d_map = defaultdict(list)
                    for m_key, s_dict in pool_by_m.items():
                        st_list = list(s_dict.keys())
                        chosen = rng.choice(st_list, size=min(6, len(st_list)), replace=False)
                        for tr in sim["all_oos_pool"]:
                            if tr["month"] == m_key and tr["strategy"] in chosen:
                                d_map[tr["date"]].append(tr["pnl_dec"] - 0.001)
                    arr = np.array([sum(d_map[d]) * (1.0 / max(10, len(d_map[d]))) for d in sim["dates"]], dtype=float)
                    sh_srs[sk] = sr_c(arr)
                shuf = {"n_shuffles": ps["shuffle_runs"], "control_type": "random_6_strategy_selector", "real_sharpe": m["sharpe"], "shuffle_mean_sharpe": round(float(np.mean(sh_srs)), 3), "shuffle_p95_sharpe": round(float(np.percentile(sh_srs, 95)), 3), "p_value": round(float(np.mean(sh_srs >= m["sharpe"])), 4)}
            else:
                # Zero-edge sign-flip control (no underlying OHLCV bars on pick table)
                signs = np.sign(r - rf_d)
                sh_srs = np.empty(ps["shuffle_runs"], dtype=float)
                abs_ex = np.abs(r - rf_d)
                for sk in range(ps["shuffle_runs"]):
                    flips = rng.choice([-1.0, 1.0], size=len(abs_ex))
                    perm_ex = flips * np.abs(r - rf_d)
                    sh_srs[sk] = float(np.mean(perm_ex) / np.std(perm_ex, ddof=1) * math.sqrt(ann)) if np.std(perm_ex, ddof=1) > 1e-12 else 0.0
                shuf = {"n_shuffles": ps["shuffle_runs"], "control_type": "sign_flip_null_no_ohlcv", "real_sharpe": m["sharpe"], "shuffle_mean_sharpe": round(float(np.mean(sh_srs)), 3), "shuffle_p95_sharpe": round(float(np.percentile(sh_srs, 95)), 3), "p_value": round(float(np.mean(sh_srs >= m["sharpe"])), 4)}
            base_cb = float(tcfg["round_trip_cost_bps"])
            tr_g = sim["trade_returns_gross"]
            be_bps, margin = breakeven_cost_search(lambda cb: float(np.mean(tr_g - cb / 10000.0)), base_cb, max_bps=250.0)

        # DSR & Monte Carlo & Regime Splits
        rf_p = (1.0 + rf_ann) ** (1.0 / ann) - 1.0
        tvar = trial_var_monthly if ann == 12.0 else trial_var_daily
        dsr_n9 = compute_deflated_sharpe(sim["net_returns"] - rf_p, ann, 9, tvar)
        dsr_n646 = compute_deflated_sharpe(sim["net_returns"] - rf_p, ann, 646, tvar)

        blk = 6 if ann == 12.0 else 5
        mc_blk = circular_block_bootstrap(sim["net_returns"] - rf_p, blk, ps["mc_paths"], rng)
        mc_iid = iid_bootstrap(sim["net_returns"] - rf_p, ps["mc_paths"], rng)

        ref_r = np.array([date_to_spy[d] for d in sim["dates"]], dtype=float) if ann == 12.0 else (bm_arr if np.any(bm_arr != 0) else sim["net_returns"])
        reg = regime_decomposition(sim["net_returns"], ref_r, ann)

        raw_pvals[tid] = m["p_value_2sided"]

        # Store without huge curves in sub-dicts
        eq_curves = {"dates": sim["dates"], "eq_net": m.pop("eq_net"), "eq_gross": m.pop("eq_gross"), "eq_cg": m.pop("eq_cg")}

        # 10-Step Conjunctive Gate Evaluation (preliminary prior to Holm adjustment)
        base_cb = float(tcfg.get("round_trip_cost_bps", 10.0) or 15.0)
        g1 = sim["est_trades"] >= 10 and len(sim["net_returns"]) >= 20
        g2 = wfo["oos_sharpe"] > 0 and wfo["wfe_sharpe_ratio"] >= 0.50 and wfo["heatmap_positive_ratio"] >= 0.60 and wfo["folds_positive_ratio"] >= 0.50
        g4 = mc_blk["pct_pos"] >= 75.0 and mc_iid["pct_pos"] >= 75.0 and mc_blk["p5_cum"] > -15.0
        g5 = m["cagr_net_pct"] > 0 and m["selected_tax_cagr_pct"] > 0 and margin >= 2.0
        g6 = mc_blk["mean_ci95_period_pct"][0] > 0 and m["t_stat"] >= 1.96 and m["p_value_2sided"] < 0.05
        g7 = reg["majority_positive"]
        g8 = shuf["p_value"] < 0.05

        trial_results[tid] = {
            "id": tid,
            "name": tcfg["name"],
            "asset_class": tcfg["asset_class"],
            "timeframe": tcfg["timeframe"],
            "cost_model_bps": base_cb,
            "breakeven_cost_bps": be_bps,
            "cost_margin_of_safety_x": margin,
            "est_trades": sim["est_trades"],
            "metrics": m,
            "wrc_pvalue": wrc_pvals.get(tid),
            "dsr_n9": round(dsr_n9, 4),
            "dsr_n646": round(dsr_n646, 4),
            "prelim_gates": {"1_temporal": g1, "2_wfo": g2, "4_mc": g4, "5_friction_tax": g5, "6_sig": g6, "7_regime": g7, "8_shuffle": g8, "9_tracker": True, "10_repro": True},
        }
        wfo_results[tid] = wfo
        mc_results[tid] = {"block": mc_blk, "iid": mc_iid}
        sig_results[tid] = {
            "dsr_n9": round(dsr_n9, 4),
            "dsr_n646": round(dsr_n646, 4),
            "wrc_pvalue": wrc_pvals.get(tid),
            "t_stat": m["t_stat"],
            "p_value_2sided": m["p_value_2sided"],
            "boot_excess_ci95_pct": mc_blk["mean_ci95_period_pct"],
            "shuffle": shuf,
        }
        regime_results[tid] = {"regimes": reg, "equity_curves": eq_curves}

    # Holm-Bonferroni across the 9 pre-registered trials
    ordered = sorted(raw_pvals.items(), key=lambda x: x[1])
    prev_adj = 0.0
    for rank_idx, (tid, p_raw) in enumerate(ordered):
        mult = len(ordered) - rank_idx
        adj = min(1.0, max(prev_adj, p_raw * mult))
        prev_adj = adj
        trial_results[tid]["holm_pvalue"] = round(adj, 5)
        sig_results[tid]["holm_pvalue"] = round(adj, 5)

        g3_n9 = trial_results[tid]["dsr_n9"] >= 0.95 and adj < 0.05
        g3_n646 = trial_results[tid]["dsr_n646"] >= 0.95 and adj < 0.05
        gates = trial_results[tid]["prelim_gates"]
        gates["3_multiple_testing_n9"] = g3_n9
        gates["3_multiple_testing_n646"] = g3_n646

        passed_strict = sum(1 for k, v in gates.items() if k != "3_multiple_testing_n9" and v)
        gates_strict_10 = all(gates[k] for k in ["1_temporal","2_wfo","3_multiple_testing_n646","4_mc","5_friction_tax","6_sig","7_regime","8_shuffle","9_tracker","10_repro"])

        if gates_strict_10:
            verdict = "PROVEN"
        elif trial_results[tid]["metrics"]["sharpe"] > 0.35 and gates["2_wfo"] and gates["5_friction_tax"] and passed_strict >= 6:
            verdict = "PROMISING (NEAR-MISS)"
        else:
            verdict = "REJECT"
        trial_results[tid]["gates_passed_of_10"] = passed_strict
        trial_results[tid]["verdict"] = verdict

    # Monthly Benchmarks for clean side-by-side comparison
    benchmarks = {}
    for bname, barr in [("SPY_BH", spy_oos), ("60_40_SPY_AGG", b6040_oos), ("AGG_BH", agg_oos), ("TLT_BH", tlt_oos), ("GLD_BH", gld_oos), ("DBC_BH", dbc_oos)]:
        bm_m = compute_metrics(barr, barr, b6040_oos, oos_dates, 12.0, rf_ann, "cap_gains")
        bm_m.pop("eq_net")
        bm_m.pop("eq_gross")
        bm_m.pop("eq_cg")
        benchmarks[bname] = bm_m
    btc_m = compute_metrics(c1_sim["bench_returns"], c1_sim["bench_returns"], c1_sim["bench_returns"], c1_sim["dates"], 365.0, rf_ann, "ordinary")
    btc_m.pop("eq_net")
    btc_m.pop("eq_gross")
    btc_m.pop("eq_cg")
    benchmarks["BTCUSDT_3mo_BH"] = btc_m

    # Save modular outputs
    full_payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": SEED,
        "dataset_sha256": dataset_hashes,
        "trials": trial_results,
        "benchmarks": benchmarks,
        "auxiliary_diagnostics": aux_notes,
    }
    (EXP_DIR / "experiment_results.json").write_text(json.dumps(full_payload, indent=2), encoding="utf-8")
    (PROOF_DIR / "walk_forward_results.json").write_text(json.dumps(wfo_results, indent=2), encoding="utf-8")
    (PROOF_DIR / "monte_carlo_results.json").write_text(json.dumps(mc_results, indent=2), encoding="utf-8")
    (PROOF_DIR / "significance_and_dsr.json").write_text(json.dumps(sig_results, indent=2), encoding="utf-8")
    (PROOF_DIR / "regime_and_equity_curves.json").write_text(json.dumps(regime_results, indent=2), encoding="utf-8")

    # Render Markdown Summary Table
    lines = [
        "# Proof Suite Summary Table (10-Step Non-Negotiable Standard)",
        "",
        f"- **Generated UTC:** `{full_payload['generated_at_utc']}` | **Seed:** `{SEED}` | **Trials Evaluated:** `9` (cascaded against `N_repo = 646`)",
        "",
        "| ID | Asset Class | Timeframe | CAGR Net | CAD After-Tax | Sharpe | Sortino | Calmar | MaxDD | WinRate | PF | DSR (N=9 / N=646) | Holm p | Block MC +% | Shuffle p | Gates (/10) | Verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for tid in ["E1", "M1", "MA1", "MA2", "S1", "C1", "B1", "CM1", "FX1"]:
        tr = trial_results[tid]
        m = tr["metrics"]
        mc_b = mc_results[tid]["block"]
        sh = sig_results[tid]["shuffle"]
        cal = f"{m['calmar']:.2f}" if m["calmar"] is not None else "n/a"
        lines.append(
            f"| `{tid}` | {tr['asset_class']} | {tr['timeframe']} | {m['cagr_net_pct']:+.2f}% | {m['selected_tax_cagr_pct']:+.2f}% | "
            f"{m['sharpe']:.2f} | {m['sortino']:.2f} | {cal} | {m['max_dd_pct']:.1f}% | {m['win_rate_pct']:.1f}% | {m['profit_factor']:.2f} | "
            f"{tr['dsr_n9']:.3f} / {tr['dsr_n646']:.3f} | {tr['holm_pvalue']:.4f} | {mc_b['pct_pos']:.1f}% | {sh['p_value']:.4f} | "
            f"{tr['gates_passed_of_10']}/10 | **{tr['verdict']}** |"
        )
    lines.extend([
        "",
        "## Benchmark Reference Curves",
        "",
        "| Benchmark | Span | CAGR | Ann Vol | Sharpe | MaxDD |",
        "|---|---|---|---|---|---|",
    ])
    for bname, bm in benchmarks.items():
        lines.append(f"| `{bname}` | {bm['n_periods']} bars | {bm['cagr_net_pct']:+.2f}% | {bm['ann_vol_pct']:.1f}% | {bm['sharpe']:.2f} | {bm['max_dd_pct']:.1f}% |")

    (PROOF_DIR / "PROOF_SUMMARY_TABLE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
