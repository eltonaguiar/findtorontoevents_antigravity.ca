# P0-B — Unified kill list on all writers (including backfill_local_sources)

**Priority:** P0 · **Date:** 2026-06-12  
**Evidence:** Part IV §39 — `futures_momentum` 94 emits/7d, `ig_contrarian_sentiment` 42/7d while `production_scanner` gates only apply to `trading_picks`; `backfill_local_sources.py` INSERT IGNORE bypasses `emitter_discipline`.

---

## Problem statement

Two emission surfaces → kills don't stick:

| Writer | Path | Gates today |
|--------|------|-------------|
| `production_scanner.py:4124-4127` | → `trading_picks` | `apply_source_ban_gate` + `apply_emitter_discipline` |
| `backfill_local_sources.py:189-209` | → `at_signal_outcomes` | **None** |
| `paper_trading/mysql_sync.py` | → various | Partial |

**Proof (7d SQL):** `forex_rsi2_mean_reversion` in `HARD_KILL_STRATEGIES` yet still emits via backfill path.

---

## Success criteria

1. **Zero** rows inserted into `at_signal_outcomes` in 7d for any `HARD_KILL_STRATEGIES` member (except explicit quarantine archive mode).
2. Single source of truth: `alpha_engine/emitter_discipline.py` imported by **all** writers.
3. Shadow log captures rejections when `EMITTER_DISCIPLINE_SHADOW_LOG=1`.

---

## Implementation plan

### Step 1 — Central gate function

Add to `alpha_engine/emitter_discipline.py`:

```python
def is_emission_allowed(strategy: str, source_system: str = "") -> tuple[bool, str]:
    """Returns (allowed, reason). Used by ALL writers."""
```

Export `HARD_KILL_STRATEGIES`, `BANNED_SOURCES` union, and new additions:

| Strategy | Why add |
|----------|---------|
| `futures_momentum` | 94 emits/7d, not in HARD_KILL |
| `ig_contrarian_sentiment` | BANNED_SOURCES only |
| `stocks_rsi2_pullback` | 20 emits/7d |
| `prediction_market_consensus` | WR 26%, Σ−29% intrabar |
| `rsi_bounce` | WR 20%, Σ−49% |
| `bollinger_squeeze` | WR 4.3%, dead |
| `fx_smart_carry_trade_momentum` | FOREX WR 16.7%, Σ−6.6 |

### Step 2 — Wire backfill_local_sources.py

Before `insert_outcome()` and `insert_pick()`:

```python
from alpha_engine.emitter_discipline import is_emission_allowed
allowed, reason = is_emission_allowed(strategy, source_system)
if not allowed:
    continue  # or shadow-log
```

File: `audit_trail/backfill_local_sources.py:167-213`

### Step 3 — Wire outcome-resolver.yml path

GHA step at `.github/workflows/outcome-resolver.yml:154-165` runs backfill — same gate applies automatically once Step 2 lands.

### Step 4 — Audit existing rows (non-destructive)

Do **not** DELETE historical rows. Add quarantine flag:

```sql
-- reporting only: exclude from aggregates via view or generator filter
WHERE strategy NOT IN (/* HARD_KILL list */)
  OR opened_at < '2026-06-12'  -- grandfather clause optional
```

Prefer generator-side filter in `build_intrabar_truth_by_class.py` + `money_ready_verdict.py`.

### Step 5 — Tests

`tests/test_emitter_discipline_unified.py`:

- Mock insert path for backfill; assert killed strategy skipped.
- Assert `futures_momentum` blocked.

---

## Rollback

Set `EMITTER_DISCIPLINE_ENFORCE=0` (existing env kill-switch in emitter_discipline.py:29-31).

---

## Verification

```bash
# 7d emission audit
python3 - <<'PY'
# query at_signal_outcomes WHERE strategy IN HARD_KILL AND created_at > NOW()-7d
PY
# Expect 0 after deploy
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| Legitimate backfill of historical closed JSON | Gate applies to **new** inserts only; historical preserved |
| Strategy rename drift | Single set in emitter_discipline; grep CI check |

---

## Cross-ref

- **Ship with P0-C in same PR** (swarm/kilo): LONG block without backfill direction gate leaves polluted intrabar book.
- P1-B auto-kill tribunal automates **future** kills from intrabar metrics.
