# Pick Funnel Swarm Verdict — 2026-08-02 05:05 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260802T050508Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real edge** – the three “PROVEN” cells each have ≥ 330 closed trades, Bayesian‑shrunk win‑rates ≈ 64‑66 % and profit‑factors ≈ 2.1. Hold‑out and Bonferroni tests pass, and the source is the internal `alpha_engine` (no external leakage signals detected).  
- **90d expected P&L (1 % risk, $100 k):** ≈ **$2.7 M**  
  *Assumptions:* 1 % risk = $1 k loss per losing trade, profit‑factor = 2.182, win‑rate = 64.5 % (shrunk). Expected value per trade ≈ $953 after a modest 10 bps slippage cost, multiplied by 2 832 closed trades.  
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 0.70` (lower the minimum Smart‑Pick score from the default ≈ 0.80 to admit more high‑PF LONG picks while still meeting the HC filter).  
- **Confidence (1‑5):** **4**

### EQUITY
- **Real/noise verdict:** **Likely leakage / over‑fit** – the “PROVEN” cells show an astronomic profit‑factor ≈ 156 on only 58 closed trades, with a Bayesian‑shrunk win‑rate of 85.9 %. Such PFs are typical of single‑symbol or look‑ahead contamination; the extreme PF together with the tiny sample size flags severe over‑optimism despite hold‑out pass.  
- **90d expected P&L (1 % risk, $100 k):** ≈ **$7.8 M** (theoretical) – however this figure is **not credible** given the likely leakage; a realistic expectation would be near‑break‑even.  
- **Gate change:** `SMART_PICKS_MIN_CONF_EQUITY = 0.65` (raise the minimum confidence band for Equity picks to force a larger, more diversified sample before a cell can be considered “PROVEN”).  
- **Confidence (1‑5):** **2**

### FOREX
- **Real/noise verdict:** **Noise** – the best PF (≈ 6.97) comes from a cell that fails hold‑out and Bonferroni tests; win‑rate is only 28 % (shrunk). No “PROVEN” cells exist.  
- **90d expected P&L (1 % risk, $100 k):** ≈ **$1.2 M** (theoretical) – but because the edge does not survive validation, the realistic expectation is **≈ $0**.  
- **Gate change:** *none needed* (the current gates already filter out the spurious signal).  
- **Confidence (1‑5):** **1**

### COMMODITY
- **Real/noise verdict:** **Noise** – top cells have PF ≈ 3.86 but fail hold‑out validation; win‑rate ≈ 51 % (shrunk) and sample size is modest. No “PROVEN” cells.  
- **90d expected P&L (1 % risk, $100 k):** ≈ **$0.78 M** (theoretical) – not reliable; expected real‑world P&L ≈ $0.  
- **Gate change:** *none* – tightening the Smart‑Pick score or confidence band would simply prune the noisy picks.  
- **Confidence (1‑5):** **1**

### BOND
- **Real/noise verdict:** **Noise** – profit‑factor ≈ 0.47, win‑rate ≈ 30 % (shrunk), and hold‑out fails. No “PROVEN” cells.  
- **90d expected P&L (1 % risk, $100 k):** **‑$19 k** (negative expectation).  
- **Gate change:** *none* – the current gates already block the weak signal.  
- **Confidence (1‑5):** **1**

### FUTURES
- **Real/noise verdict:** **Noise** – only one candidate cell, PF ≈ 1.64, win‑rate ≈ 46 % (shrunk), hold‑out fails. No “PROVEN” cells.  
- **90d expected P&L (1 % risk, $100 k):** **≈ $5 k** (theoretical) – not statistically reliable.  
- **Gate change:** *none* – further tightening would remove the marginal signal.  
- **Confidence (1‑5):** **1**

### INDEX
- **Real/noise verdict:** **No edge** – zero closed‑trade cells meet the ≥20‑trade threshold; no PF data.  
- **90d expected P&L (1 % risk, $100 k):** **$0**  
- **Gate change:** *none*  
- **Confidence (1‑5):** **1**

### ETF
- **Real/noise verdict:** **No edge** – insufficient volume; no PF data.  
- **90d expected P&L (1 % risk, $100 k):** **$0**  
- **Gate change:** *none*  
- **Confidence (1‑5):** **1**

### UNKNOWN
- **Real/noise verdict:** **No edge** – only 10 closed trades, no “PROVEN” cells.  
- **90d expected P&L (1 % risk, $100 k):** **$0**  
- **Gate change:** *none*  
- **Confidence (1‑5):** **1**

### MEME
- **Real/noise verdict:** **No edge** – single trade, cannot assess statistical significance.  
- **90d expected P&L (1 % risk, $100 k):** **$0**  
- **Gate change:** *none*  
- **Confidence (1‑5):** **1**

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – the statistically validated “PROVEN” LONG edge (PF ≈ 2.18, win‑rate ≈ 64 %) is robust across > 2 800 closed trades and survives hold‑out/BONFERRONI checks. Deploying real capital with the suggested gate relaxation (`SMART_PICKS_MIN_SCORE_CRYPTO = 0.70`) would likely increase trade volume while preserving the edge, delivering a sizable expected P&L.

- **Demote / mutate:** **EQUITY** – despite a “PROVEN” label, the edge is almost certainly a leakage artifact (tiny sample, absurd PF). According to the **MUTATION_THREE_AXIS_PROTOCOL**, this class should be **mutated** (tighten confidence and minimum‑n thresholds) before any further exposure, effectively demoting it until a genuine, diversified signal emerges.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Looking at this data with brutal honesty, the funnel reveals a system that is **massively over-trading and under-performing**. The gap between `passed_smart` and `opened` (e.g., CRYPTO: 2,650 passed vs 5,636 opened) indicates the execution layer is ignoring the quality gates entirely, likely auto-opening signals that fail the Smart_Picks criteria. This is the primary systemic failure.

Here is the per-class verdict:

### CRYPTO
- Real/noise verdict: **REAL (but fragile).** The `dir=LONG & score_dec=S50 & source=alpha_engine` cell (n=338, WR_shrunk=64.53%, PF=2.182) is statistically robust (z=5.655, Bonferroni pass). However, the overall class WR is 45.83%, meaning the edge is concentrated in a narrow slice. The `trust=UNK` dimension is a red flag—it suggests the edge is not dependent on trust, which is odd. The PF of 2.18 is high but plausible for a long-biased crypto momentum strategy with tight stops. **No leakage detected** in these specific cells, but the concentration in `alpha_engine` source warrants monitoring.
- 90d expected P&L (1% risk, $100k): **$9,472** (assuming 338 trades, avg +0.9472% per trade, 1% risk = $1,000/trade, no slippage on crypto majors).
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO = 50` (currently likely lower, allowing S40/S30 through).
- Confidence (1-5): **4**

