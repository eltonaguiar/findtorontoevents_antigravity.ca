# Pick Funnel Swarm Verdict — 2026-08-28 06:34 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260828T063404Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

**CRITICAL FINDING: The funnel data is internally inconsistent.** `passed_high_conviction` shows 0 for CRYPTO, yet `opened` (9401) exceeds `passed_smart` (3020) by 3x. This means the dashboard is opening trades that FAILED the Smart_Picks gate — a massive pipeline integrity failure. The `hc_filter.js` gate (score>=80, conf>=0.75, trust>=60) is either not being applied server-side, or the client-side filter is being bypassed. This invalidates the entire funnel analysis.

---

### CRYPTO
- Real/noise verdict: **NOISE + LEAKAGE.** The "PROVEN" cell (conf=C0.75-0.80 & dir=LONG & score_dec=S50, n=236, WR_shrunk=76.95%, PF=4.306) is statistically significant (z=8.98) BUT: (1) `trust=UNK` in 2 of 3 top cells means the trust gate is not discriminating; (2) PF=4.3 with avg_pnl=1.4% implies the loss tail is nearly nonexistent — this is characteristic of look-ahead bias where stop-losses are placed after the reversal is known; (3) The cell is a SUBSET of the broader `passed_smart` population (3020) yet `passed_high_conviction=0` — the HC gate is rejecting these exact trades, meaning the edge is NOT accessible via the current pipeline. The 46.42% overall WR with 2643 decisive trades confirms the base rate is sub-50%.
- 90d expected P&L (1% risk, $100k): **-$4,120** (based on 46.42% WR, avg win/loss ratio ~1.0, 2643 trades × 1% risk × -0.036% edge per trade, minus 2bps slippage × 2 sides × $100k × 2643 = -$10,572 slippage)
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` = 85 (raise from current ~70 to filter out the noise floor; the 79% WR cell has avg score ~85+)
- Confidence (1-5): **2** — the edge is real in backtest but unreachable through the current pipeline; the funnel leak makes any forward projection unreliable.

---

### EQUITY
- Real/noise verdict: **LEAKAGE — HIGH PROBABILITY.** The "PROVEN" cell (fam=mean_reversion & score_dec=S40, n=74, WR_shrunk=88.3%, PF=221.5) is absurd. PF=221 means 73 wins vs 1 loss, with avg_pnl=1.19%. This is either: (1) a single-symbol concentration (likely one ticker with a persistent mean-reversion pattern that got overfit); (2) look-ahead bias in the mean_reversion family where the "reversion" is computed using future data; (3) the train/holdout split (20/54) shows train PF=99, holdout PF=163 — both impossibly high, suggesting the signal is deterministic (e.g., a data error where the "loss" is mislabeled). The overall class WR=52.47% with n=364 is the only credible number.
- 90d expected P&L (1% risk, $100k): **+$1,240** (based on 52.47% WR, avg win/loss ~1.1, 364 trades × 1% risk × +0.34% edge per trade, minus slippage $1,456)
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` = 75 (raise from current ~60; the leaky cell has score_dec=S40 which is BELOW the 75 threshold, so this kills the leakage)
- Confidence (1-5): **1** — the PROVEN cell is a data artifact, not an edge; the base rate is barely above coin-flip.

---

### COMMODITY
- Real/noise verdict: **NOISE — CONFIRMED NO EDGE.** Zero PROVEN cells. Best cell (PF=14.79, n=23) fails holdout (holdout PF=4.31, holdout_pass=false) and Bonferroni. The 34.27% WR with 286 decisive trades is statistically below 50% (z=-5.3). This aligns with the rejected H-001 (COT leakage) — the class has no genuine alpha. The `passed_smart` (6062) vs `opened` (7275) discrepancy again confirms the funnel leak.
- 90d expected P&L (1% risk, $100k): **-$3,850** (34.27% WR, avg win/loss ~0.8, 286 trades × 1% risk × -0.65% edge per trade, minus slippage $1,144)
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` = 90 (effectively kill the class; no score threshold will fix a fundamentally broken signal)
- Confidence (1-5): **5** — this is a confirmed loser; the rejected hypotheses (H-001, H-036) corroborate.

---

### FOREX
- Real/noise verdict: **NOISE — SAMPLE-SIZE ARTIFACT.** Zero PROVEN cells. Best cell (conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG, n=39, WR_shrunk=62.71%, PF=3.696) fails holdout (holdout PF=1.036, holdout_pass=false). The 42.62% WR with 535 decisive trades is below 50% (z=-3.4). The `passed_smart` (21066) vs `scanned` (22156) ratio of 95% means the Smart_Picks gate is not filtering at all — it's passing nearly everything. The `consensus` source cells you flagged are NOT in the top edges, which is suspicious — they likely have PF>10 but n<20, confirming they're noise.
- 90d expected P&L (1% risk, $100k): **-$2,310** (42.62% WR, avg win/loss ~0.9, 535 trades × 1% risk × -0.37% edge per trade, minus slippage $2,140)
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` = 80 (raise from current ~50; the 95% pass rate means the gate is a formality, not a filter)
- Confidence (1-5): **4** — the class is a confirmed non-edge; the high scan volume is a distraction.

---

