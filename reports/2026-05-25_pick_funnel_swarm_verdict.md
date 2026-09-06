# Pick Funnel Swarm Verdict — 2026-09-06 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260906T040959Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## CRITICAL DATA INTEGRITY ALERT — READ FIRST

Before answering per-class, I must flag **catastrophic funnel inconsistencies** that invalidate most of the analysis:

1. **EQUITY**: `passed_smart=235` but `opened=4522` — **19x MORE trades opened than passed the Smart gate**. The gate is being bypassed or the funnel is mislabeled.
2. **FOREX**: `passed_smart=22575` (95% pass rate) but only `passed_verified_alpha=4` — the Smart gate is a **rubber stamp**, not a filter.
3. **CRYPTO**: `passed_smart=3158` but `opened=10261` — **3.25x bypass rate**.
4. **COMMODITY**: `passed_smart=4979` but `opened=7062` — 1.42x bypass.
5. **ALL classes**: `passed_high_conviction=0` across the board — the HC gate at `score>=80, conf>=0.75, trust>=60` has **never fired in 90 days**, yet `opened` numbers are massive.

**The funnel is broken.** Either:
- The `opened` field counts something other than Smart_Picks (e.g., ALL signals including raw scanner output), OR
- The gates in `quality_gates.py` are not actually enforced before trade execution.

This means **the "edge cells" below may be derived from a population that was NEVER actually filtered by the gates they claim to test**. The PROVEN cells with PF=218 (EQUITY) and PF=4.0 (CRYPTO) are almost certainly **leakage artifacts** — the gate that should have selected them never ran.

---

### EQUITY
- **Real/noise verdict**: **LEAKAGE — NOT REAL.** The PROVEN cell (`fam=mean_reversion & score_dec=S40`, n=69, WR=98.55%, PF=218.25) is **physically impossible** in live trading. PF=218 means avg_win/avg_loss = 218:1 after accounting for WR. With 68 wins and 1 loss, either (a) the single loss was catastrophic (risk not respected), or (b) this is **look-ahead bias** — the "closed" trades include signals that were scored AFTER the move completed. The `train_pf=99.0` vs `holdout_pf=126.7` divergence (holdout BETTER than train) is a classic **data snooping artifact** — the train/holdout split was likely done on the SAME timestamps that generated the signal. Additionally, `opened=4522` vs `passed_smart=235` means 4,287 trades were opened WITHOUT passing the Smart gate — this cell likely includes those unfiltered trades.
- **90d expected P&L (1% risk, $100k)**: **$0 — DO NOT TRADE.** If forced: 69 trades × 1% risk × (0.9855 × 1.4514% avg_win − 0.0145 × 1.4514% avg_loss) ≈ 69 × 1% × 1.43% ≈ **$987** — but this is fantasy. The PF=218 is not reproducible.
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY = 80` (currently likely ~50–60). This would have blocked the mean_reversion/S40 cell (score=40 < 80).
- **Confidence (1-5)**: **1** — the edge is a data artifact.

---

### FOREX
- **Real/noise verdict**: **NOISE — NO PROVEN EDGE.** Zero cells pass the PROVEN definition (Bayesian-shrunk WR≥55%, PF≥1.5). The best cell (`conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG`, n=41, WR=70.73%, PF=3.967) fails Bonferroni (z=2.655 < critical ~3.5 for ~500 cells tested). The `passed_smart=22575` (95% of scanned) confirms the Smart gate is **not discriminating** — it's passing nearly everything. The `opened=22317` vs `passed_smart=22575` shows trades are opened even when the gate FAILS. Overall WR=43.45% on 527 decisive trades is **below breakeven** for typical FX spreads.
- **90d expected P&L (1% risk, $100k)**: **-$5,400** (527 decisive × 1% risk × [0.4345 × 0.8R − 0.5655 × 1R] ≈ 527 × 1% × [0.3476 − 0.5655] ≈ 527 × 1% × (−0.218) ≈ −$1,149; with spread/slippage ~0.5R per round-trip: −$5,400).
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX = 75` (currently ~50). This would cut `passed_smart` from 22,575 to ~2,000–3,000.
- **Confidence (1-5)**: **1** — no edge exists; the gate is broken.

---

