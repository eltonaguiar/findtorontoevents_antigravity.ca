#!/usr/bin/env python3
"""
RAPID FIRE — Real-Time 1h Crypto Scanner (NOW.py)
===================================================
Runs 8 proven strategies on top 50 USDT pairs targeting crypto that
skyrockets within 1 hour. Every pick is logged to MySQL with dual R:R
tracking (1.5:1 and 2:1). Generates an HTML report.

Usage:
    python NOW.py              # Scan + resolve + generate report
    python NOW.py --resolve    # Only resolve pending picks (no new scan)
    python NOW.py --stats      # Print strategy stats from DB
    python NOW.py --pairs 20   # Scan only top 20 pairs (faster)

Author: Rapid Fire Scanner
"""

import json
import logging
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# Windows UTF-8 fix
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger('RapidFire')

# ── Configuration ────────────────────────────────────────────────────────────

TOP_N_PAIRS = 50
HOLDING_PERIOD_HOURS = 1
SOURCE_SYSTEM = 'RAPID_FIRE'
REPORT_PATH = Path(__file__).parent / 'findcryptopairs' / 'now.html'
DATA_DIR = Path(__file__).parent / 'rapid_fire_data'
DATA_DIR.mkdir(exist_ok=True)

# Binance mirrors (try in order, fallback to CoinGecko)
BINANCE_ENDPOINTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

DB_HOST = os.getenv("AUDIT_DB_HOST", "mysql.50webs.com")
DB_PORT = int(os.getenv("AUDIT_DB_PORT", "3306"))
DB_USER = os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks")
DB_PASS = os.getenv("AUDIT_DB_PASS", "stocks")
DB_NAME = os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks")


# ── Data Fetching ────────────────────────────────────────────────────────────

_binance_blocked = False

