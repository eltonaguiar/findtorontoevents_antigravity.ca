# Session Status — Audit Supplements (Claude Opus 4.7, peer broadcast)

**Date:** 2026-05-02
**Branch:** `audit-supplements-dsr-calibration-2026-05-02` (off origin/main)
**Commits:** `bc9a8f4` (calibration + DSR), `73a027ed` (notarizer + cross-AI synthesis)
**Tests:** 13/13 passing across `tests/test_confidence_calibrator.py` + `tests/test_pick_notarizer.py`
**Goal alignment:** Goal #1 (audit performance). Supplements to GH Actions cloud agent's plan, not duplicates.

## Completed action items

### Wave 1 — calibration + DSR (commit bc9a8f4)

1. **Per-class confidence calibration** wired into `alpha_engine/smart_picks_engine.py:_compute_ml_composite` behind `CONFIDENCE_CALIBRATION_ENABLED=1` env flag (default off).
   - Module: `alpha_engine/confidence_calibrator.py` (isotonic regression per asset class, JSON-serialized for dependency-free apply).
   - Fitted artifact: `alpha_engine/data/confidence_calibrators.json` (n=3,495 closed picks).
   - **Confirmed CRYPTO inversion:** high-conf WR 38.2% vs low-conf 41.8% on n=1514. ETF/EQUITY normal monotonic.
   - 5 smoke tests passing (no-op on flag-off, passthrough on missing class, mutation on fitted class, wire-up site spy).

2. **DSR with real trial count** — extended `tools/deflated_sharpe.py` internals.
   - Module: `tools/dsr_audit.py` (sidecar; reads `alpha_engine/data/dna_mutations.json` `summary.total_active_mutations` = 1213, vs naive N=209 strategies-with-picks).
   - Sidecar artifact: `tools/data/dsr_audit_results.json`.
   - Report: `reports/dsr_audit_with_real_N_2026_05_02.md`.
   - **Headline finding:** haircut saturates at SR≈3.88. Even at N=1M only 1 strategy gets deflated. The audit's observed Sharpes are so inflated that multiple-testing correction never bites — **the real bottleneck is upstream Sharpe inflation from the resolver bug, not multiple-testing**. This sidecar will be the canonical post-resolver-fix sanity check.

### Wave 2 — cross-AI review + notarizer (commit 73a027ed)

3. **Cross-AI plan review.** Drafted candidates A (Fama-MacBeth attribution), B (concept-drift canary), C (symbol-wise CV) in `.tmp_research/next_wave_supplements_plan_2026_05_02.md`. Dispatched 3 parallel review subagents (skeptic, institutional-impact, opportunity-cost). Synthesis at `reports/next_wave_review_synthesis_2026_05_02.md`.

4. **Pick notarizer** — tamper-evident forward record (highest-credibility-uplift supplement per institutional reviewer).
   - Module: `tools/pick_notarizer.py` (CLI: `notarize` / `verify` / `log`).
   - Append-only log: `audit_trail/notary/notary_log.jsonl`.
   - Hashes deterministically: `picks.active`, `summary`, `picks.recent_closed` (canonical-JSON, key-sorted, no-whitespace).
   - First entry seeded at git_sha `bc9a8f4` (n_active=41, n_closed=3500).
   - Self-test verify roundtrip: **PASS**.
   - 8 tests passing (canonical-JSON determinism, hash stability, mutation-sensitivity, isolated-section hashing, sha256 known-vector).

5. **Calibrator limitations documented.** Added Known Limitations section in `alpha_engine/confidence_calibrator.py` docstring: (a) training-label contamination via `outcome_resolver.py:148` legacy `PNL_WIN_THRESHOLD = 0.00001`; (b) trust-tier interaction (intentional, multiplicative stacking); (c) drift-over-time (re-fit cadence ≥ daily).

## Remaining action items (in priority order)

### High priority — independent of resolver fix

R1. **Wire `pick_notarizer notarize` into `.github/workflows/audit-dashboard.yml`** after the payload write step. Each hourly cron commit appends a notary entry to `audit_trail/notary/notary_log.jsonl`. Estimated cost: 30min.

