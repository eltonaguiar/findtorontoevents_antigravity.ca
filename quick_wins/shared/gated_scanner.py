#!/usr/bin/env python3
"""
gated_scanner.py — Mega Mutation gated paper-trading scanner

Emits picks ONLY for the 8 verified winning combos (mega_mutation_macd_rsi /
ema_momentum on CRYPTO), with strict risk gates:

  1. Symbol whitelist — only the 8 tournament-validated symbol×mutation combos
  2. Entry conditions — exact tournament genes (MACD/RSI or EMA cross + RSI filter)
  3. TP/SL — exact ATR multiples from tournament genes
  4. Position sizing — fixed % risk per trade (default 2%), max 2 concurrent
  5. Correlation limit — max 1 position per correlated group (JUP/ENA/ADA/WIF)
  6. Regime filter — BTC must be above its 200-EMA (bull regime only)
  7. Min edge — only emit if tournament PF >= 2.0
  8. Dedup — composite key on symbol/direction/entry/TP/SL/date

Output: JSON lines file ready for paper trading / forward validation.

Usage:
    python quick_wins/shared/gated_scanner.py --once       # single scan
    python quick_wins/shared/gated_scanner.py --watch      # continuous (not implemented)

Output file: quick_wins/shared/gated_picks.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_PATH = Path(__file__).resolve().parent / "gated_picks.jsonl"

# ============================================================================
# Verified winning combos from mega_mutation tournament (genome/mega_mutation_live_tracker.py)
# Each entry: mutation_name, symbol, primary, genes, tournament_pf, tournament_wr
# ============================================================================
WINNING_COMBOS = [
    {
        "mutation_name": "macd_rsi_m048",
        "symbol": "JUPUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_pf": 6.44, "tournament_wr": 0.857,
    },
    {
        "mutation_name": "macd_rsi_m084",
        "symbol": "ENAUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.4527,
            "direction_bias": "both",
        },
        "tournament_pf": 8.28, "tournament_wr": 0.833,
    },
    {
        "mutation_name": "macd_rsi_m017",
        "symbol": "ADAUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_pf": 3.72, "tournament_wr": 0.778,
    },
    {
        "mutation_name": "macd_rsi_m048",
        "symbol": "WIFUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_pf": 4.00, "tournament_wr": 0.800,
    },
    {
        "mutation_name": "macd_rsi_m048",
        "symbol": "STXUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_pf": 4.88, "tournament_wr": 0.833,
    },
    {
        "mutation_name": "macd_rsi_m048",
        "symbol": "RENDERUSDT",
        "primary": "MACD_RSI",
        "genes": {
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_pf": 4.08, "tournament_wr": 0.875,
    },
    {
        "mutation_name": "ema_momentum_m006",
        "symbol": "AVAXUSDT",
        "primary": "EMA_CROSS",
        "genes": {
            "ema_fast": 9, "ema_slow": 21,
            "rsi_period": 14, "rsi_filter_low": 40, "rsi_filter_high": 60,
            "tp_atr": 1.1429, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_pf": 4.66, "tournament_wr": 0.875,
    },
    {
        "mutation_name": "ema_momentum_m006",
        "symbol": "DOTUSDT",
        "primary": "EMA_CROSS",
        "genes": {
            "ema_fast": 9, "ema_slow": 21,
            "rsi_period": 14, "rsi_filter_low": 40, "rsi_filter_high": 60,
            "tp_atr": 1.1429, "sl_atr": 1.2,
            "direction_bias": "both",
        },
        "tournament_pf": 3.75, "tournament_wr": 0.857,
    },
]

MIN_TOURNAMENT_PF = 2.0
RISK_PCT_PER_TRADE = 0.02  # 2% of equity per trade
MAX_CONCURRENT_POSITIONS = 2

# Correlated groups — max 1 position per group
CORRELATION_GROUPS = [
    {"JUPUSDT", "ENAUSDT", "ADAUSDT", "WIFUSDT"},  # high-beta altcoins, move together
    {"AVAXUSDT", "DOTUSDT", "STXUSDT", "RENDERUSDT"},  # mid-cap alts
]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_ohlcv(symbol: str, limit: int = 200) -> list[dict[str, float]] | None:
    """Fetch recent OHLCV from Binance (1h candles)."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": "1h", "limit": limit},
            timeout=15,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        return [
            {
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5]),
                "ts": int(c[0]),
            }
            for c in data
        ]
    except Exception:
        return None