def fetch_json(url: str, timeout: int = 15) -> Optional[dict]:
    """Fetch JSON from URL with error handling."""
    req = Request(url, headers={"User-Agent": "RapidFire/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code in (451, 403):
            return None
        log.warning(f"HTTP {e.code}: {url}")
        return None
    except (URLError, Exception) as e:
        log.warning(f"Fetch failed: {url} - {e}")
        return None


def fetch_binance(path: str) -> Optional[dict]:
    """Try Binance endpoints, return first success."""
    global _binance_blocked
    if _binance_blocked:
        return None
    for base in BINANCE_ENDPOINTS:
        data = fetch_json(f"{base}{path}")
        if data is not None:
            return data
    _binance_blocked = True
    log.warning("All Binance endpoints blocked — using CoinGecko fallback")
    return None


STABLECOIN_BASES = {
    'USDC', 'BUSD', 'DAI', 'TUSD', 'FDUSD', 'USDP', 'GUSD', 'FRAX', 'LUSD',
    'USDD', 'PYUSD', 'USD1', 'XUSD', 'EUSD', 'CUSD', 'SUSD', 'HUSD', 'UST',
    'PAXG',  # gold-pegged, not crypto — shouldn't be scanned for 1h momentum
}

def _is_stablecoin(symbol: str) -> bool:
    """Return True if symbol is a stablecoin or pegged asset."""
    base = symbol.replace('USDT', '')
    return base in STABLECOIN_BASES


def _is_ascii_symbol(symbol: str) -> bool:
    """Return True if symbol contains only ASCII characters.
    Binance sometimes returns symbols with CJK characters (e.g., 币安人生USDT)
    which crash urllib when used in URLs (UnicodeEncodeError: 'ascii' codec)."""
    try:
        symbol.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False


def get_top_pairs() -> List[str]:
    """Get top N USDT pairs by volume, excluding stablecoins and non-ASCII symbols."""
    data = fetch_binance("/api/v3/ticker/24hr")
    if data:
        usdt = [t for t in data if t['symbol'].endswith('USDT')
                and not any(x in t['symbol'] for x in ['DOWN', 'UP', 'BULL', 'BEAR'])
                and not _is_stablecoin(t['symbol'])
                and _is_ascii_symbol(t['symbol'])]
        usdt.sort(key=lambda t: float(t.get('quoteVolume', 0)), reverse=True)
        return [t['symbol'] for t in usdt[:TOP_N_PAIRS]]

    # CoinGecko fallback
    cg = fetch_json("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=50&page=1")
    if cg:
        return [c['symbol'].upper() + 'USDT' for c in cg if c.get('symbol')]

    # CoinCap fallback (no API key needed)
    cc = fetch_json("https://api.coincap.io/v2/assets?limit=50")
    if cc and cc.get('data'):
        return [a['symbol'].upper() + 'USDT' for a in cc['data'] if a.get('symbol')]

    # Last resort: hardcoded top 20
    log.warning("All pair-list APIs failed — using hardcoded top 20")
    return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT',
            'AVAXUSDT', 'DOGEUSDT', 'LINKUSDT', 'DOTUSDT', 'MATICUSDT', 'NEARUSDT',
            'APTUSDT', 'ARBUSDT', 'OPUSDT', 'SUIUSDT', 'FETUSDT', 'INJUSDT',
            'TIAUSDT', 'SEIUSDT']


def get_klines(symbol: str, interval: str = '5m', limit: int = 100) -> List[dict]:
    """Fetch kline/candlestick data for a symbol."""
    data = fetch_binance(f"/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}")
    if data:
        return [{'time': k[0], 'open': float(k[1]), 'high': float(k[2]),
                 'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])} for k in data]

    # CoinGecko fallback — OHLC endpoint
    cg_id = _symbol_to_coingecko_id(symbol)
    if cg_id:
        days = 2 if interval in ('5m', '15m') else 7
        cg = fetch_json(f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days={days}")
        if cg:
            return [{'time': k[0], 'open': k[1], 'high': k[2], 'low': k[3],
                     'close': k[4], 'volume': 1.0} for k in cg]

    # CoinCap fallback — candles endpoint (supports m5, h1, h2, d1)
    if cg_id or symbol:
        base = symbol.replace('USDT', '').replace('USD', '').lower()
        cc_interval = 'm5' if interval == '5m' else 'h1' if interval in ('1h', '60m') else 'm15'
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - (limit * 300000 if interval == '5m' else limit * 3600000)
        cc = fetch_json(f"https://api.coincap.io/v2/candles?exchange=binance&interval={cc_interval}"
                        f"&baseId={base}&quoteId=tether&start={start_ms}&end={end_ms}")
        if cc and cc.get('data'):
            return [{'time': int(k['period']), 'open': float(k['open']), 'high': float(k['high']),
                     'low': float(k['low']), 'close': float(k['close']),
                     'volume': float(k.get('volume', 1))} for k in cc['data']]
    return []


_cg_map = {}
def _symbol_to_coingecko_id(symbol: str) -> Optional[str]:
    """Map BTCUSDT -> bitcoin etc."""
    global _cg_map
    if not _cg_map:
        _cg_map = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'BNB': 'binancecoin',
            'XRP': 'ripple', 'ADA': 'cardano', 'AVAX': 'avalanche-2', 'DOGE': 'dogecoin',
            'LINK': 'chainlink', 'DOT': 'polkadot', 'MATIC': 'matic-network',
            'NEAR': 'near', 'APT': 'aptos', 'ARB': 'arbitrum', 'OP': 'optimism',
            'SUI': 'sui', 'FET': 'artificial-superintelligence-alliance', 'INJ': 'injective-protocol',
            'TIA': 'celestia', 'SEI': 'sei-network', 'ATOM': 'cosmos', 'FIL': 'filecoin',
            'IMX': 'immutable-x', 'RENDER': 'render-token', 'STX': 'blockstack',
            'PEPE': 'pepe', 'WIF': 'dogwifcoin', 'FLOKI': 'floki',
            'SHIB': 'shiba-inu', 'LTC': 'litecoin', 'BCH': 'bitcoin-cash',
            'UNI': 'uniswap', 'AAVE': 'aave', 'MKR': 'maker', 'CRV': 'curve-dao-token',
            'LDO': 'lido-dao', 'RUNE': 'thorchain', 'GRT': 'the-graph',
            'ALGO': 'algorand', 'FTM': 'fantom', 'SAND': 'the-sandbox',
            'MANA': 'decentraland', 'AXS': 'axie-infinity', 'GALA': 'gala',
            'ENS': 'ethereum-name-service', 'DYDX': 'dydx', 'SNX': 'havven',
            'COMP': 'compound-governance-token', 'SUSHI': 'sushi',
            'ONE': 'harmony', 'HBAR': 'hedera-hashgraph', 'EOS': 'eos',
            'XLM': 'stellar', 'VET': 'vechain', 'THETA': 'theta-token',
        }
    base = symbol.replace('USDT', '').replace('USD', '')
    return _cg_map.get(base)


_funding_api_failed = False

def get_funding_rate(symbol: str) -> Optional[float]:
    """Get current funding rate for a perpetual (Binance Futures API)."""
    global _funding_api_failed
    if _funding_api_failed:
        return None
    # Futures API is on fapi.binance.com (separate from spot mirrors)
    data = fetch_json(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1")
    if data and isinstance(data, list) and len(data) > 0:
        return float(data[0].get('fundingRate', 0))
    # If fapi is blocked, don't keep retrying
    _funding_api_failed = True
    return None


# ── Technical Indicators ─────────────────────────────────────────────────────

def ema(closes: List[float], period: int) -> List[float]:
    """Exponential Moving Average."""
    if len(closes) < period:
        return [0.0] * len(closes)
    mult = 2 / (period + 1)
    result = [0.0] * (period - 1)
    result.append(sum(closes[:period]) / period)
    for i in range(period, len(closes)):
        result.append(closes[i] * mult + result[-1] * (1 - mult))
    return result


def sma(values: List[float], period: int) -> List[float]:
    """Simple Moving Average."""
    result = [0.0] * (period - 1)
    for i in range(period - 1, len(values)):
        result.append(sum(values[i - period + 1:i + 1]) / period)
    return result


def rsi(closes: List[float], period: int = 14) -> List[float]:
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result = [50.0] * period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - 100 / (1 + rs))
    return result


def macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
    """MACD line, signal line, histogram."""
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s if f and s else 0 for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)
    histogram = [m - s if m and s else 0 for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, histogram


def bollinger_bands(closes: List[float], period: int = 20, std_mult: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    """Upper, middle, lower Bollinger Bands."""
    mid = sma(closes, period)
    upper, lower = [], []
    for i in range(len(closes)):
        if i < period - 1:
            upper.append(0)
            lower.append(0)
        else:
            window = closes[i - period + 1:i + 1]
            mean = mid[i]
            std = (sum((x - mean) ** 2 for x in window) / period) ** 0.5
            upper.append(mean + std_mult * std)
            lower.append(mean - std_mult * std)
    return upper, mid, lower


def stoch_rsi(closes: List[float], rsi_period: int = 14, stoch_period: int = 14,
              k_smooth: int = 3, d_smooth: int = 3) -> Tuple[List[float], List[float]]:
    """Stochastic RSI — %K and %D lines."""
    rsi_vals = rsi(closes, rsi_period)
    k_raw = []
    for i in range(len(rsi_vals)):
        if i < stoch_period - 1:
            k_raw.append(50.0)
        else:
            window = rsi_vals[i - stoch_period + 1:i + 1]
            lo, hi = min(window), max(window)
            k_raw.append((rsi_vals[i] - lo) / (hi - lo) * 100 if hi != lo else 50.0)
    k_line = sma(k_raw, k_smooth)
    d_line = sma(k_line, d_smooth)
    return k_line, d_line


# ── Strategies ───────────────────────────────────────────────────────────────

class Signal:
    """A trading signal from a strategy."""
    def __init__(self, symbol: str, direction: str, strategy: str, confidence: float,
                 entry_price: float, reason: str, sl_pct: float = 2.0):
        self.symbol = symbol
        self.direction = direction  # LONG or SHORT
        self.strategy = strategy
        self.confidence = min(confidence, 95)  # cap at 95%
        self.entry_price = entry_price
        self.reason = reason
        self.sl_pct = sl_pct
        # Calculate TP/SL prices
        if direction == 'LONG':
            self.sl_price = entry_price * (1 - sl_pct / 100)
            self.tp_price_1_5 = entry_price * (1 + sl_pct * 1.5 / 100)
            self.tp_price_2_0 = entry_price * (1 + sl_pct * 2.0 / 100)
        else:
            self.sl_price = entry_price * (1 + sl_pct / 100)
            self.tp_price_1_5 = entry_price * (1 - sl_pct * 1.5 / 100)
            self.tp_price_2_0 = entry_price * (1 - sl_pct * 2.0 / 100)

    def to_dict(self) -> dict:
        # confidence is held internally on a 0-95 percent scale; the canonical
        # pick schema (and the edge-stability harness) expect 0-1. Emit /100 so
        # downstream ledgers do not store a percent-as-integer (issue #1241).
        _conf = self.confidence
        if _conf is not None and _conf > 1.0:
            _conf = round(_conf / 100.0, 4)
        return {
            'symbol': self.symbol, 'direction': self.direction,
            'strategy': self.strategy, 'confidence': _conf,
            'entry_price': self.entry_price, 'reason': self.reason,
            'sl_price': self.sl_price, 'tp_price_1_5': self.tp_price_1_5,
            'tp_price_2_0': self.tp_price_2_0, 'sl_pct': self.sl_pct,
        }


def strategy_macd_crossover(symbol: str, klines: List[dict]) -> Optional[Signal]:
    """Strategy 1: MACD Crossover on 5m — bullish cross with rising histogram.
    Tightened: requires volume confirmation + histogram growing for 2+ bars."""
    if len(klines) < 35:
        return None
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    macd_line, sig_line, hist = macd(closes)

    if len(hist) < 4:
        return None

    # Volume confirmation: current bar > 1.2x 20-bar average
    avg_vol = sum(volumes[-21:-1]) / 20 if len(volumes) >= 21 else sum(volumes[:-1]) / max(len(volumes) - 1, 1)
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0
    if vol_ratio < 1.2:
        return None  # No volume = unreliable signal

    # Bullish cross: MACD crossed above signal in last 2 bars (tighter window)
    cross_recent = any(macd_line[-i] > sig_line[-i] and macd_line[-i-1] <= sig_line[-i-1]
                       for i in range(1, 3) if len(macd_line) > i)
    if cross_recent and macd_line[-1] > sig_line[-1]:
        # Histogram must be positive AND growing for at least 2 bars
        if hist[-1] > 0 and hist[-1] > hist[-2] and hist[-2] > hist[-3]:
            confidence = 55 + min(abs(hist[-1]) * 1000, 15) + min(vol_ratio * 2, 8)
            return Signal(symbol, 'LONG', 'macd_crossover', confidence,
                         closes[-1], f"MACD bullish cross. Histogram: {hist[-1]:.6f} (growing 2+ bars). "
                         f"Vol {vol_ratio:.1f}x avg. MACD: {macd_line[-1]:.6f} > Signal: {sig_line[-1]:.6f}")
    # Bearish cross for SHORT — same tighter conditions
    bear_cross = any(macd_line[-i] < sig_line[-i] and macd_line[-i-1] >= sig_line[-i-1]
                     for i in range(1, 3) if len(macd_line) > i)
    if bear_cross and macd_line[-1] < sig_line[-1] and hist[-1] < 0 and hist[-1] < hist[-2] and hist[-2] < hist[-3]:
        confidence = 55 + min(abs(hist[-1]) * 1000, 15) + min(vol_ratio * 2, 8)
        return Signal(symbol, 'SHORT', 'macd_crossover', confidence,
                     closes[-1], f"MACD bearish cross. Histogram: {hist[-1]:.6f} (falling 2+ bars). "
                     f"Vol {vol_ratio:.1f}x avg. MACD: {macd_line[-1]:.6f} < Signal: {sig_line[-1]:.6f}")
    return None


def strategy_rsi_bounce(symbol: str, klines: List[dict]) -> Optional[Signal]:
    """Strategy 2: RSI Oversold Bounce — RSI drops below 30 then recovers."""
    if len(klines) < 20:
        return None
    closes = [k['close'] for k in klines]
    rsi_vals = rsi(closes, 14)

    # RSI was < 30 in last 3 bars, now crossing back above 30
    if rsi_vals[-1] > 30 and any(r < 30 for r in rsi_vals[-4:-1]):
        # Volume confirmation: current volume > average
        volumes = [k['volume'] for k in klines[-20:]]
        avg_vol = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 1
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1

        if vol_ratio > 0.8:  # At least near-average volume
            confidence = 58 + min(vol_ratio * 5, 15) + min((30 - min(rsi_vals[-4:-1])) * 0.5, 10)
            return Signal(symbol, 'LONG', 'rsi_bounce', confidence,
                         closes[-1], f"RSI bounced from {min(rsi_vals[-4:-1]):.1f} to {rsi_vals[-1]:.1f}. "
                         f"Volume {vol_ratio:.1f}x average.", sl_pct=2.5)

    # RSI Overbought Reversal (SHORT)
    if rsi_vals[-1] < 70 and any(r > 70 for r in rsi_vals[-4:-1]):
        volumes = [k['volume'] for k in klines[-20:]]
        avg_vol = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 1
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
        if vol_ratio > 0.8:
            confidence = 56 + min(vol_ratio * 5, 15) + min((max(rsi_vals[-4:-1]) - 70) * 0.5, 10)
            return Signal(symbol, 'SHORT', 'rsi_overbought', confidence,
                         closes[-1], f"RSI dropped from {max(rsi_vals[-4:-1]):.1f} to {rsi_vals[-1]:.1f}. "
                         f"Volume {vol_ratio:.1f}x average.", sl_pct=2.5)
    return None


def strategy_macd_rsi_confluence(symbol: str, klines: List[dict]) -> Optional[Signal]:
    """Strategy 3: MACD + RSI Confluence — proven 65% WR. Strongest signal."""
    if len(klines) < 35:
        return None
    closes = [k['close'] for k in klines]
    rsi_vals = rsi(closes, 14)
    macd_line, sig_line, hist = macd(closes)

    # MACD bullish cross OR histogram turning positive
    macd_bullish = (macd_line[-1] > sig_line[-1] and macd_line[-2] <= sig_line[-2]) or \
                   (hist[-1] > 0 and hist[-2] <= 0)

    # RSI recovering from below 40
    rsi_recovering = rsi_vals[-1] > 35 and any(r < 40 for r in rsi_vals[-5:-1])

    if macd_bullish and rsi_recovering:
        confidence = 65 + min(abs(hist[-1]) * 500, 15)
        return Signal(symbol, 'LONG', 'macd_rsi_confluence', confidence,
                     closes[-1], f"MACD+RSI confluence. RSI: {rsi_vals[-1]:.1f} recovering. "
                     f"MACD histogram: {hist[-1]:.6f} turned positive.", sl_pct=2.0)
    return None


def strategy_volume_spike_breakout(symbol: str, klines: List[dict]) -> Optional[Signal]:
    """Strategy 4: Volume Spike Breakout — volume > 3x avg + price breaking high."""
    if len(klines) < 25:
        return None
    closes = [k['close'] for k in klines]
    highs = [k['high'] for k in klines]
    volumes = [k['volume'] for k in klines]

    avg_vol = sum(volumes[-21:-1]) / 20 if len(volumes) >= 21 else sum(volumes[:-1]) / max(len(volumes) - 1, 1)
    cur_vol = volumes[-1]
    vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 0

    # Volume > 2x and price breaking above recent 20-bar high
    recent_high = max(highs[-21:-1]) if len(highs) >= 21 else max(highs[:-1])
    if vol_ratio >= 2.0 and closes[-1] > recent_high * 0.998:  # Within 0.2% of breakout
        confidence = 60 + min(vol_ratio * 3, 20)
        return Signal(symbol, 'LONG', 'volume_spike_breakout', confidence,
                     closes[-1], f"Volume spike {vol_ratio:.1f}x average. "
                     f"Price ${closes[-1]:.4f} broke above ${recent_high:.4f} (20-bar high).",
                     sl_pct=2.5)
    return None


def strategy_bollinger_squeeze(symbol: str, klines: List[dict]) -> Optional[Signal]:
    """Strategy 5: Bollinger Squeeze Expansion — BB width at low, price breaks upper."""
    if len(klines) < 25:
        return None
    closes = [k['close'] for k in klines]
    upper, mid, lower = bollinger_bands(closes, 20, 2.0)

    if upper[-1] == 0 or mid[-1] == 0:
        return None

    # BB width (as % of mid)
    widths = [(u - l) / m * 100 if m > 0 else 0 for u, m, l in zip(upper[-20:], mid[-20:], lower[-20:])]
    if not widths or widths[-1] == 0:
        return None

    # Current width in bottom 25% of recent range = squeeze
    sorted_w = sorted(widths)
    is_squeeze = widths[-1] <= sorted_w[len(sorted_w) // 4] if sorted_w else False

    # Price breaking above upper band after squeeze (or within 0.3%)
    near_upper = closes[-1] > upper[-1] * 0.997
    if is_squeeze and near_upper:
        above = closes[-1] > upper[-1]
        confidence = 62 + min(abs(closes[-1] - upper[-1]) / upper[-1] * 1000, 15)
        if not above:
            confidence -= 3  # Slight penalty for not fully breaking out
        return Signal(symbol, 'LONG', 'bollinger_squeeze', confidence,
                     closes[-1], f"Bollinger squeeze {'breakout' if above else 'near-breakout'}. "
                     f"Width at {widths[-1]:.2f}% (bottom quartile). "
                     f"Price {'broke above' if above else 'approaching'} upper band ${upper[-1]:.4f}.",
                     sl_pct=2.0)
    return None


def strategy_ema_stack(symbol: str, klines: List[dict]) -> Optional[Signal]:
    """Strategy 6: EMA Stack Alignment — 9>21>50 with pullback to 9 EMA.
    Tightened: require minimum 0.5% separation between EMAs + volume."""
    if len(klines) < 55:
        return None
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)

    if not all([ema9[-1], ema21[-1], ema50[-1]]):
        return None

    # Bullish stack: 9 > 21 > 50
    if ema9[-1] > ema21[-1] > ema50[-1]:
        # Stack separation must be meaningful (>0.5% between 9 and 50)
        sep = (ema9[-1] - ema50[-1]) / ema50[-1] * 100 if ema50[-1] else 0
        if sep < 0.5:
            return None  # EMAs too close = choppy/ranging market, not trending

        # Volume check
        avg_vol = sum(volumes[-21:-1]) / 20 if len(volumes) >= 21 else sum(volumes[:-1]) / max(len(volumes) - 1, 1)
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0
        if vol_ratio < 0.8:
            return None

        # Pullback: price bouncing off 9 EMA (tighter — must actually bounce, not just be near)
        bouncing = closes[-1] > ema9[-1] and closes[-2] <= ema9[-2] * 1.001
        between_emas = ema21[-1] <= closes[-1] <= ema9[-1] * 1.001

        if bouncing or between_emas:
            confidence = 60 + min(sep * 4, 12) + min(vol_ratio * 2, 6)
            return Signal(symbol, 'LONG', 'ema_stack', confidence,
                         closes[-1], f"EMA stack (9>{ema9[-1]:.2f} > 21>{ema21[-1]:.2f} > "
                         f"50>{ema50[-1]:.2f}, sep={sep:.1f}%). Vol {vol_ratio:.1f}x.", sl_pct=1.8)
    return None


def strategy_funding_reversal(symbol: str, klines: List[dict]) -> Optional[Signal]:
    """Strategy 7: Funding Rate Reversal — negative funding + reversal candle."""
    if len(klines) < 10:
        return None
    funding = get_funding_rate(symbol)
    if funding is None or funding >= 0:
        return None

    closes = [k['close'] for k in klines]
    opens = [k['open'] for k in klines]
    highs = [k['high'] for k in klines]
    lows = [k['low'] for k in klines]

    # Reversal candle: bullish engulfing or hammer
    body = closes[-1] - opens[-1]
    candle_range = highs[-1] - lows[-1]
    prev_body = closes[-2] - opens[-2]

    is_bullish_engulf = body > 0 and prev_body < 0 and body > abs(prev_body)
    is_hammer = body > 0 and (opens[-1] - lows[-1]) > 2 * body and candle_range > 0

    if is_bullish_engulf or is_hammer:
        confidence = 65 + min(abs(funding) * 5000, 15)
        pattern = "bullish engulfing" if is_bullish_engulf else "hammer"
        return Signal(symbol, 'LONG', 'funding_reversal', confidence,
                     closes[-1], f"Negative funding rate ({funding:.4%}) + {pattern} candle. "
                     f"Shorts paying longs — squeeze potential.", sl_pct=2.0)
    return None


def strategy_stochrsi_macd_combo(symbol: str, klines: List[dict]) -> Optional[Signal]:
    """Strategy 8: StochRSI + MACD Combo — oversold StochRSI + MACD confirmation.
    Tightened: MACD histogram must actually be positive (not just improving),
    K must have been truly oversold (<20), and volume must confirm."""
    if len(klines) < 35:
        return None
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    k_line, d_line = stoch_rsi(closes)
    _, _, hist = macd(closes)

    if len(k_line) < 3 or len(hist) < 2:
        return None

    # Volume check
    avg_vol = sum(volumes[-21:-1]) / 20 if len(volumes) >= 21 else sum(volumes[:-1]) / max(len(volumes) - 1, 1)
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0
    if vol_ratio < 0.9:
        return None

    # K crossed above D in last 2 bars (tighter) and still above
    k_cross = k_line[-1] > d_line[-1] and any(
        k_line[-i-1] <= d_line[-i-1] for i in range(1, 3) if len(k_line) > i)
    # Must have been deeply oversold (<20, not just <25)
    was_oversold = any(k < 20 for k in k_line[-5:-1])
    # MACD histogram must be ACTUALLY positive — not just "improving while negative"
    macd_positive = hist[-1] > 0

    if k_cross and was_oversold and macd_positive:
        confidence = 60 + min(k_line[-1] - d_line[-1], 12) + min(vol_ratio * 2, 6)
        return Signal(symbol, 'LONG', 'stochrsi_macd_combo', confidence,
                     closes[-1], f"StochRSI K({k_line[-1]:.1f}) crossed above D({d_line[-1]:.1f}) "
                     f"from oversold(<20). MACD hist +{hist[-1]:.6f}. Vol {vol_ratio:.1f}x.",
                     sl_pct=2.0)
    return None


ALL_STRATEGIES = [
    strategy_macd_crossover,
    strategy_rsi_bounce,
    strategy_macd_rsi_confluence,
    strategy_volume_spike_breakout,
    strategy_bollinger_squeeze,
    strategy_ema_stack,
    strategy_funding_reversal,
    strategy_stochrsi_macd_combo,
]


# ── Self-Learning: Strategy Weight Adaptation ────────────────────────────────

_strategy_weights: dict = {}  # strategy_name -> multiplier (0.2 to 2.0)
_killed_strategies: set = set()  # strategies disabled due to terrible WR

# Minimum confidence to appear on dashboard — filters out noise
MIN_DISPLAY_CONFIDENCE = 58

# Hard-BANNED strategies — blocked at generation time regardless of DB stats.
# These are proven losers that must never enter now_picks.json / active_picks.json.
# macd_crossover: 25-31% WR, confirmed loser across LONGs and SHORTs.
# rsi_overbought: 29% WR on SHORTs, -17.1% PnL — the SHORT branch of strategy_rsi_bounce.
BANNED_STRATEGIES: set = {
    "macd_crossover",
    "rsi_overbought",
}

def load_strategy_weights():
    """Load strategy performance from DB and compute adaptive weights.

    Self-learning tiers:
    - WR < 25% after 50+ picks: KILLED (strategy disabled entirely)
    - WR < 35% after 30+ picks: heavy penalty (0.2x-0.4x — nearly killed)
    - WR 35-45%: moderate penalty (0.5x-0.7x)
    - WR 45-55%: neutral zone (0.8x-1.1x)
    - WR 55-65%: boosted (1.2x-1.5x)
    - WR > 65%: strongly boosted (1.5x-2.0x)
    """
    global _strategy_weights, _killed_strategies
    MIN_PICKS_ADAPT = 10    # Start adapting after 10
    MIN_PICKS_KILL = 50     # Can kill after 50
    MIN_PICKS_HEAVY = 30    # Heavy penalty after 30
    KILL_WR_THRESHOLD = 25  # WR below this = dead strategy
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT strategy, total_picks, wins_1_5, losses_1_5, win_rate_1_5, avg_pnl_pct FROM now_strategy_stats")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()

        for row in rows:
            name = row['strategy']
            total = int(row.get('total_picks', 0))
            wr = float(row.get('win_rate_1_5', 50))
            avg_pnl = float(row.get('avg_pnl_pct', 0))

            if total < MIN_PICKS_ADAPT:
                _strategy_weights[name] = 1.0
                continue

            # KILL SWITCH: disable strategies that are proven losers
            if total >= MIN_PICKS_KILL and wr < KILL_WR_THRESHOLD:
                _killed_strategies.add(name)
                _strategy_weights[name] = 0.0
                log.warning(f"  KILLED strategy '{name}': WR={wr:.1f}% after {total} picks")
                continue

            # Heavy penalty for bad performers with enough data
            if total >= MIN_PICKS_HEAVY and wr < 35:
                weight = 0.2 + (wr / 35) * 0.2  # 0.2 to 0.4
            elif wr < 45:
                weight = 0.5 + (wr - 35) / 10 * 0.2  # 0.5 to 0.7
            elif wr <= 55:
                weight = 0.8 + (wr - 45) / 10 * 0.3  # 0.8 to 1.1
            elif wr <= 65:
                weight = 1.2 + (wr - 55) / 10 * 0.3  # 1.2 to 1.5
            else:
                weight = 1.5 + min((wr - 65) / 20, 0.5)  # 1.5 to 2.0

            # PnL bonus/penalty on top
            pnl_adj = max(min(avg_pnl / 3.0, 0.3), -0.3)
            weight = max(0.2, min(2.0, weight + pnl_adj))
            _strategy_weights[name] = weight

        if _strategy_weights:
            log.info(f"Self-learning weights: {_strategy_weights}")
        if _killed_strategies:
            log.warning(f"Killed strategies (WR<{KILL_WR_THRESHOLD}%): {_killed_strategies}")
    except Exception as e:
        log.debug(f"Could not load strategy weights: {e}")


def apply_strategy_weight(signal: Signal) -> Optional[Signal]:
    """Apply self-learning weight to a signal's confidence score.
    Returns None if strategy is banned/killed or confidence falls below threshold."""
    # Hard BANNED check — enforced at generation time, never enters picks files
    if signal.strategy in BANNED_STRATEGIES:
        log.info(f"  BANNED: {signal.symbol} {signal.direction} via {signal.strategy} (hard-banned, proven loser)")
        return None

    # Kill switch: strategy is disabled (dynamic, from DB WR stats)
    if signal.strategy in _killed_strategies:
        log.info(f"  BLOCKED: {signal.symbol} {signal.direction} via {signal.strategy} (killed)")
        return None

    w = _strategy_weights.get(signal.strategy, 1.0)
    if w != 1.0:
        old_conf = signal.confidence
        signal.confidence = min(95, max(20, signal.confidence * w))
        if abs(old_conf - signal.confidence) > 1:
            log.info(f"  Self-learn: {signal.strategy} weight={w:.2f} -> "
                     f"conf {old_conf:.0f}% -> {signal.confidence:.0f}%")

    # Filter out low-confidence signals
    if signal.confidence < MIN_DISPLAY_CONFIDENCE:
        log.info(f"  FILTERED: {signal.symbol} via {signal.strategy} conf={signal.confidence:.0f}% < {MIN_DISPLAY_CONFIDENCE}%")
        return None

    return signal


# ── MySQL Database ───────────────────────────────────────────────────────────

def get_db():
    """Get a MySQL connection."""
    try:
        import pymysql
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import pymysql
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                           password=DB_PASS, database=DB_NAME,
                           charset='utf8mb4', connect_timeout=15,
                           autocommit=True)


def ensure_tables():
    """Create now_history and now_strategy_stats tables if they don't exist."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS now_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                run_id VARCHAR(36) NOT NULL,
                scan_time DATETIME NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                direction ENUM('LONG','SHORT') NOT NULL,
                strategy VARCHAR(50) NOT NULL,
                entry_price DECIMAL(20,8) NOT NULL,
                sl_price DECIMAL(20,8),
                tp_price_1_5 DECIMAL(20,8),
                tp_price_2_0 DECIMAL(20,8),
                sl_pct DECIMAL(8,4),
                confidence DECIMAL(5,2),
                reason TEXT,
                outcome_1_5 ENUM('PENDING','TP_HIT','SL_HIT','EXPIRED') DEFAULT 'PENDING',
                outcome_2_0 ENUM('PENDING','TP_HIT','SL_HIT','EXPIRED') DEFAULT 'PENDING',
                peak_price DECIMAL(20,8),
                trough_price DECIMAL(20,8),
                resolved_at DATETIME,
                actual_pnl_pct DECIMAL(8,4),
                INDEX idx_symbol (symbol),
                INDEX idx_strategy (strategy),
                INDEX idx_scan_time (scan_time),
                INDEX idx_pending (outcome_1_5, scan_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS now_strategy_stats (
                strategy VARCHAR(50) PRIMARY KEY,
                total_picks INT DEFAULT 0,
                wins_1_5 INT DEFAULT 0,
                losses_1_5 INT DEFAULT 0,
                wins_2_0 INT DEFAULT 0,
                losses_2_0 INT DEFAULT 0,
                expired INT DEFAULT 0,
                win_rate_1_5 DECIMAL(5,2) DEFAULT 0,
                win_rate_2_0 DECIMAL(5,2) DEFAULT 0,
                avg_pnl_pct DECIMAL(8,4) DEFAULT 0,
                best_trade_pct DECIMAL(8,4) DEFAULT 0,
                worst_trade_pct DECIMAL(8,4) DEFAULT 0,
                last_updated DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.close()
        conn.close()
        log.info("DB tables verified")
        return True
    except Exception as e:
        log.warning(f"DB table creation failed (will use JSON fallback): {e}")
        return False


def insert_picks(run_id: str, scan_time: datetime, signals: List[Signal]) -> int:
    """Insert picks into now_history. Returns count inserted."""
    if not signals:
        return 0
    try:
        conn = get_db()
        cur = conn.cursor()
        count = 0
        for s in signals:
            cur.execute("""
                INSERT INTO now_history (run_id, scan_time, symbol, direction, strategy,
                    entry_price, sl_price, tp_price_1_5, tp_price_2_0, sl_pct, confidence, reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (run_id, scan_time, s.symbol, s.direction, s.strategy,
                  s.entry_price, s.sl_price, s.tp_price_1_5, s.tp_price_2_0,
                  s.sl_pct, s.confidence, s.reason))
            count += 1
        cur.close()
        conn.close()
        return count
    except Exception as e:
        log.warning(f"DB insert failed: {e}")
        return 0


def resolve_pending_picks() -> dict:
    """Check pending picks from >1h ago and resolve their TP/SL outcomes."""
    stats = {'resolved': 0, 'tp_1_5': 0, 'tp_2_0': 0, 'sl': 0, 'expired': 0}
    try:
        conn = get_db()
        cur = conn.cursor()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=HOLDING_PERIOD_HOURS)
        cur.execute("""
            SELECT id, symbol, direction, entry_price, sl_price, tp_price_1_5, tp_price_2_0, scan_time
            FROM now_history
            WHERE outcome_1_5 = 'PENDING' AND scan_time < %s
            ORDER BY scan_time ASC LIMIT 50
        """, (cutoff.strftime('%Y-%m-%d %H:%M:%S'),))
        pending = cur.fetchall()

        for row in pending:
            pid, symbol, direction, entry, sl, tp15, tp20, scan_time = row
            # Fetch 1m klines for the hour after the pick
            end_time = int((scan_time.replace(tzinfo=timezone.utc) + timedelta(hours=1)).timestamp() * 1000)
            start_time = int(scan_time.replace(tzinfo=timezone.utc).timestamp() * 1000)
            kline_data = fetch_binance(
                f"/api/v3/klines?symbol={symbol}&interval=1m&startTime={start_time}&endTime={end_time}&limit=60"
            )
            if not kline_data:
                # Can't resolve without data — mark expired
                cur.execute("""
                    UPDATE now_history SET outcome_1_5='EXPIRED', outcome_2_0='EXPIRED',
                    resolved_at=NOW() WHERE id=%s
                """, (pid,))
                stats['expired'] += 1
                stats['resolved'] += 1
                continue

            peak = float(entry)
            trough = float(entry)
            o15 = 'EXPIRED'
            o20 = 'EXPIRED'
            actual_pnl = 0

            for k in kline_data:
                high = float(k[2])
                low = float(k[3])
                close = float(k[4])
                peak = max(peak, high)
                trough = min(trough, low)

                if direction == 'LONG':
                    if high >= float(tp15) and o15 == 'EXPIRED':
                        o15 = 'TP_HIT'
                    if high >= float(tp20) and o20 == 'EXPIRED':
                        o20 = 'TP_HIT'
                    if low <= float(sl):
                        if o15 == 'EXPIRED':
                            o15 = 'SL_HIT'
                        if o20 == 'EXPIRED':
                            o20 = 'SL_HIT'
                        break
                else:
                    if low <= float(tp15) and o15 == 'EXPIRED':
                        o15 = 'TP_HIT'
                    if low <= float(tp20) and o20 == 'EXPIRED':
                        o20 = 'TP_HIT'
                    if high >= float(sl):
                        if o15 == 'EXPIRED':
                            o15 = 'SL_HIT'
                        if o20 == 'EXPIRED':
                            o20 = 'SL_HIT'
                        break

            # Calculate actual PnL at end of period
            last_close = float(kline_data[-1][4]) if kline_data else float(entry)
            if direction == 'LONG':
                actual_pnl = (last_close - float(entry)) / float(entry) * 100
            else:
                actual_pnl = (float(entry) - last_close) / float(entry) * 100

            cur.execute("""
                UPDATE now_history SET outcome_1_5=%s, outcome_2_0=%s, peak_price=%s,
                trough_price=%s, resolved_at=NOW(), actual_pnl_pct=%s WHERE id=%s
            """, (o15, o20, peak, trough, actual_pnl, pid))

            stats['resolved'] += 1
            if 'TP' in o15:
                stats['tp_1_5'] += 1
            if 'TP' in o20:
                stats['tp_2_0'] += 1
            if 'SL' in o15:
                stats['sl'] += 1
            if o15 == 'EXPIRED':
                stats['expired'] += 1

        # Update strategy stats
        cur.execute("""
            INSERT INTO now_strategy_stats (strategy, total_picks, wins_1_5, losses_1_5,
                wins_2_0, losses_2_0, expired, win_rate_1_5, win_rate_2_0, avg_pnl_pct,
                best_trade_pct, worst_trade_pct, last_updated)
            SELECT strategy,
                COUNT(*) as total,
                SUM(outcome_1_5='TP_HIT') as w15,
                SUM(outcome_1_5='SL_HIT') as l15,
                SUM(outcome_2_0='TP_HIT') as w20,
                SUM(outcome_2_0='SL_HIT') as l20,
                SUM(outcome_1_5='EXPIRED') as exp,
                ROUND(SUM(outcome_1_5='TP_HIT') / NULLIF(SUM(outcome_1_5 IN ('TP_HIT','SL_HIT')), 0) * 100, 2),
                ROUND(SUM(outcome_2_0='TP_HIT') / NULLIF(SUM(outcome_2_0 IN ('TP_HIT','SL_HIT')), 0) * 100, 2),
                ROUND(AVG(actual_pnl_pct), 4),
                ROUND(MAX(actual_pnl_pct), 4),
                ROUND(MIN(actual_pnl_pct), 4),
                NOW()
            FROM now_history
            WHERE outcome_1_5 != 'PENDING'
            GROUP BY strategy
            ON DUPLICATE KEY UPDATE
                total_picks=VALUES(total_picks), wins_1_5=VALUES(wins_1_5),
                losses_1_5=VALUES(losses_1_5), wins_2_0=VALUES(wins_2_0),
                losses_2_0=VALUES(losses_2_0), expired=VALUES(expired),
                win_rate_1_5=VALUES(win_rate_1_5), win_rate_2_0=VALUES(win_rate_2_0),
                avg_pnl_pct=VALUES(avg_pnl_pct), best_trade_pct=VALUES(best_trade_pct),
                worst_trade_pct=VALUES(worst_trade_pct), last_updated=VALUES(last_updated)
        """)

        cur.close()
        conn.close()
    except Exception as e:
        log.warning(f"Resolve failed: {e}")
    return stats


def get_strategy_stats() -> List[dict]:
    """Fetch strategy stats from DB."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM now_strategy_stats ORDER BY win_rate_1_5 DESC")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        log.warning(f"Stats fetch failed: {e}")
        return []


def get_recent_history(limit: int = 50) -> List[dict]:
    """Fetch recent picks from DB."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, run_id, scan_time, symbol, direction, strategy, entry_price,
                   sl_price, tp_price_1_5, tp_price_2_0, confidence, reason,
                   outcome_1_5, outcome_2_0, peak_price, trough_price, resolved_at, actual_pnl_pct
            FROM now_history ORDER BY scan_time DESC LIMIT %s
        """, (limit,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        log.warning(f"History fetch failed: {e}")
        return []


# ── JSON Fallback (when DB is unavailable) ───────────────────────────────────

def save_picks_json(run_id: str, scan_time: str, signals: List[Signal]):
    """Save picks to local JSON as DB fallback."""
    picks_file = DATA_DIR / 'now_picks.json'
    existing = []
    if picks_file.exists():
        try:
            existing = json.loads(picks_file.read_text(encoding='utf-8'))
        except:
            pass
    for s in signals:
        existing.append({
            **s.to_dict(), 'run_id': run_id, 'scan_time': scan_time,
            'outcome_1_5': 'PENDING', 'outcome_2_0': 'PENDING',
        })
    # Keep last 500
    existing = existing[-500:]
    picks_file.write_text(json.dumps(existing, indent=2, default=str), encoding='utf-8')


# ── HTML Report Generation ───────────────────────────────────────────────────

def generate_html_report(signals: List[Signal], run_id: str, scan_time: str,
                         resolve_stats: dict, strategy_stats: List[dict],
                         recent_history: List[dict],
                         scan_time_dt: datetime = None):
    """Generate the Rapid Fire HTML report."""
    if scan_time_dt is None:
        scan_time_dt = datetime.now(timezone.utc)
    now_est = scan_time_dt.astimezone(
        timezone(timedelta(hours=-5))
    ).strftime('%b %d, %Y %I:%M %p EST')

    # Build signals HTML
    signals_html = ""
    for i, s in enumerate(sorted(signals, key=lambda x: x.confidence, reverse=True)):
        conf_cls = 'badge-high' if s.confidence >= 70 else 'badge-medium' if s.confidence >= 55 else 'badge-low'
        tp15_pct = abs(s.tp_price_1_5 - s.entry_price) / s.entry_price * 100
        tp20_pct = abs(s.tp_price_2_0 - s.entry_price) / s.entry_price * 100
        signals_html += f"""<tr>
            <td>{i+1}</td>
            <td><span class="symbol">{s.symbol}</span></td>
            <td><span class="badge badge-{'active' if s.direction=='LONG' else 'closed'}">{s.direction}</span></td>
            <td>{s.strategy}</td>
            <td>${s.entry_price:,.4f}</td>
            <td><span style="color:#22c55e">+{tp15_pct:.1f}%</span> / <span style="color:#ef4444">-{s.sl_pct:.1f}%</span></td>
            <td><span style="color:#22c55e">+{tp20_pct:.1f}%</span> / <span style="color:#ef4444">-{s.sl_pct:.1f}%</span></td>
            <td><span class="badge {conf_cls}">{s.confidence:.0f}%</span></td>
            <td style="font-size:0.75rem;color:#aaa;max-width:300px">{s.reason}</td>
        </tr>"""

    if not signals_html:
        signals_html = '<tr><td colspan="9" style="text-align:center;color:#888;padding:30px;">No signals this scan. 8 strategies scanning 50 pairs every 15 min.</td></tr>'

    # Strategy stats HTML
    stats_html = ""
    for st in strategy_stats:
        wr15 = float(st.get('win_rate_1_5') or 0)
        wr20 = float(st.get('win_rate_2_0') or 0)
        avg = float(st.get('avg_pnl_pct') or 0)
        stats_html += f"""<tr>
            <td>{st['strategy']}</td>
            <td>{st.get('total_picks', 0)}</td>
            <td>{st.get('wins_1_5', 0)}</td>
            <td>{st.get('losses_1_5', 0)}</td>
            <td class="{'pnl-pos' if wr15>=50 else 'pnl-neg'}">{wr15:.1f}%</td>
            <td class="{'pnl-pos' if wr20>=50 else 'pnl-neg'}">{wr20:.1f}%</td>
            <td class="{'pnl-pos' if avg>=0 else 'pnl-neg'}">{avg:+.2f}%</td>
            <td class="pnl-pos">{float(st.get('best_trade_pct') or 0):+.2f}%</td>
            <td class="pnl-neg">{float(st.get('worst_trade_pct') or 0):+.2f}%</td>
        </tr>"""

    # Recent history HTML — convert UTC scan_time to EST
    est_tz = timezone(timedelta(hours=-5))
    history_html = ""
    for h in recent_history[:50]:
        o15 = h.get('outcome_1_5', 'PENDING')
        pnl = float(h.get('actual_pnl_pct') or 0)
        badge = {'TP_HIT': 'badge-high', 'SL_HIT': 'badge-closed', 'EXPIRED': 'badge-low', 'PENDING': 'badge-medium'}
        scan = h.get('scan_time', '')
        if hasattr(scan, 'strftime'):
            scan = scan.replace(tzinfo=timezone.utc).astimezone(est_tz).strftime('%b %d %I:%M %p EST')
        # Show "pending" instead of misleading 0% for unresolved picks
        if o15 == 'PENDING':
            pnl_display = '<span style="color:#888">pending</span>'
        else:
            pnl_display = f'<span class="{"pnl-pos" if pnl>=0 else "pnl-neg"}">{pnl:+.2f}%</span>'
        history_html += f"""<tr style="{'opacity:0.6' if o15 != 'PENDING' else ''}">
            <td>{scan}</td>
            <td class="symbol">{h.get('symbol','')}</td>
            <td>{h.get('strategy','')}</td>
            <td>${float(h.get('entry_price',0)):,.4f}</td>
            <td>{pnl_display}</td>
            <td><span class="badge {badge.get(o15,'badge-low')}">{o15}</span></td>
            <td><span class="badge {badge.get(h.get('outcome_2_0','PENDING'),'badge-low')}">{h.get('outcome_2_0','PENDING')}</span></td>
        </tr>"""

    # Overall stats
    total_resolved = sum(s.get('total_picks', 0) for s in strategy_stats)
    total_wins_15 = sum(s.get('wins_1_5', 0) for s in strategy_stats)
    total_losses_15 = sum(s.get('losses_1_5', 0) for s in strategy_stats)
    overall_wr = total_wins_15 / max(total_wins_15 + total_losses_15, 1) * 100

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapid Fire - Real-Time 1h Crypto Signals</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e0e0f0; line-height: 1.6; }}
        .container {{ max-width: 1500px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1a0a2e 0%, #2e1a0a 100%); padding: 30px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #3a2a1a; }}
        .header h1 {{ font-size: 2.2rem; background: linear-gradient(90deg, #ff6b35, #f7c948, #ff6b35); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .header p {{ color: #aaa; margin-top: 8px; }}
        .stats-bar {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 15px; margin-bottom: 25px; }}
        .stat-card {{ background: #12121c; border: 1px solid #2a2a3a; border-radius: 10px; padding: 16px; text-align: center; }}
        .stat-label {{ font-size: 0.72rem; text-transform: uppercase; color: #888; letter-spacing: 1px; }}
        .stat-value {{ font-size: 1.5rem; font-weight: 700; margin-top: 4px; }}
        .stat-value.green {{ color: #22c55e; }} .stat-value.red {{ color: #ef4444; }}
        .stat-value.orange {{ color: #f59e0b; }} .stat-value.blue {{ color: #3b82f6; }}
        .tabs {{ display: flex; gap: 5px; margin-bottom: 20px; flex-wrap: wrap; }}
        .tab {{ padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; background: transparent; color: #888; border: 1px solid #2a2a3a; transition: all 0.2s; }}
        .tab:hover {{ color: #e0e0f0; border-color: #555; }}
        .tab.active {{ background: #ff6b35; color: white; border-color: #ff6b35; }}
        .tab-content {{ display: none; }} .tab-content.active {{ display: block; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        th {{ text-align: left; padding: 10px 12px; background: #1a1a25; color: #888; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; position: sticky; top: 0; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #1a1a2a; }}
        tr:hover {{ background: rgba(255,255,255,0.03); }}
        .symbol {{ font-weight: bold; color: #ff6b35; }}
        .pnl-pos {{ color: #22c55e; font-weight: 600; }} .pnl-neg {{ color: #ef4444; font-weight: 600; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; text-transform: uppercase; }}
        .badge-high {{ background: #22c55e; color: white; }} .badge-medium {{ background: #f59e0b; color: black; }}
        .badge-low {{ background: #6b7280; color: white; }} .badge-closed {{ background: #374151; color: #9ca3af; }}
        .badge-active {{ background: rgba(34,197,94,0.2); color: #22c55e; border: 1px solid #22c55e; }}
        .section {{ background: #12121c; border: 1px solid #2a2a3a; border-radius: 10px; padding: 20px; margin-bottom: 20px; }}
        .section h3 {{ color: #ff6b35; margin-bottom: 15px; }}
        .last-updated {{ text-align: center; color: #888; font-size: 0.85rem; margin-top: 30px; padding: 20px; border-top: 1px solid #2a2a3a; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>RAPID FIRE</h1>
        <p>Real-Time 1h Crypto Signals — 8 strategies scanning 50 pairs every 15 min. Dual R:R tracking (1.5:1 &amp; 2:1).</p>
        <details style="margin-top:12px;cursor:pointer">
            <summary style="color:#ff6b35;font-weight:600;font-size:14px">How It Works — Self-Learning ML System</summary>
            <div style="margin-top:10px;color:#ccc;font-size:13px;line-height:1.6">
                <p><strong>8 Technical Strategies:</strong> MACD Crossover, Bollinger Squeeze, RSI Extremes, StochRSI+MACD Confluence, Volume Spike, EMA Stack Alignment, VWAP Reversion, Mean Reversion.</p>
                <p><strong>Self-Learning Weights:</strong> Each strategy's confidence is dynamically adjusted based on its historical win rate. Strategies that perform well get boosted (up to 1.5x), underperformers get dampened (down to 0.5x). Weights retrain automatically from resolved picks stored in MySQL.</p>
                <p><strong>Signal Pipeline:</strong> Binance 1h klines → technical indicator computation → strategy rule evaluation → confidence scoring with adaptive weights → ATR-based TP/SL (1.5:1 and 2:1 R:R) → pick output with auto-resolution tracking.</p>
                <p><strong>Resolution:</strong> Every 15-minute scan resolves prior picks against live prices. Wins/losses feed back into strategy weights, creating a continuously improving system.</p>
            </div>
        </details>
    </div>

    <div class="stats-bar">
        <div class="stat-card"><div class="stat-label">Signals Now</div><div class="stat-value orange">{len(signals)}</div></div>
        <div class="stat-card"><div class="stat-label">Total Tracked</div><div class="stat-value blue">{total_resolved}</div></div>
        <div class="stat-card"><div class="stat-label">Win Rate (1.5:1)</div><div class="stat-value {'green' if overall_wr>=50 else 'red'}">{overall_wr:.1f}%</div></div>
        <div class="stat-card"><div class="stat-label">Wins (1.5:1)</div><div class="stat-value green">{total_wins_15}</div></div>
        <div class="stat-card"><div class="stat-label">Losses</div><div class="stat-value red">{total_losses_15}</div></div>
        <div class="stat-card"><div class="stat-label">Last Resolved</div><div class="stat-value blue">{resolve_stats.get('resolved', 0)}</div></div>
    </div>

    <div class="tabs">
        <div class="tab active" data-tab="picks">Top Picks Now</div>
        <div class="tab" data-tab="track">Track Record</div>
        <div class="tab" data-tab="history">Recent History</div>
    </div>

    <div class="tab-content active" id="tab-picks">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;padding:8px 12px;background:#1a1a25;border-radius:8px;">
            <span style="color:#ff6b35;font-weight:600;font-size:0.9rem;">Scanned: {now_est}</span>
            <span id="staleness-badge" style="font-size:0.8rem;padding:3px 10px;border-radius:4px;font-weight:600;"></span>
        </div>
        <table>
            <thead><tr>
                <th>#</th><th>Symbol</th><th>Dir</th><th>Strategy</th><th>Entry</th>
                <th>TP/SL (1.5:1)</th><th>TP/SL (2:1)</th><th>Confidence</th><th>Reason</th>
            </tr></thead>
            <tbody>{signals_html}</tbody>
        </table>
    </div>

    <div class="tab-content" id="tab-track">
        <div class="section">
            <h3>Strategy Performance (Forward-Tested, Real Outcomes)</h3>
            <table>
                <thead><tr>
                    <th>Strategy</th><th>Picks</th><th>Wins</th><th>Losses</th>
                    <th>WR (1.5:1)</th><th>WR (2:1)</th><th>Avg PnL</th><th>Best</th><th>Worst</th>
                </tr></thead>
                <tbody>{stats_html if stats_html else '<tr><td colspan="9" style="text-align:center;color:#888;padding:20px;">No resolved picks yet. Stats appear after 1+ hour of tracking.</td></tr>'}</tbody>
            </table>
        </div>
    </div>

    <div class="tab-content" id="tab-history">
        <table>
            <thead><tr>
                <th>Time</th><th>Symbol</th><th>Strategy</th><th>Entry</th><th>PnL</th><th>1.5:1</th><th>2:1</th>
            </tr></thead>
            <tbody>{history_html if history_html else '<tr><td colspan="7" style="text-align:center;color:#888;padding:20px;">No history yet. Picks will appear here after the first scan.</td></tr>'}</tbody>
        </table>
    </div>

    <div class="last-updated">
        Scan: {now_est} | Run ID: {run_id} | Resolved: {resolve_stats.get('resolved',0)} picks |
        TP hit: {resolve_stats.get('tp_1_5',0)} (1.5:1) / {resolve_stats.get('tp_2_0',0)} (2:1)
    </div>
</div>
<script>
document.querySelectorAll('.tab').forEach(tab => {{
    tab.addEventListener('click', () => {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    }});
}});
// Staleness detection — scan time is embedded as ISO for parsing
(function() {{
    var scanUTC = new Date('{scan_time_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}');
    function updateStaleness() {{
        var now = new Date();
        var diffMin = Math.floor((now - scanUTC) / 60000);
        var badge = document.getElementById('staleness-badge');
        if (!badge) return;
        if (diffMin < 20) {{
            badge.textContent = 'LIVE (' + diffMin + 'm ago)';
            badge.style.background = 'rgba(34,197,94,0.2)';
            badge.style.color = '#22c55e';
        }} else if (diffMin < 45) {{
            badge.textContent = 'RECENT (' + diffMin + 'm ago)';
            badge.style.background = 'rgba(245,158,11,0.2)';
            badge.style.color = '#f59e0b';
        }} else {{
            var hours = Math.floor(diffMin / 60);
            var mins = diffMin % 60;
            badge.textContent = 'STALE (' + (hours > 0 ? hours + 'h ' : '') + mins + 'm ago)';
            badge.style.background = 'rgba(239,68,68,0.2)';
            badge.style.color = '#ef4444';
        }}
    }}
    updateStaleness();
    setInterval(updateStaleness, 60000);
}})();
</script>
</body>
</html>"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(html, encoding='utf-8')
    log.info(f"Report written to {REPORT_PATH}")

    # Also save active picks JSON for cross-aggregator (deduplicated)
    active_json = DATA_DIR / 'active_picks.json'
    picks_data = [s.to_dict() | {'scan_time': scan_time, 'source': SOURCE_SYSTEM} for s in signals]
    # Dedup: keep highest-confidence pick per (symbol, direction, entry_price)
    seen_keys = {}
    for p in picks_data:
        key = (p.get('symbol', ''), p.get('direction', ''), str(p.get('entry_price', '')))
        if key not in seen_keys or p.get('confidence', 0) > seen_keys[key].get('confidence', 0):
            seen_keys[key] = p
    picks_data = sorted(seen_keys.values(), key=lambda x: x.get('confidence', 0), reverse=True)
    active_json.write_text(json.dumps(picks_data, indent=2, default=str), encoding='utf-8')


# ── Main Scanner ─────────────────────────────────────────────────────────────

def _get_htf_trend(symbol: str) -> str:
    """Get higher-timeframe (1h) trend direction using 20/50 EMA.
    Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    klines_1h = get_klines(symbol, '1h', 60)
    if len(klines_1h) < 55:
        return 'NEUTRAL'
    closes = [k['close'] for k in klines_1h]
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    if not ema20[-1] or not ema50[-1]:
        return 'NEUTRAL'
    # Strong trend: EMA20 clearly above/below EMA50
    sep_pct = (ema20[-1] - ema50[-1]) / ema50[-1] * 100
    if sep_pct > 0.3:
        return 'BULLISH'
    elif sep_pct < -0.3:
        return 'BEARISH'
    return 'NEUTRAL'


def _scan_symbol(symbol: str) -> List[Signal]:
    """Scan a single symbol across all strategies. Thread-safe.
    Applies HTF trend filter: blocks counter-trend signals."""
    signals = []
    klines_5m = get_klines(symbol, '5m', 100)
    if len(klines_5m) < 35:
        return signals

    # Get 1h trend for filtering
    htf_trend = _get_htf_trend(symbol)

    for strat_fn in ALL_STRATEGIES:
        try:
            signal = strat_fn(symbol, klines_5m)
            if signal:
                # HTF trend filter: block counter-trend signals
                if htf_trend == 'BEARISH' and signal.direction == 'LONG':
                    log.debug(f"  HTF FILTER: blocked LONG {symbol} (1h trend bearish)")
                    continue
                if htf_trend == 'BULLISH' and signal.direction == 'SHORT':
                    log.debug(f"  HTF FILTER: blocked SHORT {symbol} (1h trend bullish)")
                    continue
                # Trend-aligned signals get a confidence boost
                if (htf_trend == 'BULLISH' and signal.direction == 'LONG') or \
                   (htf_trend == 'BEARISH' and signal.direction == 'SHORT'):
                    signal.confidence = min(95, signal.confidence + 5)
                signals.append(signal)
        except Exception:
            pass
    return signals


def run_scan(pair_count: int = TOP_N_PAIRS):
    """Main scan: fetch data, run strategies, log picks, generate report."""
    run_id = str(uuid.uuid4())[:8]
    scan_time = datetime.now(timezone.utc)
    scan_str = scan_time.strftime('%Y-%m-%d %H:%M:%S')
    t_start = time.time()

    log.info(f"{'='*60}")
    log.info(f"  RAPID FIRE — Scan {run_id}")
    log.info(f"  {scan_str} UTC")
    log.info(f"  8 strategies x {pair_count} pairs = {8*pair_count} checks")
    log.info(f"{'='*60}")

    # 1. Ensure DB tables exist
    db_ok = ensure_tables()

    # 2. Resolve pending picks from previous runs
    log.info("Resolving pending picks from previous scans...")
    resolve_stats = resolve_pending_picks() if db_ok else {}
    if resolve_stats.get('resolved', 0) > 0:
        log.info(f"  Resolved {resolve_stats['resolved']} picks: "
                 f"TP(1.5:1)={resolve_stats['tp_1_5']}, TP(2:1)={resolve_stats['tp_2_0']}, "
                 f"SL={resolve_stats['sl']}, Expired={resolve_stats['expired']}")

    # 2b. Load self-learning weights
    if db_ok:
        load_strategy_weights()

    # 3. Get top pairs
    log.info(f"Fetching top {pair_count} USDT pairs...")
    pairs = get_top_pairs()[:pair_count]
    log.info(f"  Got {len(pairs)} pairs")

    # 4. Run strategies on each pair (parallel with 5 threads)
    all_signals: List[Signal] = []
    t_fetch = time.time()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_scan_symbol, sym): sym for sym in pairs}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                signals = future.result()
                for s in signals:
                    all_signals.append(s)
                    log.info(f"  SIGNAL: {s.symbol} {s.direction} via {s.strategy} "
                             f"(conf: {s.confidence:.0f}%)")
            except Exception as e:
                log.debug(f"  Error scanning {sym}: {e}")
    scan_duration = time.time() - t_fetch
    log.info(f"  Scanned {len(pairs)} pairs in {scan_duration:.1f}s")

    # Apply self-learning weights, filter killed/low-confidence, sort
    all_signals = [s for s in (apply_strategy_weight(s) for s in all_signals) if s is not None]
    all_signals.sort(key=lambda s: s.confidence, reverse=True)

    # 5. Log to DB
    if db_ok and all_signals:
        inserted = insert_picks(run_id, scan_time, all_signals)
        log.info(f"Inserted {inserted} picks to MySQL")
    if all_signals:
        save_picks_json(run_id, scan_str, all_signals)

    # 6. Fetch stats and history for report
    strategy_stats = get_strategy_stats() if db_ok else []
    recent_history = get_recent_history(50) if db_ok else []

    # 7. Generate HTML report
    generate_html_report(all_signals, run_id, scan_str, resolve_stats,
                         strategy_stats, recent_history, scan_time_dt=scan_time)

    # 8. Print summary
    total_time = time.time() - t_start
    log.info(f"\n{'='*60}")
    log.info(f"  SCAN COMPLETE — {len(all_signals)} signals found in {total_time:.1f}s")
    log.info(f"  Fetch+analyze: {scan_duration:.1f}s | Pairs: {len(pairs)} | Strategies: 8")
    log.info(f"{'='*60}")
    if all_signals:
        log.info(f"\n  TOP PICKS:")
        for i, s in enumerate(all_signals[:10]):
            tp_pct = abs(s.tp_price_1_5 - s.entry_price) / s.entry_price * 100
            log.info(f"  {i+1}. {s.symbol:12s} {s.direction:5s} via {s.strategy:25s} "
                     f"conf={s.confidence:.0f}% TP=+{tp_pct:.1f}% SL=-{s.sl_pct:.1f}%")
    else:
        log.info("  No signals this scan. Markets may be quiet.")

    return all_signals


