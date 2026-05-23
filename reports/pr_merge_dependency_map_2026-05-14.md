# PR Merge Dependency Map — 2026-05-14

**Generated:** 2026-05-14 by Codebuff (Buffy/deepseek-v4-pro)
**Scope:** 8 open PRs originally (#995–#1007), 2 merged, 6 remaining

---

## Already Merged ✅

| PR | Description | Files | Merged |
|----|------------|-------|--------|
| **#995** | fix(etf-sector-momentum): union ETF+BOND so TLT/HYG resolve | `alpha_engine/etf_strategies.py` | ✅ Squash merged |
| **#1007** | feat(deep-dive): verification matrix + DSR browser parity + staleness metadata | `hc_filter.js`, `dashboard_generator.py`, 5 md/json, 2 tests, 1 tool | ✅ Squash merged |

---

## Remaining (6 PRs) — Root Conflict: `multi_asset_copytrader_scraper.py`

All 6 remaining PRs modify `copy_trader_intel/multi_asset_copytrader_scraper.py` which exists on `main`. Each branch added/modified this file independently, creating cross-PR merge conflicts.

### Recommended Merge Order

```
Phase 2: Docs baseline
  #996  →  docs(mmr-synthesis): Round-1 swarm + Round-2 ships + Round-3 consult
         Files: multi_asset_copytrader_scraper.py, 3 .md reports
         Risk: LOW (docs + scraper dedup baseline)
         WHY FIRST: Sets the scraper dedup foundation that #1004 depends on

Phase 3: Cleanup + corrections
  #1006 →  docs(mmr-corrections): drift field-name fix + 7 numeric corrections
         Files: multi_asset_copytrader_scraper.py, 1 .md report
         Depends on: #996 (scraper baseline)
  
  #1002 →  fix(quality-gates): quarantine breakout_b_ml + kimi_claw_research
         Files: quality_gates.py (+3), multi_asset_copytrader_scraper.py
         Depends on: #996 (scraper baseline)

Phase 4: Strategy + infra fixes (higher risk, needs rebase)
  #1004 →  fix(cot-ledger): atomic write + O_EXCL lock + direction-in-key
         Files: cot_positioning.py (+104/-36), multi_asset_copytrader_scraper.py, test
         Depends on: #996 (scraper dedup logic)
         Risk: MEDIUM (substantive cot_positioning.py changes)

  #1003 →  feat(equity-rsi2-short): mirror of 75.7% WR LONG twin
         Files: config.py (+1), equity_strategies.py (+80), multi_asset_copytrader_scraper.py
         Depends on: #996 (scraper baseline)
         Risk: MEDIUM (new strategy code + config change)

  #1005 →  fix(walkforward-gate): n-trades floor blocks Sharpe-from-noise
         Files: dashboard_generator.py (+15/-2), multi_asset_copytrader_scraper.py
         Depends on: #996 (scraper baseline), #1007 merged (dashboard_generator.py)
         Risk: MEDIUM (conflicts with already-merged #1007's dashboard_generator.py changes)
```

### Dependency Graph

```
#995 ✅───┐
          ├── main (updated)
#1007 ✅──┘
          │
          ▼
       #996 ── scraper dedup baseline ──┐
          │                              │
          ├── #1006 (docs corrections)   │
          ├── #1002 (quality gates)      │
          │                              │
          ├── #1004 (cot atomic write)◄──┘
          ├── #1003 (equity rsi2 short)
          └── #1005 (walkforward fix) ── conflicts with #1007 already merged
```

### Conflict Resolution Strategy

Since all 6 PRs add the same (+58/-0) to `multi_asset_copytrader_scraper.py`, the approach is:

1. **Merge #996 first** — it contains the COT per-release dedup ledger logic (the most substantive scraper change)
2. **Rebase remaining 5** on updated main — all will conflict on the same file with the same diff
3. **Resolve by accepting #996's version** of the scraper file since #996 is the dedup foundation
4. **Merge remaining in Phase 3→4 order**

---

## Cross-Reference: Grok Session (ses_1db6) Local PRs

The Grok session (`session-ses_1db6.md`, May 13-14) created 4 local branches not yet pushed as PRs:

| Branch | Description | Status |
|--------|-------------|--------|
| `feat/drift-dsr-browser-enforcement` | DSR + drift gates in `hc_filter.js` | Local, ready to PR |
| `fix/cot-lag-backtest` | COT 3-day publication-lag corrected backtests | Local, queued |
| `feat/bond-fred-wiring` | FRED API wiring for BOND throughput | Local, queued |
| `feat/etf-universe-expansion` | XLF/XLE/XLK ETF universe expansion | Local, queued |

**Note:** #1007 merged above already includes DSR browser parity (`hc_filter.js` + `passesDsrGate`). The Grok branch `feat/drift-dsr-browser-enforcement` may overlap or be superseded.

---

## P0 Blocker Identified

From `session-ses_1db6.md`: `tools/verify_multi_asset_cot_db.py` **FAILED** due to MySQL access denied. This is a P0 blocker for all COMMODITY PF 2.08 claims. Resolution requires:
- Live MySQL credentials OR IP allow-list update for `ejaguiar1_stocks`

---

## Summary

| Status | Count | PRs |
|--------|-------|-----|
| ✅ Merged | 2 | #995, #1007 |
| 🔀 Ready (after #996 baseline) | 5 | #1002, #1003, #1004, #1005, #1006 |
| 📋 Baseline needed first | 1 | #996 |
| 🚫 P0 Blocker (credentials) | 1 | COT DB verification |
| 📝 Local branches (Grok session) | 4 | drift-dsr, cot-lag, bond-fred, etf-expand |
