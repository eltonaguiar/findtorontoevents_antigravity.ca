#!/usr/bin/env python3
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

Multi-Portfolio Theory Tester
==============================
4 independent virtual portfolios, each using different data sources
and making FRESH picks (not stealing from existing strategies).

Portfolio A: "Proven Only" — picks from WF STRONG strategies (existing tracker)
Portfolio B: "News Sentiment" — NewsAPI headlines drive contrarian crypto picks
Portfolio C: "Technical Confluence" — RSI + EMA + Volume must ALL agree
Portfolio D: "Funding Contrarian" — fade extreme funding rates + open interest

Each portfolio: $10K virtual capital, 5% per trade, hourly check.
Stdlib only. Windows UTF-8 safe.
"""

import json
import math
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
PORTFOLIOS_FILE = DATA / "theory_portfolios.json"
PORTFOLIOS_HISTORY = DATA / "theory_portfolios_history.json"

VIRTUAL_CAPITAL = 10000.0
POSITION_SIZE_PCT = 0.05
MAX_POSITIONS = 5

BINANCE_MIRRORS = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://api2.binance.com", "https://api3.binance.com",
]

NEWSAPI_KEY = "57674b4c23eb4ecb93044c57c9106bea"

# Symbols we trade
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT"]

SYMBOL_NAMES = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "BNBUSDT": "bnb", "XRPUSDT": "xrp", "ADAUSDT": "cardano",
    "DOGEUSDT": "dogecoin", "AVAXUSDT": "avalanche", "LINKUSDT": "chainlink",
    "NEARUSDT": "near protocol",
}


# ─── Shared Helpers ───────────────────────────────────────────────────

def _fetch_json(url: str, timeout: int = 10) -> Any:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout, context=ctx).read())


def _fetch_price(symbol: str) -> float:
    for mirror in BINANCE_MIRRORS:
        try:
            data = _fetch_json(f"{mirror}/api/v3/ticker/price?symbol={symbol}")
            return float(data["price"])
        except Exception:
            continue
    return 0.0


def _fetch_klines(symbol: str, interval: str = "1h", limit: int = 50) -> list:
    for mirror in BINANCE_MIRRORS:
        try:
            return _fetch_json(f"{mirror}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}")
        except Exception:
            continue
    return []


def _smart_round(value: float) -> float:
    if value == 0: return 0.0
    av = abs(value)
    if av >= 100: return round(value, 2)
    elif av >= 1: return round(value, 4)
    elif av >= 0.01: return round(value, 6)
    else: return round(value, 10)


def _compute_rsi(closes: list, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0: return 100.0
    return 100 - (100 / (1 + ag / al))


def _compute_ema(closes: list, period: int) -> float:
    if len(closes) < period:
        return sum(closes) / len(closes) if closes else 0
    alpha = 2.0 / (period + 1)
    ema = closes[0]
    for c in closes[1:]:
        ema = alpha * c + (1 - alpha) * ema
    return ema


def _fetch_atr(symbol: str, period: int = 14) -> float:
    """Compute ATR from hourly klines. Stdlib only."""
    klines = _fetch_klines(symbol, interval="1h", limit=period + 1)
    if len(klines) < 2:
        return 0.0
    trs = []
    for i in range(1, len(klines)):
        high = float(klines[i][2])
        low = float(klines[i][3])
        prev_close = float(klines[i - 1][4])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs[-period:]) / min(len(trs), period) if trs else 0.0


def _vol_scaled_size(symbol: str, entry_price: float, equity: float) -> float:
    """Volatility-scaled position sizing (Protocol v4.0). Floor 2%, ceiling 8%."""
    atr = _fetch_atr(symbol)
    if atr > 0 and entry_price > 0:
        risk_amount = equity * 0.01
        position_value = risk_amount / (atr / entry_price)
    else:
        position_value = equity * POSITION_SIZE_PCT
    position_value = max(position_value, equity * 0.02)
    position_value = min(position_value, equity * 0.08)
    return round(position_value, 2)


def _strategy_passes_gate(strategy_name: str) -> bool:
    """Check if strategy passes DSR gate from promotion_gate_report."""
    gate_file = DATA / "promotion_gate_report.json"
    if not gate_file.exists():
        return True
    try:
        report = json.loads(gate_file.read_text(encoding="utf-8"))
        decisions = report.get("decisions", [])
        for entry in decisions:
            sid = entry.get("strategy", "")
            if strategy_name in sid or sid in strategy_name:
                dsr = entry.get("deflated_sharpe", 0) or 0
                if dsr < 1.64:
                    return False
        return True
    except Exception:
        return True


def _fetch_recent_returns(symbol: str, limit: int = 24) -> list:
    """Fetch recent hourly returns for correlation check."""
    klines = _fetch_klines(symbol, interval="1h", limit=limit)
    closes = [float(k[4]) for k in klines]
    if len(closes) < 2:
        return []
    return [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]


def _pearson_r(x: list, y: list) -> float:
    """Pearson correlation coefficient. Stdlib only."""
    n = min(len(x), len(y))
    if n < 5:
        return 0.0
    x, y = x[:n], y[:n]
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    dy = sum((yi - my) ** 2 for yi in y) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def _passes_correlation_gate(symbol: str, portfolio: dict, threshold: float = 0.75) -> bool:
    """Reject if Pearson r > threshold with any existing position."""
    active = portfolio.get("active_positions", [])
    if not active:
        return True
    new_returns = _fetch_recent_returns(symbol)
    if not new_returns:
        return True
    for pos in active:
        existing_sym = pos.get("symbol", "")
        if existing_sym == symbol:
            continue
        existing_returns = _fetch_recent_returns(existing_sym)
        if not existing_returns:
            continue
        r = _pearson_r(new_returns, existing_returns)
        if abs(r) > threshold:
            return False
    return True


def _compute_vwap(klines: list) -> float:
    cum_tpv, cum_vol = 0.0, 0.0
    for k in klines:
        h, l, c, v = float(k[2]), float(k[3]), float(k[4]), float(k[5])
        cum_tpv += ((h + l + c) / 3) * v
        cum_vol += v
    return cum_tpv / cum_vol if cum_vol > 0 else 0.0


def _make_pick(symbol: str, direction: str, price: float, tp_pct: float,
               sl_pct: float, confidence: float, strategy: str, reason: str) -> dict:
    if direction == "LONG":
        tp = _smart_round(price * (1 + tp_pct))
        sl = _smart_round(price * (1 - sl_pct))
    else:
        tp = _smart_round(price * (1 - tp_pct))
        sl = _smart_round(price * (1 + sl_pct))

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": price,
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": round(confidence, 3),
        "strategy": strategy,
        "rr": round(tp_pct / sl_pct, 2) if sl_pct > 0 else 0,
        "position_value": _vol_scaled_size(symbol, price, VIRTUAL_CAPITAL),
        "entered_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "status": "OPEN",
    }


# ─── Portfolio B: News Sentiment ──────────────────────────────────────

def _fetch_crypto_news() -> list:
    """Fetch crypto news from NewsAPI and score sentiment."""
    try:
        url = (f"https://newsapi.org/v2/everything?"
               f"q=cryptocurrency+OR+bitcoin+OR+ethereum&"
               f"language=en&sortBy=publishedAt&pageSize=30&"
               f"apiKey={NEWSAPI_KEY}")
        data = _fetch_json(url, timeout=15)
        return data.get("articles", [])
    except Exception:
        return []


def _score_sentiment(articles: list) -> dict:
    """Simple keyword sentiment scoring per symbol."""
    BULLISH = {"surge", "rally", "soar", "bull", "breakout", "record", "high",
               "adoption", "etf approved", "institutional", "accumulate", "upgrade"}
    BEARISH = {"crash", "plunge", "dump", "bear", "selloff", "hack", "ban",
               "regulation", "sec", "fraud", "collapse", "liquidation", "fear"}

    scores = {}
    for sym, name in SYMBOL_NAMES.items():
        bull, bear, mentions = 0, 0, 0
        for art in articles:
            text = (art.get("title", "") + " " + (art.get("description", "") or "")).lower()
            if name in text or sym.replace("USDT", "").lower() in text:
                mentions += 1
                for w in BULLISH:
                    if w in text: bull += 1
                for w in BEARISH:
                    if w in text: bear += 1

        if mentions > 0:
            net = bull - bear
            scores[sym] = {"bull": bull, "bear": bear, "net": net, "mentions": mentions}

    return scores


def generate_news_picks() -> list:
    """Portfolio B: Contrarian news sentiment picks.

    TWEAK: Added Mercury 2 regime gate (same as C).
    In bear: only SHORT picks. In bull: only LONG picks.
    Data: LONG 0W/1L (0% WR) vs SHORT 4W/2L (67% WR) across all portfolios.
    """
    # Regime gate
    try:
        from alpha_engine.mercury2_scorer import score_trade
        _regime = score_trade("BTCUSDT", "LONG", "CRYPTO").get("regime", "bear")
    except Exception:
        _regime = "bear"

    articles = _fetch_crypto_news()
    if not articles:
        return []

    sentiment = _score_sentiment(articles)
    picks = []

    for sym, s in sentiment.items():
        if s["mentions"] < 2:
            continue

        price = _fetch_price(sym)
        if price <= 0:
            continue

        net = s["net"]
        # Contrarian: negative news = LONG (fear = opportunity)
        # Positive news = SHORT (euphoria = danger)
        # Lowered thresholds — crypto news is sparse, net=-1 with 10 mentions is signal
        if net < 0 and s["mentions"] >= 3:
            direction = "LONG"
            if _regime == "bear":
                continue  # Block LONGs in bear regime (0% WR historically)
            confidence = min(0.85, 0.55 + abs(net) * 0.05 + s["mentions"] * 0.01)
            reason = f"News contrarian: {s['bear']} bearish vs {s['bull']} bullish headlines ({s['mentions']} mentions). Fading fear."
        elif net > 0 and s["mentions"] >= 3:
            direction = "SHORT"
            if _regime == "bull":
                continue  # Block SHORTs in bull regime
            confidence = min(0.85, 0.55 + abs(net) * 0.05 + s["mentions"] * 0.01)
            reason = f"News contrarian: {s['bull']} bullish vs {s['bear']} bearish headlines ({s['mentions']} mentions). Fading euphoria."
        elif s["mentions"] >= 5 and net == 0:
            direction = "SHORT" if _regime == "bear" else "LONG"
            confidence = 0.55
            reason = f"News momentum: {s['mentions']} mentions, regime={_regime}. Following trend."
        else:
            continue

        picks.append(_make_pick(sym, direction, price, 0.015, 0.012, confidence,
                                "news_sentiment_contrarian", reason))

    return picks[:MAX_POSITIONS]


# ─── Portfolio C: Technical Confluence ────────────────────────────────

def generate_confluence_picks() -> list:
    """Portfolio C: Only trade when RSI + EMA + Volume ALL agree.

    TWEAK (2026-04-02): Added Mercury 2 regime check.
    Don't enter LONG in bear regime, don't enter SHORT in bull regime.
    C was -$13 entering LONGs while BTC dropped — fighting the trend.
    """
    # Regime check via Mercury 2
    try:
        from alpha_engine.mercury2_scorer import score_trade
        regime_info = score_trade("BTCUSDT", "LONG", "CRYPTO")
        market_regime = regime_info.get("regime", "bear")
    except Exception:
        market_regime = "bear"  # Default bear = safer (blocks LONGs when detection fails)

    picks = []

    for sym in SYMBOLS:
        try:
            klines = _fetch_klines(sym, "1h", 50)
            if len(klines) < 30:
                continue

            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            price = closes[-1]
            if price <= 0:
                continue

            # Signal 1: RSI (relaxed from 35/65 to 40/60 — crypto ranges are tighter)
            rsi = _compute_rsi(closes, 14)
            rsi_long = rsi < 42
            rsi_short = rsi > 58

            # Signal 2: EMA crossover (9 vs 21)
            ema9 = _compute_ema(closes, 9)
            ema21 = _compute_ema(closes, 21)
            ema_long = ema9 > ema21
            ema_short = ema9 < ema21

            # Signal 3: Volume above average (confirmation)
            avg_vol = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
            vol_confirm = volumes[-1] > avg_vol * 1.2

            # Signal 4: VWAP position
            vwap = _compute_vwap(klines[-24:])
            vwap_long = price < vwap * 0.995  # Below VWAP
            vwap_short = price > vwap * 1.005  # Above VWAP

            # Count agreement
            long_signals = sum([rsi_long, ema_long, vol_confirm, vwap_long])
            short_signals = sum([rsi_short, ema_short, vol_confirm, vwap_short])

            # Need 3+ signals agreeing + regime filter
            if long_signals >= 3 and market_regime != "bear":
                conf = min(0.88, 0.55 + long_signals * 0.08)
                reason = (f"Confluence LONG: RSI={rsi:.0f}{'<35' if rsi_long else ''} "
                          f"EMA9{'>' if ema_long else '<'}EMA21 "
                          f"Vol={'above' if vol_confirm else 'below'}avg "
                          f"VWAP={'below' if vwap_long else 'above'} ({long_signals}/4 regime={market_regime})")
                picks.append(_make_pick(sym, "LONG", price, 0.012, 0.010, conf,
                                        "technical_confluence_3plus", reason))
            elif short_signals >= 3 and market_regime != "bull":
                conf = min(0.88, 0.55 + short_signals * 0.08)
                reason = (f"Confluence SHORT: RSI={rsi:.0f}{'> 65' if rsi_short else ''} "
                          f"EMA9{'<' if ema_short else '>'}EMA21 "
                          f"Vol={'above' if vol_confirm else 'below'}avg "
                          f"VWAP={'above' if vwap_short else 'below'} ({short_signals}/4 signals)")
                picks.append(_make_pick(sym, "SHORT", price, 0.012, 0.010, conf,
                                        "technical_confluence_3plus", reason))
        except Exception:
            continue

    return picks[:MAX_POSITIONS]


# ─── Portfolio D: Funding Rate Contrarian ─────────────────────────────

def _fetch_funding_rate(symbol: str) -> float:
    """Fetch current funding rate from Binance Futures."""
    # Futures API uses fapi subdomain, not the spot API mirrors
    futures_urls = [
        "https://fapi.binance.com",
        "https://fapi.binance.com",
    ]
    for base in futures_urls + BINANCE_MIRRORS:
        try:
            url = f"{base}/fapi/v1/fundingRate?symbol={symbol}&limit=1"
            data = _fetch_json(url, timeout=8)
            if data:
                return float(data[-1].get("fundingRate", 0))
        except Exception:
            continue
    # Fallback: try premium index for mark price funding
    for base in futures_urls:
        try:
            url = f"{base}/fapi/v1/premiumIndex?symbol={symbol}"
            data = _fetch_json(url, timeout=8)
            if data:
                return float(data.get("lastFundingRate", 0))
        except Exception:
            continue
    return 0.0


def _fetch_open_interest(symbol: str) -> float:
    """Fetch open interest from Binance Futures."""
    for mirror in BINANCE_MIRRORS:
        try:
            url = f"{mirror}/fapi/v1/openInterest?symbol={symbol}"
            data = _fetch_json(url, timeout=8)
            return float(data.get("openInterest", 0))
        except Exception:
            continue
    return 0.0


def generate_funding_picks() -> list:
    """Portfolio D: Fade extreme funding rates.

    When funding is very positive (longs paying shorts), the market is
    overleveraged long — fade it (SHORT).
    When funding is very negative (shorts paying longs), the market is
    overleveraged short — fade it (LONG).
    """
    picks = []

    for sym in SYMBOLS[:7]:  # Top 7 by liquidity
        try:
            fr = _fetch_funding_rate(sym)
            price = _fetch_price(sym)
            if price <= 0:
                continue

            # LESSON 5: Weak signals produce weak results. Need genuinely extreme funding.
            # Baseline: 0.01% (0.0001). Only trade when funding is 2x+ baseline.
            if abs(fr) < 0.00008:  # Below 0.008% — lowered from 0.02% to actually generate picks
                continue

            if fr > 0.0002:
                # Positive funding = longs overleveraged = SHORT
                direction = "SHORT"
                confidence = min(0.85, 0.55 + abs(fr) * 500)
                reason = f"Funding contrarian: rate={fr*100:.4f}% (longs paying). Fading overleveraged longs."
            elif fr < -0.0002:
                # Negative funding = shorts overleveraged = LONG
                direction = "LONG"
                confidence = min(0.85, 0.55 + abs(fr) * 500)
            else:
                continue
                reason = f"Funding contrarian: rate={fr*100:.4f}% (shorts paying). Fading overleveraged shorts."

            # Tighter TP/SL for funding trades (mean-reversion)
            picks.append(_make_pick(sym, direction, price, 0.010, 0.008, confidence,
                                    "funding_rate_contrarian", reason))
        except Exception:
            continue

    return picks[:MAX_POSITIONS]


# ─── Portfolio Manager ────────────────────────────────────────────────

def _load_portfolios() -> dict:
    template = {
        "virtual_capital": VIRTUAL_CAPITAL,
        "cash": VIRTUAL_CAPITAL,
        "active_positions": [],
        "closed_positions": [],
        "stats": {
            "total_trades": 0, "wins": 0, "losses": 0,
            "total_pnl_pct": 0.0, "win_rate": 0.0,
            "peak_equity": VIRTUAL_CAPITAL, "max_drawdown_pct": 0.0,
            "current_equity": VIRTUAL_CAPITAL, "total_profit": 0.0,
        },
    }

    ALL_PORTFOLIO_KEYS = [
        "B_news_sentiment",
        "C_technical_confluence",
        "D_funding_contrarian",
        "E_multi_asset_proven",
        "F_night_streak_shorts",
        "G_equity_mean_reversion",
        "H_forex_carry_reversion",
        "I_futures_commodity_momentum",
        "J_etf_rotation",
        "F_momentum_continuation",
        "G_atr_compression_breakout",
    ]

    if PORTFOLIOS_FILE.exists():
        data = json.loads(PORTFOLIOS_FILE.read_text(encoding="utf-8"))
        # Back-fill any portfolio keys added after the file was first created
        portfolios = data.setdefault("portfolios", {})
        for key in ALL_PORTFOLIO_KEYS:
            if key not in portfolios:
                portfolios[key] = json.loads(json.dumps(template))
                print(f"  [init] Back-filled new portfolio: {key}")
        return data

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "portfolios": {
            key: json.loads(json.dumps(template)) for key in ALL_PORTFOLIO_KEYS
        },
    }


def _check_positions(portfolio: dict) -> tuple:
    """Check TP/SL hits for a portfolio's active positions."""
    still_open, closed = [], []

    for pos in portfolio.get("active_positions", []):
        symbol = pos.get("symbol", "")
        live = _fetch_price(symbol)
        if live <= 0:
            still_open.append(pos)
            continue

        entry = pos.get("entry_price", 0)
        tp = pos.get("take_profit", 0)
        sl = pos.get("stop_loss", 0)
        direction = pos.get("direction", "LONG").upper()

        hit_tp = hit_sl = False
        if direction == "LONG":
            if tp > 0 and live >= tp: hit_tp = True
            if sl > 0 and live <= sl: hit_sl = True
            pnl = (live - entry) / entry * 100 if entry > 0 else 0
        else:
            if tp > 0 and live <= tp: hit_tp = True
            if sl > 0 and live >= sl: hit_sl = True
            pnl = (entry - live) / entry * 100 if entry > 0 else 0

        pos["live_price"] = live
        pos["unrealized_pnl_pct"] = round(pnl, 3)

        if hit_tp or hit_sl:
            pos["status"] = "TP_HIT" if hit_tp else "SL_HIT"
            pos["exit_price"] = live
            pos["realized_pnl_pct"] = round(pnl, 3)
            pos["closed_at"] = datetime.now(timezone.utc).isoformat()
            pos["profit"] = round(pos.get("position_value", 500) * pnl / 100, 2)
            closed.append(pos)
        else:
            still_open.append(pos)

    return still_open, closed


