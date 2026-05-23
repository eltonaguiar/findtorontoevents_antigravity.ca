# Agent B — Crypto LONG Score≥65 Promotion Gate (verification-only)

## Task
Verify the claimed "Crypto LONG Score≥65: PF 4.47 on 186 trades, ~60.8% WR" edge pocket on the current ledger. If verified, implement a soft promotion gate in crypto curation. If NOT verified, ship only the diagnostic and flag the discrepancy.

## PR
**#158** — `feat(crypto-score-promotion): diagnose claimed PF 4.47 edge pocket`
Merged: diagnostic only. No promotion gate was wired (verification failed — see Findings).

## Files modified / added

### New files
- **`tools/calibration/score_band_edge.py`** — stdlib-only diagnostic that buckets crypto LONG picks by score and computes WR / PF / Wilson 95% CI per bucket. Auto-selects the most-populated score field among `score` / `final_score` / `elite_score` / `smart_score`. Reuses `tools.data_integrity._common` for ghost filtering + asset classification. Exit code 0 iff the combined [65+] bucket Wilson lower bound ≥ 0.50 with n ≥ 30; exit 2 otherwise.

- **`tests/test_score_band_edge.py`** — 9 unit tests covering:
  - Wilson CI math (boundary cases + n=100 sanity)
  - Bucket boundary inclusion/exclusion
  - Score-field auto-selection prefers the most-populated field
  - Non-crypto / SHORT / ghost-row filtering
  - PF + expectancy math on synthetic ledgers
  - Exit code contract: weak ledger → 2, strong ledger → 0, undersized → 2
  - JSON output shape

- **`tools/calibration/out/.gitignore`** — keeps generated `score_band_edge.json` untracked.

### Untouched (explicit scope guardrail)
- No changes to `non_crypto_agent/main.py`, `alpha_engine/smart_picks_engine.py`, `cross_aggregation/aggregator.py`, or any curation path. A promotion helper was NOT created because the verification failed — see Findings.

## Why

The session's core thesis from independent analysis: compound filters like "Crypto LONG Score≥65" carry real edge (claimed PF 4.47, n=186) even when the overall system is losing (Monte Carlo PR #157 found system-wide bootstrap 95% CI [-0.163%, -0.130%] on expectancy). If the pocket edge is real, it should be promoted; if not, the claim is a data artifact that would have poisoned downstream curation.

This PR is the **verification step** before any promotion work. The guardrail was explicit: "if the real data shows bucket [65+] is NOT confidently profitable (Wilson lower bound < 0.50), STOP and report — do NOT ship the promotion gate based on a claim that doesn't reproduce."

## Findings (live data)

Ran against `alpha_engine/data/closed_picks.json` (4,157 rows, ghost-filtered). `elite_score` was the only populated score field — `score` / `final_score` / `smart_score` all 0-populated.

| Bucket | n | WR | Wilson 95% CI | PF |
|---|---|---|---|---|
| `<50` | 2,350 | 33.91% | [32.03%, 35.85%] | 0.40 |
| `[50, 65)` | 362 | 48.07% | [42.97%, 53.21%] | 0.60 |
| **`[65, 80)`** | **38** | **15.79%** | **[7.44%, 30.42%]** | **0.36** |
| `[80, 100]` | 0 | — | — | — |

**The claim does NOT reproduce.** The Wilson **upper bound** for the combined [65+] bucket is **30.42%** — well below the 50% lower-bound threshold required for promotion. The `[65,80)` bucket is actually the WORST-performing, not the best.

PF 4.47 vs PF 0.36 is a 12× discrepancy — not a small sample noise issue. The claim likely came from:
- A different score field (candidates: `method_a_score`, `ml_composite_score`, `strategies_agreed`)
- A different data source (e.g., `audit_dashboard/data/claudes_test_state.json`, `audit_trail/data/universal_resolved_picks.json`)
- A walk-forward train window that got reported as if it were forward performance
- Selection bias (filter was chosen after seeing outcomes)

## Verification
- `python -m py_compile tools/calibration/score_band_edge.py tests/test_score_band_edge.py` → clean
- `pytest tests/test_score_band_edge.py -q` → **9 passed**
- Ran against live `closed_picks.json` → exit code 2 (correctly flagging failed verification)

## Scope guardrails honored
- ✅ Did NOT ship the soft-boost promotion gate (the [65+] bucket is not confidently profitable)
- ✅ Did NOT modify DXY (#124) / VIX (#133) / MTF-RSI (#138) / ETF RS (#136) / SL floor (#144) gates
- ✅ Did NOT modify strategy function bodies
- ✅ Wrote the diagnostic alongside the verification so the claim can be re-tested later against a different score field or ledger

## Follow-ups recommended
1. **Re-run the diagnostic against each candidate score field** (`method_a_score`, `ml_composite_score`, `strategies_agreed`) and the alternate ledgers to locate the original PF 4.47 claim's actual source.
2. **Same diagnostic on `universal_resolved_picks.json` and `claudes_test_state.json`** — given the 0.61% overlap between ledgers (PR #145 finding), pocket edges may only live in one of them.
3. If the claim reproduces against ANY (score, ledger) combo, re-open this PR with the promotion helper.

## Related session PRs
- **#135** — Symbol PF tier boost (same soft-boost pattern)
- **#145** — `tools/data_integrity/_common.py` (reused for ghost filter + asset classification)
- **#157** — Monte Carlo baseline (why pockets matter when the overall system is negative)