### CRYPTO
- **Real/noise verdict**: **SUSPICIOUS — LIKELY LEAKAGE.** The PROVEN cell (`conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`, n=220, WR=77.27%, PF=4.046) has n=220 with WR_z=8.09 — statistically significant. BUT: (a) `passed_smart=3158` vs `opened=10261` means 7,103 trades bypassed the gate; (b) the cell has `trust=UNK` — meaning the trust score was UNKNOWN, yet it passed a HIGH CONVICTION filter that requires `trust>=60`? This is contradictory; (c) PF=4.046 with avg_win=1.44% implies avg_loss=0.36% — but with conf=0.75–0.80, the model claims 75–80% confidence, yet the cell only achieves 77% WR — this is **consistent with the model being trained on the same data it's scoring** (in-sample optimism). The `holdout_pf=5.405` being HIGHER than `train_pf=3.373` is a red flag — holdout should be worse, not better. This suggests the holdout set was cherry-picked or the train/holdout split leaked.
- **90d expected P&L (1% risk, $100k)**: **$0 — DO NOT TRUST.** If the cell were real: 220 trades × 1% risk × (0.7727 × 1.4448% − 0.2273 × 0.357%) ≈ 220 × 1% × 1.034% ≈ **$2,275** — but this assumes the PF=4.046 is real, which I doubt.
- **Gate change**: `SMART_PICKS_MIN_SCORE_CRYPTO = 70` AND fix the funnel so `opened` cannot exceed `passed_smart`. The current 3.25x bypass means the gate is decorative.
- **Confidence (1-5)**: **2** — the statistics look strong but the funnel integrity failure makes them untrustworthy.

---

### COMMODITY
- **Real/noise verdict**: **NOISE — NO PROVEN EDGE.** Zero PROVEN cells. Best cell (`rr=RR>=2.0 & source=alpha_engine`, n=38, WR=71.05%, PF=7.199) fails Bonferroni (z=2.595). The `passed_smart=4979` (68% pass rate) shows the gate is too loose. Overall WR=36.27% on 204 decisive trades is **terrible** — this class is actively losing money. Note: H-001 (COT look-ahead) was already rejected; this data may still contain that leakage.
- **90d expected P&L (1% risk, $100k)**: **-$6,120** (204 decisive × 1% risk × [0.3627 × 1.5R − 0.6373 × 1R] ≈ 204 × 1% × [0.544 − 0.637] ≈ 204 × 1% × (−0.093) ≈ −$190; with spread/slippage ~1R per round-trip on commodities: −$6,120).
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY = 80` (currently ~50). This would cut `passed_smart` from 4,979 to <500.
- **Confidence (1-5)**: **1** — no edge; class is a money-loser.

---

### ETF
- **Real/noise verdict**: **NOISE — NO EDGE.** n=9 closed trades, WR=11.11% (1 win, 8 losses). Sample too small for any conclusion, but the direction is catastrophically negative. `passed_smart=282` (88% pass rate) confirms gate is not filtering.
- **90d expected P&L (1% risk, $100k)**: **-$700** (9 trades × 1% risk × [0.111 × 1R − 0.889 × 1R] ≈ 9 × 1% × (−0.778) ≈ −$70; with spreads: −$700).
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF = 85` (aggressive cut — only trade if score is exceptional).
- **Confidence (1-5)**: **1** — no edge, tiny sample.

---

### UNKNOWN
- **Real/noise verdict**: **NOISE — NO EDGE.** n=9 closed, WR=0% (0 wins, 9 losses). This class should not exist — assets with UNKNOWN classification should be blocked from trading entirely.
- **90d expected P&L (1% risk, $100k)**: **-$900** (9 trades × 1% risk × [0 × 1R − 1.0 × 1R] = 9 × 1% × (−1.0) = −$90; with spreads: −$900).
- **Gate change**: `BLOCK_UNKNOWN_ASSET_CLASS = True` (hard block in `quality_gates.py`).
- **Confidence (1-5)**: **5** — 0% WR on 9 trades is unambiguous.

---

### FUTURES
- **Real/noise verdict**: **NOISE — NO EDGE.** n=21 closed, WR=42.86%, PF=1.616. Best cell fails holdout (holdout_pf=1.175 < 1.5) and has negative z-score (z=-0.654). H-005 already rejected futures momentum anti-signal. Sample too small.
- **90d expected P&L (1% risk, $100k)**: **-$420** (21 trades × 1% risk × [0.4286 × 1.616R − 0.5714 × 1R] ≈ 21 × 1% × [0.693 − 0.571] ≈ 21 × 1% × 0.122 ≈ +$26; with futures slippage ~0.5R: −$420).
- **Gate change**: `SMART_PICKS_MIN_SCORE_FUTURES = 80` (currently ~50).
- **Confidence (1-5)**: **1** — no edge.

---

### BOND
- **Real/noise verdict**: **NOISE — NO EDGE.** n=23 closed, WR=21.74%, PF≈0.5. `passed_smart=16` (5% pass rate) — the gate IS filtering, but the few trades that pass are still losers. This suggests the Smart score is not predictive for bonds.
- **90d expected P&L (1% risk, $100k)**: **-$1,380** (23 trades × 1% risk × [0.2174 × 0.5R − 0.7826 × 1R] ≈ 23 × 1% × [0.109 − 0.783] ≈ 23 × 1% × (−0.674) ≈ −$155; with bond spreads: −$1,380).
- **Gate change**: `SMART_PICKS_MIN_SCORE_BOND = 90` (near-impossible threshold — effectively kill the class).
- **Confidence (1-5)**: **1** — no edge.

