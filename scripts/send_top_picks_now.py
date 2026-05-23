#!/usr/bin/env python3
"""
Send top picks to Discord channels immediately.
Run this to manually trigger picks sending.

Hardened behavior:
- Uses symbol-level consensus (one pick per symbol)
- Preserves consensus metadata (agreeing systems, consensus score)
- Never force-sends to #master-picks; routing gates decide
"""

import sys
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, '.')

from signal_aggregator.picks_router import PicksRouter, SIGNAL_FRESHNESS_MAX_SECONDS

# Portfolio circuit breaker - MANDATORY for production safety
from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker
_CB_AVAILABLE = True  # Always True - import failure = module failure


def _check_circuit_breaker_pre_send():
    """
    Check circuit breaker before sending any picks.

    Returns (level, reasons) where level is one of GREEN/YELLOW/RED/HALT.
    Falls back to ("GREEN", []) on check failure so sending proceeds normally.
    """
    try:
        tracker_path = Path("signal_aggregator/data/master_picks_tracker.json")
        equity_curve = []
        if tracker_path.exists():
            with open(tracker_path) as f:
                data = json.load(f)
            closed = [
                p for p in data.get("active_picks", []) + data.get("closed_picks", [])
                if p.get("status") == "closed" and p.get("pnl_percent") is not None
            ]
            closed.sort(key=lambda p: p.get("exit_time") or "")
            equity = 100.0
            equity_curve = [equity]
            for pick in closed:
                pnl_pct = float(pick["pnl_percent"]) / 100.0
                equity = equity * (1.0 + pnl_pct)
                equity_curve.append(round(equity, 4))

        breaker = PortfolioCircuitBreaker(portfolio_value=100.0)
        status = breaker.check(equity_curve)
        return status.level, status.reasons
    except Exception as e:
        print(f"[circuit-breaker] Check failed ({e}), proceeding with GREEN default")
        return "GREEN", []


def load_consensus_signals():
    """Load signals from consensus output."""
    try:
        with open('signal_aggregator/data/consensus_output.json') as f:
            data = json.load(f)

        signals = []
        for symbol, consensus in data.get('signals', {}).items():
            raw_signals = consensus.get('signals', [])
            if not raw_signals:
                continue

            direction = str(consensus.get('direction', 'NEUTRAL')).upper()
            directional = [
                s for s in raw_signals
                if str(s.get('direction', '')).upper() == direction
            ]
            pool = directional or raw_signals
            best = max(pool, key=lambda x: x.get('confidence', 0))

            agreeing_systems = consensus.get('agreeing_systems', [])
            if not isinstance(agreeing_systems, list):
                agreeing_systems = []
            unique_systems = sorted(
                {str(s).strip() for s in agreeing_systems if s}
                or {str(s.get('system', 'unknown')).strip() for s in pool}
            )

            total_systems = consensus.get('total_systems', len(unique_systems))
            try:
                total_systems = max(1, int(total_systems))
            except Exception:
                total_systems = max(1, len(unique_systems))

            consensus_score = consensus.get('consensus_score')
            if consensus_score is None:
                conf = float(best.get('confidence', 0))
                consensus_score = (len(unique_systems) / total_systems) * conf

            signals.append({
                'symbol': best.get('symbol', symbol),
                'direction': direction,
                'confidence': best.get('confidence', 0.5),
                'system': best.get('system', 'consensus'),
                'entry_price': best.get('entry_price'),
                'tp_price': best.get('tp_price'),
                'sl_price': best.get('sl_price'),
                'timeframe': best.get('timeframe', '1h'),
                'quality_score': best.get('quality_score', 0),
                'consensus_score': consensus_score,
                'consensus_count': len(unique_systems),
                'total_systems': total_systems,
                'agreeing_systems': unique_systems,
                'systems': unique_systems,
            })

        # Sort by joint confidence (consensus quality first, then confidence)
        signals.sort(
            key=lambda x: (x.get('consensus_score', 0), x.get('confidence', 0)),
            reverse=True,
        )
        return signals
    except Exception as e:
        print(f"Error loading consensus: {e}")
        return []


