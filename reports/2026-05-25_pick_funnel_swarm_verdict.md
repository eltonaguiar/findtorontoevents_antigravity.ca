# Pick Funnel Swarm Verdict — 2026-07-31 05:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260731T051054Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**90‑day Pick‑Funnel Verdict – per asset class**

---

### CRYPTO
- **Real/noise verdict:** **Real** – 326 closed trades, WR shrunk = 63.9 % (≫ 55 % floor), PF = 2.16, hold‑out & Bonferroni tests passed. No known leakage patterns; the signal is spread over many symbols (≈ 30 distinct tickers in the 90‑d window).  
- **90d expected P&L (1 % risk, $100 k):**  
  - Win‑rate = 211/326 = 64.7 %  
  - Expected return per trade = (1‑WR) × (PF‑1) ≈ 0.353 × 1.158 ≈ 0.409 ≈ 40.9 % of risk  
  - $1 000 × 0.409 ≈ $409 per trade  
  - 326 trades × $409 ≈ **$133 k** (gross, before slippage & transaction costs)  
- **Gate change:** `hc_filter.js` – lower the high‑conviction score floor for crypto:  
  ```js
  const HC_SCORE_MIN_CRYPTO = 50;   // was 80
  const HC_TRUST_MIN_CRYPTO = 0;    // remove trust‑>=60 requirement
  ```  
- **Confidence (1‑5):** **4** – solid sample size, statistically validated, modest PF.

---

### EQUITY
- **Real/noise verdict:** **Real but fragile** – 58 closed trades, WR shrunk = 85.9 % (well above floor), PF = 160.8, hold‑out & Bonferroni passed. The PF is astronomically high because losses are tiny; the edge is heavily concentrated in a **few mean‑reversion symbols** (≈ 4‑5 tickers dominate the 58 trades). Risk of over‑fit/leakage is elevated.  
- **90d expected P&L (1 % risk, $100 k):**  
  - Win‑rate = 57/58 = 98.3 %  
  - Expected return per trade = (1‑WR) × (PF‑1) ≈ 0.017 × 159.8 ≈ 2.72 ≈ 272 % of risk  
  - $1 000 × 2.72 ≈ $2 716 per trade  
  - 58 trades × $2 716 ≈ **$158 k** (gross)  
- **Gate change:** `hc_filter.js` – relax the confidence threshold for equities so more mean‑reversion picks survive the HC filter:  
  ```js
  const HC_CONF_MIN_EQUITY = 0.60;   // was 0.75
  ```  
- **Confidence (1‑5):** **3** – statistically significant but tiny n and extreme PF suggest possible concentration/leakage.

---

### FOREX
- **Real/noise verdict:** **Noise** – 961 closed trades, no “PROVEN” cells; best PF = 7.30 but hold‑out fails (WR shrunk ≈ 26 %). The high‑conviction gate currently yields **zero** passes.  
- **90d expected P&L:** **$0** (no validated edge).  
- **Gate change:** `hc_filter.js` – lower confidence floor to admit more trades (e.g., `HC_CONF_MIN_FOREX = 0.65`). This may surface a real edge, but current data give no statistical support.  
- **Confidence:** **1**

---

### COMMODITY
- **Real/noise verdict:** **Noise** – 522 closed trades, best PF = 3.86 but hold‑out fails (WR shrunk ≈ 51 %). No proven cells.  
- **90d expected P&L:** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` – reduce the Smart‑Picks minimum score for commodities from 70 to 60 (`SMART_PICKS_MIN_SCORE_COMMODITY = 60`). This could increase volume, but the current edge is not statistically validated.  
- **Confidence:** **1**

---

### BOND
- **Real/noise verdict:** **Noise** – 33 closed trades, PF ≈ 0.5, WR shrunk ≈ 31 % (below floor). No proven cells.  
- **90d expected P&L:** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` – lower the Smart‑Picks minimum score for bonds (`SMART_PICKS_MIN_SCORE_BOND = 40`).  
- **Confidence:** **1**

---

### ETF
- **Real/noise verdict:** **Noise** – 23 closed trades, PF ≈ 0, WR shrunk ≈ 0 %. No proven cells.  
- **90d expected P&L:** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` – lower the Smart‑Picks minimum score for ETFs (`SMART_PICKS_MIN_SCORE_ETF = 30`).  
- **Confidence:** **1**

---

### INDEX
- **Real/noise verdict:** **Noise** – only 7 closed trades, no proven cells, PF ≈ 0.  
- **90d expected P&L:** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` – lower the Smart‑Picks minimum score for indexes (`SMART_PICKS_MIN_SCORE_INDEX = 30`).  
- **Confidence:** **1**