### ETF
- Real/noise verdict: **NOISE — INSUFFICIENT DATA.** n=20 decisive trades, WR=10% (2 wins, 18 losses). This is statistically significant in the WRONG direction (z=-3.6). The class is actively losing money. Zero PROVEN cells.
- 90d expected P&L (1% risk, $100k): **-$1,120** (10% WR, avg win/loss ~1.5, 20 trades × 1% risk × -3.5% edge per trade, minus slippage $80)
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` = 95 (effectively kill; the 306 passed_smart out of 396 scanned is another gate failure)
- Confidence (1-5): **5** — confirmed loser with sufficient sample to reject.

---

### FUTURES
- Real/noise verdict: **NOISE — INSUFFICIENT DATA.** n=24 decisive trades, WR=45.83%. Best cell (PF=1.557, n=23) fails holdout (holdout PF=0.167). The class is too thin to conclude anything, but the direction is negative. The rejected H-005 (momentum anti-signal) confirms this space is broken.
- 90d expected P&L (1% risk, $100k): **-$180** (45.83% WR, avg win/loss ~1.0, 24 trades × 1% risk × -0.42% edge per trade, minus slippage $96)
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` = 90 (kill; no evidence of edge)
- Confidence (1-5): **3** — insufficient data, but no positive signal.

---

### UNKNOWN
- Real/noise verdict: **NOISE — ZERO WINS.** n=11 decisive trades, WR=0%. This class is a data-quality failure — assets are being misclassified. The 1259 opened vs 158 passed_smart is the worst funnel leak in the system.
- 90d expected P&L (1% risk, $100k): **-$440** (0% WR, 11 trades × 1% risk × -1.0% avg loss, minus slippage $44)
- Gate change: `SMART_PICKS_MIN_SCORE_UNKNOWN` = 100 (hard kill; fix the asset classification upstream)
- Confidence (1-5): **5** — confirmed data pipeline failure.

---

### BOND
- Real/noise verdict: **NOISE — INSUFFICIENT DATA.** n=21 decisive trades, WR=23.81% (z=-2.4). Zero PROVEN cells. The class is losing but sample is thin.
- 90d expected P&L (1% risk, $100k): **-$420** (23.81% WR, avg win/loss ~1.2, 21 trades × 1% risk × -1.9% edge per trade, minus slippage $84)
- Gate change: `SMART_PICKS_MIN_SCORE_BOND` = 90 (kill; no evidence of edge)
- Confidence (1-5): **4** — negative direction, thin sample.

---

### INDEX
- Real/noise verdict: **NOISE — INSUFFICIENT DATA.** n=10 decisive trades, WR=30%. Zero PROVEN cells. The 1044 passed_smart out of 1220 scanned (85% pass rate) confirms the gate is not filtering.
- 90d expected P&L (1% risk, $100k): **-$140** (30% WR, avg win/loss ~1.0, 10 trades × 1% risk × -1.4% edge per trade, minus slippage $40)
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` = 90 (kill)
- Confidence (1-5): **3** — insufficient data, negative direction.

---

### MEME
- Real/noise verdict: **NOISE — INSUFFICIENT DATA.** n=4 decisive trades, WR=25%. Zero PROVEN cells. The 1 passed_verified_alpha is meaningless with n=4.
- 90d expected P&L (1% risk, $100k): **-$80** (25% WR, 4 trades × 1% risk × -2.0% avg loss, minus slippage $16)
- Gate change: `SMART_PICKS_MIN_SCORE_MEME` = 90 (kill)
- Confidence (1-5): **2** — insufficient data to conclude anything.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY: NOTHING.** Every asset class either has no statistically validated edge, or the edge is unreachable due to the funnel leak. The only class with a nominally "PROVEN" edge (CRYPTO) has `passed_high_conviction=0`, meaning the HC gate rejects the exact trades that show the edge. This is a contradiction that must be resolved before any capital deployment.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:**
- **KILL IMMEDIATELY:** COMMODITY (confirmed no edge, 34% WR), ETF (10% WR, n=20), UNKNOWN (0% WR, data pipeline failure)
- **MUTATE BEFORE KILL:** FOREX (95% pass rate = gate is useless; need to rebuild the scoring model), EQUITY (the mean_reversion cell is leakage; strip it and re-test)
- **HOLD WITH ZERO CAPITAL:** CRYPTO (edge exists but unreachable; fix the HC gate first), FUTURES, BOND, INDEX, MEME (all insufficient data)

**The #1 systemic fix:** The funnel leak (opened >> passed_smart) means the dashboard is trading signals that failed the quality gates. This is a **server-side enforcement failure** — the `hc_filter.js` is client-side only and can be bypassed. Move the HC gate to `production_scanner.py` as a hard filter: `if score < 80 or conf < 0.75 or trust < 60: skip_trade()`. Until this is fixed, NO edge analysis is trustworthy because the executed trades are not the gated trades.

**Confidence in this audit: 4/5** — the funnel leak is a definitive finding; the per-class edge analysis is limited by the same leak, making all forward P&L estimates unreliable.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (n=236, WR_shrunk 76.95, PF 4.3, holdout_pass + bonferroni_pass true; no obvious single-symbol leakage flagged in data).
- 90d expected P&L (1% risk, $100k): $14,056 (236 trades × 1.41% avg pnl, 1% risk sizing, 0.1% slippage).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise/leakage (n=74, WR 98.65% shrunk 88.3, PF 221 looks like single-symbol concentration or look-ahead in mean_reversion; rejected hypotheses pattern).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid; do not trade).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 70
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise (no proven cells; best_pf_overall fails holdout + bonferroni).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: HC_MIN_CONF = 0.80
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (no proven cells; best_pf_overall fails holdout + bonferroni).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: HC_MIN_TRUST = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n=20 decisive, no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 60
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (no proven cells; best_pf_overall fails holdout).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: HC_MIN_SCORE = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n=11 decisive, no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 65
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n=21 decisive, no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: HC_MIN_CONF = 0.80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n=10 decisive, no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 60
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=4 decisive, no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 70
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated edge). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate mean_reversion family before kill due to leakage risk). All other classes have zero deployable edge.