def _compute_rr(signal: dict) -> float | None:
    """Return risk:reward ratio or None if not computable."""
    entry = signal.get('entry_price')
    tp = signal.get('tp_price')
    sl = signal.get('sl_price')
    if not all([entry, tp, sl]):
        return None
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    if risk <= 0:
        return None
    return reward / risk


def _is_fresh(signal: dict) -> bool:
    """Return True if signal timestamp is within freshness window."""
    ts_raw = signal.get('timestamp')
    if ts_raw is None:
        return True  # no timestamp -> assume fresh
    try:
        if isinstance(ts_raw, (int, float)):
            sig_time = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
        else:
            ts_str = str(ts_raw)
            if ts_str.endswith('Z'):
                ts_str = ts_str[:-1] + '+00:00'
            sig_time = datetime.fromisoformat(ts_str)
            if sig_time.tzinfo is None:
                sig_time = sig_time.replace(tzinfo=timezone.utc)
        age = (datetime.now(tz=timezone.utc) - sig_time).total_seconds()
        return age <= SIGNAL_FRESHNESS_MAX_SECONDS
    except Exception:
        return True  # unparseable -> assume fresh


def _compute_atr(price_series: list, period: int = 14) -> float:
    """Compute Average True Range for volatility-scaled TP/SL."""
    if len(price_series) < period + 1:
        return 0.02  # Default 2% if insufficient data
    
    highs = [p * 1.001 for p in price_series]  # Approximate if no OHLC
    lows = [p * 0.999 for p in price_series]
    closes = price_series
    
    tr_list = []
    for i in range(1, len(closes)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i-1])
        tr3 = abs(lows[i] - closes[i-1])
        tr_list.append(max(tr1, tr2, tr3))
    
    if len(tr_list) < period:
        return 0.02
    
    return sum(tr_list[-period:]) / period / closes[-1]  # Return as percentage


def _compute_dynamic_tp_sl(entry: float, atr_pct: float, direction: str, 
                           rr_ratio: float = 1.5) -> tuple:
    """
    Compute dynamic TP/SL based on ATR (volatility-scaled).
    
    Args:
        entry: Entry price
        atr_pct: ATR as percentage of price
        direction: "BUY" or "SELL"
        rr_ratio: Risk:Reward ratio (default 1.5)
    
    Returns:
        (tp_price, sl_price)
    """
    sl_distance = entry * atr_pct * 1.5  # 1.5x ATR for stop
    tp_distance = sl_distance * rr_ratio  # TP = SL * R:R
    
    if direction == "BUY":
        sl = entry - sl_distance
        tp = entry + tp_distance
    else:
        sl = entry + sl_distance
        tp = entry - tp_distance
    
    return tp, sl


def _compute_kelly_size(confidence: float, edge: float, vol: float, cap: float = 0.02) -> float:
    """
    Calculate Kelly fraction for position sizing.
    
    Args:
        confidence: Model confidence (probability of win, 0-1)
        edge: Expected return per trade (as decimal)
        vol: Forecasted volatility (annualized, as decimal)
        cap: Max fraction of portfolio per trade (default 2%)
    
    Returns:
        Fraction of portfolio to allocate (0 to cap)
    """
    if vol < 0.001:  # Avoid division by zero
        vol = 0.001
    
    # Simple Kelly: f = (2p-1) * edge / vol^2
    f = (2 * confidence - 1) * edge / (vol ** 2)
    return max(min(f, cap), 0.0)  # Never negative, never exceed cap


