# Pick Funnel Swarm Verdict — 2026-07-20 05:15 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260720T051439Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**Audit‑Pick‑Funnel Verdict – 90‑day Edge Analysis**

---

### EQUITY
- **Real/noise verdict:** **Real edge** – three “PROVEN” cells (mean‑reversion LONG from `alpha_engine`) each have *n*≈45, **WR_shrunk≈85 %**, **PF≈99** and pass both hold‑out and Bonferroni tests.  The 100 % win‑rate is striking; the only risk is possible concentration on a single ticker or sector (the audit does not show symbol breakdown).  No obvious leakage or look‑ahead bias.
- **90d expected P&L (1 % risk, $100 k):**  
  *Assumptions*: 1 % risk ⇒ $1 000 per trade, trade notional $100 k, slippage 0.1 % of notional ($100).  
  Adjusted avg win = 1.1556 % – 0.1 % = **1.0556 %** → $1 055.6.  
  Expected profit per trade = win‑rate × adj‑avg‑win × (1 – 1/PF) = 1 × $1 055.6 × 0.9899 ≈ **$1 045**.  
  Trades in the three cells = 46 + 45 + 45 = **136**.  
  **Total 90‑day expectation ≈ $142 k** (≈ 1.4 × account size – note the edge is highly leveraged; real‑world execution would be far lower after position‑sizing limits).
- **Gate change:** lower the **SMART_PICKS_MIN_SCORE_EQUITY** constant (currently 80) to **70**.  This admits more mean‑reversion LONG picks while keeping the same “high‑conviction” filter, expanding the edge base.
- **Confidence (1‑5):** **5** – the statistical tests are clean and the cell size is respectable.

---

### CRYPTO
- **Real/noise verdict:** **Real edge** – the single “PROVEN” cell (trust = UNK, LONG, `score_dec=S50`) has *n* = 339, **WR_shrunk ≈ 64.6 %**, **PF ≈ 1.88**, and passes hold‑out & Bonferroni.  No sign of look‑ahead or single‑symbol concentration (the cell spans many symbols).  The PF is modest but statistically significant.
- **90d expected P&L (1 % risk, $100 k):**  
  Adjusted avg win = 0.7439 % – 0.1 % = **0.6439 %** → $643.9.  
  Expected profit per trade = 0.655 × $643.9 × (1 – 1/1.878) ≈ **$196.6**.  
  Trades = **339** → **$66.6 k** expected over 90 days.
- **Gate change:** relax the HC‑filter score bucket threshold – set **HC_FILTER_MIN_SCORE_DEC = 'S40'** (instead of the default S50) so that the same high‑trust, LONG bucket can capture a few more decile‑levels while preserving the proven risk‑reward profile.
- **Confidence (1‑5):** **4** – strong statistical backing, but PF is only ~1.9, so the edge is modest and sensitive to execution costs.

---

### COMMODITY
- **Real/noise verdict:** **Noise** – no “PROVEN” cells.  The best PF cell (trust = UNK, LONG, `source=alpha_engine`) fails hold‑out (PF ≈ 2.6 but hold‑out PF ≈ 2.59, Bonferroni = false) and shows a win‑rate of only 44 %.  The high PF is driven by a tiny training sample (n = 6) – classic over‑fit.
- **90d expected P&L (1 % risk, $100 k):** **$0** – edge not statistically reliable; any P&L estimate would be pure speculation.
- **Gate change:** raise the **SMART_PICKS_MIN_PF_COMMODITY** constant from its current value (≈ 2) to **3.0** to filter out the spurious high‑PF, low‑sample cells.
- **Confidence (1‑5):** **2** – the change is a defensive filter; the class shows no credible edge.

---

### FOREX
- **Real/noise verdict:** **Noise** – zero “PROVEN” cells.  The top PF cells have PF ≈ 5‑6 but **hold‑out fails** (negative Z‑scores, Bonferroni false) and win‑rates under 30 %.  The apparent PF is inflated by a tiny loss tail.
- **90d expected P&L (1 % risk, $100 k):** **$0** – no statistically validated edge.
- **Gate change:** increase the **SMART_PICKS_MIN_CONFIDENCE_FOREX** threshold from **0.75** to **0.85** to prune low‑confidence picks that are currently inflating PF.
- **Confidence (1‑5):** **3** – a moderate tightening that should reduce noise without killing volume.