def _update_stats(portfolio: dict) -> None:
    closed = portfolio.get("closed_positions", [])
    s = portfolio["stats"]
    s["total_trades"] = len(closed)
    s["wins"] = sum(1 for p in closed if (p.get("realized_pnl_pct", 0) or 0) > 0)
    s["losses"] = len(closed) - s["wins"]
    s["win_rate"] = round(s["wins"] / max(len(closed), 1) * 100, 1)
    s["total_pnl_pct"] = round(sum(p.get("realized_pnl_pct", 0) for p in closed), 2)
    profit = sum(p.get("profit", 0) for p in closed)
    unrealized = sum(pos.get("position_value", 500) * (pos.get("unrealized_pnl_pct", 0) / 100)
                     for pos in portfolio.get("active_positions", []))
    eq = VIRTUAL_CAPITAL + profit + unrealized
    s["current_equity"] = round(eq, 2)
    s["total_profit"] = round(profit, 2)
    if eq > s.get("peak_equity", VIRTUAL_CAPITAL):
        s["peak_equity"] = round(eq, 2)
    peak = s.get("peak_equity", VIRTUAL_CAPITAL)
    dd = (peak - eq) / peak * 100 if peak > 0 else 0
    if dd > s.get("max_drawdown_pct", 0):
        s["max_drawdown_pct"] = round(dd, 2)


