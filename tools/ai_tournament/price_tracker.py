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
    "PENNY": 7,
    "FUTURES": 14,
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
    clean = _sanitize_yf_symbol(symbol)
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


def _sanitize_yf_symbol(symbol: str) -> str:
    """Normalise a symbol for yfinance lookups.

    Strips writer-artifact $-prefixes, converts Yahoo class-share separators
    (``BRK.B`` → ``BRK-B``), drops ``=X`` FX suffixes, and preserves ``=F``
    futures suffixes.  Without this, ~470 price calls per run fail on BRK.B
    + $-prefixed tickers, contributing to the 20-min workflow timeout on
    ai-tournament-price-tracker.yml.
    """
    clean = symbol.lstrip("$").replace("=X", "")
    if "." in clean and not clean.endswith("=F"):
        clean = clean.replace(".", "-")
    return clean


def _scan_bars_for_touch(
    bars: list[dict], direction: str, tp: float, sl: float
) -> dict[str, Any] | None:
    """Walk daily OHLC bars from entry forward; return first TP or SL touch.

    SL is checked first (conservative — assumes worst-case fill when both
    barriers could be hit in the same bar). Gap-through: if a bar opens past
    the level, fills at the open price rather than the nominal barrier.

    Returns {"price": <fill>, "reason": "TP_HIT_REPLAY"|"SL_HIT_REPLAY",
             "bar_date": "YYYY-MM-DD", "gapped": bool} or None.
    """
    if not bars or not (tp > 0 or sl > 0):
        return None
    is_long = str(direction or "").upper() in ("LONG",)
    for bar in bars:
        try:
            hi = float(bar.get("high", 0) or 0)
            lo = float(bar.get("low", 0) or 0)
            op = float(bar.get("open", 0) or 0)
        except (TypeError, ValueError):
            continue
        if hi <= 0 or lo <= 0:
            continue
        if is_long:
            if sl > 0 and lo <= sl:
                gapped = op > 0 and op <= sl
                return {"price": op if gapped else sl,
                        "reason": "SL_HIT_REPLAY",
                        "bar_date": bar.get("date", ""), "gapped": gapped}
            if tp > 0 and hi >= tp:
                gapped = op > 0 and op >= tp
                return {"price": op if gapped else tp,
                        "reason": "TP_HIT_REPLAY",
                        "bar_date": bar.get("date", ""), "gapped": gapped}
        else:  # SHORT
            if sl > 0 and hi >= sl:
                gapped = op > 0 and op >= sl
                return {"price": op if gapped else sl,
                        "reason": "SL_HIT_REPLAY",
                        "bar_date": bar.get("date", ""), "gapped": gapped}
            if tp > 0 and lo <= tp:
                gapped = op > 0 and op <= tp
                return {"price": op if gapped else tp,
                        "reason": "TP_HIT_REPLAY",
                        "bar_date": bar.get("date", ""), "gapped": gapped}
    return None


def _yf_symbol_for(pick: dict[str, Any]) -> str:
    """Return the yfinance-ready symbol for a pick."""
    sym = pick.get("symbol", "")
    ac = (pick.get("asset_class") or "").upper()
    if ac == "FOREX":
        clean = sym.upper().replace("=X", "")
        return FOREX_YFINANCE_SUFFIX.get(clean, f"{clean}=X")
    return _sanitize_yf_symbol(sym)


