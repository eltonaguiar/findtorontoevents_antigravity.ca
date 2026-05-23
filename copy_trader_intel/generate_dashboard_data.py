#!/usr/bin/env python3
"""
Generate dashboard-compatible copy trader data files.
Reads from copy_trader_intel/data/ and writes to alpha_engine/data/
for the funds.html dashboard to consume.

Produces TWO clear categories per source:
  1. "Their Positions" — actual open positions scraped from on-chain/exchange
  2. "Our Strategy Clones" — our reverse-engineered picks (proven_trader_strategy_clone)
"""

import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

# Binance price API (geo-safe)
BINANCE_APIS = [
    "https://data-api.binance.vision",
    "https://api.binance.us",
    "https://api.binance.com",
]

_price_cache = {}


def get_live_price(symbol):
    """Fetch current price from Binance with caching."""
    if symbol in _price_cache:
        return _price_cache[symbol]
    for base in BINANCE_APIS:
        try:
            r = requests.get(f"{base}/api/v3/ticker/price",
                             params={"symbol": symbol}, timeout=5)
            if r.status_code == 200:
                price = float(r.json()["price"])
                _price_cache[symbol] = price
                return price
        except Exception:
            continue
    return None


def calc_unrealized_pnl(entry_price, current_price, direction):
    """Calculate unrealized PnL percentage."""
    if not entry_price or not current_price or entry_price == 0:
        return 0.0
    if direction == "LONG" or direction == "BUY":
        return round((current_price - entry_price) / entry_price * 100, 2)
    else:  # SHORT / SELL
        return round((entry_price - current_price) / entry_price * 100, 2)

CT_DATA = Path(__file__).parent / "data"
ALPHA_DATA = Path(__file__).parent.parent / "alpha_engine" / "data"


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def normalize_copytrader_key(value):
    """Normalize trader/strategy labels for history lookups."""
    return " ".join(str(value or "").strip().lower().split())


def extract_copytrader_label(strategy="", fallback=""):
    """Extract the underlying trader label from strategy naming conventions."""
    if fallback:
        return str(fallback)

    strategy = str(strategy or "")
    lower = strategy.lower()
    for prefix in ("clone_hl_copy_", "copy_hl_", "hs_"):
        if lower.startswith(prefix):
            return strategy[len(prefix):]
    return strategy


def normalize_copytrader_identity(strategy="", trader_label="", trader_address=""):
    """Collapse clone/high-score aliases down to a single underlying trader identity."""
    label = trader_label or extract_copytrader_label(strategy)
    label_key = normalize_copytrader_key(label)
    if label_key:
        return label_key

    addr_key = normalize_copytrader_key(trader_address)
    if addr_key:
        return addr_key

    return normalize_copytrader_key(strategy)


def build_copytrader_consensus_maps(picks):
    """Return symbol+direction -> unique underlying trader count and labels."""
    grouped = {}
    for pick in picks or []:
        sym = str(pick.get("symbol", "") or "").strip().upper()
        direction = str(pick.get("direction", "") or "").strip().upper()
        if not sym or not direction:
            continue

        label = str(
            pick.get("trader_label")
            or pick.get("clone_source_trader")
            or extract_copytrader_label(
                pick.get("strategy", ""),
                pick.get("clone_source_trader", ""),
            )
        ).strip()
        identity = normalize_copytrader_identity(
            strategy=pick.get("strategy", ""),
            trader_label=label,
            trader_address=pick.get("trader_address", ""),
        )
        if not identity:
            continue

        key = f"{sym}:{direction}"
        grouped.setdefault(key, {})
        grouped[key][identity] = label or identity

    counts = {key: len(labels) for key, labels in grouped.items()}
    labels = {
        key: sorted(display for display in identities.values() if display)
        for key, identities in grouped.items()
    }
    return counts, labels


def _summarize_pnls(pnls):
    if not pnls:
        return None
    wins = sum(1 for p in pnls if p > 0)
    return {
        "trades": len(pnls),
        "wins": wins,
        "losses": len(pnls) - wins,
        "win_rate": wins / len(pnls),
        "avg_pnl": sum(pnls) / len(pnls),
    }


def load_copytrader_history_scorebook():
    """Build strategy/trader/type performance summaries from tracked picks."""
    history_rows = load_json(CT_DATA / "highscore_pick_history.json") or []
    by_strategy = {}
    by_trader = {}
    by_type = {}

    strat_pnls = {}
    trader_pnls = {}
    type_pnls = {}

    for row in history_rows:
        pnl = row.get("final_pnl", row.get("current_pnl", 0))
        try:
            pnl = float(pnl or 0)
        except (ValueError, TypeError):
            continue

        strategy = normalize_copytrader_key(row.get("strategy", ""))
        trader = normalize_copytrader_key(
            row.get("trader_label")
            or extract_copytrader_label(row.get("strategy", ""))
        )
        type_label = normalize_copytrader_key(row.get("type_label", ""))

        if strategy:
            strat_pnls.setdefault(strategy, []).append(pnl)
        if trader:
            trader_pnls.setdefault(trader, []).append(pnl)
        if type_label:
            type_pnls.setdefault(type_label, []).append(pnl)

    for key, pnls in strat_pnls.items():
        summary = _summarize_pnls(pnls)
        if summary:
            by_strategy[key] = summary

    for key, pnls in trader_pnls.items():
        summary = _summarize_pnls(pnls)
        if summary:
            by_trader[key] = summary

    for key, pnls in type_pnls.items():
        summary = _summarize_pnls(pnls)
        if summary:
            by_type[key] = summary

    return {
        "by_strategy": by_strategy,
        "by_trader": by_trader,
        "by_type": by_type,
    }


def lookup_copytrader_history(scorebook, strategy="", trader_label="", type_label=""):
    """Prefer exact strategy history, then trader, then family/type history."""
    if not scorebook:
        return None, None

    strategy_key = normalize_copytrader_key(strategy)
    trader_key = normalize_copytrader_key(trader_label or extract_copytrader_label(strategy))
    type_key = normalize_copytrader_key(type_label)

    if strategy_key and strategy_key in scorebook["by_strategy"]:
        return scorebook["by_strategy"][strategy_key], "strategy"
    if trader_key and trader_key in scorebook["by_trader"]:
        return scorebook["by_trader"][trader_key], "trader"
    if type_key and type_key in scorebook["by_type"]:
        return scorebook["by_type"][type_key], "type"
    return None, None


