"""
Discord Webhook Notifications -- Cross-System Consensus Picks
=============================================================
Posts top consensus picks to Discord with:
  - Signal tier classification (STRONG BUY / BUY / NEUTRAL / SELL / STRONG SELL)
  - Entry/TP/SL, confidence, agreeing systems, R:R ratio
  - Position sizing via ATR vol-targeting
  - Visual progress bars for confidence and agreement
  - Reversal warning conditions (when to exit)
  - SL hit alerts, position updates, portfolio summaries
  - Rate limiting (30 min per symbol) with priority bypass
  - Batch embedding (up to 10 per message)
  - Tracking dashboard URL
  - All timestamps in EST

Uses DISCORD_WEBHOOK_URL from environment (same as all other systems).
Optional: DISCORD_WEBHOOK_PORTFOLIO for portfolio-specific channel.

Usage:
    python -m cross_aggregation.discord_notify
    # or import and call:
    from cross_aggregation.discord_notify import send_consensus_alert
"""

import json
import math
import os
import pathlib
import sys
import requests
import time as _time
from datetime import datetime, timezone, timedelta
from typing import Optional

# Repo root for imports
_repo_root_str = str(pathlib.Path(__file__).resolve().parent.parent)
if _repo_root_str not in sys.path:
    sys.path.insert(0, _repo_root_str)

# Shared formatting utils
from utils.discord_format import format_confidence_breakdown, format_per_system_stats
from utils.discord_heartbeat import send_no_picks_heartbeat

# Audit trail integration
try:
    from audit_trail import record_event as _audit_event
    _HAS_AUDIT = True
except ImportError:
    _HAS_AUDIT = False

# MySQL audit trail (fire-and-forget, never blocks Discord sends)
try:
    from audit_trail.mysql_client import log_discord_send as _mysql_log_send
    from audit_trail.mysql_client import mark_consensus_discord_sent as _mysql_mark_sent
    _HAS_MYSQL_AUDIT = True
except ImportError:
    _HAS_MYSQL_AUDIT = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
WEBHOOK_PORTFOLIO = os.environ.get("DISCORD_WEBHOOK_PORTFOLIO", "")
WEBHOOK_SANDBOX = os.environ.get("DISCORD_WEBHOOK_SANDBOX", "")
WEBHOOK_DNA_MASTER = os.environ.get("DISCORD_WEBHOOK_DNA_MASTER", "")
USERNAME = "Cross-System Consensus"

MONITOR_URL = "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/"
ALPHA_DASHBOARD_URL = "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/"
UPDATES_URL = "https://findtorontoevents.ca/updates/"

# Embed colors
COLOR_GREEN = 0x22C55E
COLOR_RED = 0xEF4444
COLOR_YELLOW = 0xEAB308
COLOR_PURPLE = 0x8B5CF6
COLOR_BLUE = 0x3B82F6
COLOR_ORANGE = 0xF97316
COLOR_GRAY = 0x6B7280
COLOR_GOLD = 0xFFD700

# ── Quality Gate Badges ──
_GATE_EMOJI = {
    "ELITE": "\U0001f451",       # crown
    "PROVEN": "\u2705",          # check mark
    "MARGINAL": "\U0001f7e1",    # yellow circle
    "TESTING": "\U0001f9ea",     # test tube
    "COLLECTING": "\u23f3",      # hourglass
}


def _quality_badge(status, checks_passed: int) -> str:
    """Return a compact badge string for Discord embed fields."""
    if status is None:
        return "\u2753 UNRATED (0/8)"
    emoji = _GATE_EMOJI.get(status, "\u2753")
    return f"{emoji} {status} ({checks_passed}/8)"


# Rate limiting: seconds between alerts for the same symbol
RATE_LIMIT_SECONDS = 30 * 60  # 30 minutes
# STRONG tier alerts bypass rate limiting
RATE_LIMIT_BYPASS_TIERS = {"STRONG BUY", "STRONG SELL"}

# Max embeds per Discord message (Discord API limit is 10)
MAX_EMBEDS_PER_MESSAGE = 10

# EST timezone offset (UTC-5)
EST = timezone(timedelta(hours=-5))

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Strategy performance loader
# ---------------------------------------------------------------------------

def _load_strategy_stats(strategy_name: str) -> Optional[dict]:
    """Load per-strategy historical performance from existing tracking files."""
    if not strategy_name:
        return None

    # Try alpha_engine strategy_performance.json first
    alpha_perf = REPO_ROOT / "alpha_engine" / "data" / "strategy_performance.json"
    if alpha_perf.exists():
        try:
            data = json.loads(alpha_perf.read_text())
            if strategy_name in data:
                s = data[strategy_name]
                closed = s.get("closed_picks", s.get("total_trades", 0))
                if closed >= 3:
                    return {
                        "win_rate": s.get("win_rate"),
                        "closed": closed,
                        "profit_factor": s.get("profit_factor"),
                        "sharpe": s.get("sharpe"),
                        "pnl": s.get("total_pnl_dollar", s.get("total_pnl_pct")),
                    }
        except Exception:
            pass

    # Try component_perf_daily.json
    comp = REPO_ROOT / "data" / "component_perf_daily.json"
    if comp.exists():
        try:
            data = json.loads(comp.read_text())
            components = data.get("components", data)
            if isinstance(components, list):
                for c in components:
                    if c.get("component", c.get("strategy", "")) == strategy_name:
                        closed = c.get("total_trades", 0)
                        if closed >= 3:
                            return {
                                "win_rate": c.get("win_rate"),
                                "closed": closed,
                                "profit_factor": c.get("profit_factor"),
                                "sharpe": c.get("sharpe_annualized", c.get("sharpe")),
                                "pnl": c.get("total_pnl_usdt"),
                            }
            elif isinstance(components, dict) and strategy_name in components:
                c = components[strategy_name]
                closed = c.get("total_trades", 0)
                if closed >= 3:
                    return {
                        "win_rate": c.get("win_rate"),
                        "closed": closed,
                        "profit_factor": c.get("profit_factor"),
                        "sharpe": c.get("sharpe_annualized"),
                        "pnl": c.get("total_pnl_usdt"),
                    }
        except Exception:
            pass

    return None


# Pick classification for routing
try:
    from cross_aggregation.pick_classifier import classify_pick, get_system_trust_badge, get_system_stats_line, get_all_system_stats
    _HAS_CLASSIFIER = True
except ImportError:
    _HAS_CLASSIFIER = False

# DNA Master Picks tracker
try:
    from cross_aggregation.dna_master_tracker import register_elite_pick, send_master_pick_alert, check_exits, send_exit_alert
    _HAS_DNA_TRACKER = True
except ImportError:
    _HAS_DNA_TRACKER = False

# Footer appended to every embed
FOOTER_DISCLAIMER = "Not financial advice | Paper trade only"

# ---------------------------------------------------------------------------
# Signal Tier Classification
# ---------------------------------------------------------------------------


def _signal_tier(agreement_count: int, total_systems: int, avg_confidence: float) -> dict:
    """
    Classify signal strength into tiers.

    Returns dict with keys: tier, emoji, color, description

    STRONG BUY:  4+ systems LONG, avg conf >= 0.60
    BUY:         3+ systems LONG, avg conf >= 0.55
    NEUTRAL:     < 3 agreement or conflicting signals
    SELL:        3+ systems SHORT, avg conf >= 0.55
    STRONG SELL: 4+ systems SHORT, avg conf >= 0.60

    Note: direction is inferred from the pick, not from this function.
    This function classifies based on magnitude only. The caller wraps
    with direction context.
    """
    tiers = {
        "STRONG BUY": {
            "tier": "STRONG BUY",
            "emoji": "\U0001f7e2\U0001f525",  # green circle + fire
            "color": COLOR_GREEN,
            "description": "Very high conviction - multiple systems strongly agree",
        },
        "BUY": {
            "tier": "BUY",
            "emoji": "\U0001f7e2",  # green circle
            "color": COLOR_GREEN,
            "description": "High conviction - solid system agreement",
        },
        "NEUTRAL": {
            "tier": "NEUTRAL",
            "emoji": "\u26aa",  # white circle
            "color": COLOR_GRAY,
            "description": "Low conviction - insufficient agreement",
        },
        "SELL": {
            "tier": "SELL",
            "emoji": "\U0001f534",  # red circle
            "color": COLOR_RED,
            "description": "High conviction SHORT - solid system agreement",
        },
        "STRONG SELL": {
            "tier": "STRONG SELL",
            "emoji": "\U0001f534\U0001f525",  # red circle + fire
            "color": COLOR_RED,
            "description": "Very high conviction SHORT - multiple systems strongly agree",
        },
    }

    # Return tier dict based on thresholds
    if agreement_count >= 4 and avg_confidence >= 0.60:
        return tiers["STRONG BUY"]  # caller remaps to STRONG SELL if SHORT
    elif agreement_count >= 3 and avg_confidence >= 0.55:
        return tiers["BUY"]  # caller remaps to SELL if SHORT
    else:
        return tiers["NEUTRAL"]


