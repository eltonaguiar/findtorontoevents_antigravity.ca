"""
KIMI Inverse Scanner -- Forward-test contrarian signals from KIMI's picks.

Historical evidence: KIMI 8% WR on 339 closed trades → Inverse = ~92% WR
Inverse contrarian report: 97.2% WR, Sharpe 23.6, walk-forward validated.

Strategy: Read KIMI active picks, flip direction, apply tighter risk management,
output as alpha_engine picks for the pick_monitor to track.
"""

import json
import os
import sys
from datetime import datetime, timezone

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
KIMI_DATA = os.path.join(PROJECT_ROOT, "KIMI_RISEOFTHECLAW", "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

_BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api.binance.us",
    "https://data-api.binance.vision",
]

# Shared multi-source failover (Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare).
# REQUIRED by project rule (CLAUDE.md / feedback_api_failover): never single Binance endpoint.
try:
    from alpha_engine.failover_imports import (
        fetch_tickers_24h as _shared_fetch_tickers_24h,
        fetch_klines as _shared_fetch_klines,
        HAS_SHARED_FAILOVER as _HAS_SHARED_FAILOVER,
    )
except ImportError:
    _HAS_SHARED_FAILOVER = False
    _shared_fetch_tickers_24h = None  # type: ignore[assignment]
    _shared_fetch_klines = None  # type: ignore[assignment]


# Binance price fetcher
def fetch_binance_prices(symbols):
    """Fetch current prices via shared multi-source failover.

    Preserves return shape: {requested_symbol: price_float}.
    """
    prices: dict = {}

    # Shared failover path (preferred): one ticker call covers everything
    if _HAS_SHARED_FAILOVER and _shared_fetch_tickers_24h is not None:
        try:
            tickers, _src = _shared_fetch_tickers_24h()
            if tickers:
                price_map = {}
                for t in tickers:
                    sym = t.get("symbol")
                    if not sym:
                        continue
                    try:
                        price_map[sym] = float(t["lastPrice"])
                    except (KeyError, ValueError, TypeError):
                        continue
                for sym in symbols:
                    normalized = sym.replace("-USD", "USDT").replace("-", "")
                    if normalized in price_map:
                        prices[sym] = price_map[normalized]
                if prices:
                    return prices
        except Exception as e:
            print(f"  [WARN] shared failover prices: {e}")

    # Fallback: direct Binance loop
    import urllib.request
    for base in _BINANCE_SPOT_BASES:
        try:
            url = f"{base}/api/v3/ticker/price"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            price_map = {t["symbol"]: float(t["price"]) for t in data}
            for sym in symbols:
                # Normalize: BTC-USD → BTCUSDT
                normalized = sym.replace("-USD", "USDT").replace("-", "")
                if normalized in price_map:
                    prices[sym] = price_map[normalized]
            return prices  # success
        except Exception as e:
            print(f"  [WARN] Binance price fetch from {base} failed: {e}")
            continue
    return prices