### FOREX
- Real/noise verdict: **NOISE / LEAKAGE.** The `best_pf_overall` cells (PF 5.7-6.9) are statistical mirages. They fail `holdout_pass` (False), have negative z-scores (-4 to -6), and the `train_pf=0.0` indicates the edge only appears in the holdout set—a classic sign of overfitting to the recent period. The `multi_asset_copytrader` source with `conf=C0.75-0.80` is likely a single-symbol concentration (e.g., EURUSD) with a few large wins skewing PF. **Do not trade.**
- 90d expected P&L (1% risk, $100k): **-$4,138** (based on the 122-trade cell at -0.4138% avg, this is a loss).
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX = 80` (kill all sub-80 signals).
- Confidence (1-5): **1**

### COMMODITY
- Real/noise verdict: **NOISE.** The `best_pf_overall` (PF 3.861) has `train_n=5` (insufficient), `holdout_pass=False`, and `wr_z=0.277` (not significant). The WR is 51.92%, barely above coin-flip. The high PF is driven by a few outlier trades (avg_pnl 2.09% on 52 trades). **Rejected.**
- 90d expected P&L (1% risk, $100k): **$0** (do not trade).
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY = 70` (raise from current).
- Confidence (1-5): **1**

### ETF
- Real/noise verdict: **NOISE.** n=23 closed, WR=8.7%. The `best_pf_overall` is empty. This class is dead. The 2 wins out of 23 are statistical noise.
- 90d expected P&L (1% risk, $100k): **-$1,000** (expected loss).
- Gate change: `SMART_PICKS_MIN_SCORE_ETF = 90` (effectively disable).
- Confidence (1-5): **1**

### UNKNOWN
- Real/noise verdict: **NOISE.** n=10, WR=0%. The class is undefined and untradeable. **Kill immediately.**
- 90d expected P&L (1% risk, $100k): **-$1,000** (guaranteed loss).
- Gate change: `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (disable).
- Confidence (1-5): **1**

### EQUITY
- Real/noise verdict: **SUSPICIOUS / LEAKAGE.** The `mean_reversion` cell (n=58, WR=98.28%, PF=156.6) is **impossible** in live trading. A 98% WR with PF 156 implies a near-perfect prediction of short-term reversals. This is either (a) look-ahead bias in the `score_dec=S40` signal, or (b) a single-symbol concentration (e.g., one ticker that reversed perfectly). The `train_n=15` vs `holdout_n=43` split shows the edge is unstable. **Flag as leakage recurrence.**
- 90d expected P&L (1% risk, $100k): **$1,073** (but this is fake money; do not trust).
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY = 60` (and add a `max_positions_per_symbol` guard).
- Confidence (1-5): **1**

