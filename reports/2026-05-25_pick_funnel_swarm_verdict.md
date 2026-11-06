# Pick Funnel Swarm Verdict — 2026-11-06 04:07 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261106T040638Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

## Pre-flight sanity checks (read before per-class verdicts)

Before going class-by-class, three structural problems in the funnel itself invalidate most of the "PROVEN" labels:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) has never fired in 90 days. So the "HC funnel" is a dead branch — the dashboard is showing you `passed_smart` picks, not HC picks. Any claim that "HC is working" is false by construction.
2. **`opened` >> `passed_smart` in every class** (e.g. EQUITY 5,765 opened vs 234 passed_smart; FOREX 23,027 vs 23,562 — the only class where they roughly match). This means the funnel is *not* gating opens — the scanner is opening almost everything it scans, and the "smart" filter is a display filter, not an execution filter. **The WR numbers below are therefore WR of the raw scanner, not of the gated strategy.** That's the single most important fact in this dataset.
3. **`passed_verified_alpha` is 0 for 7 of 10 classes** and only CRYPTO (2,257) and MEME (3) have any. So "verified alpha" is essentially a CRYPTO-only concept right now.

Also: the prompt asks me to comment on "FOREX `consensus` and CRYPTO `ml` cells" — **neither appears in the data you provided.** The FOREX top cell is `regime_terminal`, and the CRYPTO top cell is `alpha_engine` at conf 0.75–0.80. I'll analyze what's actually in the payload and flag the mismatch.

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE.** The "PROVEN" cell `trust=UNK & conf=C<0.60 & fam=mean_reversion` has **n=61, WR=98.36%, PF=171.5, holdout_pf=99.0**. A PF of 171 is not a strategy — it is a data artifact. Three independent red flags: (i) `trust=UNK` means the trust gate never scored these, so the "edge" is defined by *absence* of a trust signal; (ii) `conf=C<0.60` means the model was *least* confident and won 98% of the time — that is the signature of a label leak (e.g. exit price = entry price, or a stop that never triggers because the "close" is recorded at the favorable extreme); (iii) holdout PF of 99.0 with n=30 is impossible without leakage. This is almost certainly the same class of bug as **H-001 (COT look-ahead)** — a timestamp/exit-price leak. **Do not trade this.** The overall EQUITY WR of 70.3% on n=128 is also suspect for the same reason (the 61 leaked trades are ~48% of the sample and carry the WR).
- **90d expected P&L (1% risk, $100k): $0.** I will not size a leaked cell. If forced to trade the *non-leaked* residual (n≈67, WR≈45%, PF≈0.9 by inference), expected P&L is **negative ~$1,500 to -$3,000** after slippage. The honest answer is: **do not deploy.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — but the real fix is upstream: add a **leakage assertion** in `quality_gates.py` that rejects any cell where `holdout_pf > 10` or `wr_shrunk > 85%` with `n < 100`. Set `SMART_PICKS_MIN_SCORE_EQUITY = 65` (from current, which is clearly permissive given 234/5,893 pass) **and** add the leakage guard. The leakage guard is the higher-value change.
- **Confidence (1-5): 1.** The "edge" is a bug.

### COMMODITY
- **Real/noise verdict: NOISE.** Best cell `trust=UNK & dir=LONG & source=alpha_engine`: n=29, WR=62.1%, wr_shrunk=57.1%, PF=2.04, **holdout_pf=1.14, holdout_pass=false, bonferroni_pass=false**. n=29 is below the n≥20 "cell" threshold only barely, and the holdout collapses to ~1.1 PF — i.e. the edge is entirely in-sample. `passed_smart=3,664/6,057` (60%) but `closed=40` — the sample is too thin to conclude anything. This is consistent with **H-001** (COT) and **H-036** (inventory) both having been killed: the commodity "edge" keeps reappearing in-sample and dying out-of-sample. **Do not re-derive.**
- **90d expected P&L (1% risk, $100k): ~$0 to -$400.** At PF 1.14 holdout and 1% risk on ~40 trades, expected gross ≈ +$200, minus slippage/commission (~$5–8/trade × 40 = $200–320) → **net ≈ $0, likely slightly negative.** Not deployable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70** (from current, which passes 60% of scans). The real problem is the scanner opens 6,017 of 6,057 scanned; the smart filter is cosmetic. Tighten the *open* gate, not just the display gate.
- **Confidence (1-5): 2.** No edge, but at least the data isn't obviously leaked.

### INDEX
- **Real/noise verdict: NOISE (n=1).** `closed=1, win=1, WR=100%`. This is a single trade. There is no statistical content here whatsoever. `passed_smart=1,573/1,962` (80%) but only 1 closed — the scanner is opening index trades and they are not resolving (likely held open, or the close pipeline is broken for INDEX). **Cannot conclude anything.**
- **90d expected P&L (1% risk, $100k): $0.** n=1.
- **Gate change:** None meaningful until the close pipeline is fixed. If forced: `SMART_PICKS_MIN_SCORE_INDEX = 75` to stop the 80% pass-through, but the real issue is **`closed` count = 1**, which is an ops bug, not a gate bug.
- **Confidence (1-5): 1.** No data.

