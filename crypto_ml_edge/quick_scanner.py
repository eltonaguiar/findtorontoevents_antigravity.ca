"""
GSD Quick Scanner — Proven Strategy Aggregator
===============================================
Aggregates signals from battle-tested strategies (Connors RSI-2, Funding Rate,
VIX/Fear Contrarian) into the crypto_ml_edge active_picks.json pipeline.

No ML training required — these strategies have documented statistical edge:
  - Connors RSI-2: 75.7% WR (Connors & Alvarez 2008)
  - Funding Rate Carry: 71% WR (Binance perp anomalies)
  - VIX/Fear Contrarian: 72% WR (capitulation reversal)

Usage:
    from crypto_ml_edge.quick_scanner import quick_scan
    data = quick_scan()  # Returns updated active_picks.json dict
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"

# EST timezone
EST = timezone(timedelta(hours=-5))

# ─── Config ─────────────────────────────────────────────────────────────────
CAPITAL_BASE = 10_000
MAX_CONCURRENT_PICKS = 999  # TESTING SPRINT: was 10, uncapped
# Import from central config to stay in sync with ML scanner
try:
    from crypto_ml_edge.config import CONFIDENCE_THRESHOLD
except ImportError:
    CONFIDENCE_THRESHOLD = 0.70  # fallback if config not importable
MAX_POSITION_PCT = 0.05
MAX_HOLD_BARS = 10  # Mean reversion = 2-5 day hold, 10 bar max forces fast resolution

# Falling knife protection: regime-adaptive threshold based on Fear & Greed
# Normal market: 20% below SMA → reject (likely structural decline)
# Fear (F&G 16-30): 35% → allow deeper dips (recovery plays)
# Extreme fear (F&G ≤15): 50% → nearly disabled (capitulation plays work)
_FALLING_KNIFE_NORMAL = 0.20
_FALLING_KNIFE_FEAR = 0.35
_FALLING_KNIFE_EXTREME = 0.50

def _get_falling_knife_threshold() -> float:
    """Return regime-appropriate falling knife threshold using live F&G."""
    import time as _time
    for attempt in range(3):
        try:
            import requests as _req
            resp = _req.get("https://api.alternative.me/fng/", timeout=5)
            fng = int(resp.json()["data"][0]["value"])
            if fng <= 15:
                return _FALLING_KNIFE_EXTREME
            elif fng <= 30:
                return _FALLING_KNIFE_FEAR
            return _FALLING_KNIFE_NORMAL
        except Exception:
            if attempt < 2:
                _time.sleep(2 * (attempt + 1))
    return _FALLING_KNIFE_NORMAL

# Backwards-compat alias used in normalizers below
MAX_BELOW_SMA_PCT = _get_falling_knife_threshold()

# ─── Strategy imports (deferred to avoid import errors in CI) ────────────────

def _import_connors_rsi2():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from alpha_engine.connors_rsi2 import generate_signals
    return generate_signals

def _import_funding_rate():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from alpha_engine.funding_rate_scanner import run_scan
    return run_scan

def _import_vix_spike():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from alpha_engine.vix_spike_reversal import generate_signals
    return generate_signals


# ─── Symbol mapping ────────────────────────────────────────────────────────

SYMBOL_TO_BINANCE = {
    "BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT", "SOL-USD": "SOLUSDT",
    "BTCUSDT": "BTCUSDT", "ETHUSDT": "ETHUSDT", "SOLUSDT": "SOLUSDT",
    "BNBUSDT": "BNBUSDT", "AVAXUSDT": "AVAXUSDT", "LINKUSDT": "LINKUSDT",
    "DOGEUSDT": "DOGEUSDT", "XRPUSDT": "XRPUSDT", "ADAUSDT": "ADAUSDT",
    "MATICUSDT": "MATICUSDT",
    "SPY": None, "QQQ": None, "IWM": None, "GLD": None, "TLT": None,
}

ASSET_CLASS = {
    "BTC-USD": "Crypto", "ETH-USD": "Crypto", "SOL-USD": "Crypto",
    "BTCUSDT": "Crypto", "ETHUSDT": "Crypto", "SOLUSDT": "Crypto",
    "BNBUSDT": "Crypto", "AVAXUSDT": "Crypto", "LINKUSDT": "Crypto",
    "DOGEUSDT": "Crypto", "XRPUSDT": "Crypto", "ADAUSDT": "Crypto",
    "MATICUSDT": "Crypto",
    "SPY": "ETF", "QQQ": "ETF", "IWM": "ETF",
    "GLD": "ETF", "TLT": "ETF",
}

ASSET_DESCRIPTIONS = {
    "IWM": "Russell 2000 Small-Cap ETF",
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq 100 ETF",
    "GLD": "Gold ETF",
    "TLT": "20+ Year Treasury Bond ETF",
}

BINANCE_TRACKABLE = {v for v in SYMBOL_TO_BINANCE.values() if v is not None}


# ─── Helpers ────────────────────────────────────────────────────────────────

def _now_est() -> str:
    return datetime.now(EST).strftime("%Y-%m-%d %I:%M:%S %p EST")

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _make_pick_id(strategy_id: str, symbol: str) -> str:
    date_str = datetime.now(EST).strftime("%Y-%m-%d")
    return f"{strategy_id}::{symbol}::{date_str}"

def _assign_tier(confidence: float, risk_reward: float) -> str:
    if confidence >= 0.75 and risk_reward >= 1.5:
        return "HIGH"
    elif confidence >= 0.65:
        return "MEDIUM"
    else:
        return "WATCH"

def _compute_position_size(confidence: float, capital: float) -> dict:
    if confidence < CONFIDENCE_THRESHOLD:
        return {"position_size_usd": 0.0, "position_size_pct": 0.0}
    base_pct = 0.02 + (confidence - 0.60) * 0.12
    pct = min(base_pct, MAX_POSITION_PCT)
    usd = round(pct * capital, 2)
    return {"position_size_usd": usd, "position_size_pct": round(pct, 6)}


# ─── Normalizers ────────────────────────────────────────────────────────────

def normalize_connors_signal(sig: dict) -> Optional[dict]:
    symbol = sig.get("symbol", "")
    binance_pair = SYMBOL_TO_BINANCE.get(symbol)
    entry = sig.get("entry_price")
    confidence = sig.get("confidence", 0)
    if not entry or confidence < CONFIDENCE_THRESHOLD:
        return None

    # --- Falling knife protection (regime-adaptive) ---
    # Threshold widens during extreme fear (capitulation plays have 72% WR historically)
    sma200 = sig.get("sma200", 0)
    fk_threshold = MAX_BELOW_SMA_PCT  # Already regime-adaptive via _get_falling_knife_threshold()
    if sma200 and entry > 0 and sig.get("above_200sma") is False:
        pct_below = (sma200 - entry) / sma200
        if pct_below > fk_threshold:
            logger.info(
                "REJECTED %s: %.1f%% below 200 SMA (threshold %.0f%%) — falling knife protection",
                symbol, pct_below * 100, fk_threshold * 100,
            )
            return None

    direction = "long" if sig.get("signal_type") == "BUY" else "short"
    atr_val = sig.get("atr", 0)

    # --- Override TP/SL for mean reversion reality ---
    # Connors RSI-2 captures 2-5 day bounces, not trend reversals
    # Crypto: tighter targets (high volatility, fast moves)
    # ETF: even tighter (lower volatility, more efficient)
    asset_cls = ASSET_CLASS.get(symbol, "Crypto")
    if asset_cls == "Crypto":
        tp_mult = 1.2   # 1.2x ATR TP (~3-5% for BTC/ETH)
        sl_mult = 1.0   # 1.0x ATR SL (~2.5-4%)
    else:
        tp_mult = 1.5   # 1.5x ATR TP (~1.5-2% for ETFs)
        sl_mult = 1.0   # 1.0x ATR SL (~1%)

    if atr_val > 0 and entry > 0:
        if direction == "long":
            tp = entry + tp_mult * atr_val
            sl = entry - sl_mult * atr_val
        else:
            tp = entry - tp_mult * atr_val
            sl = entry + sl_mult * atr_val
        rr = round(tp_mult / sl_mult, 2)
    else:
        tp = sig.get("take_profit", 0)
        sl = sig.get("stop_loss", 0)
        rr = sig.get("risk_reward", 0)

    sizing = _compute_position_size(confidence, CAPITAL_BASE)
    if sizing["position_size_usd"] <= 0:
        return None

    reasons = []
    if sig.get("rsi2") is not None:
        label = "EXTREME OVERSOLD" if sig["rsi2"] < 5 else "OVERSOLD" if sig["rsi2"] < 10 else "OVERBOUGHT"
        reasons.append(f"RSI-2 = {sig['rsi2']:.1f} ({label}, threshold < 5)")
    if sig.get("connors_rsi") is not None:
        if sig["connors_rsi"] < 10:
            reasons.append(f"Connors RSI = {sig['connors_rsi']:.1f} (below 10 buy threshold)")
        else:
            reasons.append(f"Connors RSI = {sig['connors_rsi']:.1f}")
    if sig.get("above_200sma") is not None:
        trend = sig.get("trend", "UNKNOWN")
        reasons.append(f"{'Above' if sig['above_200sma'] else 'Below'} 200-day SMA (trend: {trend})")
    if sig.get("reason"):
        reasons.append(sig["reason"])

    conf_factors = ["Base confidence: 0.73"]
    if sig.get("connors_rsi", 100) < 10:
        conf_factors.append("CRSI < 10 bonus: +0.07")
    if sig.get("above_200sma") is False:
        conf_factors.append("Below 200 SMA penalty: -0.10")

    asset_cls = ASSET_CLASS.get(symbol, "Crypto")
    asset_desc = ASSET_DESCRIPTIONS.get(symbol)

    return {
        "id": _make_pick_id("connors_rsi2", symbol),
        "symbol": symbol,
        "pair": binance_pair or symbol,
        "symbol_display": symbol,
        "asset_class": asset_cls,
        "asset_description": asset_desc,
        "timeframe": "1d",
        "direction": direction,
        "confidence": round(confidence, 4),
        "tier": _assign_tier(confidence, rr),
        "entry_price": round(entry, 8),
        "tp_price": round(tp, 8) if tp else None,
        "sl_price": round(sl, 8) if sl else None,
        "position_size_usd": sizing["position_size_usd"],
        "position_size_pct": sizing["position_size_pct"],
        "risk_reward_ratio": round(rr, 3) if rr else 0.0,
        "max_hold_bars": MAX_HOLD_BARS,
        "signal_time": _now_utc_iso(),
        "signal_time_est": _now_est(),
        "source": "quick_engine",
        "status": "active",
        "bars_held": 0,
        "audit": {
            "strategy_id": "connors_rsi2",
            "strategy_name": "Connors RSI-2 Mean Reversion",
            "reasons": reasons,
            "academic_source": sig.get("academic_source", "Connors & Alvarez (2008) -- 75.7% WR on SPY backtest"),
            "market_regime": sig.get("trend", "unknown").lower(),
            "strategy_indicators": {
                k: round(v, 4) if isinstance(v, float) else v
                for k, v in sig.items()
                if k in ("rsi2", "connors_rsi", "atr", "sma200")
            },
            "confidence_factors": conf_factors,
        },
    }


def normalize_funding_signal(sig: dict) -> Optional[dict]:
    if sig.get("signal") != "BUY":
        return None

    symbol = sig.get("symbol", "")
    entry = sig.get("entry_price")
    confidence = sig.get("confidence", 0)
    if not entry or confidence < CONFIDENCE_THRESHOLD:
        return None

    tp = sig.get("take_profit")
    sl = sig.get("stop_loss")
    tp_pct = sig.get("tp_pct", 0)
    sl_pct = sig.get("sl_pct", 0)
    rr = round(tp_pct / sl_pct, 2) if sl_pct > 0 else 0.0

    sizing = _compute_position_size(confidence, CAPITAL_BASE)
    if sizing["position_size_usd"] <= 0:
        return None

    rate = sig.get("funding_rate_pct", 0)
    ann = sig.get("ann_rate_pct", 0)
    reasons = [sig.get("reason", "Negative funding rate detected")]
    reasons.append(f"Funding rate: {rate:.4f}% per 8h ({ann:.1f}% annualized)")
    if rate < -0.05:
        reasons.append("EXTREME negative funding -- shorts are paying longs heavily")
    elif rate < -0.01:
        reasons.append("Moderate negative funding -- shorts paying longs")

    return {
        "id": _make_pick_id("funding_rate", symbol),
        "symbol": symbol,
        "pair": symbol,
        "symbol_display": symbol,
        "asset_class": ASSET_CLASS.get(symbol, "Crypto"),
        "timeframe": "8h",
        "direction": "long",
        "confidence": round(confidence, 4),
        "tier": _assign_tier(confidence, rr),
        "entry_price": round(entry, 8),
        "tp_price": round(tp, 8) if tp else None,
        "sl_price": round(sl, 8) if sl else None,
        "position_size_usd": sizing["position_size_usd"],
        "position_size_pct": sizing["position_size_pct"],
        "risk_reward_ratio": rr,
        "max_hold_bars": MAX_HOLD_BARS,
        "signal_time": _now_utc_iso(),
        "signal_time_est": _now_est(),
        "source": "quick_engine",
        "status": "active",
        "bars_held": 0,
        "audit": {
            "strategy_id": "funding_rate",
            "strategy_name": "Funding Rate Carry Trade",
            "reasons": reasons,
            "academic_source": "Binance funding rate anomaly -- 71% WR on negative funding carry",
            "market_regime": "unknown",
            "strategy_indicators": {"funding_rate_pct": rate, "ann_rate_pct": ann},
            "confidence_factors": [
                f"Funding rate: {rate:.4f}%/8h",
                f"Confidence: {'0.85 (extreme negative <-0.05%)' if rate < -0.05 else '0.65 (moderate negative)'}",
            ],
        },
    }


def normalize_vix_signal(sig: dict) -> Optional[dict]:
    symbol = sig.get("symbol", "")
    binance_pair = SYMBOL_TO_BINANCE.get(symbol)
    entry = sig.get("entry_price")
    confidence = sig.get("confidence", 0)
    if not entry or confidence < CONFIDENCE_THRESHOLD:
        return None

    # --- Falling knife protection (regime-adaptive) ---
    # In extreme fear (F&G ≤15), widen threshold to 50% — capitulation recoveries are valid.
    # In normal markets, keep 20% to block structural decline entries.
    sma200 = sig.get("sma200", 0)
    fk_threshold = MAX_BELOW_SMA_PCT  # Already regime-adaptive
    if sma200 and entry > 0:
        pct_below = (sma200 - entry) / sma200
        if pct_below > fk_threshold:
            logger.info(
                "REJECTED %s (F&G): %.1f%% below 200 SMA (threshold %.0f%%) — falling knife",
                symbol, pct_below * 100, fk_threshold * 100,
            )
            return None

    tp = sig.get("take_profit", 0)
    sl = sig.get("stop_loss", 0)
    rr = sig.get("risk_reward", 0)

    sizing = _compute_position_size(confidence, CAPITAL_BASE)
    if sizing["position_size_usd"] <= 0:
        return None

    subtype = sig.get("signal_subtype", "unknown")
    reasons = [sig.get("reason", f"VIX/Fear signal ({subtype})")]
    if sig.get("vix_level"):
        reasons.append(f"VIX level: {sig['vix_level']:.1f}")
    if sig.get("vix_spike_pct"):
        reasons.append(f"VIX 1-day spike: +{sig['vix_spike_pct']:.1f}%")
    if sig.get("fear_greed_index") is not None:
        fg = sig["fear_greed_index"]
        reasons.append(f"Fear & Greed Index: {fg} ({sig.get('fg_classification', 'Extreme Fear')})")
        if fg <= 15:
            reasons.append("EXTREME FEAR -- historically every F&G < 15 preceded recovery")
    if sig.get("spy_rsi2") is not None:
        reasons.append(f"SPY RSI-2: {sig['spy_rsi2']:.1f}")

    indicators = {}
    for k in ("vix_level", "vix_spike_pct", "fear_greed_index", "spy_rsi2", "spy_above_200sma"):
        if sig.get(k) is not None:
            indicators[k] = sig[k]

    asset_cls = ASSET_CLASS.get(symbol, "Crypto")
    asset_desc = ASSET_DESCRIPTIONS.get(symbol)

    return {
        "id": _make_pick_id(f"vix_{subtype}", symbol),
        "symbol": symbol,
        "pair": binance_pair or symbol,
        "symbol_display": symbol,
        "asset_class": asset_cls,
        "asset_description": asset_desc,
        "timeframe": "1d",
        "direction": "long",
        "confidence": round(confidence, 4),
        "tier": _assign_tier(confidence, rr),
        "entry_price": round(entry, 8),
        "tp_price": round(tp, 8) if tp else None,
        "sl_price": round(sl, 8) if sl else None,
        "position_size_usd": sizing["position_size_usd"],
        "position_size_pct": sizing["position_size_pct"],
        "risk_reward_ratio": round(rr, 3) if rr else 0.0,
        "max_hold_bars": MAX_HOLD_BARS,
        "signal_time": _now_utc_iso(),
        "signal_time_est": _now_est(),
        "source": "quick_engine",
        "status": "active",
        "bars_held": 0,
        "audit": {
            "strategy_id": f"vix_{subtype}",
            "strategy_name": f"VIX/Fear Reversal ({subtype.replace('_', ' ').title()})",
            "reasons": reasons,
            "academic_source": sig.get("academic_source", "Fear & Greed contrarian -- 72% WR at extreme fear"),
            "market_regime": "extreme_fear" if sig.get("fear_greed_index", 100) < 25 else "normal",
            "strategy_indicators": indicators,
            "confidence_factors": [f"Base confidence: {confidence:.2f}", f"Signal subtype: {subtype}"],
        },
    }


# ─── Deduplication ──────────────────────────────────────────────────────────

def _is_duplicate(pick: dict, existing_picks: list) -> bool:
    pick_id = pick.get("id", "")
    for ep in existing_picks:
        if ep.get("id") == pick_id:
            return True
        if (ep.get("pair") == pick.get("pair") and
            ep.get("direction") == pick.get("direction") and
            ep.get("status") == "active"):
            return True
    return False


# ─── JSON persistence ──────────────────────────────────────────────────────

def _load_picks_json() -> dict:
    default = {
        "generated_at": "",
        "engine_version": "1.2.0-quick",
        "capital_base": CAPITAL_BASE,
        "picks": [],
        "closed_picks": [],
        "gainer_picks": [],
        "performance": {
            "total_picks": 0, "wins": 0, "losses": 0, "timeouts": 0,
            "win_rate": 0.0, "total_return_pct": 0.0, "sharpe_estimate": 0.0,
        },
        "gainer_performance": {
            "total_picks": 0, "wins": 0, "losses": 0, "timeouts": 0,
            "win_rate": 0.0, "total_return_pct": 0.0,
        },
        "model_health": {
            "models_loaded": 0, "last_training": None, "last_scan": None,
            "dsr_pass_count": 0, "dsr_fail_count": 0,
        },
        "quick_engine": {
            "strategies_active": 3,
            "last_scan_est": None,
            "strategy_counts": {},
        },
    }
    if not ACTIVE_PICKS_PATH.exists():
        return default
    try:
        with open(ACTIVE_PICKS_PATH, "r") as f:
            data = json.load(f)
        for key in default:
            if key not in data:
                data[key] = default[key]
        return data
    except Exception as e:
        logger.warning("Failed to load %s: %s", ACTIVE_PICKS_PATH, e)
        return default


def _save_picks_json(data: dict) -> None:
    data["generated_at"] = _now_utc_iso()
    data["engine_version"] = "1.2.0-quick"
    data["capital_base"] = CAPITAL_BASE
    ACTIVE_PICKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = ACTIVE_PICKS_PATH.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
        tmp.replace(ACTIVE_PICKS_PATH)
    except Exception as e:
        logger.error("Save failed: %s", e)
        try:
            with open(ACTIVE_PICKS_PATH, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e2:
            logger.error("Fallback save failed: %s", e2)


# ─── Main scan function ────────────────────────────────────────────────────

def quick_scan(dry_run: bool = False) -> dict:
    t0 = time.time()
    scan_time_est = _now_est()
    logger.info("=== QUICK SCAN START === %s", scan_time_est)

    data = _load_picks_json()
    existing_picks = data.get("picks", []) + data.get("closed_picks", [])
    new_picks = []
    strategy_counts = {}
    errors = []

    # Strategy 1: Connors RSI-2
    try:
        generate_connors = _import_connors_rsi2()
        signals = generate_connors(verbose=False)
        logger.info("Connors RSI-2: %d raw signals", len(signals))
        for sig in signals:
            pick = normalize_connors_signal(sig)
            if pick and not _is_duplicate(pick, existing_picks + new_picks):
                new_picks.append(pick)
                strategy_counts["connors_rsi2"] = strategy_counts.get("connors_rsi2", 0) + 1
    except Exception as e:
        logger.error("Connors RSI-2 failed: %s", e)
        errors.append(f"connors_rsi2: {e}")

    # Strategy 2: Funding Rate Carry
    try:
        run_funding = _import_funding_rate()
        signals = run_funding(verbose=False)
        logger.info("Funding Rate: %d raw signals", len(signals))
        for sig in signals:
            pick = normalize_funding_signal(sig)
            if pick and not _is_duplicate(pick, existing_picks + new_picks):
                new_picks.append(pick)
                strategy_counts["funding_rate"] = strategy_counts.get("funding_rate", 0) + 1
    except Exception as e:
        logger.error("Funding Rate failed: %s", e)
        errors.append(f"funding_rate: {e}")

    # Strategy 3: VIX / Fear Reversal
    try:
        generate_vix = _import_vix_spike()
        signals = generate_vix(verbose=False)
        logger.info("VIX/Fear: %d raw signals", len(signals))
        for sig in signals:
            pick = normalize_vix_signal(sig)
            if pick and not _is_duplicate(pick, existing_picks + new_picks):
                new_picks.append(pick)
                strategy_counts["vix_fear"] = strategy_counts.get("vix_fear", 0) + 1
    except Exception as e:
        logger.error("VIX/Fear failed: %s", e)
        errors.append(f"vix_fear: {e}")

    # Sort by confidence, limit by slots
    new_picks.sort(key=lambda p: p.get("confidence", 0), reverse=True)
    current_active = len(data.get("picks", []))
    slots = MAX_CONCURRENT_PICKS - current_active
    if slots < len(new_picks):
        logger.info("Limiting to %d new picks (slots available)", slots)
        new_picks = new_picks[:max(slots, 0)]

    # Merge
    data["picks"] = data.get("picks", []) + new_picks
    data["quick_engine"] = {
        "strategies_active": 3 - len(errors),
        "last_scan_est": scan_time_est,
        "last_scan_utc": _now_utc_iso(),
        "strategy_counts": strategy_counts,
        "errors": errors if errors else None,
    }
    # Update model_health from trained models
    model_health = data.setdefault("model_health", {})
    model_health["last_scan"] = _now_utc_iso()
    try:
        models_dir = BASE_DIR / "models"
        if models_dir.exists():
            meta_files = list(models_dir.glob("*_meta.json"))
            pass_count = 0
            fail_count = 0
            last_train = None
            for mf in meta_files:
                try:
                    import json as _json
                    with open(mf) as _mfh:
                        meta = _json.load(_mfh)
                    v = meta.get("validation", {})
                    if v.get("verdict") == "PASS":
                        pass_count += 1
                    else:
                        fail_count += 1
                    ts = meta.get("trained_at")
                    if ts and (last_train is None or ts > last_train):
                        last_train = ts
                except Exception:
                    continue
            model_health["models_loaded"] = pass_count
            model_health["dsr_pass_count"] = pass_count
            model_health["dsr_fail_count"] = fail_count
            if last_train:
                model_health["last_training"] = last_train
    except Exception:
        pass

    if not dry_run:
        _save_picks_json(data)

    elapsed = round(time.time() - t0, 1)
    logger.info(
        "=== QUICK SCAN END === %.1fs | %d new picks | %d total active | strategies: %s | errors: %s",
        elapsed, len(new_picks), len(data["picks"]), strategy_counts, errors or "none",
    )
    return data


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    import argparse
    parser = argparse.ArgumentParser(description="GSD Quick Scanner")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to disk")
    args = parser.parse_args()

    data = quick_scan(dry_run=args.dry_run)
    picks = data.get("picks", [])
    quick = data.get("quick_engine", {})

    print(f"\nGSD Quick Scan Complete ({quick.get('last_scan_est', '?')})")
    print(f"  New picks: {sum(quick.get('strategy_counts', {}).values())}")
    print(f"  Total active: {len(picks)}")
    print(f"  Strategies: {quick.get('strategy_counts', {})}")
    if quick.get("errors"):
        print(f"  Errors: {quick['errors']}")

    for p in picks:
        audit = p.get("audit", {})
        print(f"\n  [{p.get('tier','?')}] {p.get('pair')} {p.get('direction','?').upper()} "
              f"| Conf: {p.get('confidence',0):.1%} | Entry: ${p.get('entry_price',0):,.2f} "
              f"| TP: ${p.get('tp_price',0):,.2f} | SL: ${p.get('sl_price',0):,.2f}")
        print(f"    Strategy: {audit.get('strategy_name', '?')}")
        for r in audit.get("reasons", [])[:3]:
            print(f"    - {r}")


if __name__ == "__main__":
    main()
