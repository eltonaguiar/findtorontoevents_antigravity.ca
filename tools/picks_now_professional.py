#!/usr/bin/env python3
"""
PICKS NOW — Professional Multi-Asset Quant Screener
====================================================
Generates institutional-grade, actionable "right now" picks per asset class.

Methodology (hedge fund / quant standard):
  1. Momentum factors (3m/1m/5d cross-sectional) — AQR-style
  2. Mean reversion signals (RSI + Bollinger %-B) — Two Sigma style
  3. Analyst consensus scoring (yfinance recommendationMean + targetMeanPrice)
  4. Volatility-adjusted sizing (ATR + realized vol = Kelly/risk-parity)
  5. Insider trade activity (yfinance insider_purchases)
  6. Earnings quality (EPS growth, forward PE, PEG ratio)
  7. DB edge overlay (our at_pick_outcomes resolved performance per symbol)

Outputs:
  - reports/PICKS_NOW_<date>.md          — Full report with entry/TP/SL
  - audit_dashboard/data/picks_now.json   — Machine-readable for website
  - stdout                                 — Summary

Usage:
  python3 tools/picks_now_professional.py

Dependencies: yfinance, pandas, numpy, scipy, pymysql
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "audit_dashboard" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = REPO / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── DB credentials ──────────────────────────────────────────────────────────
DB_HOST = "mysql.50webs.com"
DB_STOCKS_USER = "ejaguiar1_stocks"
DB_STOCKS_PASS = "stocks1234560"
DB_STOCKS_NAME = "ejaguiar1_stocks"


# ── Universe by asset class ─────────────────────────────────────────────────
UNIVERSE = {
    "EQUITY": {
        "tickers": [
            "NVDA", "META", "MSFT", "GOOGL", "AMZN", "AAPL", "AMD",
            "AVGO", "JPM", "BRK-B", "V", "MA", "UNH", "WMT", "COST",
            "JNJ", "PG", "KO", "PEP", "XOM", "CVX", "CAT", "MCD",
            "DIS", "NFLX", "ADBE", "CRM", "INTC", "QCOM", "TXN",
            "AMAT", "LRCX", "MU", "NOW", "UBER", "ABNB", "GS", "MS",
        ],
        "benchmark": "SPY",
    },
    "ETF": {
        "tickers": [
            "SPY", "QQQ", "IWM", "GLD", "SLV", "TLT", "IEF", "SHY",
            "LQD", "HYG", "XLK", "XLF", "XLE", "XLU", "XLV", "XLI",
            "VGT", "VHT", "VNQ", "VB", "IVV", "VOO", "IJR", "EFA",
            "EEM", "BND", "AGG", "BITO", "IBIT", "ARKK",
        ],
        "benchmark": "SPY",
    },
    "CRYPTO": {
        "tickers": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
            "MATIC-USD", "UNI-USD", "ATOM-USD", "LTC-USD", "BCH-USD",
        ],
        "benchmark": "BTC-USD",
    },
    "FOREX": {
        "tickers": [
            "EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X",
            "USDCAD=X", "NZDUSD=X", "EURGBP=X", "EURJPY=X",
        ],
        "benchmark": "EURUSD=X",
    },
    "COMMODITY": {
        "tickers": [
            "GC=F", "SI=F", "CL=F", "NG=F", "ZW=F", "ZC=F",
            "ZS=F", "HG=F", "PA=F", "PL=F",
        ],
        "benchmark": "GC=F",
    },
    "BOND": {
        "tickers": [
            "TLT", "IEF", "SHY", "LQD", "HYG", "AGG", "BND", "MBB",
        ],
        "benchmark": "IEF",
    },
}


# ── Technical helpers ───────────────────────────────────────────────────────

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period-1, adjust=True, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period-1, adjust=True, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def calc_bollinger_pct(df, period=20, std_dev=2):
    mid = df['Close'].rolling(period).mean()
    std = df['Close'].rolling(period).std()
    lower = mid - std_dev * std
    upper = mid + std_dev * std
    return ((df['Close'] - lower) / (upper - lower)).iloc[-1]


def calc_atr(df, period=14):
    hl = df['High'] - df['Low']
    hc = (df['High'] - df['Close'].shift()).abs()
    lc = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]


def calc_realized_vol(close, window=20, annualized=True):
    log_ret = np.log(close / close.shift(1)).dropna()
    vol = log_ret.tail(window).std()
    if annualized:
        vol *= np.sqrt(252)
    return vol * 100  # as %


def calc_sharpe_from_returns(close, rfr=0.05):
    """Annualized Sharpe ratio from price series."""
    log_ret = np.log(close / close.shift(1)).dropna()
    excess = log_ret.mean() * 252 - rfr
    vol = log_ret.std() * np.sqrt(252)
    return excess / vol if vol > 0 else 0


def calc_max_drawdown(close):
    cumulative = close / close.iloc[0]
    peak = cumulative.expanding().max()
    dd = (cumulative - peak) / peak
    return abs(dd.min()) * 100


# ── DB edge data ────────────────────────────────────────────────────────────

def load_db_edge():
    """Load our resolved pick performance per symbol from at_pick_outcomes."""
    try:
        import pymysql
        conn = pymysql.connect(
            host=DB_HOST, user=DB_STOCKS_USER, password=DB_STOCKS_PASS,
            database=DB_STOCKS_NAME,
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT symbol, asset_class,
                   COUNT(*) as n,
                   SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) as wins,
                   ROUND(AVG(pnl_pct), 4) as avg_pnl,
                   ROUND(AVG(CASE WHEN status='WON' THEN pnl_pct END), 4) as avg_win,
                   ROUND(AVG(CASE WHEN status='LOST' THEN pnl_pct END), 4) as avg_loss
            FROM at_pick_outcomes
            WHERE status IN ('WON','LOST') AND pnl_pct IS NOT NULL
            GROUP BY symbol, asset_class
            HAVING COUNT(*) >= 5
        """)
        data = {}
        for r in cur.fetchall():
            symbol, ac, n, wins, avg_pnl, avg_win, avg_loss = r
            n = int(n)
            wins = int(wins)
            wr = wins / n * 100 if n > 0 else 0
            data[symbol.upper()] = {
                "n": n, "wr": round(wr, 1), "avg_pnl": float(avg_pnl or 0),
                "avg_win": float(avg_win or 0), "avg_loss": float(avg_loss or 0),
            }
        conn.close()
        return data
    except Exception as e:
        print(f"  [WARN] DB edge load failed: {e}")
        return {}


