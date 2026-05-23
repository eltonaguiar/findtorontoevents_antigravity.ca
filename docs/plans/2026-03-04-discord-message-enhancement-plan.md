# Discord Message Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make every Discord pick message show strategy-specific stats, explain confidence scores, and send heartbeat notifications when scans find no qualifying picks.

**Architecture:** Three enhancements across shared utils + 6 existing notification modules. Shared `utils/` package provides formatting helpers and heartbeat logic. Aggregator passes confidence breakdown dict through picks. Each notifier module gets a no-picks path with per-channel throttling.

**Tech Stack:** Python 3.11, requests (Discord webhooks), SQLite (ratio_store, signal_tracker), JSON data files.

---

### Task 1: Create shared utils package

**Files:**
- Create: `utils/__init__.py`
- Create: `utils/discord_format.py`
- Create: `utils/discord_heartbeat.py`

**Step 1: Create `utils/__init__.py`**

```python
"""Shared utilities for Discord notifications."""
```

**Step 2: Create `utils/discord_format.py`**

```python
"""Shared formatting helpers for Discord pick embeds."""


def format_strategy_stats(name: str, stats: dict) -> str:
    """Format strategy stats as a compact one-liner for Discord embeds.

    Args:
        name: Strategy name (e.g., 'coinglass_leverage_squeeze')
        stats: Dict with keys: total, wins, losses, win_rate, avg_pnl, profit_factor
    """
    if not stats or stats.get("total", 0) == 0:
        return f"`{name}`: 0 trades — tracking started"
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    wr = stats.get("win_rate", 0)
    pf = stats.get("profit_factor", "--")
    avg = stats.get("avg_pnl", 0)
    pf_str = f"{pf:.2f}" if isinstance(pf, (int, float)) and pf != float("inf") else str(pf)
    return (
        f"`{name}`: {wins}W/{losses}L "
        f"({wr:.0f}% WR) | PF: {pf_str} | Avg: {avg:+.2f}%"
    )


def format_symbol_history(symbol: str, direction: str, wins: int, losses: int) -> str:
    """Format symbol+direction history as a compact string."""
    total = wins + losses
    if total == 0:
        return ""
    wr = wins / total * 100
    return f"{symbol} {direction}s: {wins}W/{losses}L ({wr:.0f}%)"


def format_confidence_breakdown(breakdown: dict) -> str:
    """Format confidence breakdown as a human-readable one-liner.

    Args:
        breakdown: Dict with keys: base, wr_boost, sharpe_boost, consensus, playbook, final
    """
    if not breakdown:
        return ""
    parts = [f"Base: {breakdown.get('base', 0):.0f}%"]
    if breakdown.get("consensus", 0) > 0:
        parts.append(f"+{breakdown['consensus']:.0f}% consensus")
    if breakdown.get("wr_boost", 0) > 0:
        parts.append(f"+{breakdown['wr_boost']:.0f}% WR")
    if breakdown.get("sharpe_boost", 0) > 0:
        parts.append(f"+{breakdown['sharpe_boost']:.0f}% Sharpe")
    if breakdown.get("playbook", 0) > 0:
        parts.append(f"+{breakdown['playbook']:.0f}% playbook")
    final = breakdown.get("final", 0)
    return " → ".join(parts) + f" = **{final:.0f}%**"


def format_per_system_stats(source_systems: list, source_strategies: dict,
                            system_wrs: dict, max_display: int = 5) -> str:
    """Format per-system strategy stats for Discord embed.

    Args:
        source_systems: List of system names that agree on this pick
        source_strategies: Dict mapping system_name -> strategy_name
        system_wrs: Dict mapping system_name -> rolling win rate (0-100)
        max_display: Max systems to show before truncating
    """
    lines = []
    unique = sorted(set(source_systems))
    for sys in unique[:max_display]:
        strat = source_strategies.get(sys, "unknown")
        wr = system_wrs.get(sys)
        wr_str = f"{wr:.0f}% WR" if wr is not None else "new"
        lines.append(f"`{sys}` → {strat} ({wr_str})")
    if len(unique) > max_display:
        lines.append(f"+ {len(unique) - max_display} more")
    return "\n".join(lines) if lines else "N/A"
```

**Step 3: Create `utils/discord_heartbeat.py`**

