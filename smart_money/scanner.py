"""Smart Money Intelligence — equity signal scanner.
Fetches institutional consensus from PHP API and outputs picks for cross-aggregation."""
import json
import os
import sys
import requests
from datetime import datetime, timezone

API_BASE = "https://findtorontoevents.ca/live-monitor/api/smart_money.php"
API_KEY = os.getenv("ADMIN_API_KEY", "")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MIN_SCORE = 60  # minimum consensus score to generate a pick
MIN_CONFIDENCE = "MODERATE"  # MODERATE or HIGH

CONFIDENCE_MAP = {"HIGH": 0.85, "MODERATE": 0.65, "LOW": 0.45}
DIRECTION_MAP = {"BULLISH": "BUY", "BEARISH": "SELL", "NEUTRAL": None}


HEADERS = {"User-Agent": "Mozilla/5.0 (SmartMoney Scanner/1.0)"}


def fetch_consensus():
    """Fetch all ticker consensus scores from the API."""
    try:
        r = requests.get(f"{API_BASE}?action=consensus", headers=HEADERS, timeout=15)
        print(f"  [SMART MONEY] API status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if data.get("ok"):
                return data.get("data", [])
            else:
                print(f"  [SMART MONEY] API returned ok=false: {data.get('error', 'unknown')}")
        else:
            print(f"  [SMART MONEY] API HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  [SMART MONEY] API error: {e}", file=sys.stderr)
    return []


def fetch_price(ticker):
    """Fetch current stock price via Yahoo Finance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except:
        pass
    # Fallback: try FMP API
    fmp_key = os.getenv("FMP_API_KEY", "")
    if fmp_key:
        try:
            r = requests.get(f"https://financialmodelingprep.com/api/v3/quote-short/{ticker}?apikey={fmp_key}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data:
                    return float(data[0].get("price", 0))
        except:
            pass
    return 0


def generate_picks():
    """Generate active picks from Smart Money consensus."""
    consensus = fetch_consensus()
    if not consensus:
        print("  [SMART MONEY] No consensus data available")
        return []

    picks = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for t in consensus:
        ticker = t.get("ticker", "")
        score = t.get("overall_score", 0)
        direction_str = t.get("direction", "NEUTRAL")
        conf_str = t.get("confidence", "LOW")
        components = t.get("components", {})

        # Filter
        direction = DIRECTION_MAP.get(direction_str)
        if not direction:
            continue
        if score < MIN_SCORE:
            continue

        confidence = CONFIDENCE_MAP.get(conf_str, 0.45)
        price = fetch_price(ticker)
        if price <= 0:
            continue

        # Compute TP/SL based on direction and score strength
        atr_pct = 0.03  # ~3% ATR estimate for stocks
        if direction == "BUY":
            tp = round(price * (1 + atr_pct * 2.5), 2)
            sl = round(price * (1 - atr_pct * 1.5), 2)
        else:
            tp = round(price * (1 - atr_pct * 2.5), 2)
            sl = round(price * (1 + atr_pct * 1.5), 2)

        rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0

        # Build reasons from components
        reasons = []
        if components.get("analyst", 0) > 70:
            reasons.append(f"Analyst consensus strong ({components['analyst']}/100)")
        if components.get("insider", 0) > 60:
            reasons.append(f"Insider sentiment bullish ({components['insider']}/100)")
        if components.get("momentum", 0) > 60:
            reasons.append(f"Price momentum positive ({components['momentum']}/100)")
        if components.get("social", 0) > 50:
            reasons.append(f"Social sentiment positive ({components['social']}/100)")

        pick = {
            "symbol": ticker,
            "direction": direction,
            "signal_type": direction,
            "entry_price": price,
            "entry": price,
            "take_profit": tp,
            "tp": tp,
            "stop_loss": sl,
            "sl": sl,
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "strategy": "smart_money_consensus",
            "source_system": "smart_money",
            "reason": "; ".join(reasons) if reasons else f"Smart Money consensus {score}/100 {direction_str}",
            "timeframe": "1d",
            "asset_class": "equity",
            "timestamp": now,
            "generated_at": now,
            "smart_money_score": score,
            "smart_money_components": components,
        }
        picks.append(pick)
        print(f"  [SMART MONEY] {ticker} {direction} score={score} conf={conf_str} price=${price:.2f}")

    return picks


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print("Smart Money Intelligence — scanning equity signals...")

    picks = generate_picks()

    # Write active_picks.json
    output_path = os.path.join(DATA_DIR, "active_picks.json")
    with open(output_path, "w") as f:
        json.dump(picks, f, indent=2)
    print(f"  Output: {output_path} ({len(picks)} picks)")

    # Also write a summary
    summary_path = os.path.join(DATA_DIR, "scan_summary.json")
    with open(summary_path, "w") as f:
        json.dump({
            "last_scan": datetime.now(timezone.utc).isoformat(),
            "picks_count": len(picks),
            "tickers_scanned": 12,
            "min_score": MIN_SCORE,
        }, f, indent=2)

    return picks


if __name__ == "__main__":
    main()
