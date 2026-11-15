# Backtest & Research — What Was Tested to Determine the Picks

**Package:** WIRED_IN/2026-11-15_0135/inspect-wt
**Author:** inspect-wt · **Date:** 2026-11-15
**Reproduce:**
```bash
python final_2026_11_14/inspect-wt/06_profitable_approach/walkforward_v6.py <dashboard_payload.json>
python final_v4/inspect-wt/03_risk_management/make_risk_page.py   # sleeve backtest + bootstrap
```

---

## 1. The V0–V6 research chain (on the live closed-picks ledger)

Data: live `dashboard_payload.json` `.picks.recent_closed` — **3,500 rows, 2026-02-21 →
2026-11-14**, P/L net of the system's slippage model (`alpha_engine.charter_slippage`).

| Iteration | What was tested | Result |
|---|---|---|
| **V0** | Baseline: is the system profitable at all? | **No** — fleet PF 0.80, Σ−424pp/30d, 79% zombie picks, 81% fake 0% P/L |
| **V1** | Cell search: 8 source / 12 source×class / 26 strategy cells | **Zero** pass uncorrected z>1.96 |
| **V2** | Split-sample (median/60%/40%) | Single-split p=0.006–0.038 (suggestive); "alive-only" refinement **FAILED** (PF 0.80–0.84) |
| **V3** | Cost reality: breakeven extra round-trip cost per cell | Margins 0.23–3.31%/trade — healthy vs ~0.1–0.2% realistic equity cost |
| **V4/V6** | **Walk-forward selection procedures (4 pre-specified variants A–D)** | **Variant C survives; A/B/D fail Bonferroni** (table below) |

### Variant C — the authoritative result (8 true walk-forward months, Apr→Nov 2026)

| Metric | Value | T2 charter |
|---|---|---|
| Forward trades | n = 237 | ≥100 ✅ |
| Win rate | 47.3% | ≥50% ❌ |
| Profit factor | **1.26** | ≥1.5 ❌ |
| Total P/L | **+98.7pp** | positive ✅ |
| Randomization (800 null draws) | **0/800 → p<0.0013** | survives Bonferroni ×4 → **p<0.005 ✅** |
| Breakeven cost buffer | 0.416%/trade (realistic ~0.1–0.2%) | ✅ |
| Per-trade expectancy | +0.42%/trade | — |
| Monthly PF | May 2.63 · Jun 1.02 · **Jul 0.50** · Aug 1.74 · Sep 1.28 · Oct 1.49 · **Nov 1.72** | 4 improving months |
| By class | ETF n=120 PF 1.21 (+26.5pp) · EQUITY n=112 PF 1.30 (+73.1pp) | equity/ETF approach |

All four variants reported (honest multiple-testing): C p<0.0013 ✅ · A 0.049 · B 0.044 ·
D 0.040 (A/B/D fail Bonferroni). Top contributors: `vwap-reversion-scout` (n=15, PF 3.74),
`rs-breakout-scout` (n=110, PF 1.26, +35.3pp), `donchian-stock-breakout` (n=28, PF 1.39),
`mtf-align-scout` (n=19, PF 1.50).

**Independent reproduction:** quant-audit (`final_2026_11_14/quant-audit-2026-11-14/05_verification/`)
and finpredict-v2 (`PEER_CLAIMS_MATRIX` row 6) both reproduced it **exactly**; both correctly
label it NOT PROVED (selection-based null, sub-T2, payload-vintage sensitivity: an Oct-23
vintage rerun gave PF 0.906).

**Risk math on the pilot** (`risk_stats_extra.json`): Kelly full **9.86%** → adopted ¼-Kelly
**2.46%/trade**; 4,000-draw bootstrap: P(forward total>0) **91.6%**, P(PF≥1.15) **71%**,
median +95pp (5–95%: −18 → +216pp); bankroll maxDD at sizing median −1.2%, worst −4.4%.

## 2. The MF/ETF allocation-sleeve backtest (Family A)

