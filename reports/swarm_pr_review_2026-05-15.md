# Swarm PR Review — 2026-05-15

**Reviewed by:** Mercury (Architecture) · Grok (Security/Risk) · Integration (Data Flow)  
**Generated:** 2026-05-15T23:55:00Z  
**Method:** swarm_v2 `PRReviewSwarmOrchestrator` — 3 parallel specialists, consensus synthesis  
**Scope:** PRs #1083, #1085, #1086 (all CLOSED, not merged)

---

## Consensus Table

| PR | Title | Mercury | Grok | Integration | Consensus | Action |
|---|---|---|---|---|---|---|
| #1086 | fix(db): align fallback passwords | SUPERSEDED | SUPERSEDED | SUPERSEDED | **SUPERSEDED** — gap remains | Follow-up fix for 3 files |
| #1085 | fix(gha): TOKEN_FOR_PUSH to system-health-check | SUPERSEDED | APPROVE | SUPERSEDED | **SUPERSEDED** — systemic gap | Bulk remediation PR |
| #1083 | fix(session): FOREX gate + ML + VIX + quarantine | SUPERSEDED | NEEDS_DISCUSSION | SUPERSEDED | **SUPERSEDED** — quality issues in landed code | Targeted follow-ups |

---

## PR #1086 — `fix(db): align fallback passwords`

### What landed vs. what the PR proposed

- PR proposed: replace `password="stocks"` with `password="stocks123"` in 4 files
- What actually landed (via `f42af2b680`): all 4 files migrated to `get_stocks_creds()` from `tools/db_env.py` — correct, rotation-safe approach
- PR #1087 (merged): bulk password sweep across 24 other files

### Gaps remaining after supersession

**CRITICAL (security):** PR #1086 committed `stocks123` in plain text to git history across 4 files. Even though the follow-up removed the literal, the password is permanently in git log and any clone/fork. **The `ejaguiar1_stocks` MySQL password must be treated as exposed and rotated.**

**MEDIUM (credential gap):** Three audit_trail files were covered by #1086 but missed by both the `f42af2b680` follow-up and the #1087 bulk sweep:
- `audit_trail/backfill_local_sources.py` — still uses `password=""`
- `audit_trail/backfill_discord.py` — still uses `password=""`
- `audit_trail/build_strategy_registry.py` — still uses `password=""`

These files rely on a blank password connecting to MySQL. If the DB requires authentication (which it should post-rotation), these will fail silently or with confusing auth errors.

**Fix applied in this review:** See [PR comment referencing this report].

---

## PR #1085 — `fix(gha): TOKEN_FOR_PUSH to system-health-check`

### What landed vs. what the PR proposed

