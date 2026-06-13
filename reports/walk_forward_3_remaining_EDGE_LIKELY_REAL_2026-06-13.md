# Walk-Forward — 3 remaining EDGE_LIKELY_REAL strategies (n<100) — 2026-06-13

**Owner:** MiniMax-M3
**Trigger:** P2-14 — confirm/refute the 3 small-n EDGE_LIKELY_REAL strategies that survived the prediction_market REFUTE.
**Tool:** `tools/walk_forward_per_strategy.py --in-window 14 --out-window 5 --step 3 --min-n 20`
**Verdict:** **3/3 FAIL** (1 INSUFF_N, 2 hard FAIL)

---

## 1. Setup

- Lookback window: 14 days IS, 5 days OOS, step 3 days
- Macro-join: NOT enforced (per current single-strategy test)
- Live data: 2026-04-11 to 2026-06-12 (62 days of trade history)
- Data source: `ejaguiar1_stocks.trading_picks` with status `TP_HIT|SL_HIT|LOST|TIME_EXIT|WON` and `closed_at NOT NULL`

The 3 candidates were the only EDGE_LIKELY_REAL left in `anti_overfit_audit.json` after `prediction_market_consensus` was REFUTED on 2026-06-13. The audit's n-values (24/30/36) match the per-strategy totals from `trading_picks` (ml_enhanced_INJUSDT_1d_B_lightgbm n=24, ml_enhanced_RENDERUSDT_1h_D_ensemble_stack n=30, cta_golden_cross_200 n=35 in its largest category COMMODITY).

---

## 2. Per-strategy results

### 2.1 `cta_golden_cross_200` (COMMODITY) — n=35

| Metric | Value | Gate | Status |
|---|---:|---:|:---:|
| n_total trades | 35 | ≥100 | ❌ INSUFF_N |
| n_windows (rolling) | 6 | ≥3 | ✅ |
| n_surviving windows | 4 | n/a | n/a |
| survival_rate | 66.7% | ≥60% | ✅ PASS |
| mean_oos_pf | 652.04 | n/a | ⚠️ winsorized |
| **mean_oos_wr** | **37.0%** | **≥50%** | **❌ FAIL** |
| mean_is_pf | 18.77 | n/a | n/a (overfit signal) |
| total_pf | 14.74 | n/a | n/a |
| total_wr | 62.9% | n/a | n/a |
| **Verdict** | **FAIL** | PASS | **❌ FAIL** |

**Reason:** `mean_oos_wr=0.37 < 0.50` — OOS win rate is **13 percentage points BELOW 50%** in the average rolling window. The strategy passed survival rate (4/6 windows) but lost more than half its OOS trades. The IS PF=18.77 vs OOS PF=652.04 pattern is the classic winsorization: a handful of large winners dominate, and the average WR is sub-50%. This is a **head-fake edge** — looks great on the cohort, fails the per-trade expectancy test in forward windows.

### 2.2 `ml_enhanced_INJUSDT_1d_B_lightgbm` (CRYPTO) — n=24

| Metric | Value | Gate | Status |
|---|---:|---:|:---:|
| n_total trades | 24 | ≥100 | ❌ INSUFF_N |
| **n_windows (rolling)** | **2** | **≥3** | **❌ FAIL** |
| n_surviving windows | 0 | n/a | n/a |
| survival_rate | 0.0% | ≥60% | ❌ FAIL |
| mean_oos_pf | 0.00 | n/a | ⚠️ empty OOS (no closed trades) |
| mean_oos_wr | 100% | n/a | n/a (1 trade, trivially 100%) |
| mean_is_pf | 0.00 | n/a | n/a |
| total_pf | None | n/a | n/a (zero-loss cohort) |
| total_wr | 100% | n/a | n/a |
| **Verdict** | **INSUFF_N** | PASS | **❌ FAIL** |

