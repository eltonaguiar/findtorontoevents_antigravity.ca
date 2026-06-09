# Deep-Dive: Remaining Due-Diligence Action Items (2026-06-09)

You are a quant systems engineer. The due-diligence sweep is complete (gating SOLID, splits WIRED, GHA GREEN, 7 scale-corrupt rows quarantined). Now deep-dive the remaining follow-ups and output PRIORITIZED CONCRETE TASKS with implementation guidance.

## Context

### Action Item 1: Root prevention — validate entry_price at ingest
- 7 rows with |pnl| > 1000% were found in trading_picks, caused by mis-scaled entry/exit prices
- An existing `clamp_pnl_pct_for_pick` caps CRYPTO pnl at +500% at READ time, but 99 dormant scale-corrupt entries exist
- The fix: at pick INGEST time, validate entry_price against the symbol's current market price range
- **Deliver: which file is the ingest entrypoint? What validation function signature? What threshold? Should forex/futures be exempt?**

### Action Item 2: Recover 709 NULL-pnl rows
- 709 rows in trading_picks have terminal status but pnl_pct IS NULL, and 697 of them have exit_price
- Zoo's PR #557 includes a `backfill_resolved_pnl.py` tool but it fails on `chk_pnl_sign_coherence`
- **Deliver: should we fix Zoo's tool, write a simpler recovery script, or wait?**

### Action Item 3: Remove orphan get_split_adjustment
- `outcome_resolver.py:720 get_split_adjustment()` has 0 callers — dead code
- The live path is `universal_pick_resolver.py:1169 → should_adjust_for_split()`
- **Deliver: confirm it's truly unused. Delete or deprecation comment?**

### Action Item 4: Rebase PR #556
- 3 commits ahead of main, mergeState UNKNOWN, carries 251 staged files
- Lint-masking fix is now on main
- **Deliver: safe rebase procedure. Should all 251 files go in?**

### Deliver per item
1. Priority (P0/P1/P2) and effort estimate (minutes)
2. Concrete implementation spec (file, function, logic)
3. Risk and mitigation
4. Whether it blocks the money-ready measurement pipeline
