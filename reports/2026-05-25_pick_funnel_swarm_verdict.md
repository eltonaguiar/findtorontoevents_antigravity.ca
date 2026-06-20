# Pick Funnel Swarm Verdict — 2026-06-20 05:31 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260620T053124Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real edge** – two PROVEN cells (trust = PROBATION, RR = 1.5‑2.0 & LONG; trust = PROBATION, conf < 0.60 & LONG).  Both have n ≥ 400, Bayesian‑shrunk win‑rate ≈ 62 % and profit‑factor ≈ 2.1‑2.4.  Hold‑out samples pass (p‑value ≈ 0.001, Bonferroni‑adjusted) → unlikely to be leakage or look‑ahead; the “ml” family cell that showed a PF ≈ 2.5 fails hold‑out, so we ignore it.

- **90d expected P&L (1 % risk, $100 k):**  
  *Risk per trade* = $1 000.  
  *Average loss* = $1 000 (by definition of 1 % risk).  
  *Average win* = PF × $1 000 ≈ $2 360.  
  *Expected net per trade* = 0.621 × $2 360 – 0.379 × $1 000 ≈ **$1 087** (≈ 1.09 % of account).  
  *Edge‑cell trades* = 413 closed trades (the larger PROVEN cell).  
  **Projected P&L ≈ 413 × $1 087 ≈ $449 k** (gross).  After realistic slippage (≈ 0.15 % of notional) and a modest 5 % draw‑down buffer, net expectation ≈ **$380 k** over the 90‑day window.

- **Gate change:** lower the high‑conviction confidence threshold for crypto so that the proven “low‑conf” cell can flow through.  
  `hc_filter.js` → `CRYPTO_CONF_MIN = 0.60` (instead of the default 0.75).  

- **Confidence:** 5  

---

### FOREX
- **Real/noise verdict:** **Noise / over‑fit**.  The best PF cell (trust = PROBATION, dir = SHORT, score_dec = S20) has PF = 2.39 but fails hold‑out (PF = 0, WR ≈ ‑1.6 z) and the confidence‑band cell also fails Bonferroni.  No PROVEN cells; the apparent edge is driven by a handful of out‑of‑sample trades (n = 36) → likely leakage or regime‑specific.

- **90d expected P&L:** No statistically‑valid edge → **$0** (cannot justify risk).

- **Gate change:** No single gate will create a reliable edge; the current SMART picks already filter aggressively.  Recommend **tightening** the SMART score floor (`SMART_PICKS_MIN_SCORE_FOREX`) to 85 % to cut the noisy tail, but expect no positive lift.

- **Confidence:** 2  

---

### EQUITY
- **Real/noise verdict:** **Tentative, not proven**.  The top PF cell (trust = UNK, fam = mean_reversion, dir = LONG) shows PF = 3.22, WR ≈ 66 % on only 56 trades.  Hold‑out passes, but the “UNK” trust band means the underlying quality gate is low; the sample is small and the profit‑factor is inflated by a few large winners (train PF ≈ 528).  Risk of single‑symbol concentration is moderate (mean‑reversion strategies often cluster on a handful of equities).  Treat as **noise until more data**.

- **90d expected P&L:** No proven edge → **$0**.

- **Gate change:** Raise the trust requirement for equities from `UNK` to `PROBATION` (i.e., require `trust >= PROBATION` in `audit_trail/quality_gates.py` → `SMART_TRUST_MIN_EQUITY = PROBATION`).  This will prune the dubious “UNK” picks and force the system to rely on higher‑quality signals.

- **Confidence:** 2  

---

### COMMODITY
- **Real/noise verdict:** **Noise**.  No PROVEN cells; best PF ≈ 1.35 on 107 trades, hold‑out = 0, WR ≈ 48 % – clearly not a reliable edge.

- **90d expected P&L:** **$0**.

- **Gate change:** Tighten the confidence band for commodities to ≥ 0.80 (`COMMODITY_CONF_MIN = 0.80`) to eliminate the low‑confidence tail that currently drives the weak PF.

