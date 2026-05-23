# Cohort Harness Verdict — 2026-05-18

**Author:** Automated analysis
**Date:** 2026-05-18
**Validation Method:** `tools/edge_stability_harness.py::is_admissible()` — eff>=0.30, same sign, >=3/5 walk-forward windows (14-day buckets, >=80 picks/window)
**Data Source:** `audit_dashboard/data/pf_registry.json` canonical view — `alpha_engine/data/closed_picks.json` (deduped, spot-flicker filtered, policy-clean, net-of-slippage)
**Hypotheses Pre-Registered:** H-017 through H-020

---

## Executive Summary

**Verdict: 0/8 cohorts admissible. 8/8 KILL. Clean sweep consistent with 8-kill base rate.**

No edge exists in any tested cohort when measured against `is_admissible()` on canonical, policy-clean, deduplicated data. Additionally, the edge_analysis_2026-05-17.md cohort definitions do NOT map cleanly onto canonical data — direction naming, strategy names, and pick counts all diverge, suggesting the edge_analysis was computed against a non-canonical dataset.

---

## Task A: Cohort Harness Results

### CRYPTO 7-family LONG
- **Canonical match:** 0 picks (specific 7-family filter has no direct match in canonical data)
- **Proxy (CRYPTO ALL LONG):** n=492, WR=65.4%, PF=0.99
- **Windows at n>=80:** Only 3-4 (need >=5) → UNTESTABLE
- **Only high-density strategy:** quan_engine_scalp (n=2662) → admissible=False, sign=mixed (FAILS)
- **Verdict: KILL**

### EQUITY elite>=60
- **Canonical pick count:** 1 (stocks_rsi2_pullback_wide, PEP, 2026-03-19)
- **Edge analysis claimed:** n=44 → 44x INFLATION vs canonical n=31 for all EQUITY policy_clean
- **Verdict: KILL** (data-insufficient, inflated counts in edge_analysis)

### COMMODITY SHORT
- **Canonical count:** 0 (no SHORT-direction COMMODITY picks exist; only 1 COMMODITY pick, direction=LONG)
- **Edge analysis claimed:** n=62, direction=SHORT, dominated by cftc_cot_commercial_signal (51.6%)
- **COT strategy canonical count:** 0 under SHORT direction
- **Verdict: KILL** (cohort doesn't exist in canonical data)

### FOREX rsi-ema-scout
- **Canonical count:** 0 (strategy renamed to fx_smart_forex_rsi2_mean_reversion)
- **All FOREX canonical:** n=29, WR=27.6%, PF=0.89
- **Edge analysis claimed:** n=22, PF=1.68, OOS PF=0.65
- **Verdict: KILL** (expected from OOS PF=0.65; data-insufficient)

---

## Task B: Copytrader Data Availability

| Source | Records | Complete Outcomes | Usable? |
|--------|---------|-------------------|---------|
| closed_trades.json | 321 | 0 (all FLAT) | NO |
| highscore_closed_picks.json | 29 | partial | NO (survivorship bias) |
| clone_closed_picks.json | 46 | partial | NO (n too small) |

**Key finding:** lb_None (largest trader, 279 trades) has ALL records with outcome=FLAT and pnl_pct=0.0000. Forward WR is populated (estimated, not validated). No completed backtest outcomes exist.

**Honest answer:** The data does not exist to verify or refute copytrader edge.

---

## Data Integrity: edge_analysis vs Canonical

| Cohort | edge_analysis | Canonical | Status |
|--------|--------------|-----------|--------|
| CRYPTO 7fam LONG | n=372 | n=0 (exact), n=492 (all LONG) | MISMATCH |
| EQUITY elite>=60 | n=44 | n=1 | 44x INFLATION |
| COMMODITY SHORT | n=62, 51.6% COT | n=0 SHORT | ZERO MATCH |
| FOREX rsi-ema-scout | n=22 | n=0 exact, n=7 closest | NAME MISMATCH |

**Root cause:** edge_analysis was likely computed against raw/undeduplicated data. The canonical pipeline removes 3,691 duplicate re-emissions, 15 spot-flicker artifacts, and 476 policy-excluded picks.

---

## Honest Assessment

Base rate: **8 harness kills, 0 admissible.** This analysis adds zero to that count.

Every testable cohort either failed density requirements, failed sign stability, or could not be tested because the cohort doesn't exist in canonical data.

**No edge was found.** The system remains at zero demonstrated statistical edge.

Next productive action requires:
- A genuinely new data source surviving dedup/cleaning with n>=400 per asset class
- Expanding the traded universe beyond ~12 actively-traded symbols
- Fixing the forward-resolution pipeline (8,421 closed picks, but most have no resolved outcome)

*No code changes to production. No "Money Ready" claims.*