def load_kimi_picks():
    """Load KIMI active picks from all available sources."""
    all_picks = []

    # Source 1: active_picks.json (main scanner output)
    ap_path = os.path.join(KIMI_DATA, "active_picks.json")
    if os.path.exists(ap_path):
        with open(ap_path, encoding="utf-8") as f:
            d = json.load(f)
        picks = d.get("activePicks", [])
        for p in picks:
            all_picks.append({
                "symbol": p.get("symbol", ""),
                "direction": p.get("signal", "BUY"),
                "entry_price": p.get("entryPrice", 0),
                "current_price": p.get("currentPrice", 0),
                "strategy": p.get("reason", "unknown"),
                "source_file": "active_picks.json",
                "entry_date": p.get("entryDate", ""),
            })
        print(f"  Loaded {len(picks)} picks from active_picks.json")

    # Source 2: active_picks_v2.json (v2 engine)
    v2_path = os.path.join(KIMI_DATA, "active_picks_v2.json")
    if os.path.exists(v2_path):
        with open(v2_path, encoding="utf-8") as f:
            d = json.load(f)
        picks = d.get("activePicks", [])
        for p in picks:
            all_picks.append({
                "symbol": p.get("symbol", ""),
                "direction": p.get("direction", "LONG").replace("LONG", "BUY").replace("SHORT", "SELL"),
                "entry_price": p.get("entry_price", 0),
                "current_price": 0,
                "strategy": f"v2_{p.get('category', 'unknown')}",
                "source_file": "active_picks_v2.json",
                "entry_date": p.get("timestamp", ""),
            })
        print(f"  Loaded {len(picks)} picks from active_picks_v2.json")

    # Source 3: forward_signals_current.json
    fs_path = os.path.join(KIMI_DATA, "forward_signals_current.json")
    if os.path.exists(fs_path):
        with open(fs_path, encoding="utf-8") as f:
            d = json.load(f)
        signals = d.get("picks", d.get("signals", []))
        if isinstance(signals, list):
            for p in signals:
                direction = p.get("direction", "AVOID")
                if direction == "AVOID":
                    continue
                all_picks.append({
                    "symbol": p.get("symbol", ""),
                    "direction": direction.replace("LONG", "BUY").replace("SHORT", "SELL"),
                    "entry_price": p.get("price", 0),
                    "current_price": 0,
                    "strategy": f"forward_{p.get('category', 'unknown')}",
                    "source_file": "forward_signals_current.json",
                    "entry_date": p.get("timestamp", ""),
                })
            print(f"  Loaded {len([s for s in signals if s.get('direction') != 'AVOID'])} non-AVOID signals from forward_signals_current.json")

    return all_picks


def detect_regime(live_prices):
    """
    Multi-factor regime detection:
    1. 24h price changes (short-term momentum)
    2. Fear & Greed index (sentiment)
    3. BTC distance from 50d SMA proxy (trend)

    A 24h bounce in extreme fear != bullish. It's a relief rally.
    """
    import urllib.request
    short_term = "UNKNOWN"
    avg_change = 0
    fear_greed = 50  # default neutral
    btc_trend = "UNKNOWN"

    # Factor 1: 24h changes via shared multi-source failover
    tickers = None
    if _HAS_SHARED_FAILOVER and _shared_fetch_tickers_24h is not None:
        try:
            shared_tickers, _src = _shared_fetch_tickers_24h()
            if shared_tickers:
                tickers = shared_tickers
        except Exception:
            tickers = None

    if tickers is None:
        for _base in _BINANCE_SPOT_BASES:
            try:
                url = f"{_base}/api/v3/ticker/24hr"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    tickers = json.loads(resp.read().decode())
                break
            except Exception:
                continue
    try:
        if tickers is None:
            raise ValueError("all endpoints failed")
        top_syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                     "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"]
        ticker_map = {t["symbol"]: t for t in tickers}
        changes = []
        for sym in top_syms:
            t = ticker_map.get(sym, {})
            changes.append(float(t.get("priceChangePercent", 0)))
        avg_change = sum(changes) / len(changes)
        bullish_count = sum(1 for c in changes if c > 0)
        if avg_change > 1.5 and bullish_count >= 7:
            short_term = "STRONG_UP"
        elif avg_change > 0.3:
            short_term = "UP"
        elif avg_change > -0.3:
            short_term = "FLAT"
        elif avg_change > -1.5:
            short_term = "DOWN"
        else:
            short_term = "STRONG_DOWN"
    except Exception as e:
        print(f"  [WARN] 24h data failed: {e}")

    # Factor 2: Fear & Greed
    try:
        fg_url = "https://api.alternative.me/fng/?limit=1"
        req2 = urllib.request.Request(fg_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=5) as resp2:
            fg = json.loads(resp2.read().decode())
        fear_greed = int(fg["data"][0]["value"])
        fg_class = fg["data"][0]["value_classification"]
        print(f"  Fear & Greed: {fear_greed} ({fg_class})")
    except Exception as e:
        print(f"  [WARN] F&G fetch failed: {e}")

    # Factor 3: BTC trend (price vs 50-period SMA) via shared multi-source failover
    klines = None
    if _HAS_SHARED_FAILOVER and _shared_fetch_klines is not None:
        try:
            shared_klines = _shared_fetch_klines("BTCUSDT", "1d", 50)
            if isinstance(shared_klines, list) and shared_klines:
                klines = shared_klines
        except Exception:
            klines = None

    if klines is None:
        for _base in _BINANCE_SPOT_BASES:
            try:
                kline_url = f"{_base}/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=50"
                req3 = urllib.request.Request(kline_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req3, timeout=10) as resp3:
                    klines = json.loads(resp3.read().decode())
                break
            except Exception:
                continue
    try:
        if klines is None:
            raise ValueError("all endpoints failed")
        closes = [float(k[4]) for k in klines]
        sma50 = sum(closes) / len(closes)
        btc_price = closes[-1]
        pct_from_sma = (btc_price - sma50) / sma50 * 100
        print(f"  BTC vs 50d SMA: {pct_from_sma:+.1f}% (price=${btc_price:,.0f}, SMA=${sma50:,.0f})")
        if pct_from_sma > 5:
            btc_trend = "BULLISH"
        elif pct_from_sma > -5:
            btc_trend = "NEUTRAL"
        else:
            btc_trend = "BEARISH"
    except Exception as e:
        print(f"  [WARN] BTC trend failed: {e}")

    # Composite regime
    # Key insight: 24h bounce + extreme fear + bearish trend = RELIEF_RALLY, not BULLISH
    if fear_greed <= 25:
        if short_term in ("STRONG_UP", "UP"):
            regime = "RELIEF_RALLY"  # Bounce in fear -- fragile
        elif short_term in ("STRONG_DOWN", "DOWN"):
            regime = "CAPITULATION"
        else:
            regime = "EXTREME_FEAR"
    elif fear_greed >= 75:
        if short_term in ("STRONG_UP", "UP"):
            regime = "STRONG_BULLISH"
        else:
            regime = "EUPHORIA_FADING"
    else:
        # Normal sentiment range
        if btc_trend == "BULLISH" and short_term in ("STRONG_UP", "UP"):
            regime = "STRONG_BULLISH"
        elif btc_trend == "BULLISH":
            regime = "BULLISH"
        elif btc_trend == "BEARISH" and short_term in ("STRONG_DOWN", "DOWN"):
            regime = "STRONG_BEARISH"
        elif btc_trend == "BEARISH":
            regime = "BEARISH"
        else:
            regime = "NEUTRAL"

    print(f"  Composite: short={short_term}, F&G={fear_greed}, trend={btc_trend} -> {regime}")
    return regime, avg_change


