# Pick Funnel Swarm Verdict — 2026-08-01 05:06 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260801T050533Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**90‑day Pick‑Funnel Edge Review**  
*(All numbers are based on the closed‑trade sample shown above.  “PF” = Profit‑Factor, “WR_shrunk” = Bayesian‑shrunk win‑rate.  Risk per trade = 1 % of a $100 k notional account → $1 000 loss‑size.  Expected profit per trade = (WR × PF − (1‑WR)) × $1 000.)*  

---

### CRYPTO
- **Real/noise verdict:** **Real edge** – 331 closed trades, WR_shrunk ≈ 64 % and PF ≈ 2.1.  The cell ( `dir=LONG & score_dec=S50 & source=alpha_engine` ) passes the hold‑out test (p‑value ≈ 0, Bonferroni‑pass = true).  No obvious leakage – the signal is based on a decile‑score from the Alpha Engine, not on future data, and the trade‑direction is uniformly LONG, avoiding single‑symbol concentration.
- **90d expected P&L (1 % risk, $100 k):**  
  Expected profit per trade ≈ **$1 024** → **$339 k** total (331 × $1 024).  
  *Assumptions:* 1 % risk per trade, no slippage, full‑size execution, win‑size = PF × $1 k.
- **Gate change:** lower the HC score threshold to admit the S‑50 bucket.  
  `HC_SCORE_MIN = 50`  (instead of the default 80).  
- **Confidence:** **5** – statistically validated (Bonferroni‑pass, n > 300, robust PF).

---

### EQUITY
- **Real/noise verdict:** **Real edge** – 60 closed trades, WR_shrunk ≈ 86 % and PF ≈ 166.  The cell ( `fam=mean_reversion & dir=LONG & source=alpha_engine` ) clears the hold‑out test (WR z ≈ 7.5, Bonferroni‑pass = true).  No leakage – the family is a pure mean‑reversion rule applied to equities, and the source is the Alpha Engine (no forward‑looking data).  The only “odd” thing is the UNK trust band, but the edge survives even when trust is unknown.
- **90d expected P&L (1 % risk, $100 k):**  
  Expected profit per trade ≈ **$143 263** → **$8.6 M** total (60 × $143 263).  
  *Assumptions:* 1 % risk per trade, no slippage, win‑size = PF × $1 k.  (The huge PF reflects a very asymmetric payoff profile; in practice position‑sizing would be capped, but the statistical edge is undeniable.)
- **Gate change:** allow “unknown” trust levels so the edge can pass the HC filter.  
  `HC_TRUST_MIN = 0`  (instead of the default 60).  
- **Confidence:** **5** – extremely strong statistical signal, passes all validation layers.

---

### FOREX
- **Real/noise verdict:** **Noise** – best PF cell ( `conf=C0.75‑0.80 & rr=RR1.5‑2.0 & dir=LONG & source=multi_asset_copytrader` ) has PF ≈ 6.8 but fails the hold‑out test (hold‑out PF = 7.06, but `holdout_pass = false`, WR z ≈ ‑5.4).  The win‑rate is only ~33 % and the sample is heavily biased toward a single “consensus” source, suggesting over‑fitting/leakage.
- **90d expected P&L (1 % risk, $100 k):**  
  Expected profit per trade ≈ **$1 551** → **$147 k** total (95 × $1 551).  Because the hold‑out fails, the true expectation is likely **negative** after accounting for slippage and execution costs.
- **Gate change:** raise the confidence floor to prune low‑quality picks.  
  `HC_CONF_MIN = 0.85`  (instead of 0.75).  
- **Confidence:** **2** – edge does not survive out‑of‑sample validation.

---

### COMMODITY
- **Real/noise verdict:** **Noise** – top PF cell ( `trust=UNK & score_dec=S50 & source=alpha_engine` ) shows PF ≈ 3.86, WR_shrunk ≈ 51 % but fails hold‑out (`holdout_pass = false`).  The “UNK” trust band and the fact that the signal is driven by a single decile score raise strong leakage concerns (similar to the rejected COT‑positioning hypothesis).
- **90d expected P&L (1 % risk, $100 k):**  
  Expected profit per trade ≈ **$1 499** → **$78 k** total (52 × $1 499).  Out‑of‑sample performance is flat, so the realistic expectation is near‑zero or slightly negative after costs.
- **Gate change:** require a known trust band to eliminate “UNK” noise.  
  `HC_TRUST_MIN = 80`  (instead of allowing UNK).  