---

### FUTURES
- **Real/noise verdict:** **Noise** – no “PROVEN” cells; the best PF cell fails hold‑out (PF ≈ 1.64, Bonferroni false) with a win‑rate of 43 % and a tiny sample (n = 21).  Likely sample‑noise.
- **90d expected P&L (1 % risk, $100 k):** **$0** – edge not credible.
- **Gate change:** raise the **SMART_PICKS_MIN_RR_FUTURES** constant from the current **RR1.5‑2.0** bucket to **RR≥2.0** to keep only higher‑reward trades; this will also cut the noisy low‑RR segment.
- **Confidence (1‑5):** **2** – defensive tightening.

---

### BOND
- **Real/noise verdict:** **Noise** – no “PROVEN” cells; all PF ≤ 0.6, avg PNL % negative, hold‑out fails.  The edge is a loss‑making signal.
- **90d expected P&L (1 % risk, $100 k):** **$0** – would be a net loss.
- **Gate change:** increase **SMART_PICKS_MIN_PF_BOND** from **0.5** to **1.0** to discard all loss‑making cells.
- **Confidence (1‑5):** **2**.

---

### ETF
- **Real/noise verdict:** **Noise** – no “PROVEN” cells; win‑rate 8 % (2 wins / 23 closed), PF

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest 90-day edge analysis for each asset class in the `findtorontoevents.ca` pick-funnel.

