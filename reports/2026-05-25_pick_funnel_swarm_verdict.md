# Pick Funnel Swarm Verdict — 2026-09-14 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260914T041103Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` across every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) has never fired in 90 days. Every "edge" you're about to read about is *below* your own HC bar. That is a red flag on the gate, not a badge of quality on the picks.
2. **`opened` >> `passed_smart` in every class.** EQUITY: 4,559 opened vs 228 passed_smart. FOREX: 22,384 opened vs 22,754 passed_smart (opened > passed_smart — the funnel is not actually gating opens). The "passed_smart" counter is decorative; the scanner is opening almost everything it scans.
3. **`closed` << `opened`.** EQUITY 194/4,559 (4.3%), FOREX 1,394/22,384 (6.2%), COMMODITY 133/6,338 (2.1%). The WR numbers are computed on a tiny, non-random survivor subset. Any "edge" claim from these cells is conditional on "trades that happened to close in 90d," which is a selection bias, not a strategy.

With that framing:

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE.** The `fam=mean_reversion & score_dec=S40` cell shows WR=98.48%, PF=210, holdout PF=122.9. A PF of 210 on n=66 is not a strategy — it is a data artifact. Three specific tells: (i) `trust=UNK` on 100% of the cell, meaning the trust dimension is degenerate; (ii) `conf=C<0.60` — the *lowest* confidence band produces the *highest* WR, which is the signature of a look-ahead or exit-timing bug (e.g., mean-reversion trades being marked "win" on a touch of a limit that was set with future data, or a TP/SL inversion); (iii) `score_dec=S40` is the bottom decile of your own score — the scanner is telling you these are bad picks and they're winning 98% of the time. That is not an edge, that is a broken P&L attribution. Treat this cell as a **leakage recurrence** and quarantine it before it contaminates the registry. The 67.5% class-level WR on n=194 is also suspect for the same reason (only 4.3% of opens closed).
- **90d expected P&L (1% risk, $100k): $0 (do not deploy).** If you forced deployment on the 194 closed trades at 1% risk with avg_pnl +1.27%: 194 × $1,000 × 0.0127 ≈ **+$2,464 gross**, minus ~15 bps round-trip slippage on $194k notional ≈ −$291, minus borrow/financing on shorts ≈ −$150 → **~$2,000 net on a $100k book over 90 days (≈8% annualized)** — but this is on a 4% closed sample with a known leakage cell inside it. Realistic expectation: **$0 to negative** once the leakage is removed.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **65**, AND add a hard `trust != UNK` requirement in `quality_gates.py` for EQUITY. The `trust=UNK` cells are where every suspicious EQUITY number lives.
- **Confidence (1-5): 1**

---