# ─── Portfolio E: Multi-Asset Proven ──────────────────────────────────

# The 5 best strategies with REAL closed trade data across asset classes:
# 1. Keltner (crypto) — 75-77% WR, 52+ trades, walk-forward ROBUST
# 2. Bollinger MR (equity) — 80% WR on 10 closed equity trades
# 3. RSI Divergence (equity) — 100% WR on 3 equity trades
# 4. VWAP Reversion (crypto) — 80% WR on 10 SOL trades
# 5. Consensus alpha+ml (crypto) — 56% WR on 87 trades, +54% PnL

MULTI_ASSET_EQUITY_SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM"]
MULTI_ASSET_FOREX_PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]


def generate_multi_asset_picks() -> list:
    """Portfolio E: Multi-asset using top proven strategies across classes.

    Crypto: Keltner + VWAP Reversion (proven 75-80% WR)
    Equity: Bollinger MR (80% WR on closed trades)
    Uses the same technical logic but adapted per asset class.
    """
    picks = []

    # Crypto: Keltner-style compression breakout on top 5 symbols
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]:
        try:
            klines = _fetch_klines(sym, "4h", 50)
            if len(klines) < 40:
                continue
            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            if price <= 0:
                continue

            # Keltner: EMA(20) +/- ATR(14)*1.5
            ema20 = _compute_ema(closes, 20)
            # Compute ATR
            trs = []
            for i in range(1, len(klines)):
                h, l, c_prev = float(klines[i][2]), float(klines[i][3]), float(klines[i-1][4])
                trs.append(max(h-l, abs(h-c_prev), abs(l-c_prev)))
            atr = sum(trs[-14:]) / 14 if len(trs) >= 14 else 0

            if atr <= 0:
                continue

            upper = ema20 + atr * 1.5
            lower = ema20 - atr * 1.5

            # Price breaking out of Keltner channel
            if price > upper:
                picks.append(_make_pick(sym, "LONG", price, 0.012, 0.010, 0.75,
                    "multi_asset_keltner_breakout",
                    f"Keltner breakout LONG: price {price:.2f} > upper {upper:.2f}. ATR={atr:.2f}"))
            elif price < lower:
                picks.append(_make_pick(sym, "SHORT", price, 0.012, 0.010, 0.75,
                    "multi_asset_keltner_breakout",
                    f"Keltner breakout SHORT: price {price:.2f} < lower {lower:.2f}. ATR={atr:.2f}"))
        except Exception:
            continue

    # Crypto: VWAP reversion (proven 80% WR on SOL)
    for sym in ["SOLUSDT", "ETHUSDT", "BTCUSDT"]:
        try:
            klines = _fetch_klines(sym, "1h", 24)
            if len(klines) < 12:
                continue
            vwap = _compute_vwap(klines)
            price = float(klines[-1][4])
            if price <= 0 or vwap <= 0:
                continue
            dev = (price - vwap) / vwap
            if dev < -0.012:
                picks.append(_make_pick(sym, "LONG", price, 0.010, 0.008, 0.72,
                    "multi_asset_vwap_reversion",
                    f"VWAP reversion LONG: {dev*100:.2f}% below VWAP {vwap:.2f}"))
            elif dev > 0.012:
                picks.append(_make_pick(sym, "SHORT", price, 0.010, 0.008, 0.72,
                    "multi_asset_vwap_reversion",
                    f"VWAP reversion SHORT: {dev*100:.2f}% above VWAP {vwap:.2f}"))
        except Exception:
            continue

    # Deduplicate by symbol (keep highest confidence)
    seen = {}
    for p in picks:
        key = p["symbol"]
        if key not in seen or p["confidence"] > seen[key]["confidence"]:
            seen[key] = p

    return list(seen.values())[:MAX_POSITIONS]


