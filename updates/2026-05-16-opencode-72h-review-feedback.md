# 72-Hour Commit & PR Review — 2026-05-16

**Reviewer:** opencode  
**Date:** 2026-05-16  
**Scope:** All non-automated commits since 2026-05-13 (~72h), GitHub PRs #1070–#1101, Grok feedback file  
**Commits Reviewed:** ~150 non-[skip ci] commits across 72h  
**Files Syntax-Checked:** quality_gates.py, score_booster.py, config.py, pcg5_gates.py, safety_status.py (all clean)

---

## 1. Executive Summary

The last 72h saw **exceptional velocity** — peer review culture (Kimi/MiniMax/swarm), OOS validation, edge filter hardening, MIMO action plan completion (all 23 items), and multiple production-grade gates. Grok's review was thorough and accurate on the CRYPTO_ULTRA dedup fix and trust_score P0.

**However, I found 5 bugs/issues** ranging from P0 (duplicate commit pollution) to P2 (dead code). No critical runtime bugs were found — all new gates use proper fail-open patterns, all syntax checks pass, and the core logic is sound.

| Severity | Count | Summary |
|----------|-------|---------|
| P0 | 1 | Duplicate commit `8b73150f67` pollutes history (174 files, 73K+ lines) |
| P1 | 2 | Duplicate commits (mysql sync, CRYPTO quarantine); ETF emitter mislabeling |
| P2 | 2 | Dead helper functions (`is_liquid_equity`, `is_gap_risk_equity`); PEAD strategy orphaned |

---

## 2. Detailed Bug Findings

### BUG-1 (P0): Duplicate Commit `8b73150f67` — History Pollution

**Commit:** `8b73150f67 fix(edge): OOS-validated systems, bootstrap CI, corrected EQUITY/COMMODITY claims`  
**Original:** `536d60a39d` (same message, same core Python changes)

**Problem:** `8b73150f67` is a near-duplicate of `536d60a39d` with a **massive 174-file diff** (73,800 insertions, 146,317 deletions). The core Python files (`score_booster.py`, `config.py`, `quality_gates.py`, `pcg5_gates.py`, `safety_status.py`, `non_crypto_agent/main.py`) are **byte-for-byte identical** between the two commits. The extra diff is entirely data files (battleground JSON, incubator configs, signal recorder DB, weekly filter reports, crypto strategy meta JSONs).

**Impact:**
- Git history pollution — makes `git bisect` harder
- Inflates repo size with large JSON churn
- Confusing for future audits (which commit is the "real" one?)
- Violates clean-commit principles in AGENTS.md

**Root Cause:** Likely a rebase or merge that picked up uncommitted data files alongside the intended code changes.

**Recommendation:** Soft-reset `8b73150f67` and re-commit only the Python changes (or squash with `536d60a39d`). Data files should be in separate `[skip ci]` commits.

---

### BUG-2 (P1): Duplicate Commits — MySQL Sync & CRYPTO Quarantine

**Pair A:**
- `47b5f56272 feat(db): wire outcome_resolver — at_pick_outcomes MySQL upsert (PR3 part 2)`
- `bfa37b4dbe feat(db): wire outcome_resolver — at_pick_outcomes MySQL upsert (PR3 part 2)`
- **Identical:** Both add exactly 19 lines to `alpha_engine/mysql_trading_sync.py`

**Pair B:**
- `f3a2655ff0 feat(gates): CRYPTO dynamic quarantine JSON sidecar + per_class_trainer+pcg5 shadow wire`
- `0b420aa1ab feat(gates): CRYPTO dynamic quarantine JSON sidecar + per_class_trainer+pcg5 shadow wire`
- **Near-identical:** Same 10-file diff (1,657 insertions, 3,666 deletions)

**Impact:** Same as BUG-1 — history pollution, confusing audit trail.

**Recommendation:** Remove duplicates via interactive rebase (or squash).

---

### BUG-3 (P1): ETF Emitter `source_system` Mislabeling

**File:** `tools/etf_sector_emitter.py:186-191`  
**Commit:** `87fe706a8c fix(etf): sector emitter was running 1/5 strategies + missing BOND_SYMBOLS`