def copytrader_history_bonus(stats):
    """Translate tracked performance into a bounded score adjustment."""
    if not stats:
        return 0.0

    trades = int(stats.get("trades", 0) or 0)
    wr = float(stats.get("win_rate", 0) or 0)
    avg_pnl = float(stats.get("avg_pnl", 0) or 0)

    bonus = 0.0
    if trades >= 20:
        if wr >= 0.62 and avg_pnl > 0:
            bonus += 10
        elif wr >= 0.55 and avg_pnl > 0:
            bonus += 7
        elif wr >= 0.50 and avg_pnl > 0:
            bonus += 4
        elif wr < 0.35:
            bonus -= 7
    elif trades >= 5:
        if wr >= 0.65 and avg_pnl >= 0:
            bonus += 7
        elif wr >= 0.55 and avg_pnl > 0:
            bonus += 5
        elif wr >= 0.50 and avg_pnl > 0:
            bonus += 2
        elif wr < 0.30:
            bonus -= 5
    elif trades >= 3:
        if wr >= 0.67 and avg_pnl >= 0:
            bonus += 4
        elif wr < 0.25:
            bonus -= 4

    if avg_pnl >= 2:
        bonus += 2
    elif avg_pnl >= 1:
        bonus += 1
    elif avg_pnl <= -1:
        bonus -= 2

    return round(max(-8, min(12, bonus)), 1)


# Aliases to match picks to sources — expanded to catch all naming patterns
SOURCE_ALIASES = {
    "hyperliquid": ["hyperliquid", "hl_copy_", "copy_hl_", "_hl_", "clone_hl_"],
    "okx": ["okx"],
    "bybit": ["bybit"],
    "bitget": ["bitget"],
    "bingx": ["bingx"],
    "gate": ["gate"],
    "dex": ["dex", "gmx", "dydx", "gains", "copin"],
}


def classify_pick(pick):
    """Classify a pick as 'their_position' or 'our_clone'."""
    stype = pick.get("source_strategy_type", "")
    strategy = pick.get("strategy", "")
    if stype == "proven_trader_strategy_clone" or strategy.startswith("clone_"):
        return "our_clone"
    return "their_position"


def compute_pick_score(pick, trader_profile, consensus_syms, current_pnl):
    """Score a pick 0-100 based on trader quality and pick specifics.
    Returns (total_score, breakdown_dict)."""
    breakdown = {}

    # 1. Trader Win Rate (max 30 pts)
    wr = trader_profile.get("win_rate", 0)
    breakdown["wr_pts"] = round(min(wr * 100 / 3.33, 30), 1)

    # 2. Profit Factor (max 15 pts)
    pf = trader_profile.get("profit_factor", 0)
    breakdown["pf_pts"] = round(min(pf * 5, 15), 1)

    # 3. Symbol Specialization (max 20 pts)
    sym = pick.get("symbol", "")
    top_coins = trader_profile.get("top_coins", [])
    sym_base = sym.replace("USDT", "").replace("USD", "")
    total_pnl = sum(abs(c[2]) for c in top_coins if len(c) >= 3) or 1
    sym_pts = 0
    for coin_data in top_coins:
        coin_name = coin_data[0] if isinstance(coin_data, list) else ""
        coin_pnl = coin_data[2] if isinstance(coin_data, list) and len(coin_data) >= 3 else 0
        if sym_base.upper() in coin_name.upper():
            pnl_share = abs(coin_pnl) / total_pnl
            sym_pts = min(pnl_share * 40, 20)
            break
    breakdown["symbol_pts"] = round(sym_pts, 1)

    # 4. Current PnL boost (max 15 pts) — only green positions
    pnl_pts = min(current_pnl * 3, 15) if current_pnl > 0 else 0
    breakdown["pnl_pts"] = round(pnl_pts, 1)

    # 5. Consensus (max 10 pts)
    direction = pick.get("direction", "").upper()
    consensus_key = f"{sym}:{direction}"
    cons_pts = 0
    if consensus_key in consensus_syms:
        count = consensus_syms[consensus_key]
        cons_pts = min(count * 5, 10)
    breakdown["consensus_pts"] = round(cons_pts, 1)

    # 6. Trade volume / recent activity (max 10 pts)
    total_trades = trader_profile.get("total_trades", 0)
    breakdown["activity_pts"] = round(min(total_trades / 100, 10), 1)

    # 7. Enrichment signal alignment (max 15 pts) — new supplemental APIs
    enrichment = pick.get("enrichment", {})
    enrich_pts = 0.0
    if enrichment:
        is_long = direction == "LONG"

        # Context grade from market signal alignment
        grade = enrichment.get("context_grade", "")
        if grade == "STRONG_ALIGNMENT":
            enrich_pts += 6
        elif grade == "MODERATE_ALIGNMENT":
            enrich_pts += 3
        elif grade == "STRONG_CONTRARY":
            enrich_pts -= 4

        # Messari NVT on-chain valuation
        nvt_sig = (enrichment.get("on_chain") or {}).get("nvt_signal", "")
        if nvt_sig == "UNDERVALUED":
            enrich_pts += 3
        elif nvt_sig == "OVERVALUED":
            enrich_pts -= 2

        # Coinpaprika weekly momentum alignment
        weekly = (enrichment.get("supplemental") or {}).get("weekly_momentum", "")
        if weekly == "STRONG_UPTREND" and is_long:
            enrich_pts += 3
        elif weekly == "STRONG_DOWNTREND" and not is_long:
            enrich_pts += 3
        elif weekly == "STRONG_DOWNTREND" and is_long:
            enrich_pts -= 2
        elif weekly == "STRONG_UPTREND" and not is_long:
            enrich_pts -= 2

        # BTC mempool demand (BTC picks only)
        if "BTC" in sym:
            btc_demand = (enrichment.get("mempool") or {}).get("btc_demand_signal", "")
            if btc_demand == "BULLISH_DEMAND" and is_long:
                enrich_pts += 2

        # 1inch DEX/CEX price spread
        defi_sig = (enrichment.get("dex_1inch") or {}).get("defi_cex_signal", "")
        if defi_sig == "DEX_PREMIUM_BULLISH" and is_long:
            enrich_pts += 2
        elif defi_sig == "DEX_DISCOUNT_BEARISH" and not is_long:
            enrich_pts += 2

        # 0x liquidity depth
        liq_sig = (enrichment.get("dex_0x") or {}).get("dex_liquidity_signal", "")
        if liq_sig == "ILLIQUID_WARNING":
            enrich_pts -= 3

    breakdown["enrich_pts"] = round(max(-10, min(enrich_pts, 15)), 1)

    total = sum(breakdown.values())
    total = round(min(max(total, 0), 100), 1)
    return total, breakdown


