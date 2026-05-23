import sqlite3

db_path = "E:/findtorontoevents_antigravity.ca/data/live_picks.db"

def get_better_picks():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # We want active picks with a known direction and score/confidence
    c.execute("""
        SELECT symbol, direction, entry_price, take_profit, stop_loss, 
               confidence, score, source_system, strategy, asset_class
        FROM live_picks 
        WHERE status = 'ACTIVE' 
          AND direction IS NOT NULL
          AND (asset_class = 'CRYPTO' OR symbol LIKE '%=F' OR symbol LIKE '%USDT')
        ORDER BY score DESC, confidence DESC
        LIMIT 10
    """)
    
    picks = [dict(row) for row in c.fetchall()]
    conn.close()
    
    for i, p in enumerate(picks):
        sym = p.get('symbol')
        dir_ = p.get('direction')
        score = p.get('score')
        conf = p.get('confidence')
        entry = p.get('entry_price')
        tp = p.get('take_profit')
        sl = p.get('stop_loss')
        strat = p.get('strategy')
        sys = p.get('source_system')
        
        print(f"{i+1}. {sym} ({dir_}) - Score: {score} | Conf: {conf}")
        print(f"   Entry: {entry} | TP: {tp} | SL: {sl}")
        print(f"   System: {sys} | Strategy: {strat}")
        print("-" * 60)

if __name__ == "__main__":
    get_better_picks()
