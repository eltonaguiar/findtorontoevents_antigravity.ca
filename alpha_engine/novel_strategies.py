"""
ALPHA_ENGINE -- Novel Quick-Win Strategies
==========================================
3 strategies built on data pipelines we already have:

Strategy 1: vrp_signal (Variance Risk Premium)
  DVOL (implied vol from Deribit) - realized vol (Binance klines)
  VRP > 15 → SHORT vol (mean reversion, price stabilization)
  VRP < -5 → LONG vol (expect breakout)
  Data: Deribit DVOL (free) + Binance 30d klines (free)
  Ref: Deribit Research (2019-2024): IV > RV 70% of time, median premium 14 pts

Strategy 2: stablecoin_flow_onchain (Stablecoin Flow Signal)
  Monitor USDT Treasury wallet via Etherscan API
  Large MINT (>$50M Treasury outflow) → bullish (new capital entering)
  Large BURN (>$50M Treasury inflow) → bearish (capital leaving)
  Data: Etherscan token transfers (free API key)
  Ref: Wei, Bianchi & Liao (2024 JFE) — stablecoin supply leads crypto 2-5 days

Strategy 3: correlation_breakout (Realized Correlation Breakout)
  30-day rolling correlation between BTC and SPY
  Corr < 0.3 → decorrelation → BTC moving independently → trend signal
  Corr > 0.7 → high correlation → use stock sentiment as proxy
  Data: Binance BTC klines + yfinance SPY (both free)
  Ref: Bouri et al. (2020 JFE): BTC-equity corr regime shifts predict 15-25% moves

All strategies:
  - source_system: "novel_strategies"
  - Non-fatal (try/except everything)
  - Standard active_picks.json output format
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Windows UTF-8 fix
if sys.platform == "win32":
    for _stream in ("stdout", "stderr"):
        _s = getattr(sys, _stream, None)
        if _s and hasattr(_s, "fileno"):
            try:
                setattr(sys, _stream,
                        open(_s.fileno(), mode="w", encoding="utf-8",
                             closefd=False, errors="replace"))
            except Exception:
                pass

# Import from config (works both as module import and standalone)
try:
    from config import CRYPTO_SYMBOLS, fetch_binance_json, DATA_DIR
except ImportError:
    CRYPTO_SYMBOLS = {}
    DATA_DIR = Path(__file__).resolve().parent / "data"
    def fetch_binance_json(path, **kw):
        return None

try:
    from indicators import rsi, atr, sma
except ImportError:
    rsi = atr = sma = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    """Fetch JSON from URL with error handling."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _get_etherscan_key() -> str:
    """Load Etherscan API key from env vars, with Windows PowerShell fallback."""
    key = os.environ.get("ETHERSCAN_API_KEY", "") or os.environ.get("ETHERSCAN_KEY", "")
    if key:
        return key

    # Windows: read from User-level registry
    if sys.platform == "win32":
        try:
            import subprocess
            for name in ("ETHERSCAN_API_KEY", "ETHERSCAN_KEY"):
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"[Environment]::GetEnvironmentVariable('{name}', 'User')"],
                    capture_output=True, text=True, timeout=5
                )
                val = result.stdout.strip()
                if val:
                    return val
        except Exception:
            pass

    return ""


# ---------------------------------------------------------------------------
# Cache for Etherscan calls (avoid rate limits)
# ---------------------------------------------------------------------------
_etherscan_cache: dict = {"data": None, "ts": 0}
_ETHERSCAN_CACHE_TTL = 600  # 10 minutes


# =====================================================================
# STRATEGY 1: Variance Risk Premium (VRP)
# =====================================================================
# Enhanced version: uses Binance 1h klines for precise 30-day realized vol,
# and Deribit DVOL for implied vol. VRP = DVOL - RV.
#
# Thresholds (from user research):
#   VRP > 15  → SHORT vol (IV expensive, expect mean reversion)
#   VRP < -5  → LONG vol (IV cheap, expect breakout)
#
# Note: differs from advanced_strategies.py vol_risk_premium which uses
# VRP > 10 threshold and daily close data. This version uses 1h klines
# for more precise RV calculation and higher thresholds for conviction.
# =====================================================================

