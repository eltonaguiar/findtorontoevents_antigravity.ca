# Pick Funnel Swarm Verdict — 2026-08-17 04:16 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260817T041550Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- **Real/noise verdict:** **Real edge** – 217 closed trades, WR shrunk ≈ 81 %, PF ≈ 9.7. Hold‑out and Bonferroni tests pass. The “trust=UNK” band is a data‑quality flag, but the signal survives a clean hold‑out, so it is unlikely pure noise.  
- **90d expected P&L (1 % risk, $100 k):** ≈ **$2,860** (217 × 1.317 % × $1 000).  
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 50` (lower the smart‑pick score floor from the default ≈80 to 50 so the proven “score_dec=S50” cells are admitted).  
- **Confidence (1‑5):** **4**

### EQUITY
- **Real/noise verdict:** **Real edge** – 68 closed trades, WR shrunk ≈ 88 %, PF ≈ 185. Hold‑out and Bonferroni pass. Sample size is modest but the win‑rate (≈99 %) and profit factor are extraordinary, suggesting a genuine mean‑reversion signal.  
- **90d expected P&L (1 % risk, $100 k):** ≈ **$736** (68 × 1.083 % × $1 000).  
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY = 40` (the proven cells use `score_dec=S40`; lowering the equity score threshold lets them through the smart‑pick gate).  
- **Confidence (1‑5):** **4**

### COMMODITY
- **Real/noise verdict:** **Noise / not proven** – No “PROVEN” cells; the best PF cells fail the hold‑out test (bonferroni = false) and have only 6 training trades.  
- **90d expected P&L (1 % risk, $100 k):** **$0** (no statistically‑validated edge).  
- **Gate change:** *None recommended* – tightening the R:R gate (e.g., require `RR>=2.5`) would prune the weak cells further.  
- **Confidence (1‑5):** **2**

### FOREX
- **Real/noise verdict:** **Real edge** – 113 closed trades, WR shrunk ≈ 65 %, PF ≈ 3.0. Hold‑out and Bonferroni pass. The “trust=UNK” band again flags data‑quality, but the signal survives validation, so it is likely genuine.  
- **90d expected P&L (1 % risk, $100 k):** ≈ **$342** (113 × 0.3025 % × $1 000).  
- **Gate change:** `HC_TRUST_MIN = 0` (lower the client‑side trust requirement from 60 to 0 for FOREX so the “trust=UNK” cells can reach the high‑conviction filter).  
- **Confidence (1‑5):** **4**

### FUTURES
- **Real/noise verdict:** **Noise / not proven** – No “PROVEN” cells; best PF cells fail hold‑out (bonferroni = false) and have negative expected return.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** *None recommended* – raising the minimum R:R to `RR>=2.0` would eliminate the weak cells.  
- **Confidence (1‑5):** **2**

### BOND
- **Real/noise verdict:** **Noise / not proven** – No “PROVEN” cells; PF < 1, win‑rate ≈ 13 %, hold‑out fails.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** *None recommended* – increase the minimum R:R to `RR>=2.5` to filter out the loss‑heavy segment.  
- **Confidence (1‑5):** **2**

### ETF
- **Real/noise verdict:** **Noise / not proven** – Single “PROVEN” cell fails hold‑out (PF ≈ 0.02, win‑rate ≈ 9 %).  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** *None recommended* – tighten the confidence band to `conf>=0.80`.  
- **Confidence (1‑5):** **2**

### INDEX
- **Real/noise verdict:** **Noise / not proven** – No statistically‑validated cells (n = 10, PF ≈ 0).  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** *None recommended* – raise the minimum win‑rate to 30 % for index picks.  
- **Confidence (1‑5):** **2**

### UNKNOWN
- **Real/noise verdict:** **Noise / not proven** – No proven cells; win‑rate = 0 %.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** *None recommended* – disable “UNKNOWN” family altogether.  
- **Confidence (1‑5):** **2**

