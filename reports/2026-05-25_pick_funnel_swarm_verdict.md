# Pick Funnel Swarm Verdict — 2026-10-12 04:19 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261012T041901Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three system-wide observations that shape everything below:

1. **The funnel is broken at the top.** `passed_high_conviction = 0` for every single class. The HC gate (`score>=80, conf>=0.75, trust>=60`) is not firing on anything. Either the gate is mis-wired, or the scoring pipeline never produces a pick that clears all three thresholds simultaneously. Either way, the "HIGH CONVICTION" badge on the dashboard is currently decorative.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1908) and FOREX (3) produce any. The verified-alpha stage is effectively a CRYPTO-only filter.
3. **`opened` ≈ `scanned` for most classes** (COMMODITY 6104/6175, FOREX 22729/24111, EQUITY 5666/5816). The "smart picks" gate is not actually gating opens — it's a label, not a filter. This is the single biggest structural problem in the funnel.

---

### COMMODITY
- **Real/noise verdict:** No PROVEN cell. Best cell (`rr>=2.0 & LONG & alpha_engine`, n=23, WR_shrunk 65.1%, PF 6.97) **fails Bonferroni** and has only 23 trades. The 78% raw WR on n=23 with a 6.97 PF is exactly the shape of the falsified H-001 COT leakage pattern (85% cotton concentration, WR collapsed to 30% after dedup). **Assume this is a leakage recurrence until proven otherwise** — check symbol concentration and timestamp integrity before believing it. Class-level WR 57.75% on n=71 is not distinguishable from noise.
- **90d expected P&L (1% risk, $100k):** ~$0 to +$400. With 71 closed trades at 1% risk ($1k/trade) and 57.75% WR at ~1.5:1 avg R:R, gross ≈ +$1,150, minus ~$700 in slippage/commission on commodity CFDs/futures. Net ≈ **+$400**, well inside noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise from current value to **75** (or whatever forces `passed_smart` from 3656 → <500). The 59% pass rate is not a gate.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** The `mean_reversion & S40` cell (n=65, WR 98.46%, PF 218) is **almost certainly leakage or a data artifact**. A 98% WR with PF 218 on equities is not a real edge — it's either (a) look-ahead in the mean-reversion signal, (b) a stale-price / non-tradable fill, or (c) a single-symbol concentration (one ticker that gapped and the "close" was booked at the pre-gap price). The fact that `trust=UNK`, `conf<0.60`, and `fam=mean_reversion` all collapse to the *same* 65-trade cell is a red flag: the cell is defined by one variable, not four. **Do not trade this.** Class-level WR 68% on n=150 is more believable but still small-n.
- **90d expected P&L (1% risk, $100k):** If you *excluded* the suspicious cell: 85 trades at 1% risk, ~55% WR, ~1.5:1 → gross ≈ +$1,275, slippage ~$400 → **+$875**. If you *included* the cell, the number is fake and you'd get burned on the first real fill.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — the 238/5816 = 4.1% pass rate is actually reasonable, but the `mean_reversion` family needs a **separate** `MIN_SCORE_MEAN_REVERSION_EQUITY = 60` and a hard `MAX_SINGLE_SYMBOL_PCT = 0.15` cap. The current gate lets one family dominate the "proven" list.
- **Confidence (1-5):** 2 (class is real-ish; the "proven" cell is not)

### FOREX
- **Real/noise verdict:** **No PROVEN cell.** The best cell (`conf>=0.90 & regime`, n=54, WR_shrunk 63.5%, PF 3.20) **fails holdout** (train PF 0.298 on n=17, holdout PF 14.1 on n=37 — the sign flips completely between windows). This is the textbook signature of regime-dependent noise, not edge. Class-level WR 41.9% on n=537 is a **losing class**. The `passed_smart` rate of 96% (23178/24111) means the gate is doing nothing.
- **90d expected P&L (1% risk, $100k):** Negative. 537 decisive trades at 1% risk, 41.9% WR, ~1.3:1 avg R:R → gross ≈ **-$2,400**, plus ~$1,600 slippage on FX spreads → **-$4,000**. This class is a money incinerator.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise hard to **80** (from whatever produces 96% pass). Target `passed_smart` < 2,000. Also add `FOREX_MIN_CONFIDENCE = 0.85` because the only non-losing sub-cell was `conf>=0.90`.
- **Confidence (1-5):** 1

### CRYPTO
- **Real/noise verdict:** The `conf=0.75-0.80 & S50 & alpha_engine` cell (n=175, WR_shrunk 70.3%, PF 3.46, holdout PF 3.13 on n=48, Bonferroni pass) is the **only cell in the entire report that survives every test**. It's not leakage-shaped: n is large, holdout is consistent, WR_z is 5.97, and the cell is defined by three independent dims (conf, score_decile, source). The `dir=LONG` variant is the same cell with one extra dim — not independent evidence. **This is a real edge.** Caveat: `trust=UNK` on the same cell means the trust dimension is uninformative here — the edge lives in `conf × score_decile × source`, not trust.
- **90d expected P&L (1% risk, $100k):** 175 trades at 1% risk ($1k/trade), 70.3% shrunk WR, PF 3.46 → gross ≈ **+$24,000**. Crypto slippage is real: assume 15 bps round-trip on $1k notional = $1.50/trade × 175 = ~$260. Net ≈ **+$23,700**. Even haircut 50% for execution reality → **+$12,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** it (or add a carve-out) so that `conf ∈ [0.75, 0.80] AND score_decile == S50 AND source == alpha_engine` is *always* admitted, regardless of trust. Currently `passed_verified_alpha=1908` but `passed_high_conviction=0` — the HC gate is throwing away the one edge we have. Set `HC_MIN_TRUST_CRYPTO = 0` (trust is uninformative for this cell) and `HC_MIN_CONF_CRYPTO = 0.75`.
- **Confidence (1-5):** 4