def print_stats():
    """Print strategy stats from DB."""
    ensure_tables()
    stats = get_strategy_stats()
    if not stats:
        print("No stats yet. Run a few scans first.")
        return
    print(f"\n{'Strategy':<30} {'Picks':>6} {'W(1.5)':>7} {'L(1.5)':>7} {'WR(1.5)':>8} "
          f"{'WR(2.0)':>8} {'AvgPnL':>8} {'Best':>8} {'Worst':>8}")
    print("-" * 100)
    for s in stats:
        print(f"{s['strategy']:<30} {s.get('total_picks',0):>6} {s.get('wins_1_5',0):>7} "
              f"{s.get('losses_1_5',0):>7} {float(s.get('win_rate_1_5') or 0):>7.1f}% "
              f"{float(s.get('win_rate_2_0') or 0):>7.1f}% {float(s.get('avg_pnl_pct') or 0):>+7.2f}% "
              f"{float(s.get('best_trade_pct') or 0):>+7.2f}% {float(s.get('worst_trade_pct') or 0):>+7.2f}%")


if __name__ == '__main__':
    if '--resolve' in sys.argv:
        ensure_tables()
        stats = resolve_pending_picks()
        print(f"Resolved: {stats}")
    elif '--stats' in sys.argv:
        print_stats()
    else:
        # Parse --pairs N
        n_pairs = TOP_N_PAIRS
        if '--pairs' in sys.argv:
            idx = sys.argv.index('--pairs')
            if idx + 1 < len(sys.argv):
                try:
                    n_pairs = int(sys.argv[idx + 1])
                except ValueError:
                    pass
        run_scan(pair_count=n_pairs)
