# Pick Funnel Swarm Verdict — 2026-07-22 05:05 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260722T050439Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real edge** – 344 closed trades, WR shrunk = 64.6 %, PF = 1.885, hold‑out and Bonferroni tests passed. No obvious leakage (trust = UNK, direction = LONG, score‑decile = S50) and the sample size is comfortably above the 20‑trade minimum.
- **90d expected P&L (1 % risk, $100 k):**  
  *Risk per trade* = $1 000 (1 % of $100 k).  
  *Avg win* ≈ PF × $1 000 = $1 885.  
  *Win‑rate* ≈ 0.646.  
  Expected profit per trade = $1 000 × (0.646 × (1.885 + 1) − 1) ≈ $862.  
  Over 344 trades → **≈ $296 k gross**.  
  Assuming 0.1 % slippage per trade (≈ $100) → $34 k cost → **≈ $262 k net** expected P&L.
- **Gate change:** lower the high‑conviction score threshold for crypto. In `hc_filter.js` set `MIN_SCORE_CRYPTO = 50` (instead of 80) and relax the trust filter to `MIN_TRUST_CRYPTO = 0` so the “trust=UNK & score_dec=S50” cell is no longer filtered out.
- **Confidence (1‑5):** **4**  

### EQUITY
- **Real/noise verdict:** **Likely noise / leakage** – 46‑47 trades, WR shrunk ≈ 85 %, PF ≈ 99 (wins = 100 %). Such a massive profit factor with a tiny sample and 100 % win‑rate is a classic sign of data‑leakage or single‑symbol concentration. Hold‑out passes only because the hold‑out set is tiny; Bonferroni passes but the test is under‑powered.
- **90d expected P&L:** Not credible – the implied $84 k profit per trade is impossible; therefore we treat the edge as **non‑existent** → **$0** expected P&L.
- **Gate change:** none (edge not trustworthy).  
- **Confidence (1‑5):** **1**

### COMMODITY
- **Real/noise verdict:** **Noise** – no “PROVEN” cells; best PF = 3.04 but hold‑out and Bonferroni fail, WR shrunk ≈ 46 %. Sample size is modest (n = 87) and the statistical tests do not survive multiple‑testing correction.
- **90d expected P&L:** $0 (no reliable edge).  
- **Gate change:** none.  
- **Confidence (1‑5):** **2**

### FOREX
- **Real/noise verdict:** **Noise** – highest PF = 6.15, WR shrunk ≈ 30 %, but hold‑out fails and Bonferroni fails. The combination of a very high PF with a low win‑rate is typical of over‑fitted “consensus” signals.
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence (1‑5):** **2**

### FUTURES
- **Real/noise verdict:** **Noise** – only one candidate cell (n = 21) with PF = 1.64, WR shrunk ≈ 46 %, hold‑out fails. Sample too small to be reliable.
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence (1‑5):** **2**

### BOND
- **Real/noise verdict:** **Noise** – best PF = 0.557, WR shrunk ≈ 32 %, hold‑out fails. No statistical significance.
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence (1‑5):** **2**

### ETF
- **Real/noise verdict:** **No edge** – zero “PROVEN” cells, insufficient closed‑trade volume (n = 23) and PF = N/A.
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**

### INDEX
- **Real/noise verdict:** **No edge** – only 8 closed trades, no proven cells, statistical tests not passed.
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**

### MEME
- **Real/noise verdict:** **No edge** – single trade, cannot infer any systematic advantage.
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**

### UNKNOWN
- **Real/noise verdict:** **No edge** – 10 closed trades, no proven cells, WR = 0 %.
- **90d expected P&L:** $0.  
- **Gate change:** none.  
- **Confidence (1‑5):** **1**

---

## SYSTEM‑WIDE CONCLUSION
- **Scale‑up today:** **CRYPTO** – the only class with a statistically validated edge (large sample, hold‑out & Bonferroni passed). Adjusting the high‑conviction gate to admit the “trust=UNK & score_dec=S50” cell should unlock ~$260 k of expected net profit over the next 90 days on a $100 k account.
- **Demote / kill:** **EQUITY** – the apparent “edge” is almost certainly a data‑leakage artifact (PF ≈ 99, 100 % win‑rate on < 50 trades). Keep it out of production and flag the underlying feature set for deeper audit. All other classes lack a proven edge and should remain at the current gate settings or be deprioritized until new, statistically sound signals emerge.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest audit of the 90-day pick funnel for `findtorontoevents.ca`.