def _fetch_ohlc_crypto_binance(symbol: str, start_iso: str) -> list[dict]:
    """Daily Binance klines for crypto, from start_iso forward. Used to give CRYPTO
    intrabar TP/SL replay coverage (yfinance has no Binance klines, so without this
    every CRYPTO resolution falls back to the once-daily spot snapshot — 100% spot
    coverage measured 2026-06-03 vs 13-23% for non-crypto classes).

    Failover chain identical to fetch_price_crypto: Binance mirrors → CoinGecko OHLC
    (5-day window only) → KuCoin (recent daily). Returns [] on any total failure.
    """
    base = symbol.upper().replace("USDT", "").replace("USD", "")
    pair = f"{base}USDT"
    try:
        start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return []
    start_ms = int(start_dt.timestamp() * 1000)
    # Binance mirrors — 3-host failover per CLAUDE.md API Failover Rule
    binance_key = os.environ.get("BINANCE_API_KEY", "")
    headers = {"X-MBX-APIKEY": binance_key} if binance_key else {}
    for host in ("api", "api1", "api2", "api3"):
        try:
            r = requests.get(
                f"https://{host}.binance.com/api/v3/klines",
                params={"symbol": pair, "interval": "1d",
                        "startTime": start_ms, "limit": 90},
                headers=headers, timeout=10,
            )
            if r.status_code != 200:
                continue
            klines = r.json()
            if not isinstance(klines, list) or not klines:
                continue
            bars = []
            for k in klines:
                try:
                    # Binance kline: [open_time, O, H, L, C, V, close_time, ...]
                    ts_ms = int(k[0])
                    date_str = datetime.fromtimestamp(
                        ts_ms / 1000, tz=timezone.utc
                    ).strftime("%Y-%m-%d")
                    bars.append({
                        "date": date_str,
                        "open": float(k[1]), "high": float(k[2]),
                        "low": float(k[3]), "close": float(k[4]),
                    })
                except (TypeError, ValueError, IndexError):
                    continue
            if bars:
                return bars
        except Exception:
            continue
    # Tier 2: CoinGecko OHLC (5-day window, daily)
    try:
        cg_id = COINGECKO_IDS.get(base, base.lower())
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc",
            params={"vs_currency": "usd", "days": "30"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                bars = []
                for row in data:
                    try:
                        ts_ms, op, hi, lo, cl = row
                        if int(ts_ms) < start_ms:
                            continue
                        date_str = datetime.fromtimestamp(
                            int(ts_ms) / 1000, tz=timezone.utc
                        ).strftime("%Y-%m-%d")
                        bars.append({"date": date_str,
                                     "open": float(op), "high": float(hi),
                                     "low": float(lo), "close": float(cl)})
                    except (TypeError, ValueError):
                        continue
                if bars:
                    return bars
    except Exception:
        pass
    # Tier 3: KuCoin klines (1day). Often unblocked from GHA runners when
    # Binance returns 451 and CoinGecko hits 429. Verified 2026-06-04 from
    # GHA-equivalent: KuCoin returned 200 + 5 valid daily bars for BTC-USDT.
    # NOTE: KuCoin row order is [time, OPEN, CLOSE, HIGH, LOW, vol, turnover]
    # — not OHLC. Easy to invert. startAt/endAt are UNIX SECONDS.
    try:
        kc_pair = f"{base}-USDT"
        start_s = start_ms // 1000
        end_s = int(datetime.now(timezone.utc).timestamp())
        r = requests.get(
            "https://api.kucoin.com/api/v1/market/candles",
            params={"symbol": kc_pair, "type": "1day",
                    "startAt": start_s, "endAt": end_s},
            timeout=10,
        )
        if r.status_code == 200:
            j = r.json()
            data = j.get("data") if isinstance(j, dict) else None
            if isinstance(data, list) and data:
                bars = []
                for row in data:
                    try:
                        ts_s = int(row[0])
                        op = float(row[1]); cl = float(row[2])
                        hi = float(row[3]); lo = float(row[4])
                        date_str = datetime.fromtimestamp(
                            ts_s, tz=timezone.utc
                        ).strftime("%Y-%m-%d")
                        bars.append({"date": date_str,
                                     "open": op, "high": hi,
                                     "low": lo, "close": cl})
                    except (TypeError, ValueError, IndexError):
                        continue
                # KuCoin returns newest-first; sort ascending so the bar-scan
                # walks forward correctly from entry.
                bars.sort(key=lambda b: b["date"])
                if bars:
                    return bars
    except Exception:
        pass
    return []


def fetch_ohlc_window(pick: dict[str, Any]) -> list[dict]:
    """Fetch daily OHLC bars from entry date through today.

    Routes by asset_class: CRYPTO → Binance/CoinGecko (yfinance has no crypto
    klines), all others → yfinance. Returns [] on any failure (caller falls
    back to single-spot resolution).
    """
    try:
        submitted_at = datetime.fromisoformat(
            pick["submitted_at"].replace("Z", "+00:00")
        )
    except (KeyError, ValueError):
        return []

    # 2026-06-04 fix: CRYPTO via Binance klines, not yfinance. Without this,
    # 100% of CRYPTO resolutions fell back to spot-snapshot (594/594 in last
    # 7d as of 2026-06-03), creating the resolver-artifact bias documented in
    # the DISPUTED banner on /audit/ai-tournament.html. Wiring Binance klines
    # for CRYPTO is the single highest-impact fix for institutional-grade
    # WR/PF on the tournament page (CRYPTO is 15% of total resolution volume).
    if (pick.get("asset_class") or "").upper() == "CRYPTO":
        return _fetch_ohlc_crypto_binance(
            pick.get("symbol", ""),
            pick.get("submitted_at", ""),
        )

    yf_sym = _yf_symbol_for(pick)
    start = submitted_at - timedelta(days=1)
    end = datetime.now(timezone.utc) + timedelta(days=1)
    try:
        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(start=start.strftime("%Y-%m-%d"),
                              end=end.strftime("%Y-%m-%d"),
                              interval="1d", auto_adjust=False)
    except Exception:
        return []
    if hist is None or hist.empty:
        return []
    bars: list[dict] = []
    cutoff = submitted_at.strftime("%Y-%m-%d")
    try:
        for ts, row in hist.iterrows():
            try:
                hi = float(row["High"])
                lo = float(row["Low"])
                op = float(row["Open"])
                cl = float(row["Close"])
            except (KeyError, TypeError, ValueError):
                continue
            date_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)
            if date_str < cutoff:
                continue
            bars.append({"date": date_str, "open": op, "high": hi,
                         "low": lo, "close": cl})
    except Exception:
        return []
    return bars