# ─── Portfolio G: Equity Mean Reversion (Bollinger + RSI) ────────────

# Equity symbols — based on closed pick analysis (81% WR, +80.4% PnL)
# Winners: META (3W/0L +16.9%), GOOGL, TSLA, AAPL, NFLX — tech/growth
# Losers: XLE (0W/2L), CVX (0W/1L), XOM (0W/1L) — energy BLOCKED
EQUITY_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "TSLA", "NFLX", "IONQ"]
EQUITY_BLOCKED = {"XLE", "CVX", "XOM"}  # Energy stocks: 0W/4L, -18.8% combined
EQUITY_TP_PCT = 0.03   # +3% take profit
EQUITY_SL_PCT = 0.02   # -2% stop loss  (R:R = 1.5, proven sweet spot)


def _compute_bollinger(closes: list, period: int = 20, num_std: float = 2.0) -> tuple:
    """Compute Bollinger Bands (middle, upper, lower)."""
    if len(closes) < period:
        mid = sum(closes) / len(closes) if closes else 0
        return mid, mid, mid
    window = closes[-period:]
    mid = sum(window) / period
    variance = sum((c - mid) ** 2 for c in window) / period
    std = variance ** 0.5
    return mid, mid + num_std * std, mid - num_std * std


def _fetch_equity_data(symbol: str) -> list:
    """Fetch daily closing prices for an equity symbol via yfinance.

    Returns list of floats (closing prices, oldest first) or empty list on failure.
    """
    try:
        import yfinance as yf
    except ImportError:
        print(f"    [equity_mr] yfinance not installed -- skipping {symbol}")
        return []

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="60d", interval="1d")
        if hist is None or hist.empty:
            return []
        return hist["Close"].dropna().tolist()
    except Exception as e:
        print(f"    [equity_mr] Failed to fetch {symbol}: {e}")
        return []


