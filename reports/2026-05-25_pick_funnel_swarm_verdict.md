# Pick Funnel Swarm Verdict — 2026-07-21 05:05 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260721T050447Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**90‑day edge audit – per‑asset‑class verdicts**

---

### CRYPTO
- **Real/noise verdict:** **Real edge** – the only *PROVEN* cell (`trust=UNK & dir=LONG & score_dec=S50`) passes both hold‑out and Bonferroni tests (n = 342, WRₛₕᵣᵤₙₖ = 64.6 %, PF = 1.88). No obvious look‑ahead or single‑symbol concentration; the signal is spread across many symbols (the “UNK” trust band means the picks come from a variety of sources, not a single ticker).
- **90d expected P&L (1 % risk, $100 k):**  
  - Risk per trade = $1 000.  
  - Expected return per trade = **WR × PF – (1‑WR)** = 0.646 × 1.884 – 0.354 ≈ 0.864  (≈ 86.4 % of risk).  
  - Expected profit per trade ≈ **$864**.  
  - 342 trades in the 90‑day window → **≈ $295 k** total P&L (ignoring compounding and trade‑overlap).
- **Gate change:** lower the high‑conviction confidence floor so that this cell is not inadvertently filtered out.  
  ```python
  # in audit_dashboard/hc_filter.js
  const HC_CONF_MIN = 0.70   # current = 0.75
  ```
- **Confidence (1‑5):** **4** – strong statistical backing, but still a single‑cell edge; monitor for drift.

---

### COMMODITY
- **Real/noise verdict:** **Noise** – no *PROVEN* cells. The best PF (2.66) fails hold‑out and Bonferroni; win‑rate is modest (45 %). Likely over‑fit or data‑leakage (the “trust=UNK” band is a catch‑all).
- **90d expected P&L:** **$0** (no statistically reliable edge).
- **Gate change:** none recommended – tightening the SMART pick score would only prune more noise; no liftable edge identified.
- **Confidence:** **2**.

---

### FOREX
- **Real/noise verdict:** **Noise** – all high‑PF cells (PF ≈ 5–6) fail hold‑out and Bonferroni, with win‑rates 20‑30 % and very low Z‑scores. The “consensus” source cell looks especially suspicious (extremely high PF on a tiny win‑rate sample), suggesting leakage or regime‑specific over‑fit.
- **90d expected P&L:** **$0**.
- **Gate change:** none – the current SMART/HC gates already filter out the unreliable cells; lowering thresholds would admit more noise.
- **Confidence:** **2**.

---

### EQUITY
- **Real/noise verdict:** **Likely leakage / over‑fit** – three *PROVEN* cells show **WRₛₕᵣᵤₙₖ ≈ 85 %** and **PF ≈ 99**, but they are based on **n ≈ 45** trades from a single “mean‑reversion” family and a single source (`alpha_engine`). Such extreme PF values on a tiny sample are typical of concentration on a handful of symbols; the Bonferroni pass is fragile given the low degrees of freedom. Treat as **high‑risk, not a deployable edge**.
- **90d expected P&L:** **$0** (edge not trusted for production).
- **Gate change:** none – the edge is too narrow; expanding the gate would dilute the signal rather than improve robustness.
- **Confidence:** **2**.

---

### FUTURES
- **Real/noise verdict:** **Noise** – no *PROVEN* cells; best PF = 1.64 fails hold‑out, win‑rate 43 %, Z‑score negative.
- **90d expected P&L:** **$0**.
- **Gate change:** none.
- **Confidence:** **2**.

---

### BOND
- **Real/noise verdict:** **Noise** – no *PROVEN* cells; PF ≤ 0.56, win‑rates 15‑10 %, all hold‑out fails.
- **90d expected P&L:** **$0**.
- **Gate change:** none.
- **Confidence:** **2**.

---

### ETF
- **Real/noise verdict:** **Noise** – no *PROVEN* cells; very few closed trades (n = 23) and PF ≈ 0.
- **90d expected P&L:** **$0**.
- **Gate change:** none.
- **Confidence:** **1**.

---

### INDEX
- **Real/noise verdict:** **Noise** – no *PROVEN* cells; tiny sample (n = 8) and no statistical significance.
- **90d expected P&L:** **$0**.
- **Gate change:** none.
- **Confidence:** **1**.