```python
"""Shared no-picks heartbeat for all Discord channels."""
import json
import pathlib
import time
import requests
from datetime import datetime, timezone, timedelta

EST = timezone(timedelta(hours=-5))

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_COOLDOWN_FILE = _REPO_ROOT / "data" / "heartbeat_last_sent.json"
_DEFAULT_COOLDOWN_SEC = 30 * 60  # 30 minutes


def _load_cooldowns() -> dict:
    if _COOLDOWN_FILE.exists():
        try:
            return json.loads(_COOLDOWN_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def _save_cooldowns(data: dict):
    _COOLDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Prune entries older than 24h
    now = time.time()
    pruned = {k: v for k, v in data.items() if now - v < 86400}
    _COOLDOWN_FILE.write_text(json.dumps(pruned))


def send_no_picks_heartbeat(
    webhook_url: str,
    channel_name: str,
    scan_info: dict,
    cooldown_sec: int = _DEFAULT_COOLDOWN_SEC,
) -> bool:
    """Send a 'scan complete, no picks' embed to a Discord channel.

    Includes per-channel throttling to avoid spam.

    Args:
        webhook_url: Discord webhook URL
        channel_name: Identifier for throttle key (e.g., 'paper-trade')
        scan_info: Dict with keys:
            - symbols_scanned (int): how many symbols were checked
            - systems_checked (int, optional): how many systems contributed
            - filter_reason (str): why no picks qualified
            - active_positions (int, optional): currently tracked positions
            - scan_duration_sec (float, optional): how long the scan took
        cooldown_sec: Minimum seconds between heartbeats per channel

    Returns:
        True if sent, False if throttled or failed.
    """
    if not webhook_url:
        return False

    # Throttle check
    cooldowns = _load_cooldowns()
    last_sent = cooldowns.get(channel_name, 0)
    if time.time() - last_sent < cooldown_sec:
        return False

    now_est = datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST")
    symbols = scan_info.get("symbols_scanned", 0)
    systems = scan_info.get("systems_checked", 0)
    reason = scan_info.get("filter_reason", "No signals met quality criteria")
    active = scan_info.get("active_positions", 0)

    desc_lines = [
        f"**{now_est}**",
        f"Scanned: **{symbols}** symbols" + (f" across **{systems}** systems" if systems else ""),
        f"Result: {reason}",
    ]
    if active > 0:
        desc_lines.append(f"Active positions: **{active}** being tracked")
    desc_lines.append(
        "This is normal — the quality gate ensures only high-conviction signals are sent."
    )

    embed = {
        "title": f"Scan Complete — No New Picks",
        "description": "\n".join(desc_lines),
        "color": 0x6B7280,  # gray
        "footer": {"text": f"{channel_name} | {now_est} | System healthy"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        r = requests.post(
            webhook_url,
            json={"username": channel_name, "embeds": [embed]},
            timeout=15,
        )
        if r.status_code in (200, 204):
            cooldowns[channel_name] = time.time()
            _save_cooldowns(cooldowns)
            print(f"[Heartbeat] Sent no-picks to {channel_name}")
            return True
        elif r.status_code == 429:
            retry = r.json().get("retry_after", 5)
            time.sleep(retry)
            r2 = requests.post(
                webhook_url,
                json={"username": channel_name, "embeds": [embed]},
                timeout=15,
            )
            if r2.status_code in (200, 204):
                cooldowns[channel_name] = time.time()
                _save_cooldowns(cooldowns)
                return True
        print(f"[Heartbeat] Failed for {channel_name}: {r.status_code}")
    except Exception as e:
        print(f"[Heartbeat] Error for {channel_name}: {e}")
    return False
```

**Step 4: Commit**

```bash
git add utils/__init__.py utils/discord_format.py utils/discord_heartbeat.py
git commit -m "feat: shared Discord formatting and heartbeat utils"
```

---

### Task 2: Add confidence breakdown to aggregator

**Files:**
- Modify: `cross_aggregation/aggregator.py:589-641`

**Step 1: Compute and attach confidence_breakdown**

After line 616 (`score = adj_conf * ...`) and before `scored.append(...)`, compute per-system breakdown. Then after line 624 (`boosted_conf = min(raw_conf + CONFIDENCE_BOOST, 0.99)`), build the final breakdown dict and attach it to the unified pick.

In the scoring loop (around line 593-617), track the winning system's breakdown:

```python
# After line 616, before scored.append:
breakdown = {
    "base": round(raw_conf * 100, 1),
    "wr_boost": round((0.5 * wr_weight - 0.25) * 100, 1),  # net WR contribution
    "sharpe_boost": round((2.0 * sharpe_wt - 0.3) * 100, 1),  # net Sharpe contribution
    "playbook": round(playbook_adj * 100, 1),
    "consensus": 0,  # filled later
    "final": 0,  # filled later
}
scored.append((score, sys_name, pick, breakdown))
```

After line 624, add:

```python
# Get the winning system's breakdown
best_breakdown = scored[0][3] if len(scored[0]) > 3 else {}
best_breakdown["consensus"] = round(CONFIDENCE_BOOST * 100, 1)
best_breakdown["final"] = round(boosted_conf * 100, 1)
# Clamp negative boosts to 0 for display
for k in ("wr_boost", "sharpe_boost"):
    if best_breakdown.get(k, 0) < 0:
        best_breakdown[k] = 0
```

