
import json
import os

def audit():
    try:
        active_path = r"e:\findtorontoevents_antigravity.ca\alpha_engine\data\active_picks.json"
        closed_path = r"e:\findtorontoevents_antigravity.ca\alpha_engine\data\closed_picks.json"
        
        if not os.path.exists(active_path):
            print(f"Error: {active_path} not found")
            return
            
        with open(active_path, "r", encoding="utf-8") as f:
            active_all = json.load(f)
        with open(closed_path, "r", encoding="utf-8") as f:
            closed_all = json.load(f)
            
        active = [p for p in active_all if p.get('category') == 'crypto' or p.get('asset_class') == 'CRYPTO']
        closed = [p for p in closed_all if p.get('category') == 'crypto' or p.get('asset_class') == 'CRYPTO']
        
    except Exception as e:
        print(f"Error loading files: {e}")
        return

    # 1. Historical Stats by Strategy
    strat_stats = {}
    for p in closed:
        s = p.get("strategy", "unknown")
        if s not in strat_stats:
            strat_stats[s] = {"wins": 0, "losses": 0, "total_pnl": 0.0, "trades": []}
        
        pnl = p.get("pnl_pct", 0)
        # Standardize pnl_pct (ensure it's fractional, e.g. 0.05 for 5%)
        if abs(pnl) > 1.0:
            pnl /= 100.0
            
        if pnl > 0:
            strat_stats[s]["wins"] += 1
        elif pnl < 0:
            strat_stats[s]["losses"] += 1
        
        strat_stats[s]["total_pnl"] += pnl
        strat_stats[s]["trades"].append(pnl)

    # 2. Audit Active Picks
    audit_results = []
    print("\n[ACTIVE CRYPTO PORTFOLIO AUDIT - QUANT REPORT]")
    print(f"Found {len(active)} active crypto picks.")
    print("-" * 120)
    print(f"{'SYMBOL':12} | {'STRATEGY':40} | {'PnL':>8} | {'WR':>5} | {'R-UNIT':>8} | {'STATUS'}")
    print("-" * 120)
    
    for p in active:
        symbol = p.get("symbol")
        strat = p.get("strategy")
        pnl_pct = p.get("pnl_pct", 0.0)
        entry = p.get("entry_price")
        curr = p.get("current_price") or entry
        sl = p.get("stop_loss")
        direction = str(p.get("direction") or p.get("signal_type") or "BUY").upper()
        
        # Risk Unit (R) check
        try:
            risk_per_share = abs(float(entry or 1) - float(sl or (entry * 0.9)))
            current_r = 0.0
            if risk_per_share > 0:
                # BUY (Long): gain = current - entry
                # SELL (Short): gain = entry - current
                if direction in ("BUY", "LONG"):
                    gain_per_share = (float(curr or 0) - float(entry or 0))
                else:
                    gain_per_share = (float(entry or 0) - float(curr or 0))
                current_r = gain_per_share / risk_per_share
        except Exception:
            current_r = 0.0

        # Historical expectancy
        stats = strat_stats.get(strat, {"wins":0, "losses":0, "total_pnl":0.0})
        total_trades = stats["wins"] + stats["losses"]
        wr = stats["wins"] / total_trades if total_trades > 0 else 0.5
        
        status = "PASS"
        toxic_reasons = []
        if current_r < -0.8: 
            status = "TOXIC"
            toxic_reasons.append("Near SL")
        if wr < 0.4 and total_trades >= 5: 
            status = "TOXIC"
            toxic_reasons.append(f"Low WR ({wr:.0%})")
        if pnl_pct is not None and pnl_pct < -7.0: # Deep PnL block
            status = "TOXIC"
            toxic_reasons.append("Extreme PnL")

        audit_results.append({
            "symbol": symbol,
            "strategy": strat,
            "current_r": current_r,
            "wr": wr,
            "status": status,
            "reasons": toxic_reasons
        })
        
        _pnl_str = f"{pnl_pct:.2f}%" if pnl_pct is not None else "N/A"
        print(f"{symbol:12} | {strat:40} | {_pnl_str:>8} | {wr:>4.0%} | {current_r:>8.2f} | {status} {'(' + ', '.join(toxic_reasons) + ')' if toxic_reasons else ''}")

    # 3. Recommendations
    toxic_strats = set(r["strategy"] for r in audit_results if r["status"] == "TOXIC")
    if toxic_strats:
        print("\n[PROPOSED STRATEGY KILL LIST (NON-PERFORMING CRYPTO)]")
        for s in toxic_strats:
            print(f" - {s}")
    else:
        print("\nAll active crypto picks passed the risk-unit and historical WR gates.")

if __name__ == '__main__':
    audit()