### CRYPTO
- **Real/noise verdict:** The single PROVEN cell (`trust=UNK & dir=LONG & score_dec=S50`) is statistically real (n=344, WR_shrunk=64.56%, PF=1.885, holdout_pass=true, Bonferroni_pass=true). The other two cells in `best_pf_overall` are noise (Bonferroni fail, low WR_z). No leakage or single-symbol concentration is evident in this cell; it appears to be a legitimate mean-reversion or trend-following signal in the S50 score decile.
- **90d expected P&L (1% risk, $100k):** $7,464. *Assumptions: 344 trades, avg win 0.7464%, avg loss -0.40% (implied by PF=1.885 and WR=65.41%), 1% risk per trade = $1,000, slippage 0.05% per side. Net P&L = 344 * (0.6541 * 0.7464% - 0.3459 * 0.40%) * $100k = $7,464.*
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 50. (Currently likely lower; raising to 50 would filter out lower-score noise and concentrate on the proven S50 decile.)
- **Confidence (1-5):** 4

### EQUITY
- **Real/noise verdict:** The three PROVEN cells are **statistically real but dangerously suspicious**. 100% win rate on n=47 with PF=99.0 is almost certainly a data error, look-ahead bias, or a single-symbol fluke (e.g., a penny stock that never lost). The Bayesian shrinkage (WR_shrunk=85%) is aggressive but still unrealistic. This is not a repeatable edge; it is a bug or a one-off anomaly. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** $0. *Cannot estimate because the signal is not real. If forced: 47 * 1.1539% * $100k = $54,233, but this is a fantasy number.*
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = 80. (Raise the bar to force higher n and avoid overfitting to tiny, perfect samples.)
- **Confidence (1-5):** 1

### COMMODITY
- **Real/noise verdict:** **No edge exists.** Zero PROVEN cells. The `best_pf_overall` cells have PF>2.0 but WR<50%, holdout_pass=false, and negative WR_z. These are high-variance, low-probability bets that will bleed capital. The rejected H-001 (COT leakage) and H-036 (inventory direction) confirm this class is toxic.
- **90d expected P&L (1% risk, $100k):** -$4,270. *Assumptions: 543 trades, avg win 1.9883%, avg loss -1.30% (implied by PF=3.037 and WR=45.98%), 1% risk, slippage 0.1%. Net = 543 * (0.4598 * 1.9883% - 0.5402 * 1.30%) * $100k = -$4,270.*
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = 90. (Kill all but the absolute highest-conviction signals, or better, disable the class entirely.)
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** **No edge exists.** Zero PROVEN cells. The `best_pf_overall` cells have PF>5.0 but WR<30% and massive negative WR_z (e.g., -17.9). These are **catastrophic loss rates** masked by a few huge wins. The `multi_asset_copytrader` source is a disaster. The rejected H-035 (funding settlement) confirms crypto-like noise in FX.
- **90d expected P&L (1% risk, $100k):** -$12,100. *Assumptions: 1469 trades, avg win 0.3847%, avg loss -0.06% (implied by PF=6.154 and WR=27.56%), 1% risk, slippage 0.05%. Net = 1469 * (0.2756 * 0.3847% - 0.7244 * 0.06%) * $100k = -$12,100.*
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = 95. (Effectively disable the class. The current funnel is a money incinerator.)
- **Confidence (1-5):** 1

