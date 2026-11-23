# Blockers, 2026-11-22

Recorded per program instruction: a blocked step is documented, not silently skipped or fabricated.

## B1. AI peer fan-out unavailable (Phase 2b/2c)

Measured with `python3 tools/consult_multi.py --doctor` at 2026-11-22T06:42Z:

| provider | status |
|---|---|
| cloudflare | OK |
| nvidia | HTTP 410 Gone |
| groq | HTTP 404 (model not found) |
| cerebras | HTTP 404 |
| together | HTTP 401 Unauthorized |
| fireworks | HTTP 404 |
| github_models | DNS failure |
| huggingface | empty completion (quota/refusal) |
| gemini_api | timeout |
| deepinfra | HTTP 429 |
| nous | HTTP 404 |
| mistral | HTTP 429 |
| aimlapi | HTTP 403 |
| hypereal | HTTP 402 |

Summary: 1/14 providers answered. Consequences:

- `--fanout diverse5` needs nvidia, cloudflare, groq, gemini, cerebras → 4/5 unavailable.
- `--fanout reasoning4` needs nvidia, gemini, together, fireworks → 0/4 available.
- Therefore **delegated drafting** and the **mandatory two-model adversarial pass** could not be
  performed as specified. Dossiers are written by the curator (Measurer role) from frozen
  evidence, and their provenance footer says so. Where a review could be run on the single live
  provider, it is recorded in `REJECTED.md`.
- No dossier claims an AI review it did not receive.

## B2. Web paths referenced by pages that 404

- `/audit/audit3.html` → 404 (measured)
- `/audit2/audit3_ledger.json`, `/audit2/reports/forward_observations.json` → 404
- `/audit3/reports/audit3_confirmatory.json`, `/audit3/reports/forward_observations.json` → 404
- `/audit_dashboard/data/money_ready_verdict.json` → 404 (the live page reads `/audit/data/money_ready_verdict.json`, which is 200)

## B3. `/audit/data/audit2_forward.json` is stale

Generated 2026-11-21T08:37Z, 22 hours behind the `/audit2/` copy (2026-11-22T06:35Z).
Numbers read from the `/audit/data` copy are labelled stale in the dossiers.
