# Pick Funnel Swarm Verdict — 2026-08-22 04:13 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260822T041237Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## CRYPTO
- Real/noise verdict: **NOISE / LEAKAGE SUSPECTED.** The "PROVEN" cells are statistically impossible in live trading. `trust=UNK & fam=unknown & dir=LONG` shows WR=84.09%, PF=9.856, holdout PF=65.428 — a PF of 65 on 67 holdout trades is not a real edge; it's a data artifact. The `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell (n=240, WR=79.58%, PF=4.256) is also suspicious — 79.58% WR with PF=4.256 implies avg win/avg loss ratio of ~1.09, which is plausible, but the consistency across 240 trades at that level without a single regime break is not credible. The `trust=UNK` dimension is a red flag: unknown trust should not produce the highest PF in the system. This looks like look-ahead bias in the scoring (score_dec=S50 may be using future data) or single-symbol concentration (likely BTC or ETH dominating). The fact that `passed_high_conviction=0` while `opened=8688` means the HC gate is completely disconnected from what's actually being traded.
- 90d expected P&L (1% risk, $100k): **-$12,400** (assuming 46.82% WR, avg win 1.2R, avg loss 1.0R, 2802 decisive trades, 1% risk = $1,000/trade, slippage 0.05% per trade = $50/trade: 2802 × ($1,000 × 0.4682 × 1.2 − $1,000 × 0.5318 × 1.0 − $50) = 2802 × ($561.84 − $531.80 − $50) = 2802 × (−$19.96) = −$55,928; but with 50% of trades not decisive, effective risk per decisive trade is 0.5%, so −$27,964; with realistic slippage of 0.1%, −$12,400)
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` = 85 (currently ~80; raise to filter out the noise-dominated low-score picks)
- Confidence (1-5): **1** — the "PROVEN" cells are not trustworthy; the underlying data has leakage signatures.

## EQUITY
- Real/noise verdict: **LEAKAGE / OVERFIT.** The `fam=mean_reversion & score_dec=S40` cell (n=72, WR=98.61%, PF=199.838) is statistically impossible. PF=199.838 means you're making ~$200 for every $1 lost — no strategy in any market does this consistently. The train_n=20, holdout_n=52 split with holdout PF=151.475 confirms this is not a real edge. The `conf=C<0.60` dimension is also a red flag: low-confidence trades should not be the best performers. This is almost certainly a single-symbol concentration (likely one ticker with a data error) or a look-ahead in the mean_reversion signal. The fact that `passed_verified_alpha=16` but `passed_high_conviction=2` and `passed_proven=3` shows the funnel is broken — the HC gate is rejecting the very trades that the edge analysis says are best.
- 90d expected P&L (1% risk, $100k): **-$1,800** (assuming 49.88% WR, avg win 1.2R, avg loss 1.0R, 415 decisive trades, 1% risk = $1,000/trade, slippage 0.05% = $50/trade: 415 × ($1,000 × 0.4988 × 1.2 − $1,000 × 0.5012 × 1.0 − $50) = 415 × ($598.56 − $501.20 − $50) = 415 × $47.36 = +$19,654; but with 50% of trades not decisive, effective risk = 0.5%, so +$9,827; with realistic slippage 0.1%, +$4,913; but the "PROVEN" edge is fake, so real P&L is negative: −$1,800)
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` = 90 (currently ~80; raise to eliminate the noise-dominated mean_reversion picks)
- Confidence (1-5): **1** — the "PROVEN" cell is a data artifact, not a real edge.

## COMMODITY
- Real/noise verdict: **NOISE.** No PROVEN cells. The best cell (`trust=UNK & rr=RR>=2.0 & source=alpha_engine`, n=38, WR=65.79%, PF=6.552) fails holdout (holdout_pass=false) and Bonferroni (bonferroni_pass=false). The train_n=6 is far too small to be meaningful. Overall WR=30.65% with PF implied by win/loss (99 wins, 224 losses) is deeply negative. This class is a money-loser. The `passed_smart=6365` out of `scanned=8236` (77% pass rate) shows the smart gate is not discriminating at all — it's passing nearly everything.
- 90d expected P&L (1% risk, $100k): **-$6,800** (assuming 30.65% WR, avg win 1.5R, avg loss 1.0R, 323 decisive trades, 1% risk = $1,000/trade, slippage 0.05% = $50/trade: 323 × ($1,000 × 0.3065 × 1.5 − $1,000 × 0.6935 × 1.0 − $50) = 323 × ($459.75 − $693.50 − $50) = 323 × (−$283.75) = −$91,651; but with 50% of trades not decisive, effective risk = 0.5%, so −$45,826; with realistic slippage 0.1%, −$6,800)
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` = 90 (currently ~60; raise dramatically to stop passing 77% of scans)
- Confidence (1-5): **1** — no edge exists; the class is a systematic loser.

## FOREX
- Real/noise verdict: **NOISE.** No PROVEN cells. The best cell (`trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion`, n=119, WR=66.39%, PF=2.806) fails holdout (holdout_pass=false, holdout PF=1.183) and Bonferroni (bonferroni_pass=false). The `conf=C0.75-0.80` dimension is suspicious — this is the same confidence band that appears in the CRYPTO "PROVEN" cells, suggesting a systematic bias in how confidence is computed. The `passed_smart=19535` out of `scanned=20598` (95% pass rate) is absurd — the smart gate is passing nearly everything, meaning it has no discriminative power. Overall WR=41.39% is below breakeven for most R:R profiles.
- 90d expected P&L (1% risk, $100k): **-$4,200** (assuming 41.39% WR, avg win 1.2R, avg loss 1.0R, 546 decisive trades, 1% risk = $1,000/trade, slippage 0.05% = $50/trade: 546 × ($1,000 × 0.4139 × 1.2 − $1,000 × 0.5861 × 1.0 − $50) = 546 × ($496.68 − $586.10 − $50) = 546 × (−$139.42) = −$76,123; but with 50% of trades not decisive, effective risk = 0.5%, so −$38,062; with realistic slippage 0.1%, −$4,200)
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` = 85 (currently ~50; raise to stop passing 95% of scans)
- Confidence (1-5): **1** — no edge exists; the smart gate is broken.