def resolve_pick(
    pick: dict[str, Any],
    current_price: float,
    ohlc_bars: list[dict] | None = None,
) -> dict[str, Any]:
    """Determine if a pick has resolved (TP/SL hit or expiry).

    When ``ohlc_bars`` is provided (non-empty list of daily OHLC bars from
    entry through today), walks the bars for an intrabar TP/SL touch using
    the conservative SL-first rule. This replaces the legacy single-spot
    snapshot that missed intraday SL touches and inflated WR to 80-90%.
    Falls back to single-spot resolution when OHLC data is unavailable.
    """
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

    # ── Mispriced-entry drift guard (2026-06-04) ──────────────────────
    # AI models occasionally submit picks with pre-corporate-action prices
    # (LODE 1-for-10 split Feb 2025: entry $0.27 vs live $4.10 → 1373% false
    # win after replay). Also affects futures contract rolls (SI=F, GC=F,
    # CT=F, NG=F) and dividend-adjusted ETFs. If the first OHLC bar's open
    # is more than MAX_DRIFT_PCT away from entry_price, the entry is stale
    # — refuse to resolve as WIN/LOSS and mark MISPRICED_ENTRY for exclusion
    # from leaderboard aggregates. Measured 2026-06-04: 134 of 5677 closes
    # have |pnl|>100% (almost all this pattern).
    MAX_ENTRY_DRIFT_PCT = float(
        os.environ.get("RESOLVER_MAX_ENTRY_DRIFT_PCT", "50.0")
    )
    if ohlc_bars and entry > 0:
        first_open = float(ohlc_bars[0].get("open", 0) or 0)
        if first_open > 0:
            drift = abs(first_open - entry) / entry * 100
            if drift > MAX_ENTRY_DRIFT_PCT:
                p.update({
                    "status": "MISPRICED_ENTRY",
                    "exit_price": first_open,
                    "pnl_pct": None,
                    "resolved_at": now.isoformat(),
                    "exit_reason": "MISPRICED_ENTRY_REJECTED",
                    "_drift_pct": round(drift, 2),
                    "_market_at_submission": round(first_open, 4),
                })
                return p

    # ── Intrabar OHLC path replay (v2) ──
    if ohlc_bars:
        hit = _scan_bars_for_touch(ohlc_bars, direction, tp, sl)
        if hit:
            fill = apply_slippage(hit["price"], direction, asset_class,
                                  is_tp=hit["reason"].startswith("TP"))
            pnl = (fill - entry) / entry * direction_mult * 100
            status = "WIN" if hit["reason"].startswith("TP") else "LOSS"
            p.update({"status": status, "exit_price": fill,
                       "pnl_pct": round(pnl, 4),
                       "resolved_at": now.isoformat(),
                       "exit_reason": hit["reason"],
                       "_replay_bar_date": hit.get("bar_date", ""),
                       "_replay_gapped": hit.get("gapped", False)})
            return p
        # No touch in OHLC window. If the pick has aged past its resolution
        # window, close at the LAST bar's close (real time-exit PnL).
        if now >= expiry_dt and ohlc_bars:
            last_close = ohlc_bars[-1].get("close", 0)
            if last_close and last_close > 0:
                fill = apply_slippage(last_close, direction, asset_class,
                                      is_tp=False)
                pnl = (fill - entry) / entry * direction_mult * 100
                status = "WIN" if pnl > 0 else "LOSS"
                p.update({"status": status, "exit_price": fill,
                           "pnl_pct": round(pnl, 4),
                           "resolved_at": now.isoformat(),
                           "exit_reason": "TIME_EXIT_REPLAY",
                           "_replay_bar_date": ohlc_bars[-1].get("date", "")})
                return p

    # ── Legacy single-spot snapshot (fallback) ──
    tp_hit = (current_price >= tp) if direction == "LONG" else (current_price <= tp)
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
        fill = apply_slippage(current_price, direction, asset_class, is_tp=False)
        pnl = (fill - entry) / entry * direction_mult * 100
        status = "WIN" if pnl > 0 else "LOSS"
        p.update({"status": status, "exit_price": fill, "pnl_pct": round(pnl, 4),
                   "resolved_at": now.isoformat(), "exit_reason": "EXPIRY"})
    else:
        unrealized = (current_price - entry) / entry * direction_mult * 100
        p.update({"current_price": current_price,
                   "unrealized_pnl_pct": round(unrealized, 4)})

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
        # Do NOT overwrite LATEST_PICKS here. The submissions/*.json glob is a
        # partial cohort; the canonical writer of ai_tournament_picks_latest.json
        # is tools/ai_tournament/rebuild_latest_from_db.py (the "Restore full
        # dataset from DB" step that runs immediately after price_tracker.py in
        # both ai-tournament-pipeline.yml and ai-tournament-price-tracker.yml).
        # Truncating to [] here on glob-miss was the root cause of
        # INCIDENT_OVERALL #39 (recurring 3,873 -> 1,037 / 478-pick regressions).
        return

    open_picks = [p for p in picks if p.get("status") == "OPEN"]
    print(f"[ai-tournament] {len(picks)} total picks, {len(open_picks)} open")

    # Pre-fetch OHLC windows for open picks (one source-routed call per
    # unique symbol). 2026-06-04: removed the `if ac != "CRYPTO"` guard —
    # the original comment ("CRYPTO uses Binance spot API without OHLC") is
    # stale since PR #512 wired Binance klines + CoinGecko + KuCoin OHLC
    # for CRYPTO via _fetch_ohlc_crypto_binance. Without removing this
    # guard, the daily resolver fell back to spot-snapshot for every
    # CRYPTO close — measured 0% CRYPTO REPLAY coverage on 2026-06-04 vs
    # 100% for non-crypto classes.
    ohlc_cache: dict[str, list[dict]] = {}
    symbols_seen: set[str] = set()
    for pick in open_picks:
        sym = pick.get("symbol", "")
        if sym and sym not in symbols_seen:
            symbols_seen.add(sym)
            try:
                ohlc_cache[sym] = fetch_ohlc_window(pick)
            except Exception:
                ohlc_cache[sym] = []
            time.sleep(0.1)  # rate-limit upstream calls

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
        resolved_pick = resolve_pick(pick, price, ohlc_bars=ohlc_cache.get(symbol))
        updated.append(resolved_pick)

        status = resolved_pick.get("status", "OPEN")
        pnl = resolved_pick.get("pnl_pct")
        replay = resolved_pick.get("_replay_bar_date", "")
        tag = f" replay={replay}" if replay else ""
        print(f"  [{status:4s}] {symbol:12s} ${price:.4f} pnl={pnl}{tag}")
        time.sleep(0.2)  # avoid rate limits

    # Write per-day snapshot only. LATEST_PICKS is intentionally NOT written
    # here: this loop loads from the submissions/*.json glob, which is a
    # partial cohort (missing models whose submission files haven't synced,
    # excluding rows that only made it to the DB via ingest_to_db.py). The
    # canonical writer of ai_tournament_picks_latest.json is
    # rebuild_latest_from_db.py, which runs in the "Restore full dataset from
    # DB (anti-clobber guard)" step right after this one. Writing here was
    # the clobber path that caused INCIDENT_OVERALL #39 — when the rebuild
    # step's DB connection also failed (run 26697651272 on 2026-05-30), the
    # 1,037-pick partial committed instead of the full 4,419-pick set.
    PICKS_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = PICKS_DIR / f"picks_{date_str}.json"
    snapshot_file.write_text(json.dumps(updated, indent=2))

    resolved = [p for p in updated if p.get("status") != "OPEN"]
    wins = [p for p in resolved if p.get("pnl_pct", 0) > 0]
    print(f"[ai-tournament] done. resolved={len(resolved)} wins={len(wins)} "
          f"wr={len(wins)/max(len(resolved),1):.1%}")


if __name__ == "__main__":
    main()