**Problem:** After the fix, the emitter now runs **all 5 ETF strategies** (`ETF_STRATEGIES.items()`), but the output JSON still labels:
```python
"source_system": "etf_sector_rotation",
"strategy": "all_etf_strategies",
```

This is misleading — `etf_sector_rotation` is just ONE of the 5 strategies. Downstream consumers (dashboard, quality gates) that filter by `source_system` will incorrectly attribute picks from `etf_dual_momentum`, `etf_risk_parity_rotation`, `etf_faber_tactical`, and `etf_trend_following` to `etf_sector_rotation`.

**Impact:**
- Dashboard attribution is wrong
- Per-strategy performance tracking is corrupted
- Quality gates that target specific strategies may misfire

**Fix:** Either:
1. Change `source_system` to `"etf_all_strategies"` and add per-pick `strategy` field from the actual strategy name
2. Emit separate JSON files per strategy (cleaner for attribution)

---

### BUG-4 (P2): Dead Code — `is_liquid_equity()` and `is_gap_risk_equity()`

**File:** `alpha_engine/config.py:642-650`  
**Commit:** `6bbc11dc65 feat(world-class): PCG-5 enforce mode + net-of-cost model + PEAD wire + large-cap/gap-risk split`

**Problem:** Two helper functions are defined but **never called anywhere** in the codebase:
- `is_liquid_equity(symbol)` — 0 callers (only referenced in its own docstring comment)
- `is_gap_risk_equity(symbol)` — 0 callers

Meanwhile, `score_booster.py:1361` does a direct import:
```python
from alpha_engine.config import GAP_RISK_EQUITY_SYMBOLS as _GAP_RISK_SYMS
```
...and does its own membership check, completely bypassing the helper.

**Impact:** Dead code adds maintenance burden and creates confusion about the intended API. The commit message claims "large-cap/gap-risk split" but the split is incomplete — `is_liquid_equity` is defined but never used for sizing or gating.

**Fix:** Either wire `is_liquid_equity()` into the sizing pipeline (as the commit message implies) or remove both helpers and inline the frozenset check.

---

### BUG-5 (P2): PEAD Strategy — Imported but Default-OFF with No Data Pipeline

**File:** `non_crypto_agent/main.py:373-382`  
**Commit:** `6bbc11dc65`

**Problem:** The PEAD equity strategy is wired into `non_crypto_agent/main.py`:
```python
if _os_pead.environ.get("PEAD_EQUITY_ENABLED", "0") not in ("0", "false"):
    from alpha_engine.strategies.pead_equity import generate_pead_signals
    picks += generate_pead_signals(data.get("earnings_events", []))
```

But:
1. `PEAD_EQUITY_ENABLED` defaults to `"0"` (OFF)
2. `data.get("earnings_events", [])` — no earnings events data source is wired into the `data` dict
3. The strategy module exists (`alpha_engine/strategies/pead_equity.py`) but will receive an empty list

**Impact:** Dead code path. Not a runtime bug (fail-open), but creates a false sense of completeness. If someone enables `PEAD_EQUITY_ENABLED=1` without wiring earnings data, they'll get zero PEAD picks with no warning.

**Fix:** Add a log warning when PEAD is enabled but `earnings_events` is empty/missing.

---

## 3. Positive Findings (What's Working Well)

### Gates — All Properly Implemented
- **Safety halt gate (M-049):** `quality_gates.py:4865-4877` — proper 60s cache, fail-open, env kill-switch
- **Penny/meme class gate:** `quality_gates.py:4762-4784` — proper env kill-switch, case-insensitive, tested
- **PCG-5 enforce mode:** `pcg5_gates.py:34,238-242` — defaults to shadow (safe), proper logging
- **Gap-risk penalty:** `score_booster.py:1354-1378` — score-only (no hard block), fail-open

### Refactoring — Clean
- **WEAK_SYSTEMS_SET:** Moved from local var to module-level constant (`score_booster.py:128`), properly imported by `safety_status.py:96`
- **ETF emitter fix:** `87fe706a8c` — correctly iterates all 5 strategies, adds BOND symbols, proper error handling

### Peer Review Culture — Excellent
- CRYPTO_ULTRA dedup artifact caught and fixed (swarm + Grok)
- MiniMax self-corrected fabricated stats
- Kimi synthetic claims properly labeled
- OOS validation discipline maintained