def vrp_signal(data: dict[str, pd.DataFrame],
               context: Optional[dict] = None) -> list[dict]:
    """Variance Risk Premium: DVOL vs 30-day realized vol from hourly klines."""
    signals = []

    try:
        # --- Step 1: Get BTC price from data dict ---
        btc_df = data.get("BTC-USD") or data.get("BTCUSDT")
        if btc_df is None or len(btc_df) < 30:
            return signals

        price = float(btc_df["Close"].iloc[-1])

        # --- Step 2: Fetch 30-day hourly klines from Binance for precise RV ---
        # 30 days * 24 hours = 720 candles
        klines_path = "/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=720"
        klines_data = fetch_binance_json(klines_path)

        if klines_data and len(klines_data) >= 168:  # At least 7 days
            closes = [float(k[4]) for k in klines_data]  # Close price is index 4
            returns = pd.Series(closes).pct_change().dropna()
            # Annualized realized vol: hourly std * sqrt(24*365)
            rv_30d = float(returns.std() * np.sqrt(24 * 365) * 100)
        else:
            # Fallback: use daily data from the data dict
            close = btc_df["Close"]
            returns = close.pct_change().dropna()
            if len(returns) < 20:
                return signals
            rv_30d = float(returns.tail(30).std() * np.sqrt(365) * 100)

        # --- Step 3: Fetch DVOL from Deribit ---
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = now_ms - 7200_000  # Last 2 hours (wider window for reliability)
        dvol_url = (
            f"https://www.deribit.com/api/v2/public/get_volatility_index_data"
            f"?currency=BTC&start_timestamp={start_ms}&end_timestamp={now_ms}"
            f"&resolution=3600"
        )
        dvol_data = _fetch_json(dvol_url, timeout=12)

        if not dvol_data or "result" not in dvol_data:
            return signals

        dvol_points = dvol_data["result"].get("data", [])
        if not dvol_points:
            return signals

        # DVOL format: [timestamp, open, high, low, close]
        latest_dvol = float(dvol_points[-1][4])

        # --- Step 4: Compute VRP ---
        vrp = latest_dvol - rv_30d

        # --- Step 5: Generate signals ---
        if vrp > 15:
            # IV is expensive → expect mean reversion → SHORT vol
            # In crypto: this means range-bound / slight decline expected
            confidence = min(0.85, 0.58 + vrp * 0.012)
            tp_mult = 0.94  # 6% target
            sl_mult = 1.035  # 3.5% stop
            rr = (price - price * tp_mult) / (price * sl_mult - price)

            signals.append({
                "strategy": "vrp_signal",
                "symbol": "BTCUSDT",
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(price * tp_mult),
                "stop_loss": _smart_round(price * sl_mult),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "source_system": "novel_strategies",
                "reason": (f"Variance Risk Premium: DVOL={latest_dvol:.1f}%, "
                           f"RV(30d)={rv_30d:.1f}%, VRP=+{vrp:.1f}pts (>15 threshold). "
                           f"IV is expensive -- expect vol contraction & mean reversion"),
                "timeframe": "7-14d",
                "extra": {
                    "dvol": round(latest_dvol, 2),
                    "realized_vol_30d": round(rv_30d, 2),
                    "vrp": round(vrp, 2),
                    "rv_source": "binance_1h_klines",
                    "signal_basis": "Short vol premium (VRP>15)",
                },
                "timestamp": _now_iso(),
            })

        elif vrp < -5:
            # IV is cheap → expect breakout → LONG vol
            confidence = min(0.72, 0.52 + abs(vrp) * 0.015)
            tp_mult = 1.08  # 8% target
            sl_mult = 0.96  # 4% stop
            rr = (price * tp_mult - price) / (price - price * sl_mult)

            signals.append({
                "strategy": "vrp_signal",
                "symbol": "BTCUSDT",
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(price * tp_mult),
                "stop_loss": _smart_round(price * sl_mult),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "source_system": "novel_strategies",
                "reason": (f"Reverse VRP: DVOL={latest_dvol:.1f}% < RV={rv_30d:.1f}%, "
                           f"VRP={vrp:.1f}pts (<-5 threshold). "
                           f"IV is cheap -- expect volatility expansion & breakout"),
                "timeframe": "3-7d",
                "extra": {
                    "dvol": round(latest_dvol, 2),
                    "realized_vol_30d": round(rv_30d, 2),
                    "vrp": round(vrp, 2),
                    "rv_source": "binance_1h_klines",
                    "signal_basis": "Long vol -- IV cheap (VRP<-5)",
                },
                "timestamp": _now_iso(),
            })

    except Exception as e:
        # Non-fatal: log and continue
        print(f"  [novel/vrp_signal] Error: {e}")

    return signals