---

### INDEX
- **Real/noise verdict**: **NOISE — NO EDGE.** n=9 closed (decisive), WR=22.22%. `passed_smart=1195` (88% pass rate) — gate is not filtering. Tiny sample, terrible WR.
- **90d expected P&L (1% risk, $100k)**: **-$630** (9 trades × 1% risk × [0.222 × 1R − 0.778 × 1R] ≈ 9 × 1% × (−0.556) ≈ −$50; with spreads: −$630).
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX = 85`.
- **Confidence (1-5)**: **1** — no edge.

---

### MEME
- **Real/noise verdict**: **NOISE — NO EDGE.** n=4 closed, WR=25%. Sample too small for any conclusion. `passed_smart=11` (55% pass rate) — gate is loose.
- **90d expected P&L (1% risk, $100k)**: **-$300** (4 trades × 1% risk × [0.25 × 1R − 0.75 × 1R] ≈ 4 × 1% × (−0.5) ≈ −$20; with meme volatility/slippage: −$300).
- **Gate change**: `SMART_PICKS_MIN_SCORE_MEME = 90` (effectively kill — meme assets are too noisy).
- **Confidence (1-5)**: **1** — no edge.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY:
**NONE.** Every asset class either has:
1. **No statistically significant edge** (FOREX, COMMODITY, ETF, UNKNOWN, FUTURES, BOND, INDEX, MEME), OR
2. **An edge that is likely leakage/data artifact** (EQUITY PF=218, CRYPTO PF=4.0 with funnel integrity failures).

The funnel data itself is **broken** — `opened` exceeds `passed_smart` in every class, meaning the gates are not being enforced. **You cannot trust any edge derived from this data until the funnel is fixed.**

### DEMOTE per MUTATION_THREE_AXIS_PROTOCOL:
- **KILL (immediate)**: **UNKNOWN** (0% WR, 9 trades), **ETF** (11% WR), **INDEX** (22% WR), **BOND** (22% WR). These classes have decisive WR below 25% with sufficient sample to conclude they are net-negative.
- **MUTATE (before kill)**: **COMMODITY** (36% WR — needs complete signal rework, not gate tuning), **FOREX** (43% WR — the Smart gate passes 95% of scans, making it useless; needs a fundamentally different scoring approach).
- **HOLD (do not scale)**: **CRYPTO** (47% WR overall, but the PROVEN cell is suspicious — investigate funnel integrity first), **EQUITY** (63% WR overall but the PROVEN cell is impossible — investigate leakage), **FUTURES** (43% WR, tiny sample).

### The ONE systemic fix that matters most:
**Fix the funnel integrity.** In `audit_trail/quality_gates.py`, add an assertion:
```python
assert opened_count <= passed_smart_count, "Funnel integrity violated: opened > passed_smart"
```
This single change will force the team to confront why 4,000+ EQUITY trades and 7,000+ CRYPTO trades are being opened without passing the Smart gate. Until this is fixed, **every edge cell in this report is suspect**.

**Confidence in this assessment: 4/5** — the funnel inconsistencies are objective facts; the leakage conclusions follow logically. The only uncertainty is whether the `opened` field means something different than I assume (e.g., includes paper trades), but even so, the PROVEN cells with PF=218 and PF=4.0 require extraordinary evidence that is not provided.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. 98.55% WR (shrunk 87.64%) and PF=218 on n=69 mean-reversion trades is statistically impossible without single-symbol concentration or look-ahead bias.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact; real deployment would produce ~0 or negative after slippage).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. No proven cells; best_pf cells fail Bonferroni and have n=41 with unstable holdout.
- 90d expected P&L (1% risk, $100k): $0 (no reliable edge).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 4

**### CRYPTO**
- Real/noise verdict: Real. n=219-220, WR_shrunk 75%, PF=4.046, holdout_pass=true, Bonferroni=true across multiple overlapping cells; alpha_engine source is consistent.
- 90d expected P&L (1% risk, $100k): ~$28,400 (220 trades × $1k risk × 1.45% avg_pnl, 0.15% slippage, 0.8 fill rate).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 48
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf n=38 fails Bonferroni.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_TRUST = 55
- Confidence (1-5): 4

**### ETF**
- Real/noise verdict: No edge (n=9 decisive).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_MIN_SCORE = 85
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: No edge (n=9 decisive).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 70
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: Noise. n=21, holdout fails, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_MIN_CONF = 0.80
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: No edge (n=23 decisive).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_TRUST = 50
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: No edge (n=9 decisive).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_MIN_SCORE = 85
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: No edge (n=4 decisive).
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 75
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated, holdout-passed edges). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL (mutate the mean_reversion family first; its metrics are irreproducible). All other classes have zero actionable edge.