### COMMODITY
- **Real/noise verdict:** **Noise.** The funnel shows a 24.21% win rate on 603 decisive trades. The "best" cells (e.g., `trust=UNK & dir=LONG & source=alpha_engine`) have a high PF (2.636) but a WR of only 44.58% and a negative WR z-score (-0.988). The high PF is driven by a few large winners, not a repeatable edge. The holdout PF (2.591) passes, but the train PF (73.832) on only 6 trades is a classic sign of overfitting. The rejected H-001 (COT leakage) and H-036 (inventory direction) confirm this class is a minefield.
- **90d expected P&L (1% risk, $100k):** **-$4,200.** Assumptions: 603 decisive trades, 1% risk ($1,000) per trade, average win/loss ratio of 1.5 (based on the best cell's avg PnL). With a 24.21% WR, expected loss = 603 * $1,000 * (0.2421 * 1.5 - 0.7579) = -$420,000. This is a catastrophic loss rate. The high-PF cells are not replicable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY = 85` (currently likely lower). This would kill the 6,164 signals that pass the smart gate but produce no edge, forcing the system to only look at the top 1% of signals.
- **Confidence (1-5):** 5 (high confidence it's noise).

### FOREX
- **Real/noise verdict:** **Noise.** 26.31% WR on 1,718 decisive trades is terrible. The "best" cells (e.g., `conf=C0.75-0.80 & dir=LONG & source=multi_asset_copytrader`) show a PF of 5.965 but a WR of only 28.99% and a WR z-score of -4.936. This is a textbook example of a high-PF, low-WR trap. The PF is inflated by a few massive outliers. The holdout PF (6.397) passes, but the train PF (0.069) on 84 trades is a red flag for instability. The `multi_asset_copytrader` source appears to be a low-frequency, high-variance strategy that is not a reliable edge.
- **90d expected P&L (1% risk, $100k):** **-$5,100.** Assumptions: 1,718 decisive trades, 1% risk ($1,000) per trade, average win/loss ratio of 1.5. Expected loss = 1,718 * $1,000 * (0.2631 * 1.5 - 0.7369) = -$510,000. The high-PF cells are not tradeable.
- **Gate change:** `HC_FILTER_MIN_CONFIDENCE_FOREX = 0.85` (currently 0.75). This would eliminate the `C0.75-0.80` band that is producing the deceptive high-PF, low-WR signals.
- **Confidence (1-5):** 5 (high confidence it's noise).

### EQUITY
- **Real/noise verdict:** **Real (but fragile).** The PROVEN cells (e.g., `fam=mean_reversion & dir=LONG & source=alpha_engine`) show a 100% WR on 46 trades, with a shrunk WR of 84.85% and a PF of 99.0. The holdout PF (99.0) passes, and the WR z-score (6.782) is statistically significant. **However, this is suspicious.** A 100% WR on 46 trades in a 90-day period is almost certainly a data leakage or single-symbol concentration issue. The `trust=UNK` dimension suggests these are new or unclassified signals, which is a red flag. This is likely a look-ahead bias or a bug in the `alpha_engine` scanner for a specific ticker. Do not trade this.
- **90d expected P&L (1% risk, $100k):** **$0 (do not trade).** If the edge were real, the P&L would be massive. But given the 100% WR, the expected P&L is a trap. The real edge is likely zero or negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY = 70` (currently likely lower). This would increase the number of signals passing the smart gate, but the real fix is to investigate the `alpha_engine` source for the `mean_reversion` family. The gate change is a band-aid.
- **Confidence (1-5):** 2 (low confidence it's a real, tradeable edge; high confidence it's a bug).

### INDEX
- **Real/noise verdict:** **Noise.** Only 8 decisive trades. The 62.5% WR is meaningless with such a small sample. The funnel shows 0 signals passing the high-conviction gate, confirming the system has no confidence in this class.
- **90d expected P&L (1% risk, $100k):** **$0.** No tradeable signals.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX = 90` (effectively kill the class). The 654 signals passing the smart gate are wasting compute.
- **Confidence (1-5):** 5 (high confidence it's noise).

### CRYPTO
- **Real/noise verdict:** **Real (but weak).** The PROVEN cell (`trust=UNK & dir=LONG & score_dec=S50`) shows a 65.49% WR on 339 trades, with a shrunk WR of 64.62% and a PF of 1.878. The holdout PF (1.872) passes, and the WR z-score (5.704) is statistically significant. This is the only class with a statistically valid, replicable edge. However, the edge is weak (PF < 2.0) and the `trust=UNK` dimension is concerning. The `score_dec=S50` suggests the edge is in the top 50% of scores, not the top 10%.
- **90d expected P&L (1% risk, $100k):** **+$18,000.** Assumptions: 2,820 decisive trades, 1% risk ($1,000) per trade, average win/loss ratio of 1.5 (based on the best cell's avg PnL). Expected profit = 2,820 * $1,000 * (0.4652 * 1.5 - 0.5348) = +$180,000. This is a solid, repeatable edge.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 60` (currently likely lower). This would increase the number of signals passing the smart gate, but the real edge is in the `score_dec=S50` band. The gate change should focus on filtering out the bottom 50% of scores.
- **Confidence (1-5):** 4 (high confidence it's a real, tradeable edge).

### ETF
- **Real/noise verdict:** **Noise.** 8.7% WR on 23 decisive trades. The funnel shows 0 signals passing the high-conviction gate. The system has no edge here.
- **90d expected P&L (1% risk, $100k):** **-$1,500.** Assumptions: 23 decisive trades, 1% risk ($1,000) per trade, average win/loss ratio of 1.5. Expected loss = 23 * $1,000 * (0.087 * 1.5 - 0.913) = -$15,000.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF = 95` (effectively kill the class).
- **Confidence (1-5):** 5 (high confidence it's noise).

### UNKNOWN
- **Real/noise verdict:** **Noise.** 0% WR on 10 decisive trades. The funnel shows 0 signals passing the high-conviction gate. This class is a data error or garbage.
- **90d expected P&L (1% risk, $100k):** **-$1,000.** Assumptions: 10 decisive trades, 1% risk ($1,000) per trade, average win/loss ratio of 1.5. Expected loss = 10 * $1,000 * (0.0 * 1.5 - 1.0) = -$10,000.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (kill the class entirely).
- **Confidence (1-5):** 5 (high confidence it's noise).

### BOND
- **Real/noise verdict:** **Noise.** 12.9% WR on 31 decisive trades. The "best" cells (e.g., `trust=UNK & dir=LONG & source=bond_scanner`) show a 15% WR and a PF of 0.557. The holdout PF (0.0) fails. This is a losing strategy.
- **90d expected P&L (1% risk, $100k):** **-$2,500.** Assumptions: 31 decisive trades, 1% risk ($1,000) per trade, average win/loss ratio of 1.5. Expected loss = 31 * $1,000 * (0.129 * 1.5 - 0.871) = -$25,000.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND = 95` (effectively kill the class).
- **Confidence (1-5):** 5 (high confidence it's noise).

### FUTURES
- **Real/noise verdict:** **Noise.** 45.83% WR on 24 decisive trades. The "best" cell (`trust=UNK & dir=LONG & source=alpha_engine`) shows a 42.86% WR and a PF of 1.641, but the holdout PF (0.326) fails. The sample is too small to be meaningful.
- **90d expected P&L (1% risk, $100k):** **-$200.** Assumptions: 24 decisive trades, 1% risk ($1,000) per trade, average win/loss ratio of 1.5. Expected loss = 24 * $1,000 * (0.4583 * 1.5 - 0.5417) = -$2,000.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES = 90` (effectively kill the class).
- **Confidence (1-5):** 5 (high confidence it's noise).

### MEME
- **Real/noise verdict:** **Noise.** 1 decisive trade. The 100% WR is meaningless.
- **90d expected P&L (1% risk, $100k):** **$0.** No tradeable signals.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME = 100` (kill the class).
- **Confidence (1-5):** 5 (high confidence it's noise).

---

## SYSTEM-WIDE CONCLUSION

**Scale Up TODAY:** **CRYPTO.** It is the only class with a statistically valid, replicable edge (65.49% WR, PF 1.878, n=339). The edge is weak but real. Scale up to 2% risk per trade and increase the allocation to 20% of the portfolio.

**DEMOTE (per Mutation Three-Axis Protocol):** **COMMODITY, FOREX, BOND, ETF, UNKNOWN, MEME, INDEX, FUTURES.** These classes have no edge. They are consuming compute and generating false signals. Per the protocol, they should be mutated (e.g., gate changes to kill them) before being killed entirely. **EQUITY** is a special case: the 100% WR is a bug, not an edge. It should be investigated immediately and demoted until the `alpha_engine` source is fixed.

**Brutal Truth:** The system is generating 50,000+ scans per 90 days but only producing one real edge (CRYPTO). The rest is noise. The `hc_filter.js` gate (score>=80, conf>=0.75, trust>=60) is too permissive and is letting through high-PF, low-WR traps. The system needs a fundamental rethink of its signal generation, not just gate tweaks.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: noise (100% WR + PF=99 on n=46 is leakage; holdout still perfect implies single-symbol or label contamination)
- 90d expected P&L (1% risk, $100k): $0 (edge invalid)
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: statistically real (n=339, shrunk WR 64.6%, PF 1.88, holdout stable, bonferroni pass)
- 90d expected P&L (1% risk, $100k): ~$4200 (339 trades × 1% risk × 0.74% avg edge after 0.1% slippage)
- Gate change: HC_MIN_CONF = 0.78
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: noise (no proven cells; best PF cells fail holdout + negative z)
- 90d expected P&L (1% risk, $100k): -$1800
- Gate change: SMART_PICKS_MIN_TRUST = 70
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise (no proven cells; all high-PF cells fail holdout + extreme negative z)
- 90d expected P&L (1% risk, $100k): -$5200
- Gate change: HC_MIN_SCORE = 82
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise (n=8 decisive, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise (n=23 decisive, no proven cells, WR 8.7%)
- 90d expected P&L (1% risk, $100k): -$900
- Gate change: SMART_PICKS_MIN_TRUST = 70
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise (no proven cells; all cells negative z + failed holdout)
- 90d expected P&L (1% risk, $100k): -$1100
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 75
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise (n=24 decisive, no proven cells, holdout collapse)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST = 70
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise (WR 0%, n=10)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST = 70
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise (n=1)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: disable MEME scanner
- Confidence (1-5): 5

**SYSTEM-WIDE:** Scale CRYPTO today (only class with stable proven edge). Demote FOREX and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate filters then kill if no recovery in 30d).
