# PEAD earnings loader: enforce max_age_days + safer guidance default

## What was broken

Swarm review of PR #547 found `max_age_days` was never applied (stale earnings could enter PEAD), and `assume_guidance_on_beat=True` fabricated `guidance_raised` on every beat.

## What changed

- Filter earnings rows to `now - max_age_days` (default 14).
- Default `assume_guidance_on_beat=False`; opt in only for shadow when filings lack guidance flags.

## Verify

```bash
python3 -m pytest tests/test_equity_earnings_loader.py -q
```