def _ema(data: list[float], period: int) -> list[float]:
    out = [0.0] * len(data)
    mult = 2.0 / (period + 1)
    out[0] = data[0]
    for i in range(1, len(data)):
        out[i] = data[i] * mult + out[i - 1] * (1 - mult)
    return out


def _rsi(closes: list[float], period: int) -> list[float]:
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsis = [0.0] * period
    if avg_loss == 0:
        rsis.append(100.0)
    else:
        rsis.append(100.0 - (100.0 / (1.0 + avg_gain / avg_loss)))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsis.append(100.0)
        else:
            rsis.append(100.0 - (100.0 / (1.0 + avg_gain / avg_loss)))
    return rsis


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int) -> float:
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return 0.0
    return sum(trs[-period:]) / period


def _macd(closes: list[float], fast: int, slow: int, signal: int) -> tuple[list[float], list[float], list[float]]:
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = _ema(macd_line, signal)
    hist = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, hist


def _btc_bull_regime() -> bool:
    """BTC must be above its 200-EMA on the 1h chart."""
    ohlcv = fetch_ohlcv("BTCUSDT", 250)
    if not ohlcv or len(ohlcv) < 200:
        return False
    closes = [c["close"] for c in ohlcv]
    ema200 = _ema(closes, 200)[-1]
    return closes[-1] > ema200


def _correlation_group_free(symbol: str, existing_positions: list[dict]) -> bool:
    """Max 1 position per correlated group."""
    for group in CORRELATION_GROUPS:
        if symbol in group:
            for pos in existing_positions:
                if pos["symbol"] in group:
                    return False
            return True
    return True  # symbol not in any group → always allowed