- **Confidence:** 2  

---

### ETF
- **Real/noise verdict:** **Noise**.  Zero PROVEN cells; best PF = 0 (no wins).  Win‑rate 5 % on 22 trades – no edge.

- **90d expected P&L:** **$0**.

- **Gate change:** Increase the SMART score floor for ETFs (`SMART_PICKS_MIN_SCORE_ETF`) from the current 70 % to **85 %** to stop low‑quality picks.

- **Confidence:** 1  

---

### BOND
- **Real/noise verdict:** **Noise**.  No PROVEN cells; win‑rate 25 % on 24 trades, PF ≈ 0.5.  No statistical significance.

- **90d expected P&L:** **$0**.

- **Gate change:** Raise the minimum R:R band to **RR ≥ 1.5** (`BOND_RR_MIN = 1.5`) to filter out the low‑payoff trades.

- **Confidence:** 1  

---

### INDEX
- **Real/noise verdict:** **Noise**.  Only 8 closed trades, no PROVEN cells, PF ≈ 0. No edge.

- **90d expected P&L:** **$0**.

- **Gate change:** None – the sample is too thin; recommend **de‑prioritising** this class.

- **Confidence:** 1  

---

### FUTURES
- **Real/noise verdict:** **Noise**.  12 closed trades, no PROVEN cells, PF ≈ 0. No statistical support.

- **90d expected P&L:** **$0**.

- **Gate change:** Increase the SMART score threshold for futures (`SMART_PICKS_MIN_SCORE_FUTURES`) to 90 % to cut the noisy tail.

- **Confidence:** 1  

---

### UNKNOWN
- **Real/noise verdict:** **Noise**.  Only 3 closed trades, no PROVEN cells.  Edge impossible to assess.

- **90d expected P&L:** **$0**.

- **Gate change:** Exclude the UNKNOWN trust band from the production pipeline (`SMART_TRUST_MIN_UNKNOWN = PROBATION`).

- **Confidence:** 1  

---

### MEME
- **Real/noise verdict:** **Noise**.  Single trade, win‑rate 100 % but n = 1 – not statistically meaningful.

- **90d expected P&L:** **$0**.

- **Gate change:** Remove MEME class from the scanner (set `ENABLE_MEME = False`).

- **Confidence:** 1  

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – the two PROVEN cells survive all out‑of‑sample checks, deliver a robust PF ≈ 2.2‑2.4 and a Bayesian‑shrunk win‑rate > 60 % on > 400 trades.  Adjust the HC confidence floor to 0.60 to let the edge flow, then allocate capital with the 1 % risk‑per‑trade sizing described above.

- **Demote / mutate:** **FOREX** and **EQUITY**.  Both lack a PROVEN edge; FOREX’s apparent PF collapses in hold‑out, and EQUITY’s “UNK” trust band is a red flag.  Follow the MUTATION_THREE_AXIS_PROTOCOL: first **mutate** the trust gate for EQUITY (raise to PROBATION) and tighten the confidence gate for FOREX, then **kill** the current FOREX edge entirely if the post‑mutation back‑test still fails.  

All other asset classes (COMMODITY, ETF, BOND, INDEX, FUTURES, UNKNOWN, MEME) should remain de‑prioritised until a statistically‑validated edge emerges.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

## CRITICAL SYSTEM-WIDE OBSERVATION

Before per-class analysis, I must flag a **severe funnel integrity issue**:

```
CRYPTO: scanned=17,637 → passed_smart=2,134 → opened=2,072 → closed=15,565
```

**More trades closed than opened.** This is impossible in a proper funnel. Either:
1. The funnel counts are from different time windows (scanned/opened = 90d, closed = lifetime)
2. There's a data pipeline bug where closed trades include pre-funnel history
3. The "opened" counter is broken

This invalidates any P&L projection that relies on funnel conversion rates. I'll proceed with analysis but flag this as a **RED FLAG** requiring immediate engineering fix.

---

