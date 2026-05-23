# Kimi P0 — Code swarm verification verdict — 2026-05-20T0215Z

Cross-checked Kimi's 4 named code bugs via 3-engine cloud swarm + cavecrew
ground-truth grep. **2 of 4 bugs are REAL. 2 are LLM hallucinations.**

## Method

- 3-engine cloud swarm (xAI / Cerebras / DeepSeek) ran
  `swarm_runs/_prompts/kimi_p0_code_audit_2026-05-20T0205Z.md` — looking for
  the 4 patterns + diagnosing resolver coverage.
- `caveman:cavecrew-investigator` agent grep'd the actual repo
  independently. cavecrew is GROUND TRUTH (reads files; doesn't invent).
- Outputs in `swarm_runs/kimi_p0_code_audit_2026-05-20T0205Z/`.

## Verdict table

| Bug | xAI | DeepSeek | Cerebras | **cavecrew (truth)** | Reality |
|---|---|---|---|---|---|
| BUG-1 DSR `max(sr_var, 1e-16)` | CONFIRMED (statistical_gates.py:87-89) | CONFIRMED (~line 45-55) | NOT_FOUND | **CONFIRMED — 5 instances** | **REAL** |
| BUG-2 PBO zero-purging | CONFIRMED (quality_gates.py:142-148) | CONFIRMED (edge_stability_harness.py:120-140) | NOT_FOUND | **CONFIRMED — 2 instances** | **REAL** |
| BUG-3 IS Sharpe uses market_return | CONFIRMED (walk_forward.py:211) | CONFIRMED (walk_forward.py:80-95) | NOT_FOUND | **NOT FOUND on disk** | **HALLUCINATED** |
| BUG-4 sqrt(250) trade-Sharpe | CONFIRMED (edge_stability_harness.py:67) | CONFIRMED (audit_trail/sharpe.py:30-45) | NOT_FOUND | **NOT FOUND — codebase uses sqrt(252)/sqrt(365)** | **HALLUCINATED** |

**Key lesson:** xAI + DeepSeek both invented plausible line numbers for BUG-3
+ BUG-4 — classic "agree with the prompt" LLM trap. Cerebras correctly
refused on all 4 (over-cautious but safer than hallucinated confirmation).
**cavecrew-investigator (which actually grep'd) is the only trustworthy
verdict.** Re-affirms `feedback_multi_ai_convergence_trap.md` rule:
N AIs agreeing on a fabricated pattern ≠ verification.

## Real bugs — exact locations

### BUG-1 REAL — `max(sr_var, 1e-16)` masking negative variance (5 instances)

| File | Line | Code |
|---|---:|---|
| `alpha_engine/deflated_sharpe.py` | 168 | `max(math.sqrt(max(var_sr, 1e-16)), 1e-12)` — nested floor |
| `alpha_engine/deflated_sharpe.py` | 208 | `max(math.sqrt(max(sr_variance, 1e-16)), 1e-12)` — DSR denominator |
| `alpha_engine/anti_overfit_validator.py` | 269 | `sr_std = math.sqrt(max(sr_var, 1e-16))` |
| `alpha_engine/statistical_rigor.py` | 413 | `sr_std = math.sqrt(max(sr_var, 1e-16))` |
| `alpha_engine/validation/statistical_gates.py` | 223 | `sr_std = math.sqrt(max(sr_var, 1e-16))` |

**Issue:** Negative variance should be impossible mathematically; in
practice it arises from numerical instability with small n or tied returns.
Flooring to 1e-16 produces a near-infinite DSR denominator-flip, returning
a near-zero `sr_std` that inflates DSR. Should either (a) error explicitly,
(b) return `NaN`, or (c) require minimum n + valid sample before computing.

**Fix sketch:**
```python
if sr_var <= 0:
    return float('nan')  # or raise ValueError
sr_std = math.sqrt(sr_var)
```

Required: patch all 5 sites consistently. Add unit test that asserts NaN/
error on negative variance.

### BUG-2 REAL — PBO with embargo=0 (2 instances)

| File | Line | Code |
|---|---:|---|
| `alpha_engine/anti_overfit_validator.py` | 118 | `embargo_td=pd.Timedelta(0)` — zero embargo CombPurgedKFoldCV |
| `tools/purged_kfold.py` | 180 | `embargo_days=0` — test fold w/o temporal purge |

**Issue:** López de Prado CPCV/CSCV requires a non-zero embargo period
(typically 1-5 days for daily bars) to prevent IS leakage into OOS via
contiguous samples. embargo=0 destroys the purging benefit. **PBO computed
with embargo=0 is information-leakage-poisoned and meaningless.**

**Fix sketch:**
```python
# Default daily-bar embargo = 2 trading days
embargo_td = pd.Timedelta(days=int(os.environ.get('CPCV_EMBARGO_DAYS', 2)))
```

For intraday data (H-039 future probe), embargo should scale to bar_freq.

## Hallucinated (NOT FIX)

### BUG-3 — IS Sharpe uses market_return: **NOT IN CODE**

cavecrew confirms `market_return` / `benchmark_return` appear only in
beta-adjustment + information-ratio contexts (`institutional_scoring.py:73`,
`ab_portfolio_test.py:376+`) — **never as Sharpe ratio numerator** in
walk_forward code. xAI's "walk_forward.py:211" and DeepSeek's "_compute_is_sharpe"
function do not exist on disk. **Kimi was wrong; do not patch.**

### BUG-4 — sqrt(250) trade-Sharpe: **NOT IN CODE**

cavecrew confirms ALL Sharpe annualizations use `sqrt(252)` for daily/equity
or `sqrt(365)` for crypto, or `sqrt(252) * trade_frequency` for per-trade.
**No `sqrt(250)` anywhere.** xAI's "edge_stability_harness.py:67" and
DeepSeek's "audit_trail/sharpe.py:30-45" do not contain this pattern.
**Kimi was wrong; do not patch.**

## Resolver coverage 0.09% — diagnosis

xAI: "workflow not firing + silent continue-on-error in forward_validator.py"
DeepSeek: "schema mismatch: resolver expects `signal_id` but DB stores `pick_id`"
Cerebras: refused / unable to locate.

**Both cloud engines wrong on specifics. cavecrew grep revealed the actual
smoking gun:**

### REAL resolver coverage root cause (cavecrew, on-disk evidence)

**4 compounding bugs in `audit_trail/universal_pick_resolver.py`:**

| Line | Bug | Effect |
|---:|---|---|
| **695** | `PICK_OUTCOMES_MYSQL_ENABLED` env var gates entire MySQL write path; default OFF | Most production runs never reach the UPSERT — write path is dead code |
| **712** | UPSERT SQL targets table `at_signal_outcomes` | This table does NOT exist in `audit_trail/mysql_schema.sql` |
| **713-715** | INSERT column list omits `pick_id` (the PRIMARY KEY per `mysql_schema.sql:271-285 at_pick_outcomes`) | ON DUPLICATE KEY UPDATE can never match → all writes are either failed-silent or write to non-existent table |
| **800** | Bare `except Exception:` swallows every error silently | No log, no alert, no surfacing |

**`at_raw_picks` PRIMARY KEY = `id`** (mysql_schema.sql:30-65). No `signal_id`
column anywhere in the audit tables. DeepSeek's `signal_id→pick_id` theory
was directionally right (PK mismatch) but on the wrong column. Real fix is
correcting the **table name** + adding the **`pick_id` column to INSERT**.

### Smallest patch to lift 0.09% → ~95%

1. **Fix table name:** `at_signal_outcomes` → `at_pick_outcomes` in UPSERT
   (line 712).
2. **Add `pick_id` to INSERT column list** (line 713-715) + populate it
   from the resolved pick record.
3. **Replace bare `except Exception:`** (line 800) with `except Exception
   as e: logger.exception("resolver write failed", e); raise` (fail-loud
   per `feedback_check_env_before_claiming_missing` pattern).
4. **Set `PICK_OUTCOMES_MYSQL_ENABLED=1`** in `.github/workflows/audit-dashboard.yml`
   env block — OR remove the gate entirely. Currently the entire MySQL
   outcome-write path is gated off → outcomes never persist to canonical DB.

**Estimated lift:** 0.09% → ≥90% (resolves all closed picks that already
have JSON outcomes in `universal_resolved_picks.json` — that pathway works
fine per lines 1007-1062; only the **MySQL persistence** is dead).

**JSON resolution path IS working.** The `universal_resolved_picks.json`
output (lines 1007-1062) checks TP/SL/TIME_EXIT correctly. The 0.09%
figure in Kimi's broadcast refers specifically to **MySQL outcome
coverage** — the canonical ledger view (`pf_registry.json`,
`at_pick_outcomes`) is not getting populated because of the 4 bugs above.

**This means our canonical `pf_registry.json` numbers throughout this
session are computed on a JSON-side resolution that DOES work** — the
"99.91% unresolved" Kimi number applies to MySQL, not to our pf_registry.

So **partial walk-back on Kimi's K-P0-1:** the resolver is NOT entirely
dead. JSON-side works. MySQL-side is dead because of 4 compounding bugs.
The fix is mechanical — bug repair, not a redesign. Coverage lift after
fix should be near-complete because the data already exists in JSON.

## What this changes about the plan

### Real impact (must-fix P0)

1. **BUG-1 5 sites** — every DSR computation in the system can return a
   fake high DSR on degenerate input. Until patched, any T1 admission
   gated by DSR>0.95 is potentially false-positive.
2. **BUG-2 2 sites** — every PBO computation is information-leakage poisoned.
   PBO<0.05 gate is meaningless.

**Combined:** the Lopez-de-Prado-style institutional gate suite (the Grok
patch we received earlier) is **doubly blocked**:
- (a) by the 0.09% resolver coverage (input data invalid)
- (b) by these 2 bugs in the existing impl

### Action sequence

1. **Verify BUG-1 + BUG-2 via direct file read** (this MD already cites
   cavecrew evidence; one more sanity check before patching).
2. **Patch BUG-1 + BUG-2 across all 7 sites** in one PR. Add regression
   tests.
3. **Re-run DSR/PBO on existing mega_mutation n=58** — see if BUG-2
   embargo=0 was inflating its forward-confirm. If yes, mega_mutation
   verdict needs recompute under correct embargo.
4. **Resolver coverage fix** stays the #1 single-impact P0 (gates
   everything else).

## Companion docs

- `reports/KIMI_SWARM_VERIFICATION_2026-05-20T0200Z.md` (95e1f1f) —
  full Kimi 16-claim verification
- `swarm_runs/kimi_p0_code_audit_2026-05-20T0205Z/` — raw engine outputs
- `swarm_runs/_prompts/kimi_p0_code_audit_2026-05-20T0205Z.md` — prompt

## Lesson reinforced

**`feedback_multi_ai_convergence_trap.md`:** 2 of 3 cloud engines
(xAI + DeepSeek) confirmed BUG-3 + BUG-4 with invented line numbers. Only
cavecrew (grep ground truth) caught them. Future rule: any LLM "CONFIRMED"
on code patterns must be cross-checked with cavecrew or direct grep before
patching. Treat LLM line numbers as suspect until verified.

---

*Generated 2026-05-20T0215Z. cavecrew is the trusted truth-source for
on-disk code claims. No fabrication. 2 real fix targets (BUG-1, BUG-2), 2
hallucinations rejected.*