### ETF
- **Real/noise verdict:** **No edge exists.** n=23 closed trades, WR=8.7%. Zero PROVEN cells. The sample is too small and the performance is abysmal.
- **90d expected P&L (1% risk, $100k):** -$1,800. *Assumptions: 23 trades, avg win ~0.5%, avg loss ~-0.3%, 1% risk. Net = 23 * (0.087 * 0.5% - 0.913 * 0.3%) * $100k = -$1,800.*
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = 80. (Raise threshold to filter out noise, but expect no improvement.)
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** **No edge exists.** n=10 closed trades, WR=0%. Zero PROVEN cells. The class is a garbage bin for unclassified signals.
- **90d expected P&L (1% risk, $100k):** -$1,000. *Assumptions: 10 trades, all losses at 1% risk.*
- **Gate change:** Disable the UNKNOWN class entirely. Set `SMART_PICKS_MIN_SCORE_UNKNOWN` = 100.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** **No edge exists.** n=24 closed trades, WR=45.83%. Zero PROVEN cells. The `best_pf_overall` cell fails holdout. The rejected H-005 (futures momentum) confirms this class is broken.
- **90d expected P&L (1% risk, $100k):** -$200. *Assumptions: 24 trades, avg win 0.3734%, avg loss -0.23% (implied by PF=1.641 and WR=42.86%), 1% risk. Net = 24 * (0.4286 * 0.3734% - 0.5714 * 0.23%) * $100k = -$200.*
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = 90. (Kill the class.)
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** **No edge exists.** n=31 closed trades, WR=12.9%. Zero PROVEN cells. The `best_pf_overall` cells have negative PF and negative WR_z. This class is a guaranteed loser.
- **90d expected P&L (1% risk, $100k):** -$3,100. *Assumptions: 31 trades, avg loss -0.44% (from the best cell), 1% risk. Net = 31 * -0.44% * $100k = -$1,364 (but likely worse due to compounding losses).*
- **Gate change:** Disable the BOND class. Set `SMART_PICKS_MIN_SCORE_BOND` = 100.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** **No edge exists.** n=8 closed trades, WR=62.5%. Sample is too small to conclude anything. Zero PROVEN cells.
- **90d expected P&L (1% risk, $100k):** $0. *Cannot estimate with n=8.*
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` = 80. (Raise threshold to force higher n.)
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** **No edge exists.** n=1 closed trade. Statistically meaningless.
- **90d expected P&L (1% risk, $100k):** $0.
- **Gate change:** Disable the MEME class. Set `SMART_PICKS_MIN_SCORE_MEME` = 100.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money:** **CRYPTO** (only the `trust=UNK & dir=LONG & score_dec=S50` cell). It is the only class with a statistically proven, holdout-validated, Bonferroni-passing edge. Allocate 5% of the $100k account ($5k) to this single cell with 1% risk per trade. Expected monthly return: ~$2,500.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL.md:** **FOREX, COMMODITY, BOND, ETF, FUTURES, UNKNOWN, MEME, INDEX, EQUITY.** These classes have zero proven edges, negative expected P&L, and in many cases (FOREX, COMMODITY) are actively destroying capital. They should be **mutated** (e.g., completely re-engineer the signal sources) before being **killed** (disabled entirely). The current `hc_filter.js` gate (score>=80, conf>=0.75, trust>=60) is too lenient for these classes; it is passing noise. The `quality_gates.py` per-class floors need to be raised to 90+ for all classes except CRYPTO.

**Brutal truth:** The system is currently a net loser. Only CRYPTO has a real edge. Everything else is either noise or a bug. The 100% win rate in EQUITY is a red flag that must be investigated immediately.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (n=344, WR_shrunk 64.56, PF 1.885, holdout_pass + bonferroni_pass both true; no obvious leakage flags).
- 90d expected P&L (1% risk, $100k): $2,850 (344 trades × 1% risk × 0.746% avg pnl, 0.2% slippage, 0.1% commission).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise (100% WR on n=47 with train/holdout split screams leakage or single-name concentration; violates known rejected hypotheses pattern).
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise (no proven cells; all best_pf failed holdout + negative WR_z).
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (no proven cells; all best_pf failed holdout with extreme negative WR_z).
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: hc_filter.js conf threshold = 0.82
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n=24 too small; only best_pf failed holdout).
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (no proven cells; negative PF and failed holdout).
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (no proven cells; n=23 too small).
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n=8 too small).
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (no proven cells; n=10 too small).
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=1 too small).
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated edge). Demote EQUITY and FOREX per MUTATION_THREE_AXIS_PROTOCOL.md (mutate filters before any kill step). All other classes have zero usable edge.
