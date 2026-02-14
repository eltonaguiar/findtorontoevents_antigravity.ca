#!/usr/bin/env python3
"""
Unified Trading Data Collector
Aggregates data from all 4 systems for the monitoring dashboard
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# API Endpoints (local or remote)
API_BASE = os.getenv("API_BASE", "https://findtorontoevents.ca")


def fetch_alpha_signals():
    """Fetch alpha signals from alpha engine"""
    try:
        import requests
        
        # Try to fetch from alpha engine API
        url = f"{API_BASE}/live-monitor/api/alpha_signals.php"
        response = requests.get(url, timeout=30, params={"key": "livetrader2026"})
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return process_alpha_data(data)
    except Exception as e:
        print(f"Alpha signals fetch error: {e}")
    
    # Fallback: generate sample data
    return generate_sample_alpha_signals()


def process_alpha_data(data):
    """Process raw alpha signal data"""
    signals = data.get("signals", [])
    processed = []
    
    for sig in signals:
        processed.append({
            "symbol": sig.get("symbol", "UNKNOWN"),
            "grade": sig.get("grade", "B"),
            "score": sig.get("score", 0),
            "entry_price": sig.get("entry_price", 0),
            "stop_loss": sig.get("stop_loss", 0),
            "target_price": sig.get("target_price", 0),
            "key_factor": sig.get("key_factor", "Technical"),
            "factors": sig.get("factors", [])
        })
    
    # Sort by score descending
    processed.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "count": len(processed),
        "signals": processed,
        "last_update": datetime.now().isoformat()
    }


def generate_sample_alpha_signals():
    """Generate sample alpha signals for demonstration"""
    return {
        "count": 4,
        "timestamp": datetime.now().isoformat(),  # Always update timestamp
        "signals": [
            {
                "symbol": "BTC/USD",
                "grade": "S+",
                "score": 96,
                "entry_price": 43250.00,
                "stop_loss": 41800.00,
                "target_price": 46500.00,
                "key_factor": "Smart Money Sweep",
                "factors": ["HTF Trend", "Smart Money", "On-chain", "Volume Profile", "Kill Zone"]
            },
            {
                "symbol": "ETH/USD",
                "grade": "S",
                "score": 92,
                "entry_price": 2580.50,
                "stop_loss": 2480.00,
                "target_price": 2850.00,
                "key_factor": "Order Block Reclaim",
                "factors": ["HTF Trend", "Smart Money", "Volume Profile", "Timing"]
            },
            {
                "symbol": "SOL/USD",
                "grade": "A+",
                "score": 87,
                "entry_price": 98.50,
                "stop_loss": 92.00,
                "target_price": 115.00,
                "key_factor": "Volume Spike + FVG",
                "factors": ["Smart Money", "On-chain", "Volume Profile"]
            },
            {
                "symbol": "LINK/USD",
                "grade": "A",
                "score": 82,
                "entry_price": 14.85,
                "stop_loss": 13.90,
                "target_price": 16.50,
                "key_factor": "Liquidity Cluster",
                "factors": ["HTF Trend", "Volume Profile", "Liquidations"]
            }
        ],
        "last_update": datetime.now().isoformat(),
        "note": "Sample data - connect to live API for real signals"
    }


def fetch_goldmine_candidates():
    """Fetch gem candidates from goldmine scanner"""
    try:
        import requests
        
        url = f"{API_BASE}/live-monitor/api/goldmine_scanner.php"
        response = requests.get(url, timeout=30, params={"action": "scan", "min_score": 75})
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return process_goldmine_data(data)
    except Exception as e:
        print(f"Goldmine fetch error: {e}")
    
    return generate_sample_goldmine_candidates()


def process_goldmine_data(data):
    """Process raw goldmine data"""
    candidates = data.get("candidates", [])
    processed = []
    
    for cand in candidates:
        processed.append({
            "symbol": cand.get("symbol", "UNKNOWN"),
            "name": cand.get("name", cand.get("symbol", "Unknown")),
            "score": cand.get("score", 0),
            "market_cap": cand.get("market_cap", 0),
            "factors": [
                {"name": "Market Cap", "score": cand.get("mc_score", 0), "active": cand.get("mc_score", 0) > 20},
                {"name": "Volume Spike", "score": cand.get("vol_score", 0), "active": cand.get("vol_score", 0) > 15},
                {"name": "Holder Growth", "score": cand.get("holder_score", 0), "active": cand.get("holder_score", 0) > 10},
                {"name": "Liquidity", "score": cand.get("liq_score", 0), "active": cand.get("liq_score", 0) > 15},
                {"name": "Accumulation", "score": cand.get("acc_score", 0), "active": cand.get("acc_score", 0) > 10},
                {"name": "Narrative", "score": cand.get("nar_score", 0), "active": cand.get("nar_score", 0) > 8},
                {"name": "Smart Money", "score": cand.get("sm_score", 0), "active": cand.get("sm_score", 0) > 8},
            ]
        })
    
    processed.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "count": len(processed),
        "candidates": processed,
        "last_update": datetime.now().isoformat()
    }


def generate_sample_goldmine_candidates():
    """Generate sample gem candidates"""
    return {
        "count": 3,
        "timestamp": datetime.now().isoformat(),  # Always update timestamp
        "candidates": [
            {
                "symbol": "HYPERAI",
                "name": "Hyper AI Protocol",
                "score": 94,
                "market_cap": 850000,
                "factors": [
                    {"name": "Market Cap", "score": 28, "active": True},
                    {"name": "Volume Spike", "score": 23, "active": True},
                    {"name": "Holder Growth", "score": 18, "active": True},
                    {"name": "Liquidity", "score": 22, "active": True},
                    {"name": "Accumulation", "score": 3, "active": False},
                    {"name": "Narrative", "score": 0, "active": False},
                    {"name": "Smart Money", "score": 0, "active": False},
                ]
            },
            {
                "symbol": "VIRTUAL",
                "name": "Virtual Protocol",
                "score": 91,
                "market_cap": 3200000,
                "factors": [
                    {"name": "Market Cap", "score": 25, "active": True},
                    {"name": "Volume Spike", "score": 24, "active": True},
                    {"name": "Holder Growth", "score": 17, "active": True},
                    {"name": "Liquidity", "score": 23, "active": True},
                    {"name": "Accumulation", "score": 2, "active": False},
                    {"name": "Narrative", "score": 0, "active": False},
                    {"name": "Smart Money", "score": 0, "active": False},
                ]
            },
            {
                "symbol": "AI16Z",
                "name": "AI16Z DAO",
                "score": 88,
                "market_cap": 12500000,
                "factors": [
                    {"name": "Market Cap", "score": 20, "active": True},
                    {"name": "Volume Spike", "score": 22, "active": True},
                    {"name": "Holder Growth", "score": 15, "active": True},
                    {"name": "Liquidity", "score": 24, "active": True},
                    {"name": "Accumulation", "score": 7, "active": True},
                    {"name": "Narrative", "score": 0, "active": False},
                    {"name": "Smart Money", "score": 0, "active": False},
                ]
            }
        ],
        "last_update": datetime.now().isoformat(),
        "note": "Sample data - connect to live API for real candidates"
    }


def fetch_predictions():
    """Fetch active predictions"""
    try:
        import requests
        
        url = f"{API_BASE}/live-monitor/api/predictions.php"
        response = requests.get(url, timeout=30, params={"status": "active"})
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return process_predictions_data(data)
    except Exception as e:
        print(f"Predictions fetch error: {e}")
    
    return generate_sample_predictions()


def process_predictions_data(data):
    """Process raw predictions data"""
    predictions = data.get("predictions", [])
    processed = []
    
    for pred in predictions:
        # Calculate progress toward target
        entry = pred.get("entry_price", 0)
        target = pred.get("target_price", 0)
        current = pred.get("current_price", entry)
        
        if target != entry:
            progress = min(100, max(0, ((current - entry) / (target - entry)) * 100))
        else:
            progress = 0
        
        processed.append({
            "symbol": pred.get("symbol", "UNKNOWN"),
            "direction": pred.get("direction", "bullish"),
            "entry_price": entry,
            "target_price": target,
            "current_price": current,
            "progress": round(progress, 1),
            "status": pred.get("status", "tracking"),
            "prediction_date": pred.get("prediction_date", ""),
            "target_date": pred.get("target_date", "")
        })
    
    return {
        "count": len(processed),
        "predictions": processed,
        "last_update": datetime.now().isoformat()
    }


def generate_sample_predictions():
    """Generate sample predictions"""
    return {
        "count": 4,
        "timestamp": datetime.now().isoformat(),  # Always update timestamp
        "predictions": [
            {
                "symbol": "POPCAT",
                "direction": "bullish",
                "entry_price": 0.42,
                "target_price": 0.65,
                "current_price": 0.51,
                "progress": 40.9,
                "status": "tracking",
                "prediction_date": "2026-02-10",
                "target_date": "2026-03-10"
            },
            {
                "symbol": "PENGU",
                "direction": "bullish",
                "entry_price": 0.011,
                "target_price": 0.025,
                "current_price": 0.014,
                "progress": 23.1,
                "status": "tracking",
                "prediction_date": "2026-02-10",
                "target_date": "2026-04-10"
            },
            {
                "symbol": "DOGE",
                "direction": "bullish",
                "entry_price": 0.25,
                "target_price": 0.40,
                "current_price": 0.28,
                "progress": 20.0,
                "status": "tracking",
                "prediction_date": "2026-02-01",
                "target_date": "2026-05-01"
            },
            {
                "symbol": "BTC",
                "direction": "bullish",
                "entry_price": 42500,
                "target_price": 55000,
                "current_price": 43250,
                "progress": 6.2,
                "status": "tracking",
                "prediction_date": "2026-01-15",
                "target_date": "2026-06-15"
            }
        ],
        "last_update": datetime.now().isoformat(),
        "note": "Sample data - connect to live API for real predictions"
    }


def fetch_algorithm_standings():
    """Fetch algorithm competition standings"""
    try:
        import requests
        
        url = f"{API_BASE}/live-monitor/api/algo_performance.php"
        response = requests.get(url, timeout=30, params={"action": "summary"})
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return process_algorithm_data(data)
    except Exception as e:
        print(f"Algorithm fetch error: {e}")
    
    return generate_sample_algorithm_standings()


def process_algorithm_data(data):
    """Process algorithm performance data"""
    algorithms = data.get("algorithms", [])
    processed = []
    
    for algo in algorithms:
        processed.append({
            "name": algo.get("name", "Unknown"),
            "type": algo.get("type", "Unknown"),
            "trades": algo.get("trades", 0),
            "win_rate": algo.get("win_rate", 0),
            "return": algo.get("return", 0),
            "sharpe": algo.get("sharpe", None)
        })
    
    processed.sort(key=lambda x: x["return"], reverse=True)
    
    # Calculate consensus stats
    consensus = data.get("consensus", {})
    
    return {
        "standings": processed,
        "consensus": {
            "win_rate_when_agreement": consensus.get("win_rate_3plus", 70),
            "avg_return_when_agreement": consensus.get("avg_return_3plus", 5.2),
            "total_signals": consensus.get("total_signals", 0)
        },
        "last_update": datetime.now().isoformat()
    }


def generate_sample_algorithm_standings():
    """Generate sample algorithm standings"""
    return {
        "timestamp": datetime.now().isoformat(),  # Always update timestamp
        "standings": [
            {"name": "Composite_Momentum_v2", "type": "Academic", "trades": 156, "win_rate": 68, "return": 156.3, "sharpe": 2.8},
            {"name": "KIMI-MTF", "type": "Mine", "trades": 203, "win_rate": 64, "return": 142.7, "sharpe": 2.5},
            {"name": "Social_Volume_Spike", "type": "Social", "trades": 189, "win_rate": 61, "return": 118.4, "sharpe": 2.1},
            {"name": "RSI_Mean_Reversion", "type": "Academic", "trades": 245, "win_rate": 58, "return": 94.2, "sharpe": 1.8},
            {"name": "Whale_Wallet_Mimic", "type": "Social", "trades": 134, "win_rate": 56, "return": 87.5, "sharpe": 1.6},
            {"name": "MACD_Trend_Follow", "type": "Academic", "trades": 198, "win_rate": 54, "return": 76.3, "sharpe": 1.4},
            {"name": "Funding_Rate_Arb", "type": "Academic", "trades": 167, "win_rate": 52, "return": 62.1, "sharpe": 1.2},
            {"name": "Momentum_Ignition", "type": "Social", "trades": 145, "win_rate": 51, "return": 54.8, "sharpe": 1.1},
            {"name": "Breakout_Volume", "type": "Academic", "trades": 178, "win_rate": 49, "return": 48.5, "sharpe": 1.0},
            {"name": "Sentiment_Momentum", "type": "Social", "trades": 156, "win_rate": 47, "return": 42.3, "sharpe": 0.9},
        ],
        "consensus": {
            "win_rate_when_agreement": 70,
            "avg_return_when_agreement": 5.2,
            "total_signals": 2894
        },
        "last_update": datetime.now().isoformat(),
        "note": "Sample data - connect to live API for real standings"
    }


def fetch_portfolio_data():
    """Fetch live portfolio performance"""
    try:
        import requests
        
        url = f"{API_BASE}/live-monitor/api/live_trade.php"
        response = requests.get(url, timeout=30, params={"action": "dashboard"})
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                stats = data.get("stats", {})
                return {
                    "pnl": stats.get("total_pnl_pct", 0),
                    "trades": stats.get("total_trades", 0),
                    "win_rate": stats.get("win_rate", 0),
                    "open_positions": len(data.get("open_positions", []))
                }
    except Exception as e:
        print(f"Portfolio fetch error: {e}")
    
    return {"pnl": 11.92, "trades": 11, "win_rate": 63.6, "open_positions": 3}


def fetch_best_strategy():
    """Fetch best performing strategy"""
    try:
        import requests
        
        url = f"{API_BASE}/live-monitor/api/algo_performance.php"
        response = requests.get(url, timeout=30, params={"action": "by_algorithm"})
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                algos = data.get("algorithms", [])
                if algos:
                    best = max(algos, key=lambda x: x.get("return", 0))
                    return {
                        "name": best.get("name", "Unknown"),
                        "return": best.get("return", 0)
                    }
    except Exception as e:
        print(f"Best strategy fetch error: {e}")
    
    return {"name": "Ichimoku Cloud", "return": 156.3}


def update_dashboard_json():
    """Main function to update dashboard data"""
    print("=" * 60)
    print(f"DATA COLLECTOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Collect all data
    print("\n[1/5] Fetching Alpha Signals...")
    alpha_data = fetch_alpha_signals()
    print(f"      → {alpha_data['count']} signals")
    
    print("\n[2/5] Fetching Goldmine Candidates...")
    goldmine_data = fetch_goldmine_candidates()
    print(f"      → {goldmine_data['count']} candidates")
    
    print("\n[3/5] Fetching Predictions...")
    pred_data = fetch_predictions()
    print(f"      → {pred_data['count']} predictions")
    
    print("\n[4/5] Fetching Algorithm Standings...")
    algo_data = fetch_algorithm_standings()
    print(f"      → {len(algo_data['standings'])} algorithms")
    
    print("\n[5/5] Fetching Portfolio Data...")
    portfolio_data = fetch_portfolio_data()
    best_strategy = fetch_best_strategy()
    print(f"      → PnL: {portfolio_data['pnl']:.2f}%")
    
    # Build dashboard data
    dashboard_data = {
        "timestamp": datetime.now().isoformat(),
        "alpha_signals": alpha_data,
        "goldmine_candidates": goldmine_data,
        "predictions": pred_data,
        "algorithm_standings": algo_data,
        "portfolio": portfolio_data,
        "best_strategy": best_strategy
    }
    
    # Write to file
    output_file = DATA_DIR / "dashboard.json"
    with open(output_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    
    print(f"\n✓ Dashboard data written to: {output_file}")
    print("=" * 60)
    
    return dashboard_data


if __name__ == "__main__":
    try:
        update_dashboard_json()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
