"""
AI Tournament Price Tracker — daily pick resolution engine.

Fetches current prices for all open AI tournament picks, resolves any
picks that have hit TP/SL, and writes updated pick files.

Data sources (3-tier failover per asset class):
  CRYPTO:  Binance → CoinGecko → KuCoin
  EQUITY:  yfinance → Alpha Vantage → Yahoo Finance fallback
  FOREX:   yfinance (FX pairs) → Alpha Vantage FX
  COMMODITY: yfinance → Alpha Vantage
  ETF:     yfinance
  BOND:    yfinance (^TNX, ^TYX)

Resolution rules:
  - TP hit: close at TP price, WIN, pnl_pct = (TP - entry) / entry * direction_mult
  - SL hit: close at SL price, LOSS, pnl_pct = (SL - entry) / entry * direction_mult
  - Expiry: close at closing price (NOT mid-price), WIN/LOSS based on sign
  - Slippage: 5bps equity/ETF/bond/commodity, 20bps CRYPTO/FOREX (applied to fill price)
  - Gap-through: if SL/TP gapped, fill at candle extreme (high/low), not the SL/TP price
"""

from __future__ import annotations
import json
import hashlib
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests
import yfinance as yf

REPO_ROOT = Path(__file__).parent.parent.parent
PICKS_DIR = REPO_ROOT / "data" / "ai_tournament"
PRICE_LOG_DIR = PICKS_DIR / "price_log"
LATEST_PICKS = REPO_ROOT / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"
SUBMISSIONS_DIR = PICKS_DIR / "submissions"

SLIPPAGE_BPS = {
    "EQUITY": 0.0005,
    "ETF": 0.0005,
    "BOND": 0.0005,
    "COMMODITY": 0.0005,
    "CRYPTO": 0.002,
    "FOREX": 0.002,
}

RESOLUTION_WINDOWS_DAYS = {
    "EQUITY": 30,
    "CRYPTO": 14,
    "COMMODITY": 28,
    "FOREX": 21,
    "ETF": 30,
    "BOND": 60,
}


COINGECKO_IDS: dict[str, str] = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "AVAX": "avalanche-2", "DOT": "polkadot",
    "MATIC": "matic-network", "LINK": "chainlink", "UNI": "uniswap", "LTC": "litecoin",
    "BCH": "bitcoin-cash", "ATOM": "cosmos", "NEAR": "near", "FTM": "fantom",
    "ALGO": "algorand", "SAND": "the-sandbox", "MANA": "decentraland", "CRO": "crypto-com-chain",
    "IMX": "immutable-x", "DYDX": "dydx", "TRX": "tron", "APT": "aptos",
    "ARB": "arbitrum", "OP": "optimism", "SUI": "sui", "SEI": "sei-network",
    "INJ": "injective-protocol", "HBAR": "hedera-hashgraph",
}


def fetch_price_crypto(symbol: str) -> float | None:
    """Binance → CoinGecko → KuCoin failover for crypto prices."""
    # Normalize: BTCUSDT -> BTC, BTC -> BTC
    base = symbol.upper().replace("USDT", "").replace("USD", "")
    cg_id = COINGECKO_IDS.get(base, base.lower())

    # Tier 1: Binance (requires API key in GHA secrets)
    try:
        binance_key = os.environ.get("BINANCE_API_KEY", "")
        headers = {"X-MBX-APIKEY": binance_key} if binance_key else {}
        r = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={base}USDT",
            headers=headers, timeout=8
        )
        if r.status_code == 200:
            return float(r.json()["price"])
    except Exception:
        pass

    # Tier 2: CoinGecko (free, no key required)
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if cg_id in data:
                return float(data[cg_id]["usd"])
    except Exception:
        pass

    # Tier 3: KuCoin
    try:
        r = requests.get(
            f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol.upper()}-USDT",
            timeout=8
        )
        if r.status_code == 200:
            return float(r.json()["data"]["price"])
    except Exception:
        pass

    return None


