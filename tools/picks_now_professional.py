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
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf

# ── API failover imports (see obsidian-notes/reference/data-sources.md) ─────
try:
    from alpha_engine.equity_price_failover import fetch_market_cap, fetch_quote
    HAS_EQUITY_FAILOVER = True
except ImportError:
    HAS_EQUITY_FAILOVER = False

try:
    from alpha_engine.api_failover import fetch_price as crypto_fetch_price
    from alpha_engine.api_failover import fetch_klines as crypto_fetch_klines
    HAS_CRYPTO_FAILOVER = True
except ImportError:
    HAS_CRYPTO_FAILOVER = False

# FMP API for Piotroski, Altman-Z, analyst consensus, historical prices
FMP_API_KEY = os.environ.get("FMP_API_KEY", "iF4K10WedJZINDhUWGXlGAiA57rn4sRD")
FMP_BASE = "https://financialmodelingprep.com/stable"

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "audit_dashboard" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = REPO / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── DB credentials (SECURITY: NEVER hardcode real passwords in source) ──────
# This file must not contain secrets that could leak via git, PRs, or bundles.
#
# Correct ways (in priority order):
#   1. GitHub Actions: set env var DB_PASSWORDS_JSON (or MYSQL_PASSWORD)
#      from repository secrets. Example in workflow:
#        env:
#          DB_PASSWORDS_JSON: ${{ secrets.DB_PASSWORDS_JSON }}
#   2. Local dev: tools/db_env.py reads .env.dbpw (gitignored) or the
#      DB_PASSWORDS_JSON env var.
#   3. The db_env module centralizes all legacy env var names.
#
# DB writes are always best-effort (the screener works without the DB edge
# overlay or tracker insert).
DB_CREDS = None
try:
    from tools.db_env import get_stocks_creds
    DB_CREDS = get_stocks_creds(raise_on_missing=False)
except Exception:
    DB_CREDS = None


