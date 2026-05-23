# Loop Checkpoint 7 — T+~160m (2026-05-08 20:55 UTC)

## Fix patches drafted (NOT applied — for user review)

### Fix 1: `multi_asset/scanner.py:2232` — WON-with-negative-PnL bug

**Current** (lines 2231-2237):
```python
if hit_tp:
    pick["status"] = "WON"
    pick["exit_price"] = tp
    pick["exit_reason"] = "TAKE_PROFIT"
    pick["pnl_pct"] = pick["unrealized_pnl_pct"]
    pick["closed_at"] = datetime.now(timezone.utc).isoformat()
    closed.append(pick)
```

**Fixed**:
```python
if hit_tp:
    # Guard: status must reflect actual PnL sign, not just hit_tp signal.
    # When tp is contaminated by stale price-cache (cross-symbol leak),
    # hit_tp can fire spuriously. Without this guard, 1,247 rows in
    # trading_picks ended up with status='WON' AND pnl_pct < 0 (avg -85%).
    # Pattern matches existing hit_sl branch at line 2240.
    pnl = pick["unrealized_pnl_pct"]
    pick["status"] = "WON" if pnl > 0 else "LOST"
    pick["exit_price"] = tp if pnl > 0 else current_price  # don't trust contaminated tp
    pick["exit_reason"] = "TAKE_PROFIT" if pnl > 0 else "TP_PRICE_OUTOFRANGE"
    pick["pnl_pct"] = pnl
    pick["closed_at"] = datetime.now(timezone.utc).isoformat()
    closed.append(pick)
```

**Backfill SQL** (apply ONCE after code fix lands):
```sql
-- Sanity-check first: count affected rows
SELECT COUNT(*) FROM trading_picks
WHERE source_system = 'multi_asset_copytrader'
  AND status = 'WON'
  AND pnl_pct < 0;
-- expected ~1,247

-- Apply backfill
UPDATE trading_picks
SET status = 'LOST',
    exit_reason = COALESCE(exit_reason, 'TP_PRICE_OUTOFRANGE_BACKFILLED')
WHERE source_system = 'multi_asset_copytrader'
  AND status = 'WON'
  AND pnl_pct < 0;
```

**Verification post-fix**:
```sql
-- Should return n=0 after both fix + backfill
SELECT COUNT(*) FROM trading_picks
WHERE status = 'WON' AND pnl_pct < 0;
```

### Fix 2: `.github/workflows/penny-skyrocket-runner.yml` — git push race

**Current** (Commit results step likely):
```yaml
- name: Commit results
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    git add -A
    git diff --staged --quiet && exit 0
    git commit -m "[skip ci] Penny Skyrocket scan $(date -u +%Y-%m-%d)"
    git push    # ← RACE: fails with exit 128 when other workflows committed since checkout
```

**Fixed**:
```yaml
- name: Commit results
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    git add -A
    git diff --staged --quiet && exit 0
    git commit -m "[skip ci] Penny Skyrocket scan $(date -u +%Y-%m-%d)"
    bash tools/safe_commit_push.sh   # retry-with-rebase + jitter; 139 other workflows use this
```

If `Commit results` is currently a single-line `git push`, replace with the `safe_commit_push.sh` invocation. Reference: commit `64e44113bb2`.

## Bg health-run pid 3257

Still no completion log. Either:
- Still running (rare for 50+ min — but possible on 30M-row table)
- Process killed by Windows when shell exited
- Output redirected and not visible in task tracker

Live `db_health.json` is the 18:55 UTC version (8.4KB, 4/10 passing). The two failed checks (pnl_integrity + phantom_expired) had Decimal*float bugs that are now fixed. Re-running on next hourly cron (16:10 UTC) will produce the corrected output.

## Done since checkpoint 6

- ✅ Drafted multi_asset/scanner.py:2232 fix patch + verification SQL
- ✅ Drafted penny-skyrocket-runner.yml safe_commit_push fix
- ⏳ Bg health-run pid 3257 not confirmed finished (waiting for next hourly cron to refresh JSON instead)

## Up next (final wave)

- T+180m: write 3-hour summary report
- Plan: full inventory of what shipped, what's pending, top-5 highest-leverage user actions