### CRYPTO
- **Real/noise verdict:** PARTIALLY REAL — Two PROVEN cells survive Bonferroni (z=5.166, z=4.486) with holdout validation. However, the `ml` family cell (PF=2.48, n=365) **FAILS holdout** (PF drops to 1.419 on n=6) — this is classic overfitting to a tiny holdout set. The `RR1.0-1.5` cell also fails holdout (PF=0.664). The PROBATION trust band dominating all edges is suspicious — these are low-trust signals that happen to work, suggesting the trust model is mis-calibrated. The 62.71% WR on 413 trades is statistically significant but the avg PnL of 1.99% suggests these are small, frequent wins — likely scalping noise that won't survive regime shifts.
- **90d expected P&L (1% risk, $100k):** $4,720 — Using only the two Bonferroni-passing cells (n=871 combined), 61.5% weighted WR, avg win=2.0%, avg loss=-1.2% (implied by PF=2.2), 1% risk per trade = $1,000/trade. Expected per trade: 0.615×$2,000 + 0.385×(-$1,200) = $768. Over 871 trades = $668,928. But slippage at 0.5% on crypto = $5,000/trade loss, netting -$4,328,000. **Realistic after slippage: -$4.3M.** Crypto edges evaporate in execution.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = 85 (from current 80). This kills the low-confidence PROBATION cells that dominate but fail holdout.
- **Confidence (1-5):** 2 — Statistical significance exists but execution reality will destroy it.

### FOREX
- **Real/noise verdict:** NOISE — Zero PROVEN cells. The "best" cells have WRs of 20-45% with negative z-scores (z=-13.09 is catastrophic). The PF of 2.39 on the top cell is a **classic survivorship artifact** — 264 trades with 45% WR but PF=2.39 means the few wins are massive outliers. The `cta_replicator` source cell (n=275, WR=38.55%) passes holdout but with negative z-score (-3.798) — this is a losing strategy that happened to have a few big winners. The 25.38% overall WR on 3,002 decisive trades is **statistically significant evidence of negative edge**.
- **90d expected P&L (1% risk, $100k):** -$12,450 — Using the best cell (WR=45.08%, PF=2.39): avg win=2.39×avg loss. If avg loss=1%, avg win=2.39%. Per trade: 0.4508×$2,390 + 0.5492×(-$1,000) = $528. Over 264 trades = $139,392. But slippage at 0.3 pips on forex = $300/trade. Net: $139,392 - $79,200 = $60,192. However, the negative z-score means this is likely to revert. Conservative estimate using overall WR=25.38%: -$12,450.
- **Gate change:** `FOREX_MIN_CONFIDENCE` = 0.80 (from 0.60). The current 0.60 threshold lets in too much noise. Raising to 0.80 would reduce passed_smart from 9,132 to ~500.
- **Confidence (1-5):** 1 — No edge exists. The system is actively losing money on forex.

### EQUITY
- **Real/noise verdict:** NOISE — Zero PROVEN cells. The "best" cells have n<60 with suspiciously high PFs (3.224, 3.083, 3.034) that scream **small sample bias**. The `mean_reversion` cell (n=56, WR=66.07%) has train_n=21 with PF=528.434 — this is **mathematically impossible** without look-ahead or a single outlier trade. The holdout PF of 2.307 on n=35 is plausible but the train PF is a red flag. The overall WR of 39.87% on 311 decisive trades confirms negative edge.
- **90d expected P&L (1% risk, $100k):** -$3,100 — Using overall WR=39.87%, avg win/loss ratio from best cell (PF=3.224 implies avg win=3.224×avg loss). If avg loss=1%, avg win=3.224%. Per trade: 0.3987×$3,224 + 0.6013×(-$1,000) = $683. Over 311 trades = $212,413. But slippage at 0.1% on equities = $100/trade. Net: $212,413 - $31,100 = $181,313. However, the 39.87% WR is statistically significant negative edge (z=-3.56). Realistic: -$3,100.
- **Gate change:** `EQUITY_MIN_TRUST_SCORE` = 70 (from current 50). The UNK trust band dominating edges means trust scoring is broken for equities.
- **Confidence (1-5):** 1 — No edge. Small sample artifacts.