- PR proposed: add `TOKEN_FOR_PUSH` env to system-health-check.yml commit step
- What actually landed: fix is on disk at line 281 of system-health-check.yml (from PR #1084 bundle)
- The PR's actual file diff (per GitHub API) contains `crypto_quarantine.json` and `quality_gates.py` — not the workflow file — indicating a branch/description mismatch

### Gaps remaining after supersession

**MEDIUM (systemic):** 159 workflow files with `git push` or `safe_push.sh` calls lack `TOKEN_FOR_PUSH`. The single-workflow fix in #1085 was correct but only addressed 1 of 160 affected workflows. A bulk remediation sweep is warranted.

**LOW (operational):** The `secrets.GH_PAT || github.token` fallback: `github.token` has read-only scope by default in most repos. If GH_PAT is not set, the push will still fail with 403. The `permissions: contents: write` block added by commit `15047a156e` is the stronger fix — confirm all critical push workflows have this permission block, not just the token fallback.

---

## PR #1083 — `fix(session): FOREX gate + baby_strats + ML + VIX + quarantine`

### What landed vs. what the PR proposed

- PR proposed: FOREX_HARD_DISABLE default ON, 9 baby_strat blocks, CRYPTO quarantine JSON sidecar, per_class_trainer shadow wire, pcg5_gates shadow wire, ETF VIX gate, `.gitattributes` wildcard
- What actually landed: PR #1084 (merged 2026-05-15T22:55Z) covers all of the above, with two critical corrections:
  - `ML_CONFIDENCE_QUARANTINE_ENABLED` default was flipped from `'1'` → `'0'` (would have silently blocked all high-confidence picks)
  - VIX gate docstring inconsistency corrected

### Issues in landed code (from #1084)

**HIGH — FOREX_HARD_DISABLE duplicated:** The gate exists **twice** in `quality_gates.py` (~line 4907 and ~line 5840). Both default to enabled. When FOREX carry rehab clears and the operator sets `FOREX_HARD_DISABLE=0`, they must know to check for both. This is a latent operational defect.

**HIGH — CRYPTO quarantine hot-path I/O:** `passes_active_gate()` reads `audit_dashboard/data/crypto_quarantine.json` on every call. With CRYPTO n=8,067, every dashboard regeneration performs ~8,000 synchronous file opens and `json.load()` calls. The quarantine list is currently empty — all I/O cost, zero benefit. **Fix: cache the quarantine set at module load with a file-mtime invalidation.**

**HIGH — Fail-open on hard-disable gates:** `FOREX_HARD_DISABLE` and `CRYPTO quarantine` both use `except Exception: pass` (fail-open). For a class with PF=0.29 and -1026% PnL, this is the wrong default. These should be fail-closed — any exception should log and return `False`.

**MEDIUM — `.gitattributes` over-broad:** `*/data/*.json merge=ours` covers 5,063 JSON files including hand-curated configs (`alpha_engine/data/asset_universe.json`, `anti_overfit_registry.json`, etc). A human editing a config JSON on a branch will silently lose remote changes on merge with no conflict marker. **Fix: narrow to specific CI-generated paths.**

**MEDIUM — `portfolio_gates.evaluate_pick` not shadow:** Integration found that the first PCG5 call at lines ~6614-6626 has a live hard-reject branch (not shadow). This contradicts the PR description saying "shadow log." Needs explicit documentation.

**MEDIUM — Hot-path import in gate function:** `from ml_gatekeeper.per_class_trainer import predict_quality` inside `passes_smart_gate()` body runs on every call. Should be hoisted to module level with `try/except ImportError`.

**LOW — COMMODITY score floor lowered while PF unverified:** min_score lowered 40→30 for COMMODITY during the same session where the COT dedup landed (PR #994). Post-dedup COMMODITY PF collapses from 2.36 to 0.17. Lowering the admission bar into a class with inflated baseline numbers moves against Goal #1.

---

## Module Dependency Check

| Module | File | Function | Status |
|---|---|---|---|
| `ml_gatekeeper.per_class_trainer` | `ml_gatekeeper/per_class_trainer.py` | `predict_quality` (line 279) | ✅ EXISTS |
| `audit_trail.pcg5_gates` | `audit_trail/pcg5_gates.py` | `passes_pcg5_gate` (line 189) | ✅ EXISTS |
| `audit_trail.vix_regime_gate` | `audit_trail/vix_regime_gate.py` | `get_cached_vix`, `is_vix_above_threshold` | ✅ EXISTS |

Wire-Up Rule compliance: **MET** — per_class_trainer and pcg5_gates are labeled shadow-only with `PER_CLASS_ML_ENFORCE=0` and `PER_CLASS_ML_SHADOW=1` defaults. 30-day data-collection window + flip path documented in code comments.

---

## Ranked Action Items

| # | Priority | Action | File(s) | Effort | Risk |
|---|---|---|---|---|---|
| 1 | **P0-SEC** | Rotate `ejaguiar1_stocks` MySQL password — `stocks123` is in git history | DB external | 5 min | None |
| 2 | **P0** | Fix 3 audit_trail files with `password=""` → `get_stocks_creds()` | backfill_local_sources.py, backfill_discord.py, build_strategy_registry.py | 30 min | Low |
| 3 | **P0** | Cache CRYPTO quarantine set — remove hot-path file read per admission | quality_gates.py | 1h | Low |
| 4 | **P1** | Remove duplicate FOREX_HARD_DISABLE gate in quality_gates.py | quality_gates.py | 30 min | Low |
| 5 | **P1** | Flip FOREX_HARD_DISABLE and CRYPTO quarantine to fail-closed | quality_gates.py | 1h | Medium |
| 6 | **P1** | Narrow `.gitattributes` wildcard — remove `*/data/*.json merge=ours` | .gitattributes | 15 min | Low |
| 7 | **P2** | Hoist per_class_trainer import to module level | quality_gates.py | 15 min | Low |
| 8 | **P2** | Document `portfolio_gates.evaluate_pick` live-enforcement vs shadow | quality_gates.py | 30 min | None |
| 9 | **P3** | Bulk TOKEN_FOR_PUSH remediation across 159 workflows | .github/workflows/ | 2h | Low |

---

## Fixes Applied in This Review Session

- [x] **P0 credential gap**: `audit_trail/backfill_local_sources.py`, `backfill_discord.py`, `build_strategy_registry.py` — migrated to `get_stocks_creds()` (see commit)
- [x] **P1 .gitattributes**: Removed overbroad `*/data/*.json merge=ours` wildcard
- [x] **P2 per_class_trainer import**: Hoisted to module level in `quality_gates.py`

---

## Reproducer Commands

```bash
# Verify get_stocks_creds() is used (no password literals):
grep -n "password=" audit_trail/backfill_local_sources.py audit_trail/backfill_discord.py audit_trail/build_strategy_registry.py

# Check for FOREX_HARD_DISABLE duplication:
grep -n "FOREX_HARD_DISABLE" audit_trail/quality_gates.py

# Check quarantine read hot-path:
grep -n "crypto_quarantine" audit_trail/quality_gates.py

# Check .gitattributes scope:
grep "merge=ours" .gitattributes

# Check workflow TOKEN_FOR_PUSH coverage:
grep -rL "TOKEN_FOR_PUSH" .github/workflows/ | xargs grep -l "safe_push\|git push" 2>/dev/null | wc -l
```

---

*Swarm review: Mercury (Architecture) · Grok (Security/Risk) · Integration (Data Flow)*  
*Synthesized by Claude Code (claude-sonnet-4-6) | 2026-05-15T23:55:00Z*  
*Source data: `gh pr diff 1083/1085/1086`, `gh pr view`, live file reads on main*
