# Clone Placeholder Stats Blocker — HC Gate Analysis

**Date:** 2026-04-22  
**Status:** BLOCKER — do not use clone rows for real-money sizing decisions  
**Author:** Copilot agent  
**Referenced files:**
- `alpha_engine/data/active_picks.json`
- `audit_dashboard/data/edge_report.md`
- `audit_dashboard/hc_filter.js`
- `updates/2026-04-17-edge-deepscan-5-filter-catalog.md` §6

---

## 1. What Was Reported

The user observed that the HC gate audit showed ~50 CRYPTO passes out of 31 active picks, all from `clone_hl_copy_*` strategies, while 0 non-crypto picks passed. Suspected cause: placeholder statistics inflating pass rates.

---

## 2. What Was Actually Found

Inspecting `active_picks.json`, the clone rows contain three compounding problems:

### Problem A — Explicit Gate Bypass Tag

Every `clone_hl_copy_*` row carries:
```json
"clone_safety_mode": "EXEMPT_FROM_SAFETY_GATES",
"tags": ["proven_trader_strategy_clone", "clone_whale_433roi", "exempt_from_safety_gates"]
```

The HC gate in `hc_filter.js` and `tools/dashboard_hc_rules.py` reads this flag and routes these picks around all threshold checks. They are not passing the HC gate — they are bypassing it entirely by design.

**This is the primary blocker.** The 50 "CRYPTO HC passes" are not HC passes. They are gate-exempt entries counted in the same bucket.

### Problem B — WR% Written Into the Trade-Count Field

The `forward_trades` field should be a count of independently observed closed trades. In clone rows:

| Trader | `forward_trades` | `forward_wr` | Claimed "ExpWR" in `reason` |
|--------|-----------------|--------------|----------------------------|
| `whale_433roi` | `85.71` | `0.8571` | ExpWR:86% |
| `PensionFund_24M` | `100.0` | `1.0` | ExpWR:100% |
| `lb_None` | `80.0` | `0.8` | ExpWR:80% |

`forward_trades: 85.71` is a float — the **percentage** win rate (85.71%) was copied directly into the trade-count field. A real `forward_trades` value is always a non-negative integer. This field corruption means any downstream check on `forward_trades >= N` is nonsensical for these rows; 85.71 would pass any threshold ≤ 85.

### Problem C — `forward_validated: true` Without Independent Validation

`forward_validated: true` is set on all clone rows, but no independent backtest or forward test was run. The trader's self-reported stats ("ExpWR:86% PF:3.4") are treated as validated. Real picks from `ml_enhanced_*` or other strategies show `forward_validated: false` and `forward_status: "insufficient_data (0/15 trades)"` until they accumulate real closed results.

---

## 3. Corroborating Evidence

- **`edge_report.md` line 25:** "Active picks passing HC gates now: **1 / 31 (3.2%)**" — this is the real gate pass rate, computed from the 31 active picks shown in the HC filter UI (which presumably excludes or discounts exempt rows). The ~50 clone rows are not in this count.

- **`updates/2026-04-17-edge-deepscan-5-filter-catalog.md §6`:** Already flagged that `HIGHFWWRABV55_SCOREABOVE50_V3` has zero programmatic backing in the codebase; the edge claim collapsed from n=94 to n=1 on inspection. Clone stats contributed to that inflated n.

- **HC gate thresholds** (`hc_filter.js` embedded defaults): `scoreCompoundFloor: 50`, `forwardWRMinPct: 55`, per-class CRYPTO floor `40%/45`. A pick with `forward_wr: 0.8571` would pass numerically even if the bypass flag were removed — which means removing the `EXEMPT` tag without also purging the false `forward_validated: true` and correcting `forward_trades` would still produce invalid passes.

---

## 4. Why This Happened

The `clone_hl_copy_*` pipeline (`copy_trader_intel/`) was designed to mirror a proven external trader's open positions. When seeding the pick, the developer wrote the trader's claimed performance metrics into the HC gate fields (`forward_trades`, `forward_wr`, `elite_score`) and set `forward_validated: true` so the pick would display as high-quality in the dashboard.

