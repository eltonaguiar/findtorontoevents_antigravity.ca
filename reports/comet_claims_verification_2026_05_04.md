# Comet Claims Verification — 2026-05-04

**Source:** `alpha_engine/data/closed_picks.json` (7,472 picks total; 7,265 with both `pnl_pct` and `confidence`)
**Method:** Read-only aggregation. WR = wins / n; PF = sum(positive pnl_pct) / |sum(negative pnl_pct)|. Direction normalized: `BUY+LONG -> LONG`, `SELL+SHORT -> SHORT`.

---

## Per-claim verdicts

### Claim 1 — "Confidence sweet spot 0.75-0.79 gives ~86% WR, while conf>=0.90 is worse than random."
**REJECTED on the WR figure; partially supported on the >=0.90 portion (but n is degenerate).**

- conf [0.75, 0.80): **n=93, WR=38.71%, PF=0.69, avg pnl=-0.046%**. Comet claimed ~86% WR -> off by ~47pp. REJECTED.
- conf [0.80, 0.85): n=122, **WR=62.30%, PF=4.97**. THIS is the actual sweet spot in the data, not 0.75-0.79.
- conf >= 0.90: only **n=1** in the entire dataset (single pick, lost). Claim "worse than random" is technically true but statistically meaningless. REJECTED as actionable.

### Claim 2 — "Trust 6-7 had ~77% WR and +240% PnL vs trust 0-1 at 33.8% / -54%."
**REJECTED — no `trust_score` 0-7 field exists in the dataset.**

Searched fields: only `trust_tier`, `hf_conviction_tier`, `conviction_tier`, `hc_tier` exist, and only **3 picks** have non-empty values (all `UNKNOWN`/empty). The closest numeric proxies are `elite_score` (0-100, n=6010), `method_a_score` (8-100), `ml_composite_score` (0-75). Comet's "trust 0-7" framing is fabricated for this dataset.