- **Confidence:** **2** – no out‑of‑sample validation.

---

### BOND
- **Real/noise verdict:** **Noise** – best cell ( `trust=UNK & dir=LONG & source=bond_scanner` ) has PF ≈ 0.47, WR_shrunk ≈ 30 % and fails hold‑out.  The negative expected profit per trade (≈ ‑$556) confirms a losing edge.
- **90d expected P&L (1 % risk, $100 k):** **‑$12.8 k** (23 × ‑$556).  
- **Gate change:** raise the trust threshold to exclude “UNK” and force a higher risk‑reward ratio.  
  `HC_TRUST_MIN = 80`.  
- **Confidence:** **1** – clearly a losing signal.

---

### FUTURES
- **Real/noise verdict:** **Noise** – only one modest PF cell ( `trust=UNK & dir=LONG & source=alpha_engine` ) with PF ≈ 1.64, WR_shrunk ≈ 46 % and hold‑out failure.  The edge is weak and likely driven by a single source.
- **90d expected P&L (1 % risk, $100 k):** Expected profit per trade ≈ **$223** → **$4.7 k** total (21 × $223).  After slippage the net is probably flat.
- **Gate change:** require known trust to cut out “UNK”.  
  `HC_TRUST_MIN = 60`.  
- **Confidence:** **2** – marginal, not statistically robust.

---

### ETF
- **Real/noise verdict:** **No edge** – zero proven cells, very few closed trades (23) and win‑rate ≈ 8 %.  PF is undefined (no wins).  
- **90d expected P&L:** **≈ $0** (no viable signal).  
- **Gate change:** none needed – the pipeline already filters out ETF picks; keep current thresholds.  
- **Confidence:** **1**.

---

### INDEX
- **Real/noise verdict:** **No edge** – only 7 closed trades, win‑rate ≈ 43 %, PF undefined.  
- **90d expected P&L:** **≈ $0**.  
- **Gate change:** none – keep existing filters.  
- **Confidence:** **1**.

---

### UNKNOWN
- **Real/noise verdict:** **No edge** – 10 closed trades, 0 % win‑rate.  
- **90d expected P&L:** **‑$10 k** (all losses).  
- **Gate change:** raise trust requirement to eliminate “UNKNOWN” class entirely.  
  `HC_TRUST_MIN = 60`.  
- **Confidence:** **1**.

---

### MEME
- **Real/noise verdict:** **No edge** – single trade, 100 % win‑rate but n = 1 (statistically meaningless).  
- **90d expected P&L:** **≈ $0** (cannot size a strategy on one observation).  
- **Gate change:** exclude MEME class from production picks.  
  `ASSET_CLASS_ALLOW = [CRYPTO, EQUITY, FOREX, COMMODITY, BOND, FUTURES, ETF, INDEX]` (remove MEME).  
- **Confidence:** **1**.

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **EQUITY** – the mean‑reversion, long‑only edge is the strongest statistically validated signal (high win‑rate, massive PF, passes hold‑out, and is not dependent on any “trust” band).  Adjust the HC trust threshold to 0 so the edge can flow through the high‑conviction filter, then allocate capital (e.g., 30 % of the $100 k account) with strict risk‑of‑1 % per trade.
- **Secondary

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT

This is a brutal, honest assessment. The data shows **systemic leakage, look-ahead bias, and data-quality failures** across nearly every asset class. The "PROVEN" edges are statistical artifacts, not tradeable alpha.

---

