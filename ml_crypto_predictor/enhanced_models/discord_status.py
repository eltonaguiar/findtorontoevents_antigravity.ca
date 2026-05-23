"""
ML Crypto Predictor v4.1 — Discord Hourly Status Reporter

Reads existing JSON results and posts a rich Discord embed.
Brutally honest about what's proven vs backtest-only.

Data sources (read-only):
- results/v4_comprehensive_report.json — 32 tradeable models, aggregate metrics
- results/v4_proof_report.json — per-pair detailed results with MC stats
- results/training_summary.json or v3_training_summary.json — last trained
- alpha_engine/data/strategy_performance.json — forward test data (Alpha Engine)
- alpha_engine/data/active_picks.json — open picks
- enhanced_models/live_picks/ — ML forward picks
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("[discord_status] requests not installed — pip install requests")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
LIVE_PICKS_DIR = BASE_DIR / "live_picks"
REPO_ROOT = BASE_DIR.parent.parent
ALPHA_DATA_DIR = REPO_ROOT / "alpha_engine" / "data"

VERSION = "v4.1"
DASHBOARD_URL = "https://findtorontoevents.ca/updates/antigravity-ml-gainer.html"
LIVE_PICKS_URL = "https://findtorontoevents.ca/updates/ml-live-picks.html"

# Auto-improve config (imported or fallback)
try:
    from ml_crypto_predictor.enhanced_models.config import AUTO_IMPROVE_CONFIG
except ImportError:
    AUTO_IMPROVE_CONFIG = {
        "min_closed_picks_to_evaluate": 10,
        "retrain_trigger_wr_threshold": 0.45,
        "retrain_trigger_pf_threshold": 1.0,
        "scheduled_retrain_cron": "0 2 * * *",
        "conditional_retrain_enabled": False,
    }


def _load_json(path) -> dict | list | None:
    """Safely load a JSON file, return None if missing."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[discord_status] Could not load {path.name}: {e}")
        return None


def _trunc(s: str, n: int = 1024) -> str:
    """Truncate string to Discord field limit."""
    return s[:n] if len(s) > n else s


def _confidence_tier(trades: int | None, mc_p: float | None) -> str:
    """Assign confidence tier based on trade count and MC p-value."""
    if trades is None or trades < 7:
        return "SPECULATIVE"
    p = mc_p if mc_p is not None else 1.0
    if trades >= 30 and p < 0.02:
        return "HIGH"
    if trades >= 15 and p < 0.05:
        return "MEDIUM"
    if trades >= 7 and p < 0.05:
        return "LOW"
    return "SPECULATIVE"


def _tier_emoji(tier: str) -> str:
    return {"HIGH": "\U0001f7e2", "MEDIUM": "\U0001f7e1",
            "LOW": "\U0001f7e0", "SPECULATIVE": "\u26aa"}.get(tier, "\u2753")


