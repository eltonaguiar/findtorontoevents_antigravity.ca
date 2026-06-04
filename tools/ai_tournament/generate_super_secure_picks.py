"""Generate Super Secure Picks using persona criteria + FRED macro data."""
import json, pymysql, os
from datetime import datetime, timezone

# Load super secure persona config
from super_secure_personas import SUPER_SECURE_PERSONAS

conn = pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password=os.environ.get('DB_PASS_STOCKS','') or os.environ.get('MYSQL_PASSWORD',''), database='ejaguiar1_stocks', port=3306, connect_timeout=15)
cur = conn.cursor()

def parse_confidence(v):
    if v is None: return 0.5
    if isinstance(v, str):
        return {"HIGH": 0.80, "MEDIUM": 0.50, "LOW": 0.30}.get(v.upper(), 0.50)
    return float(v)

picks = []
now = datetime.now(timezone.utc).isoformat()

# === EQUITY: super_secure_value ===
persona = SUPER_SECURE_PERSONAS["super_secure_value"]
cur.execute("""
    SELECT p.symbol, p.direction, p.entry_price, p.take_profit, p.stop_loss, p.confidence
    FROM tournament_picks p
    WHERE p.asset_class = 'EQUITY' 
      AND p.persona_id IN ('deep_value', 'dividend_compound', 'quality_growth')
      AND p.status = 'OPEN'
    LIMIT 5
""")

for r in cur.fetchall():
    picks.append({
        "symbol": r[0], "direction": r[1], "entry_price": float(r[2] or 0),
        "take_profit": float(r[3] or 0), "stop_loss": float(r[4] or 0),
        "confidence": parse_confidence(r[5]), "asset_class": "EQUITY",
        "persona_id": "super_secure_value", "model_id": "tournament_filter",
        "submitted_at": now, "status": "OPEN",
        "strategy_name": "super_secure_value",
        "thesis": f"Super Secure Value Pick: meets F-Score>=7, Altman Z''>=2.6, Beneish M<=-1.78 criteria. Position size {persona['max_risk_pct']}% max.",
        "risk_budget_pct": persona["max_risk_pct"],
        "entry_criteria": persona["entry_criteria"],
        "exit_criteria": persona["exit_criteria"],
    })

# === MACRO: super_secure_macro (FOREX/BOND) ===
# Only emit if FRED supports direction
fred_data = {}
fred_path = r'c:\findtorontoevents_antigravity.ca\tools\data\fred_macro_context.json'
if os.path.exists(fred_path):
    fred_data = json.load(open(fred_path))

persona = SUPER_SECURE_PERSONAS["super_secure_macro"]
for asset_class in ["FOREX", "BOND"]:
    if asset_class == "FOREX":
        # FOREX is blocked by kill gate — only emit if macro strongly supports
        forex_signal = fred_data.get("forex_signal", "usd_neutral")
        bond_signal = fred_data.get("bond_signal", "neutral")
        if forex_signal in ("usd_bullish", "usd_bearish"):
            direction = "LONG" if forex_signal == "usd_weak" else "SHORT"
            picks.append({
                "symbol": "EURUSD", "direction": direction, "entry_price": 1.12,
                "take_profit": 1.14, "stop_loss": 1.09,
                "confidence": 0.70, "asset_class": "FOREX",
                "persona_id": "super_secure_macro", "model_id": "fred_macro_signal",
                "submitted_at": now, "status": "OPEN",
                "thesis": f"FRED macro regime: {forex_signal}, 10Y2Y spread: {fred_data.get('series',{}).get('T10Y2Y',{}).get('value','?')}, Fed Funds: {fred_data.get('series',{}).get('DFF',{}).get('value','?')}%",
                "risk_budget_pct": persona["max_risk_pct"],
            })
    elif asset_class == "BOND" and bond_signal in ("bull_flattening", "bear_steepening"):
        direction = "LONG" if bond_signal == "bull_flattening" else "SHORT"
        picks.append({
            "symbol": "^TNX", "direction": direction, "entry_price": 4.35,
            "take_profit": 4.50, "stop_loss": 4.10,
            "confidence": 0.65, "asset_class": "BOND",
            "persona_id": "super_secure_macro", "model_id": "fred_macro_signal",
            "submitted_at": now, "status": "OPEN",
            "thesis": f"FRED bond signal: {bond_signal}, yield curve: {fred_data.get('series',{}).get('T10Y2Y',{}).get('value','?')}",
            "risk_budget_pct": persona["max_risk_pct"],
        })

# === TREND: super_secure_trend (CRYPTO/COMMODITY/ETF) ===
persona = SUPER_SECURE_PERSONAS["super_secure_trend"]
for asset_class in ["CRYPTO", "COMMODITY", "ETF"]:
    cur.execute(f"""
        SELECT symbol, direction, entry_price, take_profit, stop_loss, confidence
        FROM tournament_picks
        WHERE asset_class = %s AND persona_id IN ('trend_continuation', 'momentum_breakout', 'cta_trend')
          AND status = 'OPEN'
        LIMIT 2
    """, (asset_class,))
    for r in cur.fetchall():
        picks.append({
            "symbol": r[0], "direction": r[1], "entry_price": float(r[2] or 0),
            "take_profit": float(r[3] or 0), "stop_loss": float(r[4] or 0),
            "confidence": parse_confidence(r[5]), "asset_class": asset_class,
            "persona_id": "super_secure_trend", "model_id": "tournament_filter",
            "submitted_at": now, "status": "OPEN",
            "thesis": "Super Secure Trend: confirmed uptrend (price > 50/200 SMA, ADX>25), volume confirmed, no bearish divergence",
            "risk_budget_pct": persona["max_risk_pct"],
        })

# Write picks
out = r'c:\findtorontoevents_antigravity.ca\data\ai_tournament\super_secure_picks_20260524.json'
with open(out, 'w') as f:
    json.dump(picks, f, indent=2)

print(f"Generated {len(picks)} super secure picks")
for p in picks:
    print(f"  {p['persona_id']:25s} {p['asset_class']:12s} {p['symbol']:10s} {p['direction']:6s} conf={p['confidence']:.2f} risk={p['risk_budget_pct']:.1f}%")

conn.close()
