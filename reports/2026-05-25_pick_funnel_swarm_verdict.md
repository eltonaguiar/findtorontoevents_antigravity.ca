# Pick Funnel Swarm Verdict — 2026-10-13 04:15 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261013T041501Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class: two structural facts dominate everything below.

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** trades across 90 days and ~53k scans. Either the gate is mis-wired (trust never reaches 60, or score never reaches 80 on the same row), or the scoring pipeline never co-satisfies all three. This is the single biggest finding in the dataset — the "HIGH CONVICTION" funnel stage is dead code in production.
2. **`opened` >> `passed_smart` in most classes** (CRYPTO 10,633 opened vs 3,502 passed_smart; FOREX 22,897 vs 23,355; EQUITY 5,627 vs 226; BOND 543 vs 3). The funnel is not actually gating opens. Whatever `passed_smart` is, it is not the admission gate for `opened`. That means the "edge cells" below are computed on a population that was **not** filtered by the gates you think are filtering it.

Also note: the prompt asks me to comment on "FOREX `consensus` and CRYPTO `ml` cells" — **neither appears in the data you provided.** The FOREX top cell is `regime_terminal`, and CRYPTO's is `alpha_engine`. I'll flag the cells that *are* present and call out the mismatch.

---

### CRYPTO
- **Real/noise verdict:** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell (n=181, WR_shrunk=68.7%, PF=3.14, holdout PF=2.52, Bonferroni pass) is the **only cell in the entire dataset that survives every robustness check you ran**. That said, three red flags: (i) it's a *narrow* confidence band (0.75–0.80) — that's a suspiciously specific slice, classic overfit signature; (ii) `score_dec=S50` is a decile bucket, and the fact that the edge lives in exactly one decile of score while the class-wide WR is 45% suggests the score is doing real work *only* in that band, which is fragile; (iii) `trust=UNK` dominates — meaning the trust dimension is uninformative here, so the "trust>=60" HC gate can never fire on this cell. **Verdict: probably real, but narrow and fragile.** Treat as a candidate, not a proven edge, until it survives a fresh 30-day out-of-sample window.
- **90d expected P&L (1% risk, $100k):** 181 trades × 1% × $100k = $1,000 risk/trade. avg_pnl_pct = 1.30% of notional. If "1% risk" means $1k risked and avg win/loss ratio implied by PF=3.14 with WR=70.7% → avg_win/avg_loss ≈ 1.30. Expected $/trade ≈ 0.707×1.30×$1k − 0.293×$1k ≈ $919 − $293 = **+$626/trade**. × 181 = **~$113k gross**. Apply 15 bps round-trip slippage on $100k notional = $150/trade × 181 = $27k drag. **Net ≈ $85k.** But this assumes you can actually route 181 trades through the HC gate — which currently fires zero times. Realistic capture at current funnel: **$0**.
- **Gate change:** `hc_filter.js` — the trust>=60 threshold is unreachable for this cell (trust=UNK). Either **lower `HC_MIN_TRUST` to 0** and rely on score+conf, or **add a bypass**: `if (source==='alpha_engine' && conf>=0.75 && conf<0.80 && score_decile===50) allow`. Cleanest single change: **`HC_MIN_TRUST: 60 → 0`** and compensate by raising `HC_MIN_SCORE: 80 → 85`. This unblocks the only statistically real cell in the dataset.
- **Confidence (1-5):** 3

