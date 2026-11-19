# Persist the audit3 denylist hit log (2026-11-19)

**Scope:** `alpha_engine/audit3_denylist_hits.py` (new),
`alpha_engine/feed_hygiene.py` (one hook), `tests/test_audit3_denylist_hits.py`.

## Why

The denylist fails **open** and is otherwise invisible. `forward_validator`
prints a drop count, but nothing records *which* picks were denied or *why*, so
the "one-week shadow review" cannot be performed: there is no data to review.

## What

`is_valid_active_pick` already calls `denied_reason(pick)`. When it denies, it now
appends one compact JSON line to `reports/audit3_denylist_hits.jsonl`:

```json
{"ts":"2026-11-19T13:45:00Z","strategy":"rsi_bounce","symbol":"BTCUSDT",
 "asset_class":"CRYPTO","direction":"LONG","source_system":"alpha_engine",
 "reason":"audit3 KILL: CRYPTO BTC LONG n=407 net=-0.84%/trade"}
```

Safety:
- append-only; past 5 MB it keeps the last 5,000 lines (no unbounded growth);
- honours the test kill switch `AUDIT3_DENYLIST_DISABLED` and
  `AUDIT3_DENYLIST_HIT_LOG=0`/`off` (or a custom path);
- wrapped in `try/except`: a logging failure can never block emission.

`summarize(path)` returns counts by strategy/symbol/class plus first/last
timestamp — the exact inputs for the weekly review.

## Verification

- `pytest tests/test_audit3_denylist_hits.py` -> 7 passed (write, no-reason, kill
  switch, env disable, summarize, missing file, rotation).
- End-to-end: with the committed ledger and a temp log path,
  `is_valid_active_pick(BTCUSDT LONG)` returns False and writes exactly one row.
- Regression: 160 passed, 1 skipped across the audit3 + hygiene + tier2 suites.

## How to run the weekly review

```bash
wc -l reports/audit3_denylist_hits.jsonl
python3 - <<'PY'
from alpha_engine.audit3_denylist_hits import summarize
import json; print(json.dumps(summarize(), indent=1))
PY
```