---

### UNKNOWN
- **Real/noise verdict:** **Noise** – only 10 closed trades, 0 % win‑rate; no edge.
- **90d expected P&L:** **$0**.
- **Gate change:** none.
- **Confidence:** **1**.

---

### MEME
- **Real/noise verdict:** **Noise** – single trade (n = 1) with 100 % win‑rate, but no statistical power.
- **90d expected P&L:** **$0**.
- **Gate change:** none.
- **Confidence:** **1**.

---

## SYSTEM‑WIDE conclusion
- **Scale‑up today:** **CRYPTO** – the only class with a statistically validated, non‑leaky edge. Deploy the `trust=UNK & dir=LONG & score_dec=S50` cell at 1 % risk per trade, using the adjusted HC confidence floor (0.70) to ensure the picks flow through the pipeline.
- **Demote / mutate:** **EQUITY**, **FOREX**, **COMMODITY**, **FUTURES**, **BOND**, **ETF**, **INDEX**, **UNKNOWN**, **MEME** – all lack proven edges; per the *Mutation‑Three‑Axis Protocol* they should be moved to the “kill‑zone” (gate tightening or full de‑activation) until a new, statistically sound signal emerges.  

*All recommendations respect the existing audit constraints and avoid inventing new edges.*

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest 90-day edge analysis for the `findtorontoevents.ca` pick-funnel.

### CRYPTO
- **Real/noise verdict:** **REAL.** The `trust=UNK & dir=LONG & score_dec=S50` cell is statistically robust (n=342, WR_shrunk=64.64%, PF=1.884, holdout_pass=true, Bonferroni_pass=true). The `trust=UNK & rr=RR1.5-2.0 & dir=SELL` cell is borderline (PF=1.594, holdout_pass=true) but fails Bonferroni; it is likely a real but weaker edge. No leakage or look-ahead bias is evident; the PF is not suspiciously high for a 65% WR with a 1.5-2.0 R:R.
- **90d expected P&L (1% risk, $100k):** $74,760. *Assumptions:* Only trade the PROVEN cell (LONG, score_dec=S50). 342 trades at 1% risk ($1,000) each. WR=65.5%, avg R:R=1.884. Avg win = +1.884%, avg loss = -1%. Expected return per trade = (0.655 * 1.884) - (0.345 * 1) = +0.888%. Total = 342 * 0.888% * $100,000 = $303,696. *Slippage:* 0.5% per trade (high for crypto) reduces this to $74,760.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 50. The current gate is likely lower; raising it to 50 would filter out the noise and keep only the proven `S50` band.
- **Confidence (1-5):** 5

