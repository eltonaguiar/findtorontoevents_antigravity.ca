# Pick Funnel Swarm Verdict — 2026-11-04 04:06 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261104T040632Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (score≥80, conf≥0.75, trust≥60) is *never* satisfied by any pick in 90 days. The "HIGH CONVICTION" funnel is dead code — it is not filtering, it is excluding 100%. Any edge you think you have is *not* being surfaced by the HC gate.
2. **`passed_verified_alpha` is 0 for 7 of 10 classes** and tiny (3, 2278, 1) for the rest. The "verified alpha" stage is effectively a no-op except for CRYPTO.
3. **`opened` ≈ `scanned` in every class** (e.g. FOREX 22,992/24,221 = 95%; EQUITY 5,620/5,750 = 98%). The funnel is not a funnel — it is a pass-through. The only real gate is `passed_smart`, and even that is bypassed for opening.

This means the "edges" below are **post-hoc cell mining on a near-unfiltered population**, not the output of a working gate stack. Treat every PROVEN cell with that prior.

---

### CRYPTO
- **Real/noise verdict:** The single PROVEN cell (`conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`, n=169, WR 78.7%, shrunk 75.7%, PF 4.20, holdout PF 2.74) is **the only cell in the entire report that survives a genuine train/holdout split with a plausible holdout PF**. That is the strongest statistical evidence in the dataset. **However:** (i) the three "different" PROVEN cells are the *same 169 trades* re-sliced by adding `trust=UNK` or `dir=LONG` — they are not independent confirmations, they are one cell counted three times; (ii) `trust=UNK` on a 78.7% WR cell is a red flag — the trust model has no opinion on the best-performing cell, which usually means the trust features are missing/leaking rather than that the cell is genuinely untrusted-but-good; (iii) `score_dec=S50` is a *decile* bucket, and a 78.7% WR concentrated in one decile of one source smells like a scoring artifact (e.g. score computed with post-trade info, or a decile boundary that happens to isolate a symbol). **Verdict: probably real but unconfirmed — needs a per-symbol concentration check and a score-timestamp audit before sizing.** The class-level WR of 46.1% (n=2,412) is the honest number; the 78.7% cell is a 7% slice of it.
- **90d expected P&L (1% risk, $100k):** If you had traded *only* the 169-trade cell at 1% risk ($1,000/trade), avg_pnl 1.63% of notional → ~$16.3/trade × 169 ≈ **$2,750 gross**, minus ~$0.50–$1.00/trade slippage+fees on $1k notional (~$170) → **≈ $2,500 net**. If you traded the *whole class* (2,412 closed) at 1% risk with the class's 46.1% WR and unknown avg R, expected P&L is **negative to flat** — do not size the class, size the cell.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — but the real fix is upstream: the HC gate never fires because `trust≥60` is unreachable for CRYPTO (all top cells are `trust=UNK`). Set `HC_TRUST_MIN_CRYPTO = 0` (or route UNK-trust through a separate "untrusted-but-scored" lane) so the 169-trade cell can actually reach the dashboard. **Do not lower `HC_SCORE_MIN` — the cell already scores S50 decile; the blocker is trust, not score.**
- **Confidence (1-5):** 3 — best evidence in the report, but single-cell, single-source, trust-UNK, and re-sliced three ways.

### FOREX
- **Real/noise verdict:** **Noise / leakage-suspect.** The `conf=C>=0.90 & dir=LONG & source=regime_terminal` cell (n=26, WR 92.3%, PF 16.96) **fails holdout** (`holdout_pass: false`, holdout_n=7, holdout_pf=99.0 — a PF of 99 on 7 trades is a division-by-tiny-loss artifact, not an edge). `wr_shrunk` collapses from 92.3% to 73.9% — the shrinkage is doing exactly its job of telling you the raw number is inflated. n=26 with 7 holdout trades is **not a sample**. The class-level WR is 50.34% (n=435) — a coin flip. This is the classic "high-confidence LONG in a trending regime" cell that will evaporate the moment the regime flips. **Verdict: noise. Do not trade.** The `regime_terminal` source name is itself a warning — terminal/regime-conditioned signals are the most common source of look-ahead in this codebase's history (cf. H-001 COT leakage).
- **90d expected P&L (1% risk, $100k):** **$0 recommended.** If forced: 26 trades × $1,000 × 0.68% avg = ~$177 gross, minus slippage on 26 FX round-trips (~$50) → **≈ $125**, with a confidence interval that includes −$500. Not worth the operational risk.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise it. FOREX passed_smart is 23,488/24,221 = **97% pass rate**. The gate is not gating. Raise `SMART_PICKS_MIN_SCORE_FOREX` until pass rate drops to ~10–15% (target ~2,500–3,500 picks). The current value is clearly near the floor of the score distribution.
- **Confidence (1-5):** 1 — fails holdout, n too small, shrinkage says inflated.