def _pick_signal_tier(pick: dict) -> dict:
    """Determine signal tier for a specific pick, accounting for direction."""
    agreement = pick.get("agreement_count", 0)
    total = pick.get("total_systems", 0)
    confidence = pick.get("confidence", 0)
    direction = pick.get("direction", "LONG")

    tier_info = _signal_tier(agreement, total, confidence)

    # Remap to SHORT-side tiers
    if direction == "SHORT":
        remap = {
            "STRONG BUY": "STRONG SELL",
            "BUY": "SELL",
            "NEUTRAL": "NEUTRAL",
        }
        tier_name = remap.get(tier_info["tier"], tier_info["tier"])
        # Rebuild with correct color/emoji
        if tier_name == "STRONG SELL":
            tier_info = {
                "tier": "STRONG SELL",
                "emoji": "\U0001f534\U0001f525",
                "color": COLOR_RED,
                "description": "Very high conviction SHORT - multiple systems strongly agree",
            }
        elif tier_name == "SELL":
            tier_info = {
                "tier": "SELL",
                "emoji": "\U0001f534",
                "color": COLOR_RED,
                "description": "High conviction SHORT - solid system agreement",
            }

    return tier_info


# ---------------------------------------------------------------------------
# Visual Helpers
# ---------------------------------------------------------------------------


def _progress_bar(value: float, max_value: float = 1.0, length: int = 10) -> str:
    """
    Create a visual progress bar.
    value=0.82, max_value=1.0, length=10 -> [========--] 82%
    """
    if max_value <= 0:
        ratio = 0.0
    else:
        ratio = min(max(value / max_value, 0.0), 1.0)
    filled = round(ratio * length)
    empty = length - filled
    bar = "\u2588" * filled + "\u2591" * empty
    pct = ratio * 100
    return f"[{bar}] {pct:.0f}%"


def _agreement_bar(agreement: int, total: int) -> str:
    """Create agreement bar: ████████░░ 4/5 systems"""
    if total <= 0:
        return "0/0 systems"
    filled = min(agreement, total)
    empty = total - filled
    bar = "\u2588" * filled + "\u2591" * empty
    return f"{bar} {agreement}/{total} systems"


def _rr_ratio(pick: dict) -> float:
    """Calculate risk:reward ratio for a pick."""
    entry = float(pick.get("entry", 0) or 0)
    tp = float(pick.get("tp", 0) or 0)
    sl = float(pick.get("sl", 0) or 0)
    direction = pick.get("direction", "LONG")

    if not entry or not tp or not sl:
        return 0.0

    if direction == "LONG":
        reward = abs(tp - entry)
        risk = abs(entry - sl)
    else:
        reward = abs(entry - tp)
        risk = abs(sl - entry)

    return reward / risk if risk > 0 else 0.0


def _pnl_pct(entry: float, current: float, direction: str) -> float:
    """Calculate PnL percentage."""
    if not entry:
        return 0.0
    if direction == "LONG":
        return (current - entry) / entry * 100
    else:
        return (entry - current) / entry * 100


def _vol_position_suggestion(pick: dict) -> str:
    """
    Suggest position size based on volatility targeting.
    Uses a simplified ATR proxy: |TP - SL| as price range.
    Target risk = 1-2% of portfolio per trade.
    """
    entry = float(pick.get("entry", 0) or 0)
    sl = float(pick.get("sl", 0) or 0)

    if not entry or not sl:
        return "N/A (no SL set)"

    risk_per_unit = abs(entry - sl)
    risk_pct = (risk_per_unit / entry) * 100 if entry > 0 else 0

    if risk_pct <= 0:
        return "N/A"

    # Suggest keeping total risk at 1-2% of portfolio
    suggested_risk = min(2.0, max(0.5, 10.0 / risk_pct))
    suggested_risk = round(suggested_risk, 1)

    return f"Suggested risk: {suggested_risk}% at {risk_pct:.1f}% SL distance"


def _regime_context(fng: int) -> str:
    """Build regime context string from Fear & Greed index."""
    if fng <= 10:
        regime = "CAPITULATION"
        label = "EXTREME FEAR"
    elif fng <= 25:
        regime = "TRENDING_DOWN"
        label = "EXTREME FEAR"
    elif fng <= 40:
        regime = "RISK_OFF"
        label = "FEAR"
    elif fng <= 60:
        regime = "NEUTRAL"
        label = "NEUTRAL"
    elif fng <= 75:
        regime = "RISK_ON"
        label = "GREED"
    else:
        regime = "EUPHORIA"
        label = "EXTREME GREED"

    return f"Market: {label} (F&G: {fng}) | Regime: {regime}"


def _est_timestamp() -> str:
    """Current time formatted in EST."""
    now_est = datetime.now(EST)
    return now_est.strftime("%Y-%m-%d %I:%M %p EST")