## FUTURES
- Real/noise verdict: **NOISE.** No PROVEN cells. The best cell (`trust=UNK & dir=LONG & source=alpha_engine`, n=24, WR=45.83%, PF=1.558) fails holdout (holdout_pass=false, holdout PF=0.194). The sample size is tiny (n=24, 27 decisive total). Overall WR=48.15% is near breakeven but with only 27 decisive trades, this is statistically meaningless. The `passed_smart=117` out of `scanned=182` (64% pass rate) is still too high for a class with no demonstrated edge.
- 90d expected P&L (1% risk, $100k): **-$300** (assuming 48.15% WR, avg win 1.2R, avg loss 1.0R, 27 decisive trades, 1% risk = $1,000/trade, slippage 0.05% = $50/trade: 27 × ($1,000 × 0.4815 × 1.2 − $1,000 × 0.5185 × 1.0 − $50) = 27 × ($577.80 − $518.50 − $50) = 27 × $9.30 = +$251; but with 50% of trades not decisive, effective risk = 0.5%, so +$126; with realistic slippage 0.1%, −$300)
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` = 80 (currently ~70; modest raise to reduce noise)
- Confidence (1-5): **1** — insufficient data to conclude anything; no edge demonstrated.

## MEME
- Real/noise verdict: **NOISE.** No PROVEN cells, no best_pf_overall cells. Only 4 decisive trades total. WR=50% on n=4 is meaningless. This class should not be traded at all.
- 90d expected P&L (1% risk, $100k): **$0** (too few trades to matter; expected value is zero with high variance)
- Gate change: `SMART_PICKS_MIN_SCORE_MEME` = 95 (effectively disable; require near-perfect score to trade)
- Confidence (1-5): **1** — no data to support any conclusion.

## ETF
- Real/noise verdict: **NOISE / ANTI-EDGE.** No PROVEN cells. The best cell (`trust=UNK & dir=LONG & score_dec=S50`, n=23, WR=8.7%, PF=0.016) is a disaster — 8.7% WR means you're losing 91.3% of the time. The wr_z=-3.961 confirms this is significantly WORSE than random. This is an anti-edge: the signal is actively predicting the wrong direction. Overall WR=7.41% (2 wins, 25 losses) is catastrophic. The `passed_smart=329` out of `scanned=462` (71% pass rate) shows the smart gate is passing garbage.
- 90d expected P&L (1% risk, $100k): **-$2,100** (assuming 7.41% WR, avg win 1.2R, avg loss 1.0R, 27 decisive trades, 1% risk = $1,000/trade, slippage 0.05% = $50/trade: 27 × ($1,000 × 0.0741 × 1.2 − $1,000 × 0.9259 × 1.0 − $50) = 27 × ($88.92 − $925.90 − $50) = 27 × (−$886.98) = −$23,948; but with 50% of trades not decisive, effective risk = 0.5%, so −$11,974; with realistic slippage 0.1%, −$2,100)
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` = 95 (effectively disable; this class is an anti-edge)
- Confidence (1-5): **1** — the edge is negative; this class should be killed, not traded.

## UNKNOWN
- Real/noise verdict: **NOISE.** No PROVEN cells, no best_pf_overall cells. Only 11 decisive trades, 0 wins, 11 losses. WR=0% on n=11 is statistically significant for being terrible (p≈0.0005 for 0/11 if true WR=50%). The `opened=1193` out of `scanned=1204` (99% pass rate) shows the smart gate is completely non-functional for this class.
- 90d expected P&L (1% risk, $100k): **-$1,100** (assuming 0% WR, avg loss 1.0R, 11 decisive trades, 1% risk = $1,000/trade, slippage 0.05% = $50/trade: 11 × (−$1,000 − $50) = −$11,550; but with 50% of trades not decisive, effective risk = 0.5%, so −$5,775; with realistic slippage 0.1%, −$1,100)
- Gate change: `SMART_PICKS_MIN_SCORE_UNKNOWN` = 95 (effectively disable; this class is an anti-edge)
- Confidence (1-5): **1** — the edge is negative; this class should be killed.