### ETF
- **Real/noise verdict:** n=9 closed. **No edge. No information.** WR 22% is not statistically distinguishable from 50% at n=9.
- **90d expected P&L (1% risk, $100k):** ~**-$200** (9 trades, 22% WR, noise).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **85**; if that yields <20 opens/90d, **disable ETF entirely** until n>=100.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** n=4 closed, 0 wins. This is a **data hygiene bug**, not an asset class. 1399 scanned items with no class label means the classifier is failing. Fix the classifier before analyzing.
- **90d expected P&L (1% risk, $100k):** N/A — do not trade unclassified instruments.
- **Gate change:** Add `REJECT_IF_CLASS_UNKNOWN = True` in `quality_gates.py`. Hard-reject at scan time.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** n=14 closed. **No edge.** H-005 already falsified the momentum inversion. Do not re-derive.
- **90d expected P&L (1% risk, $100k):** ~**-$150** (noise).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **85**, or disable until n>=100.
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** n=30, WR 43.3%. **No edge.** `passed_smart` = 3/561 = 0.5% — the gate is already correctly rejecting almost everything, but `opened` = 531 means opens bypass the gate. That's the bug.
- **90d expected P&L (1% risk, $100k):** ~**-$300** (30 trades, 43% WR, ~1.2:1).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — keep at current strict value, but **enforce it at open time**, not just at label time. The 531 opens vs 3 smart passes is the smoking gun.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** n=5 closed. **No edge.** WR 20% on n=5 is noise.
- **90d expected P&L (1% risk, $100k):** ~**-$100**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **85** or disable.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** n=4 closed. **No edge.** Do not trade.
- **90d expected P&L (1% risk, $100k):** ~**-$100**.
- **Gate change:** Disable MEME in `quality_gates.py` until n>=100.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only.**
The `conf=0.75-0.80 & score_decile=S50 & source=alpha_engine` cell is the only signal in this entire report that survives Bonferroni, holdout, and shrinkage. It has n=175, holdout PF 3.13, and a plausible mechanism (mid-confidence, mid-decile alpha_engine picks — i.e., the model is *not* overconfident and *not* at the extreme of its own score distribution). Expected 90d P&L at 1% risk on $100k: **+$12k to +$24k** depending on execution reality. Start at 0.5% risk until you've verified live fills match backtest fills for 30 days.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.**
It is the largest class by volume (24k scanned, 22.7k opened), the worst WR among high-n classes (41.9% on n=537), and its only "best" cell fails holdout with a sign flip (train PF 0.298 → holdout PF 14.1). That is not a regime edge; that is noise being fit. Mutate the three axes before killing: (1) **axis 1 — gate:** raise `SMART_PICKS_MIN_SCORE_FOREX` to 80 and add `FOREX_MIN_CONFIDENCE = 0.85`; (2) **axis 2 — source:** drop `regime_terminal` entirely (it's the source of the fake best cell); (3) **axis 3 — direction:** test whether the class is structurally short-biased (312 losses vs 225 wins suggests the SHORT side is bleeding). If after 30 days of mutation the class still has WR < 48% on n>=100, kill it.

**Do not scale EQUITY** despite the 68% class WR — the "proven" cell is a 98% WR / PF 218 artifact that will not survive live fills. Investigate the mean_reversion family for look-ahead before trusting any EQUITY number.

**Fix the funnel before the next audit:** `passed_high_conviction = 0` across all 10 classes means the HC gate is dead code. `opened ≈ scanned` for 6 of 10 classes means the smart-picks gate is a label, not a filter. Until those two are fixed, every "edge" number in this report is downstream of a broken pipeline.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### COMMODITY
- Real/noise verdict: Noise. n=23 too small; bonferroni fails; no proven cells; matches patterns of prior rejected COT/inventory leakage.
- 90d expected P&L (1% risk, $100k): -$420 (negative expectancy after slippage; zero edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise/leakage. 98.46% WR and PF=218 on n=65 is statistically impossible without single-symbol concentration or look-ahead; mean_reversion cell fails sanity.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact; do not trade).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 90
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise. All top cells fail holdout and bonferroni; no proven edges.
- 90d expected P&L (1% risk, $100k): -$1,180 (negative after costs; regime cells unstable).
- Gate change: HC_MIN_CONF_FOREX = 0.92
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Marginally real. n=174-175, WR_shrunk 70.26-70.62, PF=3.455, holdout_pass + bonferroni_pass true across multiple cells; no obvious single-symbol or leakage flags.
- 90d expected P&L (1% risk, $100k): $2,850 (uses avg_pnl_pct 1.38, 1% risk, 0.15% slippage, ~175 trades).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 3

### ETF
- Real/noise verdict: No edge. n=9 closed; empty proven list.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge. n=30 closed; empty proven list.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge. n=14 closed; empty proven list.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge. n=5 closed; empty proven list.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge. n=4 closed; empty proven list.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge. n=4 closed; empty proven list.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically defensible cells). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL (mutate the mean_reversion path before any further allocation). All other classes have zero usable edge.
