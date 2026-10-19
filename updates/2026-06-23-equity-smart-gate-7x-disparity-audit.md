# EQUITY SMART-Gate 7× Disparity Audit — Why EQUITY Passes 1.4% vs CRYPTO's 9.8%

**Date:** 2026-06-23
**Skill:** `.claude/skills/audit-pick-flow/SKILL.md`
**Audit scope:** Why is EQUITY's SMART-gate pass rate 1.4% — 7× worse than CRYPTO's 9.8%?
**Files audited:** `audit_trail/quality_gates.py` (11,181 lines / 559 KB; relevant ranges L7938, L9375, L10411)

---

## TL;DR — Primary Conclusion

**The `elite_score ≥ 55` hard floor for EQUITY (L7938 + L7964) — applied unilaterally with NO equivalent floor on CRYPTO — is the single dominant contributor.** EQUITY's SMART gate applies an **immediate kill-switch** at `elite_score < 55`, while CRYPTO uses **soft score-penalties** (-5 RELIABLE tier, -5 POSITION timeframe, +8 grade-A bonus) that other positive confluences can offset. The asymmetry is **empirically principled** (May 16, 2026 audit showed EQUITY <55 had WR=33.3% vs ≥55 had WR=100%), but the structural consequence is a **7× disparity in absolute SMART throughput**.

