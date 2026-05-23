"""Fetch TradingView technical analysis ratings for tracked symbols."""

try:
    from tradingview_ta import TA_Handler, Interval
    _HAS_TV_TA = True
except ImportError:
    _HAS_TV_TA = False
    print("WARNING: tradingview-ta not installed. Run: pip install tradingview-ta")

from signal_recorder.db import get_db, log_signal

CRYPTO_SYMBOLS = {
    "BTCUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "ETHUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "SOLUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "BNBUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "XRPUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "DOGEUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "ADAUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "AVAXUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "LINKUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "DOTUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "MATICUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "SUIUSDT": {"screener": "crypto", "exchange": "BINANCE"},
}

FOREX_SYMBOLS = {
    "EURUSD": {"screener": "forex", "exchange": "FX_IDC"},
    "GBPUSD": {"screener": "forex", "exchange": "FX_IDC"},
    "USDJPY": {"screener": "forex", "exchange": "FX_IDC"},
    "AUDUSD": {"screener": "forex", "exchange": "FX_IDC"},
}

STOCK_SYMBOLS = {
    "SPY": {"screener": "america", "exchange": "AMEX"},
    "QQQ": {"screener": "america", "exchange": "NASDAQ"},
    "AAPL": {"screener": "america", "exchange": "NASDAQ"},
    "TSLA": {"screener": "america", "exchange": "NASDAQ"},
}

RECOMMENDATION_MAP = {
    "STRONG_BUY":  ("BUY", 0.95),
    "BUY":         ("BUY", 0.70),
    "NEUTRAL":     ("NEUTRAL", 0.50),
    "SELL":        ("SELL", 0.70),
    "STRONG_SELL": ("SELL", 0.95),
}


def fetch_tv_technicals(batch_id=None):
    if not _HAS_TV_TA:
        return {"error": "tradingview-ta not installed"}

    conn = get_db()
    stats = {"symbols_checked": 0, "signals_logged": 0, "errors": []}
    all_symbols = {**CRYPTO_SYMBOLS, **FOREX_SYMBOLS, **STOCK_SYMBOLS}

    # Build timeframes dict inside function (only when library is available)
    timeframes = {
        "1h": Interval.INTERVAL_1_HOUR,
        "4h": Interval.INTERVAL_4_HOURS,
        "1d": Interval.INTERVAL_1_DAY,
        "1w": Interval.INTERVAL_1_WEEK,
    }

    for symbol, info in all_symbols.items():
        for tf_name, tf_interval in timeframes.items():
            try:
                handler = TA_Handler(
                    symbol=symbol,
                    screener=info["screener"],
                    exchange=info["exchange"],
                    interval=tf_interval,
                )
                analysis = handler.get_analysis()
                rec = analysis.summary.get("RECOMMENDATION", "NEUTRAL")
                signal, strength = RECOMMENDATION_MAP.get(rec, ("NEUTRAL", 0.50))

                extra = {
                    "recommendation": rec,
                    "buy_count": analysis.summary.get("BUY", 0),
                    "sell_count": analysis.summary.get("SELL", 0),
                    "neutral_count": analysis.summary.get("NEUTRAL", 0),
                    "rsi": analysis.indicators.get("RSI"),
                    "macd": analysis.indicators.get("MACD.macd"),
                    "ema20": analysis.indicators.get("EMA20"),
                    "sma50": analysis.indicators.get("SMA50"),
                    "close": analysis.indicators.get("close"),
                }
                price = analysis.indicators.get("close")

                db_symbol = symbol if symbol.endswith("USDT") else symbol
                system_id = f"tv_tech_{tf_name}"
                log_signal(
                    conn, system_id=system_id, symbol=db_symbol,
                    signal=signal, strength=strength,
                    price_at_signal=price,
                    extra=extra, batch_id=batch_id,
                )
                stats["signals_logged"] += 1
            except Exception as e:
                stats["errors"].append(f"{symbol}/{tf_name}: {e}")

        stats["symbols_checked"] += 1

    conn.close()
    return stats


if __name__ == "__main__":
    stats = fetch_tv_technicals()
    print(f"Symbols checked: {stats['symbols_checked']}")
    print(f"Signals logged: {stats['signals_logged']}")
    if stats["errors"]:
        print(f"Errors ({len(stats['errors'])}):")
        for e in stats["errors"][:5]:
            print(f"  {e}")