# =====================================================================
# STRATEGY 2: Stablecoin Flow Signal (On-Chain)
# =====================================================================
# Monitor USDT Treasury wallet (Tether) via Etherscan ERC-20 transfers.
# Treasury address: 0x5754284f345afc66a98fbB0a0Afe71e0F007B949
#
# Interpretation:
#   Large OUTFLOW from Treasury (mint) → new USDT entering circulation
#     → bullish (new capital entering crypto)
#   Large INFLOW to Treasury (burn) → USDT leaving circulation
#     → bearish (capital exiting crypto)
#
# Threshold: >$50M in last 24h
# Ref: Wei, Bianchi & Liao (2024 JFE)
# =====================================================================

USDT_TREASURY = "0x5754284f345afc66a98fbB0a0Afe71e0F007B949"
USDT_CONTRACT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"  # USDT ERC-20
USDT_DECIMALS = 6


def stablecoin_flow_onchain(data: dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> list[dict]:
    """Detect large USDT mint/burn events from Tether Treasury wallet."""
    signals = []

    try:
        api_key = _get_etherscan_key()
        if not api_key:
            print("  [novel/stablecoin_flow] No ETHERSCAN_KEY found, skipping")
            return signals

        # Check cache
        now = time.time()
        if _etherscan_cache["data"] is not None and (now - _etherscan_cache["ts"]) < _ETHERSCAN_CACHE_TTL:
            cached = _etherscan_cache["data"]
            net_flow = cached["net_flow"]
            mint_total = cached["mint_total"]
            burn_total = cached["burn_total"]
            tx_count = cached["tx_count"]
        else:
            # Fetch recent token transfers for Treasury wallet
            url = (
                f"https://api.etherscan.io/api"
                f"?module=account&action=tokentx"
                f"&address={USDT_TREASURY}"
                f"&contractaddress={USDT_CONTRACT}"
                f"&page=1&offset=100&sort=desc"
                f"&apikey={api_key}"
            )
            resp = _fetch_json(url, timeout=15)

            if not resp or resp.get("status") != "1" or not resp.get("result"):
                print(f"  [novel/stablecoin_flow] Etherscan API returned no data")
                return signals

            txs = resp["result"]

            # Filter to last 24 hours
            cutoff = int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp())
            recent_txs = [tx for tx in txs if int(tx.get("timeStamp", "0")) >= cutoff]

            if not recent_txs:
                # Widen to last 48 hours if no recent txs
                cutoff_48h = int((datetime.now(timezone.utc) - timedelta(hours=48)).timestamp())
                recent_txs = [tx for tx in txs if int(tx.get("timeStamp", "0")) >= cutoff_48h]

            if not recent_txs:
                return signals

            # Calculate net flow
            # FROM Treasury = MINT (outflow from treasury = new USDT minted)
            # TO Treasury = BURN (inflow to treasury = USDT being burned)
            mint_total = 0.0  # Outflow from treasury (minting)
            burn_total = 0.0  # Inflow to treasury (burning)

            for tx in recent_txs:
                value = float(tx.get("value", "0")) / (10 ** USDT_DECIMALS)
                from_addr = tx.get("from", "").lower()
                to_addr = tx.get("to", "").lower()

                if from_addr == USDT_TREASURY.lower():
                    mint_total += value  # Treasury sending out = minting
                elif to_addr == USDT_TREASURY.lower():
                    burn_total += value  # Treasury receiving = burning

            net_flow = mint_total - burn_total  # Positive = net mint, Negative = net burn
            tx_count = len(recent_txs)

            # Update cache
            _etherscan_cache["data"] = {
                "net_flow": net_flow,
                "mint_total": mint_total,
                "burn_total": burn_total,
                "tx_count": tx_count,
            }
            _etherscan_cache["ts"] = now

        # Get BTC price for signal generation
        btc_df = data.get("BTC-USD") or data.get("BTCUSDT")
        if btc_df is None or len(btc_df) < 5:
            return signals

        price = float(btc_df["Close"].iloc[-1])

        # --- Generate signals based on flow ---
        threshold = 50_000_000  # $50M

        if net_flow > threshold:
            # Large net MINT → bullish (new capital entering crypto)
            flow_m = net_flow / 1_000_000
            confidence = min(0.80, 0.55 + (net_flow / 500_000_000) * 0.15)
            tp_mult = 1.06  # 6% target
            sl_mult = 0.97  # 3% stop
            rr = (price * tp_mult - price) / (price - price * sl_mult)

            signals.append({
                "strategy": "stablecoin_flow_onchain",
                "symbol": "BTCUSDT",
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(price * tp_mult),
                "stop_loss": _smart_round(price * sl_mult),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "source_system": "novel_strategies",
                "reason": (f"USDT Treasury MINT: ${flow_m:.0f}M net minted in 24h "
                           f"(mint=${mint_total/1e6:.0f}M, burn=${burn_total/1e6:.0f}M, "
                           f"{tx_count} txs). New capital entering crypto -- bullish"),
                "timeframe": "2-5d",
                "extra": {
                    "net_flow_usd": round(net_flow, 2),
                    "mint_total_usd": round(mint_total, 2),
                    "burn_total_usd": round(burn_total, 2),
                    "tx_count": tx_count,
                    "treasury_wallet": USDT_TREASURY,
                    "signal_basis": "USDT Treasury net mint >$50M",
                },
                "timestamp": _now_iso(),
            })

            # Also signal ETH on large mints (>$100M)
            if net_flow > 100_000_000:
                eth_df = data.get("ETH-USD") or data.get("ETHUSDT")
                if eth_df is not None and len(eth_df) >= 5:
                    eth_price = float(eth_df["Close"].iloc[-1])
                    signals.append({
                        "strategy": "stablecoin_flow_onchain",
                        "symbol": "ETHUSDT",
                        "category": "crypto",
                        "signal_type": "BUY",
                        "entry_price": _smart_round(eth_price),
                        "take_profit": _smart_round(eth_price * 1.07),
                        "stop_loss": _smart_round(eth_price * 0.965),
                        "confidence": round(confidence * 0.95, 3),
                        "risk_reward": 2.0,
                        "source_system": "novel_strategies",
                        "reason": (f"USDT Treasury mega-MINT: ${flow_m:.0f}M net. "
                                   f"ETH benefits from stablecoin inflow -- bullish"),
                        "timeframe": "2-5d",
                        "extra": {
                            "net_flow_usd": round(net_flow, 2),
                            "signal_basis": "USDT Treasury net mint >$100M (ETH proxy)",
                        },
                        "timestamp": _now_iso(),
                    })

        elif net_flow < -threshold:
            # Large net BURN → bearish (capital leaving crypto)
            flow_m = abs(net_flow) / 1_000_000
            confidence = min(0.78, 0.53 + (abs(net_flow) / 500_000_000) * 0.15)
            tp_mult = 0.94  # 6% target (short)
            sl_mult = 1.03  # 3% stop
            rr = (price - price * tp_mult) / (price * sl_mult - price)

            signals.append({
                "strategy": "stablecoin_flow_onchain",
                "symbol": "BTCUSDT",
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(price * tp_mult),
                "stop_loss": _smart_round(price * sl_mult),
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "source_system": "novel_strategies",
                "reason": (f"USDT Treasury BURN: ${flow_m:.0f}M net burned in 24h "
                           f"(mint=${mint_total/1e6:.0f}M, burn=${burn_total/1e6:.0f}M, "
                           f"{tx_count} txs). Capital leaving crypto -- bearish"),
                "timeframe": "2-5d",
                "extra": {
                    "net_flow_usd": round(net_flow, 2),
                    "mint_total_usd": round(mint_total, 2),
                    "burn_total_usd": round(burn_total, 2),
                    "tx_count": tx_count,
                    "treasury_wallet": USDT_TREASURY,
                    "signal_basis": "USDT Treasury net burn >$50M",
                },
                "timestamp": _now_iso(),
            })

    except Exception as e:
        print(f"  [novel/stablecoin_flow] Error: {e}")

    return signals