def compute_high_score_picks(picks, trader_profiles, qualified_traders, history_scorebook=None):
    """Build the ranked list of high-score picks from verified traders."""
    # Build trader lookup by label/address
    profile_by_label = {}
    profile_by_addr = {}
    for tp in trader_profiles:
        label = tp.get("label", "")
        addr = tp.get("address", "")
        if label:
            profile_by_label[label.lower()] = tp
        if addr:
            profile_by_addr[addr.lower()] = tp

    # Build consensus map using underlying trader identity, not clone/high-score aliases.
    consensus, consensus_labels = build_copytrader_consensus_maps(picks)

    high_score = []
    for p in picks:
        # Match pick to trader profile
        strategy = p.get("strategy", "")
        trader_addr = p.get("trader_address", "")
        profile = None

        # Try matching by strategy name (e.g. copy_hl_Auros_66M → Auros_66M)
        for prefix in ["copy_hl_", "clone_hl_copy_", "copy_"]:
            if strategy.startswith(prefix):
                label_part = strategy[len(prefix):].lower()
                if label_part in profile_by_label:
                    profile = profile_by_label[label_part]
                    break

        # Fallback: match by address
        if not profile and trader_addr:
            profile = profile_by_addr.get(trader_addr.lower())

        if not profile:
            continue

        # Qualifying thresholds — lowered to capture more proven traders
        wr = profile.get("win_rate", 0)
        total_trades = profile.get("total_trades", 0)
        if wr < 0.50 or total_trades < 10:
            continue

        # Check symbol is in trader's top_coins + get track record
        sym = p.get("symbol", "")
        sym_base = sym.replace("USDT", "").replace("USD", "")
        top_coins = profile.get("top_coins", [])
        symbol_record = None
        for c in top_coins:
            if isinstance(c, list) and len(c) >= 3:
                if sym_base.upper() in c[0].upper():
                    symbol_record = {
                        "coin": c[0],
                        "trades": c[1],
                        "pnl": round(c[2], 2)
                    }
                    break
        # Don't skip picks without symbol record — give them a baseline score
        if not symbol_record:
            symbol_record = {"coin": sym_base, "trades": 0, "pnl": 0}

        # Calculate live PnL
        entry = p.get("entry_price", 0)
        try:
            entry = float(entry) if entry else 0
        except (ValueError, TypeError):
            entry = 0
        direction = p.get("direction", "").upper()
        current_price = get_live_price(sym)
        current_pnl = calc_unrealized_pnl(entry, current_price, direction) if entry and current_price else 0

        # ── TP/SL breach detection ──
        tp = p.get("take_profit")
        sl = p.get("stop_loss")
        try:
            tp = float(tp) if tp else None
        except (ValueError, TypeError):
            tp = None
        try:
            sl = float(sl) if sl else None
        except (ValueError, TypeError):
            sl = None

        pick_status = "ACTIVE"
        if current_price and tp and sl:
            if direction in ("LONG", "BUY"):
                if current_price >= tp:
                    pick_status = "TP_HIT"
                elif current_price <= sl:
                    pick_status = "SL_HIT"
            else:  # SHORT / SELL
                if current_price <= tp:
                    pick_status = "TP_HIT"
                elif current_price >= sl:
                    pick_status = "SL_HIT"

        # TP/SL distance percentages for gauge
        tp_distance_pct = 0
        sl_distance_pct = 0
        if current_price and entry:
            if tp:
                if direction in ("LONG", "BUY"):
                    tp_distance_pct = round((tp - current_price) / entry * 100, 2)
                else:
                    tp_distance_pct = round((current_price - tp) / entry * 100, 2)
            if sl:
                if direction in ("LONG", "BUY"):
                    sl_distance_pct = round((current_price - sl) / entry * 100, 2)
                else:
                    sl_distance_pct = round((sl - current_price) / entry * 100, 2)

        # Show ALL active picks (removed profitable-only filter)
        # Previously filtered to only profitable — this was killing all picks

        # ── Average hold time from trader profile ──
        avg_hold_hours = None
        per_coin = profile.get("per_coin_stats", {})
        sym_stats = per_coin.get(sym_base, per_coin.get(sym, {}))
        if isinstance(sym_stats, dict):
            avg_hold_hours = sym_stats.get("avg_hold_hours", sym_stats.get("avg_hold_time_hours"))
        # Fallback: overall avg hold
        if avg_hold_hours is None:
            avg_hold_hours = profile.get("avg_hold_hours", profile.get("avg_hold_time_hours"))

        # ── Hours since entry ──
        discovered_at = p.get("timestamp", p.get("entry_date", ""))
        hours_since_entry = None
        if discovered_at:
            try:
                from dateutil.parser import parse as dtparse
                dt = dtparse(discovered_at)
                delta = datetime.now(timezone.utc) - dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else datetime.now(timezone.utc) - dt
                hours_since_entry = round(delta.total_seconds() / 3600, 1)
            except Exception:
                pass

        # Penalize negative symbol track record in score
        if symbol_record and symbol_record.get("pnl", 0) < 0:
            # Still show it but note the negative track record
            pass

        ptype = classify_pick(p)
        type_label = "OUR CLONE" if ptype == "our_clone" else "THEIR PICK"

        score, breakdown = compute_pick_score(p, profile, consensus, current_pnl)
        history_stats, history_basis = lookup_copytrader_history(
            history_scorebook,
            strategy=strategy,
            trader_label=profile.get("label", ""),
            type_label=type_label,
        )
        history_bonus = copytrader_history_bonus(history_stats)
        if history_bonus:
            score = round(min(100, max(0, score + history_bonus)), 1)
            breakdown["history_pts"] = history_bonus
        if history_stats:
            breakdown["history_trades"] = history_stats["trades"]
            breakdown["history_wr"] = round(history_stats["win_rate"] * 100, 1)
            breakdown["history_avg_pnl"] = round(history_stats["avg_pnl"], 2)
            breakdown["history_basis"] = history_basis
        if score < 35:
            continue
        # Veto strong contrary enrichment signals unless pick scores very high
        enrich_grade = (p.get("enrichment") or {}).get("context_grade", "")
        if enrich_grade == "STRONG_CONTRARY" and score < 65:
            continue

        consensus_key = f"{sym}:{direction}"

        high_score.append({
            "symbol": sym,
            "direction": direction,
            "entry_price": entry,
            "current_price": current_price,
            "pnl_pct": round(current_pnl, 2),
            "take_profit": tp,
            "stop_loss": sl,
            "pick_status": pick_status,
            "tp_distance_pct": tp_distance_pct,
            "sl_distance_pct": sl_distance_pct,
            "score": score,
            "score_breakdown": breakdown,
            "trader_label": profile.get("label", "Unknown"),
            "trader_wr": round(wr * 100, 1),
            "trader_pf": profile.get("profit_factor", 0),
            "trader_pnl": round(profile.get("total_realized_pnl", 0), 0),
            "trader_trades": total_trades,
            "trader_wins": profile.get("wins", 0),
            "trader_losses": profile.get("losses", 0),
            "consensus_count": consensus.get(consensus_key, 1),
            "consensus_traders": consensus_labels.get(consensus_key, []),
            "history_trades": history_stats["trades"] if history_stats else 0,
            "history_wr": round(history_stats["win_rate"] * 100, 1) if history_stats else None,
            "history_avg_pnl": round(history_stats["avg_pnl"], 2) if history_stats else None,
            "history_basis": history_basis,
            "history_bonus": history_bonus,
            "symbol_record": symbol_record,
            "type": ptype,
            "type_label": type_label,
            "strategy": p.get("strategy", ""),
            "discovered_at": discovered_at,
            "avg_hold_hours": avg_hold_hours,
            "hours_since_entry": hours_since_entry,
            # Enrichment signal summary for dashboard display
            "enrichment_grade": (p.get("enrichment") or {}).get("context_grade", ""),
            "enrichment_alignment": (p.get("enrichment") or {}).get("alignment_score", 0),
            "enrichment_contrary": (p.get("enrichment") or {}).get("contrary_score", 0),
            "enrichment_context": (p.get("enrichment") or {}).get("context_summary", ""),
            "nvt_signal": ((p.get("enrichment") or {}).get("on_chain") or {}).get("nvt_signal", ""),
            "nvt_ratio": ((p.get("enrichment") or {}).get("on_chain") or {}).get("nvt_ratio"),
            "weekly_momentum": ((p.get("enrichment") or {}).get("supplemental") or {}).get("weekly_momentum", ""),
            "ath_distance_pct": ((p.get("enrichment") or {}).get("supplemental") or {}).get("ath_distance_pct"),
            "btc_mempool_demand": ((p.get("enrichment") or {}).get("mempool") or {}).get("btc_demand_signal", ""),
            "btc_fee_sat_vb": ((p.get("enrichment") or {}).get("mempool") or {}).get("btc_fee_fastest_sat_vb"),
            "defi_cex_signal": ((p.get("enrichment") or {}).get("dex_1inch") or {}).get("defi_cex_signal", ""),
            "defi_cex_spread_pct": ((p.get("enrichment") or {}).get("dex_1inch") or {}).get("defi_cex_spread_pct"),
            "dex_liquidity_signal": ((p.get("enrichment") or {}).get("dex_0x") or {}).get("dex_liquidity_signal", ""),
            "active_addresses_24h": ((p.get("enrichment") or {}).get("on_chain") or {}).get("active_addresses_24h"),
            "confidence_adj_reasons": ((p.get("enrichment") or {}).get("confidence_adjustment") or {}).get("reasons", []),
        })

    # Sort: ACTIVE first, then by score + enrichment grade bonus as tiebreaker
    def _hs_sort_key(x):
        grade = x.get("enrichment_grade", "")
        grade_bonus = 5 if grade == "STRONG_ALIGNMENT" else (2 if grade == "MODERATE_ALIGNMENT" else (-3 if grade == "STRONG_CONTRARY" else 0))
        return (-1 if x["pick_status"] == "ACTIVE" else 0, -(x["score"] + grade_bonus))
    high_score.sort(key=_hs_sort_key)
    seen = set()
    deduped = []
    for hs in high_score:
        key = f"{hs['symbol']}:{hs['direction']}"
        if key not in seen:
            seen.add(key)
            deduped.append(hs)
    return deduped


