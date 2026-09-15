# Pick Funnel Swarm Verdict — 2026-09-15 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260915T041037Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural facts that dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** picks across 90 days and ~62k scans. Either the gate is mis-wired, or the scoring pipeline never produces trust>=60. This is the single biggest finding in the dataset.
2. **`opened` >> `passed_smart`** in every class (e.g. FOREX: 22,542 opened vs 22,930 passed_smart; EQUITY: 4,593 opened vs 228 passed_smart). The funnel is not actually gating — picks are being opened that never passed the Smart floor. The "funnel" is decorative.
3. **`closed` is a tiny fraction of `opened`** (EQUITY 197/4593 = 4.3%; FOREX 1409/22542 = 6.3%). WR numbers are computed on the closed subset, which is a **survivorship-biased sample** — likely the ones that hit TP or SL fast. Long-dated open positions are invisible.

---

### EQUITY
- **Real/noise verdict:** The "PROVEN" cell `fam=mean_reversion & score_dec=S40` with **WR=98.53%, PF=214.7** is not a real edge — it is a **labeling artifact**. PF of 214 with n=68 means average win / average loss ≈ 200:1. That is only possible if losses are being recorded as ~0 (breakeven stops, or a P&L sign bug, or "loss" rows with pnl≈0). The `wr_z=8.0` is meaningless when the underlying P&L distribution is degenerate. **Flag as leakage/bug, not edge.** Also note `trust=UNK` on 100% of the cell — the trust dimension is not populated, so the "trust band" dimension is a null column masquerading as a filter.
- **90d expected P&L (1% risk, $100k):** Cannot responsibly estimate. If we take the cell at face value (68 trades × 1% risk × avg_pnl 1.26% × $100k = ~$85k) it's fantasy. Realistic read: EQUITY has 197 closed trades, 67.5% WR, but the WR is inflated by the same degenerate-loss issue. **Estimate: $0 to -$5k** (i.e., no demonstrable edge; likely slightly negative after slippage).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current floor to **65** and add a hard `min_avg_loss_pct` sanity check (reject any cell where avg_loss < 0.1%). The mean_reversion cell must be quarantined until the P&L sign bug is fixed.
- **Confidence (1-5): 1**

### BOND
- **Real/noise verdict:** **Noise.** n=24 closed, WR=25%, PF not even reported (no cell hit n>=20 threshold with positive edge). 478 scanned → 8 passed_smart → 0 verified_alpha → 0 HC. This class is producing picks that lose 3:1. No edge.
- **90d expected P&L (1% risk, $100k):** 24 trades × 1% × (-0.5% avg) ≈ **-$1.2k**. Effectively zero signal, negative drift.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **999 (effectively disable)** until a real edge is found. Per MUTATION_THREE_AXIS_PROTOCOL, mutate the strategy family before killing, but do not allocate capital.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict:** The `rr=RR>=2.0 & score_dec=S50` cell (n=21, WR=76%, PF=5.6) **fails Bonferroni** (`bonferroni_pass: false`) and has holdout_n=11 — that's not a holdout, that's a coin flip. Also: **H-001 (COT positioning) and H-036 (inventory direction) are both formally killed** — any COMMODITY edge that smells like positioning/inventory is a leakage recurrence. The 3,953/6,492 passed_smart rate (61%) is absurdly permissive; the Smart floor is not filtering.
- **90d expected P&L (1% risk, $100k):** 132 closed × 1% × ~0.2% avg ≈ **+$2.6k**, but with n=21 in the "edge" cell and Bonferroni fail, treat as **$0 ± $3k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise from current to **70** (currently passing 61% of scans; needs to pass <5%). Also add `MIN_RR=2.0` as a hard pre-filter, not a scoring dimension.
- **Confidence (1-5): 2**

### FOREX
- **Real/noise verdict:** The `conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG` cell (n=47, WR=72%, PF=4.34) **fails Bonferroni** (`bonferroni_pass: false`). holdout_n=14. This is the classic "one good month" pattern. More damning: **22,930 of 23,951 scans passed_smart (95.7%)** — the Smart gate is a no-op for FOREX. The 45.9% overall WR on 614 decisive trades is the honest number, and it's a losing coin flip. The "consensus" cell you flagged: I don't see a `consensus` source in the top edges, but the `source=alpha_engine` dominance + `trust=UNK` on every cell means the trust dimension is dead here too.
- **90d expected P&L (1% risk, $100k):** 614 decisive × 1% × (-0.05% avg) ≈ **-$3k**. The 47-trade "edge" cell would be +$2k if real, but Bonferroni fail + 95.7% pass rate = noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current to **75** (must cut 95.7% pass rate to <10%). This is the highest-leverage single change in the whole system.
- **Confidence (1-5): 1**

### CRYPTO
- **Real/noise verdict:** This is the **only class with a defensible edge**. The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell: n=214, WR_shrunk=74.4%, PF=4.05, **holdout_pass=true** (holdout_n=42, holdout_pf=4.98), **bonferroni_pass=true**, wr_z=7.79. Train/holdout PF are consistent (3.72 vs 4.98) — no obvious overfit. **However:** the cell is defined by `score_dec=S50` (score decile 50 = median), which is suspicious — why would the *median* score decile be the edge? That smells like the score is not monotonic with edge, i.e., the scoring model is mis-calibrated. Also `trust=UNK` on the top cell — trust dimension is dead. The `ml` source you mentioned isn't in the top-3, so I can't confirm/deny; but if an `ml` cell shows PF>10, treat as leakage until proven otherwise.
- **90d expected P&L (1% risk, $100k):** 214 trades × 1% risk × avg_pnl 1.44% × $100k = **~$30.8k** gross. Apply 0.15% slippage per trade (crypto, 214 trades) = -$3.2k. **Net ≈ +$27k** on $100k notional over 90d. This is the only class where the number is real.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** from current to **50** (to capture the S50 decile cell) AND add `MIN_CONF=0.75` as a hard pre-filter. The current gate is passing 3,195/12,417 (25.7%) but the edge lives in a narrow conf band. Tighten conf, loosen score.
- **Confidence (1-5): 4**