Spec pre-registered in `backtest_rotation.py` docstring (fixed before the run).
Data: `yahoo_monthly.json` — 11 Yahoo symbols, monthly closes, **166 months (2013-01→2026-10)**,
deduplicated, trailing partial month excluded. Benchmarks: SPY B&H (price-only, **no dividends —
conservative**, understates B&H) and 60/40 SPY/AGG monthly-rebalanced. rf 2.5%/yr.

| Variant | CAGR | Sharpe | MDD | Calmar |
|---|---|---|---|---|
| **v1 base sleeve** | 8.2% | 0.53 | −20.4% | 0.40 |
| v1 + MF fee drag (0.15%/yr) | 8.1% | 0.51 | −20.6% | 0.39 |
| v2 + 12% vol target | 8.6% | 0.59 | −19.9% | 0.43 |
| v3 + 15% DD-stop | 4.5% | 0.27 | −20.4% | 0.22 — **REJECTED** |
| v4 top-3 sensitivity (2nd trial, disclosed) | 7.4% | 0.51 | −20.1% | 0.37 |
| **bench SPY B&H** | 12.8% | 0.75 | −24.8% | 0.52 |
| **bench 60/40** | 7.3% | 0.54 | −21.0% | 0.35 |

Stress (v1): **2022 +2.3% vs SPY −19.5% · COVID −0.8% vs −19.9% · 2018Q4 −18.6% vs −14.0%
(worse — stated plainly) · 2025-26 +51.7% vs +28.9%**. Annual table and full VaR/ES
(95/99) in `backtest_results.json`.

**Honest reading:** the sleeve beats 60/40 on Calmar and cuts worst-case drawdown ~in half vs
SPY, but **loses full-cycle to buy & hold** (8.2% vs 12.8%) and its Sharpe (0.53) is *below*
the 0.7 gate — so it is **not yet past its own certification gate**; it is the best-grounded
candidate, forward-tracked. The DD-stop overlay failed and was rejected, reported like the
peers' failed COT test.

## 3. Research inputs (non-backtest)

- **Live system audit:** 703 open picks repriced vs Binance/Yahoo/FX truth (Σ−1,116pp real vs
  Σ−106pp claimed ≈ 10× understated); 4,164 active rows of which 3,272 (78.6%) EXPIRED zombies;
  `resolution_method=None` on all 3,500 closed rows (the single blocker to certifying any PF);
  garbage ingest caught (EURGBP=X entry 688.17 vs market 0.835).
- **Multiple-testing quantification:** 361 strategy families + 285 baby strategies = 646
  candidates; expected PF>1.3 "winners" by chance = 32/646; only 4 strategies have n≥100 live;
  **zero** pass n≥100 + PF>1.3 + z>1.96; 69/80 (86%) live anti-overfit flags; White Reality
  Check never ran (missing `arch` pkg).
- **Fill/cost research:** `tools/stop_fill_replay.py` (30 crypto + 25 equity + 25 ETF real
  replays); #773 settled B4 (label-not-price, `--truncate-at-exit`); kimi fill correction
  +67.5pp (crypto −837.8 → −770.3pp, PF 0.768 → ~0.80); per-class 3× cost gate shipped
  (`tools/per_class_cost_gate.py`, default ON).
- **Benchmark literature check (SubQ Decisions API, 47 typed answers + GROUNDED/PARTIAL
  factcheck):** active MF selection beats index after costs P(yes)=0.03 vs simple rotation
  beating cash+fees P(yes)=0.99; trend-following evidence 4.23/5; ~30–36 month forward bar;
  TSMOM Sharpe 2.13 ≈ its own B&H ≈2.2 (risk premium, not system alpha).
- **Equity SPY gate (#773):** t=1.05, median pick −0.57% vs SPY, 54% underperform →
  `NO_ALPHA_BETA`, class closed as edge source.

## 4. What was explicitly NOT tested / could not be verified

- No regime-out test possible (single dataset Feb–Nov 2026); payload-vintage sensitivity open.
- Linux peer host 192.168.2.52 (SSH key denied); 180/365 workflow statuses (API budget).
- Slippage model unverified against closed-row fills (blocker #1).
- COT re-test, FOREX mutations, bond decision-level gate: **not run yet** — pending
  pre-registration per the plans.