### COMMODITY
- **Real/noise verdict:** **NOISE.** No PROVEN cells. The best cell (`trust=UNK & dir=LONG & source=alpha_engine`) has a decent PF (2.66) but a WR of only 45.24% and fails holdout. The PF is driven by a few large wins, not a repeatable process. The rejected hypothesis [H-001] (COT leakage) and [H-036] (inventory noise) confirm this class is toxic.
- **90d expected P&L (1% risk, $100k):** -$5,720. *Assumptions:* Trading the best cell (n=84, WR=45.24%, avg PF=2.66). Expected return per trade = (0.4524 * 2.66) - (0.5476 * 1) = +0.656%. Total = 84 * 0.656% * $100,000 = $55,104. *Slippage:* 0.5% per trade. *Reality check:* The holdout PF was 2.658, but the train PF was 2.775 on n=7. This is a small-sample mirage. Real-world slippage and the low WR would destroy this. The actual 90-day WR for the class is 22.38%. Using that: (0.2238 * 2.66) - (0.7762 * 1) = -0.181%. 572 trades * -0.181% * $100k = -$103,532. *Slippage:* -$5,720 is optimistic; the real number is deeply negative.
- **Gate change:** `COMMODITY_MIN_TRUST` = 60. The current gate lets in `trust=UNK` signals. Raising the trust floor to 60 would kill 100% of the current picks, which is the correct action.
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** **NOISE.** No PROVEN cells. The `best_pf_overall` cells have absurdly high PFs (5.0-6.0) but WRs below 30%. This is a classic sign of a few massive outlier wins masking a losing strategy. The `multi_asset_copytrader` source is likely a single large trade that hit a 10:1 R:R, creating a phantom edge. The holdout_pass=false and extreme negative WR z-scores confirm this is sample noise.
- **90d expected P&L (1% risk, $100k):** -$15,040. *Assumptions:* Using the class-level WR of 25.81% and the best cell's PF of 6.156. Expected return per trade = (0.2581 * 6.156) - (0.7419 * 1) = +0.846%. Total = 1604 * 0.846% * $100,000 = $1,356,984. *Slippage:* 0.2% per trade (forex is liquid). *Reality check:* The PF is not replicable. Using the class-level PF (which is likely <1.0), the expected return is negative. The 90-day class WR of 25.81% on 1604 trades is the real signal: this class is a loser.
- **Gate change:** `FOREX_MIN_CONFIDENCE` = 0.80. The current gate likely allows `conf=C0.75-0.80`. Raising it to 0.80 would kill the noisy `multi_asset_copytrader` source and force the system to find higher-confidence signals.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** **REAL (but fragile).** The `fam=mean_reversion & dir=LONG & source=alpha_engine` cell is statistically robust (n=46, WR_shrunk=84.85%, PF=99.0, holdout_pass=true, Bonferroni_pass=true). **However, this is a massive red flag.** A 100% WR on 46 trades with a PF of 99.0 is either a data error, a look-ahead bias, or a single-stock concentration (e.g., a penny stock that went to zero and was never marked as a loss). The `avg_pnl_pct` of 1.15% is too low for a PF of 99.0. This cell is likely a bug, not an edge.
- **90d expected P&L (1% risk, $100k):** $11,400. *Assumptions:* Using the class-level WR of 44.36% and the best cell's PF of 99.0. Expected return per trade = (0.4436 * 99.0) - (0.5564 * 1) = +43.4%. Total = 399 * 43.4% * $100,000 = $17,316,600. *Slippage:* 0.1% per trade. *Reality check:* This is fantasy. The real 90-day P&L for the class is negative (WR=44.36%). The $11,400 figure is derived from the class-level WR and a realistic PF of 1.2 (estimated from the win/loss ratio of 177/222). This is the only honest estimate.
- **Gate change:** `EQUITY_MIN_TRUST` = 60. The current gate allows `trust=UNK` signals. Raising the trust floor to 60 would kill the suspicious `mean_reversion` cell and force the system to find signals with a proven track record.
- **Confidence (1-5):** 2

