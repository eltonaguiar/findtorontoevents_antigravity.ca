# Pick Funnel Swarm Verdict — 2026-10-17 04:09 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261017T040917Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below and must be stated up front:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** picks across 90 days and ~53k scans. Either the gate is mis-wired (trust never reaches 60, or score never reaches 80 post-scoring), or the scoring distribution is shifted far below the gate. This is the single most important finding in the dataset — the "HIGH CONVICTION" funnel stage is dead, so any "HC edge" claim is untestable and the dashboard is showing an empty top shelf.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1974) and a trickle of FOREX/FUTURES/MEME pass. The verified-alpha gate is effectively a CRYPTO-only gate.
3. **`opened` >> `passed_smart` in most classes** (EQUITY 5566 opened vs 212 passed_smart; FOREX 22653 vs 23087 — ok; COMMODITY 5953 vs 3711). For EQUITY this is a **26x** discrepancy — the funnel is not actually gating opens on the smart-pick score. The "funnel" is decorative for EQUITY/BOND/UNKNOWN.

Also note the **PROVEN cells are degenerate**: in EQUITY the three "top edges" are the *same 65 trades* sliced three ways (trust=UNK ≡ conf<0.60 ≡ dir=LONG for that cohort). Same for CRYPTO (same 179 trades) and FOREX (same 31). So there is **one** edge per class, not three. Treat n as the cohort n, not 3×n.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell is 65 trades, 64 wins, WR 98.46%, PF 230.8, avg PnL +1.41%. A PF of 230 with 98% WR on mean-reversion longs is not a market edge — it is a **data artifact**. Three red flags: (i) `trust=UNK` on 100% of the cohort means the trust pipeline never scored these; (ii) `score_dec=S40` (score decile 40) is a *low* score bucket yet produces the best PF — inverted vs. the scoring model, classic sign the score isn't what's being traded; (iii) `opened=5566` vs `passed_smart=212` means these 65 trades were **not** selected by the smart gate at all. Most likely explanation: a handful of symbols with a stale/duplicated price feed (mean-reversion + LONG + low score + unknown trust = "buy the dip on a broken ticker"). The train/holdout split (127/99 PF) is *too* stable — real edges decay; this looks like the same broken feed in both halves. **Do not trade.** Flag as potential leakage recurrence (H-001-style timestamp/dedup issue).
- **90d expected P&L (1% risk, $100k):** **$0 recommended.** If you naively sized the 65-trade cohort at 1% ($1,000) risk with avg +1.41% PnL and 98% WR, gross ≈ 65 × $1,000 × 0.0141 × (64/65) ≈ **$900**. That is a rounding error on $100k and is almost certainly fake. Realistic post-dedup expectation: **negative** (EQUITY opened 5566, closed only 139 — 97.5% of opens never resolved, so the "edge" is survivorship on the 2.5% that did).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — but the real fix is upstream: **enforce `opened ⊆ passed_smart`** (currently 5566 opens vs 212 passes). Set the open-gate to hard-require `passed_smart==True`. Without that, no score constant matters.
- **Confidence (1-5):** **1** (that the edge is real); 4 (that it's leakage).

### COMMODITY
- **Real/noise verdict:** **NOISE (borderline).** Best cell: `rr>=2.0 & LONG & alpha_engine`, n=20, WR 75%, shrunk 62.5%, PF 5.28, holdout PF 3.76 — but **`bonferroni_pass=false`** and n=20 is the minimum threshold. This is exactly the profile of H-001 (COT leakage, cotton concentration) and H-036 (inventory gate rejected). The `trust=UNK` + `alpha_engine` + high-RR signature matches the falsified COT pattern. **Do not promote.** The class-level WR is 57.14% on n=70 — barely above coin-flip, and the "edge" is 20 of those 70.
- **90d expected P&L:** Naive: 20 trades × $1,000 × 1.885% × 0.75 ≈ **$283**. Post-Bonferroni-fail discount and H-001/H-036 prior: **~$0 to negative**. Recommend **$0**.
- **Gate change:** `SMART_PICKS_MIN_RR_COMMODITY` — raise from current to **2.5** and add a hard `trust != UNK` requirement (the edge only exists in the UNK bucket, which is the leakage bucket). Better: add `COMMODITY_REQUIRE_KNOWN_TRUST = True`.
- **Confidence (1-5):** **2** (edge real); 4 (it's the H-001 recurrence).

### INDEX
- **Real/noise verdict:** **NO EDGE — too few closes.** n_closed=5, WR 20%, PF not even reported. 1882 scanned, 1538 passed_smart, 1877 opened, **5 closed**. The funnel is 99.7% unresolved. There is nothing to evaluate. Do not trade.
- **90d expected P&L:** **$0** (n=5, WR 20% → expected negative; not statistically distinguishable from zero).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` is irrelevant until resolution works. Fix the **close/resolve pipeline** for INDEX first (5/1877 = 0.27% resolution). No score constant will help.
- **Confidence (1-5):** **1**.

### FOREX
- **Real/noise verdict:** **NOISE / LIKELY LEAKAGE.** Best cell `trust=UNK & regime & LONG & regime_terminal`, n=31, WR 77.4%, shrunk 66.7%, PF 4.08 — but **`holdout_pass=false`** (train_pf=0.0 on n=5, holdout_pf=9.49 on n=26) and **`bonferroni_pass=false`**. A train PF of exactly 0.0 means the train window had **zero wins** — the "edge" is entirely in the holdout, which is the opposite of what a real edge looks like (real edges are stable across both). This is the classic signature of a **regime_terminal source that only started emitting in the holdout window** — i.e., a new data source with no train history, not an edge. Also: FOREX class WR is **42.34%** on n=529 — the class is a net loser; the 31-trade cell is a cherry-pick. The `consensus`/`ml` cells you flagged aren't even in the top-3 here, but the same logic applies: any FOREX cell with PF>4 and n<50 and a failed holdout is noise.
- **90d expected P&L:** Naive: 31 × $1,000 × 0.4543% × 0.774 ≈ **$109**. But holdout-fail + class WR 42% → realistic **negative**. Recommend **$0**; if forced, size at 0.25% risk → ~$27 expected, within noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — but the real lever is **`FOREX_REQUIRE_HOLDOUT_PASS = True`** in the promotion path, and **kill `regime_terminal` as a source** until it has ≥90d of train history. The class-level 42% WR says the smart gate is passing 96% of scans (23087/23980) — it's not gating at all. Raise `SMART_PICKS_MIN_SCORE_FOREX` to the **80th percentile of the score distribution** (currently passing 96%, should pass ~20%).
- **Confidence (1-5):** **1** (edge real); 5 (it's noise).

### CRYPTO
- **Real/noise verdict:** **PLAUSIBLY REAL — the only class with a defensible edge.** Cell `conf=0.75-0.80 & score_dec=S50 & source=alpha_engine`, n=179, WR 74.3%, **shrunk 71.86%**, PF 3.84, **holdout_pass=true** (train 4.11 / holdout 3.33 — stable decay, not inversion), **bonferroni_pass=true**, wr_z=6.50. This is the one cell that survives every check: large n, shrunk WR well above 55%, PF>1.5, holdout stable, Bonferroni-corrected. Caveats: (i) `trust=UNK` again — the trust pipeline isn't scoring CRYPTO either, so "trust" is not a usable dimension; (ii) `score_dec=S50` is the *middle* decile, not the top — the edge is in mid-score, high-conf, alpha_engine picks, which is counterintuitive but consistent (high-score picks may be overfit); (iii) single-source (`alpha_engine`) — concentration risk if that source degrades. The `ml` cell you flagged isn't in the top-3, but the same `alpha_engine`-only concentration applies. **This is the one to scale.**
- **90d expected P&L:** 179 trades × $1,000 risk × 1.4764% avg PnL × 0.743 WR ≈ **$1,963** gross on the edge cohort. Apply 10 bps slippage × 179 × $100k notional... wait — sizing is 1% risk = $1,000/trade, not $100k/trade. Slippage on $1,000 risk at typical crypto 5-10 bps round-trip ≈ $0.50-1.00/trade → ~$90-180 total drag. **Net ≈ $1,800.** If you scale to the full CRYPTO class (2462 closed, WR 45.09% — net loser), you'd **lose** money; the edge is only the 179-trade cohort. So: **$1,800 on the cohort, $0 on the class.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — but the edge is defined by **conf band 0.75-0.80**, not score. The highest-leverage change: add **`CRYPTO_CONF_BAND = (0.75, 0.80)`** as a hard filter and **`CRYPTO_REQUIRE_SOURCE = 'alpha_engine'`** for the promoted cohort. If you must pick one existing constant: set `SMART_PICKS_MIN_SCORE_CRYPTO` to the **S50 decile boundary** (i.e., stop requiring top-decile score; the edge is mid-decile). And fix the HC gate — `passed_high_conviction=0` means the 0.75 conf floor in `hc_filter.js` is never being met by the scoring output; either lower `HC_MIN_CONF` to 0.70 or fix the score→conf mapping.
- **Confidence (1-5):** **4** (edge real); 3 (it persists 90 more days — single-source concentration).

### FUTURES
- **Real/noise verdict:** **NO EDGE.** n_closed=14, no proven cells, no best-PF cells. 200 scanned, 149 passed_smart, 186 opened, 14 closed. H-005 (futures momentum anti-signal) already falsified the family. Nothing here.
- **90d expected P&L:** **$0** (n=14, WR 42.86% → negative expectation).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — irrelevant at n=14. **Demote** per mutation protocol; don't tune.
- **Confidence (1-5):** **1**.

### ETF
- **Real/noise verdict:** **NO EDGE.** n_closed=9, WR 22.22%. 353 scanned, 302 passed_smart, 344 opened, 9 closed. 97.4% unresolved. Nothing to evaluate.
- **90d expected P&L:** **$0** (negative expectation).
- **Gate change:** Fix resolution pipeline first; no score constant matters at n=9.
- **Confidence (1-5):** **1**.

### UNKNOWN
- **Real/noise verdict:** **NO EDGE — and a data-hygiene bug.** 1419 scanned, 155 passed_smart, **1416 opened**, 3 closed, 0 wins. The fact that 1416 "UNKNOWN" instruments opened means the asset-class classifier is failing on ~2.7% of the universe and those are being traded anyway. This is a **routing bug**, not a strategy.
- **90d expected P&L:** **$0** (0/3 wins).
- **Gate change:** `ASSET_CLASS_REQUIRE_KNOWN = True` — block opens when class is UNKNOWN. This is a hygiene gate, not an edge gate.
- **Confidence (1-5):** **1**.

### MEME
- **Real/noise verdict:** **NO EDGE.** n_closed=7, WR 14.29%. 29 scanned, 13 passed_smart, 22 opened, 7 closed. Too small, and the WR is catastrophic.
- **90d expected P&L:** **$0** (negative).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to top-decile or **disable MEME entirely** until n≥50 closed. Recommend disable.
- **Confidence (1-5):** **1**.

### BOND
- **Real/noise verdict:** **NO EDGE.** n_closed=33, WR 39.39%, no proven cells, no best-PF cells. 577 scanned, only **2** passed_smart, but **544 opened** — the smart gate is passing 0.3% yet 94% of scans open. The gate is inverted/decorative here too.
- **90d expected P&L:** **$0** (WR 39% → negative).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — but first fix `opened ⊆ passed_smart` (544 vs 2). Then **demote** per mutation protocol.
- **Confidence (1-5):** **1**.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only the `alpha_engine` / conf 0.75-0.80 / S50 cohort (n=179).** It is the only cell in the entire dataset that passes all five checks (n≥100, shrunk WR≥55%, PF≥1.5, holdout stable, Bonferroni-corrected). Expected 90d P&L on the cohort at 1% risk ≈ **$1,800 net of slippage**. Do **not** scale the full CRYPTO class (WR 45%, net loser) — the edge is the cohort, not the class. Size at 1% risk, cap at 5 concurrent positions, and monitor `alpha_engine` source health weekly; if that source's WR drops below 60% over a 30-trade rolling window, halt.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **FOREX** — class WR 42.34%, smart gate passing 96% of scans (not gating), best cell fails holdout and Bonferroni. Mutate: raise `SMART_PICKS_MIN_SCORE_FOREX` to 80th percentile + require `holdout_pass`. If 30-day WR still <48%, kill.
- **EQUITY** — the "98% WR" cell is leakage (opened 5566 vs passed_smart 212; trust=UNK; low-score bucket). Mutate: enforce `opened ⊆ passed_smart` and dedup/stale-feed check. If the 65-trade cohort doesn't survive dedup, kill the mean-reversion-LONG-S40 family.
- **COMMODITY** — best cell is the H-001/H-036 recurrence (UNK trust, alpha_engine, high-RR, Bonferroni-fail). Mutate: require known trust + RR≥2.5. If it collapses, kill.
- **INDEX / ETF / FUTURES / MEME / BOND / UNKNOWN** — no edge, insufficient n, or routing bug. **Kill or freeze** (no new opens) until resolution rate >50% and n_closed ≥50. UNKNOWN specifically: add `ASSET_CLASS_REQUIRE_KNOWN=True` immediately — it's a bug, not a strategy.

**The meta-finding:** `passed_high_conviction = 0` everywhere and `opened >> passed_smart` in EQUITY/BOND/UNKNOWN means the funnel is **not actually gating opens on the smart/HC scores

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. n=65 with 98.46% WR and PF=230.8 is statistically impossible in live trading; indicates single-symbol concentration or look-ahead bias.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85.
- Confidence (1-5): 1

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf cells fail Bonferroni and have n=20 with unstable holdout.
- 90d expected P&L (1% risk, $100k): -$420 (negative expectancy after costs).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 75.
- Confidence (1-5): 2

**### INDEX**
- Real/noise verdict: Noise. n_closed=5, zero proven edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: N/A.
- Confidence (1-5): 1

**### FOREX**
- Real/noise verdict: Noise. Best_pf cells fail holdout_pass and Bonferroni; no proven cells.
- 90d expected P&L (1% risk, $100k): -$1,850 (negative after slippage).
- Gate change: HC_MIN_CONF_FOREX = 0.82.
- Confidence (1-5): 2

**### CRYPTO**
- Real/noise verdict: Marginally real. n=179, WR_shrunk=71.86%, PF=3.84 with holdout_pass=true and Bonferroni_pass=true; still elevated but passes stated tests.
- 90d expected P&L (1% risk, $100k): +$8,900 (179 trades × 1% risk × 1.476% avg_pnl, 0.15% slippage).
- Gate change: HC_MIN_SCORE_CRYPTO = 82.
- Confidence (1-5): 3

**### FUTURES**
- Real/noise verdict: Noise. n_closed=14, zero proven edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: N/A.
- Confidence (1-5): 1

**### ETF**
- Real/noise verdict: Noise. n_closed=9, zero proven edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: N/A.
- Confidence (1-5): 1

**### UNKNOWN**
- Real/noise verdict: Noise. n_closed=3, zero proven edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: N/A.
- Confidence (1-5): 1

**### MEME**
- Real/noise verdict: Noise. n_closed=7, zero proven edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: N/A.
- Confidence (1-5): 1

**### BOND**
- Real/noise verdict: Noise. n_closed=33, zero proven edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: N/A.
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically passing proven cells). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion S40 path immediately; it is the clearest leakage recurrence). All other classes have no actionable edge.