# ── Scoring engine ──────────────────────────────────────────────────────────

class QuantScorer:
    """Multi-factor scoring (inspired by institutional quant frameworks)."""

    # Weights (sum = 100)
    W_MOMENTUM = 30
    W_MEAN_REVERSION = 20
    W_ANALYST = 25
    W_VOL_ADJUSTED = 15
    W_DB_EDGE = 10

    def score(self, sym: str, cls: str, df: pd.DataFrame,
              info: dict, db_edge: dict, prices: dict) -> dict:
        """Score one symbol across all factors. Returns result dict."""
        c = df['Close']
        p_now = float(c.iloc[-1])

        # ── Momentum factors ──
        ret_5d = float(c.iloc[-1] / c.iloc[-6] - 1) * 100 if len(c) >= 6 else None
        ret_1m = float(c.iloc[-1] / c.iloc[-21] - 1) * 100 if len(c) >= 21 else None
        ret_3m = float(c.iloc[-1] / c.iloc[-63] - 1) * 100 if len(c) >= 63 else None
        ret_6m = float(c.iloc[-1] / c.iloc[-126] - 1) * 100 if len(c) >= 126 else None

        # ── Technical indicators ──
        rsi_val = float(calc_rsi(c).iloc[-1])
        bb_pct = float(calc_bollinger_pct(df))
        atr_val = float(calc_atr(df))
        atr_pct = atr_val / p_now * 100 if p_now > 0 else 0
        rvol = float(calc_realized_vol(c))
        sharpe = float(calc_sharpe_from_returns(c))
        max_dd = float(calc_max_drawdown(c))

        # ── RSI signal ──
        if rsi_val < 25: rsi_sig = "OVERSOLD_25"
        elif rsi_val < 35: rsi_sig = "OVERSOLD_35"
        elif rsi_val < 45: rsi_sig = "OVERSOLD_45"
        elif rsi_val > 75: rsi_sig = "OVERBOUGHT_75"
        elif rsi_val > 65: rsi_sig = "OVERBOUGHT_65"
        else: rsi_sig = "NEUTRAL"

        # ── Analyst consensus ──
        analyst_rating = info.get("recommendationMean", None)
        analyst_key = info.get("recommendationKey", "")
        analyst_n = info.get("numberOfAnalystOpinions", 0) or 0
        target_price = info.get("targetMeanPrice", None)
        target_high = info.get("targetHighPrice", None)
        target_low = info.get("targetLowPrice", None)
        upside = ((target_price / p_now) - 1) * 100 if target_price and p_now else None
        upside_high = ((target_high / p_now) - 1) * 100 if target_high and p_now else None

        fwd_pe = info.get("forwardPE", None)
        peg = info.get("pegRatio", None)
        eps_growth = info.get("earningsQuarterlyGrowth", None)
        roe = info.get("returnOnEquity", None)
        market_cap = info.get("marketCap", None)
        div_yield = info.get("dividendYield", 0)
        if div_yield:
            div_yield *= 100

        # Insider data
        insider_shares = None
        try:
            ins = yf.Ticker(sym).insider_purchases
            if ins is not None and not ins.empty and 'Shares' in ins.columns:
                insider_shares = int(ins['Shares'].sum())
        except Exception:
            pass

        # ── DB edge overlay ──
        db = db_edge.get(sym.upper(), {})
        db_n = db.get("n", 0)
        db_wr = db.get("wr", 0)
        db_avg_pnl = db.get("avg_pnl", 0)

        # ── COMPOSITE SCORE (range: -100 to +150) ──
        score = 50  # baseline neutral

        signals = []

        # 1. Momentum (30 pts)
        if ret_3m is not None and ret_5d is not None:
            # Strong uptrend with pullback = best setup
            if ret_3m > 10 and ret_5d < -3:
                score += self.W_MOMENTUM
                signals.append(f"TREND+DIP 3m={ret_3m:.0f}%")
            elif ret_3m > 5:
                score += self.W_MOMENTUM * 0.5
                signals.append(f"UPTREND 3m={ret_3m:.0f}%")
            elif ret_3m < -15:
                score -= self.W_MOMENTUM * 0.7
                signals.append(f"DOWNTREND 3m={ret_3m:.0f}%")
            elif ret_3m < -5:
                score -= self.W_MOMENTUM * 0.3
                signals.append(f"WEAK 3m={ret_3m:.0f}%")

        # 2. Mean reversion (20 pts)
        if rsi_val < 35 and bb_pct < 0.20:
            score += self.W_MEAN_REVERSION
            signals.append(f"RSI={rsi_val:.0f} BB_LOWER")
        elif rsi_val < 40 and bb_pct < 0.30:
            score += self.W_MEAN_REVERSION * 0.6
            signals.append(f"RSI={rsi_val:.0f} NEAR_LOWER")
        elif rsi_val > 70 and bb_pct > 0.80:
            score -= self.W_MEAN_REVERSION * 0.5
            signals.append(f"RSI={rsi_val:.0f} BB_UPPER")

        # 3. Analyst consensus (25 pts)
        if analyst_n >= 5:
            if analyst_rating and analyst_rating <= 1.5:
                score += self.W_ANALYST
                signals.append(f"STRONG_BUY({analyst_n})")
            elif analyst_rating and analyst_rating <= 2.0:
                score += self.W_ANALYST * 0.7
                signals.append(f"BUY({analyst_n})")
            elif analyst_rating and analyst_rating <= 2.5:
                score += self.W_ANALYST * 0.4
                signals.append(f"OUTPERFORM({analyst_n})")
            elif analyst_rating and analyst_rating >= 4.0:
                score -= self.W_ANALYST * 0.5
                signals.append(f"SELL({analyst_n})")

            # Upside to target bonus
            if upside and upside > 25:
                score += 10
                signals.append(f"TP+{upside:.0f}%")
            elif upside and upside > 10:
                score += 5
                signals.append(f"TP+{upside:.0f}%")
            elif upside and upside < -10:
                score -= 5

        # 4. Vol-adjusted safety (15 pts)
        if rvol < 20:
            score += self.W_VOL_ADJUSTED
            signals.append(f"LOW_VOL {rvol:.0f}%")
        elif rvol < 35:
            score += self.W_VOL_ADJUSTED * 0.4
            signals.append(f"MOD_VOL {rvol:.0f}%")
        elif rvol > 60:
            score -= self.W_VOL_ADJUSTED * 0.3
            signals.append(f"HIGH_VOL {rvol:.0f}%")

        # Low drawdown bonus
        if max_dd < 15:
            score += 5

        # Dividend yield bonus (for ETFs/bonds)
        if div_yield and div_yield > 3:
            score += 5
            signals.append(f"DIV={div_yield:.1f}%")

        # 5. DB edge overlay (10 pts)
        if db_n >= 20:
            if db_wr > 55:
                score += self.W_DB_EDGE
                signals.append(f"DB_WR={db_wr:.0f}% n={db_n}")
            elif db_wr > 45:
                score += self.W_DB_EDGE * 0.4
                signals.append(f"DB_WR={db_wr:.0f}% n={db_n}")

        # ── Direction ──
        if score >= 75:
            direction = "STRONG_BUY"
        elif score >= 55:
            direction = "BUY"
        elif score >= 30:
            direction = "WATCH"
        elif score >= 10:
            direction = "HOLD"
        elif score >= -10:
            direction = "WEAK"
        else:
            direction = "AVOID"

        # ── Position sizing (Kelly/vol-parity) ──
        if direction in ("STRONG_BUY", "BUY") and rvol > 0:
            if rvol < 15:
                position_pct = 8.0  # 8% portfolio
            elif rvol < 30:
                position_pct = 5.0
            elif rvol < 50:
                position_pct = 3.0
            elif rvol < 80:
                position_pct = 2.0
            else:
                position_pct = 1.0
            # Halve for crypto/commodity
            if cls in ("CRYPTO", "COMMODITY"):
                position_pct *= 0.5
        else:
            position_pct = 0

        # ── Suggest TP/SL based on ATR ──
        if direction in ("STRONG_BUY", "BUY") and atr_pct > 0:
            sl_pct = max(atr_pct * 1.5, 4.0)  # 1.5x ATR, minimum 4%
            tp_pct = sl_pct * 2.0  # 2:1 reward:risk minimum
            # For strong trend + low vol, wider TP
            if "TREND+DIP" in str(signals) and rvol < 30:
                tp_pct = max(tp_pct, 12.0)
        else:
            sl_pct = tp_pct = None

        return {
            "symbol": sym,
            "class": cls,
            "price": round(p_now, 4),
            "direction": direction,
            "score": round(score, 1),
            "signals": " | ".join(signals),
            "ret_5d": round(ret_5d, 1) if ret_5d else None,
            "ret_1m": round(ret_1m, 1) if ret_1m else None,
            "ret_3m": round(ret_3m, 1) if ret_3m else None,
            "ret_6m": round(ret_6m, 1) if ret_6m else None,
            "rsi": round(rsi_val, 1),
            "rsi_signal": rsi_sig,
            "bb_pct": round(bb_pct, 2),
            "rvol": round(rvol, 1),
            "sharpe": round(sharpe, 2),
            "max_dd": round(max_dd, 1),
            "atr_pct": round(atr_pct, 2),
            "position_size_pct": position_pct,
            "suggested_sl_pct": round(sl_pct, 1) if sl_pct else None,
            "suggested_tp_pct": round(tp_pct, 1) if tp_pct else None,
            "analyst": analyst_key if analyst_key else None,
            "analyst_n": analyst_n if analyst_n > 0 else None,
            "target_price": round(target_price, 2) if target_price else None,
            "upside_pct": round(upside, 1) if upside else None,
            "upside_pct_high": round(upside_high, 1) if upside_high else None,
            "fwd_pe": round(fwd_pe, 1) if fwd_pe else None,
            "peg": round(peg, 2) if peg else None,
            "eps_growth_pct": round(eps_growth * 100, 1) if eps_growth else None,
            "roe_pct": round(roe * 100, 1) if roe else None,
            "div_yield_pct": round(div_yield, 2) if div_yield else None,
            "market_cap": market_cap,
            "insider_shares": insider_shares,
            "db_n": db_n,
            "db_wr": db_wr,
            "db_avg_pnl": db_avg_pnl,
        }


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    ts = datetime.now(timezone.utc)
    date_str = ts.strftime("%Y-%m-%d")
    time_str = ts.strftime("%Y-%m-%d %H:%M UTC")

    scorer = QuantScorer()

    print(f"{'='*70}")
    print(f"  PICKS NOW — Professional Quant Screener")
    print(f"  {time_str}")
    print(f"{'='*70}")

    # Load DB edge data
    print("\n📥 Loading DB edge data...")
    db_edge = load_db_edge()
    print(f"   Loaded {len(db_edge)} symbols with resolved edge data.")

    all_results = []
    all_prices = {}

    for cls, config in UNIVERSE.items():
        tickers = config["tickers"]
        print(f"\n📊 Scanning [{cls}] ({len(tickers)} symbols)...")

        for sym in tickers:
            try:
                tk = yf.Ticker(sym)
                df = tk.history(period="6mo", interval="1d", auto_adjust=True)
                if df is None or len(df) < 60:
                    continue

                info = {}
                try:
                    info = tk.info or {}
                except Exception:
                    pass

                result = scorer.score(sym, cls, df, info, db_edge, all_prices)
                all_prices[sym] = result["price"]
                all_results.append(result)

                # Progress dot
                print(".", end="", flush=True)

            except Exception as e:
                pass  # silently skip failed symbols

        print(f" done — {sum(1 for r in all_results if r['class']==cls)} scored")

    # ── Build output ──
    df_res = pd.DataFrame(all_results)
    if df_res.empty:
        print("\n❌ No data collected. Check yfinance connectivity.")
        return

    # Rank by score within each class
    df_res['rank_in_class'] = df_res.groupby('class')['score'].rank(ascending=False)
    df_res = df_res.sort_values(['class', 'rank_in_class']).reset_index(drop=True)

    # ── Print report ──
    print(f"\n{'='*70}")
    print(f"  📋 PICKS NOW — ACTIONABLE SHORTLIST")
    print(f"{'='*70}")

    for cls in ["EQUITY", "ETF", "BOND", "FOREX", "COMMODITY", "CRYPTO"]:
        sub = df_res[df_res['class'] == cls].head(5)
        if sub.empty:
            continue

        buys = sub[sub['direction'].isin(["STRONG_BUY", "BUY"])]
        strong_buys = sub[sub['direction'] == "STRONG_BUY"]

        print(f"\n{'─'*70}")
        print(f"  {cls}")
        print(f"{'─'*70}")

        if not strong_buys.empty:
            print(f"  ★ STRONG BUYS:")
            for _, r in strong_buys.iterrows():
                tp = f" TP={r['suggested_tp_pct']:.0f}%" if r['suggested_tp_pct'] else ""
                sl = f" SL={r['suggested_sl_pct']:.0f}%" if r['suggested_sl_pct'] else ""
                alloc = f" size={r['position_size_pct']:.0f}%" if r['position_size_pct'] > 0 else ""
                anl = f" | {r['analyst']}({r['analyst_n']})" if r['analyst'] else ""
                upside = f" target=${r['target_price']:.0f}(+{r['upside_pct']:.0f}%)" if r['target_price'] else ""
                print(f"    {r['symbol']:8s} ${r['price']:<8.2f} score={r['score']:<5.0f}{alloc}{tp}{sl}{anl}{upside}")
                print(f"    {'':8s} {r['signals']}")

        if not buys.empty:
            print(f"  · BUYS:")
            for _, r in buys.iterrows():
                if r['direction'] == "STRONG_BUY":
                    continue
                tp = f" TP={r['suggested_tp_pct']:.0f}%" if r['suggested_tp_pct'] else ""
                sl = f" SL={r['suggested_sl_pct']:.0f}%" if r['suggested_sl_pct'] else ""
                alloc = f" size={r['position_size_pct']:.0f}%" if r['position_size_pct'] > 0 else ""
                print(f"    {r['symbol']:8s} ${r['price']:<8.2f} score={r['score']:<5.0f}{alloc}{tp}{sl}")
                print(f"    {'':8s} {r['signals']}")

        if strong_buys.empty and buys.empty:
            print(f"  (No actionable BUY signals today)")

    # ── Top 10 overall (sorted by score descending globally) ──
    print(f"\n{'='*70}")
    print(f"  🏆 TOP OVERALL PICKS")
    print(f"{'='*70}")
    top_all = (df_res[df_res['direction'].isin(["STRONG_BUY", "BUY"])]
               .sort_values('score', ascending=False)
               .head(10))
    for i, (_, r) in enumerate(top_all.iterrows(), 1):
        tp = f" → ${r['price']*(1+r['suggested_tp_pct']/100):.0f}" if r['suggested_tp_pct'] else ""
        sl = f" ($SL ${r['price']*(1-r['suggested_sl_pct']/100):.0f})" if r['suggested_sl_pct'] else ""
        anl = f" [{r['analyst']}({r['analyst_n']})]" if r['analyst'] else ""
        print(f"  #{i:<2} {r['symbol']:8s} [{r['class']:9s}] score={r['score']:<5.0f} ${r['price']:<8.2f}{tp}{sl}{anl}")
        print(f"      {r['signals']}")

    # ── Safest picks (lowest RVOL) ──
    print(f"\n{'='*70}")
    print(f"  🛡️  SAFEST PICKS (lowest volatility)")
    print(f"{'='*70}")
    safest = df_res[df_res['rvol'].notna()].nsmallest(5, 'rvol')
    for _, r in safest.iterrows():
        print(f"  {r['symbol']:8s} [{r['class']:9s}] RVOL={r['rvol']:.0f}% DRW_DN={r['max_dd']:.1f}% score={r['score']:.0f} {r['direction']}")

    # ── Market overview ──
    print(f"\n{'='*70}")
    print(f"  📊 MARKET OVERVIEW")
    print(f"{'='*70}")
    benchmarks = {"SPY": "EQUITY", "QQQ": "TECH", "TLT": "BONDS",
                  "GLD": "GOLD", "BTC-USD": "CRYPTO", "EURUSD=X": "FX"}
    for sym, label in benchmarks.items():
        if sym in all_prices:
            price = all_prices[sym]
            row = df_res[df_res['symbol'] == sym]
            if not row.empty:
                r = row.iloc[0]
                print(f"  {label:8s} ${price:<8.2f} | 5d={r['ret_5d']:+.1f}% 1m={r['ret_1m']:+.1f}% 3m={r['ret_3m']:+.1f}% rvol={r['rvol']:.0f}%")

    # ── Write JSON ──
    json_path = DATA_DIR / "picks_now.json"
    json_picks = (df_res[df_res['direction'].isin(["STRONG_BUY", "BUY"])]
                  .sort_values('score', ascending=False)
                  .head(20))
    json_data = {
        "generated_at": ts.isoformat(),
        "date": date_str,
        "market_regime": "RISK_OFF" if any(
            r['ret_5d'] and r['ret_5d'] < -3 for _, r in
            df_res[df_res['symbol'].isin(["SPY", "QQQ", "BTC-USD"])].iterrows()
        ) else "NEUTRAL",
        "n_scored": len(df_res),
        "picks": json_picks.to_dict("records"),
        "all": df_res.sort_values('score', ascending=False).head(50).to_dict("records"),
        "safest": safest.to_dict("records"),
    }
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2, default=str)
    print(f"\n📁 JSON: {json_path}")

    # ── Write markdown report ──
    md_path = REPORTS_DIR / f"PICKS_NOW_{date_str}.md"
    md_lines = [
        f"# PICKS NOW — Multi-Asset Quant Screener",
        f"**{time_str}** | NFA — Research/Paper Only",
        "",
        "---",
        "## Market Overview",
        "| Asset | Price | 5d% | 1m% | 3m% | Vol% |",
        "|-------|-------|-----|-----|-----|------|",
    ]
    for sym, label in benchmarks.items():
        row = df_res[df_res['symbol'] == sym]
        if not row.empty:
            r = row.iloc[0]
            md_lines.append(
                f"| {label} | ${r['price']:.2f} | {r['ret_5d']:+.1f}% | "
                f"{r['ret_1m']:+.1f}% | {r['ret_3m']:+.1f}% | {r['rvol']:.0f}% |"
            )

    md_lines.extend(["", "---", "## Top Picks by Asset Class", ""])
    for cls in ["EQUITY", "ETF", "BOND", "FOREX", "COMMODITY", "CRYPTO"]:
        sub = df_res[df_res['class'] == cls]
        buys = sub[sub['direction'].isin(["STRONG_BUY", "BUY"])].head(3)
        if buys.empty:
            continue
        md_lines.append(f"### {cls}")
        md_lines.append("| Symbol | Price | Score | Direction | Signals | TP% | SL% | Size% | Analyst |")
        md_lines.append("|--------|-------|-------|-----------|---------|-----|-----|-------|---------|")
        for _, r in buys.iterrows():
            anl = f"{r['analyst']}({r['analyst_n']})" if r['analyst'] else "-"
            tp = f"{r['suggested_tp_pct']:.0f}%" if r['suggested_tp_pct'] else "-"
            sl = f"{r['suggested_sl_pct']:.0f}%" if r['suggested_sl_pct'] else "-"
            sz = f"{r['position_size_pct']:.0f}%" if r['position_size_pct'] else "-"
            sig = r['signals'][:60]
            md_lines.append(
                f"| {r['symbol']} | ${r['price']:.2f} | {r['score']:.0f} | "
                f"{r['direction']} | {sig} | {tp} | {sl} | {sz} | {anl} |"
            )
        md_lines.append("")

    md_lines.extend(["---", "## Safest Picks (Lowest Volatility)", ""])
    md_lines.append("| Symbol | Class | RVOL% | Max DD% | Score | Direction |")
    md_lines.append("|--------|-------|-------|---------|-------|-----------|")
    for _, r in safest.iterrows():
        md_lines.append(
            f"| {r['symbol']} | {r['class']} | {r['rvol']:.0f}% | "
            f"{r['max_dd']:.1f}% | {r['score']:.0f} | {r['direction']} |"
        )
    md_lines.extend(["", "---", "*Generated by tools/picks_now_professional.py*"])

    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))
    print(f"📄 Report: {md_path}")

    print(f"\n{'='*70}")
    print(f"  ✅ Done — {len(all_results)} symbols scored")
    print(f"  STRONG_BUY: {len(df_res[df_res['direction']=='STRONG_BUY'])}")
    print(f"  BUY:        {len(df_res[df_res['direction']=='BUY'])}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
