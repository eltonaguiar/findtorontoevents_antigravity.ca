# Pick Funnel Swarm Verdict — 2026-09-16 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260916T041018Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) has never fired in 90 days. Every "edge" you're about to read about is *downstream of a gate that is effectively closed*. The funnel is not filtering — it's just recording.
2. **`opened` ≈ `scanned` in every class** (e.g. FOREX 22,621/24,041 = 94%). The "Smart" gate is not gating. It's a rubber stamp. `passed_smart` for FOREX is 23,028/24,041 = 96%. That is not a filter, that is a pass-through.
3. **`closed` is a tiny fraction of `opened`** (CRYPTO 2,519/9,934 = 25%; FOREX 1,420/22,621 = 6%; EQUITY 200/4,686 = 4%). The WR numbers are computed on the *survivors*, not the population. This is the single biggest source of bias in the whole report and it is not corrected anywhere.

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE.** The `fam=mean_reversion & score_dec=S40` cell shows WR=98.55%, PF=218.4, n=69. A PF of 218 is not an edge — it is a data artifact. Three red flags: (i) `trust=UNK` on 100% of the cell, meaning trust scoring never ran; (ii) `conf=C<0.60` — the *lowest* confidence band produces the *highest* WR, which is the signature of a label leak (the "win" flag is being set by something correlated with the entry, not the exit); (iii) `score_dec=S40` is a *low* score decile. A 98.55% WR on low-confidence, low-score, unknown-trust mean-reversion trades is not a strategy — it's a bug. The `holdout_pf=99.0` on n=37 confirms the leak is stable across the split, which means it's structural, not random. **Do not trade this. Quarantine the EQUITY mean_reversion family and audit the win/loss labeling pipeline before anything else.**
- **90d expected P&L (1% risk, $100k): $0.** Not because the edge is small — because the number is not real. If you sized this at 1% risk you would be sizing a leak.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **65**, AND add a hard `trust != UNK` requirement in `quality_gates.py` before any EQUITY pick is allowed to open. The UNK-trust population is where the leak lives.
- **Confidence (1-5): 1**

### BOND
- **Real/noise verdict: NOISE.** n=24 closed, WR=25%, PF not even reported (no cell clears n>=20 with positive edge). 503 scanned → 8 passed_smart → 0 verified_alpha → 0 HC → 479 opened. The funnel is inverted: 95% of scanned bonds open despite the Smart gate. There is no edge here. There is barely a sample.
- **90d expected P&L (1% risk, $100k): -$1,800** (24 trades × 1% × -0.75R avg, rough). Negative. Do not trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **70** and add a minimum-liquidity filter. Better: **disable BOND opening entirely** until n_closed >= 100. The class is too thin to learn from.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict: NOISE (and a known-falsified recurrence risk).** The best cell is `rr=RR>=2.0 & score_dec=S50` with n=21, WR_shrunk=63.4%, PF=5.62, **bonferroni_pass=false**. n=21 is below the n>=20 threshold you set and the Bonferroni correction explicitly fails. More importantly: this is the *same shape* as [H-001] (COT positioning, look-ahead leakage, 85% CT=F cotton concentration). The `trust=UNK` tag on the top cell is the same fingerprint. **Flag this as a potential H-001 leakage recurrence, not a new edge.** The 3,916/6,487 passed_smart rate (60%) is also implausibly high for a real filter.
- **90d expected P&L (1% risk, $100k): $0.** n=21 with Bonferroni fail is not a tradeable sample.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70**, and add a `source != alpha_engine OR trust != UNK` clause. The alpha_engine/UNK combination is the H-001 fingerprint.
- **Confidence (1-5): 1**

