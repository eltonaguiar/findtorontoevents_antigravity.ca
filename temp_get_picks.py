import sqlite3
import json
import datetime

db_path = "E:/findtorontoevents_antigravity.ca/data/live_picks.db"

def get_top_open_picks():
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # We want active picks
        c.execute("""
            SELECT * FROM live_picks 
            WHERE status = 'ACTIVE'
        """)
        
        picks = [dict(row) for row in c.fetchall()]
        conn.close()
        
        open_market_picks = []
        for p in picks:
            sym = p.get('symbol', '').upper()
            asset = p.get('asset_class', '').upper()
            
            # Filter for OPEN markets at 8:30 PM EST
            # Crypto is open
            # Futures are open (usually symbols containing =F)
            # Stocks and ETFs are CLOSED
            # We skip FOREX as per recent triage (gutted)
            
            is_crypto = asset == 'CRYPTO' or 'USDT' in sym or 'USD' in sym and not '=X' in sym and len(sym) > 4
            is_futures = '=F' in sym
            
            if is_crypto or is_futures:
                if 'score' in p and p['score'] is not None:
                    open_market_picks.append(p)
                else:
                    # if no score field, let's just use confidence
                    p['score'] = p.get('confidence', 0) * 100
                    open_market_picks.append(p)
                    
        # Sort by score descending
        open_market_picks.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        print("Top 5 Picks for Currently OPEN Markets (Crypto & Futures):")
        print("-" * 60)
        for i, p in enumerate(open_market_picks[:10]):
            sym = p.get('symbol')
            dir_ = p.get('direction')
            score = p.get('score', 0)
            entry = p.get('entry_price')
            tp = p.get('take_profit')
            sl = p.get('stop_loss')
            strat = p.get('strategy')
            sys = p.get('source_system')
            
            print(f"{i+1}. {sym} ({dir_}) - Score: {score}")
            print(f"   Entry: {entry} | TP: {tp} | SL: {sl}")
            print(f"   System: {sys} | Strategy: {strat}")
            print("-" * 60)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_top_open_picks()