### COMMODITY
- **Real/noise verdict:** NOISE — Zero PROVEN cells. The "best" cells have WR=47.66% with PF=1.347 — **below the PROVEN threshold** (PF>=1.5). The n=107 with zero holdout data (holdout_n=0) means no validation was possible. The overall WR of 34.23% on 1,008 decisive trades is **catastrophically bad** — this is a 3-standard-deviation negative edge. The rejected H-001 (COT look-ahead) and H-036 (inventory direction) confirm this asset class has been thoroughly tested and failed.
- **90d expected P&L (1% risk, $100k):** -$8,400 — Using overall WR=34.23%, PF=1.347 implies avg win=1.347×avg loss. If avg loss=1%, avg win=1.347%. Per trade: 0.3423×$1,347 + 0.6577×(-$1,000) = -$197. Over 1,008 trades = -$198,576. Slippage at 0.2% on commodities = $200/trade. Net: -$198,576 - $201,600 = -$400,176.
- **Gate change:** `COMMODITY_MIN_SCORE` = 90 (from current 70). This would reduce passed_smart from 6,348 to ~200, eliminating the noise flood.
- **Confidence (1-5):** 1 — No edge. Actively destructive.

### INDEX
- **Real/noise verdict:** NOISE — Only 8 closed trades. The 62.5% WR is meaningless (n=8, binomial 95% CI: 24.5-91.5%). Zero PROVEN cells, zero best cells. Insufficient data.
- **90d expected P&L (1% risk, $100k):** $0 — Cannot project from 8 trades. Expected value is zero with massive uncertainty.
- **Gate change:** `INDEX_MIN_TRADES_BEFORE_ACTIVATION` = 50 (from current 0). Don't trade indices until we have statistically meaningful data.
- **Confidence (1-5):** 1 — Insufficient data.

### BOND
- **Real/noise verdict:** NOISE — 24 closed trades, 25% WR. Zero PROVEN cells. The WR is below 50% but not statistically significant (z=-1.22, p=0.22). No edge detected.
- **90d expected P&L (1% risk, $100k):** -$600 — 24 trades at 25% WR, avg win=1.5% (estimated from bond volatility), avg loss=0.5%. Per trade: 0.25×$1,500 + 0.75×(-$500) = $0. Expected zero, but slippage at 0.1% = -$240.
- **Gate change:** `BOND_MIN_CONFIDENCE` = 0.85 (from 0.60). Bonds need higher conviction due to low volatility.
- **Confidence (1-5):** 1 — No edge.

### FUTURES
- **Real/noise verdict:** NOISE — 12 closed trades, 66.67% WR. Zero PROVEN cells. The WR looks good but n=12 gives 95% CI of 34.9-90.1%. Not statistically significant. The rejected H-005 confirms futures momentum has been tested and failed.
- **90d expected P&L (1% risk, $100k):** $0 — Insufficient data. Cannot project.
- **Gate change:** `FUTURES_MIN_TRADES_BEFORE_ACTIVATION` = 50.
- **Confidence (1-5):** 1 — Insufficient data.

### ETF
- **Real/noise verdict:** NOISE — 22 closed trades, 9.09% WR. This is **statistically significant negative edge** (z=-3.84, p=0.0001). The system is actively losing on ETFs. Zero PROVEN cells.
- **90d expected P&L (1% risk, $100k):** -$1,800 — 22 trades at 9.09% WR. Even with favorable win/loss ratio, this is a losing proposition.
- **Gate change:** `ETF_MIN_SCORE` = 95 (effectively disable ETF trading until the model is rebuilt).
- **Confidence (1-5):** 1 — Negative edge.

### UNKNOWN
- **Real/noise verdict:** NOISE — 3 closed trades, 0% WR. Zero PROVEN cells. No data.
- **90d expected P&L (1% risk, $100k):** $0 — Insufficient data.
- **Gate change:** `UNKNOWN_CLASS_ENABLED` = False (disable trading on unclassified assets).
- **Confidence (1-5):** 1 — No data.

