# Next-Wave Audit Supplements — Cross-AI Review Synthesis

**Date:** 2026-05-02
**Plan reviewed:** `.tmp_research/next_wave_supplements_plan_2026_05_02.md` (3 candidates: A=Fama-MacBeth attribution, B=concept-drift canary, C=symbol-wise CV)
**Reviewers:** 3 internal subagents (skeptic, institutional-impact, opportunity-cost)
**Decision:** ship `tools/pick_notarizer.py` (tamper-evident forward record). Independent of resolver fix. 1-day cost. Highest credibility uplift per institutional reviewer.

## Reviewer #1 — skeptic (verdict: every candidate has a real blocker)

- **Cand A (Fama-MacBeth)** blocked by `outcome_resolver.py:384-405` returning `bar_date`-precision exit times only. Daily factor returns won't align with intraday crypto holds → biases β toward zero, inflates residual α. Killer.
- **Cand B (concept-drift)** blocked by the assumption that pick-emission features are in the payload. They aren't — `dashboard_payload.json` carries scoring outputs, not raw RSI/ATR/regime z-scores. ADWIN/Page-Hinkley needs feature provenance the audit doesn't ship.
- **Cand C (symbol-wise CV)** blocked by `smart_picks_engine.py:182` capping non-crypto at 5 picks/cycle → group-K-fold has n<10 per fold for equity/forex. Mis-flags legitimate specialists.
- **Just-shipped calibration limitation:** training labels regress on resolver-noise WIN/LOSS via the `PNL_WIN_THRESHOLD = 0.00001` legacy alias at `outcome_resolver.py:148` — calibrators for FOREX/COMMODITY/EQUITY are fitting noise, not realised edge. CRYPTO inversion is plausibly real (separate resolver path), but FOREX/COMMODITY/EQUITY calibrators must be re-fit after resolver fix lands.
- **Trust-tier interaction:** `_compute_ml_composite` applies `tier_penalty=0.3` for SANDBOX/UNTRUSTED *after* calibration. They stack multiplicatively. This is intended (calibration → honest P(win); tier penalty → "we don't trust this strategy yet"), documented in `confidence_calibrator.py` docstring.

## Reviewer #2 — institutional impact (rank by credibility uplift)

- A > C > B. But the dominant feature is none of A/B/C — it is **(d) tamper-evident forward records via signed pick hashes + git-tag / OpenTimestamps notarization.**
- "Allocators do not believe attribution, CV, or drift math computed by the same party that publishes the picks; they believe tamper-evident forward records. Everything else is decoration."
- Top 2 of the alternatives: (b) Bayesian Beta-Bernoulli posterior on per-strategy WR; (c) hypothesis pre-registration enforcement.

## Reviewer #3 — opportunity-cost (higher-leverage items the plan missed)

- **Resolver fix** (`outcome_resolver.py:97` + `:384-405`) is THE 1-day patch that beats every candidate. Unblocks 1,552 contaminated FOREX+COMMODITY picks. (Caveat: this is GH Actions cloud agent's Theme B, not mine to do.)
- **Kill 3 zombie strategies:** `goldmine_6x_consensus` (0% WR, n=17, -$60.4%), `quan_engine` (30.3% WR, n=314, -$118.2%), `forex_carry_momentum` (6.1% WR, n=66, -$32.2%). Strips negative carry from headline numbers.
- **Vol-target CRYPTO survivors** per `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md`. Already specced.
- Goal #2 (sports) and #3 (events) exclusion: correct call. Goal #1 has the 1,552-pick contamination.

## Synthesis & decision

The reviewers converge on three independent conclusions:

1. **The resolver fix is the prerequisite for everything quantitative.** It's GH Actions cloud agent's territory (Theme B). My contributions should be either (a) independent of resolver correctness, or (b) explicitly opt-in / flag-gated until the fix lands.
2. **The just-shipped calibration is partially built on contaminated labels.** CRYPTO inversion is plausibly real; FOREX/COMMODITY/EQUITY calibrators must be re-fit after resolver fix. Documented in the calibrator docstring (this commit).
3. **Tamper-evident forward records ((d)) dominate every quantitative supplement on credibility.** They commit a SHA-256 hash of `picks.active` to git history at every notarization, which is publicly timestamped by the GitHub commit graph. This works *regardless* of whether the resolver is correct, *regardless* of whether attribution is ever shipped, and *regardless* of whether DSR ever fires. It also gives the word "audit" in `findtorontoevents.ca/audit` an actual technical meaning.

## Shipped this commit

- `tools/pick_notarizer.py` — `notarize` / `verify` / `log` CLI. Hashes `picks.active`, `summary`, and `picks.recent_closed` with deterministic canonical JSON. Self-test verify roundtrip passes (PASS at git_sha bc9a8f4).
- `audit_trail/notary/notary_log.jsonl` — append-only log seeded with the first entry (n_active=41, n_closed=3500).
- `tests/test_pick_notarizer.py` — 8 tests covering canonical-JSON determinism, hash stability, mutation-sensitivity, isolated-section hashing, sha256 known-vector.
- `alpha_engine/confidence_calibrator.py` — added Known Limitations section in docstring (resolver-noise contamination, trust-tier interaction, drift-over-time).

## Wiring plan (follow-up PRs)

- Hook `python tools/pick_notarizer.py notarize` into `.github/workflows/audit-dashboard.yml` after the payload write step. Each hourly cron commit will append a notary entry.
- Surface `latest notary entry` block on `audit_dashboard/template.html` with the most recent SHA + a one-liner "How to verify". Public verification command.
- v2: anchor each notary entry into Bitcoin via OpenTimestamps. Removes the dependency on GitHub history integrity.

## Deferred (with reasons)

- Cand A (Fama-MacBeth): wait for resolver fix to give clean exit timestamps.
- Cand B (concept-drift): requires raw-feature payload extension; defer until pick emitters publish features.
- Cand C (symbol-wise CV): valuable for crypto-only strategies; defer until non-crypto cap at `smart_picks_engine.py:182` is lifted or analysis is restricted to n>=20 single-symbol strategies.
- Almgren-Chriss capacity column: multi-day, blocked on ADV/σ helpers.
- Payload anomaly canary: medium effort, touches CI cron — defer until the cloud agent stabilises.
