# Discord Message Enhancement Design

**Date:** 2026-03-04
**Goal:** Make Discord pick messages transparent and informative — strategy stats on every pick, confidence explained, and heartbeat when scans find nothing.

---

## Problem Statement

1. **Strategy stats missing** — e.g., coinglass paper-trade shows `coinglass_leverage_squeeze LONG SOLUSDT` with only a confidence bar. No win/loss history for that strategy or symbol.
2. **Confidence is opaque** — "94% confidence" with no explanation. Users don't know what it means.
3. **Silent when no picks** — if scans complete but nothing qualifies, channels go silent. Users can't tell if the system is down or just waiting.

---

## Enhancement 1: Strategy-Specific Stats on Every Pick

### Changes

| File | What changes |
|------|-------------|
| `coinglass_strategies/discord_notify.py` | Always show track record (even "0 trades — tracking started"). Add symbol-specific history. |
| `cross_aggregation/discord_notify.py` | Show per-system strategy stats inline with strategy attribution, not just lead strategy. |
| `cross_aggregation/dna_master_tracker.py` | Show specific strategy name + individual WR alongside aggregate master stats. |

### Shared Helper: `utils/discord_format.py`

Extract common formatting into a shared module to avoid duplication:

```python
def format_strategy_stats(name: str, stats: dict) -> str:
    """Format strategy stats as a compact one-liner."""
    if not stats or stats.get("total", 0) == 0:
        return f"`{name}`: 0 trades — tracking started"
    return (f"`{name}`: {stats['wins']}W/{stats['losses']}L "
            f"({stats['win_rate']:.0f}% WR) | "
            f"PF: {stats.get('profit_factor', '--')} | "
            f"Avg: {stats.get('avg_pnl', 0):+.2f}%")

def format_symbol_history(symbol: str, direction: str, wins: int, losses: int) -> str:
    """Format symbol+direction history."""
    total = wins + losses
    if total == 0:
        return ""
    wr = wins / total * 100
    return f"{symbol} {direction}s: {wins}W/{losses}L ({wr:.0f}%)"
```

### Safeguards
- Truncate after top 5 systems with "+ X more" if needed (Discord 6000 char limit).
- Cache per-symbol stats in memory during scan cycle to avoid repeated DB queries.
- Index: ensure `(symbol, direction, status)` is indexed in signal tracker DB.

---

## Enhancement 2: Confidence Breakdown (Inline)

### Data Flow

Extend the pick dict in `cross_aggregation/aggregator.py` with a `confidence_breakdown` key:

```python
pick["confidence_breakdown"] = {
    "base": 72,         # raw model/strategy confidence
    "wr_boost": 5,      # from rolling win rate weight
    "sharpe_boost": 2,  # from Sharpe ratio weight
    "consensus": 8,     # multi-system agreement boost
    "playbook": 3,      # preferred symbol/pattern adjustment
    "final": 90         # final displayed confidence
}
```

### Display Format (human-readable, compact)

```
Base: 72% (model) → +8% consensus (4 agree) → +5% WR → +2% Sharpe → +3% playbook = 90%
```

Only show non-zero components. Keeps it to one line in the embed.

### Changes

| File | What changes |
|------|-------------|
| `cross_aggregation/aggregator.py` | Compute and attach `confidence_breakdown` dict to each consensus pick. |
| `cross_aggregation/discord_notify.py` | Render breakdown under confidence bar. |
| `cross_aggregation/dna_master_tracker.py` | Render breakdown in master pick embed. |
| `coinglass_strategies/discord_notify.py` | For coinglass picks, show simpler breakdown (base + strategy model). |

### Safeguards
- If breakdown dict is missing, fall back to showing just the confidence number (backward compatible).
- Keep raw formula details in logs, show human-readable version in Discord.

---

## Enhancement 3: "No Picks" Heartbeat on All Channels

### Shared Helper: `utils/discord_heartbeat.py`

Centralized no-picks notification with per-channel throttling:

```python
def send_no_picks_heartbeat(webhook_url: str, channel_name: str, scan_info: dict) -> bool:
    """Send 'scan complete, no picks' to a Discord channel with throttling."""
    # Throttle: max once per 30 min per channel (matches scan frequency)
    # scan_info keys: timestamp, symbols_scanned, systems_checked,
    #                 filter_reason, active_positions, next_scan_est
```

### Display Format

```
🔕 Scan Complete — No Picks This Cycle
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ 2026-03-04 10:30 AM EST
📊 Scanned: 45 symbols across 25 systems
🚫 Reason: 0/45 met consensus threshold (need 3+ systems)
📈 Active positions: 3 being tracked
⏭️ Next scan: ~10:45 AM EST
🔗 Live Monitor | Updates
```

### Changes

| File | What changes |
|------|-------------|
| `utils/discord_heartbeat.py` | NEW — shared heartbeat helper with throttling. |
| `coinglass_strategies/discord_notify.py` | Add `send_no_picks_heartbeat()` call. |
| `coinglass_strategies/__main__.py` | Wrap scan in try/finally, call heartbeat if 0 picks sent. |
| `cross_aggregation/discord_notify.py` | Already has no-picks for #notifications. Extend to also fire for master-picks and fresh-picks. |
| `cross_aggregation/dna_master_tracker.py` | Add heartbeat when no new ELITE picks qualify. |
| `cross_aggregation/freshpicks_notify.py` | Ensure `send_no_picks_status()` is always called. |
| `.github/workflows/cross-aggregator.yml` | Ensure no-picks path fires for all channels. |
| `.github/workflows/coinglass-scanner.yml` | No changes needed (heartbeat triggered from Python). |

### Throttling
- In-memory dict + file-based fallback (`data/heartbeat_last_sent.json`).
- Default: 30 min between no-picks messages per channel.
- Consecutive empty scans collapse: "No picks for 3 consecutive scans (45 min)".

### Safeguards
- `try/finally` wrapper ensures heartbeat fires even on exceptions.
- Log structured entry at INFO level for every heartbeat.
- Never suppress a heartbeat if the last message in the channel was >30 min ago.

---

## Files to Create/Modify

### New Files
1. `utils/__init__.py`
2. `utils/discord_format.py` — shared strategy stats + confidence formatting
3. `utils/discord_heartbeat.py` — shared no-picks heartbeat with throttling

### Modified Files
4. `cross_aggregation/aggregator.py` — attach `confidence_breakdown` to picks
5. `cross_aggregation/discord_notify.py` — per-strategy stats, confidence breakdown, heartbeat for all channels
6. `cross_aggregation/dna_master_tracker.py` — strategy attribution, confidence breakdown, heartbeat
7. `cross_aggregation/freshpicks_notify.py` — ensure no-picks always fires
8. `coinglass_strategies/discord_notify.py` — strategy stats always shown, confidence breakdown, heartbeat
9. `coinglass_strategies/__main__.py` — try/finally for heartbeat on no-picks

---

## Implementation Order

1. Create shared utils (format + heartbeat) — no dependencies
2. Update aggregator to compute confidence breakdown — feeds into all notifiers
3. Update coinglass discord_notify — self-contained, easiest to test
4. Update cross-aggregation discord_notify — most complex, largest file
5. Update dna_master_tracker — small changes
6. Update freshpicks_notify — ensure no-picks path
7. Test end-to-end with workflow dispatch
