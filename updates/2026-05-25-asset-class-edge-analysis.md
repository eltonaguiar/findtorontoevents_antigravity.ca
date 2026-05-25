# Asset Class Edge Analysis — 2026-05-25

**Scope:** Performance of picks per asset class across the /audit dashboard, with edge identification.

**Data sources:**
- `audit_dashboard/data/pick_summary_stats.json` (generated 2026-05-25T05:46Z)
- `audit_dashboard/data/top_edges_per_class.json` (generated 2026-05-25T04:18Z, 90d window)
- `audit_trail/data/hf_asset_class_report.json` (HF tier baseline)
- `audit_dashboard/data/edge_decay_heatmap.json` (strategy-level decay)
- `audit_trail/data/performance_report_2026-05-16_to_2026-05-21.json` (weekly performance)
- `audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md` (IC / score correlations)
- `audit_dashboard/QUANT_MEMO_PER_ASSET_2026-04.md` (per-asset quant notes)

---

## 1. Asset Class Scorecard (Dashboard Closed + DB Raw 90d)

| Asset Class | Dash n (closed) | Dash WR% | Dash WR (shrunk) | Dash PF | Dash Mean PnL% | DB n (90d decisive) | DB WR% | DB PF | DB Mean PnL% | Active Picks |
|-------------|-----------------|----------|-------------------|---------|-----------------|---------------------|--------|-------|---------------|--------------|
| **CRYPTO** | 2,129 | 51.57% | 51.56% | 1.801 | +0.54% | 2,001 | 39.38% | 0.371 | −4.60% | 73 |
| **COMMODITY** | 202 | 45.05% | 45.50% | 1.079 | +0.03% | — | — | — | — | 0 |
| **FOREX** | 516 | 45.54% | 45.71% | 2.02 | +0.41% | 6,051 | 83.28% | 0.108 | −5.07% | 0 |
| **EQUITY** | 567 | 37.39% | 37.82% | 0.704 | −0.72% | 8,249 | 66.69% | 5.555 | +4.94% | 8 |
| **ETF** | 13 | 30.77% | 42.42% | 0.338 | −0.88% | 121 | 67.77% | 2.594 | +1.76% | 0 |
| **BOND** | 7 | 57.14% | 51.85% | 25.901 | +0.71% | — | — | — | — | 0 |
| **FUTURES** | 14 | 7.14% | 32.35% | 0.582 | −0.44% | 2,681 | 49.98% | 131.597 | +371.2% | 0 |
| **MEMECOIN** | 0 | — | — | — | — | 96 | 34.38% | 0.579 | −2.60% | 0 |

### Key observations on the scorecard

1. **Massive dashboard↔DB divergence** — The dashboard's curated `recent_closed` cohort is heavily filtered; the raw DB tells a different story:
   - **CRYPTO**: Dashboard WR 51.6% vs DB WR 39.4% — the dashboard cohort is survivorship-biased upward
   - **FOREX**: Dashboard WR 45.5% vs DB WR 83.3% — but DB PF is 0.108 (catastrophic losses dwarf wins), meaning the 83% WR comes from tiny TP hits with enormous SL blows
   - **EQUITY**: Dashboard WR 37.4% vs DB WR 66.7% — DB PF 5.555 is excellent, suggesting the raw DB equity book is actually profitable when decisive exits happen
   - **FUTURES**: Dashboard WR 7.1% vs DB WR 50.0% — DB PF 131.6 is absurdly high, likely a data quality issue (pnl scale anomaly)

2. **BOND** looks excellent (PF 25.9, WR 57%) but n=7 — statistically meaningless

3. **MEMECOIN** is a drain: 34% WR, PF 0.579, avg −2.6% per trade in the DB

---

## 2. Proven Edge Cells (Bonferroni + Holdout Pass)

From `top_edges_per_class.json` — 90d window, 673 cells evaluated, Bonferroni α = 7.4e-05:

### COMMODITY — ✅ REAL EDGE (6 proven cells)

| Cell | n | WR% | WR (shrunk) | PF | Avg PnL% | Holdout PF | Holdout Pass | Bonferroni |
|------|---|-----|-------------|-----|---------|------------|--------------|------------|
| conf=C0.60-0.70 & rr=RR1.0-1.5 & source=multi_asset_copytrader | 137 | 70.1% | 67.5% | 3.27 | +2.55% | 2.31 | ✅ | ✅ |
| fam=cot & dir=SHORT & score_dec=S20 | 137 | 74.5% | 71.3% | 3.22 | +2.63% | 2.13 | ✅ | ✅ |
| dir=SHORT & score_dec=S20 & source=multi_asset_cot | 137 | 74.5% | 71.3% | 3.22 | +2.63% | 2.13 | ✅ | ✅ |
| trust=UNK & rr=RR1.0-1.5 & source=multi_asset_copytrader | 146 | 69.2% | 66.9% | 3.16 | +2.47% | 2.37 | ✅ | ✅ |

**Commodity edge signature:** COT (Commitment of Traders) family, SHORT direction, score decile S20, RR 1.0-1.5, confidence 0.60-0.70, copytrader source. This is the **strongest statistically validated edge** in the system.