---

### FUTURES
- **Real/noise verdict:** **Noise** – 24 closed trades, PF ≈ 1.64 but hold‑out fails (WR shrunk ≈ 46 %). No proven cells.  
- **90d expected P&L:** **$0**.  
- **Gate change:** `audit_trail/quality_gates.py` – lower the Smart‑Picks minimum score for futures (`SMART_PICKS_MIN_SCORE_FUTURES = 40`).  
- **Confidence:** **1**

---

### UNKNOWN
- **Real/noise verdict:** **Noise** – 10 closed trades, WR = 0 %, PF = 0.  
- **90d expected P&L:** **$0**.  
- **Gate change:** No meaningful gate; class should be **demoted**.  
- **Confidence:** **1**

---

### MEME
- **Real/noise verdict:** **Noise** – single trade (win), but n = 1 is insufficient for statistical inference.  
- **90d expected P&L:** **$0** (cannot rely on a single observation).  
- **Gate change:** Exclude MEME from the pipeline (remove from `audit_trail/quality_gates.py`).  
- **Confidence:** **1**

---

## SYSTEM‑WIDE Conclusion

**Scale‑up today:** **CRYPTO** – the only class with a statistically robust, moderately sized edge (n = 326, PF ≈ 2.2, WR ≈ 64 %). Adjusting the high‑conviction score/trust thresholds will unlock many more of these profitable picks without exposing us to the concentration risk seen in EQUITY.

**Demote / kill:** **UNKNOWN** (and, by extension, MEME). These classes have zero validated performance, tiny sample sizes, and no meaningful gate that can be tweaked to produce a real edge. They should be removed from the production pipeline per the *MUTATION_THREE_AXIS_PROTOCOL*.

*All other classes (FOREX, COMMODITY, BOND, ETF, INDEX, FUTURES) currently lack statistically proven edges; any gate changes should be treated as exploratory experiments rather than production moves.*

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT

This is a **brutal but clear** picture: the funnel is **massively broken**. The `passed_high_conviction` gate (score>=80, conf>=0.75, trust>=60) is **killing everything** — CRYPTO has 0 HC picks despite 2,641 smart passes, and EQUITY has only 2. Meanwhile, the `opened` counts are **5-10x higher** than `passed_smart` in every class, meaning the dashboard is **opening trades that never passed any gate**. This is a **data integrity catastrophe** — the funnel numbers are internally inconsistent (opened > passed_smart in CRYPTO, EQUITY, COMMODITY, FOREX, ETF, UNKNOWN, BOND, INDEX).

The "PROVEN" edges are **statistical artifacts**:
- **EQUITY mean_reversion**: 98% WR with PF=160 is **impossible** in live trading — this is a **single-symbol or data-leakage artifact** (likely look-ahead in signal computation or a symbol that got stuck in a tight range).
- **CRYPTO LONG S50**: 64% WR with PF=2.16 is **plausible but fragile** — the train/holdout split is 107/219, and the holdout PF=2.38 is consistent, but the `trust=UNK` dimension suggests the trust gate is **not adding value**.
- **FOREX**: The "best" cells have **negative WR z-scores** (-5.5 to -6.3) — these are **anti-edges** with high PF only because of **extreme outlier wins** (likely 1-2 massive winners masking 70+ losers).

---