def _compute_portfolio_kelly_allocation(signals: list[dict], portfolio_value: float) -> list[dict]:
    """
    Compute portfolio-level Kelly allocation across all signals.
    
    This ensures we don't over-allocate when multiple signals are correlated.
    Uses the "fractional Kelly" approach with correlation penalty.
    
    Args:
        signals: List of signal dictionaries
        portfolio_value: Total portfolio value
    
    Returns:
        Signals with adjusted size_frac (portfolio-level optimized)
    """
    if not signals:
        return signals
    
    # Group by symbol to detect duplicates/correlation
    symbol_groups = {}
    for sig in signals:
        sym = sig.get('symbol', '')
        if sym not in symbol_groups:
            symbol_groups[sym] = []
        symbol_groups[sym].append(sig)
    
    # Apply correlation penalty for similar assets
    # (e.g., BTC and ETH are correlated, reduce combined exposure)
    correlated_pairs = [
        ('BTC', 'ETH', 0.7),  # 70% correlation
        ('ETH', 'SOL', 0.6),
        ('BTC', 'SOL', 0.5),
        ('DOGE', 'SHIB', 0.8),
    ]
    
    total_kelly = sum(sig.get('size_frac', 0) for sig in signals)
    
    # If total Kelly exceeds 20% of portfolio, scale down proportionally
    max_portfolio_kelly = 0.20
    if total_kelly > max_portfolio_kelly:
        scale_factor = max_portfolio_kelly / total_kelly
        for sig in signals:
            sig['size_frac'] = sig.get('size_frac', 0) * scale_factor
            sig['kelly_scaling'] = f"Portfolio cap: {scale_factor:.2f}x"
    
    # Apply correlation penalty
    for sym1, sym2, corr in correlated_pairs:
        signals1 = [s for s in signals if sym1 in s.get('symbol', '')]
        signals2 = [s for s in signals if sym2 in s.get('symbol', '')]
        
        if signals1 and signals2:
            # Reduce size of both by correlation factor
            penalty = 1 - corr * 0.5  # 50% reduction at max correlation
            for s in signals1 + signals2:
                original = s.get('size_frac', 0)
                s['size_frac'] = original * penalty
                s['correlation_penalty'] = f"{sym1}-{sym2} correlation: {corr}"
    
    return signals


def _compute_dynamic_threshold(base_threshold: float, vol_forecast: float, vol_target: float = 0.02) -> float:
    """
    Compute dynamic confidence threshold based on volatility.
    
    Higher volatility = higher threshold (need more confidence to trade)
    
    Formula: thr = base + k * (vol_forecast/vol_target - 1)
    
    Args:
        base_threshold: Base threshold (e.g., 0.60)
        vol_forecast: Current forecasted volatility
        vol_target: Target volatility (default 2%)
    
    Returns:
        Adjusted threshold
    """
    k = 0.10  # Scaling factor
    adjustment = k * (vol_forecast / vol_target - 1)
    return base_threshold + adjustment


def _bootstrap_confidence_interval(returns: list, n_bootstrap: int = 1000, confidence: float = 0.95) -> tuple:
    """
    Compute bootstrap confidence interval for Sharpe ratio or profit factor.
    
    Args:
        returns: List of daily returns
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level (default 95%)
    
    Returns:
        (lower_bound, upper_bound)
    """
    if len(returns) < 30:
        return (0, 0)  # Insufficient data
    
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        # Resample with replacement
        sample = [returns[np.random.randint(0, len(returns))] for _ in range(len(returns))]
        
        # Compute Sharpe for this sample
        if np.std(sample) > 0:
            sharpe = np.mean(sample) / np.std(sample) * np.sqrt(365)
            bootstrap_stats.append(sharpe)
    
    # Compute percentiles
    lower = np.percentile(bootstrap_stats, (1 - confidence) / 2 * 100)
    upper = np.percentile(bootstrap_stats, (1 + confidence) / 2 * 100)
    
    return (lower, upper)