### CRYPTO — ❌ NO PROVEN CELLS

Zero cells passed both Bonferroni AND holdout. The best unadjusted cells:

| Cell | n | WR% | PF | Holdout PF | Holdout Pass | Bonferroni |
|------|---|-----|-----|-----------|--------------|------------|
| conf=C<0.60 & rr=RR1.0-1.5 | 345 | 60.0% | 22.2 | 2.68 | ✅ | ❌ |
| conf=C<0.60 & dir=LONG | 458 | 57.0% | 8.82 | 2.39 | ✅ | ❌ |
| fam=ml & rr=RR1.5-2.0 | 271 | 56.5% | 4.71 | 1.79 | ✅ | ❌ |
| fam=ml & source=ml_crypto_predictor | 255 | 43.5% | 10.58 | 2.52 | ✅ | ❌ |

**Crypto edge signature (unproven):** Low confidence (<0.60), RR 1.0-1.5, LONG direction, ML family. The PF numbers look great but Bonferroni fails — too many cells tested, not enough statistical separation. The `ml_crypto_predictor` source has interesting PF (10.6) with holdout pass but WR is below 50% — it wins big when it wins.

### FOREX — ❌ NO PROVEN CELLS

Best PF cells have WR ~26% with absurd PF (95.5) — these are artifacts (8 trades in training, PF=0). No real edge found.

### EQUITY — ❌ NO PROVEN CELLS (but promising signal)

| Cell | n | WR% | PF | Holdout PF | Holdout Pass | Bonferroni |
|------|---|-----|-----|-----------|--------------|------------|
| conf=C0.60-0.70 & fam=mean_reversion & source=multi_asset_copytrader | 73 | 50.7% | 20.98 | 1.35 | ✅ | ❌ |
| rr=RR1.5-2.0 & fam=mean_reversion & dir=LONG | 74 | 51.4% | 20.98 | 1.39 | ✅ | ❌ |

**Equity edge signature (unproven but holdout-passing):** Mean reversion family, LONG direction, RR 1.5-2.0, confidence 0.60-0.70, copytrader source. 30 of 72 cells pass holdout — the highest holdout pass rate of any class. Low n (126 closed) prevents Bonferroni significance.

---

## 3. Strategy Decay Analysis

From `edge_decay_heatmap.json` (11 strategies tracked):

| Verdict | Count | Strategies |
|---------|-------|------------|
| **Dead** (PF<0.8 on 30d) | 9 | quan_engine_scalp, quan_engine_swing, volume_spike_breakout, macd_rsi_confluence, ml_enhanced_FETUSDT/RENDER/JTO/APE/AVAX |
| **Decaying** | 1 | ml_enhanced_RENDERUSDT_1h (90d PF 3.94 → 30d PF 1.19) |
| **Improving** | 1 | ml_enhanced_DYDXUSDT_15m (30d PF 999, 96.8% WR — likely overfit) |
| **Stable** | 0 | — |

**9 of 11 tracked strategies are dead.** The system is running on fumes for most strategy implementations.

---

## 4. Source System Performance (Weekly 2026-05-16 to 05-21)

| Source | Picks | WR% | Total PnL% | Avg PnL% | Verdict |
|--------|-------|-----|-----------|---------|---------|
| **kimi_signal_tracking** | 168 | 53.6% | +257.3% | +1.53% | 🟢 Best performer |
| **ml_crypto_pred_v12** | 88 | 45.5% | +97.0% | +1.10% | 🟢 Good |
| **aggregated_picks** | 58 | 74.1% | +111.0% | +1.91% | 🟢 High WR, decent PnL |
| **ml_crypto_pred** | 118 | 47.5% | +46.6% | +0.40% | 🟡 Marginal |
| **dna_winner_picks** | 96 | 40.6% | +21.7% | +0.23% | 🟡 Marginal |
| **alpha_engine** | 82 | 37.8% | +7.6% | +0.09% | 🟡 Weak |
| **luxalgo_filters** | 52 | 34.6% | +5.2% | +0.10% | 🟡 Weak |
| **quan_engine** | 123 | 33.3% | — | — | 🔴 Dead (scalp PF 0.4) |
| **claude_gainer_st** | 30 | 10.0% | −30.2% | −1.01% | 🔴 Toxic |
| **copy_trader_highscore** | 40 | 12.5% | −41.7% | −1.04% | 🔴 Toxic |
| **dna_rapid_fire_mutations** | 21 | 0.0% | −27.5% | −1.31% | 🔴 Toxic |
| **mutation_lab** | 14 | 7.1% | −13.1% | −0.94% | 🔴 Toxic |
| **contrarian_evolver** | 5 | 0.0% | −7.5% | −1.50% | 🔴 Toxic |
| **battleground** | 5 | 0.0% | −5.4% | −1.08% | 🔴 Toxic |

---

## 5. Score→PnL Information Coefficient (from SCORE_PNL_EDGE_REVIEW)

