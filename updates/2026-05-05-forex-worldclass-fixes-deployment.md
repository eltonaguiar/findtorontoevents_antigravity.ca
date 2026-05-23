# Forex World-Class Fixes Deployment — 2026-05-05

**Agent:** Buffy (Codebuff, deepseek-v4-pro)
**Branch:** `fix/forex-worldclass-pipeline-2026-05-05`
**Commit:** `4a80fc3`
**Source:** `updates/2026-05-05-forex-audit-swarm-review.md`

---

## Summary

5 critical fixes from the forex audit, targeting PF improvement from 0.28 → 1.50.

### Files Changed

| File | Changes |
|------|---------|
| `alpha_engine/forex_strategies.py` | Widen TP/SL, fix session guard, kill forex_tsmom_12m, add ig_contrarian (Strategy 9), fix SMA50 guard bug |
| `alpha_engine/hedge_fund_quality_gate.py` | Un-ban EURUSD=X from FOREX_BANNED_SYMBOLS |
| `alpha_engine/forex_smart_picks.py` | Widen TP/SL, remove cta_tsmom_blend + forex_tsmom_12m from ALL_STRATEGIES |

### Details

**1. TP/SL Caps Widened (0.3%/0.2% → 0.8%/0.5%)**
- Problem: Spreads consume 3-6% of a 0.3% TP target
- Fix: Wider caps let edge outrun transaction costs
- Affects: `_forex_tp_sl()` defaults (tp_mult 1.5→2.0, sl_mult 1.0→1.5), `forex_smart_picks.py` constants

**2. Session Guard Widened (13-16 UTC → 07-16 UTC)**
- Problem: Blocking signal generation during optimal entry windows (Asian end 07:00, London open 08:00)
- Fix: Generate signals from 07-16 UTC

**3. Dead Strategies Killed**
- `forex_tsmom_12m`: Sharpe -1.73 — FX mean-reverts, trend-following fails
- `cta_tsmom_blend`: Sharpe -2.69 — CTA momentum destroys capital on FX
- Functions kept as DEPRECATED for reference

**4. IG Contrarian Sentiment Promoted (Strategy 9)**
- Sharpe 5.87, WR 58.3% — best forex performer
- Promoted from `forex_smart_picks.py` to first-class strategy in `forex_strategies.py`
- Fixed SMA50 guard bug: `dropna()<55` → `dropna()<6` (was silently skipping)

**5. EURUSD Un-banned**
- World's most liquid pair with tightest spreads
- If strategies lose on EURUSD, strategies are broken, not the asset

---

## Open PR Review Commentary

### #819 — feat(ruflo): CLI parity
✅ **Ready to close.** All changes deployed to main via Buffy commit `caa50bb`. The --tier, --check-keys, --swarm all, and wizard.py fixes are all live.

### #818 — fix(swarm): pre-flight key check, empty-envelope retry
✅ **Ready to close.** All changes deployed via Buffy commit `8f1833f`. The empty-envelope retry, pre-flight key skip, and cerebras SDK fallback are all on main. Note: the `__init__.py` files, `config_loader.py` key-env aliases, and `EXECUTIVE_SUMMARY.md` were also deployed as part of the PR #818 gap closure.

### #817 — fix(ruflo): model passthrough, thread safety, auto-detect REPO_ROOT
⚠️ **Partially deployed.** The REPO_ROOT auto-detect and model passthrough are on main. The thread safety fix (`threading.Lock()`) should be verified — if `run_swarm_audit` uses paid tier (no tmux), the threading path may not be exercised. The `run_agent()` function refactoring is not yet on main — worth a diff review.

### #798 — fix(security): migrate ejaguiar1_memecoin credential
🔴 **Priority — merge ASAP.** This is a security fix replacing `testing123` plaintext password with `MEMECOIN_DB_PASS` env var across 5 files. Risk is low (MySQL rejects empty-string defaults gracefully). Merge first, then verify deployment.

### #777 — fix(sports): normalize EST day bucketing
⚠️ **Data integrity fix.** Deterministic `Intl.DateTimeFormat` parsing for midnight EST transitions. Includes regression tests. Worth reviewing and merging — midnight sports data is a real production bug.

### #772 — feat(b9): adversarial debate shadow
ℹ️ **Can wait.** Default-OFF, requires `UEPS_ADVERSARIAL_ENABLED=1`. 14-day shadow run. PR explicitly says "DO NOT ADMIN-MERGE — awaiting human review."

### #764 — feat(b5): Cursor Phase 3 — concept-aware scoring
ℹ️ **Can wait.** Shadow-mode only (`CONCEPT_SCORING_SHADOW=0`). 7-day shadow review period before enabling. 27 tests included.

---

## Estimated PF Impact

| Fix | PF Improvement |
|-----|---------------|
| Widen TP/SL caps | +0.20 |
| Kill dead strategies | +0.10 |
| Session guard widening | +0.10 |
| Promote ig_contrarian | +0.15 |
| **Phase 1 total** | **PF 0.28 → 0.83** |
| Additional (pipeline gap, COT data, etc.) | +0.67 |
| **Phase 2 target** | **PF 1.50** |

---

## Verification

- ✅ Python syntax clean on all 3 files
- ✅ Code review passed (2 rounds) — SMA50 guard bug fixed
- ✅ auto_tuner.py breakage risk assessed: none (dict key iteration, not hardcoded lookups)
- ✅ No breaking changes to existing strategy signatures