# =====================================================================
# STRATEGY 3: Realized Correlation Breakout (BTC vs SPY)
# =====================================================================
# 30-day rolling correlation between BTC and SPY/S&P500.
#
# When corr < 0.3: BTC is decorrelated from stocks → moving independently
#   → Trend signal: follow BTC's own momentum (BUY if BTC trending up)
# When corr > 0.7: BTC follows stocks → use S&P sentiment as proxy
#   → If SPY bullish, BTC likely follows → BUY
#   → If SPY bearish, BTC likely follows → SELL
#
# Data: Binance BTC klines + yfinance SPY (both free)
# Ref: Bouri et al. (2020): crypto-equity correlation regime shifts
# =====================================================================

def correlation_breakout(data: dict[str, pd.DataFrame],
                         context: Optional[dict] = None) -> list[dict]:
    """BTC-SPY correlation regime detection for trend/proxy signals."""
    signals = []

    try:
        # --- Step 1: Get BTC daily closes ---
        btc_df = data.get("BTC-USD") or data.get("BTCUSDT")
        if btc_df is None or len(btc_df) < 35:
            return signals

        btc_close = btc_df["Close"].copy()
        btc_close.index = pd.to_datetime(btc_close.index)
        price = float(btc_close.iloc[-1])

        # --- Step 2: Get SPY data ---
        spy_df = data.get("SPY")
        spy_close = None

        if spy_df is not None and len(spy_df) >= 35:
            spy_close = spy_df["Close"].copy()
            spy_close.index = pd.to_datetime(spy_close.index)
        else:
            # Try yfinance as fallback
            try:
                import yfinance as yf
                spy_ticker = yf.Ticker("SPY")
                spy_hist = spy_ticker.history(period="60d")
                if spy_hist is not None and len(spy_hist) >= 35:
                    spy_close = spy_hist["Close"]
            except Exception:
                pass

        if spy_close is None or len(spy_close) < 35:
            # Last resort: try Alpha Vantage or skip
            print("  [novel/correlation_breakout] No SPY data available, skipping")
            return signals

        # --- Step 3: Align dates and compute correlation ---
        # Resample BTC to daily and align with SPY trading days
        btc_daily = btc_close.resample("D").last().dropna()
        spy_daily = spy_close.resample("D").last().dropna()

        # Find overlapping dates
        common_idx = btc_daily.index.intersection(spy_daily.index)
        if len(common_idx) < 30:
            # Try aligning with forward-fill for weekends
            combined = pd.DataFrame({
                "btc": btc_daily,
                "spy": spy_daily,
            }).dropna()

            if len(combined) < 20:
                # Use returns-based approach: compute returns, align by date range
                btc_ret = btc_daily.pct_change().dropna()
                spy_ret = spy_daily.pct_change().dropna()

                # Get last 30 overlapping return dates
                common_ret_idx = btc_ret.index.intersection(spy_ret.index)
                if len(common_ret_idx) < 15:
                    print("  [novel/correlation_breakout] Insufficient overlapping dates")
                    return signals

                btc_aligned = btc_ret.loc[common_ret_idx].tail(30)
                spy_aligned = spy_ret.loc[common_ret_idx].tail(30)
                corr_30d = float(btc_aligned.corr(spy_aligned))
            else:
                # Use returns of aligned data
                btc_ret = combined["btc"].pct_change().dropna().tail(30)
                spy_ret = combined["spy"].pct_change().dropna().tail(30)
                corr_30d = float(btc_ret.corr(spy_ret))
        else:
            btc_aligned = btc_daily.loc[common_idx].tail(30)
            spy_aligned = spy_daily.loc[common_idx].tail(30)
            btc_ret = btc_aligned.pct_change().dropna()
            spy_ret = spy_aligned.pct_change().dropna()
            corr_30d = float(btc_ret.corr(spy_ret))

        # Sanitize
        if math.isnan(corr_30d) or math.isinf(corr_30d):
            return signals

        # --- Step 4: Compute BTC momentum (7d and 14d returns) ---
        btc_7d_ret = float((btc_close.iloc[-1] / btc_close.iloc[-8]) - 1) if len(btc_close) >= 8 else 0
        btc_14d_ret = float((btc_close.iloc[-1] / btc_close.iloc[-15]) - 1) if len(btc_close) >= 15 else 0

        # SPY momentum
        spy_7d_ret = 0.0
        if spy_close is not None and len(spy_close) >= 8:
            spy_7d_ret = float((spy_close.iloc[-1] / spy_close.iloc[-8]) - 1)

        # --- Step 5: Generate signals ---
        if corr_30d < 0.3:
            # DECORRELATION: BTC moving independently
            # Follow BTC's own momentum
            if btc_7d_ret > 0.02 and btc_14d_ret > 0:
                # BTC trending up independently → BUY
                confidence = min(0.78, 0.55 + (0.3 - corr_30d) * 0.4 + btc_7d_ret * 2)
                tp_mult = 1.07
                sl_mult = 0.965
                rr = (price * tp_mult - price) / (price - price * sl_mult)

                signals.append({
                    "strategy": "correlation_breakout",
                    "symbol": "BTCUSDT",
                    "category": "crypto",
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(price * tp_mult),
                    "stop_loss": _smart_round(price * sl_mult),
                    "confidence": round(confidence, 3),
                    "risk_reward": round(rr, 2),
                    "source_system": "novel_strategies",
                    "reason": (f"BTC-SPY decorrelation: corr={corr_30d:.2f} (<0.3). "
                               f"BTC trending independently: 7d={btc_7d_ret*100:+.1f}%, "
                               f"14d={btc_14d_ret*100:+.1f}%. "
                               f"Crypto-native bull run likely"),
                    "timeframe": "5-10d",
                    "extra": {
                        "btc_spy_corr_30d": round(corr_30d, 4),
                        "btc_7d_return": round(btc_7d_ret * 100, 2),
                        "btc_14d_return": round(btc_14d_ret * 100, 2),
                        "spy_7d_return": round(spy_7d_ret * 100, 2),
                        "regime": "decorrelated_bullish",
                        "signal_basis": "BTC decorrelated from SPY + bullish momentum",
                    },
                    "timestamp": _now_iso(),
                })

            elif btc_7d_ret < -0.02 and btc_14d_ret < 0:
                # BTC trending down independently → SELL
                confidence = min(0.75, 0.53 + (0.3 - corr_30d) * 0.35 + abs(btc_7d_ret) * 2)
                tp_mult = 0.93
                sl_mult = 1.035
                rr = (price - price * tp_mult) / (price * sl_mult - price)

                signals.append({
                    "strategy": "correlation_breakout",
                    "symbol": "BTCUSDT",
                    "category": "crypto",
                    "signal_type": "SELL",
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(price * tp_mult),
                    "stop_loss": _smart_round(price * sl_mult),
                    "confidence": round(confidence, 3),
                    "risk_reward": round(rr, 2),
                    "source_system": "novel_strategies",
                    "reason": (f"BTC-SPY decorrelation: corr={corr_30d:.2f} (<0.3). "
                               f"BTC trending down independently: 7d={btc_7d_ret*100:+.1f}%, "
                               f"14d={btc_14d_ret*100:+.1f}%. "
                               f"Crypto-native sell-off, ignore stock signals"),
                    "timeframe": "5-10d",
                    "extra": {
                        "btc_spy_corr_30d": round(corr_30d, 4),
                        "btc_7d_return": round(btc_7d_ret * 100, 2),
                        "btc_14d_return": round(btc_14d_ret * 100, 2),
                        "spy_7d_return": round(spy_7d_ret * 100, 2),
                        "regime": "decorrelated_bearish",
                        "signal_basis": "BTC decorrelated from SPY + bearish momentum",
                    },
                    "timestamp": _now_iso(),
                })

        elif corr_30d > 0.7:
            # HIGH CORRELATION: BTC follows stocks
            # Use SPY momentum as leading indicator
            if spy_7d_ret > 0.015 and btc_7d_ret > -0.01:
                # SPY bullish + BTC not falling → expect BTC follow-through
                confidence = min(0.73, 0.52 + (corr_30d - 0.7) * 0.5 + spy_7d_ret * 3)
                tp_mult = 1.055
                sl_mult = 0.97
                rr = (price * tp_mult - price) / (price - price * sl_mult)

                signals.append({
                    "strategy": "correlation_breakout",
                    "symbol": "BTCUSDT",
                    "category": "crypto",
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(price * tp_mult),
                    "stop_loss": _smart_round(price * sl_mult),
                    "confidence": round(confidence, 3),
                    "risk_reward": round(rr, 2),
                    "source_system": "novel_strategies",
                    "reason": (f"BTC-SPY high correlation: corr={corr_30d:.2f} (>0.7). "
                               f"SPY bullish 7d={spy_7d_ret*100:+.1f}% → BTC should follow. "
                               f"Using stock sentiment as leading indicator"),
                    "timeframe": "3-7d",
                    "extra": {
                        "btc_spy_corr_30d": round(corr_30d, 4),
                        "btc_7d_return": round(btc_7d_ret * 100, 2),
                        "spy_7d_return": round(spy_7d_ret * 100, 2),
                        "regime": "correlated_bullish",
                        "signal_basis": "High BTC-SPY corr + SPY bullish momentum",
                    },
                    "timestamp": _now_iso(),
                })

            elif spy_7d_ret < -0.015 and btc_7d_ret < 0.01:
                # SPY bearish + BTC not rising → expect BTC follow-through down
                confidence = min(0.70, 0.50 + (corr_30d - 0.7) * 0.4 + abs(spy_7d_ret) * 3)
                tp_mult = 0.945
                sl_mult = 1.03
                rr = (price - price * tp_mult) / (price * sl_mult - price)

                signals.append({
                    "strategy": "correlation_breakout",
                    "symbol": "BTCUSDT",
                    "category": "crypto",
                    "signal_type": "SELL",
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(price * tp_mult),
                    "stop_loss": _smart_round(price * sl_mult),
                    "confidence": round(confidence, 3),
                    "risk_reward": round(rr, 2),
                    "source_system": "novel_strategies",
                    "reason": (f"BTC-SPY high correlation: corr={corr_30d:.2f} (>0.7). "
                               f"SPY bearish 7d={spy_7d_ret*100:+.1f}% → BTC should follow. "
                               f"Risk-off across correlated assets"),
                    "timeframe": "3-7d",
                    "extra": {
                        "btc_spy_corr_30d": round(corr_30d, 4),
                        "btc_7d_return": round(btc_7d_ret * 100, 2),
                        "spy_7d_return": round(spy_7d_ret * 100, 2),
                        "regime": "correlated_bearish",
                        "signal_basis": "High BTC-SPY corr + SPY bearish momentum",
                    },
                    "timestamp": _now_iso(),
                })

    except Exception as e:
        print(f"  [novel/correlation_breakout] Error: {e}")

    return signals


