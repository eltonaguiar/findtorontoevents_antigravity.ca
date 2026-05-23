#!/usr/bin/env python3
"""
Winning Entry Criteria Backtester
=================================
Loads all closed picks with their indicator data and tests thousands of
filter combinations to find which entry criteria would have WON the
majority of trades. Outputs a ranked table + actionable recommendations.

Pure Python + numpy only (no pandas/scipy).
"""
import sys, os, io, json, math, itertools, time
from collections import defaultdict, Counter
from pathlib import Path

# Windows UTF-8 fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import numpy as np
except ImportError:
    np = None  # fallback to pure python

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

# ─────────────────────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────────────────────

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError, ValueError) as exc:
        print(f"[WARN] Could not load {path}: {exc}")
        return []

def main():
    t0 = time.time()

    closed_picks = load_json(DATA / "closed_picks.json")
    indicator_log = load_json(DATA / "indicator_correlation_log.json")
    ct_active = load_json(Path(BASE).parent / "copy_trader_intel" / "data" / "active_picks.json")

    print(f"Loaded {len(closed_picks)} closed picks, {len(indicator_log)} indicator logs, {len(ct_active)} CT active picks")

    # Filter to picks with outcome
    picks = [p for p in closed_picks if p.get("status") in ("WON", "LOST")]
    print(f"Picks with WON/LOST outcome: {len(picks)}")

    # ─────────────────────────────────────────────────────────
    # 2. BUILD INDICATOR INDEX from correlation log
    # ─────────────────────────────────────────────────────────

    # Map pick_id -> indicators from the correlation log
    ind_map = {}
    for rec in indicator_log:
        pid = rec.get("pick_id", "")
        inds = rec.get("indicators", {})
        if pid and inds:
            ind_map[pid] = inds

    # Also index by symbol for fallback matching
    ind_by_sym = defaultdict(list)
    for rec in indicator_log:
        sym = rec.get("symbol", "")
        if sym:
            ind_by_sym[sym].append(rec.get("indicators", {}))

    # ─────────────────────────────────────────────────────────
    # 3. BUILD COPY TRADER CONSENSUS from closed picks data
    # ─────────────────────────────────────────────────────────
    # For historical consensus, we use the pick's own consensus_count if available,
    # or count how many copy trader picks exist for the same symbol+direction in closed data

    # Build historical consensus: for each (date, symbol, direction), count copy traders
    ct_closed = [p for p in closed_picks if "copy" in p.get("strategy", "").lower()]
    date_sym_dir_count = Counter()
    for p in ct_closed:
        key = (p.get("entry_date", ""), p.get("symbol", ""),
               (p.get("direction") or p.get("signal_type", "")).upper())
        date_sym_dir_count[key] += 1

    # ─────────────────────────────────────────────────────────
    # 4. EXTRACT FEATURES FOR EACH PICK
    # ─────────────────────────────────────────────────────────

    enriched = []
    for p in picks:
        feat = {}
        feat["status"] = p["status"]
        feat["pnl_pct"] = p.get("pnl_pct", 0) or 0
        feat["strategy"] = p.get("strategy", "unknown")
        feat["symbol"] = p.get("symbol", "")
        feat["confidence"] = p.get("confidence")

        # Direction normalization
        raw_dir = (p.get("direction") or p.get("signal_type") or "").upper()
        if raw_dir in ("BUY", "LONG"):
            feat["direction"] = "BUY"
        elif raw_dir in ("SELL", "SHORT"):
            feat["direction"] = "SELL"
        else:
            feat["direction"] = "BUY"  # default

        # --- RSI(14) ---
        rsi14 = p.get("rsi_at_entry")
        if rsi14 is None and p.get("rsi") is not None:
            rsi14 = p["rsi"]
        feat["rsi_14"] = rsi14

        # --- RSI(2) ---
        rsi2 = p.get("rsi2")
        feat["rsi_2"] = rsi2

        # --- Volume ratio ---
        feat["volume_ratio"] = p.get("volume_ratio")

        # --- Bollinger %B ---
        feat["bb_pct_b"] = p.get("bb_pct_b")

        # --- ADX ---
        feat["adx"] = p.get("adx")

        # --- Risk/Reward ---
        tp = p.get("take_profit")
        sl = p.get("stop_loss")
        ep = p.get("entry_price")
        if tp and sl and ep and ep > 0:
            tp_dist = abs(tp - ep)
            sl_dist = abs(sl - ep)
            feat["risk_reward"] = tp_dist / sl_dist if sl_dist > 0 else None
        else:
            feat["risk_reward"] = p.get("risk_reward")

        # --- ML features (richer source) ---
        ml_feat = p.get("ml_features_at_entry")
        if ml_feat:
            if isinstance(ml_feat, str):
                try:
                    ml_feat = json.loads(ml_feat)
                except:
                    ml_feat = {}
            if isinstance(ml_feat, dict):
                if feat["rsi_14"] is None and ml_feat.get("rsi_at_entry") is not None:
                    feat["rsi_14"] = ml_feat["rsi_at_entry"]
                if feat["volume_ratio"] is None and ml_feat.get("volume_ratio") is not None:
                    feat["volume_ratio"] = ml_feat["volume_ratio"]
                if feat["bb_pct_b"] is None and ml_feat.get("bb_pct_b") is not None:
                    feat["bb_pct_b"] = ml_feat["bb_pct_b"]
                if ml_feat.get("ema_position") is not None:
                    feat["ema_alignment"] = ml_feat["ema_position"]
                if ml_feat.get("entry_distance_vwap") is not None:
                    feat["vwap_deviation_pct"] = ml_feat["entry_distance_vwap"]
                if ml_feat.get("hma_slope") is not None:
                    feat["hma_slope"] = ml_feat["hma_slope"]
                if ml_feat.get("galaxy_score") is not None:
                    feat["galaxy_score"] = ml_feat["galaxy_score"]
                if ml_feat.get("rsi_1h") is not None and feat["rsi_14"] is None:
                    feat["rsi_14"] = ml_feat["rsi_1h"]
                if ml_feat.get("funding_rate") is not None:
                    feat["funding_rate"] = ml_feat["funding_rate"]
                if ml_feat.get("orderbook_imbalance") is not None:
                    feat["orderbook_imbalance"] = ml_feat["orderbook_imbalance"]
                if ml_feat.get("spread_pct") is not None:
                    feat["spread_pct"] = ml_feat["spread_pct"]
                if ml_feat.get("wick_ratio") is not None:
                    feat["wick_ratio"] = ml_feat["wick_ratio"]
                if ml_feat.get("vpin") is not None:
                    feat["vpin"] = ml_feat["vpin"]

        # --- Indicator correlation log (match by pick_id or symbol) ---
        pid = p.get("id", "")
        ind = ind_map.get(pid)
        if not ind:
            # Try matching by symbol substring
            sym = p.get("symbol", "")
            sym_recs = ind_by_sym.get(sym, [])
            if sym_recs:
                ind = sym_recs[0]

        if ind and isinstance(ind, dict):
            if feat["rsi_14"] is None and ind.get("rsi_14") is not None:
                feat["rsi_14"] = ind["rsi_14"]
            if feat["rsi_2"] is None and ind.get("rsi_2") is not None:
                feat["rsi_2"] = ind["rsi_2"]
            if feat["bb_pct_b"] is None and ind.get("bollinger_pct_b") is not None:
                feat["bb_pct_b"] = ind["bollinger_pct_b"]
            if feat["volume_ratio"] is None and ind.get("volume_ratio") is not None:
                feat["volume_ratio"] = ind["volume_ratio"]
            if ind.get("ema_alignment") is not None:
                feat.setdefault("ema_alignment", ind["ema_alignment"])
            if ind.get("stoch_k") is not None:
                feat["stoch_k"] = ind["stoch_k"]
            if ind.get("adx") is not None and feat["adx"] is None:
                feat["adx"] = ind["adx"]
            if ind.get("vwap_deviation_pct") is not None:
                feat.setdefault("vwap_deviation_pct", ind["vwap_deviation_pct"])
            if ind.get("consecutive_candles") is not None:
                feat["consecutive_candles"] = ind["consecutive_candles"]

        # --- Stoch K from pick fields ---
        if "stoch_k" not in feat:
            feat["stoch_k"] = None

        # --- Williams %R (compute from RSI if not available) ---
        if feat["rsi_14"] is not None:
            feat["williams_pct_r"] = -(100 - feat["rsi_14"])
        else:
            feat["williams_pct_r"] = None

        # --- EMA alignment ---
        feat.setdefault("ema_alignment", None)

        # --- VWAP deviation ---
        feat.setdefault("vwap_deviation_pct", None)
        if feat["vwap_deviation_pct"] is None:
            feat["vwap_deviation_pct"] = p.get("entry_distance_vwap")

        # --- Consecutive candles ---
        feat.setdefault("consecutive_candles", None)

        # --- Copy trader consensus ---
        ct_consensus = p.get("consensus_count")
        if ct_consensus is None:
            # Count from date/symbol/direction
            key = (p.get("entry_date", ""), p.get("symbol", ""), feat["direction"])
            ct_consensus = date_sym_dir_count.get(key, 0)
        feat["ct_consensus"] = ct_consensus

        # --- Regime ---
        feat["regime"] = p.get("regime_at_entry") or p.get("regime_at_signal") or "unknown"

        # --- Source system ---
        feat["source_system"] = p.get("source_system", "")

        # --- ML score ---
        feat["ml_score"] = p.get("ml_score")

        # --- Elite score ---
        feat["elite_score"] = p.get("elite_score")

        # --- Entry timing score ---
        feat["entry_timing_score"] = p.get("entry_timing_score")

        # --- Funding rate ---
        feat.setdefault("funding_rate", p.get("funding_rate") or p.get("funding_rate_pct"))

        # --- Hold days ---
        feat["hold_days"] = p.get("hold_days")

        enriched.append(feat)

    # ─────────────────────────────────────────────────────────
    # 5. STATS HELPERS
    # ─────────────────────────────────────────────────────────

    def compute_stats(subset):
        """Compute win rate, avg pnl, profit factor, expected value."""
        if not subset:
            return None
        n = len(subset)
        wins = sum(1 for s in subset if s["status"] == "WON")
        wr = wins / n if n > 0 else 0
        pnls = [s["pnl_pct"] for s in subset]
        avg_pnl = sum(pnls) / n if n > 0 else 0
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0)
        exp_val = wr * (sum(p for p in pnls if p > 0) / max(wins, 1)) - (1 - wr) * (abs(sum(p for p in pnls if p < 0)) / max(n - wins, 1)) if n > 0 else 0
        return {
            "trades": n,
            "wins": wins,
            "losses": n - wins,
            "wr_pct": round(wr * 100, 1),
            "avg_pnl": round(avg_pnl, 4),
            "profit_factor": round(min(pf, 99.9), 2),
            "exp_val": round(exp_val, 4),
            "total_pnl": round(sum(pnls), 4),
        }

    # ─────────────────────────────────────────────────────────
    # 6. BASELINE
    # ─────────────────────────────────────────────────────────

    baseline = compute_stats(enriched)
    print(f"\n{'='*80}")
    print(f"BASELINE (all {baseline['trades']} closed picks)")
    print(f"  WR: {baseline['wr_pct']}% | Avg PnL: {baseline['avg_pnl']*100:.2f}% | PF: {baseline['profit_factor']} | ExpVal: {baseline['exp_val']*100:.2f}%")
    print(f"  Total PnL: {baseline['total_pnl']*100:.2f}%")
    print(f"{'='*80}")

    # ─────────────────────────────────────────────────────────
    # 7. NAMED FILTER TESTS
    # ─────────────────────────────────────────────────────────

    def safe_ge(val, threshold):
        return val is not None and val >= threshold

    def safe_le(val, threshold):
        return val is not None and val <= threshold

    def safe_between(val, lo, hi):
        return val is not None and lo <= val <= hi

    named_filters = {
        "a) CT consensus >= 3": lambda f: safe_ge(f["ct_consensus"], 3),
        "b) CT>=3 + RSI(14) 40-60": lambda f: safe_ge(f["ct_consensus"], 3) and safe_between(f["rsi_14"], 40, 60),
        "c) CT>=3 + VWAP dev > 0": lambda f: safe_ge(f["ct_consensus"], 3) and safe_ge(f["vwap_deviation_pct"], 0),
        "d) CT>=3 + BB%B 0.2-0.8": lambda f: safe_ge(f["ct_consensus"], 3) and safe_between(f["bb_pct_b"], 0.2, 0.8),
        "e) CT>=3 + Williams%R > -80": lambda f: safe_ge(f["ct_consensus"], 3) and safe_ge(f["williams_pct_r"], -80),
        "f) RSI(14)<35 + VolRatio>1.5": lambda f: safe_le(f["rsi_14"], 35) and safe_ge(f["volume_ratio"], 1.5),
        "g) RSI(2)<10 + EMA align>=3": lambda f: safe_le(f["rsi_2"], 10) and safe_ge(f["ema_alignment"], 3),
        "h) BB%B<0.1 + ADX<25": lambda f: safe_le(f["bb_pct_b"], 0.1) and safe_le(f["adx"], 25),
        "i) VWAP dev<-2% + consec>=2": lambda f: safe_le(f["vwap_deviation_pct"], -2) and safe_ge(f.get("consecutive_candles"), 2),
        "j) Conf>=0.80 + CT>=2": lambda f: safe_ge(f["confidence"], 0.80) and safe_ge(f["ct_consensus"], 2),
        "k) EMA align=4 + RSI 45-65": lambda f: f.get("ema_alignment") == 4 and safe_between(f["rsi_14"], 45, 65),
        "l) Stoch%K<20 + Will%R<-80": lambda f: safe_le(f["stoch_k"], 20) and safe_le(f["williams_pct_r"], -80),
        "m) BUY + CT>=3 + RSI<55": lambda f: f["direction"] == "BUY" and safe_ge(f["ct_consensus"], 3) and safe_le(f["rsi_14"], 55),
        "n) SELL + CT>=3 + RSI>55": lambda f: f["direction"] == "SELL" and safe_ge(f["ct_consensus"], 3) and safe_ge(f["rsi_14"], 55),
        "o) Any + CT>=4": lambda f: safe_ge(f["ct_consensus"], 4),
        # Additional useful combos
        "p) Conf>=0.70 + RSI 30-70": lambda f: safe_ge(f["confidence"], 0.70) and safe_between(f["rsi_14"], 30, 70),
        "q) VolRatio>2.0 + RSI<50": lambda f: safe_ge(f["volume_ratio"], 2.0) and safe_le(f["rsi_14"], 50),
        "r) ML score>=0.7 + Conf>=0.7": lambda f: safe_ge(f.get("ml_score"), 0.7) and safe_ge(f["confidence"], 0.7),
        "s) Risk/Reward>=2.0": lambda f: safe_ge(f.get("risk_reward"), 2.0),
        "t) CT>=3 + Conf>=0.70": lambda f: safe_ge(f["ct_consensus"], 3) and safe_ge(f["confidence"], 0.70),
        "u) BUY + RSI<40 + VolRatio>1.5": lambda f: f["direction"] == "BUY" and safe_le(f["rsi_14"], 40) and safe_ge(f["volume_ratio"], 1.5),
        "v) Conf>=0.80": lambda f: safe_ge(f["confidence"], 0.80),
        "w) VolRatio>3.0": lambda f: safe_ge(f["volume_ratio"], 3.0),
        "x) Copy trader strategy": lambda f: "copy" in f["strategy"].lower(),
        "y) ML score>=0.8": lambda f: safe_ge(f.get("ml_score"), 0.8),
        "z) Regime=trending": lambda f: "trend" in str(f.get("regime", "")).lower(),
        "aa) Elite score>=80": lambda f: safe_ge(f.get("elite_score"), 80),
        "bb) CT>=5": lambda f: safe_ge(f["ct_consensus"], 5),
        "cc) BUY + Conf>=0.75 + RSI<60": lambda f: f["direction"] == "BUY" and safe_ge(f["confidence"], 0.75) and safe_le(f["rsi_14"], 60),
        "dd) SELL + Conf>=0.75 + RSI>40": lambda f: f["direction"] == "SELL" and safe_ge(f["confidence"], 0.75) and safe_ge(f["rsi_14"], 40),
        "ee) Hold days<=1": lambda f: safe_le(f.get("hold_days"), 1),
        "ff) VolRatio>1.5 + BB%B<0.5": lambda f: safe_ge(f["volume_ratio"], 1.5) and safe_le(f["bb_pct_b"], 0.5),
        "gg) CT>=2 + VolRatio>1.0": lambda f: safe_ge(f["ct_consensus"], 2) and safe_ge(f["volume_ratio"], 1.0),
        "hh) Conf>=0.75 + VolRatio>1.5": lambda f: safe_ge(f["confidence"], 0.75) and safe_ge(f["volume_ratio"], 1.5),
    }

    print(f"\n{'='*80}")
    print("NAMED FILTER COMBINATIONS")
    print(f"{'='*80}")

    named_results = []
    for name, filt in named_filters.items():
        subset = [f for f in enriched if filt(f)]
        stats = compute_stats(subset)
        if stats and stats["trades"] >= 3:  # min 3 trades for significance
            named_results.append({"name": name, **stats})

    # Sort by expected value descending
    named_results.sort(key=lambda x: x["exp_val"], reverse=True)

    print(f"\n{'Rank':<5} {'Criteria':<45} {'Trades':<7} {'WR%':<7} {'AvgPnL':<9} {'PF':<7} {'ExpVal':<9} {'TotalPnL':<10}")
    print("-" * 100)
    for i, r in enumerate(named_results, 1):
        print(f"{i:<5} {r['name']:<45} {r['trades']:<7} {r['wr_pct']:<7} {r['avg_pnl']*100:>+7.2f}% {r['profit_factor']:<7} {r['exp_val']*100:>+7.2f}% {r['total_pnl']*100:>+8.2f}%")

    # ─────────────────────────────────────────────────────────
    # 8. PER-STRATEGY ANALYSIS
    # ─────────────────────────────────────────────────────────

    print(f"\n{'='*80}")
    print("PER-STRATEGY PERFORMANCE (min 5 trades)")
    print(f"{'='*80}")

    strat_groups = defaultdict(list)
    for f in enriched:
        strat_groups[f["strategy"]].append(f)

    strat_results = []
    for strat, group in strat_groups.items():
        stats = compute_stats(group)
        if stats and stats["trades"] >= 5:
            strat_results.append({"name": f"strat:{strat}", **stats})

    strat_results.sort(key=lambda x: x["exp_val"], reverse=True)

    print(f"\n{'Rank':<5} {'Strategy':<50} {'Trades':<7} {'WR%':<7} {'AvgPnL':<9} {'PF':<7} {'ExpVal':<9}")
    print("-" * 95)
    for i, r in enumerate(strat_results[:20], 1):
        print(f"{i:<5} {r['name'][:50]:<50} {r['trades']:<7} {r['wr_pct']:<7} {r['avg_pnl']*100:>+7.2f}% {r['profit_factor']:<7} {r['exp_val']*100:>+7.2f}%")

    # ─────────────────────────────────────────────────────────
    # 9. BRUTE FORCE PAIR SEARCH
    # ─────────────────────────────────────────────────────────

    print(f"\n{'='*80}")
    print("BRUTE FORCE INDICATOR PAIR SEARCH")
    print(f"{'='*80}")

    # Define indicator thresholds to test
    indicator_thresholds = {
        "rsi_14": {
            "field": "rsi_14",
            "levels": [
                ("RSI14<30", lambda v: v is not None and v < 30),
                ("RSI14<40", lambda v: v is not None and v < 40),
                ("RSI14 40-60", lambda v: v is not None and 40 <= v <= 60),
                ("RSI14>60", lambda v: v is not None and v > 60),
                ("RSI14>70", lambda v: v is not None and v > 70),
            ]
        },
        "rsi_2": {
            "field": "rsi_2",
            "levels": [
                ("RSI2<5", lambda v: v is not None and v < 5),
                ("RSI2<10", lambda v: v is not None and v < 10),
                ("RSI2<20", lambda v: v is not None and v < 20),
                ("RSI2>80", lambda v: v is not None and v > 80),
                ("RSI2>90", lambda v: v is not None and v > 90),
            ]
        },
        "volume_ratio": {
            "field": "volume_ratio",
            "levels": [
                ("VR>1.0", lambda v: v is not None and v > 1.0),
                ("VR>1.5", lambda v: v is not None and v > 1.5),
                ("VR>2.0", lambda v: v is not None and v > 2.0),
                ("VR>3.0", lambda v: v is not None and v > 3.0),
                ("VR>5.0", lambda v: v is not None and v > 5.0),
            ]
        },
        "confidence": {
            "field": "confidence",
            "levels": [
                ("Conf>=0.60", lambda v: v is not None and v >= 0.60),
                ("Conf>=0.65", lambda v: v is not None and v >= 0.65),
                ("Conf>=0.70", lambda v: v is not None and v >= 0.70),
                ("Conf>=0.75", lambda v: v is not None and v >= 0.75),
                ("Conf>=0.80", lambda v: v is not None and v >= 0.80),
            ]
        },
        "bb_pct_b": {
            "field": "bb_pct_b",
            "levels": [
                ("BB<0.1", lambda v: v is not None and v < 0.1),
                ("BB<0.3", lambda v: v is not None and v < 0.3),
                ("BB 0.2-0.8", lambda v: v is not None and 0.2 <= v <= 0.8),
                ("BB>0.7", lambda v: v is not None and v > 0.7),
                ("BB>0.9", lambda v: v is not None and v > 0.9),
            ]
        },
        "ct_consensus": {
            "field": "ct_consensus",
            "levels": [
                ("CT>=1", lambda v: v is not None and v >= 1),
                ("CT>=2", lambda v: v is not None and v >= 2),
                ("CT>=3", lambda v: v is not None and v >= 3),
                ("CT>=4", lambda v: v is not None and v >= 4),
                ("CT>=5", lambda v: v is not None and v >= 5),
            ]
        },
        "vwap_deviation_pct": {
            "field": "vwap_deviation_pct",
            "levels": [
                ("VWAP<-3%", lambda v: v is not None and v < -3),
                ("VWAP<-1%", lambda v: v is not None and v < -1),
                ("VWAP -1to1%", lambda v: v is not None and -1 <= v <= 1),
                ("VWAP>1%", lambda v: v is not None and v > 1),
                ("VWAP>3%", lambda v: v is not None and v > 3),
            ]
        },
        "ema_alignment": {
            "field": "ema_alignment",
            "levels": [
                ("EMA>=1", lambda v: v is not None and v >= 1),
                ("EMA>=2", lambda v: v is not None and v >= 2),
                ("EMA>=3", lambda v: v is not None and v >= 3),
                ("EMA=4", lambda v: v is not None and v == 4),
                ("EMA=0", lambda v: v is not None and v == 0),
            ]
        },
        "williams_pct_r": {
            "field": "williams_pct_r",
            "levels": [
                ("WR<-90", lambda v: v is not None and v < -90),
                ("WR<-80", lambda v: v is not None and v < -80),
                ("WR -80to-20", lambda v: v is not None and -80 <= v <= -20),
                ("WR>-20", lambda v: v is not None and v > -20),
                ("WR>-10", lambda v: v is not None and v > -10),
            ]
        },
        "stoch_k": {
            "field": "stoch_k",
            "levels": [
                ("SK<10", lambda v: v is not None and v < 10),
                ("SK<20", lambda v: v is not None and v < 20),
                ("SK 20-80", lambda v: v is not None and 20 <= v <= 80),
                ("SK>80", lambda v: v is not None and v > 80),
                ("SK>90", lambda v: v is not None and v > 90),
            ]
        },
        "ml_score": {
            "field": "ml_score",
            "levels": [
                ("ML>=0.5", lambda v: v is not None and v >= 0.5),
                ("ML>=0.6", lambda v: v is not None and v >= 0.6),
                ("ML>=0.7", lambda v: v is not None and v >= 0.7),
                ("ML>=0.8", lambda v: v is not None and v >= 0.8),
                ("ML>=0.9", lambda v: v is not None and v >= 0.9),
            ]
        },
        "risk_reward": {
            "field": "risk_reward",
            "levels": [
                ("RR>=1.0", lambda v: v is not None and v >= 1.0),
                ("RR>=1.5", lambda v: v is not None and v >= 1.5),
                ("RR>=2.0", lambda v: v is not None and v >= 2.0),
                ("RR>=2.5", lambda v: v is not None and v >= 2.5),
                ("RR>=3.0", lambda v: v is not None and v >= 3.0),
            ]
        },
        "direction": {
            "field": "direction",
            "levels": [
                ("BUY only", lambda v: v == "BUY"),
                ("SELL only", lambda v: v == "SELL"),
                ("any dir", lambda v: True),
                ("BUY only", lambda v: v == "BUY"),  # duplicate to pair with others
                ("SELL only", lambda v: v == "SELL"),
            ]
        },
        "adx": {
            "field": "adx",
            "levels": [
                ("ADX<15", lambda v: v is not None and v < 15),
                ("ADX<25", lambda v: v is not None and v < 25),
                ("ADX 25-50", lambda v: v is not None and 25 <= v <= 50),
                ("ADX>25", lambda v: v is not None and v > 25),
                ("ADX>40", lambda v: v is not None and v > 40),
            ]
        },
    }

    # Pre-compute: for each indicator+level, which picks pass
    level_masks = {}
    for ind_name, ind_info in indicator_thresholds.items():
        field = ind_info["field"]
        for level_name, level_fn in ind_info["levels"]:
            key = f"{ind_name}:{level_name}"
            mask = []
            for f in enriched:
                val = f.get(field)
                mask.append(level_fn(val))
            level_masks[key] = mask

    # Test all pairs
    ind_names = list(indicator_thresholds.keys())
    brute_results = []
    n_enriched = len(enriched)
    tests_run = 0

    for i in range(len(ind_names)):
        for j in range(i + 1, len(ind_names)):
            ind_a = ind_names[i]
            ind_b = ind_names[j]
            for la_name, _ in indicator_thresholds[ind_a]["levels"]:
                key_a = f"{ind_a}:{la_name}"
                mask_a = level_masks[key_a]
                for lb_name, _ in indicator_thresholds[ind_b]["levels"]:
                    key_b = f"{ind_b}:{lb_name}"
                    mask_b = level_masks[key_b]

                    # Combine masks
                    subset = [enriched[k] for k in range(n_enriched) if mask_a[k] and mask_b[k]]
                    tests_run += 1

                    if len(subset) >= 5:  # min 5 trades
                        stats = compute_stats(subset)
                        if stats and stats["wr_pct"] > baseline["wr_pct"]:
                            combo_name = f"{la_name} + {lb_name}"
                            brute_results.append({"name": combo_name, **stats})

    print(f"\nTested {tests_run} pair combinations")

    # Also test TRIPLES (top single filters x top pairs) — but limit scope
    # First get top 10 single filters
    single_results = []
    for ind_name, ind_info in indicator_thresholds.items():
        for level_name, _ in ind_info["levels"]:
            key = f"{ind_name}:{level_name}"
            mask = level_masks[key]
            subset = [enriched[k] for k in range(n_enriched) if mask[k]]
            if len(subset) >= 5:
                stats = compute_stats(subset)
                if stats:
                    single_results.append({"name": level_name, "key": key, **stats})

    single_results.sort(key=lambda x: x["exp_val"], reverse=True)

    # Test top 15 singles combined with each other as triples
    top_singles = single_results[:15]
    for i in range(len(top_singles)):
        for j in range(i+1, len(top_singles)):
            for k in range(j+1, min(j+5, len(top_singles))):  # limit triple combos
                key_a = top_singles[i]["key"]
                key_b = top_singles[j]["key"]
                key_c = top_singles[k]["key"]
                mask_a = level_masks[key_a]
                mask_b = level_masks[key_b]
                mask_c = level_masks[key_c]

                subset = [enriched[idx] for idx in range(n_enriched) if mask_a[idx] and mask_b[idx] and mask_c[idx]]
                tests_run += 1

                if len(subset) >= 4:
                    stats = compute_stats(subset)
                    if stats and stats["wr_pct"] > baseline["wr_pct"]:
                        combo_name = f"{top_singles[i]['name']} + {top_singles[j]['name']} + {top_singles[k]['name']}"
                        brute_results.append({"name": combo_name, **stats})

    print(f"Total tests (incl triples): {tests_run}")

    # Sort brute results by expectancy
    brute_results.sort(key=lambda x: x["exp_val"], reverse=True)

    # Deduplicate: keep only combos that select a DIFFERENT subset of trades
    # Use (trades, wins, total_pnl) as a fingerprint for the actual trade set
    seen_fingerprints = set()
    unique_brute = []
    for r in brute_results:
        fp = (r["trades"], r["wins"], r["total_pnl"])
        parts = frozenset(r["name"].split(" + "))
        if fp not in seen_fingerprints:
            seen_fingerprints.add(fp)
            unique_brute.append(r)
        elif parts not in {frozenset(u["name"].split(" + ")) for u in unique_brute}:
            # Allow if name is truly different even if same fingerprint (rare)
            pass

    print(f"\nTOP 30 BRUTE FORCE COMBINATIONS (beating baseline WR of {baseline['wr_pct']}%)")
    print(f"\n{'Rank':<5} {'Criteria':<55} {'Trades':<7} {'WR%':<7} {'AvgPnL':<9} {'PF':<7} {'ExpVal':<9}")
    print("-" * 100)
    for i, r in enumerate(unique_brute[:30], 1):
        print(f"{i:<5} {r['name'][:55]:<55} {r['trades']:<7} {r['wr_pct']:<7} {r['avg_pnl']*100:>+7.2f}% {r['profit_factor']:<7} {r['exp_val']*100:>+7.2f}%")

    # ─────────────────────────────────────────────────────────
    # 10. SINGLE INDICATOR ANALYSIS
    # ─────────────────────────────────────────────────────────

    print(f"\n{'='*80}")
    print("TOP SINGLE INDICATOR FILTERS")
    print(f"{'='*80}")
    print(f"\n{'Rank':<5} {'Filter':<35} {'Trades':<7} {'WR%':<7} {'AvgPnL':<9} {'PF':<7} {'ExpVal':<9}")
    print("-" * 80)
    for i, r in enumerate(single_results[:20], 1):
        print(f"{i:<5} {r['name']:<35} {r['trades']:<7} {r['wr_pct']:<7} {r['avg_pnl']*100:>+7.2f}% {r['profit_factor']:<7} {r['exp_val']*100:>+7.2f}%")

    # ─────────────────────────────────────────────────────────
    # 11. COMBINED TOP 20 — ALL SOURCES
    # ─────────────────────────────────────────────────────────

    all_results = []
    for r in named_results:
        all_results.append({**r, "source": "named"})
    for r in unique_brute[:50]:
        all_results.append({**r, "source": "brute_force"})
    for r in strat_results[:10]:
        all_results.append({**r, "source": "strategy"})

    # Sort by expectancy, require min 5 trades
    all_results = [r for r in all_results if r["trades"] >= 5]
    all_results.sort(key=lambda x: x["exp_val"], reverse=True)

    # Deduplicate grand ranking by trade fingerprint too
    seen_gfp = set()
    deduped_all = []
    for r in all_results:
        fp = (r["trades"], r.get("wins", 0), r.get("total_pnl", 0))
        if fp not in seen_gfp:
            seen_gfp.add(fp)
            deduped_all.append(r)
    all_results = deduped_all

    print(f"\n{'='*80}")
    print(f"GRAND RANKING — TOP 20 ENTRY CRITERIA (min 5 trades)")
    print(f"{'='*80}")
    print(f"\n{'Rank':<5} {'Criteria':<55} {'Trades':<7} {'WR%':<7} {'AvgPnL':<9} {'PF':<7} {'ExpVal':<9} {'Source':<12}")
    print("-" * 112)
    for i, r in enumerate(all_results[:20], 1):
        print(f"{i:<5} {r['name'][:55]:<55} {r['trades']:<7} {r['wr_pct']:<7} {r['avg_pnl']*100:>+7.2f}% {r['profit_factor']:<7} {r['exp_val']*100:>+7.2f}% {r['source']:<12}")

    # ─────────────────────────────────────────────────────────
    # 12. DATA COVERAGE REPORT
    # ─────────────────────────────────────────────────────────

    print(f"\n{'='*80}")
    print("DATA COVERAGE (how many of {0} picks have each indicator)".format(len(enriched)))
    print(f"{'='*80}")

    coverage_fields = [
        "rsi_14", "rsi_2", "volume_ratio", "bb_pct_b", "adx", "stoch_k",
        "ema_alignment", "vwap_deviation_pct", "consecutive_candles",
        "williams_pct_r", "ct_consensus", "confidence", "ml_score",
        "risk_reward", "funding_rate", "elite_score", "entry_timing_score",
    ]
    for field in coverage_fields:
        count = sum(1 for f in enriched if f.get(field) is not None)
        ct_gt0 = ""
        if field == "ct_consensus":
            ct_gt0 = f" (>0: {sum(1 for f in enriched if (f.get(field) or 0) > 0)})"
        print(f"  {field:<25}: {count:>4}/{len(enriched)} ({count/len(enriched)*100:.0f}%){ct_gt0}")

    # ─────────────────────────────────────────────────────────
    # 13. ACTIONABLE RECOMMENDATIONS
    # ─────────────────────────────────────────────────────────

    print(f"\n{'='*80}")
    print("ACTIONABLE RECOMMENDATIONS")
    print(f"{'='*80}")

    recommendations = []
    for i, r in enumerate(all_results[:10], 1):
        rec = {
            "rank": i,
            "criteria": r["name"],
            "trades": r["trades"],
            "win_rate": r["wr_pct"],
            "avg_pnl": r["avg_pnl"],
            "profit_factor": r["profit_factor"],
            "expected_value": r["exp_val"],
            "improvement_vs_baseline_wr": round(r["wr_pct"] - baseline["wr_pct"], 1),
            "improvement_vs_baseline_pnl": round((r["avg_pnl"] - baseline["avg_pnl"]) * 100, 2),
        }
        recommendations.append(rec)

        print(f"\n  #{i}: {r['name']}")
        print(f"      WR: {r['wr_pct']}% (+{rec['improvement_vs_baseline_wr']}% vs baseline)")
        print(f"      AvgPnL: {r['avg_pnl']*100:+.2f}% ({rec['improvement_vs_baseline_pnl']:+.2f}% vs baseline)")
        print(f"      Trades: {r['trades']} | PF: {r['profit_factor']} | ExpVal: {r['exp_val']*100:+.2f}%")

        # Generate filter code suggestion
        name = r["name"].lower()
        code_lines = []
        if "ct>=" in name or "ct consensus" in name:
            if "ct>=5" in name:
                code_lines.append("consensus_count >= 5")
            elif "ct>=4" in name:
                code_lines.append("consensus_count >= 4")
            elif "ct>=3" in name:
                code_lines.append("consensus_count >= 3")
            elif "ct>=2" in name:
                code_lines.append("consensus_count >= 2")
        if "rsi14<" in name or "rsi(14)<" in name:
            for t in [30, 35, 40, 55, 60]:
                if str(t) in name:
                    code_lines.append(f"rsi_14 < {t}")
                    break
        if "rsi14>" in name or "rsi(14)>" in name:
            for t in [55, 60, 70]:
                if str(t) in name:
                    code_lines.append(f"rsi_14 > {t}")
                    break
        if "rsi 40-60" in name or "rsi14 40-60" in name:
            code_lines.append("40 <= rsi_14 <= 60")
        if "conf>=" in name:
            for t in ["0.80", "0.75", "0.70", "0.65", "0.60"]:
                if t in name:
                    code_lines.append(f"confidence >= {t}")
                    break
        if "volratio>" in name or "vr>" in name:
            for t in ["5.0", "3.0", "2.0", "1.5", "1.0"]:
                if t in name:
                    code_lines.append(f"volume_ratio > {t}")
                    break
        if "buy" in name:
            code_lines.append("direction == 'BUY'")
        if "sell" in name:
            code_lines.append("direction == 'SELL'")
        if "ml>=" in name:
            for t in ["0.9", "0.8", "0.7", "0.6", "0.5"]:
                if t in name:
                    code_lines.append(f"ml_score >= {t}")
                    break
        if "bb" in name:
            if "bb<0.1" in name:
                code_lines.append("bb_pct_b < 0.1")
            elif "bb 0.2-0.8" in name:
                code_lines.append("0.2 <= bb_pct_b <= 0.8")
        if "adx" in name:
            if "adx<25" in name:
                code_lines.append("adx < 25")
            elif "adx>25" in name:
                code_lines.append("adx > 25")
        if "rr>=" in name:
            for t in ["3.0", "2.5", "2.0", "1.5"]:
                if t in name:
                    code_lines.append(f"risk_reward >= {t}")
                    break

        if code_lines:
            print(f"      Filter code: {' AND '.join(code_lines)}")
        else:
            print(f"      Filter code: (see criteria name for logic)")

    # ─────────────────────────────────────────────────────────
    # 14. SAVE RESULTS
    # ─────────────────────────────────────────────────────────

    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "total_closed_picks": len(picks),
        "baseline": baseline,
        "named_filter_results": named_results,
        "top_brute_force": unique_brute[:50],
        "top_strategies": strat_results[:20],
        "top_single_indicators": [
            {k: v for k, v in r.items() if k != "key"} for r in single_results[:30]
        ],
        "grand_ranking_top20": [
            {k: v for k, v in r.items()} for r in all_results[:20]
        ],
        "recommendations": recommendations,
        "tests_run": tests_run,
        "data_coverage": {
            field: sum(1 for f in enriched if f.get(field) is not None)
            for field in coverage_fields
        },
    }

    out_path = DATA / "winning_entry_criteria.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    elapsed = time.time() - t0
    print(f"\n{'='*80}")
    print(f"Analysis complete in {elapsed:.1f}s")
    print(f"Results saved to: {out_path}")
    print(f"Tests run: {tests_run}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