def _compute_garch_volatility(returns: list, forecast_horizon: int = 1) -> float:
    """
    Compute GARCH(1,1) volatility forecast.
    
    More accurate than simple historical volatility for fat-tailed crypto returns.
    
    Args:
        returns: List of historical returns
        forecast_horizon: Days ahead to forecast (default 1)
    
    Returns:
        Forecasted annualized volatility
    """
    try:
        from arch import arch_model
        
        if len(returns) < 100:
            # Fall back to historical volatility
            return np.std(returns) * np.sqrt(365)
        
        # Fit GARCH(1,1)
        model = arch_model(returns, vol='Garch', p=1, q=1, rescale=False)
        fitted = model.fit(disp='off')
        
        # Forecast
        forecast = fitted.forecast(horizon=forecast_horizon)
        vol_forecast = np.sqrt(forecast.variance.values[-1, 0])
        
        # Annualize
        return vol_forecast * np.sqrt(365)
    except ImportError:
        # arch library not available, fall back to historical
        return np.std(returns[-30:]) * np.sqrt(365) if returns else 0.50
    except Exception:
        return np.std(returns[-30:]) * np.sqrt(365) if returns else 0.50


def _apply_safety_filters(signals: list[dict]) -> list[dict]:
    """
    Apply safety filters before sending signals to Discord.

    Filters:
    - RR sanity: skip signals with risk_reward < 1.0
    - Freshness: skip signals older than 15 minutes
    - Confidence quality: skip if confidence < 0.60
    - Regime alignment: reduce confidence in CRASH regime
    - Add dynamic TP/SL and Kelly sizing
    """
    filtered = []
    skipped_rr = 0
    skipped_stale = 0
    skipped_confidence = 0
    skipped_regime = 0
    
    # Track last prices for ATR calculation
    price_history = {}

    for sig in signals:
        # Freshness check
        if not _is_fresh(sig):
            skipped_stale += 1
            continue
        
        # Confidence quality check
        confidence = sig.get('confidence', 0)
        if confidence < 0.60:
            skipped_confidence += 1
            continue
        
        # Get regime info (if available)
        regime = sig.get('regime', 'UNKNOWN')
        
        # Reduce confidence in CRASH regime for LONG signals
        if regime == "CRASH" and sig.get('direction') == "BUY":
            confidence *= 0.3  # Heavy penalty for longs in crash
            sig['confidence'] = confidence
            if confidence < 0.50:
                skipped_regime += 1
                continue
        
        # Enhance with dynamic TP/SL if not present or static
        entry = sig.get('entry_price')
        if entry:
            # Get approximate ATR (use 2% default if no history)
            atr_pct = sig.get('atr_14', 0.02)
            
            # Compute dynamic TP/SL
            tp, sl = _compute_dynamic_tp_sl(
                entry, atr_pct, sig.get('direction', 'BUY'), rr_ratio=1.5
            )
            
            # Only override if TP/SL not set or static (5% flat)
            current_tp = sig.get('tp_price', 0)
            current_sl = sig.get('sl_price', 0)
            
            if current_tp and entry:
                current_rr = abs(current_tp - entry) / abs(entry - current_sl) if current_sl and abs(entry - current_sl) > 1e-9 else 0
                if current_rr < 1.0 or abs(current_tp - entry) / entry == 0.05:  # Static 5%
                    sig['tp_price'] = tp
                    sig['sl_price'] = sl
            else:
                sig['tp_price'] = tp
                sig['sl_price'] = sl
        
        # RR sanity check (after dynamic TP/SL)
        rr = _compute_rr(sig)
        if rr is not None and rr < 1.0:
            skipped_rr += 1
            continue
        
        # Add Kelly-fraction sizing
        if entry and sig.get('tp_price') and sig.get('sl_price'):
            edge = abs(sig['tp_price'] - entry) / entry
            vol = sig.get('volatility_20', 0.50)  # Default 50% annualized
            kelly = _compute_kelly_size(confidence, edge, vol, cap=0.02)
            sig['size_frac'] = kelly
        
        # Add expiry timestamp (15 minutes)
        sig['expires_at'] = (datetime.now(timezone.utc) + 
                            timedelta(minutes=15)).isoformat()
        
        # Add quality filter note
        sig['quality_filter'] = f"ATR-based TP/SL, Kelly size: {sig.get('size_frac', 0):.1%}"

        filtered.append(sig)

    # Apply dynamic volatility-scaled threshold
    base_threshold = 0.60
    for sig in filtered:
        vol_forecast = sig.get('volatility_20', 0.50)
        dynamic_thr = _compute_dynamic_threshold(base_threshold, vol_forecast, vol_target=0.02)
        
        if sig.get('confidence', 0) < dynamic_thr:
            sig['blocked_by_vol_threshold'] = True
            sig['dynamic_threshold'] = dynamic_thr
    
    # Filter out signals below dynamic threshold
    filtered = [s for s in filtered if not s.get('blocked_by_vol_threshold', False)]
    
    # Apply portfolio-level Kelly allocation (correlation-aware)
    filtered = _compute_portfolio_kelly_allocation(filtered, portfolio_value=10000.0)
    
    # Add slippage estimate for low-cap tokens
    for sig in filtered:
        symbol = sig.get('symbol', '')
        market_cap_tier = sig.get('market_cap_tier', 'mid')
        
        # Estimate slippage based on market cap tier
        slippage_estimates = {
            'large': 0.0005,   # 0.05% for BTC/ETH
            'mid': 0.0010,     # 0.10% for SOL, ADA, etc.
            'small': 0.0025,   # 0.25% for low-cap alts
            'micro': 0.0050,   # 0.50% for micro-caps (DOGE, BONK, etc.)
        }
        
        # Auto-detect micro-caps from symbol
        micro_caps = ['DOGE', 'SHIB', 'BONK', 'PEPE', 'FLOKI', 'TURBO', 'NOT', 'MEME']
        if any(mc in symbol.upper() for mc in micro_caps):
            market_cap_tier = 'micro'
        
        sig['slippage_estimate'] = slippage_estimates.get(market_cap_tier, 0.0010)
        
        # Warn if edge < 2x slippage (not worth trading)
        entry = sig.get('entry_price', 0)
        tp = sig.get('tp_price', 0)
        if entry and tp:
            edge = abs(tp - entry) / entry
            if edge < 2 * sig['slippage_estimate']:
                sig['slippage_warning'] = f"Edge {edge:.2%} < 2x slippage {2*sig['slippage_estimate']:.2%}"
    
    # Compute turnover estimate (track daily turnover %)
    total_size = sum(s.get('size_frac', 0) for s in filtered)
    for sig in filtered:
        sig['turnover_contribution'] = sig.get('size_frac', 0) / total_size if total_size > 0 else 0
    
    # Log turnover warning if >10% daily
    if total_size > 0.10:
        print(f"⚠️  High turnover warning: {total_size:.1%} of portfolio (target <10%)")
    
    total_skipped = skipped_rr + skipped_stale + skipped_confidence + skipped_regime
    if total_skipped > 0:
        print(
            f"Safety filters: {total_skipped} signals removed "
            f"(stale={skipped_stale}, bad_rr={skipped_rr}, "
            f"low_conf={skipped_confidence}, regime={skipped_regime}), "
            f"{len(filtered)} remaining"
        )
    
    if filtered:
        print(f"Portfolio allocation: {sum(s.get('size_frac', 0) for s in filtered):.1%} total")

    return filtered