def pick_matches_source(pick, source_key):
    """Check if a pick belongs to a particular exchange source."""
    aliases = SOURCE_ALIASES.get(source_key, [source_key])
    combined = (
        pick.get("strategy", "") +
        pick.get("source_system", "") +
        pick.get("id", "")
    ).lower()
    return any(a in combined for a in aliases)


def build_source_portfolio(source_key, picks, trader_profiles):
    """Build portfolio stats for a single exchange source, split by type."""
    source_picks = [p for p in picks if pick_matches_source(p, source_key)]

    # Split into their positions vs our clones
    their_picks = [p for p in source_picks if classify_pick(p) == "their_position"]
    our_clones = [p for p in source_picks if classify_pick(p) == "our_clone"]

    # Stats for their positions
    their_open = [p for p in their_picks if p.get("status") == "OPEN"]
    their_closed = [p for p in their_picks if p.get("status") in ("TP_HIT", "SL_HIT", "CLOSED", "EXIT")]
    their_wins = sum(1 for p in their_closed if (p.get("pnl_pct") or 0) > 0)
    their_losses = sum(1 for p in their_closed if (p.get("pnl_pct") or 0) <= 0)
    their_total = their_wins + their_losses
    their_pnl = sum(p.get("pnl_pct", 0) or 0 for p in their_closed)

    # Stats for our clones
    clone_open = [p for p in our_clones if p.get("status") == "OPEN"]
    clone_closed = [p for p in our_clones if p.get("status") in ("TP_HIT", "SL_HIT", "CLOSED", "EXIT")]
    clone_wins = sum(1 for p in clone_closed if (p.get("pnl_pct") or 0) > 0)
    clone_losses = sum(1 for p in clone_closed if (p.get("pnl_pct") or 0) <= 0)
    clone_total = clone_wins + clone_losses
    clone_pnl = sum(p.get("pnl_pct", 0) or 0 for p in clone_closed)

    # Get trader profiles for this source
    source_traders = []
    for tp in trader_profiles:
        label = (tp.get("label", "") + tp.get("name", "")).lower()
        if source_key in label or any(source_key in str(v).lower() for v in [tp.get("source", ""), tp.get("exchange", "")]):
            source_traders.append(tp)

    avg_wr = 0
    if source_traders:
        wrs = [t.get("win_rate", 0) for t in source_traders if t.get("win_rate", 0) > 0]
        avg_wr = sum(wrs) / len(wrs) * 100 if wrs else 0

    # Build recent trades list — OUR CLONES FIRST so they're always visible
    recent = []
    total_unrealized = 0.0
    for p in (our_clones + their_picks):
        ptype = classify_pick(p)
        entry = p.get("entry_price", 0)
        sym = p.get("symbol", "")
        direction = p.get("direction", "LONG")
        pnl = p.get("pnl_pct", 0) or 0

        # Calculate unrealized PnL for OPEN positions
        if p.get("status") == "OPEN" and entry and entry > 0:
            current = get_live_price(sym)
            if current:
                pnl = calc_unrealized_pnl(entry, current, direction)
                total_unrealized += pnl

        # Get entry timestamp (from pick data)
        entry_ts = p.get("timestamp", p.get("entry_date", p.get("created_at", "")))

        # Type label for dashboard display
        if ptype == "our_clone":
            type_label = "OUR CLONE"
        else:
            type_label = "THEIR PICK"

        recent.append({
            "symbol": sym,
            "direction": direction,
            "entry_price": entry,
            "exit_price": p.get("exit_price"),
            "pnl_pct": pnl,
            "hold_time": f"{p.get('hold_days', 0) or 0}d" if p.get("hold_days") else "OPEN",
            "strategy": p.get("strategy", ""),
            "type": ptype,
            "type_label": type_label,
            "entry_date": entry_ts,
            "take_profit": p.get("take_profit"),
            "stop_loss": p.get("stop_loss"),
            "clone_source": p.get("clone_source_trader", ""),
            "clone_expected_wr": p.get("clone_expected_wr", None),
        })

    all_total = (their_total or len(their_open)) + (clone_total or len(clone_open))

    return {
        "name": source_key,
        "total_trades": all_total,
        "wins": their_wins + clone_wins,
        "losses": their_losses + clone_losses,
        "win_rate": ((their_wins + clone_wins) / max(their_total + clone_total, 1) * 100) if (their_total + clone_total) > 0 else avg_wr,
        "realized_pnl": their_pnl + clone_pnl,
        "unrealized_pnl": round(total_unrealized, 2),
        "sharpe_ratio": 0,
        "max_drawdown": 0,
        "expectancy": ((their_pnl + clone_pnl) / max(their_total + clone_total, 1)) if (their_total + clone_total) > 0 else 0,
        "avg_hold_time": "--",
        "open_positions": len(their_open) + len(clone_open),
        "tracked_traders": len(source_traders),
        "trades_list": recent,
        # NEW: breakdown by type
        "their_positions": {
            "open": len(their_open),
            "closed": their_total,
            "wins": their_wins,
            "losses": their_losses,
            "pnl": round(their_pnl, 2),
        },
        "our_clones": {
            "open": len(clone_open),
            "closed": clone_total,
            "wins": clone_wins,
            "losses": clone_losses,
            "pnl": round(clone_pnl, 2),
        },
    }


