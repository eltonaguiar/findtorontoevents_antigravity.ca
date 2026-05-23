import json
import os
import time
from datetime import datetime, timezone
import requests
from pathlib import Path
# Load Opposite Day stats (if available)
SANDBOX_STATS_PATH = Path("sandbox/opposite_day_stats.json")
if SANDBOX_STATS_PATH.is_file():
    try:
        sandbox_stats = json.loads(SANDBOX_STATS_PATH.read_text())
    except Exception:
        sandbox_stats = {}
else:
    sandbox_stats = {}

TRACKER_DIR = Path("crypto_gainer_ml/tracker")

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return {}

def get_ml_status():
    scorecard = load_json(TRACKER_DIR / "scorecard.json")
    perf_summary = load_json(TRACKER_DIR / "performance_summary.json")
    live_picks = load_json(TRACKER_DIR / "live_picks.json")
    pick_history = load_json(TRACKER_DIR / "pick_history.json")
    learned_weights = load_json(TRACKER_DIR / "learned_weights.json")

    # Additional reports
    ml_report_path = Path("CRYPTO_TRADING_SYSTEM_REPORT.json")
    forward_test_path = Path("forward_test_results.json")
    ml_report = load_json(ml_report_path) if ml_report_path.exists() else {}
    forward_test = load_json(forward_test_path) if forward_test_path.exists() else {}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Training level
    training_level = f"Feedback Iterations: {len(pick_history)} | Version: {perf_summary.get('model_version', 'N/A')} | Active Picks: {len(live_picks)}"

    # Confidence (p-values, win rates)
    live_wr = scorecard.get('win_rate', 0)
    pf = scorecard.get('profit_factor', 0)
    p_value = ml_report.get('executive_summary', {}).get('target_metrics', {}).get('p_value', 'N/A')
    confidence = f"Live Win Rate: {live_wr:.1f}% (n={scorecard.get('total_picks', 0)}) | Profit Factor: {pf:.2f} | Ensemble p-value: {p_value}"

    # Signal confidence from learned weights
    stats_str = ""
    if learned_weights.get('stats'):
        for sig, stat in learned_weights['stats'].items():
            wr = stat.get('wr', 0)
            stats_str += f"{sig}: {wr:.0f}% | "
    confidence += f"\nSignals: {stats_str}"

    # Fun Math explanations
    confidence += '\n\n**Fun Math (High School Level):**\n• Sharpe Ratio: Profit scoops / Risk wobble (>1.5 excellent!)\n• p-value: Luck chance (<0.05 = real edge, not coin flips)\n• Profit Factor: Total wins / losses (>1.5 ideal)'

    # Testing done/future
    back_sharpe = ml_report.get('executive_summary', {}).get('target_metrics', {}).get('sharpe_ratio', 'N/A')
    fwd_days = forward_test.get('forward_test_period', {}).get('trading_days', 'N/A')
    testing = f"Resolved: {len(pick_history)} | Backtest Sharpe: {back_sharpe} | Forward Test: {fwd_days} days | Future: Ongoing live + monthly retrain"

    testing += '\n\n**Sharpe Explained:** Reward per risk unit. Like MPG for profits — higher = better mileage on your money!'

    # Continual improvement
    improve_str = "Learned Weights (recent):\n"
    if learned_weights.get('weights'):
        for sig, w in list(learned_weights['weights'].items())[:5]:  # Top 5
            improve_str += f"{sig}: {w} | "
    improve_str += f"\nLast update: {learned_weights.get('last_updated', 'N/A')}"

    # Example signal
    example = "No active picks"
    if live_picks:
        top_pick = max(live_picks, key=lambda p: p.get('gainer_score', 0))
        sym = top_pick.get('symbol', '?')
        score = top_pick.get('gainer_score', 0)
        signals = ', '.join(top_pick.get('signals', [])[:3])
        pnl = top_pick.get('unrealized_pnl', 0)
        example = f"{sym} | Score: {score} | Signals: {signals} | Unrealized: {pnl:+.2f}%"

    return {
        "training_level": training_level,
        "confidence": confidence,
        "testing": testing,
        "improvement": improve_str,
        "example_signal": example,
        "timestamp": now
    }