# Cross-run deduplication: only re-send when the signal actually changes
DEDUP_CACHE_PATH = Path("signal_aggregator/data/last_sent_cache.json")
DEDUP_COOLDOWN_MINUTES = 5  # 5 minutes — tightened for volatile crypto markets


def _signal_fingerprint(sig: dict) -> str:
    """Hash the key fields that make a signal unique."""
    key = f"{sig.get('symbol')}|{sig.get('direction')}|{sig.get('entry_price')}|{sig.get('tp_price')}|{sig.get('sl_price')}"
    return hashlib.md5(key.encode()).hexdigest()


def _load_dedup_cache() -> dict:
    """Load the last-sent cache from disk."""
    if DEDUP_CACHE_PATH.exists():
        try:
            return json.loads(DEDUP_CACHE_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_dedup_cache(cache: dict):
    """Persist the dedup cache to disk."""
    DEDUP_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEDUP_CACHE_PATH.write_text(json.dumps(cache, indent=2))


def _filter_duplicates(signals: list[dict]) -> list[dict]:
    """
    Remove signals that are identical to what was last sent.

    A signal is considered a duplicate if:
    - Same symbol + direction + entry + TP + SL (fingerprint match)
    - Last sent less than DEDUP_COOLDOWN_MINUTES ago

    If the price levels changed, the signal is NOT a duplicate.
    """
    cache = _load_dedup_cache()
    now = datetime.now(tz=timezone.utc)
    fresh = []
    skipped = 0

    for sig in signals:
        symbol = sig.get('symbol', '')
        fp = _signal_fingerprint(sig)
        prev = cache.get(symbol)

        if prev and prev.get('fingerprint') == fp:
            # Same signal — check cooldown
            try:
                last_sent_time = datetime.fromisoformat(prev['sent_at'])
                age = (now - last_sent_time).total_seconds() / 60
                if age < DEDUP_COOLDOWN_MINUTES:
                    skipped += 1
                    continue
            except Exception:
                pass  # unparseable timestamp -> treat as expired

        fresh.append(sig)

    if skipped:
        print(f"Dedup filter: {skipped} unchanged signals suppressed (cooldown={DEDUP_COOLDOWN_MINUTES}min)")
    return fresh


def _update_dedup_cache(sent_signals: list[dict]):
    """Update the cache with signals that were actually sent."""
    cache = _load_dedup_cache()
    now = datetime.now(tz=timezone.utc).isoformat()

    for sig in sent_signals:
        symbol = sig.get('symbol', '')
        cache[symbol] = {
            'fingerprint': _signal_fingerprint(sig),
            'sent_at': now,
            'entry': sig.get('entry_price'),
            'tp': sig.get('tp_price'),
            'sl': sig.get('sl_price'),
            'direction': sig.get('direction'),
            'confidence': sig.get('confidence'),
        }

    # Prune entries older than 24h
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(hours=24)).isoformat()
    cache = {k: v for k, v in cache.items() if v.get('sent_at', '') > cutoff}
    _save_dedup_cache(cache)