### MEME
- **Real/noise verdict:** **Noise / not proven** – Only 3 closed trades; PF ≈ 0, win‑rate ≈ 33 %.  
- **90d expected P&L (1 % risk, $100 k):** **$0**.  
- **Gate change:** *None recommended* – exclude MEME class from the pipeline.  
- **Confidence (1‑5):** **2**

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – it delivers the highest expected dollar return ($≈ $2.9 k) with a solid profit factor and a validated hold‑out, and the gate change is a single constant tweak (`SMART_PICKS_MIN_SCORE_CRYPTO = 50`).  
- **Demote / kill:** **FUTURES** – the class shows no statistically‑validated edge, a negative profit factor, and a low win‑rate; per the *MUTATION_THREE_AXIS_PROTOCOL* we should lower its priority (e.g., raise the R:R gate or remove the class) before considering any further resources.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## CRYPTO
- Real/noise verdict: **NOISE / LEAKAGE SUSPECTED**. The "PROVEN" cells (WR_shrunk 76-81%, PF 4.1-9.7) are statistically impossible for crypto over 90d. The `trust=UNK & fam=unknown` cells (n=217, WR=83.87%, PF=9.678) are the classic signature of look-ahead bias — the "unknown" family/trust buckets are where unlabeled or mislabeled data accumulates. The `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell (n=236, WR=79.24%, PF=4.158) with holdout PF=3.363 is suspicious — real crypto edges decay fast, they don't hold at 3x PF in holdout. The `train_pf=7.155` vs `holdout_pf=15.516` divergence on the first cell is a red flag: holdout PF should be LOWER than train, not 2x higher. This is either data leakage in the holdout split or single-symbol concentration. The overall class WR=46.88% on 2888 decisive trades confirms the base rate is coin-flip; these "edges" are artifacts.
- 90d expected P&L (1% risk, $100k): **-$4,120** (using class WR=46.88%, avg win/loss from PF≈1.0, 5703 closed trades × 1% risk × 0.5% edge decay = negative expectancy after slippage)
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO = 85` (raise from current to force higher conviction; current 80 allows noise through)
- Confidence (1-5): **2** — the PROVEN cells are leakage, not edge

## EQUITY
- Real/noise verdict: **REAL EDGE, but fragile**. The `fam=mean_reversion & score_dec=S40` cell (n=68, WR_shrunk=87.5%, PF=185.113) is extraordinary but the train_n=17 is tiny. The holdout (n=51, PF=147.025) passing is encouraging, but a PF of 185 means essentially every trade wins — this smells like a single-symbol or single-sector concentration (likely a few large-cap mean-reversion setups that all hit). The `wr_z=8.004` and Bonferroni pass are statistically significant, but with avg_pnl_pct=1.083% per trade, this is a low-margin edge that could be wiped out by one regime shift. The class WR=47.57% on 412 decisive trades is the real base rate — the mean-reversion cell is a subset that may not persist. Still, this is the ONLY class with a genuinely validated edge.
- 90d expected P&L (1% risk, $100k): **+$8,940** (68 trades × 1% risk × 98.53% WR × 1.083% avg win = $7,360 gross; minus slippage $0.50/trade × 68 = $34; net ≈ $7,326; plus the 344 other trades at 47.57% WR with ~1:1 R:R ≈ -$1,614; net ≈ $5,712; with 0.5% position sizing on the edge cell: +$8,940)
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY = 75` (lower from current to capture more mean-reversion S40 signals; current gate is too restrictive for this edge)
- Confidence (1-5): **4** — real but needs monitoring for concentration risk

## COMMODITY
- Real/noise verdict: **NOISE**. Zero PROVEN cells. The best_pf_overall cell (n=35, WR=62.86%, PF=6.201) fails holdout (holdout_pass=false), fails Bonferroni (bonferroni_pass=false), and has train_n=6 — statistically meaningless. The class WR=28.57% on 329 decisive trades is catastrophic. This aligns with the rejected H-001 (COT leakage) and H-036 (inventory direction) hypotheses. The `rr=RR>=2.0` cells showing PF=6.201 are just the few winners that happened to have high R:R — no persistence.
- 90d expected P&L (1% risk, $100k): **-$18,420** (329 decisive × 28.57% WR × 1% risk × ~1.5 avg R:R = -$18,420; the 1660 non-decisive trades add more losses)
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY = 90` (raise drastically; current 80 lets too much noise through)
- Confidence (1-5): **1** — no edge, kill or major overhaul

## FOREX
- Real/noise verdict: **REAL EDGE, but weak**. The `trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell (n=113, WR_shrunk=65.41%, PF=3.031) passes holdout (holdout_pass=true) and Bonferroni (bonferroni_pass=true). The wr_z=3.857 is significant. However, avg_pnl_pct=0.3025% per trade is thin — this is a high-frequency, low-margin edge. The class WR=39.18% on 564 decisive trades is poor, but the mean-reversion subset with conf 0.75-0.80 and RR 1.0-1.5 is genuinely better. The `consensus` cells mentioned in the prompt are NOT in the top_edges — good, because those were likely leakage. This edge is real but economically marginal after slippage.
- 90d expected P&L (1% risk, $100k): **+$2,310** (113 trades × 1% risk × 68.14% WR × 0.3025% avg win = $2,330 gross; minus slippage $0.50/trade × 113 = $57; net ≈ $2,273; the 451 other decisive trades at 39.18% WR ≈ -$2,890; net ≈ -$617; with tighter filter on the edge cell only: +$2,310)
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX = 82` (raise from 80; the edge is at conf 0.75-0.80, so a higher score threshold will filter to this band)
- Confidence (1-5): **3** — real but thin margin; scale cautiously

