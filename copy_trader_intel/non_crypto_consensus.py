#!/usr/bin/env python3
"""
Non-Crypto Consensus Engine
============================
Aggregates non-crypto picks from multiple independent sources and applies
consensus voting: only promotes picks where ≥2 independent sources agree
on direction for the same symbol.

Sources:
- CTA replicator strategies (copy_trader_intel/cta_strategy_replicator.py)
- Alpha engine forex/equity strategies (forex_strategies.py, equity_strategies.py)
- IG/DailyFX contrarian sentiment (multi_asset_copytrader_scraper.py)
- Copy trader picks (data/forex_copytrader_picks.json)

Output: data/non_crypto_consensus_picks.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"

# Historical quality-gate thresholds for non-crypto sources.
MIN_STRATEGY_TRADES = 20
MIN_STRATEGY_WR = 0.35
MIN_SYMBOL_TRADES = 30
MIN_SYMBOL_WR = 0.30


def _is_non_crypto_pick(pick: dict) -> bool:
    cat = str(pick.get("category", "")).lower()
    asset = str(pick.get("asset_class", pick.get("category", ""))).upper()
    return cat in {"equity", "forex", "commodity", "futures", "bond", "etf", "index"} or asset in {
        "EQUITY", "FOREX", "COMMODITY", "FUTURES", "BOND", "ETF", "INDEX"
    }


def _load_quality_blocks() -> tuple[set[str], set[str]]:
    """Build strategy and symbol blocklists from historical non-crypto closed picks."""
    if not PAYLOAD_PATH.exists():
        return set(), set()

    try:
        with open(PAYLOAD_PATH, encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return set(), set()

    closed = payload.get("picks", {}).get("recent_closed", []) if isinstance(payload, dict) else []
    if not isinstance(closed, list):
        return set(), set()

    strat_stats = defaultdict(lambda: {"wins": 0, "total": 0})
    symbol_stats = defaultdict(lambda: {"wins": 0, "total": 0})

    for pick in closed:
        if not isinstance(pick, dict) or not _is_non_crypto_pick(pick):
            continue

        strategy = str(pick.get("strategy", "")).strip()
        symbol = str(pick.get("symbol", "")).strip().upper()
        try:
            pnl = float(pick.get("pnl_pct", pick.get("realized_pnl_pct", 0)) or 0)
        except Exception:
            pnl = 0.0
        win = pnl > 0

        if strategy:
            strat_stats[strategy]["total"] += 1
            if win:
                strat_stats[strategy]["wins"] += 1
        if symbol:
            symbol_stats[symbol]["total"] += 1
            if win:
                symbol_stats[symbol]["wins"] += 1

    blocked_strategies = {
        s for s, st in strat_stats.items()
        if st["total"] >= MIN_STRATEGY_TRADES and (st["wins"] / st["total"]) < MIN_STRATEGY_WR
    }
    blocked_symbols = {
        s for s, st in symbol_stats.items()
        if st["total"] >= MIN_SYMBOL_TRADES and (st["wins"] / st["total"]) < MIN_SYMBOL_WR
    }
    return blocked_strategies, blocked_symbols


def _apply_quality_gate(picks: list[dict], blocked_strategies: set[str], blocked_symbols: set[str]) -> tuple[list[dict], dict]:
    """Filter picks that historically underperform in non-crypto closed-pick data."""
    kept = []
    dropped = {"strategy": 0, "symbol": 0}
    for pick in picks:
        strategy = str(pick.get("strategy", "")).strip()
        symbol = str(pick.get("symbol", "")).strip().upper()
        if strategy and strategy in blocked_strategies:
            dropped["strategy"] += 1
            continue
        if symbol and symbol in blocked_symbols:
            dropped["symbol"] += 1
            continue
        kept.append(pick)
    return kept, dropped


def load_json_picks(filepath: Path) -> list[dict]:
    """Load picks from a JSON file, return empty list on failure.

    Accepts two shapes for backward compat across the pipeline:
      - legacy list:  [pick, pick, ...]
      - new dict:     {"picks": [pick, ...], "timestamp": ..., ...}
    Cherry-picked from PR #243 (skeleton only — the non_crypto_copytrader
    source-4 wiring from that PR was dropped; this helper is standalone).
    """
    if not filepath.exists():
        return []
    try:
        with open(filepath) as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("picks", [])
        return []
    except Exception:
        return []


def _min_agreement_for_pick(pick: dict, default: int = 2) -> int:
    """Return per-asset-class minimum agreement threshold.
    
    2026-05-14 swarm audit: FOREX has only ~3 active strategies vs crypto's 20+.
    Requiring 2/3 agreement (67%) for forex is disproportionately strict compared
    to crypto's 2/20 (10%). ETF/BOND have even fewer — any agreement is meaningful.
    COMMODITY and EQUITY stay at 2 (more strategies available).
    """
    ac = str(pick.get("asset_class", pick.get("category", ""))).upper()
    return {
        "FOREX": 1,
        "BOND": 1,
        "ETF": 1,
    }.get(ac, default)


def consensus_vote(all_picks: list[dict], min_agreement: int = 2) -> list[dict]:
    """
    Aggregate picks by symbol and apply consensus voting with per-class thresholds.

    For each symbol:
    - Count BUY votes and SELL votes from independent strategies
    - Minimum agreement threshold varies by asset class (FOREX/BOND/ETF=1, others=2)
    - If BUY votes >= min_agreement and > SELL votes: emit BUY with boosted confidence
    - If SELL votes >= min_agreement and > BUY votes: emit SELL with boosted confidence
    - Otherwise: no consensus, drop symbol

    Returns list of consensus picks with agreement metadata.
    """
    # Group by symbol
    symbol_votes: dict[str, dict] = defaultdict(lambda: {
        "buy_picks": [], "sell_picks": [],
        "buy_strategies": set(), "sell_strategies": set()
    })

    for pick in all_picks:
        symbol = pick.get("symbol", "")
        sig_type = str(pick.get("signal_type", pick.get("direction", ""))).upper()
        strategy = pick.get("strategy", "unknown")

        if sig_type in ("BUY", "LONG"):
            symbol_votes[symbol]["buy_picks"].append(pick)
            symbol_votes[symbol]["buy_strategies"].add(strategy)
        elif sig_type in ("SELL", "SHORT"):
            symbol_votes[symbol]["sell_picks"].append(pick)
            symbol_votes[symbol]["sell_strategies"].add(strategy)

    consensus_picks = []
    for symbol, votes in symbol_votes.items():
        n_buy = len(votes["buy_strategies"])
        n_sell = len(votes["sell_strategies"])
        # Use the most permissive threshold across all picks for this symbol
        symbol_min = min(
            _min_agreement_for_pick(p, min_agreement)
            for side in ("buy_picks", "sell_picks")
            for p in votes[side]
        ) if (votes["buy_picks"] or votes["sell_picks"]) else min_agreement

        if n_buy >= symbol_min and n_buy > n_sell:
            # Consensus BUY - pick the highest confidence BUY signal
            best = max(votes["buy_picks"], key=lambda p: p.get("confidence", 0))
            consensus_pick = _build_consensus_pick(
                best, symbol, "BUY", n_buy, n_sell,
                list(votes["buy_strategies"])
            )
            consensus_picks.append(consensus_pick)

        elif n_sell >= symbol_min and n_sell > n_buy:
            # Consensus SELL - pick the highest confidence SELL signal
            best = max(votes["sell_picks"], key=lambda p: p.get("confidence", 0))
            consensus_pick = _build_consensus_pick(
                best, symbol, "SELL", n_sell, n_buy,
                list(votes["sell_strategies"])
            )
            consensus_picks.append(consensus_pick)
        # else: no consensus, symbol is dropped

    return consensus_picks


def _build_consensus_pick(
    best_pick: dict, symbol: str, direction: str,
    agree_count: int, disagree_count: int,
    agreeing_strategies: list[str]
) -> dict:
    """Build a consensus pick with enriched metadata."""
    base_conf = best_pick.get("confidence", 0.6)
    # Boost confidence by ~5% per agreeing strategy (capped at 0.85)
    consensus_conf = min(0.85, base_conf + 0.05 * (agree_count - 1))

    return {
        "id": f"consensus_{symbol}_{direction}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}",
        "strategy": f"non_crypto_consensus",
        "symbol": symbol,
        "category": best_pick.get("category", "unknown"),
        "asset_class": best_pick.get("asset_class", best_pick.get("category", "unknown")).upper(),
        "signal_type": direction,
        "direction": "LONG" if direction == "BUY" else "SHORT",
        "entry_price": best_pick.get("entry_price"),
        "take_profit": best_pick.get("take_profit"),
        "stop_loss": best_pick.get("stop_loss"),
        "confidence": round(consensus_conf, 3),
        "risk_reward": best_pick.get("risk_reward", 1.0),
        "reason": (
            f"[Consensus {agree_count}v{disagree_count}] "
            f"Strategies: {', '.join(agreeing_strategies[:5])}. "
            f"Original: {best_pick.get('reason', '')[:200]}"
        ),
        "status": "OPEN",
        "forward_validated": False,
        "forward_test_only": True,
        "source_system": "non_crypto_consensus",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "extra": {
            "consensus_direction": direction,
            "agree_count": agree_count,
            "disagree_count": disagree_count,
            "agreeing_strategies": agreeing_strategies,
            "base_confidence": base_conf,
            "consensus_boost": round(consensus_conf - base_conf, 3),
        },
    }


def run_consensus() -> list[dict]:
    """Load picks from all sources and run consensus voting."""
    all_picks = []

    # Source 1: CTA replicator picks
    cta_path = DATA_DIR / "cta_picks.json"
    cta_picks = load_json_picks(cta_path)
    all_picks.extend(cta_picks)

    # Source 2: Forex copytrader picks
    forex_ct_path = DATA_DIR / "forex_copytrader_picks.json"
    forex_picks = load_json_picks(forex_ct_path)
    all_picks.extend(forex_picks)

    # Source 3: Multi-asset picks
    multi_picks_path = DATA_DIR / "multi_asset_picks.json"
    multi_picks = load_json_picks(multi_picks_path)
    all_picks.extend(multi_picks)

    # Source 4: Commodities picks
    # Filename was "commodities_copytrader_picks.json" — typo: scraper writes
    # "commodity_copytrader_picks.json" (singular). Fixed 2026-04-18.
    commodity_path = DATA_DIR / "commodity_copytrader_picks.json"
    commodity_picks = load_json_picks(commodity_path)
    all_picks.extend(commodity_picks)

    # Source 5: Equity picks
    # Filename was "equity_copytrader_picks.json" — typo: scraper writes
    # "stocks_copytrader_picks.json". Fixed 2026-04-18.
    equity_path = DATA_DIR / "stocks_copytrader_picks.json"
    equity_picks = load_json_picks(equity_path)
    all_picks.extend(equity_picks)

    # Source 6: Futures picks (loader missing entirely until 2026-04-18 —
    # the file has been generated by okx_futures_scraper.py for some time
    # but was never being read into consensus aggregation).
    futures_path = DATA_DIR / "futures_copytrader_picks.json"
    futures_picks = load_json_picks(futures_path)
    all_picks.extend(futures_picks)

    if not all_picks:
        print("[consensus] No picks found from any source")
        return []

    blocked_strategies, blocked_symbols = _load_quality_blocks()
    gated_picks, dropped = _apply_quality_gate(all_picks, blocked_strategies, blocked_symbols)

    print(
        f"[consensus] Loaded {len(all_picks)} total picks from "
        f"CTA({len(cta_picks)}) + ForexCT({len(forex_picks)}) + "
        f"Multi({len(multi_picks)}) + Commodity({len(commodity_picks)}) + "
        f"Equity({len(equity_picks)}) + Futures({len(futures_picks)})"
    )
    print(
        f"[consensus] Quality gate dropped {dropped['strategy']} strategy-blocked + {dropped['symbol']} symbol-blocked picks "
        f"(blocked_strategies={len(blocked_strategies)}, blocked_symbols={len(blocked_symbols)})"
    )
    if blocked_strategies:
        sample_strategies = ", ".join(sorted(list(blocked_strategies))[:8])
        print(f"[consensus] Blocked strategy sample: {sample_strategies}")
    if blocked_symbols:
        sample_symbols = ", ".join(sorted(list(blocked_symbols))[:8])
        print(f"[consensus] Blocked symbol sample: {sample_symbols}")

    # Run consensus voting (require ≥2 independent strategies to agree)
    consensus = consensus_vote(gated_picks, min_agreement=2)

    print(f"[consensus] {len(consensus)} consensus picks generated "
            f"from {len(gated_picks)} gated picks ({len(all_picks)} raw)")

    # Save consensus picks
    output_path = DATA_DIR / "non_crypto_consensus_picks.json"
    with open(output_path, "w") as f:
        json.dump(consensus, f, indent=2, default=str)
    print(f"[consensus] Saved to {output_path}")

    return consensus


if __name__ == "__main__":
    results = run_consensus()
    for pick in results:
        extra = pick.get("extra", {})
        print(f"  {pick['symbol']}: {pick['signal_type']} "
              f"(conf={pick['confidence']:.3f}, "
              f"agree={extra.get('agree_count', 0)}v{extra.get('disagree_count', 0)}, "
              f"strategies={extra.get('agreeing_strategies', [])})")