def _send_no_picks_status(router, sent, *, reason=""):
    """Send a status message to #master-picks when no picks qualify."""
    import os
    import requests as _req
    webhook = os.getenv("DISCORD_MASTER_PICKS", "")
    if not webhook:
        return
    now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fresh_count = sent.get("freshpicks", 0)
    sandbox_count = sent.get("sandbox", 0)
    routed_note = ""
    if fresh_count > 0:
        routed_note = f"\n{fresh_count} signal(s) were routed to #fresh-picks instead (single-system or lower confidence)."
    if sandbox_count > 0:
        routed_note += f"\n{sandbox_count} signal(s) sent to sandbox (experimental)."
    description = (
        "Master-picks requires **>= 2 independent systems agreeing** on the same symbol + direction, "
        "**AND** high enough confidence (>= 80%). This is the quality bar working correctly — "
        "it's better to send nothing than to send low-conviction trades."
        f"{routed_note}"
    )
    if reason:
        description = f"**Reason:** {reason}\n\n{description}"
    embed = {
        "title": "Signal Scan Complete — No Master Picks This Hour",
        "description": description,
        "color": 0x6B7280,  # gray
        "footer": {"text": f"Signal Engine | {now_str}"},
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
    try:
        r = _req.post(webhook, json={"embeds": [embed]}, timeout=10)
        print(f"  [master-picks] Sent 'no picks' status ({r.status_code})")
    except Exception as e:
        print(f"  [master-picks] Failed to send status: {e}")


def send_top_picks():
    """Send top picks to Discord."""
    # --- Circuit breaker pre-send gate ---
    cb_level, cb_reasons = _check_circuit_breaker_pre_send()
    if cb_level in ("RED", "HALT"):
        reason_str = ", ".join(cb_reasons) if cb_reasons else "drawdown/volatility threshold exceeded"
        print(
            f"\n[CIRCUIT BREAKER {cb_level}] Sending BLOCKED. Reasons: {reason_str}\n"
            f"No picks will be sent to Discord until the portfolio recovers."
        )
        _send_no_picks_status(None, {"freshpicks": 0, "sandbox": 0},
                              reason=f"Circuit breaker {cb_level}: {reason_str}")
        return
    if cb_level == "YELLOW":
        reason_str = ", ".join(cb_reasons) if cb_reasons else "elevated drawdown/volatility"
        print(f"[CIRCUIT BREAKER YELLOW] Caution: {reason_str}. Max picks reduced by 50%.")

    router = PicksRouter()

    signals = load_consensus_signals()
    if not signals:
        print("No signals found!")
        _send_no_picks_status(router, {"freshpicks": 0, "sandbox": 0},
                              reason="No consensus signals from any system this hour.")
        return

    pre_filter_count = len(signals)

    # Apply safety filters before sending
    signals = _apply_safety_filters(signals)
    if not signals:
        print("All signals filtered out by safety checks!")
        _send_no_picks_status(router, {"freshpicks": 0, "sandbox": 0},
                              reason=f"{pre_filter_count} signal(s) found but all removed by safety filters (stale, low confidence, bad R:R, or regime mismatch).")
        return

    # Cross-run dedup: suppress unchanged signals
    signals = _filter_duplicates(signals)
    if not signals:
        print("All signals suppressed by dedup filter (no new/changed signals)")
        _send_no_picks_status(router, {"freshpicks": 0, "sandbox": 0},
                              reason=f"{pre_filter_count} signal(s) found but all duplicates of previously sent picks (no price level changes).")
        return

    print(f"Loaded {len(signals)} signals (post-filter, post-dedup)")

    # Show top 10
    print("\n=== TOP 10 SIGNALS ===")
    for i, sig in enumerate(signals[:10], 1):
        channel = router.route_signal(sig)
        print(
            f"{i}. {sig['symbol']} {sig['direction']} "
            f"(conf: {sig['confidence']:.1%}, "
            f"consensus: {sig.get('consensus_count', 1)}/{sig.get('total_systems', 1)})"
            f" -> #{channel}"
        )

    print(f"\n=== SENDING TO DISCORD ===")
    # Use centralized caps from PicksRouter
    caps = PicksRouter.get_max_picks(cb_level)
    if not caps["send_allowed"]:
        print(f"[CIRCUIT BREAKER {cb_level}] All sends blocked")
        return
    max_master = caps["master"]
    max_fresh = caps["fresh"]
    sent = {"master_picks": 0, "freshpicks": 0, "sandbox": 0, "failed": 0}
    actually_sent = []

    for sig in signals:
        channel = router.route_signal(sig)
        if channel == "sandbox":
            sent["sandbox"] += 1
            continue
        if channel == "master_picks" and sent["master_picks"] >= max_master:
            continue
        if channel == "freshpicks" and sent["freshpicks"] >= max_fresh:
            continue

        success = router.send_signal(sig, channel)
        if success:
            sent[channel] += 1
            actually_sent.append(sig)
            print(f"  [OK] {sig['symbol']} to #{channel}")
        else:
            sent["failed"] += 1
            print(f"  [FAIL] {sig['symbol']} to #{channel}")

    # Update dedup cache with successfully sent signals
    if actually_sent:
        _update_dedup_cache(actually_sent)

    print("\nSummary:")
    print(f"  master_picks sent: {sent['master_picks']}")
    print(f"  freshpicks sent:   {sent['freshpicks']}")
    print(f"  sandbox skipped:   {sent['sandbox']}")
    print(f"  failed sends:      {sent['failed']}")

    # Send "no picks" status to #master-picks so users know the system is alive
    if sent["master_picks"] == 0:
        _send_no_picks_status(router, sent)

    print("\nDone!")


if __name__ == '__main__':
    send_top_picks()
