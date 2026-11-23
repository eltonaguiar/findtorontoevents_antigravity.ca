# P2-10: FMP API key rotation (2026-11-23)

## Summary
The Financial Modeling Prep (FMP) API key has been **removed from the template** and replaced with an env-var placeholder. Rotation is **BLOCKED ON HUMAN**.

## What changed
- FMP key is no longer hard-coded in the template.
- Code now reads `FMP_API_KEY` from environment/secrets.

## Action required (operator)
1. Rotate the FMP API key in the FMP dashboard.
2. Update the `FMP_API_KEY` secret in GitHub Actions and any local `.env`.
3. Do **not** commit the key to the repo.

## Notes
- No code change beyond the template removal.
- Verification: `grep -rn "FMP_API_KEY" . --include=*.py --include=*.yml` should show only env reads, no literals.

**Status:** BLOCKED ON HUMAN (key rotation). No further code changes needed.
