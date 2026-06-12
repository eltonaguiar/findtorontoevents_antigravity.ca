# P1-A — Verdict / UI only from intrabar; freeze pf_registry WR for promotion

**Priority:** P1 · **Date:** 2026-06-12  
**Evidence:** Part V §49 — FOREX pf_registry WR **57.4%** vs intrabar **42.0%** (19 pp gap). CRYPTO pf_registry WR **51.5%** vs intrabar **32.4%**.

---

## Problem statement

PM committee argues from different books:

| Surface | CRYPTO WR | FOREX WR | Source |
|---------|-----------|----------|--------|
| `pf_registry` policy_clean | 51.5% | 57.4% | Mixed resolver / tournament DB |
| `intrabar_truth` | 32.4% | 42.0% | First-touch TP/SL shadow |
| `trading_picks` Jun+ | ~48% | varies | Entry-anchored resolver |

`money_ready_verdict.py` currently shows **both** — `wr`/`pf` from policy-clean AND `intrabar_truth` block. Gates like `wr_ok` can pass on policy-clean while intrabar fails.

---

## Success criteria

1. **Promotion / Money Ready button** uses **only** `intrabar_truth` for WR, PF, n.
2. UI tiles label policy-clean as “legacy / discovery” (greyed, not sized).
3. No class displays pf_registry WR in green without intrabar corroboration when n_intrabar ≥ 30.

---

## Implementation plan

### Step 1 — money_ready_verdict.py gate reorder

File: `alpha_engine/money_ready_verdict.py`

For each class:

```python
truth = intrabar_truth or {}
n = truth.get("n") or 0
wr = truth.get("wr")
pf = truth.get("pf")
# wr_ok = wr >= 0.50 if n >= 100 else False  # ONLY from intrabar when n>=30
# Fall back to policy-clean ONLY when intrabar n < 30 with explicit flag
```

Add field: `"sizing_source": "intrabar_truth" | "insufficient_intrabar" | "legacy_fallback"`.

### Step 2 — dashboard_generator.py

- `asset_class_health` card: primary numbers from `money_ready_verdict.classes.*.intrabar_truth`.
- Secondary line: `policy_clean (discovery only): WR X% — may disagree`.

### Step 3 — template.html + pick_funnel.html

- Money Ready filter JS (`money_ready_filter.js`): read intrabar WR/PF keys only.
- Remove dual-headline cells that cite pf_registry without disclaimer.

### Step 4 — pf_registry build flag

`tools/build_pf_registry.py`: add `"display_tier": "discovery"` metadata on all rows.

Optional env: `PF_REGISTRY_PROMOTION_ELIGIBLE=0` (default off for WR/PF gating).

### Step 3 — FOREX specific fix

Current FOREX verdict **WATCH** because policy-clean passes WR/PF/n but **mdd_ok=false**, **bootstrap_ci_ok=false**. After Step 1, FOREX should show:

- intrabar: n=88, WR=42%, PF=1.13 → **NOT_READY** (WR<50%)
- Eliminates false hope from 57% policy-clean WR.

---

## Verification

```bash
python3 alpha_engine/money_ready_verdict.py --json | jq '.classes.FOREX | {verdict, intrabar_truth, wr, wr_ok, sizing_source}'
# wr_ok should reflect intrabar when n>=30
```

Playwright: `/audit` — no green WR cell > intrabar WR without “discovery” label.

---

## Rollback

Env `MONEY_READY_SIZING_SOURCE=policy_clean` restores old behavior for A/B.

---

## Risks

| Risk | Mitigation |
|------|------------|
| intrabar n too small → nothing passes | P0-A increases n first |
| Stakeholders miss tournament WR | Keep tournament on ai_leaderboard with “not sized” banner |

---

## Dependency

**P0-A must run first** — otherwise intrabar n stays at 1,553 batch-frozen and all classes look INSUFFICIENT.