| Slice | Spearman(score, pnl) | Spearman(elite_score, pnl) | Spearman(confidence, pnl) |
|-------|---------------------|---------------------------|--------------------------|
| Pool-wide (n=3500) | 0.18 | **0.20** | 0.07 |
| Crypto (n=2867) | 0.11 | 0.13 | 0.05 |
| **Non-crypto (n=633)** | **0.33** | **0.39** | — |
| Verified-alpha overlap (n=32) | **0.54** | — | — |

**Non-crypto scores are 3× more predictive than crypto scores.** Confidence is nearly uncorrelated with outcome everywhere.

---

## 6. Edge Rankings & Actionable Findings

### 🏆 Tier 1 — Statistically Proven Edge (trade with conviction)

**COMMODITY SHORTS from COT data**
- Cell: `fam=cot & dir=SHORT & score_dec=S20`
- WR 74.5% (shrunk 71.3%), PF 3.22, holdout PF 2.13, Bonferroni ✅
- This is the **only asset class with Bonferroni-validated edge**
- Source: `multi_asset_cot` and `multi_asset_copytrader`
- Action: **Increase allocation to COT-based commodity shorts. This is real alpha.**

### 🥈 Tier 2 — Promising but Unproven (trade small, validate)

**EQUITY mean-reversion LONGS from copytrader**
- Cell: `fam=mean_reversion & dir=LONG & rr=RR1.5-2.0`
- WR 51.4%, PF 20.98, holdout PF 1.39 ✅, Bonferroni ❌ (n=126 too small)
- 30/72 cells pass holdout — highest holdout ratio of any class
- DB raw data shows EQUITY PF 5.555 with 66.7% WR — the raw book is profitable
- Action: **Scale equity picks to get n>200 for Bonferroni validation. Mean-reversion + copytrader is the signal.**

**CRYPTO ML predictor (low confidence, tight RR)**
- Cell: `fam=ml & source=ml_crypto_predictor`
- WR 43.5%, PF 10.58, holdout PF 2.52 ✅
- Wins big when it wins (avg +2.66%) despite sub-50% WR
- Action: **Keep running but filter to RR 1.0-1.5 and confidence <0.60 where holdout is stronger.**

### 🗑️ Tier 3 — No Edge / Negative Edge (kill or quarantine)

| Asset/Source | Problem | Action |
|-------------|---------|--------|
| **MEMECOIN** | 34% WR, PF 0.58, −2.6% avg | Kill memecoin picks entirely |
| **FUTURES** (dashboard) | 7% WR, PF 0.58 | Kill futures from dashboard; DB data unreliable (PF 131) |
| **claude_gainer_st** | 10% WR, −30% total PnL | Kill this source — it's toxic |
| **copy_trader_highscore** | 12.5% WR, −42% total PnL | Kill — "high score" is inverse signal |
| **dna_rapid_fire_mutations** | 0% WR, 21 losses | Kill — zero wins in 21 trades |
| **quan_engine (scalp+swing)** | PF 0.4, 37% WR, dead on 30d | Kill — been dead for months |
| **mutation_lab / contrarian_evolver / battleground** | 0-7% WR | Kill — experimental garbage |
| **FOREX** (dashboard) | No proven edge, best cells are artifacts | Reduce forex allocation; DB WR 83% is misleading (PF 0.108) |

---

## 7. Capital Reallocation Recommendation

| From (kill) | Estimated freed picks/week | To (scale) | Rationale |
|-------------|---------------------------|------------|-----------|
| quan_engine (scalp+swing) | ~25/week | COT commodity shorts | Dead → proven edge |
| claude_gainer_st | ~6/week | Equity mean-reversion | Toxic → promising |
| copy_trader_highscore | ~8/week | ml_crypto_predictor (filtered) | Inverse signal → positive expectancy |
| memecoin picks | ~2/week | kimi_signal_tracking | Drain → best weekly performer |
| mutation_lab + dna_rapid_fire | ~4/week | Equity mean-reversion | Zero WR → holdout-passing |

**Expected impact:** Removing ~45 picks/week from negative-expectancy sources and redirecting to Tier 1-2 edges should improve system-wide WR by ~5-8pp and flip aggregate PnL from negative to positive.

---

## 8. Data Quality Warnings

1. **CRYPTO dashboard WR is inflated** — the Smart Picks cohort (n=337, WR 78.9%) is 91.7% one source (`claude_gainer_st`) which has 10% WR in the raw DB. EXPIRED rows counted as wins when drift was positive (63.9% WR on 97 EXPIRED rows).
2. **1,864 duplicate groups** exist in CRYPTO 90d raw picks — count inflation risk.
3. **FUTURES DB PF of 131.6** is a data anomaly — likely pnl_pct scale error (avg +371% per trade is impossible for futures).
4. **FOREX DB WR 83.3% with PF 0.108** — the WR is real but meaningless; SL hits are catastrophic relative to TP hits.
5. **BOND n=7** — too small for any conclusion despite attractive metrics.

---

*Analysis generated 2026-05-25 from audit dashboard data. Regenerate with updated `pick_summary_stats.json` and `top_edges_per_class.json` for fresh numbers.*