def invert_picks(kimi_picks, live_prices, regime="UNKNOWN"):
    """
    Invert KIMI picks: BUY→SELL, SELL→BUY.
    Regime-aware: in strong bull, only invert SELL signals (contrarian shorts).
    In bear/neutral, invert everything (full inverse edge).
    """
    inverse_picks = []
    now = datetime.now(timezone.utc).isoformat()
    skipped_regime = 0

    for pick in kimi_picks:
        symbol = pick["symbol"]
        original_dir = pick["direction"]

        # Skip non-crypto for now (forex/equity need market hours check)
        if not any(symbol.endswith(s) for s in ["-USD", "USDT"]) and symbol not in ["BTC-USD", "ETH-USD", "SOL-USD"]:
            # Include forex/equity picks too but mark them
            pass

        # Get current price
        current_price = live_prices.get(symbol, pick.get("current_price", 0))
        entry_price = current_price if current_price > 0 else pick.get("entry_price", 0)

        if entry_price <= 0:
            continue

        # Regime-aware filtering
        # STRONG_BULLISH: don't short (KIMI BUYs may be right in true bull)
        # STRONG_BEARISH: don't go long (KIMI SELLs may be right in true bear)
        # RELIEF_RALLY: invert everything (KIMI historically wrong in these)
        # CAPITULATION: invert everything (KIMI historically wrong in these)
        # NEUTRAL/UNKNOWN: invert everything (full edge)
        if regime == "STRONG_BULLISH" and original_dir in ("BUY", "LONG"):
            skipped_regime += 1
            continue  # Don't short in a confirmed strong bull
        elif regime == "STRONG_BEARISH" and original_dir in ("SELL", "SHORT"):
            skipped_regime += 1
            continue  # Don't go long in a confirmed strong bear
        # RELIEF_RALLY, EXTREME_FEAR, CAPITULATION, NEUTRAL: invert everything

        # Flip direction
        if original_dir in ("BUY", "LONG"):
            inverse_dir = "SELL"
        elif original_dir in ("SELL", "SHORT"):
            inverse_dir = "BUY"
        else:
            continue

        # Risk management: 2% TP, 3% SL (tighter than KIMI's defaults)
        # Inverse signals historically have high WR so we can use tighter TP
        tp_pct = 0.02  # 2% take profit
        sl_pct = 0.03  # 3% stop loss

        if inverse_dir == "SELL":
            tp_price = entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 + sl_pct)
        else:
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)

        inverse_picks.append({
            "symbol": symbol,
            "signal": inverse_dir,
            "direction": inverse_dir,
            "entry_price": round(entry_price, 8),
            "take_profit": round(tp_price, 8),
            "stop_loss": round(sl_price, 8),
            "confidence": 75,  # High confidence based on 97.2% historical inverse WR
            "strategy": f"kimi_inverse",
            "original_strategy": pick["strategy"][:60],
            "original_direction": original_dir,
            "source": "kimi_inverse",
            "regime": regime,
            "risk_reward": round(tp_pct / sl_pct, 2),
            "timestamp": now,
            "entry_date": now,
            "notes": f"Inverse of KIMI {original_dir} signal. Historical inverse WR: 97.2%",
        })

    if skipped_regime:
        print(f"  Skipped {skipped_regime} picks due to regime filter ({regime})")
    return inverse_picks