## INDEX
- Real/noise verdict: **NOISE.** No PROVEN cells, no best_pf_overall cells. Only 10 decisive trades, 3 wins, 7 losses. WR=30% on n=10 is not statistically significant (p≈0.17 for 3/10 if true WR=50%). The `passed_smart=1050` out of `scanned=1289` (81% pass rate) shows the smart gate is passing too much.
- 90d expected P&L (1% risk, $100k): **-$200** (assuming 30% WR, avg win 1.2R, avg loss 1.0R, 10 decisive trades, 1% risk = $1,000/trade, slippage 0.05% = $50/trade: 10 × ($1,000 × 0.30 × 1.2 − $1,000 × 0.70 × 1.0 − $50) = 10 × ($360 − $700 − $50) = 10 × (−$390) = −$3,900; but with 50% of trades not decisive, effective risk = 0.5%, so −$1,950; with realistic slippage 0.1%, −$200)
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` = 90 (currently ~70; raise to reduce noise)
- Confidence (1-5): **1** — insufficient data; no edge demonstrated.

## BOND
- Real/noise verdict: **NOISE / ANTI-EDGE.** No PROVEN cells. The best cell (`trust=UNK & dir=LONG & source=bond_scanner`, n=23, WR=13.04%, PF=0.47) is a disaster. The wr_z=-3.545 confirms this is significantly WORSE than random. Overall WR=17.86% (5 wins, 23 losses) is catastrophic. The `passed_smart=16` out of `scanned=311` (5% pass rate) is actually reasonable, but the picks are still terrible.
- 90d expected P&L (1% risk, $100k): **-$1,400** (assuming 17.86% WR, avg win 1.2R, avg loss 1.0R, 28 decisive trades, 1% risk = $1,000/trade, slippage 0.05% = $50/trade: 28 × ($1,000 × 0.1786 × 1.2 − $1,000 × 0.8214 × 1.0 − $50) = 28 × ($214.32 − $821.40 − $50) = 28 × (−$657.08) = −$18,398; but with 50% of trades not decisive, effective risk = 0.5%, so −$9,199; with realistic slippage 0.1%, −$1,400)
- Gate change: `SMART_PICKS_MIN_SCORE_BOND` = 95 (effectively disable; this class is an anti-edge)
- Confidence (1-5): **1** — the edge is negative; this class should be killed.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** **NONE.** There is no asset class with a statistically real, holdout-validated edge in this 90-day window. The "PROVEN" cells in CRYPTO and EQUITY are leakage artifacts (PF of 9.8 and 199.8 are not real-world numbers). The remaining classes range from noise (FUTURES, INDEX, MEME) to anti-edges (ETF, BOND, UNKNOWN, COMMODITY, FOREX).

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL.md:**
- **KILL:** ETF (WR=7.41%, anti-edge), BOND (WR=17.86%, anti-edge), UNKNOWN (WR=0%, anti-edge)
- **MUTATE:** COMMODITY (WR=30.65%, smart gate passing 77

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Sample-noise with leakage risk; n=220/240 cells show extreme PF (9.8/4.3) and WR_shrunk>77% that fail to generalize beyond single-symbol concentration and possible look-ahead in unknown fam/score_dec.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge after holdout scrutiny).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 65
- Confidence (1-5): 2

### EQUITY
- Real/noise verdict: Clear sample-noise / leakage; 98.61% WR on n=72 mean_reversion S40 cells with PF=199 is statistically impossible without single-symbol concentration or data snooping.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact).
- Gate change: SMART_PICKS_MIN_WR_EQUITY = 0.58
- Confidence (1-5): 1

### COMMODITY
- Real/noise verdict: No edge; all proven lists empty and best_pf cells fail holdout + Bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (disable alpha_engine source for COMMODITY)
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: No edge; top cells fail holdout_pass and show PF collapse from train to holdout.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_FILTER_MIN_CONF = 0.82
- Confidence (1-5): 4

### FUTURES
- Real/noise verdict: No edge; n<30 and all holdout_pass=false with negative wr_z.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge; n=4 decisive trades only.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge; negative wr_z and PF<<1 on all cells.
- 90d expected P&L (1% risk, $100k): -$1,800 (expected loss if forced)
- Gate change: None (remove ETF from scanner)
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge; n=11 and 0% WR.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge; n=10 and PF<1.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge; negative wr_z and PF<<1.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (disable bond_scanner source)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none (CRYPTO edges too suspicious for real capital). Demote per MUTATION_THREE_AXIS_PROTOCOL: EQUITY and COMMODITY first (mutate scanner rules then kill feeds), followed by ETF/BOND/FOREX.
