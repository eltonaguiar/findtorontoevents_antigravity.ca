# P0-A — Hourly intrabar reresolve + stamp + truth refresh

**Priority:** P0 · **Owner:** audit-dashboard pipeline · **Date:** 2026-06-12  
**Evidence:** `CURSOR_JUNE112026.MD` Part III §23–§28; forward lane stalled since 2026-06-10 noon (1,553 batch backfill, 0 live accrual after).

---

## Problem statement

The honest measurement book (`at_signal_outcomes.intrabar_*`) is the **only** ledger the master loop trusts for promotion/kill decisions. Today:

| Component | Status |
|-----------|--------|
| `universal_pick_resolver.py` (hourly GHA) | Resolves **`trading_picks`** only; does **not** write intrabar shadow cols |
| `reresolve_intrabar_signal_outcomes.py` | **Only** writer of intrabar cols; **not in any GHA workflow** |
| `stamp_entry_conditions.py` | Wired in `audit-dashboard.yml:554` but reads **already-resolved** intrabar rows — useless if reresolve stalls |
| `build_intrabar_truth_by_class.py` | Manual / ad hoc; not hourly |

**177,794** unresolved `at_signal_outcomes` rows; CRYPTO coverage **1.63%**. Forward checkpoints (`crypto_rsi5070_us`, `forex_trend_aligned`) cannot accrue n without continuous reresolve.

---

## Success criteria

1. **≥50 new intrabar resolutions per hour** on average (bounded by `--max 500`).
2. `entry_conditions_forward.json` `generated_at` advances every hourly run.
3. `money_ready_verdict.json` → `classes.*.intrabar_truth.n` increases week-over-week.
4. Freshness gate: RED banner if **zero** new `intrabar_resolved_at` rows in 48h (see P0-A gate below).

---

## Implementation plan

### Step 1 — Add GHA steps after resolver, before `stamp_entry_conditions.py`

File: `.github/workflows/audit-dashboard.yml` (after universal resolver step, ~line 520–555)

```yaml
      - name: Intrabar shadow resolution (at_signal_outcomes)
        env:
          DB_PASS_STOCKS: ${{ secrets.DB_PASS_STOCKS || secrets.MYSQL_PASSWORD }}
        run: |
          python3 tools/reresolve_intrabar_signal_outcomes.py \
            --apply --i-understand-this-mutates-production \
            --max 500 \
            || echo "intrabar reresolve warning (non-fatal)"
          python3 tools/build_intrabar_truth_by_class.py \
            --stdout > audit_dashboard/data/intrabar_truth_by_class.json \
            || echo "intrabar truth build warning (non-fatal)"
```

**Ordering:** resolver → **reresolve** → **build_intrabar_truth** → stamp → money_ready_snapshot → pf_registry → dashboard_generator.

### Step 2 — Idempotency + caps

- Default `--max 500` keeps hourly job under ~90s DB load (dry-run showed ~1.5s/row worst case → cap protects GHA timeout).
- Script already skips `intrabar_resolved_at IS NOT NULL` rows — safe to rerun hourly.
- Add `--since-days 90` default (already in script) unless `--all-time` dispatch input.

### Step 3 — Freshness gate (ties to P1 monitoring)

New check in `tools/db_freshness_check.py` or extend existing:

```sql
SELECT MAX(intrabar_resolved_at) AS last FROM at_signal_outcomes
WHERE intrabar_resolved_at IS NOT NULL;
```

Fail CI warning if `last < NOW() - INTERVAL 48 HOUR`.

**Swarm addendum (deepseek):** If hourly reresolve resolves **<5% of attempted batch** (e.g. `<25` of 500), fail the step explicitly — do not rely on `|| echo warning` alone (kilo: silent partial failure risk).

### Step 4 — Dashboard surfacing

- `audit_dashboard/template.html`: show `intrabar_truth.generated_at` + last reresolve timestamp in MEASURE panel.
- `pick_funnel.html`: already documents intrabar_truth — add “last shadow resolve” cell.

---

## Rollback

Remove the two python lines from GHA; shadow columns are additive — no canonical data mutation.

---

## Verification

```bash
# Pre-merge dry-run
python3 tools/reresolve_intrabar_signal_outcomes.py --max 50
python3 tools/build_intrabar_truth_by_class.py --stdout | head

# Post-deploy (48h)
mysql -e "SELECT DATE(intrabar_resolved_at) d, COUNT(*) FROM at_signal_outcomes
  WHERE intrabar_resolved_at >= NOW()-INTERVAL 7 DAY GROUP BY d ORDER BY d DESC LIMIT 7;"
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| GHA timeout | `--max 500`; increase only after timing profile |
| OHLC gaps (FOREX/COMMODITY) | Existing replay flags `intrabar_ambiguous`; stamp excludes ambiguous |
| Duplicate hourly + manual runs | Idempotent NULL-only apply |

---

## Dependencies

- DB creds on audit-dashboard step (already fixed 2026-06-10 for money_ready_snapshot).
- `crypto_ohlcv` / `stock_ohlcv` tables populated (outcome-resolver.yml).

---

## Not in scope

- Migrating `trading_picks` to intrabar (separate “single book” initiative — P1-A).
