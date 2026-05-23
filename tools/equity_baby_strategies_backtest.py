"""Backtest for equity baby strategies (FOOLPROOF_ACTION_PLAN line 103).

Strategies:
  - equity_vix_regime_momentum: VIX term structure + SPY momentum on SPY/QQQ/IWM
  - equity_sector_rotation_momentum: Dual-momentum top-3 sector ETF rotation

Both use exit logic aligned with shadow tracker (EXPIRED = neutral, excluded from WR/PF).

Run: python tools/equity_baby_strategies_backtest.py [--start YYYY-MM-DD]
Output: audit_dashboard/data/equity_baby_strategies_backtest.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_PATH = ROOT / "audit_dashboard" / "data" / "equity_baby_strategies_backtest.json"
CAPITAL_PER_TRADE = 10_000.0
MAX_HOLD_BARS = 30


def _wma_rsi(close: list[float], period: int = 14) -> list[float]:
    """Simple RSI using Wilder smoothing."""
    result = [float("nan")] * len(close)
    if len(close) < period + 1:
        return result
    deltas = [close[i] - close[i - 1] for i in range(1, len(close))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
        rs = avg_g / avg_l if avg_l > 0 else float("inf")
        result[i + 1] = 100 - (100 / (1 + rs))
    return result


def _sma(series: list[float], period: int) -> list[float]:
    result = [float("nan")] * len(series)
    for i in range(period - 1, len(series)):
        result[i] = sum(series[i - period + 1 : i + 1]) / period
    return result


def _backtest_trades(trades: list[dict]) -> dict:
    """Compute WR/PF/MDD/Sharpe. EXPIRED excluded from WR/PF (shadow tracker methodology)."""
    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    expired = [t for t in trades if t["outcome"] == "EXPIRED"]
    wins = [t for t in closed if t["outcome"] == "WIN"]
    losses = [t for t in closed if t["outcome"] == "LOSS"]
    pnl_list = [t["pnl_usd"] for t in closed]
    gross_win = sum(t["pnl_usd"] for t in wins)
    gross_loss = abs(sum(t["pnl_usd"] for t in losses))
    pf = round(gross_win / gross_loss, 4) if gross_loss > 0 else (9999.0 if gross_win > 0 else 0.0)
    wr = round(len(wins) / len(closed), 4) if closed else 0.0
    avg_pnl = round(sum(pnl_list) / len(pnl_list), 2) if pnl_list else 0.0
    total_pnl = round(sum(pnl_list), 2)

    cum = 0.0
    peak = 0.0
    mdd_usd = 0.0
    for t in sorted(closed, key=lambda x: x["exit_date"]):
        cum += t["pnl_usd"]
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > mdd_usd:
            mdd_usd = dd
    # MDD as % of total capital deployed across all trades
    total_deployed = len(trades) * CAPITAL_PER_TRADE if trades else CAPITAL_PER_TRADE
    mdd = mdd_usd / total_deployed

    if len(pnl_list) > 1:
        mean_r = sum(pnl_list) / len(pnl_list) / CAPITAL_PER_TRADE
        var_r = sum((x / CAPITAL_PER_TRADE - mean_r) ** 2 for x in pnl_list) / len(pnl_list)
        std_r = math.sqrt(var_r) if var_r > 0 else 0
        sharpe = round(mean_r / std_r * math.sqrt(252) if std_r > 0 else 0, 4)
    else:
        sharpe = 0.0

    return {
        "n_trades": len(trades),
        "n_closed": len(closed),
        "n_expired": len(expired),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(wr * 100, 2),
        "profit_factor": pf,
        "avg_pnl_usd": avg_pnl,
        "total_pnl_usd": total_pnl,
        "max_drawdown_pct": round(mdd * 100, 2),
        "sharpe_annualized": sharpe,
        "note": "WR/PF on closed (WIN/LOSS) only; EXPIRED (30-bar timeout) excluded",
    }


def _resolve_trade(entry_price: float, tp: float, sl: float, closes: list[float],
                   highs: list[float], lows: list[float], is_long: bool,
                   entry_idx: int, max_hold: int = MAX_HOLD_BARS) -> tuple[str, float, int]:
    """Walk forward from entry_idx to find first TP/SL touch or max_hold-bar expiry."""
    for j in range(1, max_hold + 1):
        idx = entry_idx + j
        if idx >= len(closes):
            return "EXPIRED", closes[-1], j
        hi = highs[idx]
        lo = lows[idx]
        cl = closes[idx]
        if is_long:
            if hi >= tp:
                return "WIN", tp, j
            if lo <= sl:
                return "LOSS", sl, j
        else:
            if lo <= tp:
                return "WIN", tp, j
            if hi >= sl:
                return "LOSS", sl, j
        if j == max_hold:
            return "EXPIRED", cl, j
    return "EXPIRED", closes[entry_idx + 1] if entry_idx + 1 < len(closes) else closes[-1], 1


def run_vix_regime_backtest(start: str) -> dict:
    """equity_vix_regime_momentum: VIX contango/backwardation + SPY/QQQ/IWM."""
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        return {"error": "yfinance required"}

    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    symbols = ["SPY", "QQQ", "IWM", "^VIX", "^VIX3M"]
    print(f"[vix_regime] Fetching {symbols} {start}→{end} …")

    raw = {}
    for sym in symbols:
        h = yf.Ticker(sym).history(start=start, end=end, interval="1d", auto_adjust=True)
        if not h.empty:
            raw[sym] = h

    if "^VIX" not in raw or "^VIX3M" not in raw:
        return {"error": "VIX data unavailable"}

    SMA_P = 50
    MOM_P = 21
    TP_PCT = 0.06
    SL_PCT = 0.04

    trades: list[dict] = []

    for sym in ("SPY", "QQQ", "IWM"):
        if sym not in raw:
            continue
        df = raw[sym]
        vix_df = raw["^VIX"]
        vix3m_df = raw["^VIX3M"]

        dates = [str(d.date()) for d in df.index]
        closes = df["Close"].tolist()
        highs = df["High"].tolist()
        lows = df["Low"].tolist()
        sma50 = _sma(closes, SMA_P)

        # Align VIX data by date
        vix_by_date = {str(d.date()): float(v) for d, v in zip(vix_df.index, vix_df["Close"])}
        vix3m_by_date = {str(d.date()): float(v) for d, v in zip(vix3m_df.index, vix3m_df["Close"])}

        next_entry_bar = SMA_P + MOM_P  # earliest bar at which we can enter
        for i in range(SMA_P + MOM_P, len(closes)):
            if i < next_entry_bar:
                continue  # previous position still open

            date = dates[i]
            close = closes[i]
            s50 = sma50[i]
            vix = vix_by_date.get(date)
            vix3m = vix3m_by_date.get(date)
            if math.isnan(s50) or vix is None or vix3m is None:
                continue

            mom = close / closes[i - MOM_P] - 1

            is_long = None
            if vix < vix3m and close > s50 and mom > 0:
                is_long = True
            elif vix > vix3m and close < s50 and mom < 0:
                is_long = False

            if is_long is None:
                continue

            entry = close
            tp = entry * (1 + TP_PCT) if is_long else entry * (1 - TP_PCT)
            sl = entry * (1 - SL_PCT) if is_long else entry * (1 + SL_PCT)

            outcome, exit_price, hold = _resolve_trade(
                entry, tp, sl, closes, highs, lows, is_long, i
            )
            pnl_pct = ((exit_price - entry) / entry) if is_long else ((entry - exit_price) / entry)
            pnl_usd = CAPITAL_PER_TRADE * pnl_pct if outcome != "EXPIRED" else 0.0

            trades.append({
                "symbol": sym,
                "entry_date": date,
                "exit_date": dates[min(i + hold, len(dates) - 1)],
                "direction": "LONG" if is_long else "SHORT",
                "entry_price": round(entry, 4),
                "exit_price": round(exit_price, 4),
                "outcome": outcome,
                "pnl_pct": round(pnl_pct * 100 if outcome != "EXPIRED" else 0, 4),
                "pnl_usd": round(pnl_usd, 2),
                "vix": round(vix, 2),
                "vix3m": round(vix3m, 2),
            })
            next_entry_bar = i + hold + 1  # no re-entry until previous trade closes

    return {
        "strategy": "equity_vix_regime_momentum",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "VIX term structure (contango→LONG / backwardation→SHORT) on SPY/QQQ/IWM, SMA50 trend filter, 21d momentum, TP=6%, SL=4%",
        "config": {"start": start, "end": end, "symbols": ["SPY", "QQQ", "IWM"], "tp_pct": TP_PCT, "sl_pct": SL_PCT},
        "results": _backtest_trades(trades),
        "trades": trades,
    }


def run_sector_rotation_backtest(start: str) -> dict:
    """equity_sector_rotation_momentum: Dual-momentum top-3 sector ETFs."""
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance required"}

    from baby_strategies.equity_sector_rotation_momentum import SECTOR_ETFS

    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sector_syms = list(SECTOR_ETFS.keys())
    all_syms = sector_syms + ["SPY"]
    print(f"[sector_rotation] Fetching {len(all_syms)} symbols {start}→{end} …")

    raw = {}
    for sym in all_syms:
        h = yf.Ticker(sym).history(start=start, end=end, interval="1d", auto_adjust=True)
        if not h.empty and len(h) >= 65:
            raw[sym] = h

    TOP_N = 3
    TP_PCT = 0.06   # reduced from 0.08 — 8% was too ambitious for 30-bar hold
    SL_PCT = 0.05
    SMA_P = 200
    MOM_1M = 21
    MOM_3M = 63
    MAX_HOLD_BARS_SECTOR = 60  # extended from 30 — sector rotation needs longer hold

    # Use SPY dates as the reference timeline (longest and most complete)
    if "SPY" not in raw:
        return {"error": "SPY data unavailable"}

    spy_df = raw["SPY"]
    dates = [str(d.date()) for d in spy_df.index]
    spy_closes = spy_df["Close"].tolist()
    spy_sma200 = _sma(spy_closes, SMA_P)

    trades: list[dict] = []
    # next_entry_bar_by_sym: earliest SPY timeline bar at which we can re-enter each symbol
    next_entry_bar_by_sym: dict[str, int] = {}

    # Pre-build date→index maps for each sector df (expensive inside loop otherwise)
    df_date_idx: dict[str, dict[str, int]] = {}
    for sym in sector_syms:
        if sym in raw:
            dd = [str(d.date()) for d in raw[sym].index]
            df_date_idx[sym] = {date: idx for idx, date in enumerate(dd)}

    for i in range(SMA_P + MOM_3M, len(dates)):
        date = dates[i]
        spy_s200 = spy_sma200[i]
        is_bullish = spy_closes[i] > spy_s200 if not math.isnan(spy_s200) else True

        # Score each sector
        scores: dict[str, float] = {}
        for sym in sector_syms:
            if sym not in raw:
                continue
            date_map = df_date_idx.get(sym, {})
            if date not in date_map:
                continue
            idx = date_map[date]
            if idx < MOM_3M:
                continue
            cl = raw[sym]["Close"].tolist()
            mom_1m = cl[idx] / cl[idx - MOM_1M] - 1
            mom_3m = cl[idx] / cl[idx - MOM_3M] - 1
            if mom_1m > 0 and mom_3m > 0:
                scores[sym] = (mom_1m + mom_3m) / 2

        # Long-only: only trade when SPY is in uptrend (swarm AG recommendation)
        if not is_bullish:
            continue
        targets = sorted(scores.keys(), key=lambda s: scores[s], reverse=True)[:TOP_N]

        for sym in targets:
            date_map_sym = df_date_idx.get(sym, {})
            if date not in date_map_sym:
                continue
            sym_idx = date_map_sym[date]  # per-symbol dataframe index (not SPY-timeline i)
            # Block re-entry using per-symbol index (fixes SPY-vs-sector bar count mismatch)
            if sym_idx < next_entry_bar_by_sym.get(sym, 0):
                continue
            if sym not in raw:
                continue
            df = raw[sym]
            sym_dates = list(date_map_sym.keys())
            cl = df["Close"].tolist()
            hi = df["High"].tolist()
            lo = df["Low"].tolist()
            entry = cl[sym_idx]
            tp = entry * (1 + TP_PCT)
            sl = entry * (1 - SL_PCT)

            outcome, exit_price, hold = _resolve_trade(
                entry, tp, sl, cl, hi, lo, True, sym_idx, max_hold=MAX_HOLD_BARS_SECTOR
            )

            pnl_pct = (exit_price - entry) / entry
            pnl_usd = CAPITAL_PER_TRADE * pnl_pct if outcome != "EXPIRED" else 0.0

            exit_sym_idx = min(sym_idx + hold, len(sym_dates) - 1)
            trades.append({
                "symbol": sym,
                "entry_date": date,
                "exit_date": sym_dates[exit_sym_idx],
                "direction": "LONG",
                "entry_price": round(entry, 4),
                "exit_price": round(exit_price, 4),
                "outcome": outcome,
                "pnl_pct": round(pnl_pct * 100 if outcome != "EXPIRED" else 0, 4),
                "pnl_usd": round(pnl_usd, 2),
                "sector": SECTOR_ETFS.get(sym, sym),
            })
            # Advance per-symbol next_entry_bar (fixes bar index mismatch)
            next_entry_bar_by_sym[sym] = sym_idx + hold + 1

    return {
        "strategy": "equity_sector_rotation_momentum",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "Dual-momentum (1M+3M) top-3 sector ETFs, SPY SMA200 regime filter, TP=8%, SL=5%",
        "config": {"start": start, "end": end, "top_n": TOP_N, "tp_pct": TP_PCT, "sl_pct": SL_PCT},
        "results": _backtest_trades(trades),
        "trades": trades,
    }


def run_vix_regime_4h_backtest() -> dict:
    """equity_vix_regime_momentum 4H retest (swarm AG recommendation).

    Swarm AG flagged WR=40.6% on daily bars may be due to slow signal —
    VIX contango edge might be cleaner at higher resolution. Uses 1H bars
    resampled to 4H (yfinance limit: last 730 days only).
    SMA and momentum periods scaled to 4H bars:
      50-day SMA → 100 4H bars (50 trading days × ~2 bars/day)
      21-day mom  →  42 4H bars
      Max hold 30 daily → 45 4H bars (~22 trading days equivalent)
    """
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        return {"error": "yfinance/pandas required"}

    from datetime import datetime as _dt, timedelta as _td
    _end = _dt.now()
    _start = _end - _td(days=728)
    start_str = _start.strftime("%Y-%m-%d")
    end_str = _end.strftime("%Y-%m-%d")

    symbols = ["SPY", "QQQ", "IWM", "^VIX", "^VIX3M"]
    print(f"[vix_regime_4h] Fetching 1H bars {start_str}→{end_str} …")

    raw1h: dict = {}
    for sym in symbols:
        h = yf.Ticker(sym).history(start=start_str, end=end_str, interval="1h", auto_adjust=True)
        if not h.empty:
            raw1h[sym] = h

    if "^VIX" not in raw1h or "^VIX3M" not in raw1h:
        return {"error": "VIX 1H data unavailable"}

    # Resample 1H → 4H (US market hours: 4 bars/4H session block)
    def resample_4h(df: "pd.DataFrame") -> "pd.DataFrame":
        return df.resample("4h").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
        }).dropna(subset=["Close"])

    raw4h: dict = {}
    for sym, df in raw1h.items():
        r = resample_4h(df)
        if not r.empty:
            raw4h[sym] = r

    SMA_P = 100   # 100 × 4H ≈ 50 trading days
    MOM_P = 42    # 42 × 4H ≈ 21 trading days
    MAX_HOLD_4H = 45
    TP_PCT = 0.04  # tighter TP for intraday resolution
    SL_PCT = 0.025

    trades: list[dict] = []

    for sym in ("SPY", "QQQ", "IWM"):
        if sym not in raw4h:
            continue
        df = raw4h[sym]
        if "^VIX" not in raw4h or "^VIX3M" not in raw4h:
            continue
        vix_df = raw4h["^VIX"]
        vix3m_df = raw4h["^VIX3M"]

        dates = [str(d)[:16] for d in df.index]
        closes = df["Close"].tolist()
        highs = df["High"].tolist()
        lows = df["Low"].tolist()
        sma_vals = _sma(closes, SMA_P)

        vix_by_dt = {str(d)[:16]: float(v) for d, v in zip(vix_df.index, vix_df["Close"])}
        vix3m_by_dt = {str(d)[:16]: float(v) for d, v in zip(vix3m_df.index, vix3m_df["Close"])}

        next_entry_bar = SMA_P + MOM_P
        for i in range(SMA_P + MOM_P, len(closes)):
            if i < next_entry_bar:
                continue

            date = dates[i]
            close = closes[i]
            sma = sma_vals[i]
            vix = vix_by_dt.get(date)
            vix3m = vix3m_by_dt.get(date)
            if math.isnan(sma) or vix is None or vix3m is None:
                continue

            mom = close / closes[i - MOM_P] - 1

            is_long = None
            if vix < vix3m and close > sma and mom > 0:
                is_long = True

            if is_long is None:
                continue

            entry = close
            tp = entry * (1 + TP_PCT)
            sl = entry * (1 - SL_PCT)

            outcome, exit_price, hold = _resolve_trade(
                entry, tp, sl, closes, highs, lows, is_long, i, max_hold=MAX_HOLD_4H
            )
            pnl_pct = (exit_price - entry) / entry if is_long else (entry - exit_price) / entry
            pnl_usd = CAPITAL_PER_TRADE * pnl_pct if outcome != "EXPIRED" else 0.0

            trades.append({
                "symbol": sym,
                "entry_date": date,
                "exit_date": dates[min(i + hold, len(dates) - 1)],
                "direction": "LONG",
                "entry_price": round(entry, 4),
                "exit_price": round(exit_price, 4),
                "outcome": outcome,
                "pnl_pct": round(pnl_pct * 100 if outcome != "EXPIRED" else 0, 4),
                "pnl_usd": round(pnl_usd, 2),
                "vix": round(vix, 2),
                "vix3m": round(vix3m, 2),
            })
            next_entry_bar = i + hold + 1

    results = _backtest_trades(trades)
    results["note"] = (
        "WR/PF on closed (WIN/LOSS) only; EXPIRED (45-bar timeout) excluded. "
        "4H bars: 1H resampled, last ~2 years only (yfinance limit). "
        "Long-only (VIX contango + price > SMA100 + 42-bar positive momentum)."
    )
    return {
        "strategy": "equity_vix_regime_momentum_4h",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "VIX contango LONG-only on SPY/QQQ/IWM, 4H bars, SMA100 + 42-bar mom, TP=4% SL=2.5%",
        "config": {
            "start": start_str, "end": end_str, "interval": "4h",
            "symbols": ["SPY", "QQQ", "IWM"], "tp_pct": TP_PCT, "sl_pct": SL_PCT,
            "sma_period": SMA_P, "mom_period": MOM_P, "max_hold_bars": MAX_HOLD_4H,
        },
        "results": results,
        "trades": trades,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--vix4h", action="store_true", help="Also run VIX regime 4H retest")
    args = parser.parse_args()

    vix_result = run_vix_regime_backtest(args.start)
    sector_result = run_sector_rotation_backtest(args.start)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "equity_vix_regime_momentum": vix_result,
        "equity_sector_rotation_momentum": sector_result,
    }

    if args.vix4h:
        vix4h_result = run_vix_regime_4h_backtest()
        output["equity_vix_regime_momentum_4h"] = vix4h_result
        r4 = vix4h_result.get("results", {})
        print(
            f"[vix_regime_4h] n={r4.get('n_closed')}/{r4.get('n_trades')} WR={r4.get('win_rate_pct')}% "
            f"PF={r4.get('profit_factor')} MDD={r4.get('max_drawdown_pct')}% Sharpe={r4.get('sharpe_annualized')}"
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")

    for strat_key, result in [("equity_vix_regime_momentum", vix_result), ("equity_sector_rotation_momentum", sector_result)]:
        r = result.get("results", {})
        print(
            f"[{strat_key}] n={r.get('n_closed')}/{r.get('n_trades')} WR={r.get('win_rate_pct')}% "
            f"PF={r.get('profit_factor')} MDD={r.get('max_drawdown_pct')}% Sharpe={r.get('sharpe_annualized')}"
        )
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