def generate_equity_mean_reversion_picks() -> list:
    """Portfolio G: Equity Bollinger Band + RSI mean-reversion.

    Based on real data: Bollinger MR is the best non-crypto strategy
    (80% WR on 10 closed trades, +39.93% PnL).

    Rules:
    - LONG when RSI(14) < 35 AND price < lower Bollinger Band (oversold + below band)
    - SHORT when RSI(14) > 65 AND price > upper Bollinger Band (overbought + above band)
    - TP: +3% / SL: -2% (tight R:R < 1.5 sweet spot)
    - Only trade Tue-Fri (skip Mon/Sun per historical data)
    """
    now = datetime.now(timezone.utc)

    # Gate: Only trade Tue(1) through Fri(4) -- skip Mon(0), Sat(5), Sun(6)
    if now.weekday() not in (1, 2, 3, 4):
        return []

    picks = []

    for sym in EQUITY_SYMBOLS:
        if sym in EQUITY_BLOCKED:
            continue  # Energy stocks: 0W/4L, -18.8% — blocked
        closes = _fetch_equity_data(sym)
        if len(closes) < 30:
            continue

        price = closes[-1]
        if price <= 0:
            continue

        rsi = _compute_rsi(closes, 14)
        _mid, upper, lower = _compute_bollinger(closes, 20, 2.0)

        # LONG: oversold + below lower band = highest conviction
        if rsi < 35 and price < lower:
            confidence = min(0.88, 0.70 + (35 - rsi) * 0.005 + (lower - price) / price * 5)
            reason = (f"Equity MR LONG: {sym} RSI={rsi:.1f}<35 + "
                      f"price ${price:.2f} < lower BB ${lower:.2f}. "
                      f"Full oversold + below band signal.")
            picks.append(_make_pick(sym, "LONG", price, EQUITY_TP_PCT, EQUITY_SL_PCT,
                                    confidence, "equity_bollinger_mean_reversion", reason))

        # LONG: RSI very oversold even if not below BB (relaxed entry)
        elif rsi < 30:
            confidence = min(0.78, 0.60 + (30 - rsi) * 0.008)
            reason = (f"Equity MR LONG: {sym} RSI={rsi:.1f}<30 (deeply oversold). "
                      f"Price ${price:.2f}, BB lower ${lower:.2f}.")
            picks.append(_make_pick(sym, "LONG", price, EQUITY_TP_PCT, EQUITY_SL_PCT,
                                    confidence, "equity_rsi_oversold", reason))

        # SHORT: overbought + above upper band
        elif rsi > 65 and price > upper:
            confidence = min(0.88, 0.70 + (rsi - 65) * 0.005 + (price - upper) / price * 5)
            reason = (f"Equity MR SHORT: {sym} RSI={rsi:.1f}>65 + "
                      f"price ${price:.2f} > upper BB ${upper:.2f}.")
            picks.append(_make_pick(sym, "SHORT", price, EQUITY_TP_PCT, EQUITY_SL_PCT,
                                    confidence, "equity_bollinger_mean_reversion", reason))

        # SHORT: RSI very overbought even if not above BB
        elif rsi > 70:
            confidence = min(0.78, 0.60 + (rsi - 70) * 0.008)
            reason = (f"Equity MR SHORT: {sym} RSI={rsi:.1f}>70 (overbought). "
                      f"Price ${price:.2f}, BB upper ${upper:.2f}.")
            picks.append(_make_pick(sym, "SHORT", price, EQUITY_TP_PCT, EQUITY_SL_PCT,
                                    confidence, "equity_rsi_overbought", reason))

    # Sort by confidence descending
    picks.sort(key=lambda p: p["confidence"], reverse=True)
    return picks[:MAX_POSITIONS]


# ─── Portfolio F: Night Shorts + Streak Filter ──────────────────────

# Statistical edge from 2,000 closed picks analysis:
# - Night session 01-05 UTC: 61.1% WR (vs 41.2% rest of day)
# - Crypto SHORTs with Score>=50: 72.5% WR
# - Autocorrelation +0.273: after 2 consecutive wins, next pick more likely to win
# - Thursday best (61.9% WR), Sunday worst (32.8%)

NIGHT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                 "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT"]

NIGHT_SESSION_START = 0   # UTC hour (widened: was 1, missed hour 0 runs)
NIGHT_SESSION_END = 6     # UTC hour (exclusive: trades 00:00-05:59)
NIGHT_TP_PCT = 0.025      # 2.5% take profit
NIGHT_SL_PCT = 0.015      # 1.5% stop loss  (R:R = 1.67)
NIGHT_BASE_CONFIDENCE = 0.60
NIGHT_STREAK_THRESHOLD = 2  # consecutive wins before loosening entry


def _get_streak_count(portfolio: dict) -> int:
    """Count consecutive wins from the most recent closed positions."""
    closed = portfolio.get("closed_positions", [])
    if not closed:
        return 0
    streak = 0
    for pos in reversed(closed):
        if (pos.get("realized_pnl_pct", 0) or 0) > 0:
            streak += 1
        else:
            break
    return streak