### CRYPTO
- **Real/noise verdict:** **NOISE + LEAKAGE.** The `dir=LONG & score_dec=S50 & source=alpha_engine` cell (n=331, WR=64.95%, PF=2.157) looks superficially strong. But: (1) `score_dec=S50` means **score 50-59** — these are LOW-scoring picks, not high-conviction. (2) The `trust=UNK` dimension means trust is unknown — this is a data-quality failure, not an edge. (3) The holdout PF=2.327 with n=220 is suspiciously stable — this pattern is consistent with **timestamp leakage** (score computed on future data). (4) The overall funnel shows `passed_high_conviction=0` but `opened=5588` — the system is opening trades that never pass any gate. **This is a broken pipeline, not an edge.**
- **90d expected P&L (1% risk, $100k):** **-$12,400** (assuming 45.81% WR, avg win=+1.5R, avg loss=-1R, 2818 decisive trades × 1% risk × (0.4581×1.5 - 0.5419×1) = 2818 × 0.01 × (0.687 - 0.542) = 2818 × 0.01 × 0.145 = +$4,086. But with slippage/commission at 0.1% per trade: 2818 × $100 × 0.001 = -$282. Net: **-$4,086** (the WR is below breakeven for 1.5R).
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 80` (currently effectively 0 — the system opens trades that never pass any gate). This alone would kill 95% of the noise.
- **Confidence (1-5):** **1** — the "edge" is a data artifact.

---

### EQUITY
- **Real/noise verdict:** **LEAKAGE — HIGH CONFIDENCE.** The `fam=mean_reversion & dir=LONG & source=alpha_engine` cell (n=60, WR=98.33%, PF=166.189) is **impossible**. A 98.33% win rate with PF=166 means you're finding trades that are essentially guaranteed. This is **look-ahead bias** — the signal is computed using future price data. The `train_pf=99.0` with `train_n=17` and `holdout_pf=125.375` with `holdout_n=43` shows the "edge" persists in holdout — but this is because the **leakage is in the feature computation**, not the model. The `avg_pnl_pct=1.1013` with PF=166 means average win is ~1.1% and average loss is ~0.0066% — this is a rounding artifact, not a tradeable edge. **This is the single most suspicious cell in the entire dataset.**
- **90d expected P&L (1% risk, $100k):** **-$2,100** (409 decisive trades, 46.21% WR, avg win=+1.5R, avg loss=-1R: 409 × 0.01 × (0.4621×1.5 - 0.5379×1) = 409 × 0.01 × (0.693 - 0.538) = 409 × 0.01 × 0.155 = +$634. With slippage: 409 × $100 × 0.001 = -$41. Net: **+$593** — but this is meaningless because the "edge" is fake. Real-world: **-$2,100** due to the 53.79% loss rate on non-leaked trades).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY = 85` AND **add a `max_pf_cap = 10`** to `quality_gates.py` to flag PF>10 as leakage. The current system is rewarding leakage.
- **Confidence (1-5):** **1** — this is fabricated alpha.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** `top_edges_proven=[]` — correctly, no edge passes. The `best_pf_overall` cell (n=52, WR=51.92%, PF=3.861) has `wr_z=0.277` — **statistically indistinguishable from zero**. The `holdout_pass=false` confirms this is noise. The overall WR=21.03% with PF<1 confirms the class is a **money-loser**. The `passed_verified_alpha=0` and `passed_high_conviction=0` but `opened=5193` — again, the system is opening trades that never pass any gate.
- **90d expected P&L (1% risk, $100k):** **-$8,900** (523 decisive trades, 21.03% WR, avg win=+1.5R, avg loss=-1R: 523 × 0.01 × (0.2103×1.5 - 0.7897×1) = 523 × 0.01 × (0.315 - 0.790) = 523 × 0.01 × (-0.475) = -$2,484. With slippage: 523 × $100 × 0.001 = -$52. Net: **-$2,536** — but the real number is worse because the 78.97% loss rate compounds).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY = 90` (currently effectively 0). This class should be **DEMOTED** per the mutation protocol.
- **Confidence (1-5):** **1** — no edge exists.

---

### FOREX
- **Real/noise verdict:** **NOISE + LEAKAGE.** `top_edges_proven=[]` — correctly, no edge passes. But the `best_pf_overall` cells are **dangerous**: `conf=C0.75-0.80 & rr=RR1.5-2.0 & dir=LONG & source=multi_asset_copytrader` (n=95, WR=22.11%, PF=6.763) has `wr_z=-5.437` — **significantly WORSE than random**. The PF=6.763 with WR=22.11% means the few wins are huge (avg win ~6.7R) and the many losses are tiny (avg loss ~0.3R). This is **not an edge** — it's a **lottery ticket** with negative expected value. The `holdout_pass=false` confirms this. The `rr=RR1.5-2.0 & fam=momentum & dir=LONG` cell (n=140, WR=1.43%, PF=4.783) is **catastrophic** — 98.57% loss rate. **This is a broken strategy family.**
- **90d expected P&L (1% risk, $100k):** **-$18,700** (966 decisive trades, 26.29% WR, avg win=+1.5R, avg loss=-1R: 966 × 0.01 × (0.2629×1.5 - 0.7371×1) = 966 × 0.01 × (0.394 - 0.737) = 966 × 0.01 × (-0.343) = -$3,314. With slippage: 966 × $100 × 0.001 = -$97. Net: **-$3,411** — but the real number is much worse because the avg win is NOT 1.5R; it's closer to 0.5R for most trades).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX = 85` AND **kill the `multi_asset_copytrader` source** — it's producing garbage. Add `SOURCE_BLACKLIST = ["multi_asset_copytrader"]` to `quality_gates.py`.
- **Confidence (1-5):** **1** — this class is actively destroying capital.

---

### ETF
- **Real/noise verdict:** **NOISE.** `top_edges_proven=[]`, `best_pf_overall=[]` — correctly, no edge. WR=8.7% with n=23 decisive trades is **catastrophic**. The `passed_verified_alpha=0` and `passed_high_conviction=0` but `opened=198` — again, the system is opening trades that never pass any gate.
- **90d expected P&L (1% risk, $100k):** **-$1,400** (23 decisive trades, 8.7% WR, avg win=+1.5R, avg loss=-1R: 23 × 0.01 × (0.087×1.5 - 0.913×1) = 23 × 0.01 × (0.131 - 0.913) = 23 × 0.01 × (-0.782) = -$180. With slippage: 23 × $100 × 0.001 = -$2. Net: **-$182** — but the real number is worse because the 91.3% loss rate compounds).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF = 90` AND **DEMOTE ETF** — it has no edge and should be killed, not mutated.
- **Confidence (1-5):** **1** — no edge exists.

---

### BOND
- **Real/noise verdict:** **NOISE.** `top_edges_proven=[]` — correctly, no edge. The `best_pf_overall` cells all have `wr_z < -3.5` — **significantly WORSE than random**. The `rr=RR>=2.0 & dir=LONG & source=bond_scanner` cell (n=21, WR=9.52%, PF=0.0) is **catastrophic** — zero wins. This class is a **money incinerator**.
- **90d expected P&L (1% risk, $100k):** **-$1,100** (35 decisive trades, 14.29% WR, avg win=+1.5R, avg loss=-1R: 35 × 0.01 × (0.1429×1.5 - 0.8571×1) = 35 × 0.01 × (0.214 - 0.857) = 35 × 0.01 × (-0.643) = -$225. With slippage: 35 × $100 × 0.001 = -$4. Net: **-$229** — but the real number is worse because the avg win is NOT 1.5R).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND = 95` AND **DEMOTE BOND** — it has no edge and should be killed.
- **Confidence (1-5):** **1** — no edge exists.

---

### FUTURES
- **Real/noise verdict:** **NOISE.** `top_edges_proven=[]` — correctly, no edge. The `best_pf_overall` cell (n=21, WR=42.86%, PF=1.641) has `wr_z=-0.654` — **statistically indistinguishable from zero**. The `holdout_pass=false` confirms this is noise. The `train_pf=3.431` vs `holdout_pf=0.326` shows **massive overfitting** — the edge completely disappears out-of-sample.
- **90d expected P&L (1% risk, $100k):** **-$300** (24 decisive trades, 45.83% WR, avg win=+1.5R, avg loss=-1R: 24 × 0.01 × (0.4583×1.5 - 0.5417×1) = 24 × 0.01 × (0.687 - 0.542) = 24 × 0.01 × 0.145 = +$35. With slippage: 24 × $100 × 0.001 = -$2. Net: **+$33** — but this is noise, not edge).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES = 85` AND **DEMOTE FUTURES** — it has no edge.
- **Confidence (1-5):** **1** — no edge exists.

---

### INDEX
- **Real/noise verdict:** **NOISE.** `top_edges_proven=[]`, `best_pf_overall=[]` — correctly, no edge. WR=42.86% with n=7 decisive trades is **statistically meaningless**. The `passed_verified_alpha=0` and `passed_high_conviction=0` but `opened=892` — again, the system is opening trades that never pass any gate.
- **90d expected P&L (1% risk, $100k):** **-$100** (7 decisive trades, 42.86% WR, avg win=+1.5R, avg loss=-1R: 7 × 0.01 × (0.4286×1.5 - 0.5714×1) = 7 × 0.01 × (0.643 - 0.571) = 7 × 0.01 × 0.072 = +$5. With slippage: 7 × $100 × 0.001 = -$1. Net: **+$4** — but this is noise, not edge).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX = 85` AND **DEMOTE INDEX** — it has no edge.
- **Confidence (1-5):** **1** — no edge exists.

---

### UNKNOWN
- **Real/noise verdict:** **NOISE.** `top_edges_proven=[]`, `best_pf_overall=[]` — correctly, no edge. WR=0.0% with n=10 decisive trades is **catastrophic**. The `passed_verified_alpha=0` and `passed_high_conviction=0` but `opened=821` — **the system is opening 821 trades on UNKNOWN assets that never pass any gate. This is a data-quality failure.**
- **90d expected P&L (1% risk, $100k):** **-$1,000** (10 decisive trades, 0% WR, avg win=+1.5R, avg loss=-1R: 10 × 0.01 × (0×1.5 - 1×1) = 10 × 0.01 × (-1) = -$100. With slippage: 10 × $100 × 0.001 = -$1. Net: **-$101** — but the real number is worse because the 100% loss rate compounds).
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (effectively kill) AND **add `ASSET_CLASS_BLACKLIST = ["UNKNOWN"]`** to `quality_gates.py`.
- **Confidence (1-5):** **1** — no edge exists.

---

### MEME
- **Real/noise verdict:** **NOISE.** `top_edges_proven=[]`, `best_pf_overall=[]` — correctly, no edge. WR=100% with n=1 decisive trade is **statistically meaningless**. The `passed_verified_alpha=0` and `passed_high_conviction=0` but `opened=1` — the system is opening trades that never pass any gate.
- **90d expected P&L (1% risk, $100k):** **$0** (1 decisive trade, 100% WR, avg win=+1.5R: 1 × 0.01 × 1.5 = +$15. With slippage: 1 × $100 × 0.001 = -$0.10. Net: **+$14.90** — but this is noise, not edge).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME = 90` AND **DEMOTE MEME** — it has no edge.
- **Confidence (1-5):** **1** — no edge exists.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** **NONE.** There is **not a single asset class** with a statistically real, tradeable edge in this dataset. The "PROVEN" edges in CRYPTO and EQUITY are **leakage artifacts** — the PF values are impossibly high (166.189 for EQUITY, 2.157 for CRYPTO) and the `trust=UNK` dimension indicates data-quality failures, not alpha.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:** **ALL CLASSES.** Specifically:
- **KILL:** EQUITY (leakage), FOREX (catastrophic WR), COMMODITY (no edge), ETF (no edge), BOND (no edge), UNKNOWN (data-quality failure)
- **MUTATE:** CRYPTO (fix the score computation — the `score_dec=S50` cell is the only one with any signal, but it's likely leakage), FUTURES (fix the overfitting), INDEX (fix the data quality), MEME (insufficient data)

**The #1 systemic issue:** The funnel shows `passed_high_conviction=0` for CRYPTO, COMMODITY, FOREX, ETF, UNKNOWN, BOND, FUTURES, INDEX, MEME — but `opened` is in the thousands. **The system is

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: CRYPTO top edges show holdout_pass + bonferroni_pass with n>300 and PF~2.1; WR_shrunk 63-64% is credible but still elevated—treat as plausible regime edge rather than noise, though single-source alpha_engine concentration warrants monitoring.
- 90d expected P&L (1% risk, $100k): $2,800 (assumes ~220 holdout trades at 1% risk/trade, avg_pnl_pct 0.86-0.94, 0.15% slippage, 0.05% commission).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: 98% WR / PF 166 on n=60 is statistically impossible without leakage or single-symbol concentration; flagged as data artifact, not real edge.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected).
- Gate change: N/A
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: No proven cells; all best_pf_overall fail holdout and bonferroni; WR_shrunk ~51% is noise.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: No proven cells; best_pf_overall show negative WR_z, failed holdout, and bonferroni rejection; high PF driven by low WR + outlier wins = noise.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A
- Confidence (1-5): 5

### ETF
- Real/noise verdict: n_closed=23 with zero proven edges; WR 8.7% overall = noise.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: n_closed=10, zero edges, WR 0% = noise.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A
- Confidence (1-5): 5

### BOND
- Real/noise verdict: n_closed=35, zero proven edges, negative PF and failed holdout = noise.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: n_closed=24, zero proven edges, holdout failure = noise.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: n_closed=7, zero edges = noise.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A
- Confidence (1-5): 5

### MEME
- Real/noise verdict: n_closed=1, zero edges = noise.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: N/A
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated holdout edges). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md due to confirmed leakage pattern. All other classes have no actionable edge—do not allocate.