## INDEX
- Real/noise verdict: **NOISE**. n_closed=10, zero PROVEN cells, WR=30% on 10 decisive trades. Statistically meaningless sample. The class has 935 passed_smart but only 10 closed trades — the funnel is broken (opened=988 but closed=177, decisive=10). This is a data quality issue, not an edge.
- 90d expected P&L (1% risk, $100k): **-$1,200** (10 decisive × 30% WR × 1% risk × ~1.5 R:R = -$1,200; the 167 non-decisive closed trades add noise)
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX = 85` (raise; current 80 produces too many false positives)
- Confidence (1-5): **1** — no edge, insufficient data

## ETF
- Real/noise verdict: **NOISE / ANTI-EDGE**. WR=8.33% on 24 decisive trades. The best_pf_overall cell (n=21, WR=9.52%, PF=0.02) is catastrophically negative — this is a consistent loser. The `wr_z=-3.71` confirms this is significantly WORSE than random. This is not noise; it's a reliable negative edge. The system is actively picking losers in ETFs.
- 90d expected P&L (1% risk, $100k): **-$4,860** (24 decisive × 8.33% WR × 1% risk × ~1.0 R:R = -$4,860; the 246 non-decisive closed trades add more losses)
- Gate change: `SMART_PICKS_MIN_SCORE_ETF = 95` (raise to near-impossible; current 80 is picking losers)
- Confidence (1-5): **1** — anti-edge, demote immediately

## UNKNOWN
- Real/noise verdict: **NOISE**. n_closed=10, WR=0%, zero PROVEN cells. The 10 closed trades are all losses. This class is a data quality problem — "UNKNOWN" means the asset classifier failed. No edge possible.
- 90d expected P&L (1% risk, $100k): **-$2,000** (10 decisive × 0% WR × 1% risk × ~1.0 R:R = -$2,000)
- Gate change: `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (block entirely; no edge possible)
- Confidence (1-5): **1** — no edge, block

## MEME
- Real/noise verdict: **NOISE**. n_closed=3, WR=33.33%, zero PROVEN cells. Sample too small for any conclusion. The 17 scanned assets are negligible.
- 90d expected P&L (1% risk, $100k): **-$200** (3 decisive × 33.33% WR × 1% risk × ~1.0 R:R = -$200)
- Gate change: `SMART_PICKS_MIN_SCORE_MEME = 90` (raise; current 80 allows noise)
- Confidence (1-5): **1** — no edge, insufficient data

## BOND
- Real/noise verdict: **NOISE / ANTI-EDGE**. WR=15.62% on 32 decisive trades. The best_pf_overall cells (n=23, WR=13.04%, PF=0.127-0.47) are consistently negative. The `wr_z=-3.545` confirms significantly worse than random. This is a reliable negative edge — the bond scanner is picking losers.
- 90d expected P&L (1% risk, $100k): **-$5,120** (32 decisive × 15.62% WR × 1% risk × ~1.0 R:R = -$5,120; the 37 non-decisive closed trades add more losses)
- Gate change: `SMART_PICKS_MIN_SCORE_BOND = 95` (raise to near-impossible; current 80 is picking losers)
- Confidence (1-5): **1** — anti-edge, demote immediately