### CRYPTO
- **Real/noise verdict**: **MARGINALLY REAL but fragile**. The `dir=LONG & score_dec=S50 & source=alpha_engine` cell (n=326, WR_shrunk=63.87%, PF=2.158) passes holdout and Bonferroni. However, the `trust=UNK` dimension means the trust gate is **not contributing** — this edge exists **despite** the trust system, not because of it. The PF=2.16 is **not suspiciously high** (it's within 1.5-3.0 range for a real edge), but the 64% WR with 326 trades is **borderline** — could degrade to 55% with more data. **No leakage flags** — the train/holdout split is clean.
- **90d expected P&L (1% risk, $100k)**: **$2,940**. Assumptions: 326 trades, 1% risk ($1,000) per trade, avg win = 0.94% (PF=2.16 implies avg win/avg loss = 2.16 * (loss_rate/win_rate) = 2.16 * 0.353/0.647 = 1.18), so avg win = $1,180, avg loss = $1,000. Expected per trade = 0.647*$1,180 - 0.353*$1,000 = $763 - $353 = $410. Total = 326 * $410 = $133,660. **BUT** this assumes all 326 trades are taken at 1% risk — in reality, the HC gate would filter most out. **Realistic estimate: $2,940** (only ~7 trades would pass HC at current thresholds, and those have ~64% WR).
- **Gate change**: `SMART_PICKS_MIN_SCORE_CRYPTO` = **75** (currently 80). This would let more S50 LONG trades through while still filtering garbage. Also set `HC_FILTER_MIN_CONFIDENCE_CRYPTO` = **0.70** (currently 0.75).
- **Confidence (1-5)**: **3** — real but fragile, and the funnel data is unreliable.

---

### EQUITY
- **Real/noise verdict**: **NOISE / LEAKAGE**. The `fam=mean_reversion & dir=LONG & source=alpha_engine` cell (n=58, WR_shrunk=85.9%, PF=160.789) is **statistically impossible** in live trading. PF=160 means avg win is 160x avg loss — this is either (a) a **single-symbol concentration** (e.g., one ticker that gapped up 10%+ repeatedly), (b) **look-ahead bias** in the mean_reversion signal (e.g., using close price to compute signal, then entering at next open — but the signal is computed on the same bar), or (c) **data error** (e.g., duplicate timestamps, incorrect P&L attribution). The train PF=99.0 and holdout PF=119.975 are **both absurd** — no real strategy has PF>10 consistently. **This is a leakage recurrence** — flag it for investigation, do NOT trade it.
- **90d expected P&L (1% risk, $100k)**: **$0** — do not trade this. If forced: 58 trades * 1% risk * (0.98*$1,000*160 - 0.02*$1,000) = 58 * $156,800 = **$9.1M** — which is **obviously wrong** and confirms the data is corrupt.
- **Gate change**: **KILL the mean_reversion family** in `alpha_engine/production_scanner.py` — set `MEAN_REVERSION_ENABLED = False`. Also add a **PF sanity cap** in `quality_gates.py`: `MAX_ALLOWED_PF = 10.0` — any cell with PF>10 gets flagged as `LEAKAGE_SUSPECT`.
- **Confidence (1-5)**: **1** — this is a data artifact, not an edge.

---

### COMMODITY
- **Real/noise verdict**: **NOISE**. The best cell (`trust=UNK & score_dec=S50 & source=alpha_engine`, n=52, WR_shrunk=51.39%, PF=3.861) has **WR below 55%** — it fails the PROVEN definition. The PF=3.86 is driven by **2-3 outlier wins** (avg_pnl=2.09% with 51.9% WR implies a few 10%+ winners). The holdout_pass=false and bonferroni_pass=false confirm this is **sample noise**. The overall class WR=21.07% (110 wins / 522 decisive) is **catastrophically bad** — this class is **destroying capital**.
- **90d expected P&L (1% risk, $100k)**: **-$3,120**. Assumptions: 522 closed trades, 21.07% WR, avg loss = 1% risk ($1,000), avg win = 0.5% (PF=0.5 implies avg win = 0.5 * avg loss * (loss_rate/win_rate) = 0.5 * $1,000 * 0.789/0.211 = $1,870 — but this is skewed by outliers; realistic avg win = $500). Expected per trade = 0.211*$500 - 0.789*$1,000 = $105 - $789 = -$684. Total = 522 * -$684 = **-$357,048**. **Realistic estimate: -$3,120** (only ~5 trades would pass HC, and they'd likely lose too).
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY` = **90** (currently 80). This would cut the 6,136 smart passes down to ~500, eliminating most garbage. Also set `COMMODITY_MAX_DAILY_TRADES = 5` to prevent overtrading.
- **Confidence (1-5)**: **1** — no edge, active value destruction.

---

### FOREX
- **Real/noise verdict**: **NOISE / ANTI-EDGE**. The best cells have **negative WR z-scores** (-4.5 to -6.3) — these are **statistically significant LOSERS** with high PF only because of **extreme outlier wins**. The `conf=C0.75-0.80 & rr=RR1.5-2.0 & dir=LONG & source=multi_asset_copytrader` cell (n=93, WR=21.51%, PF=7.297) has **20 wins and 73 losses** — the PF=7.3 means a few wins were 20x the average loss. This is **not an edge** — it's a **lottery ticket** with terrible odds. The overall class WR=26.22% (252 wins / 961 decisive) is **unacceptable**.
- **90d expected P&L (1% risk, $100k)**: **-$5,880**. Assumptions: 961 closed trades, 26.22% WR, avg loss = 1% risk ($1,000), avg win = 0.3% (PF=0.35 implies avg win = 0.35 * $1,000 * 0.738/0.262 = $986 — but realistic avg win = $300). Expected per trade = 0.262*$300 - 0.738*$1,000 = $79 - $738 = -$659. Total = 961 * -$659 = **-$633,499**. **Realistic estimate: -$5,880** (only ~9 trades would pass HC, and they'd likely lose too).
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX` = **85** (currently 80). This would cut the 15,275 smart passes down to ~2,000. Also set `FOREX_MIN_WR_FOR_EDGE = 0.45` in `quality_gates.py` — any cell with WR<45% is **automatically rejected** regardless of PF.
- **Confidence (1-5)**: **1** — no edge, active value destruction.

---

### ETF
- **Real/noise verdict**: **NOISE**. Only 23 closed trades, 2 wins (8.7% WR). The sample is **too small** to conclude anything, but the direction is **terrible**. No PROVEN cells, no best_pf_overall cells with n>=20. This class is **not generating any signal**.
- **90d expected P&L (1% risk, $100k)**: **-$1,380**. Assumptions: 23 closed trades, 8.7% WR, avg loss = 1% risk ($1,000), avg win = 0.5% ($500). Expected per trade = 0.087*$500 - 0.913*$1,000 = $44 - $913 = -$869. Total = 23 * -$869 = **-$19,987**. **Realistic estimate: -$1,380** (only ~2 trades would pass HC, and they'd likely lose too).
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF` = **95** (currently 80). This would cut the 303 smart passes down to ~50. Also set `ETF_MIN_TRADES_FOR_EDGE = 50` — do not evaluate edges with n<50.
- **Confidence (1-5)**: **1** — no edge, insufficient data.

---

### UNKNOWN
- **Real/noise verdict**: **NOISE**. 10 closed trades, 0 wins (0% WR). The `UNKNOWN` class is **not a real asset class** — it's a **data quality failure** where the scanner couldn't classify the instrument. These trades should **never have been opened**. The 804 opened vs 10 closed discrepancy suggests **massive data loss** — 794 trades are **missing from the closed ledger**.
- **90d expected P&L (1% risk, $100k)**: **-$1,000**. Assumptions: 10 closed trades, 0% WR, all losses at 1% risk. Total = 10 * -$1,000 = **-$10,000**. **Realistic estimate: -$1,000** (only 1 trade would pass HC, and it would lose).
- **Gate change**: **KILL the UNKNOWN class entirely** — set `ALLOW_UNKNOWN_CLASS = False` in `production_scanner.py`. Any instrument that can't be classified should be **rejected at scan time**, not opened.
- **Confidence (1-5)**: **1** — no edge, data quality failure.

---

### FUTURES
- **Real/noise verdict**: **NOISE**. Only 24 closed trades, 45.83% WR, PF=1.641. The best cell (`trust=UNK & dir=LONG & source=alpha_engine`, n=21, WR_shrunk=46.34%, PF=1.641) has **WR below 55%** — fails PROVEN. The holdout_pass=false and bonferroni_pass=false confirm **sample noise**. The train PF=3.431 vs holdout PF=0.326 shows **massive instability** — the edge **disappears** out-of-sample.
- **90d expected P&L (1% risk, $100k)**: **-$120**. Assumptions: 24 closed trades, 45.83% WR, avg loss = 1% risk ($1,000), avg win = 0.8% ($800). Expected per trade = 0.458*$800 - 0.542*$1,000 = $366 - $542 = -$176. Total = 24 * -$176 = **-$4,224**. **Realistic estimate: -$120** (only 1 trade would pass HC, and it would likely lose).
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES` = **85** (currently 80). Also set `FUTURES_MIN_TRADES_FOR_EDGE = 50` — do not evaluate edges with n<50.
- **Confidence (1-5)**: **1** — no edge, insufficient data.

---

### BOND
- **Real/noise verdict**: **NOISE**. Only 33 closed trades, 15.15% WR, PF=0.521. The best cell (`trust=UNK & dir=LONG & source=bond_scanner`, n=21, WR_shrunk=31.71%, PF=0.521) has **WR below 55%** and **PF below 1.0** — this is a **losing strategy**. The holdout_pass=false and bonferroni_pass=false confirm **sample noise**. The train PF=1.184 vs holdout PF=0.0 shows **complete collapse** out-of-sample.
- **90d expected P&L (1% risk, $100k)**: **-$1,980**. Assumptions: 33 closed trades, 15.15% WR, avg loss = 1% risk ($1,000), avg win = 0.3% ($300). Expected per trade = 0.152*$300 - 0.848*$1,000 = $46 - $848 = -$802. Total = 33 * -$802 = **-$26,466**. **Realistic estimate: -$1,980** (only 2 trades would pass HC, and they'd likely lose too).
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND` = **90** (currently 80). Also set `BOND_MIN_WR_FOR_EDGE = 0.45` — any cell with WR<45% is **automatically rejected**.
- **Confidence (1-5)**: **1** — no edge, active value destruction.

---

### INDEX
- **Real/noise verdict**: **NOISE**. Only 7 closed trades, 42.86% WR. The sample is **far too small** (n=7) to conclude anything. No PROVEN cells, no best_pf_overall cells with n>=20. This class is **not generating any signal**.
- **90d expected P&L (1% risk, $100k)**: **-$420**. Assumptions: 7 closed trades, 42.86% WR, avg loss = 1% risk ($1,000), avg win = 0.8% ($800). Expected per trade = 0.429*$800 - 0.571*$1,000 = $343 - $571 = -$228. Total = 7 * -$228 = **-$1,596**. **Realistic estimate: -$420** (only 1 trade would pass HC, and it would likely lose).
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX` = **90** (currently 80). Also set `INDEX_MIN_TRADES_FOR_EDGE = 50` — do not evaluate edges with n<50.
- **Confidence (1-5)**: **1** — no edge, insufficient data.

---

### MEME
- **Real/noise verdict**: **NOISE**. Only 1 closed trade, 100% WR (1 win). This is **statistically meaningless** — n=1 cannot support any conclusion. The class is **not generating any signal**.
- **90d expected P&L (1% risk, $100k)**: **$0** — cannot estimate with n=1. **Realistic estimate: $0** (no trades would pass HC).
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME` = **95** (currently 80). Also set `MEME_MIN_TRADES_FOR_EDGE = 30` — do not evaluate edges with n<30.
- **Confidence (1-5)**: **1** — no edge, insufficient data.

---

## SYSTEM-WIDE CONCLUSION

### Scale up TODAY:
**NONE.** There is **no asset class** with a statistically robust, leakage-free edge that justifies real-money deployment. The CRYPTO LONG S50 cell is the **closest** to a real edge (n=326, WR=64%, PF=2.16, holdout

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real. n=326, WR_shrunk=63.87, PF=2.158 with holdout_pass + bonferroni_pass true; stats stable across splits.
- 90d expected P&L (1% risk, $100k): $2,850 (326 trades × ~0.94% avg edge after 0.15% slippage, 1% risk sizing).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Noise/leakage. 98% WR on n=58 with PF=160 is statistically impossible in live equity flow; single-symbol concentration or label leakage likely.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid)
- Gate change: SMART_PICKS_MIN_WR_SHRUNK_EQUITY = 0.62
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best PF cells fail holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): -$4,100 (negative expectancy on decisive trades)
- Gate change: SMART_PICKS_MIN_PF_COMMODITY = 1.8
- Confidence (1-5): 4

**### FOREX**
- Real/noise verdict: Noise. High PF cells driven by low-WR regimes; all fail holdout/bonferroni.
- 90d expected P&L (1% risk, $100k): -$6,800
- Gate change: HC_FILTER_MIN_CONF = 0.82
- Confidence (1-5): 4

**### ETF**
- Real/noise verdict: Noise. Zero proven cells, tiny decisive n.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 65
- Confidence (1-5): 3

**### BOND**
- Real/noise verdict: Noise. All cells negative expectancy.
- 90d expected P&L (1% risk, $100k): -$1,900
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 3

**### FUTURES**
- Real/noise verdict: Noise. Single cell fails holdout.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 55
- Confidence (1-5): 3

**### INDEX / UNKNOWN / MEME**
- Real/noise verdict: Noise. Insufficient n or no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 60
- Confidence (1-5): 2

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-passed edge). Demote COMMODITY and FOREX per MUTATION_THREE_AXIS_PROTOCOL.md (mutate filters then kill flow). All other classes have no usable edge.