In the unified dict (line 626-641), add:

```python
"confidence_breakdown": best_breakdown,
```

**Step 2: Commit**

```bash
git add cross_aggregation/aggregator.py
git commit -m "feat: attach confidence_breakdown to consensus picks"
```

---

### Task 3: Enhance coinglass Discord notifications

**Files:**
- Modify: `coinglass_strategies/discord_notify.py`
- Modify: `coinglass_strategies/scanner.py`

**Step 1: Update `coinglass_strategies/discord_notify.py`**

Add import at top:

```python
import sys, pathlib
_repo_root = str(pathlib.Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
from utils.discord_format import format_strategy_stats, format_symbol_history
from utils.discord_heartbeat import send_no_picks_heartbeat
```

Modify `_get_strategy_track_record()` (line 44-58) to always return a string:

```python
def _get_strategy_track_record(strategy: str) -> str:
    """Build a short track record string for a strategy from closed positions."""
    try:
        from . import ratio_store
        stats = ratio_store.get_strategy_stats(strategy)
        if strategy not in stats or stats[strategy]["total"] == 0:
            return "0 trades — tracking started"
        return format_strategy_stats(strategy, stats[strategy])
    except Exception:
        return "0 trades — tracking started"
```

Modify `send_signal_alerts()` (line 61-98) to always show track record field and add symbol history:

In the fields list, the track_record append (line 87-89) becomes unconditional:

```python
# Always show track record (line 87-89 replacement)
track_record = _get_strategy_track_record(strategy)
fields.append({"name": "\U0001f4c8 Strategy Performance", "value": track_record, "inline": False})

# Add symbol-specific history
try:
    from . import ratio_store
    sym_stats = ratio_store.get_symbol_direction_stats(symbol, direction)
    if sym_stats and sym_stats.get("total", 0) > 0:
        sym_line = format_symbol_history(symbol, direction, sym_stats["wins"], sym_stats["losses"])
        if sym_line:
            fields.append({"name": "\U0001f4ca Symbol History", "value": sym_line, "inline": True})
except Exception:
    pass
```

Add new function `send_no_picks_alert()`:

```python
def send_no_picks_alert(symbols_scanned: int, active_positions: int = 0):
    """Send heartbeat when scan completes with no qualifying picks."""
    send_no_picks_heartbeat(
        webhook_url=WEBHOOK_URL,
        channel_name="Coinglass DNA Bundle",
        scan_info={
            "symbols_scanned": symbols_scanned,
            "filter_reason": "No signals met confidence/ratio thresholds this cycle",
            "active_positions": active_positions,
        },
    )
```

**Step 2: Add `get_symbol_direction_stats` to `ratio_store.py`**

Modify: `coinglass_strategies/ratio_store.py` — add after `get_strategy_stats`:

```python
def get_symbol_direction_stats(symbol: str, direction: str) -> Dict:
    """Return win/loss stats for a specific symbol+direction combo."""
    with _connect() as conn:
        row = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN p.pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN p.pnl_pct <= 0 THEN 1 ELSE 0 END) as losses
            FROM positions p
            JOIN signals s ON p.signal_id = s.signal_id
            WHERE p.status = 'CLOSED' AND s.symbol = ? AND s.direction = ?
        """, (symbol, direction)).fetchone()
        if not row or row["total"] == 0:
            return {"total": 0, "wins": 0, "losses": 0}
        return {"total": row["total"], "wins": row["wins"], "losses": row["losses"]}
```

**Step 3: Update scanner.py to send heartbeat on no picks**

Modify `cmd_scan()` in `coinglass_strategies/scanner.py` (line 16-22):

```python
def cmd_scan():
    logger.info("=== Coinglass DNA Scanner ===")
    picks = scan_all()
    logger.info("Generated %d picks", len(picks))
    if picks:
        send_signal_alerts(picks)
    else:
        from .discord_notify import send_no_picks_alert
        from .paper_portfolio import get_portfolio_summary
        try:
            summary = get_portfolio_summary()
            active = summary.get("open_positions", 0)
        except Exception:
            active = 0
        send_no_picks_alert(
            symbols_scanned=len(config.SYMBOLS),
            active_positions=active,
        )
    return picks
```

**Step 4: Commit**

```bash
git add coinglass_strategies/discord_notify.py coinglass_strategies/ratio_store.py coinglass_strategies/scanner.py
git commit -m "feat: coinglass — strategy stats always shown, symbol history, no-picks heartbeat"
```

---

### Task 4: Enhance cross-aggregation Discord notifications

**Files:**
- Modify: `cross_aggregation/discord_notify.py:790-870` (per-pick embed building)
- Modify: `cross_aggregation/discord_notify.py:683-702` (no-picks path)

**Step 1: Add imports**

At top of `cross_aggregation/discord_notify.py`, add:

```python
from utils.discord_format import format_confidence_breakdown, format_per_system_stats
from utils.discord_heartbeat import send_no_picks_heartbeat
```

**Step 2: Replace strategy attribution field with per-system stats**

Replace lines 833-847 (the "Strategy" field block) with:

```python
# Per-system strategy stats (replaces basic strategy attribution)
source_strats = pick.get("source_strategies", {})
system_wrs = pick.get("system_rolling_wrs", {})
if source_strats or unique_sources:
    stats_text = format_per_system_stats(
        unique_sources, source_strats, system_wrs, max_display=5
    )
    fields.append({
        "name": "\U0001f9ec Strategy × System",
        "value": stats_text,
        "inline": False,
    })
```

**Step 3: Add confidence breakdown under the confidence bar**

After the Confidence field (line 817-820), add:

```python
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
```

**Step 4: Enhance no-picks path to fire for all channels**

In `send_consensus_alert()`, after the existing no-picks embed is posted to #notifications (line 701), add heartbeats for other channels:

```python
# After _post(embeds) on line 701, before return:
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
```

**Step 5: Commit**

```bash
git add cross_aggregation/discord_notify.py
git commit -m "feat: consensus — per-system stats, confidence breakdown, all-channel heartbeat"
```

---

### Task 5: Enhance DNA Master Tracker

**Files:**
- Modify: `cross_aggregation/dna_master_tracker.py:274-335` (format_discord_embed)

**Step 1: Add imports**

```python
from utils.discord_format import format_confidence_breakdown
```

**Step 2: Add confidence breakdown and strategy name to master pick embed**

In `format_discord_embed()` (around line 313-325), after the existing fields list, add:

```python
# Strategy attribution
source_strats = pick.get("source_strategies", {})
if source_strats:
    strat_lines = [f"`{s}` → {st}" for s, st in list(source_strats.items())[:5]]
    fields.append({
        "name": "\U0001f9ec Contributing Strategies",
        "value": "\n".join(strat_lines),
        "inline": False,
    })

# Confidence breakdown
cb = pick.get("confidence_breakdown")
if cb:
    from utils.discord_format import format_confidence_breakdown
    breakdown_text = format_confidence_breakdown(cb)
    if breakdown_text:
        fields.append({
            "name": "\U0001f50d Confidence Breakdown",
            "value": breakdown_text,
            "inline": False,
        })
```

Also update the embed description (line 331) to include the lead strategy:

```python
lead_strat = pick.get("strategy", "multi-system consensus")
"description": f"**Elite consensus** — {agreement} systems agree with {conf_display} confidence.\n"
               f"Lead strategy: `{lead_strat}`\n"
               f"Forward-tracked with live TP/SL validation.",
```

**Step 3: Commit**

```bash
git add cross_aggregation/dna_master_tracker.py
git commit -m "feat: DNA master — strategy attribution and confidence breakdown"
```

---

### Task 6: Ensure freshpicks no-picks always fires

**Files:**
- Verify: `cross_aggregation/freshpicks_notify.py` (already has `send_no_picks_status`)
- Verify: `.github/workflows/cross-aggregator.yml` (already calls it)

**Step 1: Verify the existing workflow**

The workflow at lines 95-98 and 160-161 already calls `send_no_picks_status()` for both the "all_sent" and "quality_gate" cases. The freshpicks module already has the 60-min cooldown.

Add one more case: when there are zero consensus picks at all (no_signals):

In the workflow inline Python (around line 78-80), add:

```python
if not picks:
    send_no_picks_status('no_signals', total_scanned=0)
    exit(0)
```

**Step 2: Commit**

```bash
git add .github/workflows/cross-aggregator.yml
git commit -m "feat: freshpicks — send no-picks status when zero consensus picks"
```

---

### Task 7: End-to-end verification

**Step 1: Syntax check all modified files**

```bash
python -c "import py_compile; py_compile.compile('utils/discord_format.py', doraise=True)"
python -c "import py_compile; py_compile.compile('utils/discord_heartbeat.py', doraise=True)"
python -c "import py_compile; py_compile.compile('coinglass_strategies/discord_notify.py', doraise=True)"
python -c "import py_compile; py_compile.compile('cross_aggregation/discord_notify.py', doraise=True)"
python -c "import py_compile; py_compile.compile('cross_aggregation/dna_master_tracker.py', doraise=True)"
```

**Step 2: Verify imports resolve**

```bash
cd /path/to/repo
python -c "from utils.discord_format import format_strategy_stats, format_confidence_breakdown, format_per_system_stats, format_symbol_history; print('OK')"
python -c "from utils.discord_heartbeat import send_no_picks_heartbeat; print('OK')"
```

**Step 3: Final commit if needed**

```bash
git add -A
git commit -m "feat: Discord message enhancement — strategy stats, confidence breakdown, heartbeats"
```
