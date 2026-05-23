"""
ANTIGRAVITY-CLAUDEOPUS Discord Bot — Live Picks & Forward Tracking
====================================================================
Posts real forward-looking predictions and tracks their outcomes.
Clearly separates BACKTEST results from FORWARD (live) results.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("[discord] requests not installed")
    sys.exit(1)

BASE = Path(__file__).resolve().parent
RESULTS_DIR = BASE / "results"
PICKS_DIR = BASE / "live_picks"
AB_TEST_DIR = BASE / "ab_tests"

# Load files
def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _trunc(s, n=1024):
    return s[:n] if len(s) > n else s


def _fmt_price(price):
    if price >= 1000: return f"${price:,.0f}"
    elif price >= 1: return f"${price:.2f}"
    elif price >= 0.01: return f"${price:.4f}"
    else: return f"${price:.6f}"


def build_live_picks_embed(now, active_picks, forward_stats, training_summary):
    """Embed 1: LIVE PICKS RIGHT NOW — forward-looking, non-projected."""
    now_iso = now.isoformat()

    # Training info
    total_models = training_summary.get("total_models", 0) if training_summary else 0
    ab_winner = training_summary.get("ab_test_winner", "N/A") if training_summary else "N/A"
    trained_at = training_summary.get("trained_at", "unknown") if training_summary else "unknown"

    # Active picks
    if active_picks:
        # Sort by confidence/probability
        active_picks.sort(key=lambda p: -float(p.get("probability", 0)))
        top_picks = active_picks[:8]

        pick_lines = []
        for p in top_picks:
            sym = p.get("symbol", "?").replace("USDT", "")
            tf = p.get("timeframe", "?")
            direction = p.get("direction", "?")
            entry = float(p.get("entry_price", 0))
            current = float(p.get("current_price", entry))
            tp = float(p.get("take_profit", 0))
            sl = float(p.get("stop_loss", 0))
            prob = float(p.get("probability", 0))
            conf = p.get("confidence", "?")
            pnl = float(p.get("unrealized_pnl_pct", 0))

            emoji = "\U0001f7e2" if direction == "BUY" else "\U0001f534"
            pnl_emoji = "\U0001f4c8" if pnl >= 0 else "\U0001f4c9"
            pnl_str = f"{pnl:+.1f}%"

            pick_lines.append(
                f"{emoji} **{direction}** `{sym}/{tf}` @ {_fmt_price(entry)} "
                f"| TP:{_fmt_price(tp)} SL:{_fmt_price(sl)} "
                f"| {pnl_emoji} {pnl_str} | {conf} ({prob:.0%})"
            )

        total_active = len(active_picks)
        total_buy = sum(1 for p in active_picks if p.get("direction") == "BUY")
        total_sell = total_active - total_buy
        green = sum(1 for p in active_picks if float(p.get("unrealized_pnl_pct", 0)) > 0)

        picks_text = (
            f"**{total_active} LIVE PICKS** | {total_buy} BUY / {total_sell} SELL | {green} green\n\n"
            + "\n".join(pick_lines)
        )
        if total_active > 8:
            picks_text += f"\n*+{total_active - 8} more positions*"
    else:
        picks_text = "No active picks yet. Waiting for next prediction cycle."

    # ─── Performance Transparency ───
    fs = forward_stats or {}
    # Check archived stats if current is empty
    archived_stats_path = PICKS_DIR / "archive_v1.2" / "forward_stats.json"
    archived_fs = _load(archived_stats_path) or {}
    fwd_picks = fs.get("total_picks", 0) or archived_fs.get("total_picks", 0)
    fwd_wr = fs.get("win_rate", 0) or archived_fs.get("win_rate", 0)
    fwd_sharpe = fs.get("sharpe_ratio", 0) or archived_fs.get("sharpe_ratio", 0)
    fwd_pf = fs.get("profit_factor", 0) or archived_fs.get("profit_factor", 0)
    fwd_pnl = fs.get("total_pnl_pct", 0) or archived_fs.get("total_pnl_pct", 0)
    version = fs.get("version", "v1.3")

    # Direction analysis from archived closed picks
    archived_closed = _load(PICKS_DIR / "archive_v1.2" / "closed_picks.json") or []
    buy_wins = sum(1 for p in archived_closed if p.get('direction') == 'BUY' and float(p.get('actual_pnl_pct', 0)) > 0)
    buy_total = sum(1 for p in archived_closed if p.get('direction') == 'BUY')
    sell_wins = sum(1 for p in archived_closed if p.get('direction') == 'SELL' and float(p.get('actual_pnl_pct', 0)) > 0)
    sell_total = sum(1 for p in archived_closed if p.get('direction') == 'SELL')
    buy_wr = buy_wins / max(buy_total, 1) * 100
    sell_wr = sell_wins / max(sell_total, 1) * 100

    perf_text = (
        f"⚠️ **Model NOT profitable yet** ({version})\n"
        f"FORWARD WR: **{fwd_wr:.1f}%** | FORWARD Sharpe: **{fwd_sharpe:.2f}** | FORWARD PF: **{fwd_pf:.2f}** | FORWARD P&L: **{fwd_pnl:+.1f}%**\n"
        f"FORWARD BUY WR: {buy_wr:.0f}% ({buy_wins}W/{buy_total-buy_wins}L) | FORWARD SELL WR: {sell_wr:.0f}% ({sell_wins}W/{sell_total-sell_wins}L)\n"
        f"📊 [Forensic Analysis Dashboard](https://findtorontoevents.ca/crypto_roocode/live-picks.html)\n"
        f"*6 root causes identified. All fixes deployed. Paper trading only.*"
    )

    embed = {
        "title": "\U0001f680 ANTIGRAVITY-CLAUDEOPUS | Live Picks (FORWARD)",
        "description": (
            "*These are REAL forward-looking predictions, NOT backtested. "
            "Every pick is tracked from entry to exit for honest performance.*"
        ),
        "color": 0x6366f1,  # Purple
        "timestamp": now_iso,
        "fields": [
            {
                "name": "⚠️ Performance Transparency (Live)",
                "value": _trunc(perf_text),
                "inline": False,
            },
            {
                "name": "\U0001f3af Live Positions (Non-Projected)",
                "value": _trunc(picks_text),
                "inline": False,
            },
            {
                "name": "\U0001f916 Model Info",
                "value": _trunc(
                    f"Models: **{total_models}** | Champion: **{ab_winner}**\n"
                    f"Last trained: {str(trained_at)[:16]} UTC\n"
                    f"Data: TRIPLED (up to 15,000 candles/pair)\n"
                    f"🔗 [**LIVE DASHBOARD**](https://findtorontoevents.ca/crypto_roocode/live-picks.html) — Full forensic analysis"
                ),
                "inline": False,
            },
        ],
        "footer": {
            "text": f"ANTIGRAVITY-CLAUDEOPUS {version} | FORWARD: {fwd_wr:.0f}% WR ({fwd_picks} forward picks) | NOT FINANCIAL ADVICE",
        },
    }
    return embed


def build_forward_vs_backtest_embed(now, forward_stats, ab_report):
    """Embed 2: FORWARD vs BACKTEST honest comparison."""
    now_iso = now.isoformat()

    # Simpleton baseline
    simpleton = {
        "sharpe": 0.567, "win_rate": 51.3,
        "pf": 1.09, "max_dd": -34.1
    }

    # Forward stats
    if forward_stats and forward_stats.get("total_picks", 0) > 0:
        fs = forward_stats
        forward_text = (
            f"**FORWARD Picks (REAL — not backtested):**\n"
            f"Total: {fs['total_picks']} | W:{fs['wins']} L:{fs['losses']}\n"
            f"FORWARD Win Rate: **{fs['win_rate']}%**\n"
            f"FORWARD Sharpe: **{fs['sharpe_ratio']}**\n"
            f"FORWARD Profit Factor: **{fs['profit_factor']}**\n"
            f"FORWARD Max Drawdown: **{fs['max_drawdown_pct']}%**\n"
            f"FORWARD P&L: **{fs['total_pnl_pct']:+.1f}%**\n"
            f"Forward TP Hits: {fs['tp_hits']} | SL Hits: {fs['sl_hits']} | Expired: {fs['expired']}"
        )

        # Comparison — compute directly from numbers, don't rely on stored booleans
        markers = []
        our_sharpe = float(fs.get("sharpe_ratio", 0))
        our_wr = float(fs.get("win_rate", 0))
        our_pf = float(fs.get("profit_factor", 0))

        if our_sharpe > simpleton["sharpe"]:
            markers.append("\U00002705 FORWARD Sharpe BEATS BACKTEST Simpleton")
        else:
            markers.append(f"\U0000274c FORWARD Sharpe {our_sharpe:.3f} vs BACKTEST Simpleton {simpleton['sharpe']}")

        if our_wr > simpleton["win_rate"]:
            markers.append("\U00002705 FORWARD Win Rate BEATS BACKTEST Simpleton")
        else:
            markers.append(f"\U0000274c FORWARD WR {our_wr}% vs BACKTEST Simpleton {simpleton['win_rate']}%")

        if our_pf > simpleton["pf"]:
            markers.append("\U00002705 FORWARD Profit Factor BEATS BACKTEST Simpleton")
        else:
            markers.append(f"\U0000274c FORWARD PF {our_pf} vs BACKTEST Simpleton {simpleton['pf']}")

        comparison_text = "\n".join(markers)
    else:
        forward_text = (
            "**Forward Picks:** 0 completed yet\n"
            "Collecting live predictions... check back in 4-12 hours.\n"
            "Need 30+ closed picks for meaningful forward stats."
        )
        comparison_text = "Waiting for first closed picks to compare..."

    # Backtest stats
    if ab_report:
        total_exp = ab_report.get("total_experiments", 0)
        variant_wins = ab_report.get("variant_wins", {})
        aucs = []
        pos_sharpes = []
        for k, v in ab_report.get("per_pair_results", {}).items():
            w = v["all_variants"][v["winner"]]
            aucs.append(w["roc_auc"])
            sh = w.get("sharpe_ratio", 0)
            if sh > 0:
                pos_sharpes.append(sh)

        avg_auc = sum(aucs) / len(aucs) if aucs else 0
        above60 = sum(1 for a in aucs if a > 0.60)

        backtest_text = (
            f"**BACKTEST Results (Historical simulation):**\n"
            f"Total models: {total_exp * 4} across {total_exp} pair/TF combos\n"
            f"BACKTEST Avg AUC: {avg_auc:.4f} | AUC>0.60: {above60}/{len(aucs)}\n"
            f"BACKTEST Positive Sharpe models: {len(pos_sharpes)}\n"
            f"Champion: {variant_wins}\n\n"
            f"**Key:** BACKTEST = past data only. FORWARD = real live data.\n"
            f"Typically FORWARD = 60-80% of BACKTEST due to slippage + regime shifts."
        )
    else:
        backtest_text = "No backtest data available."

    embed = {
        "title": "\U0001f4ca ANTIGRAVITY-CLAUDEOPUS | Forward vs Backtest",
        "description": (
            "*Honest comparison: REAL forward picks vs historical backtests. "
            "Baseline to beat: Simpleton Signals v0.07*"
        ),
        "color": 0x22c55e,  # Green
        "timestamp": now_iso,
        "fields": [
            {
                "name": "\U0001f3af Forward Results (LIVE)",
                "value": _trunc(forward_text),
                "inline": True,
            },
            {
                "name": "\U0001f4da Backtest Results (HISTORICAL)",
                "value": _trunc(backtest_text),
                "inline": True,
            },
            {
                "name": f"\U0001f3c6 vs Simpleton Signals v0.07",
                "value": _trunc(
                    f"**Simpleton BACKTEST Baseline:**\n"
                    f"BACKTEST Sharpe: {simpleton['sharpe']} | BACKTEST WR: {simpleton['win_rate']}% | "
                    f"BACKTEST PF: {simpleton['pf']} | BACKTEST MaxDD: {simpleton['max_dd']}%\n\n"
                    f"**Our FORWARD Status:**\n{comparison_text}"
                ),
                "inline": False,
            },
            {
                "name": "\U0001f517 Links",
                "value": _trunc(
                    "📊 [**LIVE DASHBOARD**](https://findtorontoevents.ca/crypto_roocode/live-picks.html) — Full picks with reasoning\n"
                    "[Forward Picks Data](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/ml_crypto_predictor/enhanced_models/live_picks) | "
                    "[Source Code](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/ml_crypto_predictor/enhanced_models) | "
                    "[Architecture](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/ml_crypto_predictor/ANTIGRAVITY_ALPHA_ENGINE.md)"
                ),
                "inline": False,
            },
        ],
        "footer": {
            "text": "ANTIGRAVITY-CLAUDEOPUS | Transparency > Marketing | github.com/eltonaguiar",
        },
    }
    return embed


def post_to_discord(embeds):
    """Send embeds to Discord via webhook."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        print("[discord] No DISCORD_WEBHOOK_URL — printing to stdout")
        for i, embed in enumerate(embeds):
            print(f"\n{'='*60}\nEMBED {i+1}:\n{'='*60}")
            print(json.dumps(embed, indent=2, default=str))
        return False

    payload = {
        "username": "ANTIGRAVITY-CLAUDEOPUS",
        "content": None,
        "embeds": embeds,
    }

    import time as _time
    for _attempt in range(3):
        try:
            r = requests.post(webhook_url, json=payload, timeout=15)
            if r.status_code in (200, 204):
                print(f"[discord] Posted {len(embeds)} embeds as ANTIGRAVITY-CLAUDEOPUS")
                return True
            if r.status_code == 429:
                _time.sleep(r.json().get("retry_after", 3))
                continue
            print(f"[discord] Discord returned {r.status_code}: {r.text[:300]}")
            if _attempt < 2:
                _time.sleep(2 * (_attempt + 1))
                continue
            return False
        except Exception as e:
            if _attempt == 2:
                print(f"[discord] Webhook failed after 3 attempts: {e}")
            else:
                _time.sleep(2 * (_attempt + 1))
        return False