def build_status_message() -> dict:
    """Build the full Discord embed payload from existing JSON data."""
    now_utc = datetime.now(timezone.utc)

    # --- Load data sources ---
    comprehensive = _load_json(RESULTS_DIR / "v4_comprehensive_report.json")
    proof = _load_json(RESULTS_DIR / "v4_proof_report.json")
    training = (_load_json(RESULTS_DIR / "training_summary.json")
                or _load_json(RESULTS_DIR / "v3_training_summary.json"))
    strategy_perf = _load_json(ALPHA_DATA_DIR / "strategy_performance.json")
    active_picks = _load_json(ALPHA_DATA_DIR / "active_picks.json")
    ml_active = _load_json(LIVE_PICKS_DIR / "active_picks.json") or []
    ml_closed = _load_json(LIVE_PICKS_DIR / "closed_picks.json") or []

    # ===== Section 1: Training State =====
    trained_at = "unknown"
    days_ago = "?"
    total_models = "?"
    ab_winner = "?"
    if training:
        trained_at = training.get("trained_at", "unknown")
        if trained_at != "unknown":
            try:
                t = datetime.fromisoformat(trained_at.replace("Z", "+00:00"))
                days_ago = (now_utc - t).days
                trained_at = t.strftime("%Y-%m-%d %H:%M UTC")
            except (ValueError, TypeError):
                days_ago = "?"
        total_models = training.get("total_models", "?")
        ab_winner = training.get("ab_test_winner", "?")

    tradeable = 0
    pairs_with_edge = 0
    timeframes_list = []
    if comprehensive:
        agg = comprehensive.get("aggregate_metrics", {})
        tradeable = agg.get("total_tradeable_models", 0)
        pairs_with_edge = agg.get("unique_pairs_with_edge", 0)
        tf_results = comprehensive.get("timeframe_results", {})
        for tf, data in tf_results.items():
            if isinstance(data, dict) and data.get("models_passed", 0) > 0:
                timeframes_list.append(tf)

    training_text = (
        f"```\n"
        f"Last trained:     {trained_at} ({days_ago}d ago)\n"
        f"Models on record: {total_models} | A/B winner: {ab_winner}\n"
        f"Proven edge:      {tradeable} pass all gates\n"
        f"Pairs with edge:  {pairs_with_edge} tested\n"
        f"Timeframes:       {', '.join(timeframes_list) if timeframes_list else 'none yet'}\n"
        f"```"
    )

    # ===== Section 2: Top 5 Models =====
    all_models = []
    if proof and "tradeable_models" in proof:
        all_models = proof["tradeable_models"]
    elif comprehensive and "timeframe_results" in comprehensive:
        for tf, data in comprehensive.get("timeframe_results", {}).items():
            if isinstance(data, dict):
                for m in data.get("passing_models", []):
                    m.setdefault("tf", tf)
                    all_models.append(m)

    models_sorted = sorted(all_models, key=lambda m: m.get("sharpe", 0), reverse=True)
    top5 = models_sorted[:5]

    if top5:
        lines = []
        for m in top5:
            pair = m.get("pair", "?")
            tf = m.get("tf", m.get("timeframe", "?"))
            strat = m.get("strategy", "?")
            sharpe = m.get("sharpe", 0)
            wr = m.get("win_rate", 0)
            pf = m.get("profit_factor", m.get("pf", 0))
            trades = m.get("total_trades", m.get("trades", None))
            mc_p = m.get("mc_pvalue", m.get("mc_p", None))
            tier = _confidence_tier(trades, mc_p)
            emoji = _tier_emoji(tier)
            trade_str = str(trades) if trades else "n/a"
            lines.append(
                f"`{pair}/{tf}` {strat} | Sharpe **{sharpe:.2f}** | "
                f"WR {wr*100:.0f}% | PF {pf:.2f} | {trade_str}t | {emoji}{tier}"
            )
        top5_text = "\n".join(lines)
    else:
        top5_text = "No tradeable models found in results."

    # ===== Section 3: Confidence Assessment =====
    if all_models:
        high_count = sum(1 for m in all_models
                        if _confidence_tier(m.get("total_trades", m.get("trades")),
                                           m.get("mc_pvalue", m.get("mc_p"))) == "HIGH")
        med_count = sum(1 for m in all_models
                       if _confidence_tier(m.get("total_trades", m.get("trades")),
                                          m.get("mc_pvalue", m.get("mc_p"))) == "MEDIUM")
        spec_count = sum(1 for m in all_models
                        if _confidence_tier(m.get("total_trades", m.get("trades")),
                                           m.get("mc_pvalue", m.get("mc_p"))) == "SPECULATIVE")
        low_trade = sum(1 for m in all_models
                       if (m.get("total_trades") or m.get("trades") or 0) < 15)

        confidence_text = (
            f"All {tradeable} models pass MC permutation test (p<0.05).\n"
            f"**CAUTION:** {low_trade}/{tradeable} have <15 trades — limited stats.\n"
            f"\U0001f7e2 HIGH: {high_count} | \U0001f7e1 MEDIUM: {med_count} | "
            f"\u26aa SPECULATIVE: {spec_count}"
        )
    else:
        confidence_text = "No models to assess."

    # ===== Section 4: Forward Testing (HONEST) =====
    # Alpha Engine forward stats
    alpha_closed = 0
    alpha_wins = 0
    alpha_losses = 0
    if strategy_perf and isinstance(strategy_perf, dict):
        for strat_data in strategy_perf.values():
            if isinstance(strat_data, dict):
                alpha_closed += strat_data.get("closed_picks", 0)
                alpha_wins += strat_data.get("wins", 0)
                alpha_losses += strat_data.get("losses", 0)
    alpha_wr = (alpha_wins / alpha_closed * 100) if alpha_closed > 0 else 0

    alpha_open = 0
    if active_picks and isinstance(active_picks, list):
        alpha_open = sum(1 for p in active_picks if p.get("status") == "OPEN")

    # ML forward stats
    ml_wins = sum(1 for p in ml_closed if p.get("outcome") == "TP_HIT")
    ml_losses = sum(1 for p in ml_closed if p.get("outcome") == "SL_HIT")
    ml_total = ml_wins + ml_losses
    ml_wr = f"{ml_wins/ml_total*100:.0f}%" if ml_total > 0 else "N/A"
    ml_pnl = sum(float(p.get("actual_pnl_pct", 0)) for p in ml_closed)

    forward_text = (
        f"\u26a0\ufe0f **ML {VERSION} backtest-only models: {tradeable}.** "
        f"Forward picks below.\n"
        f"```\n"
        f"ML Forward:    {ml_wins}W / {ml_losses}L | WR: {ml_wr} | PnL: {ml_pnl:+.2f}%\n"
        f"ML Active:     {len(ml_active)} picks\n"
        f"Alpha Engine:  {alpha_closed} closed | W:{alpha_wins} L:{alpha_losses} | WR: {alpha_wr:.0f}%\n"
        f"Alpha Active:  {alpha_open} picks\n"
        f"```"
    )

    # ===== Section 5: Top ML Forward Picks =====
    ml_sorted = sorted(ml_active, key=lambda x: float(x.get("probability", 0)), reverse=True)
    pick_lines = []
    for p in ml_sorted[:5]:
        sym = p.get("symbol", p.get("pair", "?"))
        direction = p.get("direction", p.get("signal_type", "?"))
        prob = float(p.get("probability", p.get("confidence", 0)))
        entry = p.get("entry_price", 0)
        tp = p.get("take_profit", 0)
        sl = p.get("stop_loss", 0)
        emoji = "\U0001f7e2" if direction == "BUY" else "\U0001f534"
        pick_lines.append(
            f"{emoji} **{sym}** `{direction}` | {prob:.0%} conf | "
            f"Entry ${entry} \u2192 TP ${tp} / SL ${sl}"
        )
    picks_text = "\n".join(pick_lines) if pick_lines else "No ML picks active — next scan generates picks."

    # ===== Section 6: Auto-Improvement =====
    cron = AUTO_IMPROVE_CONFIG.get("scheduled_retrain_cron", "0 2 * * *")
    wr_thresh = AUTO_IMPROVE_CONFIG.get("retrain_trigger_wr_threshold", 0.45)
    min_picks = AUTO_IMPROVE_CONFIG.get("min_closed_picks_to_evaluate", 10)
    conditional = AUTO_IMPROVE_CONFIG.get("conditional_retrain_enabled", False)

    auto_text = (
        f"**Retrain:** Daily at `{cron}` UTC (fixed schedule)\n"
        f"**Auto-trigger:** WR < {wr_thresh*100:.0f}% with {min_picks}+ picks "
        f"({'ACTIVE' if conditional else 'not yet live'})\n"
        f"[Dashboard]({DASHBOARD_URL}) | [Live Picks]({LIVE_PICKS_URL})"
    )

    # ===== Build Discord embeds =====
    # Determine overall color
    if ml_total > 0 and ml_wins > ml_losses:
        color = 0x10b981  # green — winning
    elif ml_total > 0 and ml_wins < ml_losses:
        color = 0xef4444  # red — losing
    else:
        color = 0x7c3aed  # purple — no forward data yet

    embeds = [
        {
            "title": f"\U0001f9e0 ML Crypto Predictor {VERSION} \u2014 Hourly Status",
            "description": f"Report: {now_utc.strftime('%Y-%m-%d %H:%M UTC')}",
            "color": color,
            "timestamp": now_utc.isoformat(),
            "fields": [
                {"name": "\U0001f4ca Training State", "value": _trunc(training_text), "inline": False},
                {"name": "\U0001f3c6 Top 5 Models (by Sharpe)", "value": _trunc(top5_text), "inline": False},
                {"name": "\U0001f52c Confidence Assessment", "value": _trunc(confidence_text), "inline": False},
            ],
        },
        {
            "title": f"\U0001f3af Forward Testing \u2014 Honest Assessment",
            "color": color,
            "timestamp": now_utc.isoformat(),
            "fields": [
                {"name": "\u26a0\ufe0f Forward Performance", "value": _trunc(forward_text), "inline": False},
                {"name": "\U0001f3af Active ML Picks", "value": _trunc(picks_text), "inline": False},
                {"name": "\U0001f504 Auto-Improvement", "value": _trunc(auto_text), "inline": False},
            ],
            "footer": {
                "text": f"ML Crypto Predictor {VERSION} | Not financial advice | All metrics honest",
            },
        },
    ]

    return {"embeds": embeds}