### ETF
- **Real/noise verdict:** **Noise.** n=7 closed, WR=14.3%. 332 scanned → 292 passed_smart (88% pass rate — gate is a no-op). No edge.
- **90d expected P&L (1% risk, $100k):** 7 trades × 1% × (-1% avg) ≈ **-$700**. Statistically meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **999 (disable)**. 7 closed trades in 90 days is not a strategy.
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict:** **Noise + data hygiene failure.** 1,432 scanned, 1,423 opened, 9 closed, 0 wins. The fact that 1,423 picks have no asset class is a **pipeline bug**, not a strategy. These should be rejected at ingestion.
- **90d expected P&L (1% risk, $100k):** 9 trades × 1% × (-1% avg) ≈ **-$900**. But the real cost is the 1,423 open positions with unknown exposure.
- **Gate change:** Add `REQUIRE_ASSET_CLASS=True` in `production_scanner.py` — reject any pick without a class tag. This is a hygiene fix, not a gate tune.
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict:** **Noise.** n=4 closed, 0 wins. 1,413/1,568 passed_smart (90% pass rate). No edge.
- **90d expected P&L (1% risk, $100k):** ~**-$400**. Meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **999 (disable)**.
- **Confidence (1-5): 1**

### FUTURES
- **Real/noise verdict:** **Noise.** n=18 closed, WR=38.9%. **H-005 (futures_momentum_anti_signal) is formally killed** — do not re-derive. No edge.
- **90d expected P&L (1% risk, $100k):** 18 × 1% × (-0.3%) ≈ **-$540**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **999 (disable)** pending new hypothesis.
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict:** **Noise.** n=4 closed. Not a strategy.
- **90d expected P&L (1% risk, $100k):** ~**-$200**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **999 (disable)**.
- **Confidence (1-5): 1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only.**
- The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the only one that passes Bonferroni, has a real holdout (n=42), and shows train/holdout PF consistency. Expected 90d P&L ≈ **+$27k on $100k** at 1% risk.
- **Caveat:** the `score_dec=S50` (median decile) definition is a red flag that the scoring model is mis-calibrated. Before scaling, verify the score→edge relationship is monotonic; if not, the "edge" may be a proxy for something else (e.g., a specific strategy family that happens to cluster at S50). Run the cell with `fam` added as a dimension to check for single-family concentration.

**Demote per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill):**
- **FOREX** — the 95.7% pass rate is the worst gate failure in the system. Mutate the Smart floor to 75, re-run 90d, and if WR stays <50%, kill.
- **COMMODITY** — 61% pass rate, Bonferroni-fail edge, and two killed hypotheses (H-001, H-036) in the same class. Mutate the RR pre-filter, re-run, expect kill.
- **EQUITY** — the PF=214 cell is a **bug, not an edge**. Do not mutate; **fix the P&L sign/loss-recording bug first**, then re-evaluate. Until then, EQUITY is untrustworthy.
- **BOND, ETF, UNKNOWN, INDEX, FUTURES, MEME** — disable Smart picks entirely (set floor to 999). These are not strategies; they are pipeline noise.

**The single most important fix is not a gate value — it's the `passed_high_conviction = 0` across all classes.** The HC gate is either mis-wired or the trust dimension is never populated (every top cell shows `trust=UNK`). Fix the trust pipeline before tuning any threshold, or every gate change is tuning a dead signal.

**Honest bottom line:** Of 10 asset classes, **1 has a defensible edge (CRYPTO)**, **1 has a bug masquerading as an edge (EQUITY)**, **2 have Bonferroni-failing noise (FOREX, COMMODITY)**, and **6 have no edge at all**. The funnel is not a funnel — it's a wide-open pipe with a decorative filter. Do not scale anything except CRYPTO, and do not trust any WR number until the closed-trade survivorship bias (4-6% close rate) is addressed.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: noise (leakage / single-symbol concentration). n=68 with 98.53% WR and PF=214 is statistically impossible in live trading; violates every known market regime.
- 90d expected P&L (1% risk, $100k): $0 (edge is fictitious; any real deployment would lose to slippage + regime shift).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: no edge (n=24 total closed, zero proven cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: no edge (zero proven cells; best_pf cells fail Bonferroni and n<30 after split).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 75
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: no edge (best_pf cells fail Bonferroni; n=47 too small for claimed PF=4.34).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 5

**### CRYPTO**
- Real/noise verdict: statistically real. n=213–214, WR_shrunk 74.4%, PF=4.05, holdout passes, Bonferroni passes, high wr_z. Alpha_engine source is consistent.
- 90d expected P&L (1% risk, $100k): ~$28,400 (214 trades × ~$133 avg win after 1% risk + 0.15% slippage; assumes 0.8 R:R realized).
- Gate change: HC_MIN_SCORE = 75
- Confidence (1-5): 4

**### ETF**
- Real/noise verdict: no edge (n=7 total closed).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: no edge (n=9 total closed).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: no edge (n=4 total closed).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: no edge (n=18 total closed).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: no edge (n=4 total closed).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, Bonferroni-passing edge). Demote EQUITY, BOND, COMMODITY, FOREX, ETF, INDEX, FUTURES, MEME, UNKNOWN per MUTATION_THREE_AXIS_PROTOCOL.md — they have either zero or fabricated edges and should be mutated (score/conf floors raised) before any further capital allocation.