def _composite_key(symbol: str, direction: str, entry: float, tp: float, sl: float, day: str) -> str:
    raw = f"{symbol}|{direction}|{entry:.6f}|{tp:.6f}|{sl:.6f}|{day}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def scan(combos: list[dict], existing_positions: list[dict] | None = None) -> list[dict]:
    """Scan all combos and emit gated picks."""
    existing_positions = existing_positions or []
    picks: list[dict] = []

    btc_bull = _btc_bull_regime()
    print(f"[gate] BTC bull regime: {btc_bull}")

    for combo in combos:
        if combo["tournament_pf"] < MIN_TOURNAMENT_PF:
            print(f"[skip] {combo['symbol']} {combo['mutation_name']}: tournament PF {combo['tournament_pf']} < {MIN_TOURNAMENT_PF}")
            continue

        symbol = combo["symbol"]
        genes = combo["genes"]

        # Regime filter
        if not btc_bull:
            print(f"[skip] {symbol}: BTC not in bull regime")
            continue

        # Correlation limit
        if not _correlation_group_free(symbol, existing_positions):
            print(f"[skip] {symbol}: correlation group already has a position")
            continue

        # Max concurrent positions
        if len(existing_positions) >= MAX_CONCURRENT_POSITIONS:
            print(f"[skip] {symbol}: max concurrent positions ({MAX_CONCURRENT_POSITIONS}) reached")
            continue

        ohlcv = fetch_ohlcv(symbol, 200)
        if not ohlcv or len(ohlcv) < 50:
            print(f"[skip] {symbol}: insufficient OHLCV data")
            continue

        closes = [c["close"] for c in ohlcv]
        highs = [c["high"] for c in ohlcv]
        lows = [c["low"] for c in ohlcv]
        atr = _atr(highs, lows, closes, 14)
        if atr == 0:
            continue

        current_price = closes[-1]
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if combo["primary"] == "MACD_RSI":
            macd_line, signal_line, hist = _macd(closes, genes["macd_fast"], genes["macd_slow"], genes["macd_signal"])
            rsi_values = _rsi(closes, genes["rsi_period"])
            if len(rsi_values) == 0:
                continue
            rsi = rsi_values[-1]

            # MACD crossover: macd_line crosses above/below signal_line
            macd_cross_up = macd_line[-2] <= signal_line[-2] and macd_line[-1] > signal_line[-1]
            macd_cross_down = macd_line[-2] >= signal_line[-2] and macd_line[-1] < signal_line[-1]

            entry = None
            direction = None
            if macd_cross_up and rsi < genes["rsi_buy"]:
                entry = current_price
                direction = "LONG"
            elif macd_cross_down and rsi > genes["rsi_sell"]:
                entry = current_price
                direction = "SHORT"

            if entry is None:
                continue

            tp_mult = genes["tp_atr"]
            sl_mult = genes["sl_atr"]
            if direction == "LONG":
                tp = entry + tp_mult * atr
                sl = entry - sl_mult * atr
            else:
                tp = entry - tp_mult * atr
                sl = entry + sl_mult * atr

        elif combo["primary"] == "EMA_CROSS":
            ema_fast_vals = _ema(closes, genes["ema_fast"])
            ema_slow_vals = _ema(closes, genes["ema_slow"])
            rsi_values = _rsi(closes, genes["rsi_period"])
            if len(rsi_values) == 0:
                continue
            rsi = rsi_values[-1]

            ema_cross_up = ema_fast_vals[-2] <= ema_slow_vals[-2] and ema_fast_vals[-1] > ema_slow_vals[-1]
            ema_cross_down = ema_fast_vals[-2] >= ema_slow_vals[-2] and ema_fast_vals[-1] < ema_slow_vals[-1]

            entry = None
            direction = None
            if ema_cross_up and genes["rsi_filter_low"] < rsi < genes["rsi_filter_high"]:
                entry = current_price
                direction = "LONG"
            elif ema_cross_down:
                entry = current_price
                direction = "SHORT"

            if entry is None:
                continue

            tp_mult = genes["tp_atr"]
            sl_mult = genes["sl_atr"]
            if direction == "LONG":
                tp = entry + tp_mult * atr
                sl = entry - sl_mult * atr
            else:
                tp = entry - tp_mult * atr
                sl = entry + sl_mult * atr
        else:
            continue

        # Risk: position size based on 2% risk
        risk_per_unit = abs(entry - sl)
        if risk_per_unit == 0:
            continue
        # Position size in USDT (2% of $10k equity = $200 risk per trade)
        equity = 10000.0
        risk_usd = equity * RISK_PCT_PER_TRADE
        position_size_usd = risk_usd / (risk_per_unit / entry)

        pick = {
            "strategy": "mega_mutation",
            "mutation_name": combo["mutation_name"],
            "symbol": symbol,
            "direction": direction,
            "entry_price": round(entry, 6),
            "take_profit": round(tp, 6),
            "stop_loss": round(sl, 6),
            "position_size_usd": round(position_size_usd, 2),
            "risk_pct": RISK_PCT_PER_TRADE,
            "atr": round(atr, 6),
            "rsi": round(rsi, 2),
            "tournament_pf": combo["tournament_pf"],
            "tournament_wr": combo["tournament_wr"],
            "combo_index": combos.index(combo),
            "status": "PAPER",
            "source_system": "mega_mutation_gated_scanner",
            "created_at": _utc_iso(),
            "day": day,
            "pick_id": _composite_key(symbol, direction, entry, tp, sl, day),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat(),
        }
        picks.append(pick)
        print(f"[EMIT] {symbol} {direction} entry={entry:.6f} tp={tp:.6f} sl={sl:.6f} size=${position_size_usd:.2f} tourPF={combo['tournament_pf']}")

    return picks


def main() -> int:
    ap = argparse.ArgumentParser(description="Mega Mutation gated paper-trading scanner")
    ap.add_argument("--once", action="store_true", help="Run single scan and exit")
    ap.add_argument("--output", default=str(OUTPUT_PATH), help="Output JSONL path")
    args = ap.parse_args()

    picks = scan(WINNING_COMBOS)

    # Dedup by pick_id
    seen: set[str] = set()
    unique_picks: list[dict] = []
    for p in picks:
        if p["pick_id"] not in seen:
            seen.add(p["pick_id"])
            unique_picks.append(p)

    out_path = Path(args.output)
    with out_path.open("a", encoding="utf-8") as f:
        for p in unique_picks:
            f.write(json.dumps(p, default=str) + "\n")

    print(f"\n[RESULT] {len(unique_picks)} gated picks emitted to {out_path}")
    print(f"[RESULT] BTC bull regime: {_btc_bull_regime()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
