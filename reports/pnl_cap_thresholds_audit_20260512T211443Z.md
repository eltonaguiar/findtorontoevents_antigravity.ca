# PnL Cap Thresholds Audit — 2026-05-12T21:14:43Z

**Spec:** P0-#3 prerequisite per 4-engine swarm Q4 unanimous
`REVIEW_FIRST` — review cap thresholds before any disclosure UI ships.

## Active cap layers (writer-side, read-side, summary-side)

### Layer 1 — Ingest writer clamp (`audit_trail/pnl_ingest_sanity.py`)

| Asset class | Min pnl_pct | Max pnl_pct | Rationale |
|---|---|---|---|
| CRYPTO, MEME | -99.0% | +500.0% | Allow wide tails (micro-cap pumps); reject impossible -100%+ wipeout |
| EQUITY, FOREX, ETF, BOND, FUTURES, COMMODITY, UNKNOWN | -100.0% | +200.0% | Single-trade beyond this is data corruption per RCA 2026-04-21 (pip-vs-percent or bad price stamp) |

**Where applied:**
- `dashboard_generator.py:6966` (`_normalize_pick`) — every closed pick on the dashboard build path
- `audit_trail/outcome_resolver.py` (writer-side, mysql_sync 2026-05-09 / PR #876)
- Output field: `pnl_pct_ingest_clamped: True` + `pnl_pct_pre_clamp` preserved

### Layer 2 — Read-side system-level cap (`dashboard_generator.py:9304`)

| Constant | Value | Scope |
|---|---|---|
| `MAX_PNL` | 500.0 | Per-pick PnL clamp before adding to `total_pnl` and `pnl_series` — applies AFTER ingest clamp to handle legacy uncleaned rows |

Outcome: any single pick contributing >500% (after ingest) is logged
and capped. Affects `systems[].total_pnl_pct`, `pnl_series` (used for
MDD), per-symbol PnL aggregates.

### Layer 3 — Read-side MDD-element clamp (`dashboard_generator.py:9413`)

```python
# 2026-05-11 SUPREME EDGE P0 #7: clamp each pnl element to [-100, 200]%
# on READ before cumulating. PR #876 added writer-side clamp in mysql_sync
# 2026-05-09 but legacy rows pre-clamp can emit -106,700% (FOREX unit
# corruption) which compounds into a 680% MDD per Kimi audit.
```

**Hardcoded `[-100, 200]` on EVERY class** at the cumulative MDD step.
Note: this overrides Layer 1's class-aware CRYPTO ceiling (500%) for
the MDD computation only — a CRYPTO single-trade legit +400% would
be truncated to +200% for MDD purposes.

### Layer 4 — Summary-level cap (`dashboard_generator.py:13243-13288`)

| Constant | Value | Scope |
|---|---|---|
| `_MAX_PNL_SUMMARY` | 500 | Same as Layer 2 but applied at `summary` aggregate level (overview tab numbers) |
| `_MAX_PNL_COMPOUND` | 2 | Bound for compound-mean computation (max 200% per element) |

### Layer 5 — Per-class concentration aggregator (`dashboard_generator.py:5444`)

```python
def _compute_closed_pnl_concentration_by_source(
    resolved_closed: list, max_pnl_cap: float = 500.0
```

500% per-pick cap when computing class-level PnL concentration shares.

## Inconsistencies surfaced

| # | Class | Layer 1 (ingest) | Layer 2/4 (read) | Layer 3 (MDD) | Conflict? |
|---|---|---|---|---|---|
| 1 | CRYPTO | +500% | +500% | **+200%** | Layer 3 caps CRYPTO tighter than ingest; legit 300% crypto pump shows up correctly in total_pnl but is silently clipped from MDD denominator |
| 2 | FOREX | +200% | +500% | +200% | Ingest is tighter than read-side Layer 2 — but legacy unclamped rows can still slip up to 500% on total_pnl before Layer 3 catches them for MDD only |
| 3 | EQUITY | +200% / -100% | +500% | +200% / -100% | Same as FOREX |
| 4 | All | NO MIN ENFORCEMENT IN LAYER 2 | symmetric ±500% | -100% min | Layer 2 allows -500% on a non-crypto class even though ingest blocks at -100%; if ingest is bypassed (resolver path bug), Layer 2 lets -500% propagate to total_pnl |

## Concrete impact (Kimi 680% MDD anomaly)

Per `dashboard_generator.py:9413-9417` comment block: legacy FOREX rows
emitted `-106,700%` pre-clamp. Layer 1 (ingest) catches new writes,
but legacy rows existed before the writer-side fix. Layer 3's
hard-coded `[-100, 200]` defends MDD downstream. Without Layer 3,
MDD compounds into 680%.

**Verdict:** Layer 3's hard-coded `[-100, 200]` is doing real work but
also silently clips legitimate CRYPTO tails for MDD only. Different
caps for MDD vs total_pnl produce **discoverable but unsurfaced** gaps:

```
crypto_winners system:
  total_pnl_pct (Layer 2, +500% cap):  +900
  cum_pnl_series for MDD (Layer 3, +200% cap):  +540
  Implicit gap: +360% pnl "exists" but doesn't show up in MDD denominator
```

The Codex prescription `capped_vs_raw_pnl_gap` field would surface this.

## Recommendations for P0-#3 disclosure UI

1. **DON'T change cap values** — they exist for real failures (FOREX
   unit corruption, micro-cap pump rows). Risk-cap re-tuning is a
   separate workstream needing fresh per-class outlier RCA.

2. **DO emit `capped_vs_raw_pnl_gap` field** per system + per class:
   ```
   systems[i].capped_vs_raw_pnl_gap = {
     "total_pnl_uncapped": float,  # before Layer 2
     "total_pnl_capped": float,    # after Layer 2 (current behavior)
     "gap_pct": float,             # difference as % of capped
     "n_picks_clamped": int,       # how many rows hit a cap
   }
   ```

3. **DO disclose Layer 3 vs Layer 2 mismatch** — if a system's MDD
   denominator was clipped tighter than its total_pnl, the Calmar
   ratio is inflated. Surface `mdd_cap_applied: True` + the gap.

4. **DEFER UI work until #2 + #3 land** — disclosure of a phantom
   gap is worse than no disclosure.

## What this audit changes

- The original P0-#3 plan (write disclosure UI directly) is now
  conditionally blocked. UI build SHOULD happen, but only after the
  payload fields (`capped_vs_raw_pnl_gap`) are emitted by
  `dashboard_generator.py`.
- This unblocks the swarm Q4 unanimous prerequisite.

## Reproducer

```bash
grep -nE "MAX_PNL|_PNL_CLAMP_|max_pnl_cap|capped_pnl|clamp_pnl_pct_for_pick" \
  audit_trail/pnl_ingest_sanity.py audit_trail/dashboard_generator.py
```

## NFA

Research surface only. No code changes in this audit.