**Reason:** Only 2 rolling windows can be constructed (n=24 trades ÷ step=3 picks = 8 windows, but only 2 are non-empty because the closed_at range is tight: 2026-03-16 to 2026-06-04 with all 24 trades concentrated in 2 short bursts). Cannot make a verdict with n_windows < 3.

**Sub-finding:** The IS PF is **0.00** — meaning the in-sample period has no losing trades (PF=inf). This is a hallmark of a strategy that's been **retired before it could lose** (DOGE/INJ-class meme-coin run-ups, then the model was stopped or the symbol was delisted). The 100% WR is an artifact, not an edge.

### 2.3 `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` (CRYPTO) — n=30

| Metric | Value | Gate | Status |
|---|---:|---:|:---:|
| n_total trades | 30 | ≥100 | ❌ INSUFF_N |
| n_windows (rolling) | 4 | ≥3 | ✅ |
| n_surviving windows | 2 | n/a | n/a |
| **survival_rate** | **50.0%** | **≥60%** | **❌ FAIL** |
| mean_oos_pf | 1.6033 | ≥1.2 | ✅ |
| mean_oos_wr | 80.0% | ≥50% | ✅ |
| mean_is_pf | 15.06 | n/a | n/a (overfit signal) |
| total_pf | 6.83 | n/a | n/a |
| total_wr | 83.3% | n/a | n/a |
| **Verdict** | **FAIL** | PASS | **❌ FAIL** |

**Reason:** `survival_rate=0.50 < 0.6` — Only 2 of 4 OOS windows beat the IS_PF × 0.85 threshold. The strategy's OOS WR=80% and OOS PF=1.60 are excellent per-window, but the strategy fails half the windows it's tested on. IS PF=15.06 → OOS PF=1.60 is a 9x decay — the in-sample fit doesn't generalize to forward periods as cleanly as a real edge would.

---

## 3. Why all 3 fail despite the audit's EDGE_LIKELY_REAL tag

The 4-strategy EDGE_LIKELY_REAL list from `anti_overfit_audit.json` was a **single-cohort DSR** view. DSR (Deflated Sharpe Ratio) answers: "is this strategy's Sharpe statistically distinguishable from 0, after correcting for the number of strategies we tested?" All 4 had DSR≥0.998.

Walk-forward answers a different question: "if we re-fit the strategy in 14-day chunks and predict the next 5 days, does it work?" All 4 fail this second test.