# =====================================================================
# Standalone runner: test all 3 strategies directly
# =====================================================================

def run() -> list[dict]:
    """Run all 3 novel strategies and return combined signals."""
    all_signals = []

    # Build minimal data dict for testing
    print("[novel_strategies] Running 3 quick-win strategies...")

    # Fetch BTC data from Binance klines (daily, 60 days)
    data: dict[str, pd.DataFrame] = {}

    try:
        klines = fetch_binance_json("/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=60")
        if klines:
            df = pd.DataFrame(klines, columns=[
                "open_time", "Open", "High", "Low", "Close", "Volume",
                "close_time", "quote_vol", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore"
            ])
            for col in ("Open", "High", "Low", "Close", "Volume"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df.index = pd.to_datetime(df["open_time"], unit="ms")
            data["BTC-USD"] = df
            data["BTCUSDT"] = df
            print(f"  BTC data: {len(df)} daily candles")
    except Exception as e:
        print(f"  Failed to fetch BTC data: {e}")

    # Fetch ETH data
    try:
        klines = fetch_binance_json("/api/v3/klines?symbol=ETHUSDT&interval=1d&limit=60")
        if klines:
            df = pd.DataFrame(klines, columns=[
                "open_time", "Open", "High", "Low", "Close", "Volume",
                "close_time", "quote_vol", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore"
            ])
            for col in ("Open", "High", "Low", "Close", "Volume"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df.index = pd.to_datetime(df["open_time"], unit="ms")
            data["ETH-USD"] = df
            data["ETHUSDT"] = df
            print(f"  ETH data: {len(df)} daily candles")
    except Exception as e:
        print(f"  Failed to fetch ETH data: {e}")

    # Fetch SPY data via yfinance
    try:
        import yfinance as yf
        spy = yf.Ticker("SPY")
        spy_hist = spy.history(period="90d")
        if spy_hist is not None and len(spy_hist) >= 30:
            data["SPY"] = spy_hist
            print(f"  SPY data: {len(spy_hist)} daily candles")
        else:
            print("  SPY data: insufficient history")
    except Exception as e:
        print(f"  Failed to fetch SPY data: {e}")

    # Run each strategy
    for name, func in [
        ("vrp_signal", vrp_signal),
        ("stablecoin_flow_onchain", stablecoin_flow_onchain),
        ("correlation_breakout", correlation_breakout),
    ]:
        try:
            sigs = func(data)
            all_signals.extend(sigs)
            if sigs:
                for s in sigs:
                    print(f"  [{name}] {s['signal_type']} {s['symbol']} @ {s['entry_price']} "
                          f"(conf={s['confidence']:.2f}) -- {s['reason'][:80]}...")
            else:
                print(f"  [{name}] No signal (thresholds not met)")
        except Exception as e:
            print(f"  [{name}] FAILED: {e}")

    print(f"[novel_strategies] Total signals: {len(all_signals)}")
    return all_signals


# =====================================================================
# Strategy dict for scanner.py import
# =====================================================================

NOVEL_STRATEGIES: dict[str, callable] = {
    "vrp_signal": vrp_signal,
    "stablecoin_flow_onchain": stablecoin_flow_onchain,
    "correlation_breakout": correlation_breakout,
}


# =====================================================================
# Main entry point for standalone testing
# =====================================================================

if __name__ == "__main__":
    signals = run()

    # Save results
    if signals:
        output_path = DATA_DIR / "novel_strategy_signals.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(signals, f, indent=2, default=str)
        print(f"\nSaved {len(signals)} signals to {output_path}")
    else:
        print("\nNo signals generated (all thresholds inactive)")
