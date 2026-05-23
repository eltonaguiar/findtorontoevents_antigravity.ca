import sqlite3
import pandas as pd

db_path = "E:/findtorontoevents_antigravity.ca/data/live_picks.db"

def analyze_best_picks():
    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT *
    FROM live_picks
    WHERE status = 'ACTIVE' 
      AND (symbol LIKE '%=F' OR symbol LIKE '%USDT' OR symbol LIKE '%USD')
      AND symbol NOT LIKE '%=X'
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(df.columns)
    
    # Check if we have confidence or score
    if 'score' in df.columns:
        df = df[df['score'] > 40].sort_values('score', ascending=False)
    elif 'confidence' in df.columns:
        df = df[df['confidence'] > 0.6].sort_values('confidence', ascending=False)
    
    df = df.head(10)
    
    if len(df) == 0:
        print("No high-quality active picks currently found.")
    else:
        print(df.to_string())

if __name__ == "__main__":
    analyze_best_picks()