def _est_iso() -> str:
    """Current time as ISO string for Discord embed timestamp."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Historical Edge (reads from signal tracker DB if available)
# ---------------------------------------------------------------------------


def _historical_edge(symbol: str, direction: str) -> Optional[str]:
    """
    Look up historical win rate for this symbol+direction combo.
    Reads from signal_tracker.db if available.
    Returns string like "This setup historically wins 67% (12/18 trades)" or None.
    """
    try:
        import sqlite3
        db_path = REPO_ROOT / "data" / "signal_tracker.db"
        if not db_path.exists():
            db_path = REPO_ROOT / "KIMI_RISEOFTHECLAW" / "data" / "signal_tracker.db"
        if not db_path.exists():
            return None

        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        # Try to query closed trades for this symbol
        cur.execute(
            "SELECT COUNT(*), SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) "
            "FROM signals WHERE symbol = ? AND direction = ? AND status = 'CLOSED'",
            (symbol, direction),
        )
        row = cur.fetchone()
        conn.close()

        if row and row[0] and row[0] >= 3:
            total, wins = row[0], row[1] or 0
            wr = (wins / total) * 100
            return f"This setup historically wins {wr:.0f}% ({wins}/{total} trades)"
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Core Helpers (preserved from original)
# ---------------------------------------------------------------------------


def _fmt_price(val) -> str:
    """Format price without scientific notation."""
    if val is None or val == 0:
        return "$0"
    val = float(val)
    if val >= 1000:
        return f"${val:,.2f}"
    elif val >= 1:
        return f"${val:.4f}"
    elif val >= 0.001:
        return f"${val:.6f}"
    else:
        return f"${val:.10f}"


def _truncate(text: str, max_len: int = 1024) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _post(embeds: list, webhook_url: str = ""):
    """Post embeds to Discord, batching if needed. Retries up to 3 times."""
    url = webhook_url or WEBHOOK_URL
    if not url:
        return

    # Discord allows max 10 embeds per message
    for i in range(0, len(embeds), MAX_EMBEDS_PER_MESSAGE):
        batch = embeds[i : i + MAX_EMBEDS_PER_MESSAGE]
        payload = {"username": USERNAME, "embeds": batch}
        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, timeout=15)
                if resp.status_code in (200, 204):
                    print(f"[Discord] Sent {len(batch)} embed(s) OK")
                    break
                elif resp.status_code == 429:
                    # Rate limited by Discord API -- back off
                    retry_after = resp.json().get("retry_after", 5)
                    print(f"[Discord] Rate limited, waiting {retry_after}s")
                    _time.sleep(retry_after)
                    continue
                else:
                    print(f"[Discord] Failed: {resp.status_code} {resp.text[:200]}")
                    if attempt < 2:
                        _time.sleep(2 * (attempt + 1))
                        continue
                    break
            except Exception as e:
                if attempt == 2:
                    print(f"[Discord] Error after 3 attempts: {e}")
                else:
                    print(f"[Discord] Attempt {attempt + 1} failed: {e}, retrying...")
                    _time.sleep(2 * (attempt + 1))


def _post_to_webhook(webhook_url: str, embeds: list):
    """Post embeds to a specific webhook URL."""
    _post(embeds, webhook_url=webhook_url)


# ---------------------------------------------------------------------------
# Dedup & Rate Limiting
# ---------------------------------------------------------------------------


def _load_sent_keys() -> dict:
    """Load dedup state: {pick_key: timestamp_iso}."""
    sent_path = REPO_ROOT / "data" / "discord_consensus_sent.json"
    if sent_path.exists():
        try:
            return json.loads(sent_path.read_text())
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def _save_sent_keys(sent: dict):
    """Save dedup state, pruning entries older than 24 hours."""
    sent_path = REPO_ROOT / "data" / "discord_consensus_sent.json"
    now = datetime.now(timezone.utc)
    pruned = {}
    for k, ts in sent.items():
        try:
            dt = datetime.fromisoformat(ts)
            if (now - dt).total_seconds() < 86400:
                pruned[k] = ts
        except (ValueError, TypeError):
            pass
    sent_path.parent.mkdir(parents=True, exist_ok=True)
    sent_path.write_text(json.dumps(pruned, indent=2))


def _consensus_pick_key(pick: dict) -> str:
    """Stable dedup key for a consensus pick."""
    sym = pick.get("symbol", "")
    direction = pick.get("direction", "")
    entry = round(float(pick.get("entry", 0)), 4)
    return f"{sym}__{direction}__{entry}"


def _rate_limit_key(symbol: str) -> str:
    """Rate limit key: per-symbol, not per-pick."""
    return f"rl__{symbol}"


def _load_rate_limits() -> dict:
    """Load rate limit state: {rl_key: epoch_timestamp}."""
    rl_path = REPO_ROOT / "data" / "discord_rate_limits.json"
    if rl_path.exists():
        try:
            return json.loads(rl_path.read_text())
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def _save_rate_limits(rl: dict):
    """Save rate limit state, pruning entries older than 2 hours."""
    rl_path = REPO_ROOT / "data" / "discord_rate_limits.json"
    now_epoch = _time.time()
    pruned = {k: v for k, v in rl.items() if now_epoch - v < 7200}
    rl_path.parent.mkdir(parents=True, exist_ok=True)
    rl_path.write_text(json.dumps(pruned, indent=2))


def _is_rate_limited(symbol: str, tier: str, rate_limits: dict) -> bool:
    """
    Check if a symbol is rate-limited.
    STRONG BUY/SELL bypass rate limits.
    """
    if tier in RATE_LIMIT_BYPASS_TIERS:
        return False

    key = _rate_limit_key(symbol)
    if key in rate_limits:
        elapsed = _time.time() - rate_limits[key]
        if elapsed < RATE_LIMIT_SECONDS:
            return True
    return False


def _mark_sent(symbol: str, rate_limits: dict):
    """Mark a symbol as recently sent for rate limiting."""
    rate_limits[_rate_limit_key(symbol)] = _time.time()


# ---------------------------------------------------------------------------
# Fear & Greed
# ---------------------------------------------------------------------------


def _fetch_fng() -> int:
    """Fetch Fear & Greed index with retry. Returns 50 on failure."""
    urls = [
        "https://api.alternative.me/fng/?limit=1",
        "https://api.alternative.me/fng/?limit=1&format=json",
    ]
    for attempt in range(3):
        for url in urls:
            try:
                r = requests.get(url, timeout=10)
                return int(r.json()["data"][0]["value"])
            except Exception:
                pass
        if attempt < 2:
            _time.sleep(2 * (attempt + 1))
    print("[FNG] Failed after 3 attempts, returning default 50")
    return 50


def _health_label(fng: int) -> tuple:
    """Return (label, emoji, color) based on F&G."""
    if fng <= 15:
        return "PANIC", "\U0001f6a8", COLOR_RED
    elif fng <= 25:
        return "WARNING", "\u26a0\ufe0f", COLOR_YELLOW
    elif fng <= 35:
        return "CAUTION", "\U0001f7e1", COLOR_YELLOW
    else:
        return "SAFE", "\u2705", COLOR_GREEN


# ---------------------------------------------------------------------------
# Reversal Warnings (preserved and enhanced)
# ---------------------------------------------------------------------------


def _reversal_warnings(pick: dict, fng: int) -> list:
    """Generate reversal warning conditions for a pick."""
    warnings = []
    direction = pick.get("direction", "LONG")
    symbol = pick.get("symbol", "")
    sl = pick.get("sl", 0)
    entry = pick.get("entry", 0)

    if direction == "LONG":
        warnings.append(
            f"\U0001f534 **Exit if** {symbol} closes below SL `{_fmt_price(sl)}`"
        )
        if fng <= 15:
            warnings.append(
                f"\u26a0\ufe0f **Watch:** F&G={fng} (Extreme Fear) "
                f"\u2014 bounce may fail if F&G drops to single digits"
            )
        warnings.append(
            f"\U0001f504 **Reversal signal:** 3+ systems flip to SHORT on {symbol}"
        )
        if entry:
            breakeven = entry * 0.995  # 0.5% buffer for fees
            warnings.append(
                f"\U0001f6e1\ufe0f **Trail stop** to breakeven "
                f"`{_fmt_price(breakeven)}` once +3% in profit"
            )
    else:
        warnings.append(
            f"\U0001f534 **Exit if** {symbol} closes above SL `{_fmt_price(sl)}`"
        )
        warnings.append(
            f"\U0001f504 **Reversal signal:** F&G rises above 25 (fear subsiding)"
        )
        warnings.append(
            f"\U0001f504 **Reversal signal:** 3+ systems flip to LONG on {symbol}"
        )

    return warnings


# ---------------------------------------------------------------------------
# Alert Functions
# ---------------------------------------------------------------------------


def send_consensus_alert(
    picks: list,
    fng: Optional[int] = None,
    previous_picks: Optional[list] = None,
):
    """
    Send consensus picks to Discord with enhanced embeds.

    Args:
        picks: List of consensus pick dicts from aggregator
        fng: Fear & Greed index (fetched if None)
        previous_picks: Previous consensus picks (for detecting changes)
    """
    if not WEBHOOK_URL:
        print("[Discord] No DISCORD_WEBHOOK_URL set, skipping notification")
        return

    if fng is None:
        fng = _fetch_fng()

    health_label, health_emoji, health_color = _health_label(fng)
    timestamp_est = _est_timestamp()
    iso_now = _est_iso()

    if not picks:
        embeds = [
            {
                "title": "\U0001f6ab Cross-System Consensus \u2014 No Picks",
                "description": (
                    f"**{timestamp_est}**\n"
                    f"{health_emoji} Market Health: **{health_label}** (F&G: {fng})\n"
                    f"\U0001f30d {_regime_context(fng)}\n\n"
                    "No symbol has >=3 systems agreeing on direction.\n"
                    f"\U0001f517 [Live Monitor]({MONITOR_URL})"
                ),
                "color": COLOR_PURPLE,
                "timestamp": iso_now,
                "footer": {
                    "text": f"Cross-System Consensus | Threshold: 3 systems | {FOOTER_DISCLAIMER}"
                },
            }
        ]
        _post(embeds)

        # Also send heartbeat to DNA master picks channel
        if WEBHOOK_DNA_MASTER:
            send_no_picks_heartbeat(
                WEBHOOK_DNA_MASTER,
                "DNA Master Picks",
                {
                    "symbols_scanned": 0,
                    "systems_checked": 0,
                    "filter_reason": "No symbol has >=3 systems agreeing on direction",
                    "active_positions": 0,
                },
            )
        return

    embeds = []

    # Header embed
    total_long = sum(1 for p in picks if p.get("direction") == "LONG")
    total_short = sum(1 for p in picks if p.get("direction") == "SHORT")

    # Classify strongest pick for header color
    strongest_tier = "NEUTRAL"
    for p in picks:
        tier = _pick_signal_tier(p)
        if "STRONG" in tier["tier"]:
            strongest_tier = tier["tier"]
            break
        if tier["tier"] in ("BUY", "SELL"):
            strongest_tier = tier["tier"]

    header_color = health_color
    if "STRONG" in strongest_tier:
        header_color = COLOR_GOLD

    # Direction performance from source system picks if available
    dir_stats = ""
    try:
        agg_path = REPO_ROOT / "data" / "aggregated_picks.json"
        if agg_path.exists():
            agg_raw = json.loads(agg_path.read_text())
            all_picks_list = agg_raw.get("all_picks", []) if isinstance(agg_raw, dict) else []
            closed_l = [p for p in all_picks_list if p.get("direction") == "LONG" and p.get("status") in ("tp_hit", "sl_hit", "closed")]
            closed_s = [p for p in all_picks_list if p.get("direction") == "SHORT" and p.get("status") in ("tp_hit", "sl_hit", "closed")]
            if closed_l or closed_s:
                parts = []
                if closed_l:
                    lw = sum(1 for p in closed_l if p.get("status") == "tp_hit" or float(p.get("pnl_pct", 0) or 0) > 0)
                    parts.append(f"LONG {lw}/{len(closed_l)} ({lw/len(closed_l)*100:.0f}%)")
                if closed_s:
                    sw = sum(1 for p in closed_s if p.get("status") == "tp_hit" or float(p.get("pnl_pct", 0) or 0) > 0)
                    parts.append(f"SHORT {sw}/{len(closed_s)} ({sw/len(closed_s)*100:.0f}%)")
                dir_stats = f"\n\U0001f4ca Direction WR: {' | '.join(parts)}"
    except Exception:
        pass

    header_desc = (
        f"**{timestamp_est}**\n"
        f"{health_emoji} {_regime_context(fng)}\n"
        f"\U0001f4ca **{len(picks)} consensus picks:** "
        f"{total_long} LONG, {total_short} SHORT{dir_stats}\n"
        f"\U0001f517 [Live Monitor]({MONITOR_URL}) | [Dashboard]({ALPHA_DASHBOARD_URL}) | [Updates]({UPDATES_URL})"
    )

    embeds.append(
        {
            "title": f"\u26a1 Cross-System Consensus \u2014 {len(picks)} Top Picks",
            "description": header_desc,
            "color": header_color,
            "timestamp": iso_now,
        }
    )

    # Individual pick embeds (max 9 to stay under 10 total with header)
    for pick in picks[:9]:
        symbol = pick.get("symbol", "?")
        direction = pick.get("direction", "?")
        confidence = pick.get("confidence", 0)
        entry = pick.get("entry", 0)
        tp = pick.get("tp", 0)
        sl = pick.get("sl", 0)
        agreement = pick.get("agreement_count", 0)
        total_sys = pick.get("total_systems", 0)
        sources = pick.get("source_systems", [])
        unique_sources = sorted(set(sources))

        # Signal tier
        tier_info = _pick_signal_tier(pick)
        rr = _rr_ratio(pick)

        # Reversal warnings
        warnings = _reversal_warnings(pick, fng)
        warnings_text = "\n".join(warnings) if warnings else "_No specific warnings_"

        # Position sizing suggestion
        pos_suggestion = _vol_position_suggestion(pick)

        # Historical edge
        edge_text = _historical_edge(symbol, direction)

        # Build fields
        fields = [
            {
                "name": "\U0001f3af Signal Tier",
                "value": f"**{tier_info['emoji']} {tier_info['tier']}**",
                "inline": True,
            },
            {
                "name": "\U0001f4b0 Entry",
                "value": f"`{_fmt_price(entry)}`",
                "inline": True,
            },
            {
                "name": "\u2195\ufe0f R:R",
                "value": f"`{rr:.1f}:1`" if rr else "`--`",
                "inline": True,
            },
            {
                "name": "\u2705 Take Profit",
                "value": f"`{_fmt_price(tp)}`" if tp else "`--`",
                "inline": True,
            },
            {
                "name": "\U0001f6d1 Stop Loss",
                "value": f"`{_fmt_price(sl)}`" if sl else "`--`",
                "inline": True,
            },
            {
                "name": "\U0001f4ca Confidence",
                "value": _progress_bar(confidence, 1.0, 10),
                "inline": True,
            },
            {
                "name": "\U0001f91d Agreement",
                "value": _agreement_bar(agreement, total_sys),
                "inline": False,
            },
            {
                "name": "\U0001f4e1 Sources",
                "value": ", ".join(f"`{s}`" for s in unique_sources),
                "inline": False,
            },
        ]

        # Per-system strategy stats (replaces basic strategy attribution)
        source_strats = pick.get("source_strategies", {})
        system_wrs = pick.get("system_rolling_wrs", {})
        if source_strats or unique_sources:
            stats_text = format_per_system_stats(
                unique_sources, source_strats, system_wrs, max_display=5
            )
            fields.append({
                "name": "\U0001f9ec Strategy \u00d7 System",
                "value": stats_text,
                "inline": False,
            })

        # Confidence breakdown (inline explanation)
        cb = pick.get("confidence_breakdown")
        if cb:
            breakdown_text = format_confidence_breakdown(cb)
            if breakdown_text:
                fields.append({
                    "name": "\U0001f50d Confidence Breakdown",
                    "value": breakdown_text,
                    "inline": False,
                })

        # Lead strategy track record
        lead_strategy = pick.get("strategy", "")
        if lead_strategy:
            stats = _load_strategy_stats(lead_strategy)
            if stats:
                wr = stats.get("win_rate")
                wr_str = f"{wr:.0%}" if wr is not None else "--"
                pf = stats.get("profit_factor")
                pf_str = f"{pf:.2f}" if pf else "--"
                sh = stats.get("sharpe")
                sh_str = f"{sh:.1f}" if sh else "--"
                pnl = stats.get("pnl")
                pnl_str = f"${pnl:,.0f}" if pnl is not None else "--"
                fields.append({
                    "name": f"\U0001f4ca {lead_strategy} ({stats['closed']} trades)",
                    "value": f"WR: **{wr_str}** | PF: {pf_str} | Sharpe: {sh_str} | PnL: {pnl_str}",
                    "inline": False,
                })

        # Add system trust badges (shows if each source is a WINNER/LOSER/UNDETERMINED)
        if _HAS_CLASSIFIER:
            badge_lines = []
            for src in unique_sources[:5]:
                badge_emoji, badge_text = get_system_trust_badge(src)
                stats_line = get_system_stats_line(src)
                badge_lines.append(f"{badge_emoji} `{src}`: {stats_line.split('|', 1)[-1].strip() if '|' in stats_line else badge_text}")
            if badge_lines:
                fields.append({
                    "name": "\U0001f3c5 System Trust",
                    "value": "\n".join(badge_lines),
                    "inline": False,
                })

            # Classify pick and add tier label
            pick_class = classify_pick(pick)
            class_emoji = {
                "ELITE": "\U0001f9ec\U0001f451",  # DNA + crown
                "PROVEN": "\u2705",
                "EXPERIMENTAL": "\u26a0\ufe0f",
            }.get(pick_class, "\u2754")
            fields.append({
                "name": "\U0001f4cb Classification",
                "value": f"{class_emoji} **{pick_class}**",
                "inline": True,
            })
        else:
            pick_class = "PROVEN"  # default if classifier not available

        fields.extend([
            {
                "name": "\U0001f4b5 Position Sizing",
                "value": pos_suggestion,
                "inline": False,
            },
        ])

        # Add quality gate badge if present
        gate_status = pick.get("gate_status")
        gate_checks = pick.get("gate_checks", 0)
        if gate_status:
            fields.append({
                "name": "Quality Gate",
                "value": _quality_badge(gate_status, gate_checks),
                "inline": True,
            })

        # Add historical edge if available
        if edge_text:
            fields.append(
                {
                    "name": "\U0001f4c8 Historical Edge",
                    "value": edge_text,
                    "inline": False,
                }
            )

        fields.append(
            {
                "name": "\u26a0\ufe0f Reversal Warnings",
                "value": _truncate(warnings_text),
                "inline": False,
            }
        )

        dir_arrow = "\u2197\ufe0f" if direction == "LONG" else "\u2198\ufe0f"

        # Asset class label
        asset_class = pick.get("asset_class", "")
        if not asset_class:
            sym_upper = symbol.upper().replace("-", "").replace("/", "")
            if any(sym_upper.endswith(sfx) for sfx in ("USDT", "BTC", "ETH", "BUSD", "USDC")):
                asset_class = "CRYPTO"
            elif any(sym_upper.startswith(p) for p in ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD")) and len(sym_upper) == 6:
                asset_class = "FOREX"
            else:
                asset_class = "EQUITY"
        ac_emoji = {"CRYPTO": "\U0001fa99", "FOREX": "\U0001f4b1", "EQUITY": "\U0001f4c8", "MEMECOIN": "\U0001f436", "PENNY_STOCK": "\U0001f4b5", "COMMODITY": "\U0001f48e"}.get(asset_class.upper(), "\U0001f4ca")
        ac_label = asset_class.upper()

        embed_obj = {
            "title": (
                f"{tier_info['emoji']} {symbol} \u2014 "
                f"{direction} {dir_arrow} [{ac_emoji} {ac_label}]"
            ),
            "color": tier_info["color"],
            "fields": fields,
            "footer": {
                "text": (
                    f"{timestamp_est} | {FOOTER_DISCLAIMER}"
                ),
            },
        }

        # Route ELITE picks to DNA Master Picks channel (in addition to main)
        if _HAS_CLASSIFIER and _HAS_DNA_TRACKER and pick_class == "ELITE":
            try:
                pick_id = register_elite_pick(pick)
                if pick_id:
                    send_master_pick_alert(pick)
                    print(f"  [DNA Master] Registered ELITE pick: {symbol} {direction} (ID: {pick_id})")
            except Exception as e:
                print(f"  [DNA Master] Error: {e}")

        # Route EXPERIMENTAL picks to sandbox, skip main channel
        if pick_class == "EXPERIMENTAL" and WEBHOOK_SANDBOX:
            embed_obj["footer"]["text"] = f"EXPERIMENTAL | {timestamp_est} | {FOOTER_DISCLAIMER}"
            _post_to_webhook(WEBHOOK_SANDBOX, [embed_obj])
        else:
            embeds.append(embed_obj)

    # Send main embeds to #notifications channel
    _post(embeds)

    # ── Audit: log Discord posts (SQLite + MySQL) ──
    for p in picks:
        try:
            if _HAS_AUDIT:
                _audit_event("DISCORD_POSTED", symbol=p.get("symbol"),
                             payload={"direction": p.get("direction"),
                                      "confidence": p.get("confidence"),
                                      "agreement": p.get("agreement_count")},
                             origin="discord_notify")
        except Exception:
            pass
        try:
            if _HAS_MYSQL_AUDIT:
                _channel = "sandbox" if p.get("classification") == "EXPERIMENTAL" else "consensus"
                _mysql_log_send(p, channel=_channel, event_type="PICK_POSTED",
                                webhook_name="DISCORD_WEBHOOK_URL")
                _mysql_mark_sent(p.get("symbol", ""), p.get("direction", "LONG"),
                                 channel=_channel)
        except Exception:
            pass

    # Check DNA master pick exits
    if _HAS_DNA_TRACKER:
        try:
            exits = check_exits()
            for ex in exits:
                send_exit_alert(ex)
                print(f"  [DNA Master] Exit: {ex['symbol']} → {ex['status']} ({ex['pnl_pct']:+.2f}%)")
        except Exception as e:
            print(f"  [DNA Master] Exit check error: {e}")


def send_tp_hit_alert(pick: dict, live_price: float, fng: int = 50):
    """Send celebration alert when a consensus pick hits TP."""
    if not WEBHOOK_URL:
        return

    symbol = pick.get("symbol", "?")
    direction = pick.get("direction", "?")
    entry = pick.get("entry", 0)
    tp = pick.get("tp", 0)
    agreement = pick.get("agreement_count", 0)
    total_sys = pick.get("total_systems", 0)
    sources = pick.get("source_systems", [])
    unique_sources = sorted(set(sources)) if sources else []

    pnl = _pnl_pct(entry, live_price, direction)
    timestamp_est = _est_timestamp()

    # Calculate hold time if issued_at is available
    hold_time_str = ""
    issued_at = pick.get("issued_at")
    if issued_at:
        try:
            issued_dt = datetime.fromisoformat(issued_at)
            hold_seconds = (datetime.now(timezone.utc) - issued_dt).total_seconds()
            hours = int(hold_seconds // 3600)
            mins = int((hold_seconds % 3600) // 60)
            hold_time_str = f"\nHold time: {hours}h {mins}m"
        except (ValueError, TypeError):
            pass

    fields = [
        {"name": "Entry", "value": f"`{_fmt_price(entry)}`", "inline": True},
        {"name": "TP Target", "value": f"`{_fmt_price(tp)}`", "inline": True},
        {"name": "Exit Price", "value": f"`{_fmt_price(live_price)}`", "inline": True},
        {"name": "PnL", "value": f"**+{pnl:.2f}%**", "inline": True},
        {
            "name": "Agreement",
            "value": f"{agreement}/{total_sys} systems",
            "inline": True,
        },
        {"name": "F&G at Entry", "value": f"{fng}", "inline": True},
    ]

    if unique_sources:
        fields.append(
            {
                "name": "Contributing Systems",
                "value": ", ".join(f"`{s}`" for s in unique_sources),
                "inline": False,
            }
        )

    # Strategy context: why picked, track record, dashboard link
    strategy = pick.get("strategy") or pick.get("strategy_name") or ""
    reason = pick.get("reason") or pick.get("reason_category") or ""
    if strategy:
        fields.append({"name": "Strategy", "value": f"`{strategy}`", "inline": True})
    if reason:
        fields.append({"name": "Why Picked", "value": reason[:200], "inline": False})
    if strategy:
        stats = _load_strategy_stats(strategy)
        if stats and stats.get("closed"):
            wr = (stats["win_rate"] or 0) * 100
            fields.append({
                "name": "Track Record",
                "value": f"{stats['closed']} trades | {wr:.0f}% WR | PF {stats.get('profit_factor', 0):.2f}",
                "inline": True,
            })
        fields.append({
            "name": "Dashboard",
            "value": f"[View Live]({ALPHA_DASHBOARD_URL})",
            "inline": True,
        })

    embeds = [
        {
            "title": f"\U0001f3c6 CONSENSUS TP HIT \u2014 {symbol} +{pnl:.2f}%",
            "description": (
                f"**{symbol} {direction}** hit take profit!\n"
                f"Entry: `{_fmt_price(entry)}` \u2192 "
                f"TP: `{_fmt_price(tp)}` \u2192 "
                f"Live: `{_fmt_price(live_price)}`\n"
                f"PnL: **+{pnl:.2f}%**{hold_time_str}"
            ),
            "color": COLOR_GOLD,
            "fields": fields,
            "timestamp": _est_iso(),
            "footer": {
                "text": f"{timestamp_est} | {FOOTER_DISCLAIMER}",
            },
        }
    ]

    _post(embeds)

    # ── Audit: log TP hit (SQLite + MySQL) ──
    if _HAS_AUDIT:
        try:
            _audit_event("TP_HIT", symbol=symbol,
                         payload={"direction": direction, "entry": entry,
                                  "tp": tp, "exit_price": live_price,
                                  "pnl_pct": pnl, "agreement": agreement},
                         origin="discord_notify")
        except Exception:
            pass
    if _HAS_MYSQL_AUDIT:
        try:
            _mysql_log_send(pick, channel="consensus", event_type="TP_HIT",
                            webhook_name="DISCORD_WEBHOOK_URL", pnl_pct=pnl)
        except Exception:
            pass


def send_sl_hit_alert(pick: dict, live_price: float, fng: int = 50):
    """
    Send alert when a consensus pick hits stop loss.

    Includes auto-generated lesson based on market conditions.
    """
    if not WEBHOOK_URL:
        return

    symbol = pick.get("symbol", "?")
    direction = pick.get("direction", "?")
    entry = float(pick.get("entry", 0) or 0)
    sl = float(pick.get("sl", 0) or 0)
    agreement = pick.get("agreement_count", 0)
    total_sys = pick.get("total_systems", 0)

    pnl = _pnl_pct(entry, live_price, direction)
    timestamp_est = _est_timestamp()

    # Auto-generate lesson based on conditions
    lesson = _generate_sl_lesson(pick, fng, pnl)

    # Calculate hold time if issued_at is available
    hold_time_str = ""
    issued_at = pick.get("issued_at")
    if issued_at:
        try:
            issued_dt = datetime.fromisoformat(issued_at)
            hold_seconds = (datetime.now(timezone.utc) - issued_dt).total_seconds()
            hours = int(hold_seconds // 3600)
            mins = int((hold_seconds % 3600) // 60)
            hold_time_str = f"Hold time: {hours}h {mins}m"
        except (ValueError, TypeError):
            pass

    fields = [
        {"name": "Entry", "value": f"`{_fmt_price(entry)}`", "inline": True},
        {"name": "SL Target", "value": f"`{_fmt_price(sl)}`", "inline": True},
        {"name": "Exit Price", "value": f"`{_fmt_price(live_price)}`", "inline": True},
        {"name": "PnL", "value": f"**{pnl:+.2f}%**", "inline": True},
        {
            "name": "Agreement",
            "value": f"{agreement}/{total_sys} systems",
            "inline": True,
        },
        {"name": "F&G", "value": f"{fng}", "inline": True},
    ]

    if hold_time_str:
        fields.append(
            {"name": "Duration", "value": hold_time_str, "inline": False}
        )

    fields.append(
        {
            "name": "\U0001f4d6 Lesson",
            "value": lesson,
            "inline": False,
        }
    )

    # Strategy context: why picked, track record, dashboard link
    strategy = pick.get("strategy") or pick.get("strategy_name") or ""
    reason = pick.get("reason") or pick.get("reason_category") or ""
    if strategy:
        fields.append({"name": "Strategy", "value": f"`{strategy}`", "inline": True})
    if reason:
        fields.append({"name": "Why Picked", "value": reason[:200], "inline": False})
    if strategy:
        stats = _load_strategy_stats(strategy)
        if stats and stats.get("closed"):
            wr = (stats["win_rate"] or 0) * 100
            fields.append({
                "name": "Track Record",
                "value": f"{stats['closed']} trades | {wr:.0f}% WR | PF {stats.get('profit_factor', 0):.2f}",
                "inline": True,
            })
        fields.append({
            "name": "Dashboard",
            "value": f"[View Live]({ALPHA_DASHBOARD_URL})",
            "inline": True,
        })

    embeds = [
        {
            "title": f"\U0001f534 CONSENSUS SL HIT \u2014 {symbol} {pnl:+.1f}%",
            "description": (
                f"Entry: `{_fmt_price(entry)}` \u2192 "
                f"SL: `{_fmt_price(sl)}` \u2192 "
                f"Live: `{_fmt_price(live_price)}`\n"
                f"PnL: **{pnl:+.2f}%**"
            ),
            "color": COLOR_RED,
            "fields": fields,
            "timestamp": _est_iso(),
            "footer": {
                "text": f"{timestamp_est} | {FOOTER_DISCLAIMER}",
            },
        }
    ]

    _post(embeds)

    # ── Audit: log SL hit (SQLite + MySQL) ──
    if _HAS_AUDIT:
        try:
            _audit_event("SL_HIT", symbol=symbol,
                         payload={"direction": direction, "entry": entry,
                                  "sl": sl, "exit_price": live_price,
                                  "pnl_pct": pnl, "agreement": agreement,
                                  "lesson": lesson},
                         origin="discord_notify")
        except Exception:
            pass
    if _HAS_MYSQL_AUDIT:
        try:
            _mysql_log_send(pick, channel="consensus", event_type="SL_HIT",
                            webhook_name="DISCORD_WEBHOOK_URL", pnl_pct=pnl)
        except Exception:
            pass


def _generate_sl_lesson(pick: dict, fng: int, pnl: float) -> str:
    """Auto-generate a lesson based on market conditions when SL is hit."""
    direction = pick.get("direction", "LONG")
    agreement = pick.get("agreement_count", 0)
    confidence = pick.get("confidence", 0)

    lessons = []

    # Low agreement lesson
    if agreement <= 3:
        lessons.append(
            "Low system agreement (3 or fewer) -- "
            "consider requiring 4+ systems for entries."
        )

    # Fear/Greed context
    if direction == "LONG" and fng <= 20:
        lessons.append(
            f"Entered LONG during extreme fear (F&G: {fng}). "
            "Counter-trend trades in fear need wider stops or smaller size."
        )
    elif direction == "SHORT" and fng >= 70:
        lessons.append(
            f"Entered SHORT during greed (F&G: {fng}). "
            "Shorting euphoria requires precise timing."
        )

    # Low confidence
    if confidence < 0.55:
        lessons.append(
            f"Confidence was only {confidence:.0%}. "
            "Consider a minimum 55% confidence threshold."
        )

    # Quick SL hit
    if abs(pnl) > 5:
        lessons.append(
            f"Large loss ({pnl:+.1f}%). Gap risk or volatility spike. "
            "Consider ATR-based position sizing to cap dollar risk."
        )

    if not lessons:
        lessons.append(
            "Normal SL hit within expected parameters. "
            "Risk was managed correctly -- losses are part of the edge."
        )

    return "\n".join(f"- {l}" for l in lessons)


def send_position_update(pick: dict, live_price: float, fng: int = 50):
    """
    Send periodic position update for an active pick.

    Shows current PnL, trailing stop level, and hold time.
    """
    if not WEBHOOK_URL:
        return

    symbol = pick.get("symbol", "?")
    direction = pick.get("direction", "?")
    entry = float(pick.get("entry", 0) or 0)
    tp = float(pick.get("tp", 0) or 0)
    sl = float(pick.get("sl", 0) or 0)

    pnl = _pnl_pct(entry, live_price, direction)
    timestamp_est = _est_timestamp()

    # Determine color based on PnL
    if pnl >= 2.0:
        color = COLOR_GREEN
    elif pnl >= 0:
        color = COLOR_BLUE
    elif pnl >= -1.0:
        color = COLOR_YELLOW
    else:
        color = COLOR_ORANGE

    # Trailing stop calculation
    trailing_stop_text = "N/A"
    if entry and sl:
        if pnl >= 3.0:
            # Move to breakeven + buffer
            if direction == "LONG":
                trailing = entry * 1.005
            else:
                trailing = entry * 0.995
            trailing_stop_text = (
                f"Moved to: `{_fmt_price(trailing)}` (breakeven + buffer)"
            )
        elif pnl >= 1.5:
            # Tighten stop
            if direction == "LONG":
                trailing = entry * 0.998
            else:
                trailing = entry * 1.002
            trailing_stop_text = (
                f"Tightened to: `{_fmt_price(trailing)}` (near breakeven)"
            )
        else:
            trailing_stop_text = f"Original: `{_fmt_price(sl)}`"

    # Hold time
    hold_time_str = "N/A"
    issued_at = pick.get("issued_at")
    if issued_at:
        try:
            issued_dt = datetime.fromisoformat(issued_at)
            hold_seconds = (datetime.now(timezone.utc) - issued_dt).total_seconds()
            hours = int(hold_seconds // 3600)
            mins = int((hold_seconds % 3600) // 60)
            max_hours = 24
            hold_time_str = f"{hours}h {mins}m / {max_hours}h max"
        except (ValueError, TypeError):
            pass

    # Progress toward TP
    tp_progress = ""
    if entry and tp and live_price:
        if direction == "LONG":
            total_move = tp - entry
            current_move = live_price - entry
        else:
            total_move = entry - tp
            current_move = entry - live_price
        if total_move > 0:
            pct_to_tp = max(0.0, min(current_move / total_move, 1.0))
            tp_progress = _progress_bar(pct_to_tp, 1.0, 10)

    fields = [
        {"name": "Entry", "value": f"`{_fmt_price(entry)}`", "inline": True},
        {
            "name": "Current",
            "value": f"`{_fmt_price(live_price)}`",
            "inline": True,
        },
        {"name": "PnL", "value": f"**{pnl:+.2f}%**", "inline": True},
        {
            "name": "\U0001f6e1\ufe0f Trailing Stop",
            "value": trailing_stop_text,
            "inline": False,
        },
        {
            "name": "\u23f1\ufe0f Hold Time",
            "value": hold_time_str,
            "inline": True,
        },
    ]

    if tp_progress:
        fields.append(
            {
                "name": "\U0001f3af Progress to TP",
                "value": tp_progress,
                "inline": True,
            }
        )

    dir_emoji = "\U0001f7e2" if direction == "LONG" else "\U0001f534"

    embeds = [
        {
            "title": (
                f"\U0001f4ca POSITION UPDATE \u2014 "
                f"{symbol} {dir_emoji} {pnl:+.2f}%"
            ),
            "description": (
                f"Entry: `{_fmt_price(entry)}` | "
                f"Current: `{_fmt_price(live_price)}` | "
                f"PnL: **{pnl:+.2f}%**"
            ),
            "color": color,
            "fields": fields,
            "timestamp": _est_iso(),
            "footer": {
                "text": f"{timestamp_est} | {FOOTER_DISCLAIMER}",
            },
        }
    ]

    _post(embeds)

    # Audit trail logging
    if _HAS_MYSQL_AUDIT:
        try:
            _mysql_log_send(
                pick, channel="consensus", event_type="POSITION_UPDATE",
                pnl_pct=pnl,
                extra_payload={"live_price": live_price, "hold_time": hold_time_str},
            )
        except Exception:
            pass


def send_portfolio_summary(metrics: dict):
    """
    Send daily portfolio health summary.

    Args:
        metrics: Dict with keys:
            - sharpe: float (current portfolio Sharpe)
            - sharpe_30d: float (rolling 30-day Sharpe)
            - max_drawdown: float (max drawdown %)
            - win_rate: float (win rate 0-1)
            - active_picks: int
            - long_count: int
            - short_count: int
            - top_system: str (name)
            - top_system_sharpe: float
            - worst_system: str (name)
            - worst_system_sharpe: float
            - worst_system_status: str (e.g., "disabled")
            - total_trades: int (optional)
            - total_pnl: float (optional, cumulative PnL %)
    """
    url = WEBHOOK_PORTFOLIO or WEBHOOK_URL
    if not url:
        print("[Discord] No webhook URL for portfolio summary, skipping")
        return

    timestamp_est = _est_timestamp()

    sharpe = metrics.get("sharpe", 0)
    sharpe_30d = metrics.get("sharpe_30d", 0)
    max_dd = metrics.get("max_drawdown", 0)
    win_rate = metrics.get("win_rate", 0)
    active = metrics.get("active_picks", 0)
    longs = metrics.get("long_count", 0)
    shorts = metrics.get("short_count", 0)
    top_sys = metrics.get("top_system", "N/A")
    top_sharpe = metrics.get("top_system_sharpe", 0)
    worst_sys = metrics.get("worst_system", "N/A")
    worst_sharpe = metrics.get("worst_system_sharpe", 0)
    worst_status = metrics.get("worst_system_status", "active")
    total_trades = metrics.get("total_trades", 0)
    total_pnl = metrics.get("total_pnl", 0)

    # Color based on Sharpe
    if sharpe >= 2.0:
        color = COLOR_GREEN
    elif sharpe >= 1.0:
        color = COLOR_BLUE
    elif sharpe >= 0:
        color = COLOR_YELLOW
    else:
        color = COLOR_RED

    # Sharpe visual
    sharpe_bar = _progress_bar(min(sharpe, 3.0), 3.0, 10)
    wr_bar = _progress_bar(win_rate, 1.0, 10)

    fields = [
        {
            "name": "\U0001f4c8 Portfolio Sharpe",
            "value": f"`{sharpe:.2f}` {sharpe_bar}",
            "inline": True,
        },
        {
            "name": "\U0001f4c5 Rolling 30d Sharpe",
            "value": f"`{sharpe_30d:.2f}`",
            "inline": True,
        },
        {
            "name": "\U0001f4c9 Max Drawdown",
            "value": f"`{max_dd:+.1f}%`",
            "inline": True,
        },
        {
            "name": "\U0001f3af Win Rate",
            "value": f"{wr_bar}",
            "inline": True,
        },
        {
            "name": "\U0001f4ca Active Picks",
            "value": f"**{active}** ({longs} LONG, {shorts} SHORT)",
            "inline": True,
        },
    ]

    if total_trades:
        fields.append(
            {
                "name": "\U0001f522 Total Trades",
                "value": f"`{total_trades}`",
                "inline": True,
            }
        )

    if total_pnl:
        pnl_emoji = "\U0001f7e2" if total_pnl >= 0 else "\U0001f534"
        fields.append(
            {
                "name": f"{pnl_emoji} Cumulative PnL",
                "value": f"**{total_pnl:+.2f}%**",
                "inline": True,
            }
        )

    fields.extend(
        [
            {
                "name": "\U0001f947 Top System",
                "value": f"`{top_sys}` (Sharpe: {top_sharpe:.2f})",
                "inline": False,
            },
            {
                "name": "\u26a0\ufe0f Worst System",
                "value": (
                    f"`{worst_sys}` ({worst_status}, Sharpe: {worst_sharpe:.2f})"
                ),
                "inline": False,
            },
        ]
    )

    embeds = [
        {
            "title": "\U0001f4c8 DAILY PORTFOLIO SUMMARY",
            "description": (
                f"**{timestamp_est}**\n"
                f"\U0001f517 [Live Monitor]({MONITOR_URL}) | "
                f"[Updates]({UPDATES_URL})"
            ),
            "color": color,
            "fields": fields,
            "timestamp": _est_iso(),
            "footer": {
                "text": f"Cross-System Portfolio | {FOOTER_DISCLAIMER}",
            },
        }
    ]

    _post(embeds, webhook_url=url)

    # Audit trail logging
    if _HAS_MYSQL_AUDIT:
        try:
            _mysql_log_send(
                {"symbol": "PORTFOLIO", "direction": "", "entry_price": 0},
                channel="portfolio", event_type="PORTFOLIO_SUMMARY",
                webhook_name="DISCORD_WEBHOOK_PORTFOLIO",
                extra_payload=metrics,
            )
        except Exception:
            pass


def send_reversal_alert(
    symbol: str,
    old_direction: str,
    new_direction: str,
    reason: str,
    fng: int = 50,
):
    """Send alert when consensus flips direction on a symbol."""
    if not WEBHOOK_URL:
        return

    timestamp_est = _est_timestamp()
    embeds = [
        {
            "title": (
                f"\U0001f504 CONSENSUS REVERSAL \u2014 "
                f"{symbol} {old_direction} \u2192 {new_direction}"
            ),
            "description": (
                f"**WARNING:** The cross-system consensus has flipped on {symbol}.\n\n"
                f"Previous: **{old_direction}**\n"
                f"Now: **{new_direction}**\n"
                f"Reason: {reason}\n"
                f"F&G: {fng}\n"
                f"\U0001f30d {_regime_context(fng)}\n\n"
                f"\u26a0\ufe0f If you followed the previous {old_direction} pick, "
                f"review your position.\n"
                f"\U0001f517 [Live Monitor]({MONITOR_URL})"
            ),
            "color": COLOR_YELLOW,
            "timestamp": _est_iso(),
            "footer": {
                "text": (
                    f"{timestamp_est} | Reversal Warning | {FOOTER_DISCLAIMER}"
                ),
            },
        }
    ]

    _post(embeds)

    # Audit trail logging
    if _HAS_MYSQL_AUDIT:
        try:
            _mysql_log_send(
                {"symbol": symbol, "direction": new_direction, "entry_price": 0},
                channel="consensus", event_type="REVERSAL",
                extra_payload={"old_direction": old_direction, "reason": reason, "fng": fng},
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Batch Sending (multiple picks in fewer messages)
# ---------------------------------------------------------------------------


def send_batch_alerts(
    picks: list,
    fng: Optional[int] = None,
    previous_picks: Optional[list] = None,
):
    """
    Send consensus picks in batched messages, respecting rate limits.
    Prioritizes STRONG tier alerts (bypass rate limits).

    This is the recommended entry point for automated pipelines.
    Falls back to send_consensus_alert behavior.
    """
    if not WEBHOOK_URL:
        print("[Discord] No DISCORD_WEBHOOK_URL set, skipping notification")
        return

    if fng is None:
        fng = _fetch_fng()

    if not picks:
        send_consensus_alert([], fng, previous_picks)
        return

    rate_limits = _load_rate_limits()

    # Separate into priority (STRONG) and normal
    priority_picks = []
    normal_picks = []

    for pick in picks:
        tier = _pick_signal_tier(pick)
        symbol = pick.get("symbol", "")
        if _is_rate_limited(symbol, tier["tier"], rate_limits):
            print(
                f"  [RATE-LIMIT] Skipping {symbol} -- "
                f"sent within {RATE_LIMIT_SECONDS // 60} min"
            )
            continue
        if tier["tier"] in RATE_LIMIT_BYPASS_TIERS:
            priority_picks.append(pick)
        else:
            normal_picks.append(pick)

    # Send priority picks first (always go through)
    all_to_send = priority_picks + normal_picks

    if not all_to_send:
        print("[Discord] All picks rate-limited, skipping")
        _save_rate_limits(rate_limits)
        return

    # Mark all as sent for rate limiting
    for pick in all_to_send:
        _mark_sent(pick.get("symbol", ""), rate_limits)

    # Use the standard consensus alert (which handles batching internally)
    send_consensus_alert(all_to_send, fng, previous_picks)
    _save_rate_limits(rate_limits)


# ---------------------------------------------------------------------------
# Main (standalone execution)
# ---------------------------------------------------------------------------


def main():
    """Run standalone: load aggregated picks and send to Discord."""
    agg_path = REPO_ROOT / "data" / "aggregated_picks.json"
    if not agg_path.exists():
        print(f"No aggregated picks at {agg_path}")
        return

    raw = json.loads(agg_path.read_text())
    # Handle both formats: plain list or dict with regime wrapper
    if isinstance(raw, dict):
        picks = raw.get("consensus_picks", [])
    elif isinstance(raw, list):
        picks = raw
    else:
        picks = []
    fng = _fetch_fng()

    # -- Dedup: only send picks we haven't sent recently --
    sent_keys = _load_sent_keys()
    now = datetime.now(timezone.utc)
    new_picks = []
    for p in picks:
        key = _consensus_pick_key(p)
        if key in sent_keys:
            try:
                last_sent = datetime.fromisoformat(sent_keys[key])
                hours_ago = (now - last_sent).total_seconds() / 3600
                if hours_ago < 6:
                    print(f"  [DEDUP] Skipping {key} -- sent {hours_ago:.1f}h ago")
                    continue
            except (ValueError, TypeError):
                pass
        new_picks.append(p)
        sent_keys[key] = now.isoformat()

    if not new_picks:
        print(
            f"[Discord] All {len(picks)} picks already sent within 6h -- skipping"
        )
        _save_sent_keys(sent_keys)
        return

    # Check for previous picks to detect reversals
    prev_path = REPO_ROOT / "data" / "aggregated_picks_prev.json"
    previous = json.loads(prev_path.read_text()) if prev_path.exists() else []

    # Detect reversals
    prev_by_sym = {p["symbol"]: p["direction"] for p in previous}
    for pick in picks:
        sym = pick["symbol"]
        if sym in prev_by_sym and prev_by_sym[sym] != pick["direction"]:
            send_reversal_alert(
                sym,
                prev_by_sym[sym],
                pick["direction"],
                f"Consensus flipped: was {prev_by_sym[sym]}, now {pick['direction']}",
                fng,
            )

    # Save current as previous for next run
    prev_path.write_text(json.dumps(picks, indent=2))

    # Send via batch alerts (handles rate limiting)
    send_batch_alerts(new_picks, fng, previous)
    _save_sent_keys(sent_keys)
    print(
        f"[Discord] Sent consensus alert: {len(new_picks)} new picks "
        f"(skipped {len(picks) - len(new_picks)} dupes), F&G={fng}"
    )


def send_combo_findings():
    """Post winning signal combinations from the combo backtester to Discord."""
    import sqlite3
    combo_db = REPO_ROOT / "signal_recorder" / "data" / "signal_log.db"
    if not combo_db.exists():
        print("[Discord] No signal_log.db yet -- combo findings skipped")
        return

    try:
        conn = sqlite3.connect(str(combo_db))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT combo_key, direction, total_trades, wins, win_rate,
                   avg_pnl_pct, sharpe, p_value
            FROM combo_results
            WHERE p_value < 0.05 AND win_rate > 0.55 AND total_trades >= 5
            ORDER BY p_value ASC LIMIT 10
        """).fetchall()

        # Also get signal recorder health stats
        total_signals = conn.execute("SELECT COUNT(*) FROM signal_log").fetchone()[0]
        total_outcomes = conn.execute("SELECT COUNT(*) FROM signal_outcomes").fetchone()[0]
        unique_systems = conn.execute("SELECT COUNT(DISTINCT system_id) FROM signal_log").fetchone()[0]
        conn.close()
    except Exception as e:
        print(f"[Discord] Combo DB error: {e}")
        return

    # Health embed
    health_embed = {
        "title": "Signal Recorder Health",
        "color": COLOR_GREEN if total_signals > 0 else COLOR_YELLOW,
        "fields": [
            {"name": "Total Signals", "value": f"{total_signals:,}", "inline": True},
            {"name": "Outcomes Tracked", "value": f"{total_outcomes:,}", "inline": True},
            {"name": "Systems Active", "value": str(unique_systems), "inline": True},
        ],
        "footer": {"text": f"Updated {_est_timestamp()}"},
        "timestamp": _est_iso(),
    }

    embeds = [health_embed]

    if rows:
        lines = []
        for r in rows:
            wr = r["win_rate"] * 100
            emoji = "" if wr >= 65 else "" if wr >= 55 else ""
            lines.append(
                f"{emoji} **{r['combo_key']}** {r['direction']}: "
                f"{wr:.0f}% WR ({r['wins']}/{r['total_trades']}), "
                f"Sharpe={r['sharpe']:.1f}, p={r['p_value']:.3f}"
            )
        combo_embed = {
            "title": "Winning Signal Combos (p<0.05)",
            "description": "\n".join(lines),
            "color": COLOR_PURPLE,
            "footer": {"text": "Combo Backtester | findtorontoevents.ca"},
            "timestamp": _est_iso(),
        }
        embeds.append(combo_embed)
    else:
        embeds.append({
            "title": "Combo Backtester",
            "description": "Accumulating data... First significant combos expected in ~7 days.",
            "color": COLOR_YELLOW,
            "timestamp": _est_iso(),
        })

    _post(embeds)
    print(f"[Discord] Combo findings posted: {len(rows)} winners, {total_signals} total signals")

    # Audit trail logging
    if _HAS_MYSQL_AUDIT:
        try:
            _mysql_log_send(
                {"symbol": "COMBO", "direction": "", "entry_price": 0},
                channel="consensus", event_type="COMBO_FINDINGS",
                extra_payload={"winners": len(rows), "total_signals": total_signals},
            )
        except Exception:
            pass