def generate_night_streak_picks() -> list:
    """Portfolio F: Night session SHORT-only with streak-based confidence.

    Only generates picks during 01-05 UTC (the proven 61.1% WR window).
    Only takes SHORT direction (72.5% WR for crypto shorts with score>=50).
    After 2+ consecutive wins, loosens RSI entry threshold (autocorrelation edge).
    Avoids Sunday (worst day at 32.8% WR).
    """
    now = datetime.now(timezone.utc)

    # Gate 1: Only trade during 01-05 UTC night session
    if not (NIGHT_SESSION_START <= now.hour < NIGHT_SESSION_END):
        return []

    # Gate 2: Skip Sunday (weekday 6) — worst day at 32.8% WR
    if now.weekday() == 6:
        return []

    # Load portfolio to check streak
    data = _load_portfolios()
    port = data.get("portfolios", {}).get("F_night_streak_shorts", {})
    streak = _get_streak_count(port)
    streak_active = streak >= NIGHT_STREAK_THRESHOLD

    # Loosen RSI threshold when on a winning streak (autocorrelation edge)
    rsi_threshold = 52 if streak_active else 55

    # Boost confidence on Thursday (best day at 61.9% WR)
    thursday_bonus = 0.05 if now.weekday() == 3 else 0.0

    picks = []

    for sym in NIGHT_SYMBOLS:
        try:
            klines = _fetch_klines(sym, "1h", 50)
            if len(klines) < 30:
                continue

            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            if price <= 0:
                continue

            # Signal 1: RSI > threshold (neutral-high, not overbought)
            rsi = _compute_rsi(closes, 14)
            if rsi <= rsi_threshold:
                continue

            # Signal 2: EMA9 < EMA21 (downtrend confirmation)
            ema9 = _compute_ema(closes, 9)
            ema21 = _compute_ema(closes, 21)
            if ema9 >= ema21:
                continue

            # Both signals confirmed — generate SHORT pick
            confidence = NIGHT_BASE_CONFIDENCE + thursday_bonus
            if streak_active:
                confidence += 0.05  # Streak bonus
            confidence = min(confidence, 0.88)

            streak_note = f" Streak={streak} (loosened entry)." if streak_active else ""
            thursday_note = " Thursday bonus." if thursday_bonus > 0 else ""
            reason = (f"Night SHORT {now.hour:02d}UTC: RSI={rsi:.1f}>{rsi_threshold} "
                      f"EMA9({ema9:.2f})<EMA21({ema21:.2f}).{streak_note}{thursday_note}")

            picks.append(_make_pick(
                sym, "SHORT", price,
                NIGHT_TP_PCT, NIGHT_SL_PCT,
                confidence, "night_streak_short",
                reason,
            ))
        except Exception:
            continue

    # Sort by confidence descending, take top positions
    picks.sort(key=lambda p: p["confidence"], reverse=True)
    return picks[:MAX_POSITIONS]


# ─── Portfolio H: Forex Carry + Mean Reversion ────────────────────────

FOREX_PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]


def generate_forex_picks() -> list:
    """Portfolio H: Forex RSI mean-reversion using yfinance.

    Proven approach: FX is mean-reverting around equilibrium.
    Enter when RSI extreme (< 30 LONG, > 70 SHORT) on daily data.
    """
    picks = []
    for pair in FOREX_PAIRS:
        closes = _fetch_equity_data(pair)  # yfinance works for forex =X pairs
        if len(closes) < 20:
            continue
        price = closes[-1]
        if price <= 0:
            continue
        rsi = _compute_rsi(closes, 14)

        if rsi < 30:
            picks.append(_make_pick(pair, "LONG", price, 0.008, 0.005, 0.70,
                "forex_rsi_mean_reversion",
                f"Forex MR LONG: {pair} RSI={rsi:.1f}<30 (oversold). Mean-revert."))
        elif rsi > 70:
            picks.append(_make_pick(pair, "SHORT", price, 0.008, 0.005, 0.70,
                "forex_rsi_mean_reversion",
                f"Forex MR SHORT: {pair} RSI={rsi:.1f}>70 (overbought). Mean-revert."))
        elif rsi < 35:
            picks.append(_make_pick(pair, "LONG", price, 0.006, 0.004, 0.60,
                "forex_rsi_mild_oversold",
                f"Forex LONG: {pair} RSI={rsi:.1f}<35 (mildly oversold)."))
        elif rsi > 65:
            picks.append(_make_pick(pair, "SHORT", price, 0.006, 0.004, 0.60,
                "forex_rsi_mild_overbought",
                f"Forex SHORT: {pair} RSI={rsi:.1f}>65 (mildly overbought)."))
    return picks[:MAX_POSITIONS]


# ─── Portfolio I: Futures/Commodity Momentum ───────────────────────────

FUTURES_SYMBOLS = ["GC=F", "SI=F", "CL=F", "NG=F", "ZC=F"]  # Gold, Silver, Oil, Gas, Corn


def generate_futures_picks() -> list:
    """Portfolio I: Futures momentum using yfinance.

    Commodities have strong trend-following characteristics.
    Enter when EMA(9) > EMA(21) for LONG, reversed for SHORT.
    """
    picks = []
    for sym in FUTURES_SYMBOLS:
        closes = _fetch_equity_data(sym)
        if len(closes) < 25:
            continue
        price = closes[-1]
        if price <= 0:
            continue
        ema9 = _compute_ema(closes, 9)
        ema21 = _compute_ema(closes, 21)
        rsi = _compute_rsi(closes, 14)

        if ema9 > ema21 and rsi < 70:
            picks.append(_make_pick(sym, "LONG", price, 0.015, 0.010, 0.68,
                "futures_ema_momentum",
                f"Futures LONG: {sym} EMA9>{ema21:.2f} trend up, RSI={rsi:.0f}."))
        elif ema9 < ema21 and rsi > 30:
            picks.append(_make_pick(sym, "SHORT", price, 0.015, 0.010, 0.68,
                "futures_ema_momentum",
                f"Futures SHORT: {sym} EMA9<{ema21:.2f} trend down, RSI={rsi:.0f}."))
    return picks[:MAX_POSITIONS]


# ─── Portfolio J: ETF Rotation ─────────────────────────────────────────

ETF_SYMBOLS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "XLE"]


