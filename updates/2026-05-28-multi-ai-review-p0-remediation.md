# Multi-AI Review: P0 Incident Remediation .MD

**Reviewed by 6 AI models**: Grok (xAI), Ring 2.6 1T (InclusionAI), NVIDIA Kimi K2.6, Groq Qwen3-32B, Together Llama 3-8B, Fireworks Kimi K2p5

**Date**: 2026-05-28

---

## Consensus Verdict: ❌ NOT APPROVED — needs follow-up work

**5 of 6 models** (Grok, Ring, Kimi, Qwen, Llama) independently flagged the remediation as incomplete or unsafe for production. Fireworks Kimi was softer but raised the same concerns.

---

## Critical Issues (all models flagged)

### 1. 🔴 Documentation-Code Mismatch (Grok, Ring, Kimi, Qwen)
The `.MD` documents a two-pass NULL-safe dedup (2,195 + 368 = 2,563 rows removed), but the committed `tools/db_p0_integrity_remediation.py` contains different logic:
- Script uses `(category, strategy, symbol, direction, pnl_pct, created_at)` as dedup key
- Actual execution used `(symbol, direction, entry_price, created_at)` without pnl_pct
- The script still has the `asset_class`→`category` bug fix but doesn't match what ran

**Grok**: "Profound process failure — discrepancies erode trust in data integrity."
**Ring**: "Assumptions not empirically verified."
**Kimi**: "The NULL-safe join approach documented may have deleted rows with `NULL <=> NULL = TRUE` matching distinct trades."

### 2. 🔴 Dangerous Dedup — could delete legit picks (ALL models)
The dedup key `(symbol, direction, entry_price, created_at)` is too broad:
- Two different AI models could pick the same symbol at the same price at the same second
- Distinct trades with different exit_prices or pnl_pct would be collapsed
- No `DISTINCT exit_price` or `DISTINCT pnl_pct` pre-check was done

**Kimi**: "Validate with `COUNT(DISTINCT exit_price)` before deleting."
**Qwen**: "Rows with same params but different exit data could be mistakenly deleted."
**Grok**: "Material risk of destroying distinct, valid trade data."

### 3. 🔴 Incomplete Status Standardization (ALL models)
Only `WON` addressed. 139 rows with status `WIN` remain untouched.
Other non-canonical statuses (`LOSS`, `CLOSED`, `CLOSED_SL`, `CLOSED_TP`, `SIGNAL`, `FLAT`, `STALE`) not addressed.

**Ring**: "Significant gap. Must apply PnL-based relabeling consistently across ALL statuses."
**Qwen**: Provided specific SQL to audit and fix `WIN` rows.
**Grok**: "Inconsistent status taxonomy allows same contradictions to recur."

### 4. 🔴 No Backup/Rollback (Grok, Llama, Ring)
Destructive `DELETE` on the canonical performance ledger with no pre-delete backup.

**Grok**: "Hard requirement for modifying the performance ledger. Without backup, any error is unrecoverable."
**Llama**: "Recommend transactional approach with explicit rollback path."

### 5. 🟡 Dead Code in Script (Kimi, Qwen, Llama)
`CREATE TEMPORARY TABLE tmp_dedup` created but never used in the DELETE (uses inline subquery instead). Misleading and wasteful.

### 6. 🟡 No Prevention Measures (Grok)
No `UNIQUE` constraints, no insertion guards, no regression tests added to `db_health_check.py`.
The ghost-row problem is likely to recur.

---

## Recommended Next Steps (cross-model consensus)

1. **Reconcile documentation** — Update the .MD to match exactly what ran, with the actual SQL used and row counts
2. **Implement pre-delete backup** — `CREATE TABLE trading_picks_backup_YYYYMMDD AS SELECT * FROM trading_picks WHERE id IN (...)` before any future DELETEs
3. **Expand dedup key with safety** — Include `strategy` or source_system in the match to avoid collapsing distinct picks, and pre-check `COUNT(DISTINCT pnl_pct)` per group
4. **Standardize ALL statuses** — Sweep `WIN`, `LOSS`, `CLOSED`, `CLOSED_SL`, `CLOSED_TP`, `SIGNAL`, `FLAT`, `STALE` into a canonical set
5. **Clean up dead code** — Remove `tmp_dedup` or actually use it
6. **Add prevention** — `UNIQUE` constraints or `INSERT ... ON DUPLICATE KEY` guards, plus regression tests
7. **Post-remediation audit** — Compare live DB state with documentation; flag inconsistencies as P1

---

## Per-Model Quick Summaries

| Model | Verdict | Top Concern |
|-------|---------|-------------|
| **Grok** (xAI) | ❌ Not approved | Doc/code mismatch, no backup, dedup key too narrow |
| **Ring 2.6 1T** | ❌ Significant gap | Status standardization incomplete, row survival risk |
| **NVIDIA Kimi K2.6** | ❌ Not safe | NULL-safe join could match distinct trades, arbitrary DELETE |
| **Groq Qwen3-32B** | ❌ Needs work | Dedup criteria may delete legit picks, incomplete status sweep |
| **Together Llama 3-8B** | ❌ Risky | No rollback path, dedup columns too broad |
| **Fireworks Kimi K2p5** | ⚠️ Soft reject | Two-pass approach clever but risky, dead code smell |

---

## Bottom Line

The data issues were real and the intent was correct, but:
- The remediation was run as one-off scripts rather than through the committed, reviewed `db_p0_integrity_remediation.py`
- The .MD doesn't accurately reflect what ran
- No pre-delete backup exists for the 2,563 removed rows
- Status standardization is incomplete (139 WIN rows remain)
- No prevention measures were added

**The data is likely cleaner than before**, but the process gap needs closing before this is considered a production-quality remediation.