### FOREX
- **Real/noise verdict: NOISE, with a specific leakage signature.** The top cell `conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG` has n=47, WR_shrunk=65.7%, PF=4.34, **bonferroni_pass=false**. The `trust=UNK` variant is identical (same n, same WR) — meaning trust scoring is not running on FOREX at all. The `score_dec=S50` variant is also identical — meaning score decile is not discriminating. Three "different" cells with identical stats is the signature of a single underlying population being sliced by dimensions that carry no information. **This is not an edge; it is one cluster of 47 trades being re-labeled.** The 23,028/24,041 passed_smart rate (96%) confirms the Smart gate is not filtering FOREX.
- **90d expected P&L (1% risk, $100k): $0.** n=47, Bonferroni fail, and the "edge" is a re-labeling artifact.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current to **70**, AND fix the trust-scoring pipeline so `trust=UNK` is not the modal value. Until trust runs, no FOREX cell is interpretable.
- **Confidence (1-5): 1**

### CRYPTO
- **Real/noise verdict: THE ONLY CELL WORTH TAKING SERIOUSLY — but still suspect.** `conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine`: n=216, WR=77.3%, WR_shrunk=75.0%, PF=4.10, train_pf=4.08 (n=173), holdout_pf=4.19 (n=43), **holdout_pass=true, bonferroni_pass=true, wr_z=8.03**. This is the only cell in the entire report that clears Bonferroni. That matters. But: (i) `trust=UNK` on the sibling cell means trust scoring is not running here either; (ii) PF=4.10 on a 77% WR with avg_pnl=1.46% implies avg_loss ≈ 0.36% — that is a *very* tight stop, and tight stops on crypto are the classic way to manufacture high WR with hidden tail risk; (iii) the cell is `dir=LONG` only — in a 90-day window that was likely a crypto bull leg, this is beta, not alpha. **Verdict: real enough to paper-trade, not real enough to size at 1% yet.** The Bonferroni pass is the strongest signal in the report; the UNK-trust and LONG-only concentration are the strongest cautions.
- **90d expected P&L (1% risk, $100k): +$3,200** (216 trades × 1% × 0.148R avg, using avg_pnl=1.46% and assuming 1R≈1% notional). Range: **+$1,800 to +$4,500** depending on slippage. See assumptions below.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower to 55** (from current, which is clearly above the S50 decile that carries the edge), AND add `conf >= 0.75` as a hard pre-filter in `quality_gates.py` so the C0.75-0.80 band is not diluted by lower-confidence picks. Do **not** touch `hc_filter.js` yet — the HC gate has never fired and lowering it now would open the floodgates on unvalidated classes.
- **Confidence (1-5): 3**

### ETF
- **Real/noise verdict: NOISE.** n=7 closed, WR=14.3%. 332 scanned → 292 passed_smart (88%) → 0 HC → 325 opened. No edge, no sample.
- **90d expected P&L (1% risk, $100k): -$600** (7 trades × 1% × -0.86R). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **75** or disable opening until n_closed >= 50.
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict: NOISE.** n=4 closed, WR=0%. 1,573 scanned → 1,418 passed_smart (90%) → 1,566 opened → 7 closed. The funnel is a straight pipe.
- **90d expected P&L (1% risk, $100k): -$400** (4 trades × 1% × -1.0R). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **75** or disable.
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict: NOISE, and a data-hygiene failure.** n=9 closed, WR=0%. 1,423 scanned → 187 passed_smart → 1,414 opened. The fact that 1,414 "UNKNOWN" class picks opened is itself the bug — the classifier is failing on ~6% of the universe and those picks are being traded anyway.
- **90d expected P&L (1% risk, $100k): -$900** (9 trades × 1% × -1.0R). Negative.
- **Gate change:** Add a hard `asset_class != UNKNOWN` requirement in `quality_gates.py` before any pick can open. This is a one-line fix with the highest hygiene ROI in the report.
- **Confidence (1-5): 1**

### FUTURES
- **Real/noise verdict: NOISE.** n=18 closed, WR=38.9%. [H-005] already falsified the futures momentum inversion. No cell clears n>=20.
- **90d expected P&L (1% risk, $100k): -$400** (18 trades × 1% × -0.22R). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **70** or disable.
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict: NOISE.** n=4 closed, WR=25%. 21 scanned. Not a class, a rounding error.
- **90d expected P&L (1% risk, $100k): -$300** (4 trades × 1% × -0.75R). Negative.
- **Gate change:** Disable MEME opening entirely until n_closed >= 50.
- **Confidence (1-5): 1**