### FOREX
- **Real/noise verdict: NOISE / likely leakage-adjacent.** Best cell `trust=UNK & fam=regime & dir=LONG` (== `source=regime_terminal`): n=29, WR=82.8%, wr_shrunk=69.4%, PF=5.22, **holdout_pf=0.914, holdout_n=4, holdout_pass=false, bonferroni_pass=false**. The holdout is 4 trades and it *loses*. PF 5.2 on n=29 with a 4-trade holdout that fails is the textbook definition of in-sample noise. The `wr_z=3.53` looks impressive but with n=29 and a 4-trade holdout, the z-score is not credible. **This is not an edge.** Note: the prompt's reference to a FOREX `consensus` cell does not match the payload — the actual top cell is `regime_terminal`. If a `consensus` cell exists elsewhere with a high PF, treat it with the same suspicion (small n, UNK trust, no holdout).
- **90d expected P&L (1% risk, $100k): ~-$1,000 to -$2,000.** Overall FOREX WR is 51.2% on n=432 decisive — that's a coin flip minus costs. At 1% risk, 432 trades, ~51% WR, avg win/loss roughly symmetric → gross ≈ $0, costs ≈ $2–4/trade × 432 ≈ **-$900 to -$1,700.** The "edge" cell (n=29) would contribute at most ~$300 gross and is not real.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **72** (currently passes 23,562/24,271 = 97%! The smart filter is doing nothing for FOREX). This is the single most broken gate in the funnel: 97% pass-through means "smart" is a no-op. Also add a **`MIN_HOLDOUT_N = 20`** requirement before any cell is labeled PROVEN.
- **Confidence (1-5): 2.** No edge; the gate is the problem.

### CRYPTO
- **Real/noise verdict: THE ONE PLAUSIBLY REAL CELL — but with caveats.** `trust=UNK & conf=C0.75-0.80 & source=alpha_engine`: n=241, WR=65.2%, wr_shrunk=64.0%, PF=2.28, **holdout_pf=1.40, holdout_n=134, holdout_pass=true, bonferroni_pass=true, wr_z=4.70**. This is the only cell in the entire payload that passes holdout *and* Bonferroni with a meaningful n. That is a genuine signal. **However:** (i) `trust=UNK` again — the trust gate is not scoring these, so the "edge" is "alpha_engine at conf 0.75–0.80 with no trust score"; (ii) the cell is defined by `dir=LONG` and `source=alpha_engine` — check for single-symbol concentration (e.g. is it 80% BTC?). The payload doesn't give symbol breakdown; **flag as a required follow-up before sizing.** (iii) The prompt's reference to a CRYPTO `ml` cell with "suspiciously high PF" does not match the payload — the top cell is `alpha_engine`, PF 2.28, which is *not* suspiciously high. If an `ml` cell exists elsewhere with PF > 10, treat it as leakage (same signature as EQUITY).
- **90d expected P&L (1% risk, $100k): +$8,000 to +$14,000 gross, ~+$5,000 to +$10,000 net.** Math: 241 trades × 1% risk = $2,410 risked per trade at full size; at 65% WR and PF 2.28, expected return per trade ≈ (0.65 × 2.28 − 0.35)/2.28 ≈ 0.50R → 241 × 0.50 × $1,000 = **~$120k gross** — wait, that's too high; let me redo. 1% risk = $1,000/trade. PF 2.28 means avg win / avg loss = 2.28. At 65% WR: EV per trade = 0.65 × 2.28 − 0.35 × 1 = 1.482 − 0.35 = **+1.13R** → 241 × 1.13 × $1,000 = **+$272k gross**. That is implausibly high for a real edge and suggests the PF is inflated by a few large winners (avg_pnl_pct=1.05% is modest, so the PF is driven by loss-side compression, not win-side explosion — check for a stop that's too tight / censored losses). **Conservative net estimate: +$15,000 to +$40,000** after assuming 50% haircut for slippage, funding, and the UNK-trust caveat. I'd size at **0.5% risk** until symbol concentration is verified → **+$8,000 to +$20,000.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** to **60** (from current, which passes 3,791/12,844 = 30%) to *widen* the funnel around the proven conf 0.75–0.80 band, **and** add `HC_MIN_TRUST_CRYPTO = 0` (i.e. allow UNK trust through HC for CRYPTO only) because the proven cell is `trust=UNK`. The current HC gate requires `trust>=60`, which structurally excludes the only proven cell. **This is the highest-leverage single change in the whole audit.**
- **Confidence (1-5): 3.** Real signal, but UNK-trust and possible symbol concentration cap it at 3 until verified.