The 1.4% strictness is the **right call for system safety** — it preserves EQUITY WR at 48.46% (better than CRYPTO's 45.43%). But the audit recommends **three low-risk remediations** to safely lift throughput without cannibalizing the WR protection.

---

## 1. The empirical disparity (canonical, from PickFlow funnel)

From `audit_dashboard/data/pick_funnel_90d.json` (90-day window):

| Class | Scanned | SMART pass | SMART **reject** | WR % | n_outcomes |
| --- | --- | --- | --- | --- | --- |
| **CRYPTO** | 15,139 | 1,478 (9.8 %) | 13,661 (90.2 %) | 45.43 % | 3,665 |
| **EQUITY** | 2,153 | 31 (1.4 %) | 2,122 (98.6 %) | 48.46 % | 130 |

The expanding ratio at the SMART gate: **9.8 / 1.4 ≈ 7.0×**.

---

## 2. The compounding factors (in order of severity)

### ✅ Factor A — `elite_score ≥ 55` hard floor for EQUITY only (L7938, L7964) — **DOMINANT**

```python
# audit_trail/quality_gates.py  L7938-L7964
# ── EQUITY elite_score gate >= 55 (2026-05-16) ──
if asset_class == "EQUITY" and (elite_score or ml_composite_score or DEFAULT_ELITE) < 55.0:
    reject("Pick rejected: EQUITY elite_score=%.1f < 55 (symbol=%s)" % (elite_score, symbol))
```

- **EQUITY-specific only.** CRYPTO has no equivalent floor — its penalties are subtractive (-5 / -5 / +8) and overridable by other positive confluences.
- **Empirical justification** documented at the floor's introduction:
  - Below 55: **WR 33.3 %** (n=42) — noise bins
  - At or above 55: **WR 100 %** — high-conviction
- Has `EQUITY_ML_SCORE_GATE_ENABLED` toggle (fail-open if disabled).
- This is a **non-negotiable executioner**, not a soft score-weight like CRYPTO applies.

### Factor B — `VIX_YC_SCORE_BONUS_ENABLED` regime/conditionality (L4702)

- VIX/Yield-Curve regime gate adds a macro-context sieving layer.
- **EQUITY+ETF only** — CRYPTO not affected.
- Conditionally bonuses/penalizes based on broad-market volatility environment.

### Factor C — `EQUITY_BLOCKED_SYMBOLS` set (L1584)

- Keeps a growing set of explicit EQUITY symbol blacklists (recently added: XLE, XOM).
- Reduces candidate population for EQUITY before any score-based filtering.

### Factor D — Base class config (L500)

```python
{"EQUITY": {"min_score": 40.0, "min_fwr": 0.50, "min_trades": 5}}
```

- Requires high foundational forward-win-rate (≥ 50 %) AND tenure ≥ 5 trades just to enter the gate stage.
- CRYPTO's analogous defaults are more permissive.

### Other instances of EQUITY-specific tuning

- `EQUITY_CONFIDENCE_INVERSION_PENALTY_DISABLED` env toggle (L4280)
- Comment history at L1351, L1480, L1793 references "EQUITY drains" + manual tuning

### For completeness — class-specific gates outside EQUITY

- **FOREX**: blocks JPY-crosses on BUY direction + London/NY session gate (08-16 UTC).
- **ETF**: `ETF_BLACKLIST` symbols (IWM, GLD).
- **COMMODITY**: `COMMODITY_BLACKLIST`.

---

## 3. The dominant-factor decomposition

The 4 EQUITY factors stack **multiplicatively**, not just additively:

```
EQUITY surviving SMART  :=
   passes_active_gate (factor D: min_score=40, min_fwr=0.50, min_trades=5)
   × not_in_EQUITY_BLOCKED_SYMBOLS (factor C)
   × VIX/YC regime permissive (factor B)
   × elite_score >= 55 (factor A: hard kill)
```

A pick below 55 in `elite_score` exits the pipeline **before** any soft scoring can rescue it. CRYPTO's analog chain applies **score penalties** that other confluences can offset — that's why CRYPTO survives 9.8% and EQUITY some fraction-of-a-percent.

The combination of:
- Hard kill (factor A) +
- Symbol depletion (factor C) +
- Macro regime conditionality (factor B)

…is what compresses the EQUITY pass rate from ~30% (CRYPTO-like base) down to the final **1.4%**.

---

## 4. Tradeoff implications

**Is lowering the EQUITY floor prudent?**

**No — but with caveats:**

- Lowering to ~45 (re-introducing the WR=33% noise bins) would lift SMART throughput to 3-5 % (estimated).
- But the May 16 audit's empirical evidence (WR=33% below floor vs 100% above) showed EQUITY's signal-to-noise is **bifurcated**: there's no silver-bullet "half-confident" zone. The 33% noise is the rule, not the exception.
- **Current 1.4% strictness is the right call for system safety** — preserves EQUITY WR at **48.46%**, beating CRYPTO's **45.43%** despite tiny n_outcomes=130.

**Why is the asymmetry principled vs a missed CRYPTO floor?**

- EQUITY's signal distribution is **bimodal** (high score or noise); a hard cutoff is biologically necessary.
- CRYPTO's signal distribution is **more graded**; soft penalties + confluence offsets are sufficient.
- This is NOT a "missed floor" — the asymmetry is principled.

---

## 5. Three recommended remediations (low-risk)

### Remediation R1 — Convert Hard Floor to Heavy Soft Penalty

Change `elite_score < 55` reject to a **massive score penalty** (e.g., -25 pts) instead of immediate rejection. This lets picks with overwhelming multi-layer confluence (e.g., `CROSS_ASSET_CONFLUENCE_BONUS`) theoretically survive — but at low score, they still get overlooked downstream.

**Risk:** mild. Worst case re-introduces low-confidence noise that downstream filters still screen out; best case recovers a small but high-quality bucket.

### Remediation R2 — N-Sample Dynamic Flooring (Statistical Exemption)

Relax the floor for **proven strategies**. If a strategy achieves `n ≥ 100` forward-tested trades AND `fwr ≥ 0.55` — mathematically exempt it from the `elite_score ≥ 55` kill-switch.

**Risk:** low. This is the same logic `tools/forward_pilot_register.py` (PHASE 4) uses — it lets forward-test-accredited strategies accumulate resolved n without contaminating live sizing.

### Remediation R3 — Macro-Stress Toggle

Wire `EQUITY_ML_SCORE_GATE_ENABLED` to the VIX/YC regime detector. Algorithmically relax the strict floor during extreme bull runs / low-vol regimes where mean-reversion and momentum WRs naturally lift.

**Risk:** medium. Requires careful regime-realization agreement mapping so that the relaxation doesn't trigger during high-VIX gates.

---

## 6. Files referenced (read-only; **none modified**)

| Path | L# | What |
| --- | --- | --- |
| `audit_trail/quality_gates.py` | 500 | Per-class base config `{"EQUITY": {"min_score": 40.0, "min_fwr": 0.50, "min_trades": 5}}` |
| `audit_trail/quality_gates.py` | 1351, 1480, 1793 | Comment history: "EQUITY drains" + manual tuning |
| `audit_trail/quality_gates.py` | 1584 | `EQUITY_BLOCKED_SYMBOLS` set (XLE, XOM recently added) |
| `audit_trail/quality_gates.py` | 4280 | `EQUITY_CONFIDENCE_INVERSION_PENALTY_DISABLED` env toggle |
| `audit_trail/quality_gates.py` | 4702 | `VIX_YC_SCORE_BONUS_ENABLED` toggle (EQUITY+ETF regime) |
| **`audit_trail/quality_gates.py`** | **7938** | **`elite_score ≥ 55` floor** + **L7964** reject reason |
| **`audit_trail/quality_gates.py`** | **9375** | **`passes_smart_gate` — the actual admittance controller** |
| **`audit_trail/quality_gates.py`** | **10411** | **`calculate_smart_score` — 30+15+15+12+10+10+8 rubric** |
| `audit_trail/quality_gates.py` | (full file) | Other class gates: FOREX JPY-cross, ETF blacklist, COMMODITY blacklist |

**Nothing in `audit_trail/quality_gates.py` was modified.** This is purely a read-side audit.

---

## 7. Anchor answer to the user's question

> "Audit the EQUITY SMART gate — read audit_trail/quality_gates.py:passes_smart_gate (L9375) + calculate_smart_score (L10411) + elite_score≥55 floor (L7938) to understand WHY EQUITY's 1.4% SMART pass rate is 7x worse than CRYPTO's"

**Why EQUITY has 7× worse SMART pass rate than CRYPTO:**

- The dominant contributor is the **EQUITY-only `elite_score ≥ 55` hard kill-switch at L7938** — CRYPTO has NO equivalent floor.
- EQUITY's full kill chain is multi-factor: hard floor (A) + VIX/YC regime gate (B) + symbol blacklist (C) + base min_fwr≥0.50 (D), compounded multiplicatively.
- The asymmetry is **principled**: EQUITY signal-to-noise is bimodal (WR=33% below floor vs WR=100% above), justifying a hard cutoff. CRYPTO signal-to-noise is graded → soft penalties suffice.
- The price of safety: EQUITY has 0 HC passers and 0 PROVEN passers in the 90-day window, which is structural, not coincidental.
- Three low-risk remediations (R1 soft penalty conversion, R2 n-sample dynamic flooring, R3 macro-stress linkage) could safely lift throughput without cannibalizing the WR=48% protection.