def main():
    """Full cycle: update picks → build HTML → build embeds → post to Discord."""
    print("=" * 70)
    print("ANTIGRAVITY-CLAUDEOPUS — Discord Status Update")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    now = datetime.now(timezone.utc)

    # Run prediction cycle first
    from .live_picks_tracker import run_prediction_cycle
    cycle_result = run_prediction_cycle()

    # Generate HTML page
    try:
        from .generate_picks_html import generate_html
        html_path = generate_html()
        print(f"[discord] HTML page generated: {html_path}")
    except Exception as e:
        print(f"[discord] HTML generation failed: {e}")

    # Load data for embeds
    active_picks = _load(PICKS_DIR / "active_picks.json") or []
    forward_stats = _load(PICKS_DIR / "forward_stats.json") or {}
    training_summary = _load(RESULTS_DIR / "training_summary.json") or {}
    ab_report = _load(AB_TEST_DIR / "ab_test_report.json") or {}

    # Build embeds
    live_embed = build_live_picks_embed(now, active_picks, forward_stats, training_summary)
    comparison_embed = build_forward_vs_backtest_embed(now, forward_stats, ab_report)

    # Post to Discord
    post_to_discord([live_embed, comparison_embed])

    print("\n[discord] Status update complete.")


if __name__ == "__main__":
    main()