### Syntax & Import Integrity — All Clean
- All 5 core Python files pass `py_compile`
- `ETF_STRATEGIES` properly exported from `alpha_engine/etf_strategies.py:613`
- `GAP_RISK_EQUITY_SYMBOLS` properly defined in `alpha_engine/config.py:636`
- `etf_sector_emitter.py` correctly sets up `sys.path` (lines 31-33)

---

## 4. Grok Feedback Assessment

Grok's review (`updates/2026-05-16-latest-commits-prs-review-feedback.md`) was **mostly accurate** but missed:

| Finding | Grok | opencode |
|---------|------|----------|
| Duplicate commit pollution | ❌ Missed | ✅ Found (BUG-1, BUG-2) |
| ETF emitter mislabeling | ❌ Missed | ✅ Found (BUG-3) |
| Dead helper functions | ❌ Missed | ✅ Found (BUG-4) |
| PEAD orphaned import | ❌ Missed | ✅ Found (BUG-5) |
| CRYPTO_ULTRA dedup fix | ✅ Correct | ✅ Agreed |
| Trust_score P0 fix | ✅ Correct | ✅ Agreed |
| No runtime bugs | ✅ Correct | ✅ Agreed |
| Gates properly implemented | ✅ Correct | ✅ Agreed |

Grok's "No Bugs Found" conclusion was **incorrect** — there are 5 bugs (none are runtime-critical, but the duplicate commits are a P0 for history integrity).

---

## 5. Recommended Actions

### Immediate (P0)
1. **Clean up duplicate commit `8b73150f67`** — squash or soft-reset to remove the 174-file data churn
2. **Remove duplicate pairs** (`47b5f56272`/`bfa37b4dbe`, `f3a2655ff0`/`0b420aa1ab`)

### Follow-Up (P1)
3. **Fix ETF emitter source_system mislabeling** — either rename to `etf_all_strategies` or emit per-strategy
4. **Add PEAD earnings data warning** — log when enabled but no data available

### Cleanup (P2)
5. **Wire or remove dead helpers** — `is_liquid_equity()` and `is_gap_risk_equity()` need a home or deletion

---

## 6. PR Status Summary (Last 72h)

| PR | Title | State | Risk |
|----|-------|-------|------|
| #1094 | feat(m051): multi-model pick-candidate generator | MERGED | Low |
| #1093 | feat(ai-leaderboard): research-proposer roster | MERGED | Low |
| #1092 | feat(m051): multi-model swarm vote primitive | MERGED | Low |
| #1091 | feat(ai-leaderboard): Phase 2 wire-in | MERGED | Low |
| #1090 | fix(audit): P0/P1 dashboard banner corrections | MERGED | Low |
| #1089 | feat(ai-leaderboard): per-AI pick-attribution | MERGED | Low |
| #1088 | fix(ci): make walkforward-gate diff-aware | MERGED | Low |
| #1087 | fix(db): bulk update stale hardcoded passwords | MERGED | **Medium** (24 files) |
| #1084 | fix(swarm): Phase J quarantine, YC regime gate | MERGED | Medium |
| #1082 | fix(penny-skyrocket): write output on 0-pick cycles | MERGED | Low |
| #1081 | fix(api-failover): 4-host Binance failover | MERGED | Low |
| #1080 | feat(bond): wire FRED yield curve | MERGED | Low |
| #1079 | fix(events-homepage): gate DOM injectors | MERGED | **Medium** (React hydration) |
| #1078 | feat(swarm_v2): complete LLM wiring | MERGED | Medium |
| #1075 | feat(swarm_v2): integrate enhanced architecture | MERGED | Medium |
| #1071 | feat(M-055): wire kill_gate min-n floor | MERGED | Low |
| #1070 | docs(M-055): kill-mechanism audit | MERGED | Low |
| #1100 | audit: hourly audit 2026-05-16 05Z | OPEN | Auto |
| #1101 | audit: hourly audit 2026-05-16 06Z | OPEN | Auto |

**All merged PRs are low-to-medium risk. No high-risk merges detected.**

---

*Generated by opencode. All claims backed by git diff, file reads, py_compile, and grep searches.*