### COMMODITY
- **Real/noise verdict:** n_closed=72 is too thin to prove anything. The `rr>=2.0 & source=alpha_engine` cell (n=24, WR_shrunk=63.6%, PF=4.99) **fails Bonferroni** and has train_n=13 / holdout_n=11 — that's not a holdout, that's a coin flip. Also: H-001 and H-036 in your registry already killed COMMODITY directional signals (COT leakage, inventory gate). The 56.9% class WR on n=72 is within noise of 50%. **Verdict: noise.** Do not size.
- **90d expected P&L (1% risk, $100k):** Statistically indistinguishable from $0. Point estimate on the 24-trade cell: 24 × $1k × (0.75×~1.5 − 0.25) ≈ **+$21k gross**, minus slippage (~$3.6k) ≈ **+$17k** — but with n=24 and Bonferroni fail, the 95% CI spans negative. **Report as $0 expected.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise it hard. Currently 3,661/6,136 pass (60%). Set to a value that cuts pass rate to <15% until n_closed > 200. Suggest **+15 points** on whatever the current constant is.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** **This is the loudest leakage alarm in the dataset.** `fam=mean_reversion & score_dec=S40` with **WR=98.46% (64/65), PF=220.9, holdout PF=99.0**. A PF of 220 is not an edge — it is a **data artifact**. Three specific failure modes to check: (i) **look-ahead in the mean-reversion entry** — if the "reversion" is measured against a close that includes the exit bar, WR goes to ~100%; (ii) **single-symbol concentration** — 65 trades in one family/decile bucket smells like one ticker (e.g., a low-float name) with a broken price feed; (iii) **survivorship / delisting** — losers dropped from the panel. The `holdout_pf=99.0` is the tell: a real holdout does not produce PF=99. **Verdict: leakage, not edge.** Do not trade. File as H-0xx leakage recurrence.
- **90d expected P&L (1% risk, $100k):** If real (it isn't): 65 × $1k × (0.985×~1.35 − 0.015) ≈ **+$85k**. **Realistic: $0, and possibly negative once the leak is fixed** — mean-reversion families that look this good pre-fix typically go to WR≈48–52% post-fix.
- **Gate change:** Do **not** loosen gates to capture this. Instead, add a **sanity cap in `quality_gates.py`**: reject any cell with `PF > 20` from the "PROVEN" list and route to a `LEAKAGE_REVIEW` queue. Constant name suggestion: `MAX_PLAUSIBLE_PF = 20.0`. This is the gate change that lifts edge most for EQUITY — by *removing* the fake edge that's currently crowding out real signal.
- **Confidence (1-5):** 1 (that it's real); 5 (that it's leakage)

### FOREX
- **Real/noise verdict:** Class WR 41.5% on n=528 decisive — **losing class**. The top cell (`conf>=0.90 & dir=LONG & source=regime_terminal`, n=29, WR_shrunk=69.4%, PF=6.02) **fails holdout** (`holdout_pass=false`, train_n=5, holdout_n=24 — the "train" set is 5 trades, which is not a train set). **Bonferroni fail.** This is exactly the pattern that H-035 killed for CRYPTO funding: sign instability across windows. **Verdict: noise.** The 82.8% raw WR on n=29 with a 5-trade train is a textbook small-sample mirage.
- **90d expected P&L (1% risk, $100k):** Class-wide, 528 decisive × $1k × (0.415×~1.1 − 0.585) ≈ **−$95k**. The "top cell" would be +$12k if real, but it isn't. **Report class as −$95k realized, $0 forward.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — currently 23,355/24,270 pass (96%!). The gate is doing nothing. Raise until pass rate <20%. Also: **`HC_MIN_CONF` should not be lowered for FOREX** — the 0.90+ band is where the mirage lives.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** n_closed=6. **No verdict possible.** WR 16.7% is 1/6. Do not trade, do not analyze further.
- **90d expected P&L (1% risk, $100k):** **$0** (insufficient n; point estimate −$3.3k but meaningless).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to effectively disable until n_closed ≥ 100. Or add `MIN_CLOSED_FOR_PROMOTION = 100` in `quality_gates.py`.
- **Confidence (1-5):** 1

### ETF
- **Real/noise verdict:** n_closed=9, WR 22.2%. **Noise / insufficient.** Same as MEME.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** Same `MIN_CLOSED_FOR_PROMOTION = 100` guard.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** n_closed=3, WR 0%. This is a **data hygiene failure**, not an asset class. 1,403 scans landed in UNKNOWN and 1,400 opened. That's a classifier bug, not a strategy. **Verdict: fix the classifier, don't trade it.**
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** Add a hard reject in `production_scanner.py`: `if asset_class == 'UNKNOWN': skip`. Constant: `REJECT_UNKNOWN_CLASS = True`.
- **Confidence (1-5):** 5 (that it's a bug)

### BOND
- **Real/noise verdict:** n_closed=30, WR 43.3%. **Noise.** 543 opened vs 3 passed_smart — the gate is inverted (it's passing almost nothing but opening almost everything).
- **90d expected P&L (1% risk, $100k):** **$0** (point estimate −$2k, meaningless).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — currently 3/573 pass. The gate is *too tight* to be useful and the opens bypass it. Fix the bypass first (see system-wide).
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** n_closed=13. H-005 already killed the futures momentum inversion. **Noise.**
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** `MIN_CLOSED_FOR_PROMOTION = 100` guard.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** n_closed=5 (decisive), WR 20%. **Noise.**
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** `MIN_CLOSED_FOR_PROMOTION = 100` guard.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money:** **CRYPTO only**, and only the single cell `conf∈[0.75,0.80] & score_dec=S50 & source=alpha_engine`. It is the only cell in the entire 90-day dataset that passes holdout, Bonferroni, and has n≥180. Size it at **0.25% risk per trade** (not 1%) until it survives a fresh 30-day window, because the narrow confidence band is a fragility signal. Expected forward P&L at 0.25% risk: **~$21k/90d**, not the $85k headline.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **EQUITY** — demote immediately. The `mean_reversion & S40` cell is a **leakage recurrence** (PF=220, holdout PF=99). Mutate the axis: re-run with (a) entry price = next-bar open, (b) per-symbol concentration cap, (c) delisted-symbol inclusion. If WR drops below 55% post-fix, kill the family. Do **not** promote any EQUITY cell until the leakage audit clears.
2. **FOREX** — demote. Class WR 41.5% on n=528 is a real losing signal, not noise. The `regime_terminal` cell fails holdout with a 5-trade train set. Mutate: test whether the 0.90+ confidence band is a *calibration* artifact (i.e., the model is overconfident, not correct). If calibration fix doesn't lift WR above 50%, kill the class.
3. **COMMODITY** — demote. H-001 and H-036 already killed the two obvious axes. The remaining `rr>=2.0` cell fails Bonferroni on n=24. Mutate: test `rr>=2.0` on a *different* source than `alpha_engine` to see if the edge is source-specific or family-specific. If neither, kill.

**Do not scale:** MEME, ETF, BOND, FUTURES, INDEX, UNKNOWN — all have n_closed < 35 and no cell passes Bonferroni. UNKNOWN is a classifier bug, not a class.

**The single highest-leverage fix across the whole system** is not a threshold — it's the **`passed_high_conviction = 0` bug**. The HC gate is firing on zero trades in 90 days. Until that's fixed, the "HIGH CONVICTION" funnel stage is decorative, and every downstream metric (including the edge cells above) is computed on a population that was never actually filtered by the gate you think is filtering it. Fix the HC gate wiring *before* tuning any threshold constant, or you'll be tuning a gate that isn't connected to anything.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real — n=180+, WR_shrunk 68-69%, PF=3.14, holdout_pass + bonferroni_pass both true; no obvious leakage flags.
- 90d expected P&L (1% risk, $100k): +$2,800 (edge subset only; 180 trades × ~1.3% avg pnl at 1% risk, 0.2% slippage).
- Gate change: hc_filter.js MIN_SCORE = 50
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Noise — PF=220 and 98% WR on n=65 is statistically impossible without single-symbol concentration or leakage.
- 90d expected P&L (1% risk, $100k): -$1,450 (overall WR 70% collapses after costs/slippage on small sample).
- Gate change: quality_gates.py SMART_PICKS_MIN_SCORE_EQUITY = 70
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — all top cells fail holdout and bonferroni; n=29 too small.
- 90d expected P&L (1% risk, $100k): -$3,100 (overall WR 41%).
- Gate change: quality_gates.py SMART_PICKS_MIN_SCORE_FOREX = 85
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise — bonferroni fails; n=24 marginal and matches rejected COT-style patterns.
- 90d expected P&L (1% risk, $100k): -$180 (overall WR 57% but tiny closed count).
- Gate change: quality_gates.py SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 4

### MEME
- Real/noise verdict: Noise — n=6 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): -$120.
- Gate change: quality_gates.py SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n=9 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): -$70.
- Gate change: quality_gates.py SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n=30 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): -$80.
- Gate change: quality_gates.py SMART_PICKS_MIN_SCORE_BOND = 85
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n=13 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): -$40.
- Gate change: quality_gates.py SMART_PICKS_MIN_SCORE_FUTURES = 85
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n=5 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): -$30.
- Gate change: quality_gates.py SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n=3 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): -$20.
- Gate change: quality_gates.py SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified holdout-passing edges). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate score floor upward before any further allocation). All other classes have no actionable edge.