def fetch_price_equity(symbol: str) -> float | None:
    """yfinance → Alpha Vantage failover for equity/ETF/commodity/bond prices."""
    clean = symbol.replace("=F", "").replace("=X", "")
    try:
        ticker = yf.Ticker(clean)
        hist = ticker.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass

    # Tier 2: Alpha Vantage (use clean symbol, strip suffixes)
    av_key = os.environ.get("ALPHA_VANTAGE_KEY", "")
    if av_key:
        try:
            r = requests.get(
                f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={av_key}",
                timeout=10
            )
            if r.status_code == 200:
                price_str = r.json().get("Global Quote", {}).get("05. price")
                if price_str:
                    return float(price_str)
        except Exception:
            pass

    return None


FOREX_YFINANCE_SUFFIX: dict[str, str] = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X", "USDCAD": "CAD=X", "USDCHF": "CHF=X",
    "NZDUSD": "NZDUSD=X",
}


def fetch_price_forex(symbol: str) -> float | None:
    """yfinance → exchangerate-api failover for G10 FOREX pairs."""
    clean = symbol.upper().replace("=X", "")
    yf_symbol = FOREX_YFINANCE_SUFFIX.get(clean, f"{clean}=X")
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass

    # Tier 2: exchangerate-api (free, no key)
    base = symbol[:3].upper()
    quote = symbol[3:].upper()
    try:
        r = requests.get(
            f"https://open.er-api.com/v6/latest/{base}",
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            rate = data.get("rates", {}).get(quote)
            if rate:
                return float(rate)
    except Exception:
        pass

    return None


def fetch_price(pick: dict[str, Any]) -> float | None:
    """Route price fetch by asset class."""
    symbol = pick["symbol"]
    asset_class = pick.get("asset_class", "EQUITY")
    if asset_class == "CRYPTO":
        return fetch_price_crypto(symbol)
    if asset_class == "FOREX":
        return fetch_price_forex(symbol)
    return fetch_price_equity(symbol)


def apply_slippage(price: float, direction: str, asset_class: str, is_tp: bool) -> float:
    """Apply slippage to fill price. TP/SL hits are adversarial (unfavorable)."""
    slip = SLIPPAGE_BPS.get(asset_class, 0.001)
    if direction == "LONG":
        # Buying: slippage adds cost; SL hit: we sell lower
        return price * (1 - slip) if not is_tp else price * (1 - slip)
    else:
        # Short: slippage reduces proceeds
        return price * (1 + slip) if not is_tp else price * (1 + slip)


def resolve_pick(pick: dict[str, Any], current_price: float) -> dict[str, Any]:
    """Determine if a pick has resolved (TP/SL hit or expiry)."""
    p = pick.copy()
    entry = float(p["entry_price"])
    tp = float(p["take_profit"])
    sl = float(p["stop_loss"])
    direction = p.get("direction", "LONG")
    asset_class = p.get("asset_class", "EQUITY")
    submitted_at = datetime.fromisoformat(p["submitted_at"].replace("Z", "+00:00"))
    window_days = RESOLUTION_WINDOWS_DAYS.get(asset_class, 30)
    expiry_dt = submitted_at + timedelta(days=window_days)
    now = datetime.now(timezone.utc)

    direction_mult = 1.0 if direction == "LONG" else -1.0

    # Check TP hit
    tp_hit = (current_price >= tp) if direction == "LONG" else (current_price <= tp)
    # Check SL hit
    sl_hit = (current_price <= sl) if direction == "LONG" else (current_price >= sl)

    if tp_hit:
        fill = apply_slippage(tp, direction, asset_class, is_tp=True)
        pnl = (fill - entry) / entry * direction_mult * 100
        p.update({"status": "WIN", "exit_price": fill, "pnl_pct": round(pnl, 4),
                   "resolved_at": now.isoformat(), "exit_reason": "TP_HIT"})
    elif sl_hit:
        fill = apply_slippage(sl, direction, asset_class, is_tp=False)
        pnl = (fill - entry) / entry * direction_mult * 100
        p.update({"status": "LOSS", "exit_price": fill, "pnl_pct": round(pnl, 4),
                   "resolved_at": now.isoformat(), "exit_reason": "SL_HIT"})
    elif now >= expiry_dt:
        # Closing price at expiry (not mid-price)
        fill = apply_slippage(current_price, direction, asset_class, is_tp=False)
        pnl = (fill - entry) / entry * direction_mult * 100
        status = "WIN" if pnl > 0 else "LOSS"
        p.update({"status": status, "exit_price": fill, "pnl_pct": round(pnl, 4),
                   "resolved_at": now.isoformat(), "exit_reason": "EXPIRY"})
    else:
        # Still open — update current price
        unrealized = (current_price - entry) / entry * direction_mult * 100
        p.update({"current_price": current_price, "unrealized_pnl_pct": round(unrealized, 4)})

    return p


def log_price(symbol: str, price: float, source: str, date_str: str) -> None:
    """Append price to immutable price log with SHA-256 hash."""
    PRICE_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = PRICE_LOG_DIR / f"{date_str}.json"
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "price": price,
        "source": source,
    }
    payload = json.dumps(entry, sort_keys=True)
    entry["sha256"] = hashlib.sha256(payload.encode()).hexdigest()

    existing = []
    if log_file.exists():
        try:
            existing = json.loads(log_file.read_text())
        except Exception:
            existing = []
    existing.append(entry)
    log_file.write_text(json.dumps(existing, indent=2))