### BOND
- Real/noise verdict: **NOISE.** n=35, WR=14.29%. The `best_pf_overall` shows PF=0.47 (losing). The `bond_scanner` source is broken. **Kill.**
- 90d expected P&L (1% risk, $100k): **-$243** (expected loss).
- Gate change: `SMART_PICKS_MIN_SCORE_BOND = 90` (disable).
- Confidence (1-5): **1**

### FUTURES
- Real/noise verdict: **NOISE.** n=24, WR=45.83%. The `best_pf_overall` (PF 1.641) has `holdout_pass=False` and `wr_z=-0.654`. Not significant. **Rejected.**
- 90d expected P&L (1% risk, $100k): **$0** (do not trade).
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES = 75`.
- Confidence (1-5): **1**

### INDEX
- Real/noise verdict: **NOISE.** n=7, WR=42.86%. Insufficient data. **Do not trade.**
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX = 80`.
- Confidence (1-5): **1**

### MEME
- Real/noise verdict: **NOISE.** n=1. Statistically meaningless. **Ignore.**
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: N/A.
- Confidence (1-5): **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** **CRYPTO** — specifically the `dir=LONG & score_dec=S50 & source=alpha_engine` cell. It is the only statistically validated edge (z=5.655, holdout pass). Size at 1% risk, cap at 10 concurrent positions, and only take LONG signals with score >= 50.

**DEMOTE (per MUTATION_THREE_AXIS_PROTOCOL):**
1. **FOREX** — Mutate the `multi_asset_copytrader` source. The PF is a mirage; the source is likely overfitting to a single pair. Kill the source, not the class.
2. **EQUITY** — The `mean_reversion` cell is a **leakage recurrence**. The 98% WR is impossible. Investigate the `score_dec=S40` calculation for look-ahead bias (e.g., using close price to predict the same close). **Do not scale.**
3. **BOND, ETF, UNKNOWN** — Kill all three. They have no edge and are burning capital via spread costs.

**The #1 gate change:** In `audit_trail/quality_gates.py`, set `SMART_PICKS_MIN_SCORE_CRYPTO = 50` AND **fix the execution layer** to respect `passed_smart` (the `opened` count exceeding `passed_smart` is the root cause of all losses). If the bot cannot respect the gate, the gate is worthless.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real. Three cells with n=256-338, WR_shrunk 64-65%, PF 2.08-2.18, holdout_pass + bonferroni_pass all true; z-scores >5. No obvious leakage.
- 90d expected P&L (1% risk, $100k): $8,400 (338 trades × ~$1k risk × 0.62% avg edge after 0.15% slippage/commissions).
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` = 50
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Noise/leakage. 98% WR and PF 156 on n=58 (train n=15) is statistically impossible in live equity mean-reversion; single-strategy concentration + tiny train set screams data error or look-ahead.
- 90d expected P&L (1% risk, $100k): -$2,100 (edge collapses out-of-sample).
- Gate change: `HC_MIN_TRUST` = 70
- Confidence (1-5): 2

**### FOREX**
- Real/noise verdict: Noise. All "best_pf" cells fail holdout and bonferroni; high PF driven by low WR + small n. No proven cells.
- 90d expected P&L (1% risk, $100k): -$4,800
- Gate change: `HC_MIN_CONF` = 0.82
- Confidence (1-5): 1

**### COMMODITY**
- Real/noise verdict: Noise. All candidates fail holdout/bonferroni; n=52 too small and PF inflated by outliers.
- 90d expected P&L (1% risk, $100k): -$3,900
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` = 55
- Confidence (1-5): 1

**### BOND**
- Real/noise verdict: Noise. n=23-35, negative expectancy, all gates fail.
- 90d expected P&L (1% risk, $100k): -$1,100
- Gate change: disable `bond_scanner` entirely
- Confidence (1-5): 1

**### FUTURES**
- Real/noise verdict: Noise. n=21-24, holdout fails, no proven cells.
- 90d expected P&L (1% risk, $100k): -$800
- Gate change: `HC_MIN_TRUST` = 70
- Confidence (1-5): 1

**### INDEX / ETF / UNKNOWN / MEME**
- Real/noise verdict: Noise. All n<25 and zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no trades)
- Gate change: `passed_verified_alpha` threshold = 1 (block all)
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with multiple verified, holdout-passing edges). Demote EQUITY and FOREX immediately per MUTATION_THREE_AXIS_PROTOCOL.md — both show clear leakage/overfit signatures and should be mutated (or killed) before any further capital allocation. All other classes have no actionable edge.
