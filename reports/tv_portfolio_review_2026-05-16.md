# TV Portfolio Review — 2026-05-16

**Date:** 2026-05-16  
**Operator:** Grok 4.3 (WSL) + desktop Claude coordination via file channel  
**Source:** `tv-portfolio-extract` (5 tabs per account) + `tv-portfolio-review` skill (A/B/C/D attribution + lessons)  
**Status:** Draft — awaiting full JSON dump from desktop TV run (CSV export for closures + active positions). The extract + review skills are now on main (per Claude 00:30Z message).

## Portfolios Reviewed (7 books swept per session log)

From the 2026-05-16 WSL + desktop coordination:
- HYROTRADER (crypto-focused, C-origin heavy)
- SCALPER / TESTER / TRUSTOURSCORE / zerounderscore / BROKIE / other audit-gated books (B-origin)
- One or more swarm/consensus books (A-origin)

**Origin Attribution Framework (from .claude/skills/tv-portfolio-review/SKILL.md):**
- **C — /audit/hyrotrader:** `hyrotrader_adx_vol_breakout`, CCI Divergence, CMF Cross, BB Squeeze, Multi-EMA with ATR plans. Portfolio name contains "hyrotrader" → strong C prior.
- **B — /audit:** dashboard_data.json, active_picks.json, smart_picks.json, source_system labels (kimi_riseoftheclaw, regime_terminal, multi_asset_copytrader, etc.).
- **A — swarm:** swarm_picks.json, consensus_tier_picks.json, copy_trader_intel consensus builders.
- **D — combo:** ≥2 sources match.

**Hard rule:** Any holding in a `hyrotrader`-named book that does NOT trace to a hyrotrader ledger is a **mis-sourced pick** — flag explicitly.

## Close Candidates (to be populated from dump.json)

After `tv-portfolio-extract`:
- Lock profit: unrealized ≥ +60% to TP or standout winner with stalled momentum.
- Cut loss: worse than −(SL × 0.8) or thesis broken or unprotected (immediate `/tv-protect-position`).
- Hold: inside band, thesis intact.

**From 2026-05-16 TV Protect Saga (lessons applied):**
- All new or unprotected positions must use `tools/tv_calc_levels.py <SYMBOL> <SIDE> [ENTRY]` for valid 1.5×ATR SL / 2×risk TP (Binance failover, side-sanity check).
- Toggles: max-robust pointer events or CDP rect click (React switch).
- SL must be BELOW market for LONGs (placeholder is always invalid — overwrite with execCommand insertText).
- The 5-hour loop on BNBUSDT/ETHUSDT was 100% the desktop Grok instance being send-only (never polled DM + all inbox). Fixed by `cross_pc_protocol/inbox_drain.py` + mandatory `startup_inbox_check()` in `cursor_claude_adapter.py`.

**Action:** Run `/tv-protect-position` on any `unprotected: true` rows first (P1–P5 procedure in the skill).

## Lessons Learned — "Is the system working?" (Goal #1 tie-in)

**Per-origin (after n≥20 clean closes):**
- **B (/audit):** Check WR/PF of recent_closed with source_system in dashboard_data.json. Compare to Tier-2 floor (PF>1.5 / WR>50). From 2026-05-16 statistical_edge_analysis: EQUITY B-origin is T2 (1.56/51.5% filtered); FOREX B-origin still sub-floor (0.86) but directional + symbol gates now shipped.
- **C (hyrotrader):** Live closes vs backtested 82-90% confidence for ADX/vol breakout etc. Crypto books in HYROTRADER were the ones protected during the saga.
- **A (swarm):** Consensus adding edge? Or stale JSONs (pipeline health flag)? From session: swarm_v2 tasks created for multi-model AI leaderboard.

**Cross-portfolio verdict (to be filled post-extract):**
- Which books net-positive?
- Does bleed trace to one origin (e.g. C crypto vs B equity wins)?
- Pipeline issues: mis-sourced picks in HYROTRADER books, unprotected positions, send-only agent anti-pattern (now mitigated).

**Statistical edge note (from 2026-05-16 reports):**
- COMMODITY verified Tier 1 post-dedup (PF 2.57/62.6%).
- CRYPTO Tuesday DOW claim in FOOLPROOF_ACTION_PLAN.md refuted (+4.4pp actual).
- The portfolio review will tell us if the live books reflect the audited edge or the drag systems (alpha_engine_fast etc).

## Ranked Actions

1. **Protect any unprotected** — run `tv-protect-position` (or the batch mode once polished) using `tv_calc_levels.py` numbers + robust toggle + execCommand.
2. **LOCK / CUT** the flagged holdings from the review tables.
3. **Pipeline fixes:** 
   - Enforce inbox_drain in all agents (hermes/ruflo/Cursor).
   - Flag mis-sourced picks in HYROTRADER books.
   - Update weekly filter with COMMODITY elite (multi_asset_cot + copytrader) + EQUITY drag-system removal.
4. **Swarm_v2 follow-up:** Run on `_task_forex_directional_gate.md`, `_task_forex_symbol_gate.md`, `_task_futures_tile_from_contract_type.md`, `_task_cross_pc_inbox_enforcement.md`, `_task_multi_model_swarm_for_ai_leaderboard.md` (M-051).

## Verification

- Skills on main: tv-portfolio-extract (with Step 2.5 for Order history shadowing bug), tv-portfolio-review, tv_calc_levels.py, tv-protect-position, tv-eval-bridge.
- Local commit for daily log + this review draft pushed via MCP where possible.
- Full numbers require desktop run of the extract (CSV for May-1+ closures + JSON dump).

**Next operator step (per Claude 00:30Z):** On the Windows desktop with TV open, run the tv-portfolio-extract skill per account (use CSV export for closures), produce the dump.json(s), then I (or the review skill) will analyze and fill the tables above.

Report will be updated post-extract with exact tables and "is the system working?" verdicts tied to the 2026-05-16 asset-class health (COMMODITY T1, EQUITY T2, FOREX mutation active).

---
*Draft created by Grok 4.3 to unblock the TV review task while desktop TV is unavailable in this WSL environment. Full data-driven version awaits the extract JSON.*