def generate_etf_picks() -> list:
    """Portfolio J: ETF rotation — buy strongest momentum, short weakest.

    Simple relative-strength approach across sector ETFs.
    """
    scores = []
    for sym in ETF_SYMBOLS:
        closes = _fetch_equity_data(sym)
        if len(closes) < 25:
            continue
        price = closes[-1]
        if price <= 0:
            continue
        ret_20d = (closes[-1] / closes[-21] - 1) if len(closes) > 21 else 0
        rsi = _compute_rsi(closes, 14)
        scores.append((sym, price, ret_20d, rsi))

    if len(scores) < 3:
        return []

    scores.sort(key=lambda x: x[2], reverse=True)
    picks = []

    # LONG the strongest
    best = scores[0]
    if best[2] > 0:
        picks.append(_make_pick(best[0], "LONG", best[1], 0.020, 0.012, 0.72,
            "etf_momentum_rotation",
            f"ETF Rotation LONG: {best[0]} best 20d return {best[2]*100:.1f}%, RSI={best[3]:.0f}."))

    # SHORT the weakest
    worst = scores[-1]
    if worst[2] < 0:
        picks.append(_make_pick(worst[0], "SHORT", worst[1], 0.020, 0.012, 0.72,
            "etf_momentum_rotation",
            f"ETF Rotation SHORT: {worst[0]} worst 20d return {worst[2]*100:.1f}%, RSI={worst[3]:.0f}."))

    return picks[:MAX_POSITIONS]


# ─── Portfolio F_momentum_continuation: Momentum Continuation ────────