def also_invert_zero_wr_alpha(live_prices):
    """
    Also invert zero-WR alpha_engine strategies.
    From audit: 8 strategies with 0% WR can serve as inverse signals.
    """
    zero_wr_strats = [
        "cross_sectional_momentum",
        "altcoin_season_rotation",
        "momentum_mean_rev_blend",
        "price_touch_recurrence",
        "smart_money_fvg",
        "fourier_cycle_detector",
        "halloween_effect",
        "exchange_netflow_reversal",
    ]

    # Load active picks and find zero-WR strategy picks
    active_path = os.path.join(PROJECT_ROOT, "data", "active_picks.json")
    if not os.path.exists(active_path):
        active_path = os.path.join(OUTPUT_DIR, "active_picks.json")
    if not os.path.exists(active_path):
        return []

    with open(active_path, encoding="utf-8") as f:
        picks = json.load(f)

    inverse_picks = []
    now = datetime.now(timezone.utc).isoformat()

    for pick in picks:
        strat = pick.get("strategy", "")
        if strat not in zero_wr_strats:
            continue

        symbol = pick.get("symbol", "")
        original_dir = pick.get("signal", pick.get("direction", ""))

        current_price = live_prices.get(symbol, 0)
        entry_price = current_price if current_price > 0 else pick.get("entry_price", pick.get("entryPrice", 0))
        if entry_price <= 0:
            continue

        # Flip
        if original_dir in ("BUY", "LONG", "L"):
            inverse_dir = "SELL"
        elif original_dir in ("SELL", "SHORT", "S"):
            inverse_dir = "BUY"
        else:
            continue

        tp_pct = 0.02
        sl_pct = 0.03

        if inverse_dir == "SELL":
            tp_price = entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 + sl_pct)
        else:
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)

        inverse_picks.append({
            "symbol": symbol,
            "signal": inverse_dir,
            "direction": inverse_dir,
            "entry_price": round(entry_price, 8),
            "take_profit": round(tp_price, 8),
            "stop_loss": round(sl_price, 8),
            "confidence": 65,
            "strategy": f"inverse_{strat}",
            "original_strategy": strat,
            "original_direction": original_dir,
            "source": "alpha_inverse",
            "risk_reward": round(tp_pct / sl_pct, 2),
            "timestamp": now,
            "entry_date": now,
            "notes": f"Inverse of 0%-WR strategy '{strat}'",
        })

    return inverse_picks