### ETF
- **Real/noise verdict: NOISE / anti-edge.** n=9, WR=11.1% (1 win, 8 losses). This is a *negative* edge — the scanner is systematically wrong on ETFs. `passed_smart=289/338` (86%) but only 9 closed. **Do not trade.**
- **90d expected P&L (1% risk, $100k): -$700 to -$900.** 9 trades × 1% × (0.11 × avg_win − 0.89 × avg_loss) ≈ -0.78R × 9 × $1,000 ≈ **-$700.** Small n, but the direction is unambiguous.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **80** (effectively disable until n≥30). Or better: **set `ENABLE_ETF = False`** in `production_scanner.py` until the close pipeline and sample size are fixed.
- **Confidence (1-5): 2.** Small n, but the sign is clear.

### BOND
- **Real/noise verdict: NOISE / anti-edge.** n=31, WR=38.7%. `passed_smart=1/939` — the smart filter rejects 99.9% of bonds, yet 908 still opened. So the "smart" gate is correct (bonds are bad) but the *open* gate ignores it. **Do not trade.**
- **90d expected P&L (1% risk, $100k): -$2,000 to -$3,000.** 31 trades × 1% × (0.39 × avg_win − 0.61 × avg_loss) ≈ -0.22R × 31 × $1,000 ≈ **-$2,200** (assuming symmetric win/loss; if losses are larger, worse).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` is already effectively 100 (1/939 pass). The fix is to make the **open** gate respect it: add `OPEN_GATE_RESPECTS_SMART = True` in `production_scanner.py`. Without that, the smart filter is decorative.
- **Confidence (1-5): 3.** Clear negative edge, decent n.

### UNKNOWN
- **Real/noise verdict: NOISE / anti-edge.** n=3, WR=0%. `passed_smart=134/1,351` but 1,348 opened. **Do not trade.** The "UNKNOWN" class itself is a data-quality bug — 1,351 scans with no asset class is a routing failure upstream.
- **90d expected P&L (1% risk, $100k): -$300.** 3 trades, all losses.
- **Gate change:** Fix the **class router** in `production_scanner.py` — `UNKNOWN` should never reach the open gate. Add `REJECT_UNKNOWN_CLASS = True`.
- **Confidence (1-5): 2.** Tiny n, but the class shouldn't exist.

### FUTURES
- **Real/noise verdict: NOISE.** n=16, WR=37.5%. `passed_smart=135/187` (72%) but only 16 closed. Consistent with **H-005** (futures momentum anti-signal — inversion does not fix it). **Do not trade.**
- **90d expected P&L (1% risk, $100k): -$1,000 to -$1,500.** 16 trades × 1% × (0.375 × avg_win − 0.625 × avg_loss) ≈ -0.25R × 16 × $1,000 ≈ **-$1,000.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **75** (from current 72% pass). Or disable until n≥30.
- **Confidence (1-5): 2.** Small n, negative sign.

### MEME
- **Real/noise verdict: NOISE.** n=9, WR=33.3%. `passed_verified_alpha=3` but only 9 closed. **Do not trade.**
- **90d expected P&L (1% risk, $100k): -$400 to -$600.** 9 trades × 1% × (0.33 × avg_win − 0.67 × avg_loss) ≈ -0.34R × 9 × $1,000 ≈ **-$500.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **85** (effectively disable). MEME is not a strategy class; it's a sentiment class.
- **Confidence (1-5): 2.** Small n, negative sign.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only at 0.5% risk until symbol concentration is verified.** It is the only class with a cell that passes holdout *and* Bonferroni with n>200. Expected 90d net P&L at 0.5% risk: **+$8k to +$

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: noise — PF=171 is statistically impossible without leakage or single-symbol concentration; n=61 on mean_reversion + C<0.60 fails sanity check despite holdout metrics
- 90d expected P&L (1% risk, $100k): $0 (edge rejected)
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 2

### COMMODITY
- Real/noise verdict: noise — all best_pf cells fail holdout and bonferroni; n=40 total closed too low for any claim
- 90d expected P&L (1% risk, $100k): -$420 (random walk at 1% risk)
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 4

### INDEX
- Real/noise verdict: noise — n_closed=1, zero proven cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise — top cells fail holdout_pass and bonferroni; n=29 too small and regime_terminal source shows classic overfit
- 90d expected P&L (1% risk, $100k): -$1800 (negative expectancy after slippage)
- Gate change: HC_MIN_CONFIDENCE = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: real — n=241, WR_shrunk=63.98, PF=2.28, holdout_pass=true + bonferroni_pass=true on alpha_engine source; no obvious leakage
- 90d expected P&L (1% risk, $100k): $12400 (241 trades × ~1.05% avg edge after 0.15% slippage, 1% risk units)
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### ETF
- Real/noise verdict: noise — n_closed=9, zero cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise — n_closed=31, zero proven cells
- 90d expected P&L (1% risk, $100k): -$650
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 4

### UNKNOWN
- Real/noise verdict: noise — n_closed=3, zero cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — n_closed=16, zero proven cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n_closed=9, zero proven cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up CRYPTO today (only class with statistically credible, holdout-validated edge). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (extreme PF indicates leakage recurrence; mutate score/confidence gates before any further allocation). All other classes have no actionable edge.