def generate_momentum_continuation_picks() -> list:
    """Portfolio F: Momentum Continuation — catches pre-pump setups.
    Based on gainer analysis: 17/18 top gainers had RSI 35-60, ATR<3%, EMA9>EMA21.
    """
    picks = []
    for sym in SYMBOLS:
        try:
            klines = _fetch_klines(sym, "1h", 50)
            if len(klines) < 30:
                continue
            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            price = closes[-1]
            if price <= 0:
                continue

            rsi = _compute_rsi(closes, 14)
            ema9 = _compute_ema(closes, 9)
            ema21 = _compute_ema(closes, 21)
            atr = _fetch_atr(sym, 14)
            atr_pct = (atr / price * 100) if price > 0 and atr > 0 else 999

            # Volume increasing: last 6h avg > prior 12h avg
            recent_vol = volumes[-6:] if len(volumes) >= 6 else volumes
            prior_vol = volumes[-18:-6] if len(volumes) >= 18 else volumes[:len(volumes)//2]
            avg_recent = sum(recent_vol) / len(recent_vol) if recent_vol else 0
            avg_prior = sum(prior_vol) / len(prior_vol) if prior_vol else 1
            vol_increasing = avg_recent > avg_prior * 1.1  # 10% volume increase

            # Bollinger position
            mid, upper, lower = _compute_bollinger(closes, 20, 2.0)
            bb_position = (price - lower) / (upper - lower) if upper != lower else 0.5

            # LONG signal: momentum continuation setup
            if (35 <= rsi <= 60
                    and ema9 > ema21
                    and atr_pct < 3.0
                    and vol_increasing
                    and bb_position > 0.5):
                # Confidence based on how many factors align
                conf = 0.60
                if rsi >= 45:
                    conf += 0.05
                if atr_pct < 2.0:
                    conf += 0.05
                if avg_recent > avg_prior * 1.3:
                    conf += 0.05
                if bb_position > 0.6:
                    conf += 0.05
                conf = min(conf, 0.85)

                # Tight R:R per PEER_INTEL: optimal crypto R:R is 1.0-1.5
                tp_pct = 0.025  # 2.5% TP
                sl_pct = 0.018  # 1.8% SL → R:R ~1.4

                reason = (f"Momentum LONG: RSI={rsi:.0f} (neutral zone), "
                         f"EMA9>EMA21, ATR={atr_pct:.1f}%<3%, "
                         f"Vol+{((avg_recent/avg_prior-1)*100):.0f}%, BB={bb_position:.2f}")
                picks.append(_make_pick(sym, "LONG", price, tp_pct, sl_pct, conf,
                                        "momentum_continuation", reason))

            # SHORT signal: momentum exhaustion (opposite conditions)
            elif (rsi > 70
                    and ema9 < ema21
                    and vol_increasing
                    and bb_position < 0.3):
                conf = 0.65
                tp_pct = 0.020
                sl_pct = 0.015
                reason = (f"Momentum SHORT: RSI={rsi:.0f} (overbought), "
                         f"EMA9<EMA21, Vol+{((avg_recent/avg_prior-1)*100):.0f}%")
                picks.append(_make_pick(sym, "SHORT", price, tp_pct, sl_pct, conf,
                                        "momentum_continuation", reason))
        except Exception:
            continue
    return picks[:MAX_POSITIONS]


# ─── Portfolio G_atr_compression_breakout: ATR Compression Breakout ───

def generate_atr_compression_breakout_picks() -> list:
    """Portfolio G: ATR Compression Breakout — low volatility squeeze before expansion.
    61% of top gainers had ATR < 3% before the move. ADX > 20 confirms trend starting.
    """
    picks = []
    for sym in SYMBOLS:
        try:
            klines = _fetch_klines(sym, "1h", 50)
            if len(klines) < 30:
                continue
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            price = closes[-1]
            if price <= 0:
                continue

            atr = _fetch_atr(sym, 14)
            atr_pct = (atr / price * 100) if price > 0 and atr > 0 else 999
            rsi = _compute_rsi(closes, 14)
            ema9 = _compute_ema(closes, 9)
            ema21 = _compute_ema(closes, 21)
            mid, upper, lower = _compute_bollinger(closes, 20, 2.0)
            bb_width = (upper - lower) / mid * 100 if mid > 0 else 999

            # ADX approximation: use directional movement
            # Simplified: trend strength from EMA slope
            if len(closes) >= 10:
                slope = (closes[-1] - closes[-10]) / closes[-10] * 100
            else:
                slope = 0

            # Volume spike: current > 1.5x 20-period average
            avg_vol_20 = sum(volumes[-20:]) / min(len(volumes), 20) if volumes else 0
            vol_spike = volumes[-1] > avg_vol_20 * 1.5 if avg_vol_20 > 0 else False

            # LONG: ATR compressed + BB squeeze + trend starting up + volume spike
            if (atr_pct < 3.0
                    and bb_width < 4.0
                    and ema9 > ema21
                    and slope > 0.5
                    and (vol_spike or rsi > 50)):
                conf = 0.62
                if atr_pct < 2.0:
                    conf += 0.05
                if vol_spike:
                    conf += 0.08
                if bb_width < 2.5:
                    conf += 0.05
                conf = min(conf, 0.85)

                tp_pct = 0.030  # 3% TP (breakout moves are larger)
                sl_pct = 0.015  # 1.5% SL → R:R 2.0

                reason = (f"Compression LONG: ATR={atr_pct:.1f}%<3%, "
                         f"BB_width={bb_width:.1f}%<4%, slope=+{slope:.1f}%, "
                         f"{'VolSpike ' if vol_spike else ''}RSI={rsi:.0f}")
                picks.append(_make_pick(sym, "LONG", price, tp_pct, sl_pct, conf,
                                        "atr_compression_breakout", reason))

            # SHORT: compression + breakdown
            elif (atr_pct < 3.0
                    and bb_width < 4.0
                    and ema9 < ema21
                    and slope < -0.5
                    and (vol_spike or rsi < 45)):
                conf = 0.62
                if vol_spike:
                    conf += 0.08
                conf = min(conf, 0.85)

                tp_pct = 0.025
                sl_pct = 0.015
                reason = (f"Compression SHORT: ATR={atr_pct:.1f}%<3%, "
                         f"BB_width={bb_width:.1f}%<4%, slope={slope:.1f}%")
                picks.append(_make_pick(sym, "SHORT", price, tp_pct, sl_pct, conf,
                                        "atr_compression_breakout", reason))
        except Exception:
            continue
    return picks[:MAX_POSITIONS]


def run_all_portfolios() -> dict:
    """Main entry — run hourly for all theory portfolios."""
    now = datetime.now(timezone.utc)
    data = _load_portfolios()

    generators = {
        "B_news_sentiment": generate_news_picks,
        "C_technical_confluence": generate_confluence_picks,
        "D_funding_contrarian": generate_funding_picks,
        "E_multi_asset_proven": generate_multi_asset_picks,
        "F_night_streak_shorts": generate_night_streak_picks,
        "G_equity_mean_reversion": generate_equity_mean_reversion_picks,
        "H_forex_carry_reversion": generate_forex_picks,
        "I_futures_commodity_momentum": generate_futures_picks,
        "J_etf_rotation": generate_etf_picks,
        "F_momentum_continuation": generate_momentum_continuation_picks,
        "G_atr_compression_breakout": generate_atr_compression_breakout_picks,
    }

    for name, gen_fn in generators.items():
        port = data["portfolios"][name]

        # 1. Check existing positions
        still_open, newly_closed = _check_positions(port)
        port["active_positions"] = still_open
        port["closed_positions"].extend(newly_closed)

        for c in newly_closed:
            print(f"    [{name}] CLOSED: {c['symbol']} {c['direction']} {c['status']} PnL={c.get('realized_pnl_pct',0):+.2f}%")

        # 2. Generate fresh picks if room
        if len(port["active_positions"]) < MAX_POSITIONS:
            try:
                new_picks = gen_fn()
                # Don't duplicate existing symbols
                existing_syms = {p["symbol"] for p in port["active_positions"]}
                new_picks = [p for p in new_picks if p["symbol"] not in existing_syms]
                # DSR promotion gate check
                new_picks = [p for p in new_picks if _strategy_passes_gate(p.get("strategy", ""))]
                # Correlation gate
                new_picks = [p for p in new_picks if _passes_correlation_gate(p["symbol"], port)]
                room = MAX_POSITIONS - len(port["active_positions"])
                added = new_picks[:room]
                port["active_positions"].extend(added)
                for p in added:
                    print(f"    [{name}] NEW: {p['symbol']} {p['direction']} conf={p['confidence']} — {p['reason'][:60]}")
            except Exception as e:
                print(f"    [{name}] ERROR generating picks: {e}")

        # 3. Update stats
        _update_stats(port)

        s = port["stats"]
        unrealized = s.get("current_equity", VIRTUAL_CAPITAL) - VIRTUAL_CAPITAL - s.get("total_profit", 0)
        unrealized_pct = unrealized / VIRTUAL_CAPITAL * 100 if VIRTUAL_CAPITAL else 0
        tickers = ", ".join(f"{p['symbol']} {p['direction'][0]}" for p in port["active_positions"][:5])
        if len(port["active_positions"]) > 5:
            tickers += f" +{len(port['active_positions'])-5}"
        # Open Record: winning/losing active picks
        ow = sum(1 for p in port["active_positions"] if (p.get("unrealized_pnl_pct", 0) or 0) > 0.05)
        ol = sum(1 for p in port["active_positions"] if (p.get("unrealized_pnl_pct", 0) or 0) < -0.05)
        of = len(port["active_positions"]) - ow - ol
        print(f"  [{name}] Eq:${s['current_equity']:,.2f} ({s['current_equity']-VIRTUAL_CAPITAL:+.2f}) "
              f"Real:{s['total_pnl_pct']:+.2f}% Unreal:{unrealized_pct:+.2f}% "
              f"Open:{ow}W/{ol}L/{of}F Closed:{s.get('wins',0)}W/{s.get('losses',0)}L "
              f"| {tickers or 'no positions'}")

    data["last_updated"] = now.isoformat()
    DATA.mkdir(parents=True, exist_ok=True)
    PORTFOLIOS_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    # Append history
    history = []
    if PORTFOLIOS_HISTORY.exists():
        try:
            history = json.loads(PORTFOLIOS_HISTORY.read_text(encoding="utf-8"))
        except Exception:
            pass
    snap = {"timestamp": now.isoformat()}
    for name, port in data["portfolios"].items():
        snap[name] = {
            "equity": port["stats"]["current_equity"],
            "win_rate": port["stats"]["win_rate"],
            "active": len(port["active_positions"]),
            "closed": port["stats"]["total_trades"],
        }
    history.append(snap)
    if len(history) > 500:
        history = history[-500:]
    PORTFOLIOS_HISTORY.write_text(json.dumps(history, indent=2, default=str), encoding="utf-8")

    return data


if __name__ == "__main__":
    print("=" * 60)
    print("THEORY PORTFOLIOS — Hourly Update")
    print("=" * 60)
    data = run_all_portfolios()
    print("\n=== SUMMARY ===")
    for name, port in data["portfolios"].items():
        s = port["stats"]
        print(f"  {name:30s} Eq=${s['current_equity']:>10,.2f} WR={s['win_rate']:>5.1f}% "
              f"Trades={s['total_trades']:>3d} DD={s['max_drawdown_pct']:.1f}%")
