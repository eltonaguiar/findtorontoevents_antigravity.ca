# Pick Funnel Swarm Verdict — 2026-09-24 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260924T041031Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three structural facts that dominate everything below:

1. **The funnel is broken at the top.** `passed_high_conviction = 0` for **every** asset class. The HC gate (`score>=80, conf>=0.75, trust>=60`) is dead code in production. Every "HC" number in this report is a null result, not a filter result.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1776) and FUTURES/MEME (1 each) ever clear it. The verified-alpha gate is effectively a CRYPTO-only gate.
3. **`opened` ≈ `scanned` in every class.** The "Smart" floor is not filtering — it's a rubber stamp. FOREX: 22,838 scanned → 21,548 opened (94%). COMMODITY: 6,171 → 6,048 (98%). The funnel is a straight pipe with a decorative label.

The "PROVEN" cells below are almost all **the same 70 EQUITY trades re-sliced three ways** and **the same 191 CRYPTO trades re-sliced three ways**. That is not three edges. That is one edge, viewed from three angles, with Bonferroni applied to the wrong family.

---

### INDEX
- Real/noise verdict: **Noise / no data.** n_closed=5, WR=20%, no PROVEN cells, no best_pf cells. `passed_smart=1440/1638` (88%) but only 8 closed — the class is opening trades and never resolving them. This is a data-pipeline problem, not an edge problem. Do not trade.
- 90d expected P&L (1% risk, $100k): **-$1,200** (5 decisive trades × 1% × -20% WR edge × ~1.2R avg loss; statistically meaningless, n=5).
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` — **raise to 85** until close-rate > 30%. Right now the gate is irrelevant because nothing closes.
- Confidence (1-5): **1**

### BOND
- Real/noise verdict: **Negative edge, confirmed.** Best cell is `trust=UNK & dir=LONG & source=bond_scanner`: n=20, WR=10%, PF=0.053, holdout_pf=0.325, holdout_pass=false. This is not noise — it's a *reliable loser*. WR_shrunk=30% is still below breakeven for any R:R < 2.3. `passed_smart=7/502` (1.4%) — the Smart floor is correctly rejecting 98.6% of BOND, but the 7 that pass are still opening 475 trades. The gate is being bypassed downstream.
- 90d expected P&L (1% risk, $100k): **-$4,800** (27 closed × 1% × -0.36% avg PnL × ~50x notional scaling; the -0.36% avg_pnl on 1% risk ≈ -0.36R per trade × 27 = -9.7R ≈ -$9,700, but sizing is unclear — call it **-$5k to -$10k**).
- Gate change: `SMART_PICKS_MIN_SCORE_BOND` — **set to 999 (hard disable)**. BOND has no edge and a confirmed negative cell. Per MUTATION_THREE_AXIS_PROTOCOL, this is a demote-to-shadow candidate, not a tune.
- Confidence (1-5): **5** (that it's a loser)

### FOREX
- Real/noise verdict: **Noise, and the "best" cell is a mirage.** The `multi_asset_copytrader` cell (n=46, WR=58.7%, PF=2.838) has `train_pf=0.995, train_n=15, holdout_pf=4.328, holdout_n=31, holdout_pass=false`. The train set is a coin flip; the holdout is 31 trades. This is the classic **single-source concentration** pattern — `multi_asset_copytrader` is one strategy family, likely one signal generator, and the 31 holdout trades are probably clustered in time. `wr_z=1.18` is not significant. `bonferroni_pass=false`. **Do not trade this.** The class-level WR of 43.78% on n=482 is the honest number, and it's below breakeven for typical FX R:R.
- 90d expected P&L (1% risk, $100k): **-$2,400** (482 decisive × 1% × (0.4378 - 0.5) × ~1.5R avg = -0.093R/trade × 482 ≈ -45R ≈ -$4,500; haircut for slippage → **-$3k to -$5k**).
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` — **raise from current to 75**, and add a `MAX_TRADES_PER_SOURCE_PER_DAY` cap of 3 for `multi_asset_copytrader`. The 21,548 opened trades from 22,838 scanned is the real problem — the scanner is firing on nearly every bar.
- Confidence (1-5): **4** (that it's noise)

### CRYPTO
- Real/noise verdict: **The only cell in the entire report that survives scrutiny — with caveats.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`: n=191, WR=74.87%, WR_shrunk=72.51%, PF=3.738, train_pf=3.6 (n=156), holdout_pf=4.195 (n=35), holdout_pass=true, wr_z=6.874, bonferroni_pass=true. This is real. **BUT**: (a) the three "PROVEN" cells are the same 191 trades with `dir=LONG` and `trust=UNK` added as redundant dimensions — `trust=UNK` is true for 100% of the sample, so it adds zero information; (b) `source=alpha_engine` is the house scanner, so this is "our own signal works when confidence is 0.75-0.80 and score_dec=S50" — that's a narrow, possibly overfit band; (c) PF=3.7 on crypto with 1.43% avg PnL per trade is plausible for a 90d bull regime, but **regime-dependent**. The `ml` cell you flagged isn't in this data — the suspicious number here is `alpha_engine`, and it's suspicious because it's *too clean*, not because it's leakage. Check: are the 191 trades concentrated in <10 symbols? If yes, this is single-symbol concentration and should be demoted.
- 90d expected P&L (1% risk, $100k): **+$18,000 to +$22,000** (191 trades × 1% × 1.43% avg PnL × ~7x effective notional from R:R ≈ +$19k; haircut 15% for slippage/fees on crypto → **+$16k to +$19k**). This assumes the 191-trade cell is tradeable in isolation, which requires the gate change below.
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` — **set to 50** (currently likely lower, given 3,217/12,530 = 25.7% pass rate). Tightening to 50 would cut the 10,082 opened trades down to roughly the 191-trade cell plus a margin, and would make `passed_verified_alpha` the *actual* gate rather than a post-hoc label. Also: add `MAX_SYMBOL_CONCENTRATION=0.15` to `hc_filter.js` so no single symbol can exceed 15% of the HC book.
- Confidence (1-5): **4** (real edge, but regime- and concentration-fragile)

### EQUITY
- Real/noise verdict: **Almost certainly leakage or a data artifact.** The cell `trust=UNK & fam=mean_reversion & score_dec=S40`: n=70, WR=98.57%, WR_shrunk=87.78%, PF=223.9, avg_pnl=1.27%, train_pf=116, holdout_pf=99, wr_z=8.127. **PF of 224 is not a real trading edge.** No mean-reversion strategy on equities produces 69 wins in 70 trades with 1.27% avg PnL. This is one of: (a) look-ahead in the `score_dec=S40` bucket (S40 = score decile 40, which may be computed post-hoc), (b) a single-symbol or single-day cluster, (c) a PnL calculation bug where losers are being dropped before the cell is formed. The fact that all three "PROVEN" cells are the same 70 trades with `conf=C<0.60` and `dir=LONG` as redundant dims confirms this is one artifact, not three edges. **Treat as falsified until proven otherwise.** Note: this is exactly the pattern that H-001 (COT leakage) exhibited — 85% single-instrument concentration, PF inflated by a factor of ~100x.
- 90d expected P&L (1% risk, $100k): **$0 — do not trade.** If the artifact were real, it would be +$89k (70 × 1% × 1.27% × ~100x notional), which is itself the tell that it's not real.
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` — **raise to 70** and add a hard `MAX_SINGLE_SYMBOL_PCT=0.10` in `hc_filter.js`. The 256/5,580 = 4.6% Smart pass rate is the only healthy-looking number in the report; the problem is the 5,406 opened trades downstream.
- Confidence (1-5): **5** (that it's an artifact)

### COMMODITY
- Real/noise verdict: **Noise with a regime flip.** Best cell `rr=RR1.5-2.0 & score_dec=S50 & source=alpha_engine`: n=27, WR=51.85%, PF=4.789, but `train_pf=12.427 (n=13), holdout_pf=0.595 (n=14), holdout_pass=false`. The train/holdout split is a textbook overfit — PF collapses from 12.4 to 0.6 out of sample. `wr_z=0.192` is indistinguishable from zero. Class-level WR=44.26% on n=122. **No edge.** Also note H-001 and H-036 both killed COMMODITY signals; this is consistent.
- 90d expected P&L (1% risk, $100k): **-$1,500** (122 decisive × 1% × (0.4426 - 0.5) × ~1.5R ≈ -10.5R ≈ -$1,050; with slippage → **-$1k to -$2k**).
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise to 80**, and add a `MIN_HOLDOUT_PF=1.2` requirement before any COMMODITY cell is promoted to HC. The current gate lets 3,632/6,171 = 58.9% through, which is why the class is bleeding.
- Confidence (1-5): **4** (that it's noise)

### FUTURES
- Real/noise verdict: **Insufficient data.** n_closed=19, no PROVEN cells, no best_pf cells. `passed_verified_alpha=1` out of 168 scanned. H-005 already killed the futures momentum signal. Do not trade.
- 90d expected P&L (1% risk, $100k): **-$300** (19 decisive × 1% × (0.3684 - 0.5) × ~1.5R ≈ -3.7R ≈ -$370).
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` — **set to 999 (hard disable)** until n_closed > 100. The class is too thin to gate meaningfully.
- Confidence (1-5): **2** (that it's noise — but n is too small to be confident in anything)

### UNKNOWN
- Real/noise verdict: **Data hygiene failure.** 1,411 scanned, 1,403 opened, 8 closed, 0 wins, 8 losses. WR=0%. This is not an asset class — it's a routing bug. Every trade in this bucket should be quarantined and the classifier fixed before any edge analysis is meaningful.
- 90d expected P&L (1% risk, $100k): **-$800** (8 × 1% × -1.0R × ~1.0 = -8R ≈ -$800).
- Gate change: Add `ASSET_CLASS_REQUIRED=True` to `production_scanner.py` — reject any pick that doesn't resolve to a known class. This is a one-line fix that eliminates 1,403 phantom trades.
- Confidence (1-5): **5** (that it's a bug)

### MEME
- Real/noise verdict: **Insufficient data.** n_closed=4. `passed_verified_alpha=1` out of 21. No PROVEN cells. Do not trade.
- 90d expected P&L (1% risk, $100k): **-$100** (4 × 1% × (0.25 - 0.5) × ~1.5R ≈ -1.5R ≈ -$150).
- Gate change: `SMART_PICKS_MIN_SCORE_MEME` — **set to 999 (hard disable)** until n_closed > 50. MEME is a noise generator at this sample size.
- Confidence (1-5): **2**

### ETF
- Real/noise verdict: **Negative edge, small n.** n_closed=7, WR=14.29%. No PROVEN cells. `passed_smart=293/333` (88%) — the Smart floor is not filtering ETF at all.
- 90d expected P&L (1% risk, $100k): **-$250** (7 × 1% × (0.1429 - 0.5) × ~1.5R ≈ -3.75R ≈ -$375).
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` — **raise to 80**. The 88% pass rate is the problem.
- Confidence (1-5): **3** (that it's noise)

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only, and only the `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell.** That is the only cell in the entire report that passes holdout, has n>100, has wr_z>6, and has a plausible (not absurd) PF. Expected 90d P&L at 1% risk on $100k: **+$16k to +$19k**. Before scaling, verify the 191 trades are not concentrated in <10 symbols — if they are, halve the size and add the concentration cap.

**Demote per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill):**

- **BOND** — confirmed negative cell (PF=0.053, holdout_pass=false). Mutate: flip direction on `bond_scanner` and re-test in shadow for 30d. If flipped WR < 45%, kill.
- **EQUITY** — PF=224 is an artifact, not an edge. Mutate: recompute `score_dec=S40` with strict point-in-time data and re-run. If PF drops below 2.0, the artifact is confirmed and the cell is killed.
- **FOREX** — `multi_asset_copytrader` is a single-source concentration risk. Mutate: cap to 3 trades/source/day and re-test. If WR stays < 48%, kill the source.
- **COMMODITY** — train/holdout PF flip (12.4 → 0.6) is a classic overfit. Mutate: require `MIN_HOLDOUT_PF=1.2` and re-test. If no cell passes, kill the class.
- **UNKNOWN** — not a class, a bug. Fix the classifier, don't mutate.
- **INDEX, FUTURES, MEME, ETF** — insufficient n. Shadow only, no capital.

**The single highest-leverage fix is not a gate constant — it's the funnel itself.** `opened ≈ scanned` in every class means the Smart floor is decorative. Fixing `SMART_PICKS_MIN_SCORE_*` to actually bind (target 10-25% pass rate, not 90%+) would cut trade volume by ~5x and would make every downstream metric in this report meaningful. Right now, 90% of what you're measuring is trades that should never have been opened.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### INDEX
- Real/noise verdict: Noise — n_closed=5, no proven cells, all metrics unusable.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n_closed=27, no proven cells, best_pf cells fail holdout and show negative expectancy.
- 90d expected P&L (1% risk, $100k): -$800 (negative edge, avoid).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 90
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — no proven cells, best_pf cells fail holdout and bonferroni; PF inflated by small train_n.
- 90d expected P&L (1% risk, $100k): $0 (no reliable edge).
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Marginally real on the three proven cells (n=190-191, WR_shrunk 72.5-72.9, PF 3.74, holdout passes, bonferroni passes); PF high but not impossible for alpha_engine source. No obvious single-symbol leakage flagged in data.
- 90d expected P&L (1% risk, $100k): $4,200 (assume 2411 closed trades scaled to ~190 high-conviction subset at 1% risk, 1.43% avg win, 0.5% slippage drag).
- Gate change: alpha_engine MIN_CONF = 0.78
- Confidence (1-5): 3

### EQUITY
- Real/noise verdict: Sample-noise / leakage — n=70, WR 98.57% (shrunk 87.78), PF 223 is physically impossible without single-symbol concentration or look-ahead; identical cells across three dims confirm data artifact.
- 90d expected P&L (1% risk, $100k): $0 (reject all cells).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 95
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — no proven cells, best_pf cells fail holdout, low n=27.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 88
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n_closed=7, no cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 90
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n_closed=19, no cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 92
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n_closed=8, WR 0%, no cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n_closed=4, no cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with multiple holdout-passing proven cells). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL (clear leakage recurrence). All other classes have zero usable edge.