R2. **Surface latest notary entry on `audit_dashboard/template.html`.** A small "Verify this audit page" block with the latest SHA + a one-liner verify command. Makes "audit" in the URL technically meaningful. Estimated cost: 1-2h.

R3. **Bayesian Beta-Bernoulli posterior on per-strategy WR** (institutional reviewer top-2 alternative). Replace point-estimate WR on the audit page with a credible interval; small-n strategies visibly shrink toward the prior. Estimated cost: 1 day.

R4. **Hypothesis pre-registration ledger** (institutional reviewer top-2 alternative). `audit_trail/preregistration/<strategy>.yaml` — target metric, threshold, sample size, holdout window — committed at strategy birth, hash-locked. Audit page only displays strategies whose forward results match pre-registration. Estimated cost: 2 days.

### Medium priority — depends on resolver fix landing

R5. **Re-fit calibrators after resolver fix.** Once `outcome_resolver.py:148` legacy `PNL_WIN_THRESHOLD` alias is removed and `:384-405` live-yfinance reuse is patched, re-run `python -m alpha_engine.confidence_calibrator fit`. FOREX/COMMODITY/EQUITY calibrators currently fit to noise; re-fit will give honest per-class scaling.

R6. **Re-run `dsr_audit` after resolver fix.** Inflated Sharpes will deflate; expect material change to "survivors" count. This is the validation step for whether the resolver fix actually moves the audit's headline numbers.

R7. **Candidate A (Fama-MacBeth attribution).** Blocked on intraday exit timestamps from `outcome_resolver.py:384-405`. Resume after resolver fix.

### Lower priority — bigger lifts

R8. **Almgren-Chriss capacity column** on audit page (per-strategy and per-pick `capacity_usd`). Multi-day. Blocked on missing ADV helper, σ on picks, λ calibration. See research notes from a262524c10e7a89fb.

R9. **Payload anomaly canary** on `audit_trail/data/dashboard_payload.json` via Isolation Forest over 30-day historical baseline. Medium effort. Touches CI workflow. See research notes from aed295f4780a0256d.

R10. **OpenTimestamps anchor for notary log entries.** Removes dependence on GitHub history integrity — proves timestamps to a third party even if repo is deleted. v2 of the notarizer.

### Explicitly deferred

- **Candidate B (concept-drift canary):** blocked on raw-feature payload extension — `dashboard_payload.json` only has scoring outputs.
- **Candidate C (symbol-wise CV):** blocked on `smart_picks_engine.py:182` non-crypto cap (5 picks/cycle → fold n<10).

## Coordination notes for peers

- I am NOT touching `outcome_resolver.py` — that's GH Actions cloud agent's Theme B.
- I am NOT touching the kill-list for zombie strategies (`goldmine_6x_consensus`, `quan_engine`, `forex_carry_momentum`).
- I am NOT touching vol-targeting (`reports/deep_dive_crypto_mdd_reduction_2026_04_28.md`).
- I noticed peer artifacts in `reports/feedback/` (`cerebras-qwen-strategy.md`, `deepseek-strategy.md`) and `reports/STRATEGY_PLAN_2026_05_02_NEXT_BLOCK.md` from a parallel session. Did not include in this commit.
- Branch is feature-only; no production cron / payload modifications. Safe to merge into main once peer reviewed.

## Files touched this session

```
alpha_engine/confidence_calibrator.py       (new module + Known Limitations docstring)
alpha_engine/data/confidence_calibrators.json (fitted artifact)
alpha_engine/smart_picks_engine.py          (15-line wire-up behind env flag)
audit_trail/notary/notary_log.jsonl         (new append-only log, 1 entry seeded)
reports/dsr_audit_with_real_N_2026_05_02.md (DSR human-readable report)
reports/next_wave_review_synthesis_2026_05_02.md (cross-AI review synthesis)
reports/SESSION_STATUS_2026_05_02_audit_supplements.md (this file)
tests/test_confidence_calibrator.py         (5 tests)
tests/test_pick_notarizer.py                (8 tests)
tools/data/dsr_audit_results.json           (DSR sidecar artifact)
tools/dsr_audit.py                          (DSR with N=1213)
tools/pick_notarizer.py                     (notarize / verify / log CLI)
```
