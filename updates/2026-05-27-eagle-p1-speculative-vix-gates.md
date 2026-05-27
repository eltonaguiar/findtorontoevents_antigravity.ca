# EAGLE P1: Speculative EQUITY quarantine + VIX active gate (2026-05-27)

## What changed

1. **`alpha_engine/config.py`**
   - Added `SOFI`, `SNDL` to `GAP_RISK_EQUITY_SYMBOLS`.
   - New `RESEARCH_ONLY_SPECULATIVE_SYMBOLS` frozenset + `is_research_only_speculative()`.

2. **`audit_trail/quality_gates.py`**
   - `passes_speculative_equity_gate()` — blocks EQUITY picks on GME/AMC/NIO/etc. Kill-switch: `EQUITY_SPECULATIVE_GATE_ENABLED=0`.
   - `passes_vix_regime_active_gate()` — blocks EQUITY/ETF active picks when VIX > 22. Kill-switch: `VIX_REGIME_ACTIVE_GATE_ENABLED=0`.
   - Both wired into `passes_active_gate()` after penny/meme gate.

3. **Workflows**
   - `smart-picks-tracker.yml`: `CONFIDENCE_INVERT_CRYPTO=1`.
   - `outcome-resolver.yml`: WON/PnL coherence step; expanded `active_picks_sync` to COMMODITY/ETF/BOND.
   - `audit-dashboard.yml`: `sync_summary_picks_json.py` + git-add `summary_picks.json`.

4. **Tools**
   - `tools/sync_summary_picks_json.py` — real per-class `last_pick` timestamps.
   - `tools/clamp_forex_pnl_extremes.py` — opt-in via `FOREX_PNL_CLAMP_APPLY=1`.
   - `tools/sql/audit_roadmap_items.sql` + `tools/audit_roadmap_seed.py` — roadmap DB DDL + seed from incidents feed.

5. **Tests**
   - `tests/test_equity_speculative_gate.py` — 5 passed.

## Verification

```bash
python3 -m pytest tests/test_equity_speculative_gate.py -q
python3 tools/sync_summary_picks_json.py
```

## Operator actions (GitHub repo vars)

| Variable | Value | Effect |
|---|---|---|
| `WON_PNL_AUTO_APPLY` | `1` | Hourly WON→LOSS relabel in outcome-resolver |
| `FOREX_PNL_CLAMP_APPLY` | `1` | Clamp extreme FOREX pnl in outcome-resolver |

## Still open (P1/P0)

- QW-02 PEAD equity promotion — blocked until 2026-06-14 review gate
- QW-10 IPO tab caveat — not started
- P0: forward_validator restart, ghost dedup, trust_score backfill, PnL re-resolve

## Evidence

- `reports/EAGLE-2026-05-27T02-25-00_EST-cursor-composer-strategy-audit.md`
- `reports/EAGLE-2026-05-27T02-25-00_EST-cursor-composer-quick-wins.md`
