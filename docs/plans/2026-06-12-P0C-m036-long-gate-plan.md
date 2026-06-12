# P0-C — Extend M-036 to LONG (block unproven CRYPTO LONG until forward proof)

**Priority:** P0 · **Date:** 2026-06-12  
**Evidence:** Part V §47 — CRYPTO LONG n=1,050 WR **30.1%** Σ−503%; SHORT n=104 WR **55.8%** Σ+39. M-036 blocks `BUY` only; DB stores `LONG`.

---

## Problem statement

```427:429:alpha_engine/config.py
CRYPTO_BLOCKED_DIRECTIONS = frozenset({"BUY"})
```

Intrabar ledger uses `LONG` for 91% of CRYPTO trades. The documented anti-predictive direction (M-036: BUY PF=0.38 / WR=28.9%) was never applied to the label actually written.

**This is the largest PnL leak in the book** — not mercury2 ensemble, not measurement.

---

## Success criteria

1. New CRYPTO LONG emissions drop to **zero** in production (or probation-only shadow) until forward lane proves LONG edge.
2. Existing SHORT / luxalgo_confluence path continues.
3. Intrabar forward slice `crypto_short_only` accrues n with WR above geometry BE.

---

## Implementation options (pick one for v1)

### Option A — Hard block LONG (recommended for P0)

```python
CRYPTO_BLOCKED_DIRECTIONS = frozenset({"BUY", "LONG", "STRONG_BUY"})
```

Wire in `audit_trail/quality_gates.py:7218` (existing M-036 import path) **and** `production_scanner.py` pre-emit.

**Pros:** Immediate stop-bleed. **Cons:** Reduces volume; may miss luxalgo LONG edge.

### Option B — Probation whitelist (luxalgo only)

Block LONG unless `strategy in {"luxalgo_confluence"}` AND `ml_score >= MIN_ML_SCORE_CRYPTO`.

**Pros:** Preserves only intrabar-proven sleeve (WR 50.5%, n=93). **Cons:** More code; whitelist maintenance.

### Option C — Regime-conditional LONG

Allow LONG only when `regime_at_entry in {risk_off, funding_negative}` (from stamp F3/F5).

**Pros:** Aligns with SHORT working in bearish regimes. **Cons:** Needs stamp wired first (P0-A).

**Recommendation:** **Option A now** (hard block LONG). **No luxalgo LONG whitelist** — swarm consensus + `quality_gates.py:1561` shows luxalgo LONG penalty (−10, ~35% WR); edge is SHORT-side per inverse_system.

---

## Implementation plan

### Step 1 — config.py

Extend `CRYPTO_BLOCKED_DIRECTIONS` per Option A or B.

### Step 2 — quality_gates.py

Ensure gate normalizes direction:

```python
dir_u = (direction or "").upper()
if asset_class == "CRYPTO" and dir_u in CRYPTO_BLOCKED_DIRECTIONS:
    return False, "M-036b_crypto_long_blocked"
```

### Step 3 — backfill_local_sources.py

Apply same direction gate on `insert_outcome` for CRYPTO rows (ties to P0-B).

### Step 4 — Forward experiment

Pre-register in `reports/hypothesis_registry.json`:

- H-2026-06-12-crypto-short-only: promote if n≥100, WR≥50%, PF≥1.5 on intrabar SHORT cohort.

### Step 5 — Dashboard honesty

`/audit` banner: “CRYPTO LONG emissions frozen 2026-06-12 — intrabar WR 30.1% (n=1050).”

---

## Verification

```bash
# After deploy: 7d emission check
SELECT direction, COUNT(*) FROM at_signal_outcomes
WHERE asset_class='CRYPTO' AND opened_at > NOW()-7d
GROUP BY direction;
# Expect LONG=0 (Option A)
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| luxalgo LONG killed | Option B whitelist |
| Tournament picks still LONG | Extend gate to tournament ingest path |
| User expects long-only crypto culture | Document in pick_funnel + updates card |

---

## Expected impact

Counterfactual from Part V: SHORT-only cohort Σ+39% vs actual Σ−463%. Does not guarantee future SHORT edge (n=104) but **stops −503% LONG bleed** immediately.

---
## ⚠️ MASTER-LOOP REVIEW NOTE (claude-fable, 2026-06-12 — REQUIRED reading before implementing)
The M-036 BUY-vs-LONG label gap is CONFIRMED (14d live: LONG=1,227 vs BUY=335 — the existing block misses ~79% of long-side emissions). The diagnosis stands. **BUT Option A as written conflicts with the master loop's forward lanes:** a blanket LONG block also stops the shadow/measurement picks that feed `crypto_rsi5070_us` (LONG-dominant; pre-registered checkpoint 2026-06-25 n≥150) and the `crypto_eu_us_handoff LONG` forward observation (2026-07-09). Killing LONG emission entirely starves both of forward n and breaks two pre-registered checkpoints.
**REQUIRED amendment to any implementation:** the LONG block applies to the SIZED lane only — picks with `forward_test_only`/shadow markers MUST be exempt (mirror the Option-A cap exemption pattern in `alpha_engine/non_crypto_policy.py::is_daily_cap_reached`). Option C (regime-conditional) is the better v2 once P0-A stamps land. Run `tools/loop_preflight.py --stage promotion` semantics: stop the bleed where money is at stake, keep the measurement flowing.
