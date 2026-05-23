# Day-of-week effects on closed trades — statistical study (UTC)

**Date:** 2026-04-07  
**Data:** `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed` (**n = 3500** usable with `closed_at` + `pnl_pct`)  
**Repro:** `python tools/analyze_dow_closed_trades.py` → `tools/data/dow_closed_trades_analysis.json`

---

## 1. Definition (scientific setup)

| Choice | Detail |
|--------|--------|
| **Outcome (binary)** | Win if `pnl_pct > 0`, else loss (ties at exactly 0 treated as non-win). |
| **Outcome (continuous)** | `pnl_pct` as reported in JSON. |
| **Factor** | Calendar **weekday of `closed_at`**, **UTC** (Python `weekday()`: **Mon=0 … Sun=6**). |
| **Why UTC** | Timestamps are stored with `Z` / `+00:00`; avoids ambiguous local interpretation across agents. |
| **Slices** | **All** closed picks; **CRYPTO** only (**n = 2855**). |

---

## 2. Statistical tests

### 2.1 Chi-square test of independence (win/loss × weekday)

**H₀:** Win rate does **not** depend on weekday (independent).  
**H₁:** At least one weekday has a different win-rate mix.

7×2 contingency table (rows = Mon–Sun, cols = loss / win).

| Slice | χ² | df | p-value | Cramér’s V |
|-------|---:|---:|--------:|-----------:|
| **All** | 107.60 | 6 | ≈ **6.5 × 10⁻²¹** | **0.175** |
| **Crypto** | 127.83 | 6 | ≈ **3.7 × 10⁻²⁵** | **0.212** |

**Interpretation:** Under H₀ and standard assumptions (random sample, expected counts adequate), p-values are **extremely small** — **strong evidence against independence** of win/loss and weekday in this historical window. For this table, **minimum expected cell count ≈ 110** (χ² asymptotics comfortable).

**Cramér’s V** (~0.18 all, ~0.21 crypto): between **small and medium** association by common rules of thumb (0.1 / 0.3 / 0.5).

### 2.2 Kruskal–Wallis H (PNL distribution across weekdays)

**H₀:** The seven `pnl_pct` distributions are identical (same location/scale in rank sense).  
Nonparametric one-way layout; robust to heavy tails vs ANOVA.

| Slice | H | p-value |
|------|---:|--------:|
| **All** | 179.85 | ≈ **3.7 × 10⁻³⁶** |
| **Crypto** | 200.02 | ≈ **1.9 × 10⁻⁴⁰** |

**Interpretation:** **Reject H₀** — weekday groups differ materially on **ranked** PnL as well as win rate.

---

## 3. Descriptive pattern (all closed, UTC)

| Day | n | Win % | Mean PnL % | Median PnL % |
|-----|--:|------:|-----------:|-------------:|
| Mon | 561 | **52.4** | **+0.86** | +0.17 |
| Tue | 241 | 48.1 | +0.22 | −0.17 |
| Wed | 467 | 46.0 | +0.16 | −0.38 |
| **Thu** | 497 | **27.0** | **−1.25** | **−1.54** |
| Fri | 561 | 50.3 | +0.04 | +0.05 |
| Sat | 576 | **54.5** | +0.25 | +0.21 |
| Sun | 597 | 41.7 | +0.07 | −0.28 |

**Thu** is the **worst** mean and median PnL and the **lowest win rate** in this sample. **Mon** has the **best mean** PnL among days with substantial n.

### Crypto-only (UTC)

| Day | n | Win % | Mean PnL % |
|-----|--:|------:|-----------:|
| Mon | 434 | 53.7 | **+0.88** |
| Tue | 165 | 53.3 | +0.66 |
| Wed | 370 | 48.1 | +0.20 |
| **Thu** | 370 | **27.0** | **−1.14** |
| **Fri** | 399 | **62.7** | **+0.77** |
| Sat | 541 | 55.1 | +0.27 |
| Sun | 576 | 41.3 | +0.06 |

**Thu** remains the **clear trough** for crypto. **Fri** shows the **highest win rate** in the crypto slice (descriptive).

---

## 4. Limitations (honest science)

1. **Observational:** No randomization; confounders (macro calendar, strategy mix, volatility regime) may align with weekday.  
2. **Close-time ≠ entry-time:** DOW is on **`closed_at`**; entries may cluster on other days.  
3. **UTC vs sessions:** For equities/forex, “Thursday UTC” overlaps US Wed evening / Thu — label is **not** “NYSE Thursday close” without mapping.  
4. **Multiple looks:** Omnibus tests are pre-specified here; **pairwise** day comparisons would need **multiplicity control** if used for many tests.  
5. **Non-stationarity:** Past DOW pattern may **decay**; re-run monthly on fresh closes.

---

## 5. Actionable recommendations

1. **Research:** Decompose **Thu** — strategy × asset_class × `source_system` counts vs other days; check overlap with known event windows.  
2. **Scoring / risk:** Optional **DOW prior** as a **small** modifier (e.g. −ε to score or −size on Thu UTC) **only after** confirming stability on a walk-forward split — avoid overfitting a single full-sample pattern.  
3. **Monitoring:** Add **weekly** DOW breakdown to dashboard or cron JSON; alert if Thu win rate deviates from trailing baseline.  
4. **Repro:** Always store **timezone** in docs; re-run `analyze_dow_closed_trades.py` after regenerating `dashboard_data.json`.

---

## 6. Redis bus

Topic: **`DOW_CLOSED_TRADES_STUDY`** — see `tools/bus_post_dow_closed_trades_study.py`.

---

## References (context)

- Lakonishok, J., & Maberly, E. (1990). *The Day-of-the-Week Effect: A Test of Foreign Investment Hypothesis.* (classic equity calendar literature — not a claim our crypto/alt mix matches their mechanism.)  
- Reporting: association + **effect size** (Cramér’s V) + **nonparametric** check (Kruskal–Wallis) alongside χ².