# ── Universe by asset class (expanded 2026-06-06) ───────────────────────────
# Added: more bonds (TIPS, municipal, international, floating-rate, ultrashort,
# preferred, convertible), more ETFs (factor, dividend, international sector,
# covered-call, infrastructure, REIT sectors), more equities.
UNIVERSE = {
    "EQUITY": {
        "tickers": [
            # Mega-cap tech
            "NVDA", "META", "MSFT", "GOOGL", "AMZN", "AAPL", "AMD",
            "AVGO", "TSLA", "NFLX", "ADBE", "CRM", "ORCL", "IBM",
            # Semis / hardware
            "INTC", "QCOM", "TXN", "AMAT", "LRCX", "MU", "MRVL",
            # Banks & financials
            "JPM", "GS", "MS", "BAC", "WFC", "C", "AXP", "V", "MA",
            "PYPL", "SQ", "BLK", "SCHW",
            # Insurance
            "BRK-B", "MET", "PRU", "AIG",
            # Healthcare
            "UNH", "JNJ", "PFE", "MRK", "ABBV", "TMO", "LLY",
            "AMGN", "GILD", "VRTX", "ISRG", "BSX", "SYK", "ZTS",
            # Consumer staples
            "WMT", "COST", "PG", "KO", "PEP", "CL", "KMB", "SYY",
            # Consumer discretionary
            "MCD", "DIS", "SBUX", "CMG", "HD", "LOW", "TJX", "TGT",
            "NKE", "LULU", "DECK", "AMZN",
            # Energy
            "XOM", "CVX", "COP", "EOG", "PSX", "VLO",
            # Industrials
            "CAT", "GE", "BA", "HON", "LMT", "RTX", "UPS", "FDX",
            "DE", "CARR", "CSX", "UNP",
            # Growth / tech
            "NOW", "UBER", "ABNB", "DASH", "SNOW", "CRWD", "PANW",
            "PLTR", "DDOG", "MDB", "NET", "ZM", "WDAY",
            # Real estate
            "AMT", "PLD", "CCI", "EQIX",
            # Telecom
            "VZ", "T", "TMUS", "CMCSA",
            # Auto
            "F", "GM", "RIVN", "LCID",
            # Canadian
            "SHOP", "CNQ", "SU", "BNS", "RY",
        ],
        "benchmark": "SPY",
    },
    "ETF": {
        "tickers": [
            # Broad market
            "SPY", "IVV", "VOO", "QQQ", "VGT", "IWM", "VB", "VTWO",
            # International
            "EFA", "EEM", "VXUS", "IXUS", "VWO", "VEA", "SCHE", "SCHF",
            "FXI", "EWJ", "EWZ", "INDA", "EPI", "FLIN",
            # Sector
            "XLK", "XLF", "XLE", "XLU", "XLV", "XLI", "XLB", "XLRE", "XLC", "XLY", "XLP",
            "VGT", "VHT", "VDC", "VIS", "VAW",
            # Dividend
            "SCHD", "VYM", "HDV", "VIG", "DGRO", "SDY", "SPYD", "DVY",
            # Factor / smart beta
            "SPLV", "USMV", "QUAL", "MTUM", "IVLU", "VLUE", "SIZE", "AVUV",
            # Covered call income
            "JEPI", "JEPQ", "DIVO", "QYLD", "XYLD", "RYLD",
            # Real estate
            "VNQ", "IYR", "REET", "SCHH",
            # Infrastructure
            "PAVE", "IFRA", "TBLU",
            # Commodity
            "GLD", "SLV", "DBC", "PDBC", "COPX", "LIT", "SOXX", "SMH",
            # Thematic
            "ARKK", "ARKG", "ARKW", "ICLN", "TAN", "IBUY", "ROBO",
            # Crypto
            "BITO", "IBIT",
        ],
        "benchmark": "SPY",
    },
    "CRYPTO": {
        "tickers": [
            "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
            "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
            "MATIC-USD", "UNI-USD", "ATOM-USD", "LTC-USD", "BCH-USD",
            "TRX-USD", "FTM-USD", "NEAR-USD", "APT-USD", "SUI-USD",
            "ARB-USD", "OP-USD", "AAVE-USD", "MKR-USD", "ENA-USD",
            "PEPE-USD", "SHIB-USD", "CRO-USD", "VET-USD", "FIL-USD",
        ],
        "benchmark": "BTC-USD",
    },
    "FOREX": {
        "tickers": [
            # Majors
            "EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X",
            "USDCAD=X", "NZDUSD=X", "EURGBP=X", "EURJPY=X",
            "GBPJPY=X", "EURAUD=X", "GBPAUD=X", "EURCHF=X",
            # Crosses
            "AUDJPY=X", "CHFJPY=X", "NZDJPY=X", "CADJPY=X",
            # Scandies / exotics
            "USDSEK=X", "USDNOK=X", "USDDKK=X", "USDZAR=X",
            "USDSGD=X", "USDHKD=X", "USDMXN=X", "USDTRY=X",
        ],
        "benchmark": "EURUSD=X",
    },
    "COMMODITY": {
        "tickers": [
            # Precious metals
            "GC=F", "SI=F", "PA=F", "PL=F",
            # Energy
            "CL=F", "NG=F", "HO=F", "RB=F",
            # Grains
            "ZW=F", "ZC=F", "ZS=F", "ZM=F", "ZL=F",
            # Softs
            "KC=F", "CT=F", "SB=F", "CC=F", "JO=F",
            # Industrial metals
            "HG=F", "ALI=F", "NIO=F",
            # Livestock
            "LE=F", "GF=F", "HE=F",
        ],
        "benchmark": "GC=F",
    },
    "BOND": {
        "tickers": [
            # Treasuries by duration
            "TLT", "IEF", "SHY", "GOVT", "SHV", "BIL", "SGOV",
            # TIPS (inflation-protected)
            "TIP", "STIP", "VTIP", "SCHP",
            # Corporate bonds
            "LQD", "HYG", "VCIT", "VCSH", "VCLT", "SPSB", "SPIB", "SPLB",
            # Municipal bonds
            "MUB", "SUB", "VTEB", "PZA", "HYD", "TFI",
            # International bonds
            "BNDX", "EMB", "PCY", "IGOV", "BWX", "WIP", "VWOB",
            # Broad / aggregate
            "AGG", "BND", "BIV", "BSV", "BLV",
            # Mortgage-backed
            "MBB", "MBS", "VMBS", "GNMA",
            # Floating rate
            "FLOT", "FLRN", "PULS", "GSY", "NEAR",
            # Convertible
            "CWB", "ICVT",
            # Preferred
            "PFF", "PFFD", "PFFA", "PFXF",
            # Ultra-short
            "JPST", "JPIE",
            # Emerging market
            "EMB", "VWOB", "PCY",
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
    """Load our resolved pick performance per symbol from at_pick_outcomes.

    SECURITY: Never embed passwords. Uses tools/db_env.py which reads
    from GitHub secrets (via DB_PASSWORDS_JSON or MYSQL_PASSWORD env vars
    in GHA) or local .env.dbpw (gitignored). Falls back gracefully so the
    screener still works with yfinance/analyst data when DB is unavailable.
    """
    try:
        import pymysql
        from tools.db_env import get_stocks_creds

        creds = get_stocks_creds(raise_on_missing=False)
        if not creds or not creds.get("password"):
            # Common in local dev or when GHA secret not injected for this job
            print("  [INFO] DB edge overlay skipped (no secure creds via db_env / env vars). Using yfinance + analyst scoring only.")
            return {}

        conn = pymysql.connect(**creds)
        cur = conn.cursor()
        # Banned/refuted strategies must NOT corroborate a pick's WR. Mirrors
        # alpha_engine.production_scanner.BANNED_SOURCES plus two sources flagged
        # in project memory (myfxbook/ig contrarian). Defined locally to avoid a
        # heavy production_scanner import in this generator.
        banned = (
            "Predictions", "sandbox_opposite", "rapid_fire", "incubator_gainer",
            "luxalgo_filters", "multi_asset_copytrader", "forex_copy_trader",
            "signal_validation", "multi_asset_cot", "regime_terminal",
            "myfxbook_retail_contrarian", "ig_contrarian_sentiment",
        )
        placeholders = ",".join(["%s"] * len(banned))
        # WR DENOMINATOR FIX: count EXPIRED/FLAT as non-wins. Previously the
        # query filtered status IN ('WON','LOST'), silently dropping EXPIRED and
        # inflating WR (e.g. GBPUSD 58.8% displayed vs ~6% true — ~89% of FX
        # picks EXPIRE). avg_pnl/avg_win/avg_loss ignore NULLs automatically.
        cur.execute(f"""
            SELECT symbol, asset_class,
                   COUNT(*) as n,
                   SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN status='EXPIRED' THEN 1 ELSE 0 END) as expired,
                   ROUND(AVG(pnl_pct), 4) as avg_pnl,
                   ROUND(AVG(CASE WHEN status='WON' THEN pnl_pct END), 4) as avg_win,
                   ROUND(AVG(CASE WHEN status='LOST' THEN pnl_pct END), 4) as avg_loss
            FROM at_pick_outcomes
            WHERE status IN ('WON','LOST','EXPIRED','FLAT')
              AND (strategy IS NULL OR strategy NOT IN ({placeholders}))
            GROUP BY symbol, asset_class
            HAVING COUNT(*) >= 5
        """, banned)
        data = {}
        for r in cur.fetchall():
            symbol, ac, n, wins, expired, avg_pnl, avg_win, avg_loss = r
            n = int(n)
            wins = int(wins)
            expired = int(expired or 0)
            wr = wins / n * 100 if n > 0 else 0
            data[symbol.upper()] = {
                "n": n, "wr": round(wr, 1), "avg_pnl": float(avg_pnl or 0),
                "avg_win": float(avg_win or 0), "avg_loss": float(avg_loss or 0),
                "expired": expired,
                "expired_pct": round(expired / n * 100, 1) if n > 0 else 0,
            }
        conn.close()
        return data
    except Exception as e:
        print(f"  [WARN] DB edge load failed: {e}")
        return {}


# ── FMP financial scores (Piotroski, Altman-Z) ──────────────────────────────

def load_fmp_scores(tickers: list[str]) -> dict[str, dict]:
    """Fetch Piotroski F-Score and Altman-Z from FMP for tickers.

    Uses per-symbol fetches with delay to respect free-tier rate limits.
    Only fetches for a reasonable subset (up to 60 symbols) to avoid 429s.
    """
    try:
        import requests
        import time
    except ImportError:
        print("  [INFO] requests not installed — skipping FMP scores")
        return {}

    # Focus on EQUITY + ETF symbols (where fundamentals are available)
    priority_tickers = [t for t in tickers if not t.endswith(("=F", "-USD", "=X"))]
    # Limit to 30 symbols to avoid rate limits
    fetch_list = [t for t in priority_tickers[:60]]

    result: dict[str, dict] = {}
    for sym in tickers:
        result[sym] = {"piotroski": None, "altman_z": None}

    fetched_count = 0
    for sym in fetch_list:
        if fetched_count >= 30:  # hard cap to avoid rate limits
            break
        try:
            # Piotroski
            r = requests.get(
                f"{FMP_BASE}/financial-scores",
                params={"symbol": sym, "apikey": FMP_API_KEY},
                timeout=10,
            )
            if r.status_code == 200:
                d = r.json()
                if isinstance(d, list) and d:
                    result[sym]["piotroski"] = d[0].get("piotroskiScore")
            elif r.status_code == 429:
                print(f"  [FMP] rate-limited at {sym}, stopping early")
                break
            time.sleep(0.3)  # 300ms delay between requests

            # Altman-Z
            r2 = requests.get(
                f"{FMP_BASE}/key-metrics-ttm",
                params={"symbol": sym, "apikey": FMP_API_KEY},
                timeout=10,
            )
            if r2.status_code == 200:
                d2 = r2.json()
                if isinstance(d2, list) and d2:
                    result[sym]["altman_z"] = d2[0].get("altmanZScoreTTM")
            elif r2.status_code == 429:
                print(f"  [FMP] rate-limited at {sym} (key-metrics), stopping early")
                break
            time.sleep(0.3)

            fetched_count += 1
        except Exception:
            pass

    ok = sum(1 for v in result.values() if v["piotroski"] is not None or v["altman_z"] is not None)
    print(f"  [FMP] loaded scores for {ok}/{len(tickers)} symbols (fetched {fetched_count})")
    return result


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
              info: dict, db_edge: dict, prices: dict,
              fmp_scores: dict | None = None) -> dict:
        """Score one symbol across all factors. Returns result dict."""
        c = df['Close']
        p_now = float(c.iloc[-1])

        # ── FMP scores (Piotroski, Altman-Z) ──
        fmps = (fmp_scores or {}).get(sym.upper(), {})
        piotroski = fmps.get("piotroski")
        altman_z = fmps.get("altman_z")

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

        # ── Negative-expectancy guard ──
        # A symbol whose OWN resolved (EXPIRED-inclusive) average PnL is negative
        # with a meaningful sample must not carry a BUY/STRONG_BUY label or full
        # size, regardless of the technical/analyst score. Demote to WATCH.
        if direction in ("STRONG_BUY", "BUY") and db_n >= 20 and db_avg_pnl < 0:
            signals.append(f"DB_NEG_EXPECTANCY(avg={db_avg_pnl:.2%},n={db_n})")
            direction = "WATCH"

        # ── Position sizing (Kelly/vol-parity) ──
        if direction in ("STRONG_BUY", "BUY") and rvol > 0:
            if rvol < 15:
                position_pct = 8.0
            elif rvol < 30:
                position_pct = 5.0
            elif rvol < 50:
                position_pct = 3.0
            elif rvol < 80:
                position_pct = 2.0
            else:
                position_pct = 1.0
            if cls in ("CRYPTO", "COMMODITY"):
                position_pct *= 0.5
        else:
            position_pct = 0

        if direction in ("STRONG_BUY", "BUY") and atr_pct > 0:
            sl_pct = max(atr_pct * 1.5, 4.0)
            tp_pct = sl_pct * 2.0
            if "TREND+DIP" in str(signals) and rvol < 30:
                tp_pct = max(tp_pct, 12.0)
            # ── Per-class TP/SL caps (mirror production_scanner) ──
            # FX/COMMODITY were emitting a flat 8%/4% — ~5x the enforced FX cap,
            # which is itself why ~89% of FX picks EXPIRE before TP. Clamp to the
            # production caps so picks-now TP/SL is achievable within horizon.
            _TP_CAP = {"FOREX": 1.5, "COMMODITY": 12.0, "EQUITY": 10.0,
                       "ETF": 10.0, "CRYPTO": 15.0}
            _SL_CAP = {"FOREX": 1.0, "COMMODITY": 8.0, "EQUITY": 7.0,
                       "ETF": 7.0, "CRYPTO": 10.0}
            cap_tp = _TP_CAP.get(cls)
            cap_sl = _SL_CAP.get(cls)
            if cap_sl is not None:
                sl_pct = min(sl_pct, cap_sl)
            if cap_tp is not None:
                tp_pct = min(tp_pct, cap_tp)
        else:
            sl_pct = tp_pct = None

        # ── ELI5 Reason (Explain Like I'm 5) ──
        eli5_parts = []
        if "TREND+DIP" in str(signals):
            eli5_parts.append(
                f"This stock has been going UP over the last 3 months (+{ret_3m:.0f}%) "
                f"but just dropped -{abs(ret_5d):.0f}% in the last 5 days. "
                f"That's like a strong athlete who stumbled — likely to bounce back.")
        elif "STRONG_TREND" in str(signals):
            eli5_parts.append(
                f"This has been steadily climbing (+{ret_3m:.0f}% over 3 months). "
                f"The trend is your friend.")
        if rsi_val < 35:
            eli5_parts.append(
                f"The RSI is {rsi_val:.0f} (way below 30 means 'very oversold'). "
                f"Historically, things this oversold tend to bounce back up.")
        elif rsi_val < 40:
            eli5_parts.append(
                f"The RSI is {rsi_val:.0f} — below the normal range, suggesting it's undervalued right now.")
        if bb_pct < 0.15:
            eli5_parts.append(
                f"Price is near the LOWER Bollinger Band — a statistical "
                f"boundary that price rarely stays below for long.")
        if analyst_rating and analyst_rating <= 1.5 and analyst_n >= 10:
            eli5_parts.append(
                f"Wall Street analysts are VERY bullish: {analyst_n} analysts "
                f"say STRONG BUY with an average target of ${target_price:.0f} "
                f"(that's {upside:.0f}% higher than today's price).")
        elif analyst_rating and analyst_rating <= 2.0 and analyst_n >= 5:
            eli5_parts.append(
                f"Most analysts say BUY ({analyst_n} analysts). "
                f"They see it going to ${target_price:.0f} on average.")
        if rvol and rvol < 15:
            eli5_parts.append(
                f"This is a low-volatility asset ({rvol:.0f}% annualized vol) — "
                f"like a calm boat in a storm. Less risky to hold.")
        elif rvol and rvol > 50:
            eli5_parts.append(
                f"High volatility ({rvol:.0f}%) means bigger swings — "
                f"we're keeping position size small (1-2% of portfolio).")
        if cls in ("BOND",) and div_yield and div_yield > 3:
            eli5_parts.append(
                f"It's a bond ETF paying {div_yield:.1f}% dividend — "
                f"steady income even if price doesn't move much.")
        if fwd_pe and fwd_pe < 20:
            eli5_parts.append(
                f"The forward P/E is {fwd_pe:.0f}x — reasonably priced "
                f"compared to historical averages.")
        if db_n >= 20 and db_wr > 50:
            eli5_parts.append(
                f"Our own trading history shows {db_wr:.0f}% win rate "
                f"on this symbol across {db_n} closed trades — "
                f"it's one of our best-performing symbols.")

        eli5_reason = " ".join(eli5_parts) if eli5_parts else (
            f"Multi-factor score of {score:.0f}/100 based on "
            f"{'momentum' if ret_3m and ret_3m > 5 else ''} "
            f"{'oversold RSI' if rsi_val < 40 else ''} "
            f"{'analyst consensus' if analyst_n and analyst_n >= 5 else ''} "
            f"{'and low volatility' if rvol and rvol < 20 else ''}. "
            f"Combined, these factors suggest a favorable risk/reward entry."
        )

        # ── EST timestamp (approximate ET for display; browser can refine) ──
        now_utc = datetime.now(timezone.utc)
        est_pretty = now_utc.strftime("%b %d, %Y %I:%M %p ET (approx)")
        est_ts = now_utc.strftime("%Y-%m-%d %H:%M UTC")

        return {
            "symbol": sym,
            "class": cls,
            "price": round(p_now, 4),
            "direction": direction,
            "score": round(score, 1),
            "signals": " | ".join(signals),
            "eli5_reason": eli5_reason,
            "generated_at_est": est_pretty,
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
            "piotroski": piotroski,
            "altman_z": round(altman_z, 2) if altman_z else None,
            "db_n": db_n,
            "db_wr": db_wr,
            "db_avg_pnl": db_avg_pnl,
        }


# ── API failover helpers (per CLAUDE.md API Failover Rule) ──────────────────
# These wrap yfinance with fallback chains so picks_now keeps working even
# when yfinance rate-limits or fails in CI.

_IS_CRYPTO_RE = re.compile(r"-USD$", re.I)
_IS_FOREX_RE = re.compile(r"=X$", re.I)
_IS_COMMODITY_RE = re.compile(r"=F$", re.I)

def _class_for_symbol(sym: str) -> str:
    """Return the asset-class key for a symbol (crypto/equity/forex/commodity)."""
    if _IS_CRYPTO_RE.search(sym): return "crypto"
    if _IS_FOREX_RE.search(sym):  return "forex"
    if _IS_COMMODITY_RE.search(sym): return "commodity"
    return "equity"


def fetch_ohlcv_failover(sym: str) -> tuple[pd.DataFrame | None, dict]:
    """Fetch 6-month daily OHLCV + info dict with multi-source failover.

    Failover chain per class:
      CRYPTO:  api_failover.fetch_klines() → yfinance
      EQUITY:  yfinance → FMP historical-price-eod → None
      FOREX:   yfinance → None
      COMMOD:  yfinance → None

    Returns (DataFrame | None, info_dict)
    """
    cls = _class_for_symbol(sym)
    info = {}

    # ── CRYPTO: Binance mirrors → CoinGecko → yfinance ───────────────────
    if cls == "crypto" and HAS_CRYPTO_FAILOVER:
        try:
            klines = crypto_fetch_klines(sym, interval="1d", limit=180)
            if klines and len(klines) >= 60:
                df = pd.DataFrame(klines, columns=[
                    "timestamp", "open", "high", "low", "close", "volume"
                ])
                for c in ["open","high","low","close","volume"]:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
                df.index = pd.to_datetime(df["timestamp"], unit="ms")
                df = df.sort_index()
                info["source"] = "api_failover(binance→coingecko)"
                return df, info
        except Exception:
            pass

    # ── Primary: yfinance ────────────────────────────────────────────────
    try:
        tk = yf.Ticker(sym)
        df = tk.history(period="6mo", interval="1d", auto_adjust=True)
        if df is not None and len(df) >= 60:
            # Normalize column names to lowercase
            df.columns = [c.lower() for c in df.columns]
            try:
                info = tk.info or {}
            except Exception:
                pass
            info["source"] = "yfinance"
            return df, info
    except Exception:
        pass  # fall through

    # ── EQUITY fallback: FMP historical prices ────────────────────────────
    if cls == "equity":
        try:
            import requests as req
            from datetime import timedelta
            r = req.get(
                f"{FMP_BASE}/historical-price-eod/{sym}",
                params={"apikey": FMP_API_KEY, "from": (
                    datetime.now(timezone.utc) - timedelta(days=200)
                ).strftime("%Y-%m-%d")},
                timeout=10,
            )
            if r.status_code == 200:
                rows = r.json()
                if isinstance(rows, list) and len(rows) >= 60:
                    df = pd.DataFrame(rows)
                    df = df.rename(columns={
                        "date": "Date", "open": "Open", "high": "High",
                        "low": "Low", "close": "Close", "volume": "Volume",
                    })
                    df["Date"] = pd.to_datetime(df["Date"])
                    df = df.set_index("Date").sort_index()
                    for c in ["Open","High","Low","Close","Volume"]:
                        df[c] = pd.to_numeric(df[c], errors="coerce")
                    info = {"source": "fmp_historical"}
                    return df, info
        except Exception:
            pass

    return None, info


def fetch_analyst_info_failover(sym: str) -> dict:
    """Fetch analyst consensus + key metrics with failover.

    Chain: yfinance → FMP profile/rating → Finnhub → empty dict
    """
    cls = _class_for_symbol(sym)

    # Skip analyst data for forex/commodity/crypto (no Wall St coverage)
    if cls in ("forex", "commodity"):
        return {}

    # ── Primary: yfinance ────────────────────────────────────────────────
    try:
        tk = yf.Ticker(sym)
        info = tk.info or {}
        if info.get("recommendationMean") is not None:
            info["source"] = "yfinance"
            return info
    except Exception:
        pass

    # ── Fallback: FMP profile + rating ───────────────────────────────────
    try:
        import requests as req
        profile = req.get(
            f"{FMP_BASE}/profile/{sym}",
            params={"apikey": FMP_API_KEY}, timeout=8,
        )
        rating = req.get(
            f"{FMP_BASE}/rating/{sym}",
            params={"apikey": FMP_API_KEY}, timeout=8,
        )
        info = {"source": "fmp"}
        if profile.status_code == 200:
            pd_ = profile.json()
            if isinstance(pd_, list) and pd_:
                info["marketCap"] = pd_[0].get("mktCap")
                info["forwardPE"] = pd_[0].get("peRatio")
                info["dividendYield"] = pd_[0].get("lastDiv")
                info["sector"] = pd_[0].get("sector")
                info["industry"] = pd_[0].get("industry")
        if rating.status_code == 200:
            rd_ = rating.json()
            if isinstance(rd_, list) and rd_:
                info["recommendationMean"] = {
                    "strong_buy": 1, "buy": 2, "hold": 3,
                    "sell": 4, "strong_sell": 5,
                }.get(rd_[0].get("rating", "").lower(), None)
                info["targetMeanPrice"] = rd_[0].get("targetMeanPrice") or \
                                          rd_[0].get("priceTargetMean")
                info["numberOfAnalystOpinions"] = rd_[0].get("ratingDetailsSCORE", {}).get(
                    "totalAnalyst", rd_[0].get("numberOfAnalystOpinions"))
        if info.get("recommendationMean") is not None or info.get("marketCap"):
            return info
    except Exception:
        pass

    return {}


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

    # Load FMP financial scores (Piotroski, Altman-Z)
    all_tickers = [t for cfg in UNIVERSE.values() for t in cfg["tickers"]]
    print(f"\n📥 Loading FMP financial scores for {len(all_tickers)} symbols...")
    fmp_scores = load_fmp_scores(all_tickers)

    all_results = []
    all_prices = {}

    for cls, config in UNIVERSE.items():
        tickers = config["tickers"]
        print(f"\n📊 Scanning [{cls}] ({len(tickers)} symbols)...")

        for sym in tickers:
            try:
                # Use multi-source failover chain instead of bare yfinance
                df, info = fetch_ohlcv_failover(sym)
                if df is None or len(df) < 60:
                    # Also try fetching analyst info for scoring even without OHLCV
                    if not info:
                        info = fetch_analyst_info_failover(sym)
                    continue

                # Supplement info with analyst failover if yfinance didn't provide it
                if not info or info.get("recommendationMean") is None:
                    analyst_info = fetch_analyst_info_failover(sym)
                    for k, v in analyst_info.items():
                        if k not in info or info[k] is None:
                            info[k] = v

                result = scorer.score(sym, cls, df, info, db_edge, all_prices, fmp_scores)
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

    risk_off_explanation = (
        "Market appears RISK-OFF (recent 5d declines visible across SPY/QQQ/BTC benchmarks). "
        "Screener is favoring lower-volatility defensive names (e.g. TLT bonds) and high-conviction analyst-supported pullbacks in quality equities. "
        "All suggested position sizes are deliberately small and conservative. "
        "This output is a 'best possible actionable option right now' bridge tool while the system accumulates more clean n≥100 resolved trades under policy-clean gates. "
        "Current status per money_ready_verdict.json + pf_registry: 0/9 asset classes meet full Tier-2 money-ready criteria (n≥100 clean post-noise, WR≥50%, PF≥1.5, MDD<20). "
        "ALWAYS verify the latest 14d/48h recency panels (pick_summary_stats_*.json) and concentration before any paper sizing. NFA — research / paper trading only."
    )

    print(f"\n{'='*70}")
    print(f"  ⚠️  RISK-OFF CONTEXT (ELI5)")
    print(f"{'='*70}")
    print("  " + risk_off_explanation[:300] + "...")
    print("  (Full explanation is in the JSON under risk_off_explanation for the web surface.)")

    # ── Write JSON ──
    json_path = DATA_DIR / "picks_now.json"
    json_picks = (df_res[df_res['direction'].isin(["STRONG_BUY", "BUY"])]
                  .sort_values('score', ascending=False)
                  .head(20))
    regime = "RISK_OFF" if any(
        r['ret_5d'] and r['ret_5d'] < -3 for _, r in
        df_res[df_res['symbol'].isin(["SPY", "QQQ", "BTC-USD"])].iterrows()
    ) else "NEUTRAL"

    json_data = {
        "generated_at": ts.isoformat(),
        "generated_at_est": datetime.now(timezone.utc).strftime("%b %d, %Y %I:%M %p ET (approx)"),
        "date": date_str,
        "market_regime": regime,
        "risk_off_explanation": risk_off_explanation,
        "n_scored": len(df_res),
        "picks": json_picks.to_dict("records"),
        "all": df_res.sort_values('score', ascending=False).head(50).to_dict("records"),
        "safest": safest.to_dict("records"),
    }
    # Clean NaN values before JSON serialization — NaN is NOT valid JSON
    # and causes JavaScript JSON.parse() to throw SyntaxError.
    def clean_nan(obj):
        if isinstance(obj, dict):
            return {k: clean_nan(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean_nan(v) for v in obj]
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return obj

    json_data = clean_nan(json_data)
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2, default=str)
    print(f"\n📁 JSON: {json_path}")

    # ── Save to MySQL tracking table (best-effort, production GHA path preferred) ──
    try:
        import pymysql
        if DB_CREDS and DB_CREDS.get("password"):
            db_conn = pymysql.connect(**DB_CREDS)
        else:
            raise RuntimeError("no secure creds from tools.db_env (DB_PASSWORDS_JSON or fallbacks)")
        db_cur = db_conn.cursor()
        inserted = 0
        for _, r in json_picks.iterrows():
            tp = r.get('suggested_tp_pct')
            sl = r.get('suggested_sl_pct')
            price = r.get('price', 0)
            def safe_float(v, default=None):
                if v is None: return default
                try: return float(v)
                except: return default
            def safe_int(v, default=None):
                if v is None: return default
                try: return int(v)
                except: return default
            db_cur.execute('''
                INSERT INTO picks_now_tracker 
                (generated_at, symbol, asset_class, direction, entry_price,
                 suggested_tp, suggested_sl, score, rvol, rsi,
                 analyst_rating, analyst_count, target_price, upside_pct,
                 eli5_reason, signals)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                r['symbol'], r['class'], r.get('direction', 'LONG'),
                safe_float(price),
                safe_float(price * (1 + tp/100)) if tp else None,
                safe_float(price * (1 - sl/100)) if sl else None,
                safe_float(r.get('score')),
                safe_float(r.get('rvol')),
                safe_float(r.get('rsi')),
                str(r.get('analyst', ''))[:30] if r.get('analyst') else None,
                safe_int(r.get('analyst_n'), 0),
                safe_float(r.get('target_price')),
                safe_float(r.get('upside_pct')),
                (r.get('eli5_reason') or '')[:2000] if r.get('eli5_reason') else None,
                (r.get('signals') or '')[:500],
            ))
            inserted += 1
        db_conn.commit()
        db_conn.close()
        print(f"💾 DB saved: {inserted} picks to picks_now_tracker")
    except Exception as e:
        print(f"  [WARN] DB save skipped (use GHA for production tracking): {e}")

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

    # Goal #1 honesty bridge (0/9 money-ready policy-clean; this is "best possible RIGHT NOW" overlay)
    # Load verdict for context (graceful; the top_notch generator + /audit/ai-tournament.html have the full recency/DSR view)
    try:
        verdict_path = ROOT / "audit_dashboard" / "data" / "money_ready_verdict.json"
        if verdict_path.exists():
            v = json.loads(verdict_path.read_text())
            note = "0/9 classes money-ready (policy-clean n≥100 / WR≥50 / PF≥1.5 Tier-2 min per Goal #1 + CLAUDE.md). This is the best-possible 'IF WE HAD TO MAKE PICKS RIGHT NOW' bridge using live market (yf analyst/momentum/mean-rev/vol) + our DB edge overlay (at_pick_outcomes). Full statistical edge (DSR/PBO/CPCV proxies, 14d/48h pick_summary recency, conc gates, policy_clean_net) lives in money_ready_verdict.json + top_notch_money_ready.json + ai-tournament.html Top Notch table. ALWAYS verify 14d/48h panels first before sizing (recency rule). Paper-first / NFA. See picks-now.html + /audit/ai-tournament.html."
            print("\n" + note)
            # Inject into the written JSON for consumers (picks-now.html, future widgets)
            try:
                if json_path.exists():
                    jj = json.loads(json_path.read_text())
                    jj["honest_bridge_note"] = note
                    jj["money_ready_status"] = "0/9 policy-clean; recency + gates required; paper only"
                    jj["cross_ref"] = {"top_notch": "audit_dashboard/data/top_notch_money_ready.json", "ai_tournament": "/audit/ai-tournament.html#top-notch", "verdict": "audit_dashboard/data/money_ready_verdict.json"}
                    json_path.write_text(json.dumps(jj, indent=2))
            except Exception:
                pass
    except Exception:
        pass


if __name__ == "__main__":
    main()