def run():
    print("=" * 60)
    print("  KIMI INVERSE SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    # 1. Load KIMI picks
    print("\n[1] Loading KIMI picks...")
    kimi_picks = load_kimi_picks()
    print(f"  Total KIMI picks: {len(kimi_picks)}")

    if not kimi_picks:
        print("  No KIMI picks found. Exiting.")
        return

    # 2. Fetch live prices
    print("\n[2] Fetching live prices...")
    crypto_symbols = list(set(p["symbol"] for p in kimi_picks if "-USD" in p["symbol"]))
    live_prices = fetch_binance_prices(crypto_symbols)
    print(f"  Got prices for {len(live_prices)} symbols")

    # 2b. Detect market regime
    print("\n[2b] Detecting market regime...")
    regime, avg_change = detect_regime(live_prices)
    print(f"  Regime: {regime} (avg 24h change: {avg_change:+.2f}%)")

    # 3. Generate inverse picks
    print("\n[3] Generating KIMI inverse picks...")
    inverse_picks = invert_picks(kimi_picks, live_prices, regime=regime)
    print(f"  Generated {len(inverse_picks)} inverse picks")

    # 4. Also invert zero-WR alpha strategies
    print("\n[4] Inverting zero-WR alpha strategies...")
    alpha_inverse = also_invert_zero_wr_alpha(live_prices)
    print(f"  Generated {len(alpha_inverse)} alpha inverse picks")

    all_inverse = inverse_picks + alpha_inverse

    # 5. Deduplicate by symbol+direction
    seen = set()
    deduped = []
    for p in all_inverse:
        key = f"{p['symbol']}_{p['direction']}"
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    all_inverse = deduped

    # 6. Score current P&L for existing inverse picks
    print(f"\n[5] Scoring {len(all_inverse)} inverse picks...")
    for p in all_inverse:
        sym = p["symbol"]
        if sym in live_prices and p["entry_price"] > 0:
            cur = live_prices[sym]
            if p["direction"] == "SELL":
                pnl = (p["entry_price"] - cur) / p["entry_price"] * 100
            else:
                pnl = (cur - p["entry_price"]) / p["entry_price"] * 100
            p["current_pnl_pct"] = round(pnl, 4)
            p["current_price"] = cur

            # Check TP/SL
            if p["direction"] == "SELL":
                if cur <= p["take_profit"]:
                    p["status"] = "TP_HIT"
                elif cur >= p["stop_loss"]:
                    p["status"] = "SL_HIT"
                else:
                    p["status"] = "OPEN"
            else:
                if cur >= p["take_profit"]:
                    p["status"] = "TP_HIT"
                elif cur <= p["stop_loss"]:
                    p["status"] = "SL_HIT"
                else:
                    p["status"] = "OPEN"

    # 7. Summary
    priced = [p for p in all_inverse if "current_pnl_pct" in p]
    wins = sum(1 for p in priced if p["current_pnl_pct"] > 0.05)
    losses = sum(1 for p in priced if p["current_pnl_pct"] < -0.05)
    flat = len(priced) - wins - losses
    avg_pnl = sum(p["current_pnl_pct"] for p in priced) / len(priced) if priced else 0

    print(f"\n{'='*60}")
    print(f"  INVERSE PICKS SUMMARY")
    print(f"{'='*60}")
    print(f"  Total inverse picks: {len(all_inverse)}")
    print(f"  Priced (crypto):     {len(priced)}")
    print(f"  Wins:                {wins}")
    print(f"  Losses:              {losses}")
    print(f"  Flat:                {flat}")
    if priced:
        print(f"  Win Rate:            {wins/(wins+losses)*100:.1f}%" if wins+losses else "  Win Rate:            N/A")
        print(f"  Avg P&L:             {avg_pnl:+.2f}%")

    # Show top picks
    priced_sorted = sorted(priced, key=lambda x: x["current_pnl_pct"], reverse=True)
    print(f"\n  Top 5 Inverse Winners:")
    for p in priced_sorted[:5]:
        print(f"    {p['direction']:4s} {p['symbol']:12s} PnL={p['current_pnl_pct']:+.2f}% [{p['strategy']}]")
    print(f"\n  Bottom 5 Inverse Losers:")
    for p in priced_sorted[-5:]:
        print(f"    {p['direction']:4s} {p['symbol']:12s} PnL={p['current_pnl_pct']:+.2f}% [{p['strategy']}]")

    # 8. Save results
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scanner": "kimi_inverse",
        "total_picks": len(all_inverse),
        "kimi_inverse_count": len(inverse_picks),
        "alpha_inverse_count": len(alpha_inverse),
        "summary": {
            "priced": len(priced),
            "wins": wins,
            "losses": losses,
            "flat": flat,
            "win_rate": round(wins / (wins + losses) * 100, 1) if wins + losses else 0,
            "avg_pnl": round(avg_pnl, 4),
        },
        "picks": all_inverse,
    }

    out_path = os.path.join(OUTPUT_DIR, "kimi_inverse_picks.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved to: {out_path}")

    # Also merge into active_picks.json for the pick_monitor
    merge_into_active_picks(all_inverse)

    return output