def send_discord_status(webhook_url=None):
    status = get_ml_status()
    scorecard = load_json(TRACKER_DIR / "scorecard.json")
    color = 0x00ff00 if scorecard.get('win_rate', 0) > 50 else 0xffa500 if scorecard.get('win_rate', 0) > 30 else 0xff0000
# Load Opposite Day stats (if present) for inclusion in the embed
SANDBOX_STATS_PATH = Path("sandbox/opposite_day_stats.json")
if SANDBOX_STATS_PATH.is_file():
    try:
        sandbox_stats = json.loads(SANDBOX_STATS_PATH.read_text())
    except Exception as e:
        sandbox_stats = {}
else:
    sandbox_stats = {}


    launch_status = "2026-02-22; needs 1-3 months training"

    dashboard_links = '`Live Picks`: https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/crypto_gainer_ml/tracker/live_picks.json\n`Scorecard`: https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/crypto_gainer_ml/tracker/scorecard.json\n`Perf Summary`: https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/crypto_gainer_ml/tracker/performance_summary.json\n`Learned Weights`: https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/crypto_gainer_ml/tracker/learned_weights.json\n\n[GitHub Repo](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/crypto_gainer_ml)\n[Live Dashboard](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/)'

    embed = {
        "title": "Crypto Gainer ML - Full Status Report! (Fun Math + Raw Data + Sharpe)",
        "description": "🤖 High-school friendly AI report!\n\nThis bot uses machine learning to predict crypto gainers.\nLike training a dog: Show past trades (data), reward good predictions.\n\nIncludes:\n• Raw numbers & JSON links\n• Fun math explanations (Sharpe, p-value)\n• Live picks & performance",
        "color": color,
        "fields": [
            {
                "name": "📊 Training Level",
                "value": status['training_level'],
                "inline": False
            },
            {
                "name": "📈 Confidence (Live Stats + p-values)",
                "value": status['confidence'],
                "inline": False
            },
            {
                "name": "🧪 Testing (Backtest + Forward)",
                "value": status['testing'],
                "inline": False
            },
            {
                "name": "🔄 Self-Improvement (Learned Weights)",
                "value": status['improvement'],
                "inline": False
            },
            {
                "name": "🎯 Top Live Signal Example",
                "value": status['example_signal'],
                "inline": False
            },
            {
                "name": "🧪 Opposite Day Win‑Rate",
                "value": f"{sandbox_stats.get('win_rate_pct', 0)}%",
                "inline": True
            },
            {
                "name": "🧪 Opposite Day Profit Factor",
                "value": str(sandbox_stats.get('profit_factor', 'N/A')),
                "inline": True
            },
            {
                "name": "🧪 Opposite Day Closed Picks",
                "value": str(sandbox_stats.get('closed_opposite_picks', 0)),
                "inline": True
            },
            {
                "name": "🚀 Launch Status",
                "value": launch_status,
                "inline": False
            },
            {
                "name": "🔗 Dashboard & Raw Data (Click to Verify!)",
                "value": dashboard_links,
                "inline": False
            }
        ],
        "footer": {
            "text": f"VS CODE_ROOCODE_GROKFAST1 | {status['timestamp']} | Paper Trading Only | Not financial advice — DYOR!"
        }
    }

    webhook_url = webhook_url or os.getenv("DISCORD_STATUS_WEBHOOK")
    if not webhook_url:
        print("No DISCORD_STATUS_WEBHOOK env var set. Printing status instead:")
        print(json.dumps(status, indent=2))
        print("\nEmbed preview:")
        print(json.dumps(embed, indent=2))
        return

    payload = { "embeds": [embed] }
    for _attempt in range(3):
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                print("Discord message sent successfully")
                break
            if resp.status_code == 429:
                time.sleep(resp.json().get("retry_after", 3))
                continue
            print(f"Discord error: {resp.status_code} - {resp.text}")
            if _attempt < 2:
                time.sleep(2 * (_attempt + 1))
                continue
            break
        except Exception as e:
            if _attempt == 2:
                print(f"Send error after 3 attempts: {e}")
            else:
                time.sleep(2 * (_attempt + 1))

if __name__ == "__main__":
    send_discord_status()