---

## Sizing / slippage assumptions (for the CRYPTO number)

- $100k notional account, 1% risk per trade = $1,000 risk per trade.
- 1R = 1% of notional (matches the avg_pnl_pct=1.46% scale in the cell).
- 216 trades over 90d = ~2.4 trades/day. At 1% risk each, peak concurrent exposure could exceed account if not capped — assume max 5 concurrent, so effective sizing is 0.2% per trade on average. **This halves the P&L estimate to ~+$1,600.**
- Slippage: 8 bps round-trip on crypto majors, 25 bps on alts. Blended 15 bps × 216 trades × $100k notional = **-$3,240**. This is the number that kills the edge.
- Fees: 10 bps taker × 2 sides × 216 = **-$4,320**.
- **Net expected P&L after costs: approximately -$6,000 to +$1,000.** The edge is real on paper and roughly break-even after realistic crypto costs. This is the honest number.

For every other class, the expected P&L is negative before costs and more negative after.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: NONE.** The only cell that clears Bonferroni (CRYPTO `conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine`) is roughly break-even after realistic crypto slippage and fees, is LONG-only in a likely-bull 90d window, and sits on a `trust=UNK` population where trust scoring never ran. **Paper-trade it for 30 more days with trust scoring fixed, then re-evaluate.** Do not put real money behind it yet.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **EQUITY mean_reversion family** — demote immediately. The 98.55% WR / PF=218 cell is a labeling leak, not a strategy. Mutate the win/loss labeling pipeline before any further EQUITY work. This is the highest-priority fix in the report.
2. **COMMODITY alpha_engine/UNK cells** — demote and flag as [H-001] leakage recurrence. The `rr>=2.0 & score_dec=S50 & trust=UNK` fingerprint matches the falsified COT hypothesis. Mutate the source/trust axis before re-testing.
3. **FOREX** — demote the entire class to observation-only. The Smart gate passes 96% of picks; trust scoring is not running; the "top edge" is one 47-trade cluster re-labeled three ways. Mutate the trust-scoring pipeline, then re-run.
4. **BOND, ETF, INDEX, UNKNOWN, FUTURES, MEME** — disable opening. These classes have n_closed < 25 and negative WR. They are not strategies; they are noise being traded.

**The single highest-ROI fix in the entire report is not a gate threshold — it is the `trust=UNK` population.** It appears in the top cell of EQUITY, COMMODITY, FOREX, and CRYPTO. Trust scoring is not running on the majority of the universe, and every "edge" in this report is downstream of that failure. Fix trust scoring first, then re-run the 90-day funnel. The gate changes above are secondary to that.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: noise (extreme PF 218 and 98% WR on n=69 screams single-symbol leakage or data error; shrunk WR still implausibly high)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 60
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise (no proven cells at all; tiny n=24)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: noise (no proven cells; best_pf cells fail Bonferroni and n too small)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise (no proven cells; best_pf cells fail Bonferroni; high PF suspicious but unproven)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: noise (PF 4.1 on n=217 looks like alpha_engine concentration or leakage despite holdout pass; real money would degrade fast)
- 90d expected P&L (1% risk, $100k): $0 (edge not reliable enough to size)
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 4

### ETF
- Real/noise verdict: noise (no proven cells; n=7)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise (no proven cells; n=4, 0% WR)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise (no proven cells; n=9)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 70
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise (no proven cells; n=18)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 65
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise (no proven cells; n=4)
- 90d expected P&L (1% risk, $100k): $0 (no usable edge)
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up: none (zero classes have trustworthy, non-leaky edges worth real capital).  
Demote: all classes per MUTATION_THREE_AXIS_PROTOCOL.md — start with EQUITY and CRYPTO (highest apparent metrics but highest leakage risk), then COMMODITY/FOREX. Tighten every gate first; current funnel is mostly noise.
