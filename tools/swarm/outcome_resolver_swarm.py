"""Resolve open swarm picks against live market data.

Reads `audit_dashboard/data/swarm_picks.json`, finds picks where `outcome is
None`, fetches current price for each symbol (yfinance for stocks/ETFs/forex,
TV MCP for crypto perps), checks if TP or SL was hit since `created_at`.

Idempotent — never overwrites resolved outcomes.

Run: `python tools/swarm/outcome_resolver_swarm.py [--dry-run]`

This is a SKELETON. Real implementation needs:
- yfinance high-low fetch since created_at (intraday for short TFs)
- TV MCP integration for crypto perps not on yfinance
- Slippage assumption (per CLAUDE.md performance charter)
- Time-cap exit per timeframe field (e.g., 4H pick = 30d cap, 1M pick = 180d cap)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.swarm.swarm_pick_schema import atomic_write_store, load_store

STORE_PATH = REPO_ROOT / "audit_dashboard" / "data" / "swarm_picks.json"

# Time-cap by timeframe — pick auto-expires if neither TP nor SL hit
TIMEFRAME_CAP_DAYS = {
    "5m": 1, "15m": 2, "30m": 3,
    "1H": 5, "4H": 14, "1D": 30,
    "1W": 90, "1M": 180, "3M": 270, "6M": 540, "1Y": 730,
}


SYMBOL_MAP = {
    # crypto perps -> spot proxies on yfinance
    "BINANCE:BTCUSDT": "BTC-USD", "BINANCE:ETHUSDT": "ETH-USD",
    "BINANCE:SOLUSDT": "SOL-USD", "BINANCE:BNBUSDT": "BNB-USD",
    "BINANCE:XRPUSDT": "XRP-USD", "BINANCE:ADAUSDT": "ADA-USD",
    "BINANCE:DOGEUSDT": "DOGE-USD", "BINANCE:LINKUSDT": "LINK-USD",
    "BINANCE:AVAXUSDT": "AVAX-USD", "BINANCE:ARBUSDT": "ARB-USD",
    "BINANCE:DOTUSDT": "DOT-USD", "BINANCE:INJUSDT": "INJ-USD",
    "BINANCE:TIAUSDT": "TIA-USD", "BINANCE:POLUSDT": "POL-USD",
    "BINANCE:RUNEUSDT": "RUNE-USD", "BINANCE:APTUSDT": "APT-USD",
    "BINANCE:ONDOUSDT": "ONDO-USD",
    "COINBASE:BTCUSDC.P": "BTC-USD", "COINBASE:ETHUSDC.P": "ETH-USD",
    "COINBASE:SOLUSDC.P": "SOL-USD", "COINBASE:DOGEUSDC.P": "DOGE-USD",
    "COINBASE:XRPUSDC.P": "XRP-USD",
    # forex
    "FX:USDJPY": "USDJPY=X", "FX:EURUSD": "EURUSD=X", "FX:GBPUSD": "GBPUSD=X",
    "FX:AUDUSD": "AUDUSD=X", "FX:USDCAD": "USDCAD=X", "FX:AUDJPY": "AUDJPY=X",
    # futures (micros not on yfinance — use full-size proxy)
    "NYMEX:MCL1!": "CL=F", "CME_MINI:MES1!": "ES=F", "CME_MINI:MNQ1!": "NQ=F",
    "COMEX:GC1!": "GC=F", "NYMEX:NG1!": "NG=F",
}


def _resolve_yf_ticker(symbol: str) -> str | None:
    if symbol in SYMBOL_MAP:
        return SYMBOL_MAP[symbol]
    # strip exchange prefix for stocks/ETFs (NYSE:F -> F, NASDAQ:NVDA -> NVDA)
    if ":" in symbol:
        prefix, tail = symbol.split(":", 1)
        if prefix in {"NYSE", "NASDAQ", "AMEX"}:
            return tail
    return None


# Fallback: CoinGecko free API for crypto tickers delisted on yfinance (APT/POL etc.).
# Map TV-style symbol -> CoinGecko coin id (https://api.coingecko.com/api/v3/coins/list).
COINGECKO_MAP = {
    "BINANCE:APTUSDT": "aptos",
    "BINANCE:POLUSDT": "polygon-ecosystem-token",
    "BINANCE:MATICUSDT": "matic-network",
    "BINANCE:TIAUSDT": "celestia",
    "BINANCE:INJUSDT": "injective-protocol",
    "BINANCE:RUNEUSDT": "thorchain",
    "BINANCE:ONDOUSDT": "ondo-finance",
}


def _fetch_yf(ticker: str, since: datetime) -> tuple[float, float] | None:
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        df = yf.Ticker(ticker).history(start=since.date().isoformat(),
                                        interval="1d", auto_adjust=False)
        if df.empty:
            return None
        return float(df["High"].max()), float(df["Low"].min())
    except Exception:
        return None


def _fetch_coingecko(coin_id: str, since: datetime) -> tuple[float, float] | None:
    import urllib.request
    import time
    end = int(time.time())
    start = int(since.timestamp())
    url = (f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
           f"?vs_currency=usd&from={start}&to={end}")
    req = urllib.request.Request(url, headers={
        "User-Agent": "findtorontoevents-swarm-resolver/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        prices = data.get("prices", [])
        if not prices:
            return None
        highs = [p[1] for p in prices]
        return max(highs), min(highs)  # CG free tier: hourly granularity, no OHLC
    except Exception:
        return None


def fetch_high_low(symbol: str, since: datetime) -> tuple[float, float] | None:
    """Fetch (high, low) since `since`. yfinance primary, CoinGecko fallback."""
    ticker = _resolve_yf_ticker(symbol)
    if ticker is not None:
        result = _fetch_yf(ticker, since)
        if result is not None:
            return result
    cg_id = COINGECKO_MAP.get(symbol)
    if cg_id is not None:
        return _fetch_coingecko(cg_id, since)
    return None


def resolve_pick(p: dict, now: datetime) -> dict | None:
    """Returns outcome dict if pick should now have one, else None."""
    if p["outcome"] is not None:
        return None  # already resolved, never overwrite

    created = datetime.fromisoformat(p["created_at"])
    cap_days = TIMEFRAME_CAP_DAYS.get(p["timeframe"], 30)
    cap_time = created + timedelta(days=cap_days)

    high_low = fetch_high_low(p["symbol"], created)
    if high_low is None:
        return None  # can't fetch, skip
    high, low = high_low

    direction = p["direction"]
    entry, tp, sl = float(p["entry"]), float(p["tp"]), float(p["sl"])

    if direction == "LONG":
        if high >= tp:
            return {"exit_reason": "TP_HIT", "exit_price": tp,
                    "exit_time": now.isoformat(),
                    "pnl_pct": (tp / entry - 1) * 100,
                    "pnl_R": (tp - entry) / (entry - sl) if entry > sl else None}
        if low <= sl:
            return {"exit_reason": "SL_HIT", "exit_price": sl,
                    "exit_time": now.isoformat(),
                    "pnl_pct": (sl / entry - 1) * 100,
                    "pnl_R": -1.0}
    else:  # SHORT
        if low <= tp:
            return {"exit_reason": "TP_HIT", "exit_price": tp,
                    "exit_time": now.isoformat(),
                    "pnl_pct": (entry / tp - 1) * 100,
                    "pnl_R": (entry - tp) / (sl - entry) if sl > entry else None}
        if high >= sl:
            return {"exit_reason": "SL_HIT", "exit_price": sl,
                    "exit_time": now.isoformat(),
                    "pnl_pct": (entry / sl - 1) * 100,
                    "pnl_R": -1.0}

    if now >= cap_time:
        return {"exit_reason": "TIME_CAP", "exit_price": None,
                "exit_time": now.isoformat(), "pnl_pct": None, "pnl_R": None}

    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    picks = load_store(STORE_PATH)
    if not picks:
        print("No picks in store.")
        return

    now = datetime.now(timezone.utc)
    open_count = sum(1 for p in picks if p["outcome"] is None)
    resolved_now = 0
    for p in picks:
        out = resolve_pick(p, now)
        if out is not None:
            p["outcome"] = out
            resolved_now += 1

    if args.dry_run:
        print(f"DRY-RUN: would resolve {resolved_now} of {open_count} open picks. No write.")
        return

    if resolved_now > 0:
        atomic_write_store(STORE_PATH, picks)
        print(f"Resolved {resolved_now} of {open_count} open picks.")
    else:
        print(f"No picks resolved. {open_count} still open.")


if __name__ == "__main__":
    main()
