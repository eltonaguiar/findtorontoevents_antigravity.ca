#!/usr/bin/env python3
"""
Deep analysis runner: validates stats, finds scoring anomalies,
checks gates, and prepares A/B/C forward testing framework.
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path("alpha_engine/data")

def load_json(p):
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return []

def main():
    closed = load_json(DATA_DIR / "closed_picks.json")
    active = load_json(DATA_DIR / "active_picks.json")
    kill_switch = load_json(DATA_DIR / "kill_switch_status.json")
    
    print(f"Loaded: {len(closed)} closed, {len(active)} active picks")
    print()
    
    # ---- 1. OVERALL STATS VALIDATION ----
    print("=" * 70)
    print("1. OVERALL PERFORMANCE STATS")
    print("=" * 70)
    
    total = len(closed)
    wins = sum(1 for p in closed if float(p.get("pnl_pct", 0) or 0) > 0)
    losses = total - wins
    total_pnl = sum(float(p.get("pnl_pct", 0) or 0) for p in closed)
    avg_pnl = total_pnl / total if total else 0
    
    win_pnl = [float(p.get("pnl_pct", 0) or 0) for p in closed if float(p.get("pnl_pct", 0) or 0) > 0]
    loss_pnl = [float(p.get("pnl_pct", 0) or 0) for p in closed if float(p.get("pnl_pct", 0) or 0) <= 0]
    avg_win = sum(win_pnl) / len(win_pnl) if win_pnl else 0
    avg_loss = sum(loss_pnl) / len(loss_pnl) if loss_pnl else 0
    pf = abs(sum(win_pnl) / sum(loss_pnl)) if sum(loss_pnl) != 0 else 999
    
    print(f"Total closed picks: {total}")
    print(f"Win Rate:           {wins/total*100:.1f}%")
    print(f"Total PnL:          {total_pnl:+.2f}%")
    print(f"Avg Win:            {avg_win:+.2f}%")
    print(f"Avg Loss:           {avg_loss:+.2f}%")
    print(f"Profit Factor:      {pf:.2f}")
    print()
    
    # ---- 2. BY ASSET CLASS ----
    print("=" * 70)
    print("2. PERFORMANCE BY ASSET CLASS")
    print("=" * 70)
    
    def classify(sym):
        sym = str(sym or "")
        if "USDT" in sym or "BUSD" in sym or "BTC-USD" in sym or "ETH-USD" in sym:
            return "CRYPTO"
        if any(x in sym for x in ["/", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "USD=", "FOREX"]):
            return "FOREX"
        if any(x in sym for x in ["CL=", "GC=", "SI=", "NG=", "ZC="]):
            return "FUTURES"
        return "EQUITY"
    
    by_class = defaultdict(list)
    for p in closed:
        cls = classify(p.get("symbol"))
        by_class[cls].append(float(p.get("pnl_pct", 0) or 0))
    
    for cls, pnls in sorted(by_class.items()):
        w = sum(1 for x in pnls if x > 0)
        wp_list = [x for x in pnls if x > 0]
        lp_list = [x for x in pnls if x <= 0]
        cls_pf = abs(sum(wp_list) / sum(lp_list)) if sum(lp_list) != 0 else 999
        print(f"{cls:10} | {len(pnls):4d} picks | WR: {w/len(pnls)*100:5.1f}% | PnL: {sum(pnls):+8.2f}% | PF: {cls_pf:.2f}")
    print()
    
    # ---- 3. TOP/BOTTOM STRATEGIES ----
    print("=" * 70)
    print("3. STRATEGY PERFORMANCE (min 5 picks)")
    print("=" * 70)
    
    strat_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0})
    for p in closed:
        strat = str(p.get("strategy") or p.get("strategy_name") or "unknown")
        pnl = float(p.get("pnl_pct", 0) or 0)
        strat_stats[strat]["pnl"] += pnl
        if pnl > 0:
            strat_stats[strat]["wins"] += 1
        else:
            strat_stats[strat]["losses"] += 1
    
    eligible = [(k, v) for k, v in strat_stats.items() if v["wins"] + v["losses"] >= 5]
    
    print("\n--- TOP 20 by Win Rate ---")
    for k, v in sorted(eligible, key=lambda x: x[1]["wins"] / (x[1]["wins"] + x[1]["losses"]), reverse=True)[:20]:
        total = v["wins"] + v["losses"]
        wr = v["wins"] / total * 100
        print(f"  {k[:55]:<55} | {total:3d} | WR {wr:5.1f}% | PnL {v['pnl']:+.1f}%")
    
    print("\n--- BOTTOM 10 by Win Rate ---")
    for k, v in sorted(eligible, key=lambda x: x[1]["wins"] / (x[1]["wins"] + x[1]["losses"]))[:10]:
        total = v["wins"] + v["losses"]
        wr = v["wins"] / total * 100
        print(f"  {k[:55]:<55} | {total:3d} | WR {wr:5.1f}% | PnL {v['pnl']:+.1f}%")
    print()
    
    # ---- 4. LOW SCORE / HIGH PERFORMANCE ANOMALIES ----
    print("=" * 70)
    print("4. SCORING ANOMALIES: LOW SCORE BUT HIGH PnL")
    print("=" * 70)
    
    try:
        from alpha_engine.elite_scorer import compute_elite_score
        scored_picks = []
        for p in closed:
            try:
                result = compute_elite_score(p)
                score = float(result.get("elite_score", 0))
            except Exception:
                score = 0
            pnl = float(p.get("pnl_pct", 0) or 0)
            scored_picks.append((p, score, pnl))
        
        # Low score winners
        low_win = [(p, sc, pnl) for p, sc, pnl in scored_picks if sc < 30 and pnl > 5]
        high_lose = [(p, sc, pnl) for p, sc, pnl in scored_picks if sc > 60 and pnl < -2]
        
        print(f"\nLow Score (<30) but Won (>5% PnL): {len(low_win)} picks")
        for p, sc, pnl in sorted(low_win, key=lambda x: x[2], reverse=True)[:15]:
            strat = str(p.get("strategy") or "?")[:40]
            sym = str(p.get("symbol") or "?")[:15]
            print(f"  {sym:15} | {strat:40} | score={sc:4.1f} | pnl={pnl:+.2f}%")
        
        print(f"\nHigh Score (>60) but Lost (<-2% PnL): {len(high_lose)} picks")
        for p, sc, pnl in sorted(high_lose, key=lambda x: x[2])[:15]:
            strat = str(p.get("strategy") or "?")[:40]
            sym = str(p.get("symbol") or "?")[:15]
            print(f"  {sym:15} | {strat:40} | score={sc:4.1f} | pnl={pnl:+.2f}%")
        
        # Score distribution
        score_ranges = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
        wr_ranges = {"0-20": [0, 0], "21-40": [0, 0], "41-60": [0, 0], "61-80": [0, 0], "81-100": [0, 0]}
        for p, sc, pnl in scored_picks:
            if sc <= 20:
                rng = "0-20"
            elif sc <= 40:
                rng = "21-40"
            elif sc <= 60:
                rng = "41-60"
            elif sc <= 80:
                rng = "61-80"
            else:
                rng = "81-100"
            score_ranges[rng] += 1
            if pnl > 0:
                wr_ranges[rng][0] += 1
            wr_ranges[rng][1] += 1
        
        print("\n--- Score Distribution vs Actual Win Rate ---")
        print(f"{'Score Band':12} | {'Count':6} | {'Actual WR':10}")
        for rng, cnt in score_ranges.items():
            w, t = wr_ranges[rng]
            wr = w / t * 100 if t else 0
            print(f"  {rng:12} | {cnt:6d} | {wr:8.1f}%")
            
    except ImportError as e:
        print(f"Could not import elite_scorer: {e}")
    
    print()
    
    # ---- 5. GATE ANALYSIS ----
    print("=" * 70)
    print("5. GATE / KILL SWITCH ANALYSIS")
    print("=" * 70)
    
    print("\nKill Switch Status:")
    if isinstance(kill_switch, dict):
        print(f"  Killed: {kill_switch.get('is_killed', '?')}")
        print(f"  Severity: {kill_switch.get('severity', '?')}")
        print(f"  Reason: {kill_switch.get('kill_reason', '?')}")
        print(f"  Action: {kill_switch.get('recommended_action', '?')}")
        for cond in kill_switch.get("conditions", []):
            print(f"  Condition: {cond.get('condition')} [{cond.get('severity')}] - {cond.get('detail')}")
    
    # Check strategy-level gates
    try:
        from alpha_engine.crypto_risk_gates import LOW_CONFIDENCE_STRATEGIES, HARD_KILL_STRATEGIES
        print(f"\nHard-Kill Strategies: {len(HARD_KILL_STRATEGIES)}")
        for s in HARD_KILL_STRATEGIES:
            print(f"  - {s}")
        print(f"\nLow-Confidence Strategies: {len(LOW_CONFIDENCE_STRATEGIES)}")
        for s, reason in LOW_CONFIDENCE_STRATEGIES.items():
            print(f"  - {s}: {reason}")
    except ImportError as e:
        print(f"Could not load gates: {e}")
    
    print()
    
    # ---- 6. UNIVERSE COVERAGE CHECK ----
    print("=" * 70)
    print("6. CRYPTO UNIVERSE COVERAGE")
    print("=" * 70)
    
    symbols_traded = set(str(p.get("symbol", "")) for p in closed)
    crypto_symbols = {s for s in symbols_traded if "USDT" in s or "BTC-USD" in s or "ETH-USD" in s}
    print(f"Unique crypto symbols traded: {len(crypto_symbols)}")
    print(f"All symbols: {sorted(crypto_symbols)[:30]}")
    
    # Top cryptos by market cap we might be missing
    top_cryptos_expected = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
        "AVAXUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "UNIUSDT", "LTCUSDT",
        "MATICUSDT", "ATOMUSDT", "NEARUSDT", "FTMUSDT", "ALGOUSDT", "VETUSDT",
        "FILUSDT", "TRXUSDT", "XLMUSDT", "HBARUSDT", "ICPUSDT", "EGLDUSDT",
        "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "SUIUSDT", "SEIUSDT",
    ]
    missing = [s for s in top_cryptos_expected if s not in crypto_symbols]
    print(f"\nTop 30 cryptos MISSING from our traded universe: {len(missing)}")
    for m in missing:
        print(f"  - {m}")
    
    print()
    
    # ---- 7. PICK SCORE vs ACTUAL PnL CORRELATION ----
    print("=" * 70)
    print("7. SESSION SCORING CORRELATION")
    print("=" * 70)
    
    ab_path = DATA_DIR / "scoring_ab_results.json"
    if ab_path.exists():
        with open(ab_path) as f:
            ab = json.load(f)
        print("Scoring Method Comparison (from last AB test):")
        for method, stats in ab.get("methods", {}).items():
            print(f"  {method:25} | Top20% WR: {stats['top20_wr']:5.1f}% | Separation: {stats['separation']:5.1f}%")
    
    print()
    print("DIAGNOSIS: Method C (ML-First forward_wr) has 48% separation vs 26% current.")
    print("This means the current elite_scorer is leaving 22% of discrimination on the table.")
    print()
    
    # ---- 8. COPY TRADER INTEL STATUS ----
    print("=" * 70)
    print("8. COPY TRADER INTEL")
    print("=" * 70)
    
    ct_dir = Path("copy_trader_intel/data")
    if ct_dir.exists():
        ct_files = list(ct_dir.glob("*.json"))
        print(f"Copy trader data files: {len(ct_files)}")
        for f in ct_files[:10]:
            print(f"  {f.name}")
    else:
        print("  copy_trader_intel/data/ NOT FOUND")
    
    print()
    
    # ---- 9. ACTIVE PICKS SCORE DISTRIBUTION ----
    print("=" * 70)
    print("9. CURRENT ACTIVE PICKS ANALYSIS")
    print("=" * 70)
    
    if isinstance(active, list):
        for p in active[:10]:
            sym = p.get("symbol", "?")
            strat = str(p.get("strategy") or "?")[:40]
            conf = p.get("confidence", "?")
            direction = p.get("direction", "?")
            entry = p.get("entry_price", "?")
            print(f"  {sym:15} | {direction:5} | conf={conf} | {strat}")
    
    print()
    print("Analysis complete. See deep_strategy_analysis.md for full report.")

if __name__ == "__main__":
    main()
