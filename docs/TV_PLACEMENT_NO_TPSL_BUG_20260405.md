# TV Paper Placement — NO TP/SL Root Cause & Fix (2026-04-05)

## Summary

`antigrav-dash-integrity` reported (cycle 7) that picks are being opened on all 5 TV
paper portfolios (SCALPER, TESTER, TRUSTOURSCORE, BROKIE, zerounderscore) **without
TP or SL** set, and that the violators keep recurring after manual patching. Same
symbols cycle: `JTOUSDT`, `SUIUSDT`, `OP`, `KITE`, `BTC`, `ADA`, `LINK`.

## Investigation

Searched the entire repo for any automated TV placement mechanism:

- **No batch Python script** loops across portfolios calling `place_order`.
  `grep -r "ui_click.*side-control-buy"` only matches `tools/redis_bus_dm_claude_tv_paper_picks.py`
  (a Redis DM tool that *requests* Claude to place, it does not place).
- **No GitHub Actions workflow** places TV paper trades
  (`.github/workflows/*.yml` search → only sports bet auto_place).
- **No cron job / scheduler** mentions TV placement.
- The audit log `alpha_engine/data/tv_paper_trade_audit_log.jsonl` shows manual
  PM-driven placements by `agent: claude-opus-4.6-1m` — these placements **do**
  include `tp` and `sl` fields in the log.

## Root cause (identified)

**All TV paper placements are performed by live Claude Code / Cursor / Antigravity
agents running the `.claude/skills/tv-paper-trade/SKILL.md` skill** (or calling the
`mcp__tradingview-desktop__ui_*` tools directly). The skill **already** has a HARD
BLOCKER gate at Step 4 that tells the agent to abort placement if TP/SL inputs are
not visible:

> `BLOCKER_FAIL: only N inputs visible — TP/SL section collapsed. EXPAND Exits
> panel first, then re-run Step 4. DO NOT PROCEED TO STEP 5.`

**The bug is agent behavior, not a script.** Agents are:

1. Running Step 4 → seeing `BLOCKER_FAIL` because the "Exits" panel is collapsed.
2. Failing to expand the Exits panel / retry.
3. **Proceeding to Step 5 (market click) anyway** — opening a position with no
   protection.

The symbols cycle because the same scored picks pipeline (active_picks.json + 
smart_picks.json) surfaces JTO/SUI/OP/KITE/BTC/ADA/LINK each run, different agents
pick from that shared candidate list, and several of them skip the TP/SL gate.

## Fix applied

### 1. Strengthened the skill (hard-fail language)
`.claude/skills/tv-paper-trade/SKILL.md` — Steps 4/5 now include a pre-flight
panel-expansion check and an explicit `VIOLATION: AGENT MUST ABORT` banner when
the TP/SL inputs are not present. Added an **order-sanity check**:

- LONG → `tp > entry > sl` required, otherwise abort.
- SHORT → `sl > entry > tp` required, otherwise abort.

### 2. Added nightly audit tool
`tools/tv_paper_tpsl_audit.py` — reads current open positions from the TV DOM
and flags any with missing/inverted TP/SL. Broadcasts violators on the Redis
bus so `antigrav-dash-integrity` (or whoever is on that lane) can auto-fix.

### 3. Logging discipline
Every placement logged to `alpha_engine/data/tv_paper_trade_audit_log.jsonl`
MUST include `tp` and `sl` fields. A placement logged without both is a
retroactive violator signal.

## Short-term workaround

Run the audit tool every 15 min while we track whether the skill hardening
stops the violators:

```bash
python tools/tv_paper_tpsl_audit.py --broadcast
```

## Symbols currently under watch
`JTOUSDT`, `SUIUSDT`, `OPUSDT`, `KITEUSDT`, `BTCUSDT`, `ADAUSDT`, `LINKUSDT`

## If violators persist after skill hardening
Escalate: temporarily add a JS confirm() dialog injection into the TV desktop
app that requires typing the TP/SL values before Step 5 can fire. Or: disable
the `ui_click` side-control tools entirely at the MCP layer until a safer
placement wrapper is built.