def build_patterns(picks, qualified_traders):
    """Build aggregated pattern data for the dashboard."""
    symbols = Counter()
    directions = Counter()
    for p in picks:
        sym = p.get("symbol", "")
        if sym:
            symbols[sym] += 1
            directions[p.get("direction", "LONG")] += 1

    top_symbols = [{"symbol": s, "count": c} for s, c in symbols.most_common(10)]

    # Consensus picks (same symbol from multiple traders)
    symbol_traders = {}
    for p in picks:
        sym = p.get("symbol", "")
        trader = p.get("strategy", "")
        if sym and trader:
            symbol_traders.setdefault(sym, set()).add(trader)

    consensus = []
    for sym, traders in symbol_traders.items():
        if len(traders) >= 2:
            pick = next((p for p in picks if p.get("symbol") == sym), {})
            consensus.append({
                "symbol": sym,
                "direction": pick.get("direction", "LONG"),
                "trader_count": len(traders),
                "traders": list(traders)[:5],
                "avg_confidence": pick.get("confidence", 0.5),
            })

    # Trader quality overview from qualified_traders.json
    trader_stats = []
    traders_data = qualified_traders.get("traders", []) if isinstance(qualified_traders, dict) else []
    for t in traders_data[:10]:
        trader_stats.append({
            "label": t.get("label", t.get("address", "")[:8]),
            "win_rate": round(t.get("win_rate", 0) * 100, 1),
            "pnl": round(t.get("total_realized_pnl", 0), 2),
            "edge_score": t.get("edge_score", 0),
            "trades": t.get("total_trades", 0),
            "profit_factor": t.get("profit_factor", 0),
        })

    # Separate clone picks vs copy picks
    clone_count = sum(1 for p in picks if classify_pick(p) == "our_clone")
    copy_count = sum(1 for p in picks if classify_pick(p) == "their_position")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_symbols": top_symbols,
        "consensus_picks": len(consensus),
        "consensus": consensus,
        "avg_hold_time": "--",
        "total_picks_tracked": len(picks),
        "their_positions_count": copy_count,
        "our_clones_count": clone_count,
        "total_traders_qualified": len(traders_data),
        "long_short_ratio": f"{directions.get('LONG', 0)}L / {directions.get('SHORT', 0)}S",
        "top_traders": trader_stats,
    }