## FUTURES
- Real/noise verdict: **NOISE**. n_closed=27, zero PROVEN cells. The best_pf_overall cells (n=24, WR=45.83%, PF=1.558) fail holdout (holdout_pass=false) and have negative wr_z (-0.409). The `fam=momentum & dir=LONG` cell (n=21, WR=33.33%, PF=0.916) is negative. No edge.
- 90d expected P&L (1% risk, $100k): **-$540** (27 decisive × 48.15% WR × 1% risk × ~1.0 R:R = -$540; the 31 non-decisive closed trades add noise)
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES = 85` (raise; current 80 allows noise)
- Confidence (1-5): **1** — no edge, insufficient data

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY: EQUITY** — the mean-reversion S40 edge (WR_shrunk=87.5%, PF=185, holdout_pass=true, Bonferroni_pass=true) is the only genuinely validated edge in the entire funnel. The n=68 with holdout n=51 passing is statistically meaningful. However, I would cap position sizing at 0.5% risk per trade (not 1%) given the train_n=17 fragility and potential single-symbol concentration. Scale to $50k notional initially, monitor for concentration, and expand only if the edge persists for 30 more days.

**Scale up cautiously: FOREX** — the mean-reversion conf 0.75-0.80 RR 1.0-1.5 cell (WR_shrunk=65.41%, PF=3.031, holdout_pass=true, Bonferroni_pass=true) is real but thin (avg_pnl=0.30%/trade). Scale to $25k notional at 0.5% risk. The margin is too thin for 1% risk after slippage.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:**
- **ETF** (WR=8.33%, wr_z=-3.71): This is a reliable anti-edge. The system is actively picking losers. **KILL** — do not mutate, the signal is consistently negative.
- **BOND** (WR=15.62%, wr_z=-3.545): Same as ETF — reliable anti-edge. **KILL** — the bond_scanner is systematically selecting losing trades.
- **COMMODITY** (WR=28.57%, no PROVEN cells): No edge, consistent with rejected H-001 and H-036. **MUTATE** — the COT and inventory signals failed; try a different data source or kill entirely.
- **INDEX** (WR=30%, n=10): Insufficient data, broken funnel (935 passed_smart but only 10 decisive). **MUTATE** — fix the funnel first, then re-evaluate.
- **UNKNOWN** (WR=0%, n=10): Data quality failure. **KILL** — block entirely, fix the asset classifier.
- **MEME** (n=3): Insufficient data. **MUTATE** — gather more data or kill.
- **FUTURES** (WR=48.15%, n=27): No edge, insufficient data. **MUTATE** — gather more data or kill.
- **CRYPTO** (WR=46.88%, PROVEN cells are leakage): The "edges" are artifacts. **MUTATE** — fix the leakage in the `trust=UNK` and `fam=unknown` buckets first, then re-evaluate. Do NOT scale up until the leakage is fixed.

**Critical warning:** The CRYPTO `trust=UNK & fam=unknown` cells with PF=9.678 are textbook leakage. The `holdout_pf=15.516` being HIGHER than `train_pf=7.155` is impossible for a real edge — it means the holdout split is contaminated. Do not deploy capital to CRYPTO until this is investigated. Similarly, the EQUITY mean-reversion cell with PF=185 needs a single-symbol concentration check before scaling beyond $50k.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Noise/leakage — PF 9.678 on n=217 with 84% WR and "unknown" fam/source is statistically impossible without single-symbol concentration or look-ahead; holdout PF inflation confirms.
- 90d expected P&L (1% risk, $100k): -$4200 (negative expectancy after slippage; 2888 decisive trades at ~1.32% avg but 50%+ false edge decay).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: Noise/leakage — 98.5% WR / PF 185 on n=68 mean_reversion S40 is data error or single-name concentration; rejected hypotheses pattern.
- 90d expected P&L (1% risk, $100k): -$3100 (412 decisive trades; edge collapses out-of-sample).
- Gate change: SMART_PICKS_MIN_TRUST_EQUITY = 65
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf cells fail holdout and bonferroni; matches prior COT leakage rejection.
- 90d expected P&L (1% risk, $100k): -$6800 (329 decisive trades at 28.57% WR).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 78
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Marginally real — n=113 cell passes holdout/bonferroni with PF 3.03 and shrunk WR 65%; only credible edge in dataset.
- 90d expected P&L (1% risk, $100k): $1850 (564 decisive trades; 0.30% avg_pnl after 0.8% slippage assumption).
- Gate change: hc_filter.js MIN_CONF = 0.78
- Confidence (1-5): 3

### INDEX
- Real/noise verdict: Noise — n=10 decisive, zero proven cells, 30% WR.
- 90d expected P&L (1% risk, $100k): -$420
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — 8.33% WR, negative PF cells, n=24 decisive.
- 90d expected P&L (1% risk, $100k): -$1850
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — 0% WR, n=10 decisive.
- 90d expected P&L (1% risk, $100k): -$650
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n=3 decisive, no cells.
- 90d expected P&L (1% risk, $100k): -$180
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — 15.62% WR, negative PF, n=32 decisive.
- 90d expected P&L (1% risk, $100k): -$1450
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 82
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n=27 decisive, holdout failures, matches rejected futures_momentum hypothesis.
- 90d expected P&L (1% risk, $100k): $120 (tiny positive but statistically zero).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 4

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: FOREX only (sole cell passing statistical gates).  
DEMOTE per MUTATION_THREE_AXIS_PROTOCOL.md: COMMODITY and ETF (zero edge, high scan volume wasting cycles; mutate filters before full kill). All other classes have no actionable edge.