def merge_into_active_picks(inverse_picks):
    """Merge inverse picks into the main active_picks.json for monitoring."""
    active_path = os.path.join(PROJECT_ROOT, "data", "active_picks.json")
    if not os.path.exists(active_path):
        return

    with open(active_path, encoding="utf-8") as f:
        existing = json.load(f)

    # Remove old kimi_inverse picks
    existing = [p for p in existing if p.get("strategy", "") != "kimi_inverse"
                and not p.get("strategy", "").startswith("inverse_")]

    # --- Inline quality gates ---
    STABLES = {"USDCUSDT", "USDTUSDT", "BUSDUSDT", "DAIUSDT", "FDUSDUSDT", "TUSDUSDT"}
    MIN_CONF = 0.70
    kill_list = set()
    try:
        kl_path = os.path.join(OUTPUT_DIR, "core_whitelist.json")
        if os.path.exists(kl_path):
            with open(kl_path, encoding="utf-8") as kf:
                wl = json.load(kf)
            _safe = set()
            for _sg in ("protected_strategies", "core_strategies", "incubator_strategies"):
                _safe.update(s.lower() for s in wl.get(_sg, []) if isinstance(s, str))
            for _ks in wl.get("kill_list", []):
                _kb = _ks.split("::", 1)[1].lower() if "::" in _ks else _ks.lower()
                if _kb not in _safe:
                    kill_list.add(_ks.lower())
                    if "::" in _ks:
                        kill_list.add(_kb)
    except Exception:
        pass
    existing_syms_dirs = {f"{p.get('symbol','')}_{p.get('direction', p.get('signal',''))}" for p in existing}

    gated_picks = []
    for p in inverse_picks:
        sym = p.get("symbol", "").replace("-USD", "USDT").replace("-", "")
        strat = (p.get("strategy") or "").lower()
        conf = float(p.get("confidence", 0) or 0)
        # Normalize confidence from percentage to decimal if needed
        if conf > 1.0:
            conf = conf / 100.0
        if conf < MIN_CONF:
            print(f"  [QUALITY GATE] Rejected {sym}: conf={conf:.2f} < {MIN_CONF}")
            continue
        if sym in STABLES:
            print(f"  [QUALITY GATE] Rejected {sym}: stablecoin")
            continue
        if strat in kill_list:
            print(f"  [QUALITY GATE] Rejected {sym}: strategy '{strat}' in kill list")
            continue
        dedup_key = f"{p.get('symbol','')}_{p.get('direction', p.get('signal',''))}"
        if dedup_key in existing_syms_dirs:
            continue
        existing_syms_dirs.add(dedup_key)
        gated_picks.append(p)

    # Add gated inverse picks (format for pick_monitor)
    for p in gated_picks:
        existing.append({
            "symbol": p["symbol"],
            "signal": p["signal"],
            "strategy": p["strategy"],
            "entry_price": p["entry_price"],
            "take_profit": p["take_profit"],
            "stop_loss": p["stop_loss"],
            "confidence": p["confidence"],
            "source": p["source"],
            "timestamp": p["timestamp"],
        })

    with open(active_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    print(f"  Merged {len(gated_picks)} inverse picks into active_picks.json (total: {len(existing)})")


if __name__ == "__main__":
    run()
