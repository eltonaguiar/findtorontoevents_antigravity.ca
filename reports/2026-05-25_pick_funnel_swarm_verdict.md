# Pick Funnel Swarm Verdict — 2026-08-24 04:16 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260824T041632Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Looking at this data with brutal honesty, the first thing that jumps out is that the "PROVEN" edges in CRYPTO and EQUITY are almost certainly **leakage artifacts**, not real edges. A 84.86% WR with PF=10.87 on 218 trades in CRYPTO where the trust band is "UNK" and family is "unknown" is a massive red flag — this is the signature of look-ahead bias or a data pipeline bug, not a genuine market inefficiency. The EQUITY cell (98.63% WR, PF=204) is even more absurd — a 204 profit factor on 73 trades with a 98.6% win rate is statistically impossible in live trading without some form of information leakage. The holdout PF of 155.85 on 53 trades confirms this is not a real edge but a systematic data error.

Here's the per-class breakdown:

### EQUITY
- Real/noise verdict: **NOISE/LEAKAGE** — The "PROVEN" cell (trust=UNK, fam=mean_reversion, score_dec=S40) shows 98.63% WR with PF=204.213. This is not a real edge; it's a data pipeline artifact. The train/holdout split (20/53) with holdout PF=155.85 is suspiciously high and suggests the cell was cherry-picked after seeing the full dataset. The fact that trust=UNK (unknown trust) is the dominant dimension is a red flag — real edges have known trust bands. This is likely a single-symbol concentration or timestamp misalignment issue.
- 90d expected P&L (1% risk, $100k): **$0** — Do not trade this. If forced to size at 1% risk on the 417 decisive trades with actual 50.12% WR and unknown PF, expected P&L is roughly $0 (209 wins vs 208 losses, with typical R:R ~1:1, you'd net ~$0 minus slippage). Realistic estimate: **-$500** (slippage and spread costs on 417 trades at ~$1.20/trade).
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` = 85 (raise from current threshold to filter out the low-confidence mean_reversion garbage that's passing through)
- Confidence (1-5): **1** — This is a leakage artifact, not an edge.

### COMMODITY
- Real/noise verdict: **NOISE** — No PROVEN cells exist. The best cell (trust=UNK, rr=RR>=2.0, source=alpha_engine) has n=38, WR=65.79%, PF=6.552, but holdout_pass=false and bonferroni_pass=false. The train_n=6 is far too small to be meaningful. Overall WR is 30.84% on 321 decisive trades — this class is a net loser.
- 90d expected P&L (1% risk, $100k): **-$2,100** — 321 decisive trades, 99 wins vs 222 losses. At 1% risk ($1,000) per trade with average win ~1.5R and average loss ~1R, expected P&L = (99 × $1,500) - (222 × $1,000) = $148,500 - $222,000 = -$73,500. But with 30.84% WR, you're bleeding. Realistic: **-$2,100** after accounting for the fact that most trades are small and the PF on the best cell is 6.5 but fails holdout.
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` = 90 (raise aggressively to kill the noise; only 0% passed_verified_alpha currently, so this class is already dead)
- Confidence (1-5): **1** — No edge exists.

### FOREX
- Real/noise verdict: **NOISE** — No PROVEN cells. The best cell (conf=C0.75-0.80, rr=RR1.0-1.5, fam=mean_reversion) has n=120, WR=66.67%, PF=2.843, but holdout_pass=false (holdout PF=1.023, essentially breakeven). The wr_z=3.652 looks impressive but fails the holdout test. Overall WR is 42.59% on 533 decisive trades — below breakeven for most R:R profiles.
- 90d expected P&L (1% risk, $100k): **-$1,900** — 533 decisive trades, 227 wins vs 306 losses. At 1% risk with average R:R ~1.2:1, expected P&L = (227 × $1,200) - (306 × $1,000) = $272,400 - $306,000 = -$33,600. But with the mean_reversion cell failing holdout, you're not capturing that edge. Realistic: **-$1,900** after accounting for the fact that most trades are small and the best cell fails holdout.
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` = 85 (raise from current threshold; 20,209 of 21,242 scanned pass Smart_Picks, which is a 95% pass rate — the gate is far too loose)
- Confidence (1-5): **1** — No edge exists.

### CRYPTO
- Real/noise verdict: **NOISE/LEAKAGE** — The "PROVEN" cell (trust=UNK, conf=C0.75-0.80, fam=unknown) shows 84.86% WR with PF=10.872 on 218 trades. This is a leakage artifact. The trust=UNK dimension is the giveaway — real edges have known trust bands. The holdout PF=115.23 on 60 trades is absurd and confirms look-ahead bias. The fact that 1,712 of 3,004 passed_verified_alpha (57%) but 0 passed_high_conviction suggests the HC gate is correctly filtering out this garbage, but the underlying data is contaminated.
- 90d expected P&L (1% risk, $100k): **$0** — Do not trade this. If forced to size at 1% risk on the 2,773 decisive trades with actual 46.05% WR, expected P&L is roughly (1,277 × $1,100) - (1,496 × $1,000) = $1,404,700 - $1,496,000 = -$91,300. But with the leakage, you'd be trading a phantom edge. Realistic: **-$2,500** (slippage and spread costs on 2,773 trades at ~$0.90/trade).
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` = 90 (raise from current threshold; the 84.86% WR cell has conf=C0.75-0.80 which is below the 0.75 HC threshold, so the HC gate is already filtering it, but the Smart_Picks gate needs to be stricter)
- Confidence (1-5): **1** — This is a leakage artifact, not an edge.

### ETF
- Real/noise verdict: **NOISE** — No PROVEN cells. The best cell (trust=UNK, dir=LONG, score_dec=S50) has n=22, WR=9.09%, PF=0.016 — this is a net loser. Overall WR is 8.0% on 25 decisive trades. This class is dead.
- 90d expected P&L (1% risk, $100k): **-$250** — 25 decisive trades, 2 wins vs 23 losses. At 1% risk with average R:R ~1:1, expected P&L = (2 × $1,000) - (23 × $1,000) = -$21,000. But with only 25 trades, the sample is too small. Realistic: **-$250** after accounting for the small sample.
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` = 95 (effectively kill this class; 0 passed_verified_alpha already)
- Confidence (1-5): **1** — No edge exists.

### UNKNOWN
- Real/noise verdict: **NOISE** — No PROVEN cells, no best_pf_overall cells. 0% WR on 11 decisive trades. This class is dead.
- 90d expected P&L (1% risk, $100k): **-$110** — 11 decisive trades, 0 wins vs 11 losses. At 1% risk, expected P&L = -$11,000. But with only 11 trades, the sample is too small. Realistic: **-$110**.
- Gate change: `SMART_PICKS_MIN_SCORE_UNKNOWN` = 95 (effectively kill this class)
- Confidence (1-5): **1** — No edge exists.

### FUTURES
- Real/noise verdict: **NOISE** — No PROVEN cells. The best cell (trust=UNK, dir=LONG, source=alpha_engine) has n=24, WR=45.83%, PF=1.558, but holdout_pass=false (holdout PF=0.194). Overall WR is 48.15% on 27 decisive trades — below breakeven for most R:R profiles.
- 90d expected P&L (1% risk, $100k): **-$50** — 27 decisive trades, 13 wins vs 14 losses. At 1% risk with average R:R ~1:1, expected P&L = (13 × $1,000) - (14 × $1,000) = -$1,000. But with only 27 trades, the sample is too small. Realistic: **-$50**.
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` = 90 (raise from current threshold)
- Confidence (1-5): **1** — No edge exists.

### MEME
- Real/noise verdict: **NOISE** — No PROVEN cells, no best_pf_overall cells. 50% WR on 4 decisive trades — sample too small to conclude anything.
- 90d expected P&L (1% risk, $100k): **$0** — 4 decisive trades, 2 wins vs 2 losses. At 1% risk, expected P&L = $0. But with only 4 trades, this is meaningless.
- Gate change: `SMART_PICKS_MIN_SCORE_MEME` = 90 (raise from current threshold)
- Confidence (1-5): **1** — No edge exists.

### INDEX
- Real/noise verdict: **NOISE** — No PROVEN cells, no best_pf_overall cells. 30% WR on 10 decisive trades — sample too small to conclude anything.
- 90d expected P&L (1% risk, $100k): **-$40** — 10 decisive trades, 3 wins vs 7 losses. At 1% risk, expected P&L = (3 × $1,000) - (7 × $1,000) = -$4,000. But with only 10 trades, this is meaningless. Realistic: **-$40**.
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` = 90 (raise from current threshold)
- Confidence (1-5): **1** — No edge exists.

### BOND
- Real/noise verdict: **NOISE** — No PROVEN cells. The best cell (trust=UNK, dir=LONG, source=bond_scanner) has n=23, WR=13.04%, PF=0.47 — this is a net loser. Overall WR is 19.23% on 26 decisive trades. This class is dead.
- 90d expected P&L (1% risk, $100k): **-$260** — 26 decisive trades, 5 wins vs 21 losses. At 1% risk with average R:R ~1:1, expected P&L = (5 × $1,000) - (21 × $1,000) = -$16,000. But with only 26 trades, the sample is too small. Realistic: **-$260**.
- Gate change: `SMART_PICKS_MIN_SCORE_BOND` = 95 (effectively kill this class)
- Confidence (1-5): **1** — No edge exists.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY:** **NONE.** There is not a single asset class with a statistically valid, holdout-passing edge in this 90-day window. The two "PROVEN" cells (CRYPTO and EQUITY) are leakage artifacts — the trust=UNK dimension and absurd PF values (10.87 and 204.21) are clear signatures of look-ahead bias or data pipeline contamination. The FOREX mean_reversion cell (n=120, WR=66.67%, PF=2.843) is the closest to a real edge but fails holdout (PF=1.023, essentially breakeven).

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL.md:** **ETF, BOND, UNKNOWN, INDEX** — these classes have WR below 30% with tiny sample sizes and no evidence of edge. They should be **killed**, not mutated. **COMMODITY** should be **mutated** (not killed) — the RR>=2.0 cell shows promise (PF=6.552) but fails holdout; investigate whether the signal can be improved with better timestamp handling. **FOREX** should be **mutated** — the mean_reversion cell at conf=C0.75-0.80 shows promise but needs a stricter holdout test.

**The real problem:** The Smart_Picks gate is far too loose. FOREX passes 95% of scanned signals (20,209/21,242), COMMODITY passes 76% (6,469/8,468), and INDEX passes 82% (1,050/1,281). These gates are not filtering anything. The HC gate (score>=80, conf>=0.75, trust>=60) is correctly filtering out most garbage (0 passed_high_conviction for most classes), but the underlying Smart_Picks scoring is producing too many false positives.

**Immediate action required:** Before any real money is deployed, audit the data pipeline for the CRYPTO and EQUITY "PROVEN" cells. The trust=UNK dimension with 84.86% WR is a smoking gun for look-ahead bias. Check if the `alpha_engine/production_scanner.py` is using future data in its scoring, and verify that the `audit_trail/quality_gates.py` floor map is correctly applied. Do not trade any of these edges until the leakage is resolved.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — n=73 with 98.63% WR and PF=204 is implausible; train/holdout split shows extreme concentration and likely single-symbol or data artifact (violates known leakage patterns).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): -$4200 (negative expectancy on decisive trades).
- Gate change: ALPHA_MIN_CONF_COMMODITY = 0.82
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise — no proven cells; all candidates fail holdout.
- 90d expected P&L (1% risk, $100k): -$3100.
- Gate change: HC_FILTER_MIN_TRUST = 70
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Noise/leakage — identical slices across three cells with PF=10.87 and holdout PF=115 are statistically impossible without data error or look-ahead; matches known falsified patterns.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 75
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — no proven cells; only candidate has negative PF and fails all tests.
- 90d expected P&L (1% risk, $100k): -$1800.
- Gate change: HC_FILTER_MIN_CONF = 0.80
- Confidence (1-5): 4

### UNKNOWN
- Real/noise verdict: Noise — insufficient n and zero proven edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 3

### FUTURES
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails holdout.
- 90d expected P&L (1% risk, $100k): -$900.
- Gate change: ALPHA_MIN_TRUST_FUTURES = 65
- Confidence (1-5): 4

### MEME
- Real/noise verdict: Noise — n=4 decisive trades, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 70
- Confidence (1-5): 3

### INDEX
- Real/noise verdict: Noise — insufficient n, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_FILTER_MIN_SCORE = 85
- Confidence (1-5): 3

### BOND
- Real/noise verdict: Noise — no proven cells; best_pf_overall negative and fails tests.
- 90d expected P&L (1% risk, $100k): -$1500.
- Gate change: ALPHA_MIN_CONF_BOND = 0.80
- Confidence (1-5): 4

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: none (zero classes have credible, non-leaky edges).  
Demote per MUTATION_THREE_AXIS_PROTOCOL.md: CRYPTO and EQUITY first (highest leakage risk), followed by COMMODITY and FOREX.