The intent was: "this trader has a 86% win rate, so treat the pick as if it has been forward-validated." The implementation translated that into literal field values that pass numeric threshold checks.

---

## 5. Option Analysis (from user's a/b/c/d framing)

| Option | Description | Assessment |
|--------|-------------|-----------|
| **a** | Accept clone rows as "HC-equivalent" based on trader WR | ❌ Not safe. No independent validation. Trader self-reported stats are not the same as your pipeline's forward-tested edge. Closed-book HC counterfactual (65.3% WR, PF 3.44) was not generated from clone rows. |
| **b** | Strip clone rows from active picks entirely | Cleanest short-term fix but loses signal if trader is genuinely good. The right quarantine, not permanent removal. |
| **c** | Add a second HC tier that accepts `clone_safety_mode=EXEMPT` at a separate display level | Reasonable for UX transparency — show "Clone/Unvalidated" bucket separately — but dangerous if the UI conflates it with HC-passed picks. |
| **d** | Fix the pipeline: require independent forward trades before HC acceptance | ✅ **Recommended.** Until clone rows accumulate `forward_trades >= 5` from independently observed closed results, gate them the same as any new strategy. Remove the `forward_validated: true` override for rows with `forward_trades < 5` or `forward_trades` as a float. |

---

## 6. Recommended Fix (Option D — Pipeline-First)

**Immediate (data hygiene):**
1. In `copy_trader_intel/` wherever `clone_hl_copy_*` picks are seeded, do NOT write the trader's claimed WR into `forward_trades`. Use `forward_trades: 0` and `forward_wr: 0.0` and `forward_validated: false` at seed time.
2. Remove `clone_safety_mode: "EXEMPT_FROM_SAFETY_GATES"` or rename it to `clone_safety_mode: "DISPLAY_ONLY"` and ensure HC gate code does NOT route exempt picks into the passing bucket — only into a clearly labeled "Unvalidated Clone" bucket.
3. Rename the `forward_validated: true` override to an explicit `clone_stats_seeded: true` flag so downstream code can distinguish "independently validated" from "trader stat copy".

**Medium term:**
4. Once a clone row accumulates ≥ 5 independently observed closed trades via `audit_trail/universal_pick_resolver.py`, allow it to earn `forward_validated: true` through the normal path.
5. Add a regression test: assert that no row with `clone_source_trader` != null has `forward_trades` as a non-integer or `forward_validated: true` at seed time.

---

## 7. Blast Radius

Until this is fixed:
- The HC gate pass count metric in `edge_report.md` (1/31, 3.2%) remains correct for non-clone picks.
- Any UI or alert that uses HC pass count will show inflated numbers if clone rows are counted.
- `audit_dashboard/data/edge_report.md` commentary on "high_conviction_counterfactual" (75 picks, 65.3% WR, PF 3.44) is NOT generated from clone rows — that stat is from `recent_closed` counterfactual filter on actual closed picks and remains valid.
- Real-money sizing decisions should NOT be triggered by clone rows until Problem B and C are fixed.

---

## 8. Verification

The blocker is confirmed directly from `active_picks.json`. Reproducer:

```bash
python -c "
import json
with open('alpha_engine/data/active_picks.json') as f:
    picks = json.load(f)
clones = [p for p in picks if 'clone_hl_copy' in p.get('strategy','')]
print(f'Clone rows: {len(clones)}')
float_trades = [p for p in clones if isinstance(p.get('forward_trades'), float)]
print(f'Float forward_trades (WR% masquerading as trade count): {len(float_trades)}')
exempt = [p for p in clones if p.get('clone_safety_mode') == 'EXEMPT_FROM_SAFETY_GATES']
print(f'Explicit gate bypass: {len(exempt)}')
"
```

Expected output confirms all three problems.