Using **`elite_score`/14.29 as a synthetic 0-7 tier** (proxy, not Comet's claim):
- tier [0,2): n=3581, WR=26.72%, PF=0.37
- tier [2,4): n=1679, WR=29.54%, PF=0.36
- tier [4,6): n=749, WR=46.33%, PF=0.47
- tier [6,8): **n=1**, degenerate

Even as a proxy: there is a real WR lift from low to mid elite_score (26.7% -> 46.3%), but not the 33.8% -> 77% gap Comet claimed, and no PF>1 anywhere. REJECTED.

### Claim 3 (sub-claim) — "SHORT picks dramatically outperform LONG"
**CLOSE / partially VERIFIED on WR; REJECTED on profitability.**
- LONG: n=5910, WR=29.83%, PF=0.37, avg=-0.154%
- SHORT: n=1355, WR=46.27%, PF=0.65, avg=-0.074%
SHORT is genuinely better (+16.4pp WR, +0.28 PF, half the avg loss), but **both are unprofitable** (PF<1). "Dramatically outperform" overstates it.

### Claim 4 (sub-claim) — "long+high-conf (>=0.90) is the worst combo"
**REJECTED — degenerate.** LONG & conf>=0.90: n=1. The actual worst LONG cell with material n is **LONG [0.50,0.70): n=5026, WR=27.3%, PF=0.35, avg=-0.168%** (the bulk of the book).

---

## Confidence band table (all directions)

| band          | n    | WR%   | PF   | avg pnl% |
|---------------|------|-------|------|----------|
| [0.00, 0.50)  | 563  | 47.07 | 0.20 | -0.065   |
| [0.50, 0.70)  | 6025 | 30.76 | 0.41 | -0.153   |
| [0.70, 0.75)  | 457  | 34.79 | 0.50 | -0.130   |
| [0.75, 0.80)  | 93   | 38.71 | 0.69 | -0.046   |
| **[0.80, 0.85)** | **122** | **62.30** | **4.97** | **+0.082** |
| [0.85, 0.90)  | 4    | 25.00 | 0.01 | -0.220   |
| [0.90, 0.95)  | 1    | 0.00  | 0.00 | -0.045   |
| [0.95, 1.01)  | 0    | -     | -    | -        |

## Trust-band table (elite_score-proxy, 0-100 deciles)

| band     | n    | WR%   | PF   | avg pnl% |
|----------|------|-------|------|----------|
| [0,10)   | 22   | 0.00  | 0.00 | -0.021   |
| [10,20)  | 18   | 50.00 | 0.57 | -0.047   |
| [20,30)  | 3944 | 25.76 | 0.37 | -0.181   |
| [30,40)  | 381  | 38.58 | 0.54 | -0.102   |
| [40,50)  | 18   | 16.67 | 0.19 | -0.011   |
| [50,60)  | 877  | 31.70 | 0.29 | -0.120   |
| [60,70)  | 746  | 46.25 | 0.47 | -0.137   |
| [70,80)  | 3    | 66.67 | 0.03 | -0.097   |
| [80,90)  | 0    | -     | -    | -        |
| [90,101) | 1    | 100   | inf  | +0.035   |

(Note: Comet's stated trust_score 0-7 field does not exist; this table uses `elite_score` as the closest numeric proxy. There is no `trust_score`, `trust`, or numeric `trust_tier` field in the schema.)

## Direction x Confidence cross-tab

| dir   | band         | n    | WR%   | PF   | avg     |
|-------|--------------|------|-------|------|---------|
| LONG  | [0.00,0.50)  | 284  | 52.46 | 0.24 | -0.0707 |
| LONG  | [0.50,0.70)  | 5026 | 27.32 | 0.35 | -0.1683 |
| LONG  | [0.70,0.75)  | 403  | 34.74 | 0.53 | -0.1195 |
| LONG  | [0.75,0.80)  | 72   | 34.72 | 0.56 | -0.0799 |
| **LONG**  | **[0.80,0.85)**  | **120**  | **62.50** | **5.83** | **+0.0818** |
| LONG  | [0.85,0.90)  | 4    | 25.00 | 0.01 | -0.2203 |
| LONG  | [0.90,0.95)  | 1    | 0.00  | 0.00 | -0.0449 |
| SHORT | [0.00,0.50)  | 279  | 41.58 | 0.14 | -0.0584 |
| SHORT | [0.50,0.70)  | 999  | 48.05 | 0.70 | -0.0736 |
| SHORT | [0.70,0.75)  | 54   | 35.19 | 0.32 | -0.2106 |
| SHORT | [0.75,0.80)  | 21   | 52.38 | 2.44 | +0.0683 |
| SHORT | [0.80,0.85)  | 2    | 50.00 | 1.33 | +0.0790 |

---

## Top 3 actually-verified findings (audit-dashboard hardening candidates)

1. **conf [0.80, 0.85) is the real edge band: n=122, WR=62.3%, PF=4.97, +0.082% avg.** Driven by LONG [0.80,0.85) (n=120, WR=62.5%, PF=5.83). This is the only band with PF>1 and material n. Promote as a gate.
2. **SHORT structurally beats LONG by ~16pp WR + 0.28 PF (5910 vs 1355).** Both PF<1, but SHORT loses materially less. Sport-/asset-specific tightening should bias short or require stronger LONG confluence.
3. **SHORT [0.75, 0.80): n=21, WR=52.4%, PF=2.44, +0.068% avg.** Small but a second profitable cell — supports a SHORT-priority gate around mid-high confidence.

## Top 3 claimed but NOT verified (flag for further work)

1. **No `trust_score` (0-7) field exists.** Comet's entire "trust 6-7 vs 0-1" comparison is unbacked by the actual schema. Either Comet hallucinated the field or used a different dataset. Need to ask which artifact Comet read.
2. **Conf >= 0.90 has only n=1 in 7,472 picks.** Any claim about high-conf behavior is statistically empty in this corpus. If Comet saw ">=0.90 worse than random" with material n, it was a different snapshot or fabricated.
3. **"Sweet spot 0.75-0.79 ~86% WR" is off by ~47pp (actual 38.7%).** The actual sweet spot is one band higher (0.80-0.85). Comet may have miscoded the bin edge or hallucinated the WR magnitude — either way, do not feed into gates.

---

## Summary

Of 4 testable Comet claims: **0 VERIFIED, 1 CLOSE (SHORT>LONG direction edge, but both unprofitable), 3 REJECTED**. The audit-dashboard team should treat Comet's percentages as untrusted and use the tables above instead. The single robust signal worth wiring in is the **[0.80, 0.85) confidence band** (especially LONG), which is the only PF>1 zone with n>=100.