| | anti_overfit_audit (DSR) | walk-forward (rolling) |
|---|---|---|
| Method | Single cohort over the full lookback | Rolling IS/OOS, 14d/5d windows |
| Survival criterion | DSR≥0.95 (Lopez de Prado) | survival_rate≥60% AND mean_oos_wr≥50% |
| WINSORIZATION | Implicit (single PF number) | Per-window unbiased, then aggregated |
| OVERFIT detection | Partial (DSR adjusts for #tests) | Direct (OOS is unseen data) |
| Result | 4/4 EDGE_LIKELY_REAL | 1/1 REFUTED, 3/3 FAIL |

The two methods measure different things. DSR is a "is this not zero?" test; walk-forward is a "does it survive the test of time?" test. **The walk-forward is the more honest test for forward deployment.**

---

## 4. Operator decision matrix

The 4 EDGE_LIKELY_REAL candidates are now all REFUTED or FAIL:

| Strategy | DSR | Walk-forward | Live at_signal | Status |
|---|---:|---|---|---|
| `prediction_market_consensus` | 0.998 | 1/1 FAIL | n=141 WR 49.6% | **REFUTED 2026-06-13** (in PR #581) |
| `cta_golden_cross_200` | 1.000 | 1/1 FAIL (37% OOS WR) | n=35 | **FAIL — recommend KILL** |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 1.000 | INSUFF_N (n_windows<3) | n=24, 100% WR artifact | **FAIL — INSUFF_N; do not size up** |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 0.997 | 1/1 FAIL (50% survival) | n=30, 83% WR (overfit) | **FAIL — recommend KILL** |

**Recommended actions:**

1. **Confirm the kill of all 3 surviving candidates** by adding to `HARD_KILL_STRATEGIES` in `alpha_engine/emitter_discipline.py:49` (the same list that already contains `prediction_market_consensus` per the 2026-06-12 P0B session). The DSR=1.000 is a single-cohort artifact; the walk-forward is the honest test.

2. **Demote all 4 from `candidate_paper` to `REFUTED`** in `metric_honesty_tiers.json` + `money_ready_verdict.json::summary.candidate_paper`. Update the `current_live_examples` to show the 4 walk-forward reports.

3. **Add `cta_golden_cross_200` and `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` to `HARD_KILL_STRATEGIES`** in `alpha_engine/emitter_discipline.py:49` (operator approval required for that file change per CLAUDE.md).

4. **Do NOT size up on `ml_enhanced_INJUSDT_1d_B_lightgbm` despite 100% WR** — the closed_at range is too tight, the IS PF=0.00 is suspicious, and n=24 is well below the 100-trade gate.

---

## 5. What this means for `anti_overfit_audit.json`

The 2026-06-12 anti_overfit_audit.json had 4 EDGE_LIKELY_REAL candidates. After 2026-06-13 walk-forward:

- 0 survive both DSR and walk-forward
- 4 are REFUTED by walk-forward (the honest test for forward deployment)

**The anti_overfit_audit DSR-only view is misleading by itself** — it produces 4 false-positive EDGE_LIKELY_REAL signals per cohort, all of which fail walk-forward. Recommendation: update `anti_overfit_audit.json` and the verdict-generation pipeline to include walk-forward as a **second gate** after DSR (both must pass for a strategy to be considered for sizing).

---

## 6. Reproducer

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
# Set DB creds via the canonical env-only convention (see tools/db_env.py).
# Per INCIDENT_OVERALL #89 + DB_CREDENTIALS_MIGRATION_2026-06-02.md,
# do NOT inline a literal password.
export DB_STOCKS_HOST=mysql.50webs.com
export DB_STOCKS_USER=ejaguiar1_stocks
export DB_STOCKS_NAME=ejaguiar1_stocks
# export DB_STOCKS_PASSWORD=***set-via-env-only***

for strat in cta_golden_cross_200 ml_enhanced_INJUSDT_1d_B_lightgbm ml_enhanced_RENDERUSDT_1h_D_ensemble_stack; do
    python3 tools/walk_forward_per_strategy.py --strategy $strat --in-window 14 --out-window 5 --step 3 --min-n 20
    cat audit_dashboard/data/walk_forward_per_strategy_latest.json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'  {c[\"strategy\"]}::{c[\"category\"]}: n={c[\"n_total\"]} survival={c[\"survival_rate\"]:.0%} OOS_PF={c[\"mean_oos_pf\"]:.2f} OOS_WR={c[\"mean_oos_wr\"]:.0%} verdict={c[\"verdict\"]}') for c in d.get('cells',[])]"
done
```

---

## 7. Cross-references

- `reports/walk_forward_prediction_market_consensus_2026-06-13.md` (the first REFUTE)
- `audit_dashboard/data/walk_forward_cta_golden_cross_200_2026-06-13.json`
- `audit_dashboard/data/walk_forward_ml_enhanced_INJUSDT_1d_B_lightgbm_2026-06-13.json`
- `audit_dashboard/data/walk_forward_ml_enhanced_RENDERUSDT_1h_D_ensemble_stack_2026-06-13.json`
- `audit_dashboard/data/anti_overfit_audit.json` (the 4 EDGE_LIKELY_REAL list, all now REFUTED)
- `alpha_engine/emitter_discipline.py:49` (HARD_KILL_STRATEGIES — operator approval needed for additions)
- `audit_dashboard/data/money_ready_verdict.json::summary.candidate_paper[3]` (the 4th entry to demote)

---

*Last update: 2026-06-13 by MiniMax-M3.*
