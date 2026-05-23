"""
Copy Trader Consensus + Prediction Market Integration
- Reads copy_trader_intel/data/copytrader_database.json (schema: crypto_traders + forex_traders)
- Scores traders by edge_score (pre-computed composite), win_rate, drawdown
- Builds consensus picks where 2+ top traders all hold the same clean asset symbol
- Cross-references with prediction market probability signals
- Outputs ranked picks + high-certainty tier
"""
import json
import os
import math
from datetime import datetime
from collections import defaultdict

# --- Config ---
INPUT_DB = "copy_trader_intel/data/copytrader_database.json"
PM_DATA = "alpha_engine/data/prediction_market_picks.json"
OUT_FILE = "audit_dashboard/data/copytrade_pm_consensus.json"
HIGH_CERTAINTY_FILE = "audit_dashboard/data/copy_pm_high_certainty_candidates.json"

# Quality gates
MIN_TRADER_EDGE_SCORE = 60   # edge_score >= 60 (pre-computed composite quality)
MIN_TRADER_WR = 0.50         # 50% win rate (0-1 scale after normalization)
MAX_DRAWDOWN = 0.50          # 50% max drawdown (fraction)
MIN_CONSENSUS = 2            # minimum traders holding same symbol
MIN_PM_PROB = 0.60           # prediction market probability threshold


def _clean_symbols(coins_traded):
    """Extract clean, exchange-agnostic ticker symbols from coins_traded list."""
    clean = []
    for c in (coins_traded or []):
        if not isinstance(c, str):
            continue
        c = c.upper().strip()
        # Skip Hyperliquid numeric IDs (@107), compound IDs (xyz:MU), pairs (PURR/USDC)
        if c.startswith("@") or ":" in c or "/" in c:
            continue
        base = c.replace("-", "").replace("_", "")
        if base.isalnum() and 2 <= len(c) <= 12:
            clean.append(c)
    return clean


def _trader_score(edge_score, wr, dd, trades):
    """Composite trader quality score returning value in 0-1 range."""
    es_score = edge_score / 100.0
    wr_score = max(0.0, (wr - 0.5) * 2.0)   # 0 at 50% WR, 1.0 at 100% WR
    dd_score = max(0.0, 1.0 - dd * 2.0)      # 1.0 at 0 DD, 0 at 50% DD
    size_score = min(math.log10(max(trades, 1)) / 4.0, 1.0)
    return round(es_score * 0.40 + wr_score * 0.35 + dd_score * 0.15 + size_score * 0.10, 4)


def load_copytraders():
    """Load and filter quality copy traders from the actual DB schema."""
    if not os.path.exists(INPUT_DB):
        print(f"  WARNING: {INPUT_DB} not found")
        return []
    raw = json.load(open(INPUT_DB))
    all_traders = raw if isinstance(raw, list) else (
        raw.get("crypto_traders", []) + raw.get("forex_traders", [])
    )
    qualified = []
    for t in all_traders:
        if not isinstance(t, dict):
            continue
        edge_score = float(t.get("edge_score", 0) or 0)
        wr_raw = float(t.get("win_rate", 0) or 0)
        wr = wr_raw / 100.0 if wr_raw > 1.0 else wr_raw
        # max_drawdown_pct stored in percentage-point scale (e.g. 0.87 = 0.87%)
        dd_raw = float(t.get("max_drawdown_pct", t.get("max_drawdown", 50)) or 50)
        dd = dd_raw / 100.0
        trades = int(t.get("total_trades", 0) or 0)
        coins = _clean_symbols(t.get("coins_traded", []))
        if (edge_score >= MIN_TRADER_EDGE_SCORE
                and wr >= MIN_TRADER_WR
                and dd <= MAX_DRAWDOWN
                and trades >= 20):
            qualified.append({
                "trader_id": t.get("trader_id", t.get("name", "unknown")),
                "edge_score": edge_score,
                "win_rate": wr,
                "max_drawdown": dd,
                "trades": trades,
                "positions": coins,
                "source": t.get("platform", "unknown"),
                "score": _trader_score(edge_score, wr, dd, trades),
                "profit_factor": float(t.get("profit_factor", 1.0) or 1.0),
            })
    qualified.sort(key=lambda x: -x["score"])
    print(f"  Copy traders: {len(all_traders)} loaded, {len(qualified)} qualified")
    return qualified[:50]


def build_consensus(traders):
    """Find symbols held by >= MIN_CONSENSUS top traders."""
    symbol_map = defaultdict(list)
    for trader in traders:
        for sym in trader.get("positions", []):
            symbol_map[sym].append({
                "trader_id": trader["trader_id"],
                "score": trader["score"],
                "edge_score": trader["edge_score"],
            })
    consensus = {}
    for sym, holders in symbol_map.items():
        if len(holders) >= MIN_CONSENSUS:
            total_score = sum(h["score"] for h in holders)
            avg_edge = sum(h["edge_score"] for h in holders) / len(holders)
            consensus[sym] = {
                "symbol": sym,
                "trader_count": len(holders),
                "combined_score": round(total_score, 4),
                "avg_edge_score": round(avg_edge, 2),
                "dominant_direction": "long",
                "traders": [h["trader_id"] for h in holders],
                "source": "copy_trader_consensus",
            }
    return consensus