def main():
    # Load all data
    all_picks = load_json(CT_DATA / "active_picks.json") or []
    qualified = load_json(CT_DATA / "qualified_traders.json") or {}

    # Always merge clone_picks.json (our strategy clones) into active_picks
    # This ensures clones aren't lost when the scraper overwrites active_picks
    clone_picks = load_json(CT_DATA / "clone_picks.json") or []
    if clone_picks:
        # Remove old clones from active, then add fresh
        all_picks = [p for p in all_picks if p.get("source_strategy_type") != "proven_trader_strategy_clone"]

        # DIRECTIONAL CONFLICT FILTER:
        # If the trader is SHORT on BTCUSDT, remove our clone LONG on BTCUSDT.
        # Build a lookup of trader actual directions per symbol
        their_directions = {}
        for p in all_picks:
            sym = p.get("symbol", "")
            d = p.get("direction", "").upper()
            if sym and d and p.get("source_strategy_type") != "proven_trader_strategy_clone":
                if sym not in their_directions:
                    their_directions[sym] = set()
                their_directions[sym].add(d)

        # Filter clones: keep only those that agree with the trader's actual direction
        filtered_clones = []
        removed = 0
        for c in clone_picks:
            sym = c.get("symbol", "")
            clone_dir = c.get("direction", "").upper()
            actual_dirs = their_directions.get(sym, set())
            if actual_dirs and clone_dir and clone_dir not in actual_dirs:
                removed += 1  # Clone disagrees with every trader's direction — skip
            else:
                filtered_clones.append(c)

        all_picks.extend(filtered_clones)
        # Persist merged file so /audit also sees the clones
        with open(CT_DATA / "active_picks.json", "w", encoding="utf-8") as f:
            json.dump(all_picks, f, indent=2, default=str)
        print(f"  [MERGE] {len(filtered_clones)} clone picks merged ({removed} removed — disagreed with trader direction)")

    # Load per-exchange picks
    for exchange in ["okx", "bybit", "bitget", "bingx", "gate"]:
        exchange_picks = load_json(CT_DATA / f"{exchange}_picks.json") or []
        if exchange_picks:
            for p in exchange_picks:
                if "strategy" not in p:
                    p["strategy"] = f"copy_{exchange}"
            all_picks.extend(exchange_picks)


    # Also load the closed trades so the dashboard can compute historical win rates
    closed_files = ['closed_trades.json', 'highscore_closed_picks.json', 'clone_closed_picks.json', 'consensus_closed_picks.json']
    for cf in closed_files:
        c_picks = load_json(CT_DATA / cf) or []
        if isinstance(c_picks, list):
            all_picks.extend(c_picks)
        elif isinstance(c_picks, dict):
            # sometimes wrapper dicts
            all_picks.extend(c_picks.get('picks', []))
    # Deduplicate by id (prefer CLOSED statuses over OPEN)
    pick_map = {}
    for p in all_picks:
        pid = p.get("id", str(id(p)))
        if pid not in pick_map:
            pick_map[pid] = p
        else:
            # If the current mapped pick is OPEN but this new one is CLOSED, overwrite it.
            existing_status = str(pick_map[pid].get("status", "")).upper()
            new_status = str(p.get("status", "")).upper()
            if existing_status in ("", "OPEN", "ACTIVE") and new_status in ("CLOSED", "EXIT", "TP_HIT", "SL_HIT"):
                pick_map[pid] = p
    unique_picks = list(pick_map.values())

    # Load trader profiles (from multiple sources)
    all_profiles = []
    for f in CT_DATA.glob("*_trader_profiles.json"):
        data = load_json(f)
        if isinstance(data, dict):
            all_profiles.extend(data.get("profiles", data.get("traders", [])))
        elif isinstance(data, list):
            all_profiles.extend(data)
    # Also load the main trader_profiles.json and qualified_traders.json
    for extra in ["trader_profiles.json", "qualified_traders.json"]:
        data = load_json(CT_DATA / extra)
        if isinstance(data, dict):
            all_profiles.extend(data.get("profiles", data.get("traders", [])))
        elif isinstance(data, list):
            all_profiles.extend(data)

    # Build portfolio data per source
    portfolio = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "portfolios": []
    }
    for source in ["hyperliquid", "okx", "bybit", "bitget", "bingx", "gate", "dex"]:
        src_data = build_source_portfolio(source, unique_picks, all_profiles)
        if src_data["total_trades"] > 0 or src_data["open_positions"] > 0:
            portfolio["portfolios"].append(src_data)

    # Build high-score picks
    history_scorebook = load_copytrader_history_scorebook()

    high_score_picks = compute_high_score_picks(unique_picks, all_profiles, qualified, history_scorebook)
    portfolio["high_score_picks"] = high_score_picks
    print(f"  [SCORE] {len(high_score_picks)} high-score picks (score >= 50, profitable, WR >= 60%)")

    # Also write high-score picks as audit-compatible active_picks.json
    # so they appear on the main /audit dashboard
    hs_audit_picks = []
    for hs in high_score_picks:
        hs_audit_picks.append({
            "symbol": hs["symbol"],
            "direction": hs["direction"],
            "entry_price": hs["entry_price"],
            "take_profit": hs.get("take_profit"),
            "stop_loss": hs.get("stop_loss"),
            "confidence": hs["score"],
            "source_system": "copy_trader_highscore",
            "strategy": f"hs_{hs['trader_label']}",
            "status": "OPEN",
            "timestamp": hs.get("discovered_at", datetime.now(timezone.utc).isoformat()),
            "notes": f"Score:{hs['score']} | Trader:{hs['trader_label']} WR:{hs['trader_wr']}% PF:{hs['trader_pf']} | {hs['consensus_count']}x consensus",
            "category": "crypto",
            "trader_label": hs["trader_label"],
            "consensus_count": hs["consensus_count"],
            "history_trades": hs.get("history_trades", 0),
            "history_wr": hs.get("history_wr"),
            "history_avg_pnl": hs.get("history_avg_pnl"),
            "type_label": hs.get("type_label"),
        })
    hs_path = CT_DATA / "highscore_active_picks.json"
    with open(hs_path, "w", encoding="utf-8") as f:
        json.dump(hs_audit_picks, f, indent=2, default=str)
    print(f"  [AUDIT] Wrote {len(hs_audit_picks)} high-score picks to highscore_active_picks.json")

    # ========== HISTORICAL PICK TRACKER ==========
    # Tracks what would have happened if we followed every high-score pick
    history_path = CT_DATA / "highscore_pick_history.json"
    try:
        existing_history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
    except Exception:
        existing_history = []

    # Build lookup of existing entries by unique key
    existing_keys = {}
    for i, eh in enumerate(existing_history):
        key = f"{eh.get('symbol')}:{eh.get('direction')}:{eh.get('entry_price')}:{eh.get('strategy')}"
        existing_keys[key] = i

    now_iso = datetime.now(timezone.utc).isoformat()
    # Current high-score pick keys (still active)
    active_hs_keys = set()

    for hs in high_score_picks:
        key = f"{hs['symbol']}:{hs['direction']}:{hs['entry_price']}:{hs.get('strategy','')}"
        active_hs_keys.add(key)

        if key in existing_keys:
            # Update existing entry with latest PnL
            idx = existing_keys[key]
            existing_history[idx]["current_pnl"] = hs["pnl_pct"]
            existing_history[idx]["current_score"] = hs["score"]
            existing_history[idx]["last_updated"] = now_iso
            existing_history[idx]["status"] = "ACTIVE"
            # Track PnL snapshots (max 100 per pick)
            snapshots = existing_history[idx].get("pnl_snapshots", [])
            snapshots.append({"ts": now_iso, "pnl": hs["pnl_pct"]})
            existing_history[idx]["pnl_snapshots"] = snapshots[-100:]
        else:
            # New pick — record entry
            existing_history.append({
                "symbol": hs["symbol"],
                "direction": hs["direction"],
                "entry_price": hs["entry_price"],
                "take_profit": hs.get("take_profit"),
                "stop_loss": hs.get("stop_loss"),
                "entry_score": hs["score"],
                "score_breakdown": hs.get("score_breakdown", {}),
                "current_score": hs["score"],
                "current_pnl": hs["pnl_pct"],
                "peak_pnl": hs["pnl_pct"],
                "trader_label": hs["trader_label"],
                "trader_wr": hs["trader_wr"],
                "consensus_count": hs["consensus_count"],
                "type_label": hs["type_label"],
                "strategy": hs.get("strategy", ""),
                "entered_at": now_iso,
                "discovered_at": hs.get("discovered_at", now_iso),
                "last_updated": now_iso,
                "status": "ACTIVE",
                "pnl_snapshots": [{"ts": now_iso, "pnl": hs["pnl_pct"]}],
            })

    # Mark picks that are no longer in the high-score list
    for eh in existing_history:
        key = f"{eh.get('symbol')}:{eh.get('direction')}:{eh.get('entry_price')}:{eh.get('strategy','')}"
        if key not in active_hs_keys and eh.get("status") == "ACTIVE":
            # Update final PnL from live price
            sym = eh.get("symbol", "")
            entry = eh.get("entry_price", 0)
            direction = eh.get("direction", "")
            try:
                entry = float(entry) if entry else 0
            except (ValueError, TypeError):
                entry = 0
            current_price = get_live_price(sym)
            final_pnl = calc_unrealized_pnl(entry, current_price, direction) if entry and current_price else eh.get("current_pnl", 0)
            eh["status"] = "CLOSED"
            eh["closed_at"] = now_iso
            eh["final_pnl"] = round(final_pnl, 2)
            eh["current_pnl"] = round(final_pnl, 2)
        # Track peak PnL
        if eh.get("current_pnl", 0) > eh.get("peak_pnl", 0):
            eh["peak_pnl"] = eh["current_pnl"]

    # Save history
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(existing_history, f, indent=2, default=str)

    # Calculate tracker stats
    total_tracked = len(existing_history)
    active_tracked = sum(1 for e in existing_history if e.get("status") == "ACTIVE")
    closed_tracked = sum(1 for e in existing_history if e.get("status") == "CLOSED")
    closed_entries = [e for e in existing_history if e.get("status") == "CLOSED"]
    active_entries = [e for e in existing_history if e.get("status") == "ACTIVE"]
    wins = sum(1 for e in closed_entries if e.get("final_pnl", 0) > 0)
    closed_wr = round(wins / max(len(closed_entries), 1) * 100, 1)
    avg_pnl_closed = round(sum(e.get("final_pnl", 0) for e in closed_entries) / max(len(closed_entries), 1), 2) if closed_entries else 0
    avg_pnl_active = round(sum(e.get("current_pnl", 0) for e in active_entries) / max(len(active_entries), 1), 2) if active_entries else 0
    total_pnl = round(sum(e.get("final_pnl", e.get("current_pnl", 0)) for e in existing_history), 2)

    tracker_stats = {
        "total_picks_tracked": total_tracked,
        "active": active_tracked,
        "closed": closed_tracked,
        "closed_win_rate": closed_wr,
        "avg_pnl_closed": avg_pnl_closed,
        "avg_pnl_active": avg_pnl_active,
        "total_pnl": total_pnl,
        "history": existing_history[-20:],  # Last 20 for frontend display
    }
    portfolio["highscore_tracker"] = tracker_stats
    print(f"  [TRACKER] {total_tracked} picks tracked ({active_tracked} active, {closed_tracked} closed, WR:{closed_wr}%)")

    # Write reverse-engineered clone picks for audit dashboard
    # These get a LOWER confidence score until proven
    clone_audit_picks = []
    clone_consensus, clone_consensus_labels = build_copytrader_consensus_maps(unique_picks)
    clone_picks_all = [p for p in unique_picks if classify_pick(p) == "our_clone"]
    for cp in clone_picks_all:
        sym = cp.get("symbol", "")
        entry = cp.get("entry_price", 0)
        try:
            entry = float(entry) if entry else 0
        except (ValueError, TypeError):
            entry = 0
        direction = cp.get("direction", "").upper()
        current_price = get_live_price(sym)
        pnl = calc_unrealized_pnl(entry, current_price, direction) if entry and current_price else 0

        trader_label = extract_copytrader_label(
            cp.get("strategy", ""),
            cp.get("clone_source_trader", ""),
        )
        history_stats, history_basis = lookup_copytrader_history(
            history_scorebook,
            strategy=cp.get("strategy", ""),
            trader_label=trader_label,
            type_label="OUR CLONE",
        )
        consensus_key = f"{sym}:{direction}"
        consensus_count = clone_consensus.get(consensus_key, 1)
        consensus_traders = clone_consensus_labels.get(consensus_key, [])

        clone_score = 28
        clone_score += copytrader_history_bonus(history_stats)
        if pnl > 0:
            clone_score += min(pnl * 3, 10)
        elif pnl < 0:
            clone_score += max(pnl * 1.5, -6)

        if history_stats and history_stats.get("trades", 0) >= 10:
            max_clone_score = 70
        elif history_stats and history_stats.get("trades", 0) >= 3:
            max_clone_score = 60
        else:
            max_clone_score = 50
        clone_score = max(10, min(clone_score, max_clone_score))

        history_note = ""
        if history_stats:
            history_note = (
                f" | Hist WR:{history_stats['win_rate']*100:.0f}%/"
                f"{history_stats['trades']} Avg:{history_stats['avg_pnl']:+.2f}%"
            )

        clone_audit_picks.append({
            "symbol": sym,
            "direction": direction,
            "entry_price": entry,
            "current_price": current_price,
            "pnl_pct": round(pnl, 2),
            "take_profit": cp.get("take_profit"),
            "stop_loss": cp.get("stop_loss"),
            "confidence": round(clone_score, 1),
            "source_system": "copy_trader_clones",
            "strategy": cp.get("strategy", "clone_unknown"),
            "status": "OPEN",
            "timestamp": cp.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "notes": f"Reverse-engineered clone | PnL:{pnl:+.2f}%{history_note}",
            "category": "crypto",
            "trader_label": trader_label,
            "consensus_count": consensus_count,
            "consensus_traders": consensus_traders,
            "history_trades": history_stats["trades"] if history_stats else 0,
            "history_wr": round(history_stats["win_rate"] * 100, 1) if history_stats else None,
            "history_avg_pnl": round(history_stats["avg_pnl"], 2) if history_stats else None,
            "history_basis": history_basis,
            "type_label": "OUR CLONE",
        })
    clone_path = CT_DATA / "clone_active_picks.json"
    with open(clone_path, "w", encoding="utf-8") as f:
        json.dump(clone_audit_picks, f, indent=2, default=str)
    print(f"  [AUDIT] Wrote {len(clone_audit_picks)} clone picks to clone_active_picks.json")

    # Build reverse-engineered summary for funds.html
    clone_profitable = sum(1 for c in clone_audit_picks if "PnL:+" in c.get("notes", ""))
    clone_wr = round(clone_profitable / max(len(clone_audit_picks), 1) * 100, 1)
    portfolio["reverse_engineered"] = {
        "total_clones": len(clone_audit_picks),
        "profitable": clone_profitable,
        "win_rate": clone_wr,
        "picks": [{
            "symbol": c["symbol"],
            "direction": c["direction"],
            "entry_price": c["entry_price"],
            "take_profit": c.get("take_profit"),
            "stop_loss": c.get("stop_loss"),
            "confidence": c["confidence"],
            "strategy": c["strategy"],
            "notes": c["notes"],
        } for c in clone_audit_picks],
    }

    # ── Variation Tournament: Paper trading portfolios testing strategy mutations ──
    variation_fwd_file = CT_DATA / "variation_forward_test.json"
    variation_audit_picks = []
    variation_tournament = {
        "total_variations": 0,
        "active": 0,
        "probation": 0,
        "promoted": 0,
        "star": 0,
        "killed": 0,
        "open_positions": 0,
        "total_trades": 0,
        "total_pnl_usd": 0,
        "variations": [],
    }
    if variation_fwd_file.exists():
        try:
            with open(variation_fwd_file, "r", encoding="utf-8") as f:
                vdata = json.load(f)
            vsummary = vdata.get("summary", {})
            variation_tournament.update({
                "total_variations": vsummary.get("total_variations", 0),
                "active": vsummary.get("active", 0),
                "probation": vsummary.get("probation", 0),
                "promoted": vsummary.get("promoted", 0),
                "star": vsummary.get("star", 0),
                "killed": vsummary.get("killed", 0),
                "open_positions": vsummary.get("open_positions", 0),
                "total_trades": vsummary.get("total_trades", 0),
                "total_pnl_usd": round(vsummary.get("total_pnl_usd", 0), 2),
                "updated_at": vdata.get("updated_at", ""),
            })
            # Build per-variation summary for dashboard display
            for var_id, var_state in vdata.get("variations", {}).items():
                params = var_state.get("params", {})
                stats = var_state.get("stats", {})
                status = var_state.get("status", "ACTIVE")
                variation_tournament["variations"].append({
                    "id": var_id,
                    "source_trader": params.get("source_trader", ""),
                    "coin": params.get("coin", ""),
                    "direction": params.get("direction", ""),
                    "variation_type": params.get("variation_type", ""),
                    "tp_pct": params.get("tp_pct", 0),
                    "sl_pct": params.get("sl_pct", 0),
                    "max_hold_hours": params.get("max_hold_hours", 0),
                    "session": params.get("session", ""),
                    "capital": var_state.get("capital", 1000),
                    "trades": stats.get("trades", 0),
                    "wins": stats.get("wins", 0),
                    "wr": stats.get("wr", 0),
                    "pnl_pct": stats.get("pnl_pct", 0),
                    "pnl_usd": stats.get("pnl_usd", 0),
                    "status": status,
                    "has_position": var_state.get("position") is not None,
                })
                # Generate audit-compatible picks for active/promoted/star variations with positions
                pos = var_state.get("position")
                if pos and status not in ("KILLED",):
                    # Variation confidence: base 25 for active, 40 for promoted, 55 for star
                    var_conf = 25 if status == "ACTIVE" else 35 if status == "PROBATION" else 40 if status == "PROMOTED" else 55
                    # Bonus for WR
                    if stats.get("wr", 0) > 0.6:
                        var_conf += 10
                    var_conf = min(var_conf, 60)  # cap until proven
                    variation_audit_picks.append({
                        "symbol": params.get("coin", ""),
                        "direction": pos.get("direction", "LONG"),
                        "entry_price": pos.get("entry_price", 0),
                        "take_profit": pos.get("tp_price", 0),
                        "stop_loss": pos.get("sl_price", 0),
                        "confidence": var_conf,
                        "source_system": "copy_trader_variations",
                        "strategy": f"variation_{params.get('variation_type', 'base')}_{params.get('source_trader', '')}",
                        "status": "OPEN",
                        "timestamp": pos.get("opened_at", datetime.now(timezone.utc).isoformat()),
                        "notes": f"Variation: {params.get('variation_type','')} | WR:{stats.get('wr',0)*100:.0f}% | {status}",
                        "category": "crypto",
                    })
            # Sort variations: star > promoted > active, then by PnL
            status_order = {"STAR": 0, "PROMOTED": 1, "ACTIVE": 2, "PROBATION": 3, "KILLED": 4}
            variation_tournament["variations"].sort(
                key=lambda v: (status_order.get(v["status"], 5), -v["pnl_pct"])
            )
            print(f"  [VARIATIONS] {variation_tournament['total_variations']} variations | "
                  f"Active:{variation_tournament['active']} Promoted:{variation_tournament['promoted']} "
                  f"Star:{variation_tournament['star']} Killed:{variation_tournament['killed']} | "
                  f"Trades:{variation_tournament['total_trades']} PnL:${variation_tournament['total_pnl_usd']:.2f}")
        except Exception as e:
            print(f"  [WARN] Failed to load variation forward test: {e}")

    # Save variation audit picks
    variation_path = CT_DATA / "variation_active_picks.json"
    with open(variation_path, "w", encoding="utf-8") as f:
        json.dump(variation_audit_picks, f, indent=2, default=str)
    if variation_audit_picks:
        print(f"  [AUDIT] Wrote {len(variation_audit_picks)} variation picks to variation_active_picks.json")

    portfolio["variation_tournament"] = variation_tournament

    # Build patterns
    patterns = build_patterns(unique_picks, qualified)

    # Save to alpha_engine/data/
    ALPHA_DATA.mkdir(parents=True, exist_ok=True)

    with open(ALPHA_DATA / "portfolio_copytrader_dashboard.json", "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)
    print(f"[OK] Wrote portfolio_copytrader_dashboard.json ({len(portfolio['portfolios'])} sources)")
    for p in portfolio["portfolios"]:
        tp = p.get("their_positions", {})
        oc = p.get("our_clones", {})
        print(f"     {p['name']}: their_positions={tp.get('open',0)} open / {tp.get('closed',0)} closed | "
              f"our_clones={oc.get('open',0)} open / {oc.get('closed',0)} closed")

    with open(ALPHA_DATA / "copy_trader_patterns.json", "w", encoding="utf-8") as f:
        json.dump(patterns, f, indent=2)
    print(f"[OK] Wrote copy_trader_patterns.json ({patterns['total_picks_tracked']} picks, "
          f"{patterns.get('their_positions_count', 0)} their + {patterns.get('our_clones_count', 0)} clones, "
          f"{patterns['consensus_picks']} consensus)")

    try:
        from consensus_pick_builder import run as build_consensus_picks

        consensus_output = build_consensus_picks()
        print(f"[OK] Refreshed consensus_active_picks.json ({consensus_output.get('total_consensus_picks', 0)} picks)")
    except Exception as e:
        print(f"[WARN] Failed to refresh consensus_active_picks.json: {e}")

    try:
        from copytrader_lesson_extractor import build_lessons_and_mutations

        lesson_output = build_lessons_and_mutations()
        print(
            f"[OK] Refreshed copytrader lessons "
            f"({lesson_output['lessons'].get('total_lessons', 0)} lessons, "
            f"{lesson_output['mutations'].get('total_mutations', 0)} mutations)"
        )
    except Exception as e:
        print(f"[WARN] Failed to refresh copytrader lessons/mutations: {e}")


if __name__ == "__main__":
    main()