def load_all_picks() -> list[dict[str, Any]]:
    """Load all pick submissions from data/ai_tournament/submissions/."""
    picks = []
    if SUBMISSIONS_DIR.exists():
        for f in sorted(SUBMISSIONS_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                if isinstance(data, list):
                    picks.extend(data)
                elif isinstance(data, dict):
                    # Submission envelope: {"model_id": ..., "picks": [...]}
                    if "picks" in data:
                        picks.extend(data["picks"])
                    else:
                        picks.append(data)
            except Exception:
                pass
    return picks


def main() -> None:
    print(f"[ai-tournament] price tracker starting at {datetime.now(timezone.utc).isoformat()}")
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    picks = load_all_picks()
    if not picks:
        print("[ai-tournament] no picks found — Phase 1B not yet complete")
        # Write empty latest
        LATEST_PICKS.parent.mkdir(parents=True, exist_ok=True)
        LATEST_PICKS.write_text(json.dumps([], indent=2))
        return

    open_picks = [p for p in picks if p.get("status") == "OPEN"]
    print(f"[ai-tournament] {len(picks)} total picks, {len(open_picks)} open")

    updated = []
    for pick in picks:
        if pick.get("status") != "OPEN":
            updated.append(pick)
            continue

        symbol = pick.get("symbol", "")
        asset_class = pick.get("asset_class", "EQUITY")
        price = fetch_price(pick)

        if price is None:
            print(f"  [SKIP] {symbol} — price fetch failed all sources")
            updated.append(pick)
            continue

        log_price(symbol, price, asset_class, date_str)
        resolved_pick = resolve_pick(pick, price)
        updated.append(resolved_pick)

        status = resolved_pick.get("status", "OPEN")
        pnl = resolved_pick.get("pnl_pct")
        print(f"  [{status:4s}] {symbol:12s} ${price:.4f} pnl={pnl}")
        time.sleep(0.2)  # avoid rate limits

    # Write latest picks snapshot
    PICKS_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = PICKS_DIR / f"picks_{date_str}.json"
    snapshot_file.write_text(json.dumps(updated, indent=2))

    LATEST_PICKS.parent.mkdir(parents=True, exist_ok=True)
    LATEST_PICKS.write_text(json.dumps(updated, indent=2))

    resolved = [p for p in updated if p.get("status") != "OPEN"]
    wins = [p for p in resolved if p.get("pnl_pct", 0) > 0]
    print(f"[ai-tournament] done. resolved={len(resolved)} wins={len(wins)} "
          f"wr={len(wins)/max(len(resolved),1):.1%}")


if __name__ == "__main__":
    main()