def load_prediction_market():
    """Load prediction market signals."""
    if not os.path.exists(PM_DATA):
        return {}
    raw = json.load(open(PM_DATA))
    picks = raw if isinstance(raw, list) else raw.get("picks", [])
    pm_map = {}
    for pick in picks:
        if not isinstance(pick, dict):
            continue
        sym = pick.get("symbol", "").upper().replace("USDT", "").replace("USD", "")
        prob = float(pick.get("probability", pick.get("confidence", 0)) or 0)
        if prob > 1.0:
            prob = prob / 100.0
        direction = pick.get("direction", pick.get("signal_type", "long")).lower()
        direction = "short" if direction in ("sell", "short") else "long"
        if sym and prob >= MIN_PM_PROB:
            pm_map[sym] = {
                "symbol": sym,
                "probability": round(prob, 3),
                "direction": direction,
                "source": pick.get("source", "prediction_market"),
                "raw_symbol": pick.get("symbol", ""),
            }
    print(f"  Prediction market: {len(pm_map)} signals above {MIN_PM_PROB:.0%} threshold")
    return pm_map


def score_combined_picks(consensus, pm_signals):
    """Score picks combining copy trader consensus + prediction market signals."""
    all_symbols = set(consensus.keys()) | set(pm_signals.keys())
    scored = []
    for sym in all_symbols:
        ct = consensus.get(sym)
        pm = pm_signals.get(sym)
        sources = []
        certainty_score = 0.0
        direction = "long"
        if ct:
            sources.append("copy_trader")
            certainty_score += ct["combined_score"] * 0.7 + (ct["avg_edge_score"] / 100.0) * 0.3
            direction = ct["dominant_direction"]
        if pm:
            sources.append("prediction_market")
            certainty_score += pm["probability"] * 0.8
            direction = pm["direction"]
        scored.append({
            "symbol": sym,
            "direction": direction,
            "certainty_score": round(certainty_score, 4),
            "sources": sources,
            "source_count": len(sources),
            "copy_trader_data": ct,
            "prediction_market_data": pm,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        })
    scored.sort(key=lambda x: -x["certainty_score"])
    return scored


def classify_certainty(picks):
    """Split into HIGH / MEDIUM / LOW certainty tiers.
    certainty_score is cumulative sum of trader scores (can exceed 1.0 with many holders).
    HIGH: score >= 1.5 (strong consensus) OR score >= 0.5 with 2+ sources.
    MEDIUM: score >= 0.20 (some support).
    """
    high = [p for p in picks if p["certainty_score"] >= 1.5
            or (p["certainty_score"] >= 0.5 and p["source_count"] >= 2)]
    high_syms = {p["symbol"] for p in high}
    medium = [p for p in picks if p["symbol"] not in high_syms and p["certainty_score"] >= 0.20]
    low = [p for p in picks if p["symbol"] not in high_syms and p["certainty_score"] < 0.20]
    return {"HIGH": high, "MEDIUM": medium, "LOW": low}


def main():
    print("Loading copy traders ...")
    traders = load_copytraders()
    print("Building consensus ...")
    consensus = build_consensus(traders)
    print(f"  Consensus symbols: {len(consensus)}")
    print("Loading prediction market signals ...")
    pm_signals = load_prediction_market()
    print("Scoring combined picks ...")
    scored = score_combined_picks(consensus, pm_signals)
    tiers = classify_certainty(scored)
    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "strategy": "copytrade_pm_consensus",
        "stats": {
            "qualified_traders": len(traders),
            "consensus_symbols": len(consensus),
            "pm_signals": len(pm_signals),
            "total_picks": len(scored),
            "high_certainty": len(tiers["HIGH"]),
            "medium_certainty": len(tiers["MEDIUM"]),
        },
        "all_picks": scored[:50],
        "tiers": tiers,
    }
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {OUT_FILE}")
    hc_out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "high_certainty_picks": tiers["HIGH"],
        "medium_certainty_picks": tiers["MEDIUM"][:10],
        "count": len(tiers["HIGH"]),
        "min_score_threshold": 0.70,
        "min_sources": 2,
    }
    with open(HIGH_CERTAINTY_FILE, "w") as f:
        json.dump(hc_out, f, indent=2)
    print(f"Wrote {HIGH_CERTAINTY_FILE}")
    print(f"\nHigh-certainty picks: {len(tiers['HIGH'])}")
    for p in tiers["HIGH"][:10]:
        print(f"  {p['symbol']}: dir={p['direction']}, score={p['certainty_score']:.3f}, sources={p['sources']}")
    print(f"\nMedium-certainty picks: {len(tiers['MEDIUM'])}")
    for p in tiers["MEDIUM"][:10]:
        print(f"  {p['symbol']}: dir={p['direction']}, score={p['certainty_score']:.3f}")
    return out


if __name__ == "__main__":
    main()