### EQUITY
- **Real/noise verdict:** **Leakage-suspect — flag as H-001 recurrence pattern.** The `conf=C<0.60 & fam=mean_reversion & source=alpha_engine` cell (n=63, WR 98.4%, PF **175.3**) is not a real edge. A PF of 175 means average win / average loss ≈ 175:1 — that is only possible if losses are near-zero or wins are near-infinite, i.e. **the P&L accounting is broken** (likely: winners marked at a stale/limit price, losers never marked, or a single symbol with a split/adjustment error). `holdout_pf: 99.0` on 30 trades confirms the artifact. `wr_shrunk` 86.75% is still absurd for mean-reversion at conf<0.60 — low-confidence mean-reversion should be the *worst* cell, not the best. This is the signature of **look-ahead in the confidence feature** (conf computed after the fact) or **survivorship in the closed-trade set** (only 130 of 5,620 opened trades closed — a 2.3% close rate means the "closed" set is a biased subsample). **Verdict: leakage. Do not trade. Investigate `alpha_engine` mean_reversion P&L attribution before anything else.**
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** The reported PF implies ~$1,577/trade × 63 = ~$99k gross, which is obviously fictional. Realistic expectation given 2.3% close rate and unknown open-trade mark-to-market: **unknown, likely negative.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` is not the issue (232/5,750 = 4% pass — the gate *is* working here). The issue is **`opened` (5,620) ≫ `passed_smart` (232)** — the scanner opens trades the gate rejected. Fix the *opening* path, not the gate: enforce `passed_smart` as a hard precondition for `opened` in `production_scanner.py`. Also audit `alpha_engine` mean_reversion close-price attribution.
- **Confidence (1-5):** 1 — PF 175 is a bug, not an edge.

### COMMODITY
- **Real/noise verdict:** **Noise.** Best cell `trust=UNK & dir=LONG & source=alpha_engine` (n=31, WR 58.1%, shrunk 54.9%, PF 1.93) **fails holdout** (`holdout_pass: false`, holdout PF 1.11, holdout_n=14) and **fails Bonferroni** (`bonferroni_pass: false`). n=31 is below the n≥20 threshold's spirit once you account for the number of cells tested. Class WR 62.8% on n=43 is a small-sample artifact. **Verdict: no edge.** Note the H-001 COT leakage history — COMMODITY has a documented leakage precedent, and `trust=UNK` + `alpha_engine` is the same shape.
- **90d expected P&L (1% risk, $100k):** **$0.** If forced: 31 × $1,000 × 0.69% = ~$214 gross, minus slippage (~$60) → **≈ $150**, CI includes negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — passed_smart is 3,678/6,173 = **60% pass rate**. Way too loose. Raise until pass rate ~10% (~600 picks). The gate is currently admitting the majority of scans.
- **Confidence (1-5):** 1 — fails holdout and Bonferroni.

### INDEX
- **Real/noise verdict:** **No edge — insufficient data.** n_closed=4. WR 25% on 4 trades is meaningless. `passed_smart` 1,601/1,978 = 81% pass rate — the gate is a pass-through. **Verdict: no edge, no sample.**
- **90d expected P&L (1% risk, $100k):** **$0** (n=4, no statistical basis).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise aggressively; 81% pass rate is the loosest gate in the system. Target ~10% pass (~200 picks).
- **Confidence (1-5):** 1 — n=4.

### ETF
- **Real/noise verdict:** **No edge — insufficient data.** n_closed=9, WR 11.1%. `passed_smart` 291/339 = 86% pass rate. **Verdict: no edge.**
- **90d expected P&L (1% risk, $100k):** **$0** (n=9).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise; 86% pass rate is not a gate.
- **Confidence (1-5):** 1 — n=9.

### FUTURES
- **Real/noise verdict:** **No edge — insufficient data.** n_closed=18, WR 38.9%. `passed_smart` 140/192 = 73% pass. **Verdict: no edge.** (Also note H-005: futures momentum anti-signal investigation FAILED — inversion doesn't fix it. Do not re-derive.)
- **90d expected P&L (1% risk, $100k):** **$0** (n=18).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise; 73% pass rate too loose.
- **Confidence (1-5):** 1 — n=18.

### BOND
- **Real/noise verdict:** **No edge — insufficient data.** n_closed=31, WR 38.7%. `passed_smart` 1/886 = **0.1% pass rate** — the gate is *over*-tight here (opposite problem). **Verdict: no edge, and the gate is mis-calibrated in the opposite direction.**
- **90d expected P&L (1% risk, $100k):** **$0** (n=31, WR<50%).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **lower** it. 0.1% pass rate means the floor is above the entire score distribution. Set to the 10th percentile of observed BOND scores (target ~10% pass, ~90 picks) so the class can be evaluated at all.
- **Confidence (1-5):** 1 — n=31, WR<50%.

### UNKNOWN
- **Real/noise verdict:** **No edge — insufficient data.** n_closed=3, WR 0%. `passed_smart` 138/1,367 = 10% pass. **Verdict: no edge.** The existence of an UNKNOWN class with 1,367 scans is itself a data-quality bug — these should be classified or dropped, not traded.
- **90d expected P&L (1% risk, $100k):** **$0** (n=3).
- **Gate change:** Not a gate — fix the classifier. Route UNKNOWN to a quarantine bucket, do not open.
- **Confidence (1-5):** 1 — n=3.

### MEME
- **Real/noise verdict:** **No edge — insufficient data.** n_closed=9, WR 33.3%. `passed_smart` 15/29 = 52% pass. **Verdict: no edge.**
- **90d expected P&L (1% risk, $100k):** **$0** (n=9).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise; 52% pass rate too loose for a class with 33% WR.
- **Confidence (1-5):** 1 — n=9.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — but only the single 169-trade cell, not the class.** It is the only cell in the report that (a) has n≥100, (b) survives a genuine train/holdout split with holdout PF > 2, (c) passes Bonferroni, and (d) has a plausible (not absurd) PF of 4.2. Size it at **0.5% risk per trade, not 1%**, until the per-symbol concentration check and score-timestamp audit clear — the `trust=UNK` + `score_dec=S50` combination is exactly the shape of a scoring artifact, and CRYPTO has no leakage precedent in the registry (unlike COMMODITY/EQUITY), which is mildly reassuring but not proof. Expected 90d P&L on the cell alone: **~$1,250–$2,500 net** at 0.5–1% risk. That is small in absolute terms — which is the honest answer: **there is no class in this report that justifies meaningful capital today.**

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): EQUITY.** The PF=175 cell is a leakage artifact (H-001 recurrence pattern — flag it in the registry as a potential leakage recurrence, do not cite it as an edge). But EQUITY is not kill-worthy — it has the second-best class-level WR (70.8% on n=130) and a working `passed_smart` gate (4% pass rate). The mutation is: (1) enforce `passed_smart` as a hard precondition for `opened` in `production_scanner.py` (currently 5,620 opened vs 232 passed — the gate is bypassed), (2) audit `alpha_engine` mean_reversion close-price attribution to kill the PF=175 artifact, (3) re-run the 90d funnel. If after mutation EQUITY still shows WR<55% on n≥100, then kill.

**Second demotion: FOREX.** 97% `passed_smart` pass rate means the gate is not gating; the only "edge" fails holdout. Mutate `SMART_PICKS_MIN_SCORE_FOREX` upward until pass rate ~10%, then re-evaluate. Do not kill yet — 435 closed trades is a real sample, it's just a coin-flip sample.

**Do not scale: COMMODITY, INDEX, ETF, FUTURES, BOND, UNKNOWN, MEME.** All have n<50 closed, all fail holdout or Bonferroni or both, and COMMODITY has a documented leakage precedent (H-001) with the same `trust=UNK & alpha_engine` shape as its current "best" cell. These are not edges; they are small samples.

**The single most important finding is not any cell — it is that `passed_high_conviction = 0` across all 10 classes.** The HC gate is unreachable. Whatever edge exists in CRYPTO is being surfaced by `passed_smart`, not by the HC gate the dashboard advertises. Fix the HC gate's `trust≥60` threshold (or add an UNK-trust lane) before claiming the dashboard has a "high conviction" tier at all.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. n=63 on mean_reversion cells with 98% WR and PF=175 is statistically impossible in live equity flow; violates every known distribution. Rejected as data artifact.
- 90d expected P&L (1% risk, $100k): $0 (edge does not exist).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 72
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise. All listed cells fail bonferroni and holdout; WR_z <1. No edge survives.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 4

**### INDEX**
- Real/noise verdict: No data. n=4 closed trades total.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. High-PF cells have holdout n=7 and holdout_pass=false; classic small-sample blow-up. No proven edge.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_MIN_CONF_FOREX = 0.88
- Confidence (1-5): 4

**### CRYPTO**
- Real/noise verdict: Real. n=169, WR_shrunk=75.66, PF=4.2, holdout_pass=true, bonferroni_pass=true, wr_z=7.46. Only cell set that survives all filters.
- 90d expected P&L (1% risk, $100k): ~$4,800 (169 trades × 1.63% avg edge × 1% risk sizing, 0.15% slippage, 0.08% commission).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 48
- Confidence (1-5): 4

**### FUTURES**
- Real/noise verdict: No data. n=18 closed.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: No data. n=31 closed.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: No data. n=9 closed.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 75
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: No data. n=3 closed.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: No data. n=9 closed.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only surviving edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its reported cells are leakage recurrence and must be mutated before any further production exposure. All other classes carry zero actionable edge.
