# Pick Funnel Swarm Verdict — 2026-11-20 04:41 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261120T044110Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three structural facts that dominate everything below:

1. **`passed_high_conviction = 0` across every single class.** The HC gate (score≥80, conf≥0.75, trust≥60) is dead code in production. Nothing has ever passed it in 90 days. Any "HC edge" claim is untestable — there is no HC cohort.
2. **`passed_verified_alpha` is 0 for 8 of 11 classes.** Only CRYPTO (2588), FOREX (9), FUTURES (1), MEME (2) have any verified-alpha picks. The verified-alpha funnel is effectively CRYPTO-only.
3. **The funnel is inverted.** `opened` ≈ `scanned` in every class (e.g. FOREX 26,342 opened vs 27,731 scanned = 95%). The "gates" are not gating. `passed_smart` is the only real filter and it's permissive (FOREX 97.6% pass, COMMODITY 66%, INDEX 75%). The dashboard is showing you a funnel that doesn't exist.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell `rr=RR>=2.0 & fam=mean_reversion` has n=37, WR=97.3%, PF=132. Three red flags: (i) PF=132 with avg_pnl=1.6% is mathematically impossible without a single outsized winner or a PnL accounting bug — 36 wins × 1.6% ≈ 58% gross return on 37 trades at 1% risk is not PF=132; (ii) `trust=UNK` on 100% of the cell means the trust dimension is not populated — this is a data-plumbing artifact, not an edge; (iii) train_n=11, holdout_n=26 with holdout_pf=99.0 (capped) is the classic signature of a **single-symbol or single-event concentration** — 36/37 wins in mean_reversion LONG almost certainly = one ticker in one regime. `bonferroni_pass=true` on a cell that is one of three near-identical projections of the same 37 trades (trust/rr/fam, rr/fam/dir, rr/fam/source are the *same trades* re-sliced) is a Bonferroni accounting error — you corrected for 3 tests but they're 1 test. **Do not trade this.** It is the same failure mode as H-001 (COT leakage): a clean-looking cell that collapses on dedup.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not size. If forced to model the *reported* cell: 37 trades × 1% × 1.6% avg = ~$592 gross, but I assign ≥90% probability this is leakage and the true expectancy is negative. Expected realized: **–$200 to +$100**, i.e. noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — currently permissive (227/5759 = 3.9% pass, which is fine) but the real problem is `trust=UNK` on 100% of closed trades. Set `TRUST_MIN_EQUITY = 60` (currently effectively 0/UNK) so no EQUITY pick can close without a populated trust score. This kills the leakage cell at the source.
- **Confidence (1-5):** **1**

---

### COMMODITY
- **Real/noise verdict:** **NO EDGE.** `top_edges_proven = []`. Best cell is `trust=UNK & dir=LONG & source=alpha_engine`, n=32, WR_shrunk=55.8%, PF=1.90, but `bonferroni_pass=false` and holdout_n=13. This is a LONG-only commodity beta tilt over a 90d window — it is not a strategy, it is "commodities went up." The H-001 and H-036 rejections in your registry confirm this class has repeatedly produced false positives that die on timestamp/dedup fixes. n=40 closed total is far too thin to certify anything.
- **90d expected P&L (1% risk, $100k):** **$0.** If you traded the best cell at n=32: 32 × 1% × 0.66% = ~$211 gross, but with `bonferroni_pass=false` and a LONG-beta confound, expected realized is **–$50 to +$150**. Not investable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **65** (from current permissive ~50 that lets 66% through). 3794/5730 = 66% pass rate is not a filter. Target ~15% pass.
- **Confidence (1-5):** **1**

---

### FOREX
- **Real/noise verdict:** **NOISE — and the PF=14.4 cell is the most suspicious number in the entire dataset.** `trust=UNK & conf=C>=0.90 & fam=regime` / `source=regime_terminal`: n=38, WR=89.5%, PF=14.4, **holdout_n=2**, `holdout_pass=false`. This is the textbook signature of **single-symbol concentration + look-ahead in the regime label**. `regime_terminal` as a source name strongly implies the regime was labeled *after* the outcome (terminal = end-of-window classification). 34/38 wins at conf≥0.90 with only 2 holdout trades means the "holdout" is not a holdout — it's 2 trades. `bonferroni_pass=true` is again a mis-correction (3 projections of the same 38 trades). **This is H-001-class leakage.** The class-level WR of 50.85% (n=468 decisive) is the honest number: **zero edge, coin flip.** The 26,342 opened vs 27,731 scanned (95%) confirms the gates are not filtering FOREX at all.
- **90d expected P&L (1% risk, $100k):** **$0.** Class-level: 468 decisive × 1% × (50.85% WR at ~1:1) ≈ **–$50 to +$50** after slippage. The PF=14.4 cell is not tradeable — it's a data artifact. Expected realized on the "edge": **negative** once you account for the 2-trade holdout being meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **70** (currently 97.6% pass = no gate). This is the single highest-leverage change in the whole system: it would cut 26,342 opens to ~2,000 and force the regime_terminal source to prove itself on a real sample. Also add `TRUST_MIN_FOREX = 60` to kill `trust=UNK` cells.
- **Confidence (1-5):** **1** (that there is no edge); **5** (that the PF=14.4 cell is leakage)

