# Stale OPEN picks — controlled batch resolve (2026-06-02)

## What ran

```bash
python3 tools/resolve_stale_open_picks.py --execute --max-batches 5 --batch-size 500
```

Resolved stale OPEN rows as `TIME_EXIT` per asset-class hold windows (`tools/resolve_stale_open_picks.py`).

## Result

- **OPEN count:** dropped from ~100k+ inflated backlog to **~3,806** (post-run health check).
- Top stale strategies cleared in this pass: `non_crypto_consensus`, `ig_contrarian_sentiment`, `prediction_market_consensus`, forex/commodity CTA sleeves, copy-trader PM rows, etc.

## Follow-up

- Re-run dry-run; if stale remains high, continue in slices:
  ```bash
  python3 tools/resolve_stale_open_picks.py --execute --max-batches 10 --batch-size 500
  ```
- Pair with hourly universal resolver on CI so OPEN rows close at TP/SL/time instead of accumulating.

## Capital

Unchanged — **NO-GO** production `/audit` sizing.