def send_forward_test_update():
    """Post forward-test tracker results to Discord."""
    fwd_path = REPO_ROOT / "signal_recorder" / "data" / "forward_test_results.json"
    if not fwd_path.exists():
        print("[Discord] No forward_test_results.json yet")
        return

    try:
        data = json.loads(fwd_path.read_text())
    except Exception as e:
        print(f"[Discord] Forward test read error: {e}")
        return

    portfolio = data.get("portfolio", {})
    total_trades = portfolio.get("total_trades", 0)
    total_pnl = portfolio.get("total_pnl", 0)
    open_count = portfolio.get("open_trades", 0)

    # System-level stats
    fields = []
    for sys_key in ("keltner_mean_rev", "connors_rsi2"):
        sys = data.get(sys_key, {})
        if not sys:
            continue
        label = sys.get("label", sys_key)
        fwd_trades = sys.get("forward_trades", 0)
        fwd_wr = sys.get("forward_wr", 0)
        fwd_pnl = sys.get("forward_total_pnl", 0)
        hist_wr = sys.get("historical_wr", 0)
        budget = sys.get("budget", 0)
        fwd_sharpe = sys.get("forward_sharpe", 0)
        hist_sharpe = sys.get("historical_sharpe", 0)

        wr_delta = (fwd_wr - hist_wr) * 100 if fwd_trades > 0 else 0
        wr_arrow = "\u2191" if wr_delta >= 0 else "\u2193"

        value = (
            f"Budget: **${budget}** | Trades: **{fwd_trades}**\n"
            f"WR: **{fwd_wr:.0%}** (hist: {hist_wr:.0%}) {wr_arrow}\n"
            f"PnL: **{fwd_pnl:+.2f}%** | Sharpe: {fwd_sharpe:.2f} (hist: {hist_sharpe:.2f})"
        )
        emoji = "\U0001f7e2" if fwd_pnl >= 0 else "\U0001f534"
        fields.append({
            "name": f"{emoji} {label}",
            "value": value,
            "inline": True,
        })

    pnl_color = COLOR_GREEN if total_pnl >= 0 else COLOR_RED

    embed = {
        "title": "\U0001f4b0 FORWARD TEST: $1,000 Allocation Tracker",
        "description": (
            f"**Keltner Mean Rev ($600) + Connors RSI-2 ($400)**\n"
            f"Tracking since Mar 2, 2026\n\n"
            f"Total Trades: **{total_trades}** | Open: **{open_count}** | "
            f"Portfolio PnL: **{total_pnl:+.2f}%**"
        ),
        "color": pnl_color,
        "fields": fields,
        "footer": {"text": f"Updated {_est_timestamp()} | {FOOTER_DISCLAIMER}"},
        "timestamp": _est_iso(),
    }

    _post([embed])
    print(f"[Discord] Forward test update: {total_trades} trades, {total_pnl:+.2f}% PnL")

    # Audit trail logging
    if _HAS_MYSQL_AUDIT:
        try:
            _mysql_log_send(
                {"symbol": "FORWARD_TEST", "direction": "", "entry_price": 0},
                channel="consensus", event_type="FORWARD_TEST_UPDATE",
                extra_payload={"total_trades": total_trades, "total_pnl": total_pnl, "open_count": open_count},
            )
        except Exception:
            pass


def send_job_failure(system_label: str, job_name: str, error_msg: str):
    """Notify Discord when a trading job (scan, backtest, forward-test) fails."""
    if not WEBHOOK_URL:
        return

    now = datetime.now(timezone.utc)
    error_msg = error_msg[:500] + ("..." if len(error_msg) > 500 else "")

    embeds = [
        {
            "title": f"\U0001f6a8 {system_label} \u2014 {job_name.upper()} FAILURE",
            "description": f"An error occurred while running **{job_name}**.\n\n`{error_msg}`",
            "color": COLOR_RED,
            "timestamp": now.isoformat(),
            "footer": {"text": "Automated failure alert | Cross-System Consensus"},
        }
    ]
    _post(embeds)

    # Audit trail logging
    if _HAS_MYSQL_AUDIT:
        try:
            _mysql_log_send(
                {"symbol": system_label, "direction": "", "entry_price": 0},
                channel="consensus", event_type="JOB_FAILURE",
                extra_payload={"job_name": job_name, "error_msg": error_msg},
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
    send_combo_findings()
    send_forward_test_update()