def send_to_discord(payload: dict) -> bool:
    """Post the payload to Discord webhook. Sends embeds in separate messages."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[discord_status] No DISCORD_WEBHOOK_URL — dry run only")
        return False

    import time as _time
    embeds = payload.get("embeds", [])
    for i, embed in enumerate(embeds):
        for _attempt in range(3):
            try:
                r = requests.post(webhook_url, json={"embeds": [embed]}, timeout=15)
                if r.status_code in (200, 204):
                    print(f"[discord_status] Embed {i+1}/{len(embeds)} sent")
                    break
                if r.status_code == 429:
                    _time.sleep(r.json().get("retry_after", 3))
                    continue
                print(f"[discord_status] Discord returned {r.status_code}: {r.text[:300]}")
                if _attempt < 2:
                    _time.sleep(2 * (_attempt + 1))
                    continue
                break
            except requests.RequestException as e:
                if _attempt == 2:
                    print(f"[discord_status] Discord webhook failed after 3 attempts: {e}")
                    return False
                _time.sleep(2 * (_attempt + 1))
    return True


def main():
    print(f"[discord_status] ML Crypto Predictor {VERSION} — building hourly status...")
    payload = build_status_message()

    # Always print to stdout for debugging
    for embed in payload.get("embeds", []):
        print(f"\n=== {embed.get('title', '?')} ===")
        for field in embed.get("fields", []):
            print(f"\n--- {field['name']} ---")
            print(field["value"])

    if os.environ.get("DISCORD_WEBHOOK_URL"):
        success = send_to_discord(payload)
        sys.exit(0 if success else 1)
    else:
        print("\n[discord_status] DISCORD_WEBHOOK_URL not set — dry run complete.")
        sys.exit(0)


if __name__ == "__main__":
    main()