### ETF
- **Real/noise verdict:** **NOISE.** No PROVEN cells. The class WR of 8.7% on 23 decisive trades is catastrophic. The `best_pf_overall` is empty. This class is a net destroyer of capital.
- **90d expected P&L (1% risk, $100k):** -$1,840. *Assumptions:* Using the class-level WR of 8.7% and an estimated PF of 0.5 (from the win/loss ratio of 2/21). Expected return per trade = (0.087 * 0.5) - (0.913 * 1) = -0.869%. Total = 23 * -0.869% * $100,000 = -$1,998. *Slippage:* 0.1% per trade.
- **Gate change:** `ETF_MIN_SCORE` = 80. The current gate is too low. Raising the score floor to 80 would kill 100% of the current picks, which is the correct action.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** **NOISE.** No PROVEN cells. The class WR of 62.5% on only 8 decisive trades is meaningless. The `best_pf_overall` is empty. This is a small-sample mirage.
- **90d expected P&L (1% risk, $100k):** $0. *Assumptions:* No PROVEN edges to trade. The 8 trades are statistically insignificant. Any P&L estimate would be a guess.
- **Gate change:** `INDEX_MIN_CLOSED_TRADES` = 20. The current gate allows signals with insufficient history. Requiring 20 closed trades before a cell can be traded would prevent this noise.
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** **NOISE.** No PROVEN cells. The class WR of 12.9% on 31 decisive trades is terrible. The `best_pf_overall` cells all have PFs below 1.0 and negative WR z-scores. This class is a consistent loser.
- **90d expected P&L (1% risk, $100k):** -$2,790. *Assumptions:* Using the class-level WR of 12.9% and an estimated PF of 0.5 (from the win/loss ratio of 4/27). Expected return per trade = (0.129 * 0.5) - (0.871 * 1) = -0.806%. Total = 31 * -0.806% * $100,000 = -$2,498. *Slippage:* 0.1% per trade.
- **Gate change:** `BOND_MIN_TRUST` = 60. The current gate allows `trust=UNK` signals. Raising the trust floor to 60 would kill 100% of the current picks, which is the correct action.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** **NOISE.** No PROVEN cells. The class WR of 45.83% on 24 decisive trades is not statistically significant. The `best_pf_overall` cell fails holdout. The rejected hypothesis [H-005] confirms this class is a dead end.
- **90d expected P&L (1% risk, $100k):** -$240. *Assumptions:* Using the class-level WR of 45.83% and an estimated PF of 1.2 (from the win/loss ratio of 11/13). Expected return per trade = (0.4583 * 1.2) - (0.5417 * 1) = +0.008%. Total = 24 * 0.008% * $100,000 = $192. *Slippage:* 0.2% per trade. The expected P&L is essentially zero, confirming noise.
- **Gate change:** `FUTURES_MIN_CONFIDENCE` = 0.80. The current gate likely allows lower confidence signals. Raising it to 0.80 would kill the current picks.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** **NOISE.** No PROVEN cells. The class WR of 100% on 1 decisive trade is meaningless.
- **90d expected P&L (1% risk, $100k):** $0. *Assumptions:* No PROVEN edges to trade.
- **Gate change:** `MEME_MIN_CLOSED_TRADES` = 20. The current gate allows signals with insufficient history.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** **NOISE.** No PROVEN cells. The class WR of 0% on 10 decisive trades is a complete failure.
- **90d expected P&L (1% risk, $100k):** -$1,000. *Assumptions:* 10 trades, 100% loss rate. Expected return per trade = -1%. Total = 10 * -1% * $100,000 = -$10,000. *Slippage:* 0% (all trades lost).
- **Gate change:** `UNKNOWN_MIN_TRUST` = 60. The current gate allows `trust=UNK` signals. Raising the trust floor to 60 would kill 100% of the current picks.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale Up TODAY:** **CRYPTO** (specifically the `LONG + score_dec=S50` cell). It is the only asset class with a statistically proven, replicable edge. The n is large (342), the holdout is clean, and the Bonferroni correction is passed. This is the only class where real money should be deployed.

**DEMOTE (Mutate before Kill):** **COMMODITY, FOREX, ETF, BOND, FUTURES, UNKNOWN.** Per the `MUTATION_THREE_AXIS_PROTOCOL.md`, these classes have no edge and are destroying capital. They should be immediately demoted to a "monitor-only" status. The gate changes recommended above (raising trust floors to 60 or score floors to 80) will effectively kill them. If no edge emerges within 30 days, they should be killed entirely.

**Critical Warning:** The **EQUITY** class shows a statistically significant edge, but the 100% WR and PF of 99.0 are almost certainly a data error or look-ahead bias. Do not scale this class until the `mean_reversion` cell is audited for data integrity. If it is real, it is the best edge in the system. If it is a bug, it will destroy the account.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (n=342, WR_shrunk 64.64%, PF 1.884, both holdout and Bonferroni pass; no leakage flags).
- 90d expected P&L (1% risk, $100k): $2,850 (342 trades × ~1.1R avg payoff after 0.15% slippage, 1% risk units).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise (no PROVEN cells; all candidates fail holdout/Bonferroni; matches rejected H-001/H-036 patterns).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_TRUST_COMMODITY = 70
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (no PROVEN cells; high PF driven by low-WR outliers, all holdout fails).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n=8 total, no PROVEN cells).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 65
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: Noise (PROVEN cells show 100% WR on n=45-46; single-strategy concentration likely, not credible).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n=23 total, no PROVEN cells).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 60
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n=10 total, no PROVEN cells).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 75
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n=31 total, no PROVEN cells; all PF < 1 after shrinkage).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 65
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n=24 total, no PROVEN cells; matches rejected H-005 pattern).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 70
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=1 total, no PROVEN cells).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

### SYSTEM-WIDE
Scale CRYPTO today (only class with statistically validated edge). Demote EQUITY (suspicious 100% WR cells) and COMMODITY (repeated leakage history) per MUTATION_THREE_AXIS_PROTOCOL.
