"""
Prediction Market Consensus Engine — Multi-Asset

Builds high-conviction signals when independent prediction-market categories
agree across crypto, equities, commodities, forex, and macro events:

- Polymarket wallet copy signals from proven traders
- Reverse-engineered Polymarket market signals
- Kalshi market consensus

This is intentionally stricter than the raw source feeds. The goal is not to
emit every market view; it is to surface the overlap between proven wallets and
prediction-market structure.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_FILE = DATA_DIR / "prediction_market_picks.json"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"

POLYMARKET_WALLET_PICKS = ROOT_DIR / "copy_trader_intel" / "data" / "polymarket_picks.json"
POLYMARKET_SIGNAL_FILE = DATA_DIR / "polymarket_signals.json"
KALSHI_SIGNAL_FILE = DATA_DIR / "kalshi_signals.json"

MIN_CONFIDENCE = 0.55  # Lowered from 0.60 — was filtering 80%+ of valid PM signals (Kimi K6)
MAX_CONFIDENCE = 0.95  # Raised from 0.90 — high-conf PM signals are often correct
MIN_SOURCE_CATEGORIES = 2
MIN_SCORE_GAP = 0.08

SOURCE_WEIGHTS = {
    "wallet_copy": 1.00,
    "kalshi": 0.85,
    "polymarket_reverse": 0.65,
}

# Import shared asset class detection
try:
    from alpha_engine.config import detect_asset_class as _detect_asset_class
except Exception:
    try:
        from config import detect_asset_class as _detect_asset_class
    except Exception:
        def _detect_asset_class(symbol: str) -> str:
            return "crypto" if str(symbol).upper().endswith("USDT") else "equity"


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# Resilient price fetch — import from shared api_failover module
# with fallback for when this module is run directly and alpha_engine
# is not on sys.path.
try:
    from alpha_engine.api_failover import fetch_price_resilient as _fetch_price_resilient
except Exception:
    try:
        from api_failover import fetch_price_resilient as _fetch_price_resilient
    except Exception:
        _fetch_price_resilient = None  # type: ignore[assignment]


def _fetch_price(symbol: str) -> float:
    """Fetch current price using the shared failover chain, with a minimal
    inline Binance fallback when api_failover cannot be imported at all.
    Returns float price or 0.0 on failure.
    """
    sym = str(symbol or "").upper().strip()

    if _fetch_price_resilient is not None:
        try:
            price = _fetch_price_resilient(sym)
            if price and float(price) > 0:
                return float(price)
        except Exception:
            logger.warning("fetch_price_resilient(%s) raised, trying inline fallback", sym)

    # Last resort: minimal inline Binance spot fetch
    import urllib.request as _urllib_request
    import json as _json
    for base in ("https://api.binance.com", "https://data-api.binance.vision"):
        try:
            url = f"{base}/api/v3/ticker/price?symbol={sym}"
            req = _urllib_request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with _urllib_request.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read())
            if isinstance(data, dict) and "price" in data:
                p = float(data["price"])
                if p > 0:
                    return p
        except Exception:
            continue

    logger.warning("All price sources failed for %s", sym)
    return 0.0


def _derive_trade_levels(
    entry_price: float,
    direction: str,
    confidence: float,
    source_count: int,
) -> tuple[float, float]:
    if entry_price <= 0:
        return (0.0, 0.0)

    conf = max(0.55, min(0.95, _float(confidence or 0.70)))
    source_bonus = max(0, min(int(source_count or 1) - 1, 3))
    tp_pct = min(0.04, max(0.015, 0.014 + (conf - 0.55) * 0.04 + source_bonus * 0.0025))
    sl_pct = max(0.009, tp_pct / 1.67)

    if str(direction).upper() == "SHORT":
        return (
            round(entry_price * (1 - tp_pct), 8),
            round(entry_price * (1 + sl_pct), 8),
        )
    return (
        round(entry_price * (1 + tp_pct), 8),
        round(entry_price * (1 - sl_pct), 8),
    )


def _extract_trade_levels(
    symbol: str,
    direction: str,
    confidence: float,
    winning_entries: list[dict[str, Any]],
    source_count: int,
) -> tuple[float, float, float]:
    for entry in sorted(winning_entries, key=lambda item: float(item.get("confidence", 0) or 0), reverse=True):
        best_pick = entry.get("best_pick") if isinstance(entry.get("best_pick"), dict) else {}
        entry_price = _float(best_pick.get("entry_price"))
        take_profit = _float(best_pick.get("take_profit", best_pick.get("target_price", best_pick.get("tp"))))
        stop_loss = _float(best_pick.get("stop_loss", best_pick.get("stop_price", best_pick.get("sl"))))
        if entry_price > 0:
            if take_profit <= 0 or stop_loss <= 0:
                take_profit, stop_loss = _derive_trade_levels(entry_price, direction, confidence, source_count)
            return (round(entry_price, 8), take_profit, stop_loss)

    entry_price = _fetch_price(symbol)
    if entry_price > 0:
        take_profit, stop_loss = _derive_trade_levels(entry_price, direction, confidence, source_count)
        return (round(entry_price, 8), take_profit, stop_loss)
    return (0.0, 0.0, 0.0)


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _normalize_direction(pick: dict[str, Any]) -> str | None:
    direction = str(pick.get("direction", pick.get("signal_type", ""))).upper()
    if direction in ("BUY", "LONG"):
        return "LONG"
    if direction in ("SELL", "SHORT"):
        return "SHORT"
    return None


def _contributor_id(pick: dict[str, Any]) -> str:
    for key in ("trader_address", "strategy", "id", "source_system"):
        value = str(pick.get(key, "") or "").strip()
        if value:
            return value
    return "unknown"


def _collapse_source_picks(
    picks: list[dict[str, Any]],
    *,
    source_category: str,
) -> list[dict[str, Any]]:
    """
    Collapse a raw source into one best directional entry per symbol+direction.
    Multiple agreeing wallet traders on the same symbol get a small confidence
    bonus, but they still count as one source category for final consensus.
    """
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for pick in picks:
        if not isinstance(pick, dict):
            continue
        symbol = str(pick.get("symbol", "")).upper()
        direction = _normalize_direction(pick)
        confidence = float(pick.get("confidence", 0) or 0)
        if not symbol or not direction or confidence <= 0:
            continue

        key = (symbol, direction)
        bucket = grouped.setdefault(
            key,
            {
                "symbol": symbol,
                "direction": direction,
                "source_category": source_category,
                "contributors": set(),
                "items": [],
                "best_pick": pick,
                "max_confidence": confidence,
            },
        )
        bucket["contributors"].add(_contributor_id(pick))
        bucket["items"].append(pick)
        if confidence > bucket["max_confidence"]:
            bucket["max_confidence"] = confidence
            bucket["best_pick"] = pick

    collapsed: list[dict[str, Any]] = []
    for bucket in grouped.values():
        contributor_bonus = min((len(bucket["contributors"]) - 1) * 0.03, 0.10)
        collapsed_confidence = min(0.95, bucket["max_confidence"] + contributor_bonus)
        collapsed.append(
            {
                "symbol": bucket["symbol"],
                "direction": bucket["direction"],
                "source_category": source_category,
                "confidence": round(collapsed_confidence, 3),
                "contributor_count": len(bucket["contributors"]),
                "best_pick": bucket["best_pick"],
                "contributors": sorted(bucket["contributors"]),
            }
        )
    return collapsed


def _normalize_wr_fraction(value: Any) -> float | None:
    wr = _float(value)
    if wr <= 0:
        return None
    if wr > 100:
        return None
    if wr > 1.5:
        wr /= 100.0
    return round(wr, 4)


def _max_sample_size(pick: dict[str, Any], *fields: str) -> int:
    return max((int(_float(pick.get(field))) for field in fields), default=0)


def _pick_first_wr_fraction(pick: dict[str, Any], fields: tuple[str, ...]) -> float | None:
    for field in fields:
        wr = _normalize_wr_fraction(pick.get(field))
        if wr is not None:
            return wr
    return None


def _aggregate_consensus_audit_metadata(
    winning_entries: list[dict[str, Any]],
    wallet_support: dict[str, Any] | None,
) -> dict[str, Any]:
    history_sum = 0.0
    history_weight = 0.0
    forward_sum = 0.0
    forward_weight = 0.0
    history_sample_max = 0
    forward_sample_max = 0
    contributor_total = 0
    source_systems: set[str] = set()
    type_labels: set[str] = set()

    for entry in winning_entries:
        contributor_total += max(1, int(_float(entry.get("contributor_count"))))
        best_pick = entry.get("best_pick") if isinstance(entry.get("best_pick"), dict) else {}
        items = entry.get("items") if isinstance(entry.get("items"), list) and entry.get("items") else [best_pick]

        for pick in items:
            if not isinstance(pick, dict):
                continue
            source_system = str(pick.get("source_system") or "").strip()
            if source_system:
                source_systems.add(source_system)
            type_label = str(pick.get("type_label") or "").strip()
            if type_label:
                type_labels.add(type_label)

            history_wr = _pick_first_wr_fraction(
                pick,
                ("history_wr_bayes", "profile_crypto_wr_bayes", "history_wr", "profile_crypto_wr"),
            )
            history_sample = _max_sample_size(pick, "history_trades", "consensus_count")
            if history_wr is not None:
                weight = float(max(1, history_sample))
                history_sum += history_wr * weight
                history_weight += weight
                history_sample_max = max(history_sample_max, history_sample)

            forward_wr = _pick_first_wr_fraction(pick, ("forward_wr",))
            forward_sample = _max_sample_size(pick, "forward_trades")
            if forward_wr is not None and forward_sample > 0:
                weight = float(max(1, forward_sample))
                forward_sum += forward_wr * weight
                forward_weight += weight
                forward_sample_max = max(forward_sample_max, forward_sample)

    wallet_pick = wallet_support.get("best_pick") if isinstance(wallet_support, dict) else {}
    trader_label = (
        wallet_pick.get("trader_label")
        or wallet_pick.get("trader_name")
        or wallet_pick.get("username")
        or wallet_pick.get("strategy")
        or None
    ) if isinstance(wallet_pick, dict) else None

    return {
        "history_wr_bayes": round(history_sum / history_weight, 4) if history_weight > 0 else None,
        "history_trades": history_sample_max or None,
        "forward_wr": round(forward_sum / forward_weight, 4) if forward_weight > 0 else None,
        "forward_trades": forward_sample_max or None,
        "consensus_count": contributor_total or None,
        "source_systems": sorted(source_systems) or None,
        "type_label": "🔮 PM Consensus",
        "trader_label": str(trader_label) if trader_label else None,
        "agreeing_sources": sorted(type_labels) or None,
    }


def _get_polymarket_wallet_picks() -> list[dict[str, Any]]:
    data = _load_json(POLYMARKET_WALLET_PICKS)
    if isinstance(data, list) and data:
        return data
    try:
        from copy_trader_intel.polymarket_scraper import scan_polymarket_traders, save_polymarket_results

        profiles, picks = scan_polymarket_traders()
        save_polymarket_results(profiles, picks)
        return picks
    except Exception as exc:
        logger.warning("Polymarket wallet scan failed: %s", exc)
        return []


def _get_polymarket_reverse_picks() -> list[dict[str, Any]]:
    data = _load_json(POLYMARKET_SIGNAL_FILE)
    if isinstance(data, dict):
        picks = data.get("picks")
        if isinstance(picks, list):
            return picks
    try:
        from alpha_engine.polymarket_signals import fetch_crypto_markets, generate_polymarket_picks

        markets = fetch_crypto_markets()
        return generate_polymarket_picks(markets)
    except Exception as exc:
        logger.warning("Polymarket reverse-engineered import failed: %s", exc)
        return []


def _get_kalshi_picks() -> list[dict[str, Any]]:
    data = _load_json(KALSHI_SIGNAL_FILE)
    if isinstance(data, dict):
        picks = data.get("picks")
        if isinstance(picks, list):
            return picks
    try:
        from alpha_engine.kalshi_signals import generate_kalshi_picks

        return generate_kalshi_picks()
    except Exception as exc:
        logger.warning("Kalshi import failed: %s", exc)
        return []


def aggregate_signals(
    wallet_picks: list[dict[str, Any]],
    polymarket_picks: list[dict[str, Any]],
    kalshi_picks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    wallet_entries = _collapse_source_picks(wallet_picks, source_category="wallet_copy")
    reverse_entries = _collapse_source_picks(polymarket_picks, source_category="polymarket_reverse")
    kalshi_entries = _collapse_source_picks(kalshi_picks, source_category="kalshi")

    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for entry in wallet_entries + reverse_entries + kalshi_entries:
        by_symbol.setdefault(entry["symbol"], []).append(entry)

    now = datetime.now(timezone.utc)
    consensus_picks: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    for symbol, entries in by_symbol.items():
        long_entries = [entry for entry in entries if entry["direction"] == "LONG"]
        short_entries = [entry for entry in entries if entry["direction"] == "SHORT"]

        def _score(rows: list[dict[str, Any]]) -> float:
            return sum(SOURCE_WEIGHTS[row["source_category"]] * row["confidence"] for row in rows)

        long_score = _score(long_entries)
        short_score = _score(short_entries)
        if long_score == 0 and short_score == 0:
            continue

        if abs(long_score - short_score) < MIN_SCORE_GAP:
            logger.info("Skipping %s: conflicting consensus too close (gap=%.3f)", symbol, abs(long_score - short_score))
            continue

        winning_direction = "LONG" if long_score > short_score else "SHORT"
        winning_entries = long_entries if winning_direction == "LONG" else short_entries
        losing_entries = short_entries if winning_direction == "LONG" else long_entries
        source_categories = {entry["source_category"] for entry in winning_entries}
        if len(source_categories) < MIN_SOURCE_CATEGORIES:
            continue

        winner_score = max(long_score, short_score)
        loser_score = min(long_score, short_score)
        conflict_penalty = min(loser_score * 0.20, 0.08) if losing_entries else 0.0
        final_confidence = min(
            MAX_CONFIDENCE,
            0.58 + (winner_score * 0.22) + ((len(source_categories) - 1) * 0.05) - conflict_penalty,
        )
        if final_confidence < MIN_CONFIDENCE:
            continue

        wallet_support = next((entry for entry in winning_entries if entry["source_category"] == "wallet_copy"), None)
        audit_meta = _aggregate_consensus_audit_metadata(winning_entries, wallet_support)
        base_id = f"pmconsensus_{symbol}_{winning_direction[:1]}_{now.strftime('%Y%m%d%H%M')}"
        pick_id = base_id
        suffix = 0
        while pick_id in used_ids:
            suffix += 1
            pick_id = f"{base_id}_{suffix}"
        used_ids.add(pick_id)

        details = []
        strategies = []
        for entry in winning_entries:
            best_pick = entry["best_pick"]
            strategies.append(str(best_pick.get("strategy") or entry["source_category"]))
            details.append(
                {
                    "source_category": entry["source_category"],
                    "confidence": entry["confidence"],
                    "contributors": entry["contributor_count"],
                    "strategy": best_pick.get("strategy"),
                    "reason": str(best_pick.get("reason", "") or "")[:160],
                }
            )

        reason = (
            f"Prediction-market consensus: {', '.join(sorted(source_categories))} agree "
            f"{winning_direction} {symbol}"
        )
        if wallet_support:
            wallet_pick = wallet_support["best_pick"]
            trader_name = wallet_pick.get("trader_name") or wallet_pick.get("strategy") or "wallet cluster"
            reason += f"; lead wallet source={trader_name}"

        entry_price, take_profit, stop_loss = _extract_trade_levels(
            symbol,
            winning_direction,
            final_confidence,
            winning_entries,
            len(source_categories),
        )
        status = "OPEN" if entry_price > 0 else "SIGNAL"
        asset_class = _detect_asset_class(symbol)

        consensus_picks.append(
            {
                "id": pick_id,
                "strategy": "prediction_market_consensus",
                "symbol": symbol,
                "category": asset_class,
                "signal_type": "BUY" if winning_direction == "LONG" else "SELL",
                "direction": winning_direction,
                "entry_price": entry_price or None,
                "entry_date": now.strftime("%Y-%m-%d"),
                "take_profit": take_profit or None,
                "stop_loss": stop_loss or None,
                "confidence": round(final_confidence, 3),
                "ml_score": None,
                "status": status,
                "source_system": "prediction_market_consensus",
                "created_at": now.isoformat(),
                "has_conflict": bool(losing_entries),
                "type_label": audit_meta.get("type_label"),
                "trader_label": audit_meta.get("trader_label"),
                "cross_source_agreement": True,
                "sources": sorted(source_categories),
                "source_count": len(source_categories),
                "source_systems": audit_meta.get("source_systems"),
                "strategies": sorted(set(strategies)),
                "consensus_count": audit_meta.get("consensus_count"),
                "history_wr_bayes": audit_meta.get("history_wr_bayes"),
                "history_trades": audit_meta.get("history_trades"),
                "forward_wr": audit_meta.get("forward_wr"),
                "forward_trades": audit_meta.get("forward_trades"),
                "agreeing_sources": audit_meta.get("agreeing_sources"),
                "consensus_data": {
                    "winner_score": round(winner_score, 4),
                    "loser_score": round(loser_score, 4),
                    "long_score": round(long_score, 4),
                    "short_score": round(short_score, 4),
                    "source_category_count": len(source_categories),
                    "wallet_copy_present": wallet_support is not None,
                    "source_details": details,
                },
                "reason": reason,
            }
        )

    consensus_picks.sort(key=lambda item: float(item.get("confidence", 0) or 0), reverse=True)
    logger.info("Prediction-market consensus generated %d picks", len(consensus_picks))
    return consensus_picks


def merge_into_active_picks(consensus_picks: list[dict[str, Any]]) -> int:
    """Merge prediction-market consensus picks into active_picks.json."""
    active_data = _load_json(ACTIVE_PICKS_PATH)
    if active_data is None:
        active_picks = []
        is_dict_format = False
    elif isinstance(active_data, dict):
        active_picks = active_data.get("picks", [])
        is_dict_format = True
    else:
        active_picks = active_data
        is_dict_format = False

    filtered_active_picks: list[dict[str, Any]] = []
    removed_stale = 0
    for pick in active_picks:
        if not isinstance(pick, dict):
            filtered_active_picks.append(pick)
            continue
        strategy = str(pick.get("strategy", "")).strip()
        source_system = str(pick.get("source_system", "")).lower()
        source = str(pick.get("source", "")).lower()
        if (
            strategy == "prediction_market_consensus"
            and (
                source_system in {"prediction_market_consensus", "prediction_market_agents"}
                or source in {"prediction_market_consensus", "prediction_market_agents"}
            )
        ):
            removed_stale += 1
            continue
        filtered_active_picks.append(pick)
    active_picks = filtered_active_picks

    existing_keys: set[str] = set()
    for pick in active_picks:
        if not isinstance(pick, dict):
            continue
        symbol = str(pick.get("symbol", "")).upper()
        direction = _normalize_direction(pick)
        source = str(pick.get("source_system", "")).lower()
        if symbol and direction:
            existing_keys.add(f"{symbol}_{direction}_{source}")

    merged = 0
    skipped = 0
    for pick in consensus_picks:
        if float(pick.get("confidence", 0) or 0) < MIN_CONFIDENCE:
            skipped += 1
            continue
        symbol = str(pick.get("symbol", "")).upper()
        direction = _normalize_direction(pick)
        key = f"{symbol}_{direction}_prediction_market_consensus"
        if key in existing_keys:
            skipped += 1
            continue

        merged_pick = dict(pick)
        merged_pick["status"] = "ACTIVE" if _float(merged_pick.get("entry_price")) > 0 else "SIGNAL"
        merged_pick["entry_price"] = merged_pick.get("entry_price") or 0
        merged_pick["take_profit"] = merged_pick.get("take_profit") or 0
        merged_pick["stop_loss"] = merged_pick.get("stop_loss") or 0

        active_picks.append(merged_pick)
        existing_keys.add(key)
        merged += 1

    if removed_stale > 0 or merged > 0:
        payload = {"picks": active_picks} if is_dict_format else active_picks
        with open(ACTIVE_PICKS_PATH, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)

    logger.info(
        "Merged %d prediction-market consensus picks (%d skipped, %d stale removed)",
        merged,
        skipped,
        removed_stale,
    )
    return merged


def run_consensus(auto_merge: bool = True) -> list[dict[str, Any]]:
    logger.info("=== Prediction Market Consensus Engine (Multi-Asset) ===")

    logger.info("[1/3] Loading Polymarket wallet-copy picks...")
    wallet_picks = _get_polymarket_wallet_picks()
    logger.info("  %d wallet-copy picks", len(wallet_picks))

    logger.info("[2/3] Loading reverse-engineered market signals...")
    polymarket_picks = _get_polymarket_reverse_picks()
    logger.info("  %d reverse-engineered Polymarket picks", len(polymarket_picks))

    logger.info("[3/3] Loading Kalshi signals...")
    kalshi_picks = _get_kalshi_picks()
    logger.info("  %d Kalshi picks", len(kalshi_picks))

    consensus_picks = aggregate_signals(wallet_picks, polymarket_picks, kalshi_picks)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "prediction_market_consensus",
        "wallet_input": len(wallet_picks),
        "polymarket_input": len(polymarket_picks),
        "kalshi_input": len(kalshi_picks),
        "pick_count": len(consensus_picks),
        "picks": consensus_picks,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    logger.info("Saved consensus picks to %s", OUTPUT_FILE)

    if auto_merge:
        merge_into_active_picks(consensus_picks)
    return consensus_picks


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 70)
    print("  Prediction Market Consensus — Multi-Asset")
    print("  Wallet Copy + Polymarket Reverse + Kalshi")
    print("=" * 70)

    picks = run_consensus(auto_merge=True)
    print(f"\nResults: {len(picks)} consensus picks\n")
    for pick in picks:
        sources = ",".join(pick.get("sources", []))
        ac = pick.get("category", "crypto")
        print(
            f"  {'LONG ' if pick['direction'] == 'LONG' else 'SHORT'} "
            f"{pick['symbol']:<12s} [{ac:<9s}] conf={pick['confidence']:.2f} [{sources}]"
        )
        for detail in pick.get("consensus_data", {}).get("source_details", [])[:3]:
            print(f"    - {detail['source_category']}: {detail['reason']}")
        print()


if __name__ == "__main__":
    main()