---

### CRYPTO
- **Real/noise verdict:** **THE ONLY CLASS WITH A DEFENSIBLE EDGE — but it's modest, not the PF=1.79 headline.** The one cell that survives scrutiny: `trust=UNK & conf=C0.75-0.80 & score_dec=S50`, n=194, WR_shrunk=63.1%, PF=1.68, train_pf=1.40, holdout_pf=2.39, holdout_n=82, `bonferroni_pass=true`. This is the *only* cell in the entire dataset where: (i) n is large enough to matter (194), (ii) holdout_n is real (82), (iii) train and holdout are both >1.3 PF, (iv) the Bonferroni correction is not obviously mis-applied (it's one of many cells but the only one that passes). **Caveat:** `trust=UNK` again — the trust dimension is unpopulated, so this is really "conf 0.75-0.80 & score_dec=S50" and the trust label is noise. The `best_pf_overall` cells (PF=1.79, `rr=RR1.5-2.0 & source=alpha_engine`) have `bonferroni_pass=false` and holdout_pf=1.24 — treat as **suggestive, not proven**. The class-level WR of 45.2% (n=2170) is the honest baseline: **slightly negative before the conf-band filter, positive after.** The edge is real but thin and concentrated in a narrow confidence band.
- **90d expected P&L (1% risk, $100k):** Model the proven cell: 194 trades × 1% risk × avg_pnl 0.67% = **~$1,300 gross**. Apply 15% slippage/fee haircut on crypto (wide spreads, funding): **~$1,100 net**. If you also take the `best_pf_overall` cell (n=169, avg 0.86%, but unproven): +$1,450 gross, –15% = +$1,230, but with lower confidence — discount 50% for `bonferroni_pass=false`: **+$615 expected**. **Total realistic 90d P&L: $1,100–$1,700.** This is the only class where the number is positive and defensible.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **narrow the conf band, don't raise the score.** The edge lives at conf 0.75–0.80; the current gate lets 3861/11604 = 33% through, which dilutes the edge with conf>0.85 picks that underperform. Set `CRYPTO_CONF_BAND = [0.75, 0.82]` (or equivalently `SMART_PICKS_MIN_SCORE_CRYPTO = 55` with a `MAX_CONF_CRYPTO = 0.82` cap). This is counterintuitive but the data says high-confidence crypto picks are *worse* — classic overconfidence in a fat-tailed asset.
- **Confidence (1-5):** **3** (edge is real but thin; the PF=1.68 cell is the only one I'd size)

---

### ETF
- **Real/noise verdict:** **NO EDGE — actively bad.** n=8 closed, WR=12.5% (1 win, 7 losses). This is not noise, it's a small sample of a losing strategy. 270/306 passed_smart = 88% pass rate = no gate. Do not trade.
- **90d expected P&L (1% risk, $100k):** **–$60** (8 trades × 1% × –7.5% avg, roughly). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **70** (from ~50). 88% pass is not a filter. Or better: **disable ETF picks entirely** until n≥30 closed with WR>50%.
- **Confidence (1-5):** **1** (confident it's bad)

---

### PREDICTION_MARKET
- **Real/noise verdict:** **UNTESTABLE.** n=0 closed. 69 scanned, 3 passed_smart, 69 opened, 0 closed. The class is not resolving — either the resolution pipeline is broken or the market horizon exceeds 90d. Cannot certify or reject.
- **90d expected P&L (1% risk, $100k):** **$0** (no closed trades).
- **Gate change:** None — fix the resolution pipeline first. `PREDICTION_MARKET_RESOLUTION_ENABLED = True` (currently effectively off).
- **Confidence (1-5):** **1** (no data)

---

### BOND
- **Real/noise verdict:** **NO EDGE — negative.** n=31, WR=38.7%. 1/1188 passed_smart = 0.08% pass rate, which means the gate is *too tight* and the 1157 opened picks are ungated garbage. This is the opposite failure mode from FOREX: the gate rejects almost everything, but the pipeline opens anyway. The 12 wins / 19 losses is a real losing sample.
- **90d expected P&L (1% risk, $100k):** **–$120** (31 × 1% × –3.9% avg). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **lower to 45** (from current ~55 that rejects 99.9%) AND add `BOND_MAX_OPEN_PER_DAY = 5` to stop the 1157-opens-against-1-pass leak. The gate isn't the problem; the bypass is.
- **Confidence (1-5):** **2** (small n but directionally clear)

---

### UNKNOWN
- **Real/noise verdict:** **DATA HYGIENE FAILURE.** n=5, WR=0%. 1242 scanned, 106 passed_smart, 1237 opened. This class should not exist — it's picks that failed asset-class classification. 0/5 wins is not an edge signal, it's a routing bug. **Do not trade. Fix the classifier.**
- **90d expected P&L (1% risk, $100k):** **–$25** (5 × 1% × –5%). Negative and meaningless.
- **Gate change:** `ASSET_CLASS_FALLBACK = "REJECT"` (currently defaults to UNKNOWN and opens anyway). Route UNKNOWN to a quarantine queue, not to `opened`.
- **Confidence (1-5):** **1**

---

### INDEX
- **Real/noise verdict:** **UNTESTABLE.** n=1 closed, 1 win. 1542/2042 passed_smart = 75% pass. One trade is not a sample. The 100% WR is meaningless.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1, not investable).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **65** (from ~50). 75% pass is not a filter. But the real issue is n=1 closed — the resolution pipeline for INDEX is broken.
- **Confidence (1-5):** **1**

---

### FUTURES
- **Real/noise verdict:** **NO EDGE — negative.** n=16, WR=37.5%. 111/156 passed_smart = 71% pass. H-005 in your registry already killed the futures momentum inversion. This class has no demonstrated edge and a small losing sample.
- **90d expected P&L (1% risk, $100k):** **–$100** (16 × 1% × –6.25% avg). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **70** (from ~50). 71% pass is not a filter.
- **Confidence (1-5):** **2** (small n but consistent with H-005)

---

### MEME
- **Real/noise verdict:** **UNTESTABLE / NO EDGE.** n=5, WR=40%. 4/12 passed_smart. Too thin to certify, directionally negative. Do not trade.
- **90d expected P&L (1% risk, $100k):** **–$20** (5 × 1% × –4%). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **75** (from ~50). 33% pass on n=12 is noise; require n≥30 before re-enabling.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the conf 0.75–0.82 band.** It is the only class with (i) a large enough closed sample (n=2170), (ii) a cell that survives train/holdout/Bonferroni scrutiny (n=194, WR_shrunk=63.1%, PF=1.68, holdout_n=82), and (iii) a positive expected P&L under realistic slippage (~$1,100–$1,700 per 90d on $100k at 1% risk). Size it at **0.5% risk per trade, not 1%**, until the cell accumulates another 90d out-of-sample — the edge is real but thin, and the `trust=UNK` label means you're flying without a trust dimension.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill): FOREX.** It is the largest funnel (27,731 scanned, 26,342 opened) with the worst gate integrity (97.6% pass rate = no gate) and the most suspicious "edge" (PF=14.4 on n=38 with holdout_n=2 — this is H-001-class leakage, not a strategy). Do not kill it outright — mutate the gate first: `SMART_PICKS_MIN_SCORE_FOREX = 70` and `TRUST_MIN_FOREX = 60`. If after 90d the class-level WR is still ~50% on a properly gated sample, then kill. The current 95% open rate means you are paying spread on 26,000 coin-flip trades per quarter — that is the single largest P&L leak in the system, larger than any edge you could add.

**Second demotion: EQUITY.** The PF=132 cell is leakage (same failure mode as H-001). Mutate `TRUST_MIN_EQUITY = 60` to force trust population, then re-test. Do not trade the

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage. n=37 is tiny; WR_shrunk 80.7% and PF=132 are statistically impossible without single-symbol concentration or look-ahead bug in mean_reversion scanner. Holdout PF=99 on 26 trades is a red flag.
- 90d expected P&L (1% risk, $100k): $0 (edge is not real).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise. No proven cells; all best_pf cells fail bonferroni or holdout and n<35.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: None (no edge to protect)
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise. No proven cells; regime cells show PF=14 only because holdout n=2. Bonferroni pass is meaningless on such small samples.
- 90d expected P&L (1% risk, $100k): $0 (no usable edge).
- Gate change: None (no edge to protect)
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Marginally real. One proven cell (n=194, WR_shrunk=63.08, PF=1.68) passes holdout and bonferroni; other high-PF cells are weaker and fail bonferroni.
- 90d expected P&L (1% risk, $100k): ~$2,800 (assume ~40 qualifying trades/90d at 1% risk, avg win 0.67% after slippage).
- Gate change: HC_MIN_CONF = 0.78
- Confidence (1-5): 3

### ETF
- Real/noise verdict: Noise (n=8 total closed).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

### PREDICTION_MARKET
- Real/noise verdict: Noise (n=0 closed).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n=31, no proven cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n=5).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n=1).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n=16, no proven cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n=5).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with a statistically credible cell). DEMOTE EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its "edge" is almost certainly leakage and should be mutated or killed before any further capital allocation. All other classes have no actionable edge.