### BOND
- **Real/noise verdict: NOISE, and actively negative.** n=23 closed, WR=21.7%, PF<1 implied. No PROVEN cells. This is a class where the scanner is opening 446 trades and closing 23 — the funnel is not functioning. The 21.7% WR is not "small sample noise," it is a *consistent* loss rate that says the BOND signal set has negative expectancy.
- **90d expected P&L (1% risk, $100k): −$1,500 to −$2,500.** 23 closed × $1,000 × (0.217×avg_win − 0.783×avg_loss). With typical bond R:R ~1:1, expectancy ≈ −0.57R per trade → 23 × −$570 ≈ **−$1,300**, plus slippage on illiquid bond proxies → **~−$1,800**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — set to **999 (effectively disable)** until a BOND-specific edge is re-derived. Do not mutate-and-keep; mutate-and-park.
- **Confidence (1-5): 4** (confident it's negative)

---

### COMMODITY
- **Real/noise verdict: NOISE.** n=132 closed, WR=44.7%, no PROVEN cells. The best cell (`rr=RR>=2.0 & score_dec=S50`, n=21, WR=76.2%, PF=5.6) fails Bonferroni and has holdout_n=11 — that is not evidence, that is a coin flip that landed heads 16 times. Note the registry already killed H-001 (COT leakage) and H-036 (inventory direction) for this class; the surviving "edge" here is the residue of a class that has been repeatedly falsified. Do not re-derive.
- **90d expected P&L (1% risk, $100k): −$800 to −$1,200.** 132 closed × $1,000 × (0.447×1.0 − 0.553×1.0) ≈ −$1,060, plus commodity slippage (wider spreads) → **~−$1,300**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70**, and add a `rr >= 1.5` hard floor in `quality_gates.py`. The only cell that even sniffed positive was the RR>=2.0 bucket; the class is being diluted by low-RR noise.
- **Confidence (1-5): 3**

---

### FOREX
- **Real/noise verdict: WEAK-REAL but fragile.** The `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell (n=139, WR=66.2%, shrunk 64.2%, PF=2.72, holdout PF=1.56, Bonferroni pass) is the *only* cell in the entire report that survives all four tests (n≥100, shrunk WR>55%, PF>1.5, holdout pass, Bonferroni pass). That is genuinely notable. **However:** (i) holdout PF drops from 3.19 → 1.56, a 51% degradation — the edge is decaying; (ii) `trust=UNK` again — the trust dimension is not discriminating; (iii) the class-level WR is 46.3% on n=605, meaning the *aggregate* is a coin flip and the edge is concentrated in one narrow cell. The `dir=LONG` variant (n=46, PF=4.6) fails Bonferroni — do not chase it. **This is the one class where a real, if modest, edge exists.**
- **90d expected P&L (1% risk, $100k): +$3,000 to +$5,000.** Deploy only on the proven cell (n=139): 139 × $1,000 × (0.662×0.27 − 0.338×0.27) ≈ 139 × $1,000 × 0.0874 ≈ **+$12,150 gross**. Apply 40% haircut for holdout degradation and 15 bps FX slippage → **~+$6,500**. If you size at 0.5% risk (more honest given holdout decay): **~+$3,200**. Call it **+$3,000 to +$5,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **60**, AND add a `fam == "mean_reversion"` allowlist for FOREX in `quality_gates.py`. The class is 22,754 passed_smart out of 23,778 scanned (95.7% pass rate) — the gate is not gating. Tighten to the one family that works.
- **Confidence (1-5): 3**

---

### CRYPTO
- **Real/noise verdict: LIKELY REAL, but the cell is suspiciously clean.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` (n=214, WR=76.6%, shrunk 74.4%, PF=4.05, holdout PF=6.59, Bonferroni pass). This is the strongest cell in the report by every metric. **But:** (i) holdout PF (6.59) is *higher* than train PF (3.17) — that is unusual and warrants a leakage check on the holdout split (are holdout trades genuinely out-of-sample, or is the split by row rather than by time?); (ii) `trust=UNK` again; (iii) `score_dec=S50` is the *median* decile — the edge is not in your top-scored picks, it's in the middle, which means your scoring function is not aligned with the edge; (iv) the cell is defined by `source=alpha_engine` — check whether this is a single-strategy concentration. The class-level WR (47.3% on n=2,473) is a coin flip; the edge is one narrow cell. **Verdict: real enough to deploy small, but verify the holdout split is temporal before scaling.**
- **90d expected P&L (1% risk, $100k): +$8,000 to +$14,000.** 214 × $1,000 × (0.766×1.45 − 0.234×1.45) ≈ 214 × $1,000 × 0.771 ≈ **+$165,000 gross** — but that assumes avg_pnl_pct=1.45% is realized on every trade, which is optimistic. Apply 60% haircut for holdout optimism + crypto slippage (20-30 bps) + funding costs → **~+$10,000**. At 0.5% risk: **~+$5,000**. Call it **+$8,000 to +$14,000** at 1% risk.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise to **70**, AND add `source == "alpha_engine"` as a required dimension for CRYPTO in `quality_gates.py`. The 3,154 passed_smart out of 12,368 scanned (25.5%) is too loose; the edge is in one source.
- **Confidence (1-5): 3** (would be 4 if holdout split is confirmed temporal)

---

### ETF
- **Real/noise verdict: NOISE.** n=7 closed, WR=14.3%. Not enough data to say anything. Do not deploy.
- **90d expected P&L (1% risk, $100k): −$500 to −$700.** 7 × $1,000 × (0.143 − 0.857) ≈ −$714.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — set to **999 (disable)** until n≥50 closed.
- **Confidence (1-5): 4**

---

### UNKNOWN
- **Real/noise verdict: NOISE / DATA HYGIENE FAILURE.** n=9 closed, WR=0%. The fact that 1,447 instruments are classified as UNKNOWN and 1,438 were opened is a taxonomy bug, not a strategy. Fix the classifier before this class exists.
- **90d expected P&L (1% risk, $100k): −$900.** 9 × $1,000 × (0 − 1) = −$9,000 gross, but n=9 so call it **−$900** at realistic sizing.
- **Gate change:** Add `asset_class == "UNKNOWN"` → **hard reject** in `quality_gates.py`. Do not open trades on unclassified instruments.
- **Confidence (1-5): 5**

---

### INDEX
- **Real/noise verdict: NOISE.** n=4 closed, WR=0%. Same as UNKNOWN — not enough data, and what exists is negative.
- **90d expected P&L (1% risk, $100k): −$400.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — set to **999 (disable)** until n≥50.
- **Confidence (1-5): 4**

---

### FUTURES
- **Real/noise verdict: NOISE.** n=18 closed, WR=38.9%, no PROVEN cells. Registry already killed H-005 (futures momentum anti-signal). Do not re-derive.
- **90d expected P&L (1% risk, $100k): −$400.** 18 × $1,000 × (0.389 − 0.611) ≈ −$400.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **75**, and require `rr >= 1.5`.
- **Confidence (1-5): 3**

---

### MEME
- **Real/noise verdict: NOISE.** n=4 closed, WR=25%. Not enough data.
- **90d expected P&L (1% risk, $100k): −$500.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — set to **999 (disable)** until n≥50.
- **Confidence (1-5): 4**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO (small) and FOREX (smaller).**
- CRYPTO: deploy the `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell at **0.5% risk** (not 1%) until the holdout split is confirmed temporal. Expected 90d: **+$5,000 to +$7,000** on $100k.
- FOREX: deploy the `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell at **0.5% risk**. Expected 90d: **+$3,000 to +$5,000**.
- Combined realistic 90d on $100k: **+$8,000 to +$12,000 (≈8-12% annualized)** — modest, but real, and it's the only real edge in the report.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **BOND** — mutate the signal set (try credit-spread momentum, not rate momentum) before killing. Current state is negative expectancy.
- **COMMODITY** — mutate the RR floor (raise to 1.5) and re-test; if still negative after 90d, kill. Two prior hypotheses already falsified.
- **EQUITY** — **quarantine, do not mutate.** The 98.5% WR cell is a leakage recurrence. Fix the P&L attribution bug first, then re-evaluate. Do not deploy real money on EQUITY until the leakage is explained.
- **ETF, INDEX, MEME, UNKNOWN, FUTURES** — park (disable gates) until n≥50 closed. These are not strategies, they are data hygiene problems.

**The single most important finding:** `passed_high_conviction = 0` across all 10 classes over 90 days. Your HC gate is either misconfigured (thresholds unreachable given the score distribution) or the scanner never produces picks that meet it. Either way, the HC gate is not doing its job. Before adding any new edge logic, **instrument the HC gate to log the max score/conf/trust observed per class per day** — if the max never approaches 80/0.75/60, the thresholds are wrong; if it does and HC still doesn't fire, the gate logic is wrong. This is a higher-leverage fix than any single class tuning.

**Brutal honesty:** 7 of 10 classes have no edge. 2 have a weak edge. 1 (EQUITY) has a leakage artifact masquerading as the best edge in the report. The funnel is opening 95%+ of what it scans in most classes, closing <7% of opens, and reporting WR on the survivor subset. The "edge" you're seeing is mostly selection bias plus one genuine FOREX/CRYPTO cell. Do not scale the system; scale the two cells.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — PF=210 and 98% WR on n=66 mean_reversion trades is statistically impossible without single-symbol concentration or data error; rejected per protocol.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n=23 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf cells fail bonferroni and n=21 too small.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Real — n=139-146, WR_shrunk 64%, PF 2.6-2.7, holdout passes, bonferroni true; only credible edge in dataset.
- 90d expected P&L (1% risk, $100k): $2,800 (assume 1% risk/trade on 146 trades, 0.26% avg edge after slippage, 0.3% commission/slippage drag).
- Gate change: HC_FILTER_MIN_CONF = 0.78
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Noise/leakage — PF=4+ on n=213-214 with 77% WR is suspiciously high; matches flagged ml/consensus pattern and likely data leakage.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 75
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n=7 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n=9 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n=4 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n=18 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n=4 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up FOREX today (only class with statistically credible, non-rejected edge). Demote CRYPTO and EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate filters before any further capital allocation; their cells are leakage artifacts). All other classes remain at zero allocation.
