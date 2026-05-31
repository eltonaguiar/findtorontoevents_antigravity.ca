# METHODOLOGY WARNING 2026-05-31: This module filters OUT TIME_EXIT trades (zero-pnl median outcomes) before computing metrics.
# That is survivorship bias by selection. Reported PF/EV/WR are INFLATED 5-30x vs. actual forward outcomes.
# The module's own permutation p-values (commodity p=0.999, crypto_mega p=1.000, crypto_pma p=0.66, forex p=0.41) refute the PROMISING verdict.
# Independent live-DB re-derivation: crypto_mega_mut+genome_mut n=3 closed, mean=-2.49%, WR=0%. The header claims (WR=65.4%, PF=3.33) are not supported.
# Do NOT use for live capital sizing. Research artifact only. See reports/peer_claude-FORCED_RESOLUTION_SURVIVORSHIP_BIAS_2026-05-31.md
"""Per-Asset-Class Winning Strategies with Forced Resolution.

Each strategy is designed to:
  1. Generate high-quality signals (not noise)
  2. Set tight TP/SL to force resolution (no TIME_EXIT at 0%)
  3. Have a clear academic or empirical basis
  4. Be testable via Monte Carlo

Strategies:
  CRYPTO: mega_mutation momentum (WR=65.4%, PF=3.33 on resolved trades)
  FOREX: contrarian SHORT on retail sentiment (WR=52.6%, PF=16.26)
  COMMODITY: COT positioning extreme (WR=66.7%, PF=1.67)
  EQUITY: RSI2 pullback with regime filter (WR=48.3%, PF=1.41)
  ETF: Faber 10-month tactical MA (trend-following)
  BOND: Yield curve mean-reversion
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from alpha_engine.forced_resolution import (
    ForcedResolutionWrapper,
    get_wrapper_for_class,
)

logger = logging.getLogger(__name__)


def generate_crypto_mega_mutation_picks() -> List[Dict[str, Any]]:
    """CRYPTO: mega_mutation momentum strategy.
    
    Based on: DNA mutation engine evolved strategies
    Edge: WR=65.4%, PF=3.33, R:R=1.77 on resolved trades (n=283)
    Forced resolution: 72h max, TP=5%, SL=3%
    """
    wrapper = get_wrapper_for_class('CRYPTO')
    
    # Load current mega_mutation picks from active picks
    active_path = Path("alpha_engine/data/active_picks.json")
    if not active_path.exists():
        return []
    
    data = json.loads(active_path.read_text(encoding="utf-8"))
    picks = data.get("picks", []) if isinstance(data, dict) else data
    
    # Filter to mega_mutation source
    mm_picks = [
        p for p in picks
        if p.get("source_system") in ("mega_mutation", "genome_mutations")
        and p.get("category", "").lower() == "crypto"
    ]
    
    # Apply forced resolution TP/SL
    for pick in mm_picks:
        entry = pick.get("entry_price", 0)
        if entry:
            tpsl = wrapper.set_tp_sl(entry, pick.get("direction", "LONG"))
            pick.update(tpsl)
            pick["forced_resolution"] = True
            pick["strategy_type"] = "crypto_mega_mutation"
    
    return mm_picks


def generate_forex_contrarian_short_picks() -> List[Dict[str, Any]]:
    """FOREX: Contrarian SHORT on retail sentiment.
    
    Based on: Academic literature on retail trader losses (80%+ lose)
    Edge: WR=52.6%, PF=16.26, R:R=14.64 on resolved trades (n=228)
    Sources: myfxbook_retail_contrarian, ig_contrarian_sentiment, non_crypto_consensus
    Forced resolution: 24h max, TP=0.3%, SL=0.2%
    """
    wrapper = get_wrapper_for_class('FOREX')
    
    active_path = Path("alpha_engine/data/active_picks.json")
    if not active_path.exists():
        return []
    
    data = json.loads(active_path.read_text(encoding="utf-8"))
    picks = data.get("picks", []) if isinstance(data, dict) else data
    
    forex_sources = {
        "myfxbook_retail_contrarian",
        "ig_contrarian_sentiment",
        "non_crypto_consensus",
        "forex_rsi2_mean_reversion",
    }
    
    forex_picks = [
        p for p in picks
        if p.get("source_system") in forex_sources
        and p.get("category", "").lower() == "forex"
        and p.get("direction", "").upper() in ("SHORT", "SELL")
    ]
    
    for pick in forex_picks:
        entry = pick.get("entry_price", 0)
        if entry:
            tpsl = wrapper.set_tp_sl(entry, pick.get("direction", "SHORT"))
            pick.update(tpsl)
            pick["forced_resolution"] = True
            pick["strategy_type"] = "forex_contrarian_short"
    
    return forex_picks


def generate_equity_rsi2_pullback_picks() -> List[Dict[str, Any]]:
    """EQUITY: RSI2 pullback with regime filter.
    
    Based on: Connors RSI2 strategy (Larry Connors, "Short Term Trading Strategies That Work")
    Edge: WR=48.3%, PF=1.41, R:R=1.51 on resolved trades (n=58)
    Forced resolution: 72h max, TP=3%, SL=2%
    """
    wrapper = get_wrapper_for_class('EQUITY')
    
    active_path = Path("alpha_engine/data/active_picks.json")
    if not active_path.exists():
        return []
    
    data = json.loads(active_path.read_text(encoding="utf-8"))
    picks = data.get("picks", []) if isinstance(data, dict) else data
    
    equity_picks = [
        p for p in picks
        if p.get("source_system") == "multi_asset_copytrader"
        and p.get("strategy") == "stocks_rsi2_pullback"
        and p.get("category", "").lower() == "equity"
    ]
    
    for pick in equity_picks:
        entry = pick.get("entry_price", 0)
        if entry:
            tpsl = wrapper.set_tp_sl(entry, pick.get("direction", "LONG"))
            pick.update(tpsl)
            pick["forced_resolution"] = True
            pick["strategy_type"] = "equity_rsi2_pullback"
    
    return equity_picks


def generate_etf_faber_picks() -> List[Dict[str, Any]]:
    """ETF: Faber 10-month tactical MA.
    
    Based on: Meb Faber's "A Quantitative Approach to Tactical Asset Allocation"
    Edge: Trend-following on major ETFs (SPY, QQQ, IWM, EEM, GLD)
    Forced resolution: 720h (30d) max, TP=5%, SL=3%
    """
    from alpha_engine.faber_etf_strategy import generate_faber_picks
    
    wrapper = get_wrapper_for_class('ETF')
    picks = generate_faber_picks()
    
    for pick in picks:
        entry = pick.get("entry_price", 0)
        if entry:
            tpsl = wrapper.set_tp_sl(entry, pick.get("direction", "LONG"))
            pick.update(tpsl)
            pick["forced_resolution"] = True
            pick["strategy_type"] = "etf_faber_10mo_ma"
    
    return picks


def generate_commodity_cot_picks() -> List[Dict[str, Any]]:
    """COMMODITY: COT positioning extreme.
    
    Based on: CFTC Commitment of Traders data
    Edge: WR=66.7%, PF=1.67 on resolved trades (n=26)
    Forced resolution: 168h (1wk) max, TP=3%, SL=2%
    """
    wrapper = get_wrapper_for_class('COMMODITY')
    
    active_path = Path("alpha_engine/data/active_picks.json")
    if not active_path.exists():
        return []
    
    data = json.loads(active_path.read_text(encoding="utf-8"))
    picks = data.get("picks", []) if isinstance(data, dict) else data
    
    commodity_picks = [
        p for p in picks
        if p.get("source_system") in ("multi_asset_cot", "cta_replicator")
        and p.get("category", "").lower() == "commodity"
    ]
    
    for pick in commodity_picks:
        entry = pick.get("entry_price", 0)
        if entry:
            tpsl = wrapper.set_tp_sl(entry, pick.get("direction", "LONG"))
            pick.update(tpsl)
            pick["forced_resolution"] = True
            pick["strategy_type"] = "commodity_cot_positioning"
    
    return commodity_picks


def generate_all_winning_picks() -> List[Dict[str, Any]]:
    """Generate picks from ALL winning strategies with forced resolution."""
    all_picks = []
    
    generators = [
        ("crypto_mega_mutation", generate_crypto_mega_mutation_picks),
        ("forex_contrarian_short", generate_forex_contrarian_short_picks),
        ("equity_rsi2_pullback", generate_equity_rsi2_pullback_picks),
        ("etf_faber_10mo", generate_etf_faber_picks),
        ("commodity_cot", generate_commodity_cot_picks),
    ]
    
    for name, gen in generators:
        try:
            picks = gen()
            logger.info(f"{name}: {len(picks)} picks with forced resolution")
            all_picks.extend(picks)
        except Exception as e:
            logger.error(f"{name}: failed — {e}")
    
    # Save
    output_path = Path("alpha_engine/data/forced_resolution_picks.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks": len(all_picks),
        "picks": all_picks,
        "methodology": "forced_resolution_wrapper",
        "configs": {
            "CRYPTO": {"max_hold_hrs": 72, "tp_pct": 5.0, "sl_pct": 3.0},
            "FOREX": {"max_hold_hrs": 24, "tp_pct": 0.3, "sl_pct": 0.2},
            "EQUITY": {"max_hold_hrs": 72, "tp_pct": 3.0, "sl_pct": 2.0},
            "ETF": {"max_hold_hrs": 720, "tp_pct": 5.0, "sl_pct": 3.0},
            "COMMODITY": {"max_hold_hrs": 168, "tp_pct": 3.0, "sl_pct": 2.0},
        },
    }, indent=2), encoding="utf-8")
    
    return all_picks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    picks = generate_all_winning_picks()
    print(f"\nTotal picks with forced resolution: {len(picks)}")
    for p in picks:
        entry = p.get('entry_price', 0)
        tp = p.get('take_profit', 0)
        sl = p.get('stop_loss', 0)
        max_h = p.get('max_hold_hours', 0)
        print(f"  {p.get('symbol', '?'):10s} {p.get('direction', '?'):5s} "
              f"entry={entry:10.2f} TP={tp:10.2f} SL={sl:10.2f} "
              f"max_hold={max_h}h type={p.get('strategy_type', '?')}")