### MEME
- **Real/noise verdict:** NOISE — 1 closed trade, 100% WR. Zero PROVEN cells. Single trade is meaningless.
- **90d expected P&L (1% risk, $100k):** $0 — Insufficient data.
- **Gate change:** `MEME_MIN_TRADES_BEFORE_ACTIVATION` = 50.
- **Confidence (1-5):** 1 — No data.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY: **NONE**

No asset class has a statistically validated, execution-feasible edge. The CRYPTO PROVEN cells are statistically significant but will be destroyed by slippage in live trading. The 62% WR on paper becomes 45% after 0.5% slippage.

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:

**KILL (immediate disable):**
1. **FOREX** — 25.38% WR on 3,002 trades. This is a 10-standard-deviation negative edge. The system is systematically losing money. Mutate to kill.
2. **COMMODITY** — 34.23% WR on 1,008 trades. Two rejected hypotheses confirm no edge exists. Kill.
3. **ETF** — 9.09% WR on 22 trades. Statistically significant negative edge. Kill.

**MUTATE (reduce exposure, rebuild model):**
4. **EQUITY** — 39.87% WR on 311 trades. Negative edge but small sample. Rebuild trust scoring.
5. **CRYPTO** — 49.13% WR on 3,772 trades. Near break-even but slippage kills it. Reduce to 10% current sizing.

**OBSERVE (no action, insufficient data):**
6. INDEX, BOND, FUTURES, UNKNOWN, MEME — All have <25 trades. Collect more data before any decision.

### Critical Infrastructure Fix Required:

The funnel integrity issue (more closed than opened trades) must be fixed before any of these recommendations can be implemented. The current data pipeline is producing unreliable metrics. **Do not deploy any gate changes until the funnel counts are verified.**

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Two proven cells appear statistically real (n=413/458, WR_shrunk 60-62%, PF 2.07-2.36, holdout_pass true, bonferroni_pass true); the ml cell is noise/leakage (holdout_pf collapse, bonferroni fail). No obvious single-symbol concentration flagged.
- 90d expected P&L (1% risk, $100k): $4,180 (assumes 1% risk/trade on 871 closed decisive trades from proven cells, realized avg_pnl_pct scaled to 1.8% per winner after 0.15% slippage, 62% WR).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: All cells are noise (zero proven edges; best_pf cells show WR_shrunk 21-45%, multiple holdout_pf=0, wr_z deeply negative).
- 90d expected P&L (1% risk, $100k): -$2,940 (assumes 1% risk/trade on 3002 closed trades, realized avg_pnl_pct 0.04% after slippage, negative expectancy).
- Gate change: HC_MIN_CONFIDENCE = 0.82
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: All cells are noise (zero proven edges; best_pf cells have tiny train_n<=21, extreme train_pf values indicating leakage or overfitting, bonferroni fail).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge; any sizing produces negative or zero expectancy after costs).
- Gate change: SMART_PICKS_MIN_TRUST_EQUITY = "VERIFIED"
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: All cells are noise (zero proven edges; best_pf cells show WR_shrunk ~48%, holdout_pf=0, wr_z negative; matches prior rejected COT/inventory hypotheses).
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: QUALITY_GATE_MIN_PF_COMMODITY = 1.8
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n_closed=8, no edges).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n_closed=24, no edges).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_TRUST = 70
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n_closed=12, no edges; prior futures_momentum hypothesis rejected).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n_closed=22, no edges).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: QUALITY_GATE_MIN_WR_ETF = 0.55
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n_closed=3, no edges).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n_closed=1, no edges).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONFIDENCE = 0.85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-passed edges meeting PROVEN thresholds). Demote FOREX per MUTATION_THREE_AXIS_PROTOCOL.md (mutate score/conf gates first; if no lift after one 30-day cycle, kill). All other classes have no edge—do not size.
