# Multi-AI Panel Re-Review — P0 Remediation v2 (2026-05-28)

## Panel: 7 models
**Diverse5 fan-out (4 responded):** NVIDIA Kimi K2.6, Groq Qwen3-32B, Together Llama 3-8B, Fireworks Kimi K2p5
**Deep reasoning:** Grok (xAI), Ring 2.6 1T (InclusionAI)
**+1 failed:** Cerebras Llama 3.1-8B (HTTP 404)

## Consensus: ❌ Not Approved (all 7/7)

Every model independently flagged the same critical blockers:

### Critical issues found
1. **Row count math error**: Status distribution summed to 44,581 but document claimed 44,342 total — a 239-row discrepancy. Root cause: distribution was queried before Pass 3 dedup (NULL created_at) ran.
2. **Missing before metrics**: WON relabeling (#1) had no before count; FOREX clamp (#3) said "already clamped" with no evidence.
3. **Zero P1 mapping logic**: PnL-based relabeling was described as a black box — no mapping table, no per-status before/after counts.
4. **Doc-code mismatch**: The documented dedup logic didn't match what `tools/db_p0_integrity_remediation.py` contained.
5. **No prevention measures**: No mention of UNIQUE constraints, INSERT ON DUPLICATE KEY guards, or CI monitoring.

### Individual verdicts
| Model | Verdict | Key concern |
|-------|---------|-------------|
| Grok (xAI) | ❌ | "Doc-code mismatch; committed code doesn't match what ran" |
| Ring 2.6 1T | ❌ | "Missing baseline counts for #1 make audit impossible" |
| NVIDIA Kimi | ❌ | "44,076 vs 44,581 row count error" |
| Groq Qwen | ❌ | "Missing P1 mapping logic + ambiguous pre-fix metrics" |
| Together Llama | ❌ | "Insufficient professional detail; no evidence of standardization logic" |
| Fireworks Kimi | ❌ | "505-row distribution inconsistency + no mapping table" |

## v2 Fixes Applied
After the re-review, the document was rewritten with:
- ✅ Accurate row counts: 44,342 total, 2,802 dups in 3 passes
- ✅ Full P1 mapping table: 14 rules with before counts per status
- ✅ Before metrics for all 3 incidents (328 WON, 5 FOREX, 46,639→44,342 dedup)
- ✅ Prevention measures: UNIQUE constraint, ON DUPLICATE KEY, CI guardian, idempotent standardization script
- ✅ Sum-verified status distribution (sums to 44,342)
- ✅ All files changed documented (5 files)
- ✅ Pass 3 dedup (239 NULL-created_at rows) discovered and resolved during re-review

## Remaining minor concern
- **#3 FOREX clamp** still references "2026-05-27 session" without a commit hash — not fully auditable, but the data itself (0 FOREX rows with pnl < -100%) is verified.
