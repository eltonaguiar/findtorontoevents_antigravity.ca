# Pick Funnel Swarm Verdict — 2026-10-28 04:08 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261028T040757Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` across every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** picks in 90 days. The dashboard's "HIGH CONVICTION" tab is empty. That is the single biggest finding in this dataset.
2. **`opened` >> `passed_smart` in most classes** (CRYPTO 10,475 opened vs 3,639 smart; FOREX 23,267 vs 23,770; EQUITY 5,680 vs 234). The funnel is not actually gating — most trades are being opened *outside* the smart-pick path. The "passed_smart" column is decorative for CRYPTO/EQUITY.
3. **`passed_verified_alpha` is near-zero everywhere** (CRYPTO 2,066 is the only non-trivial number; everything else is 0–3). The verified-alpha stage is effectively dead.

---

### CRYPTO
- **Real/noise verdict:** The "PROVEN" cell is **one cell reported three times** (same n=181, same wins=142, same PF=4.135 — it's just `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` with redundant dims tacked on). So the "top 3 edges" are actually **one edge**. That edge has holdout_pass=true (holdout PF 2.675, n=85) and bonferroni_pass=true, which is genuinely encouraging — but the cell is defined by `score_dec=S50`, i.e. **a single score decile**, and `conf=C0.75-0.80`, a **single 5-point confidence bucket**. That is a very narrow slice of a 12,909-scan universe. Two red flags: (i) `trust=UNK` on the winning cell means the trust gate is not contributing — the edge is riding on confidence+score alone; (ii) the class-level WR is 44.65% while this cell is 78.45% — a 34-point gap on 181 trades out of 2,419 closed. That is either a real narrow edge or a **selection artifact from the score-decile bucketing** (S50 = the 50th percentile decile; if scores are bimodal, S50 may be a "clean" cluster). The `ml` cell the prompt warns about is **not present** in this data — the only PROVEN cell is `alpha_engine`. So the "suspiciously high PF" concern applies to **PF=4.135 on n=181**, which is high but not impossible for a tight confidence+score slice. **Verdict: plausibly real but fragile — needs a second 90-day window before sizing up.** The 2,066 `passed_verified_alpha` with 0 `passed_high_conviction` is the real story: the HC gate is mis-calibrated for CRYPTO.
- **90d expected P&L (1% risk, $100k):** If we had traded **only** the 181-trade PROVEN cell at 1% risk ($1,000/trade), avg_pnl 1.5728% of notional → ~$15.73/trade × 181 = **~$2,847 gross**. Apply 0.10% round-trip slippage+fees on $100k notional = $100/trade × 181 = $18,100 cost — **the edge is destroyed by realistic costs at $100k notional per trade.** At $10k notional/trade (0.1% risk), gross ~$285, costs ~$1,810 — still negative. **The cell only works at very small notional or with sub-5bps costs.** Realistic estimate: **$0 to +$500** if costs are institutional-grade; **negative** at retail costs. Do not size this up on this evidence.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — but the real fix is the HC gate. In `hc_filter.js`, the `trust>=60` threshold is unreachable because the winning cell is `trust=UNK`. **Lower `HC_TRUST_MIN` from 60 to 0 (or route UNK through a separate path) and raise `HC_SCORE_MIN` from 80 to 85** to compensate. That would let the conf=0.75-0.80/S50 cell through while keeping the bar high on score.
- **Confidence (1-5): 2**

### COMMODITY
- **Real/noise verdict:** **No PROVEN edge.** Best PF overall is 1.934 on n=31, holdout_pass=**false** (holdout PF 1.161, n=16), bonferroni_pass=**false**. The class WR is 60.42% but on only **48 closed trades** — that is not a sample, it's an anecdote. The `trust=UNK & dir=LONG & source=alpha_engine` cell is the same shape as the falsified **H-001 (COT positioning)** and **H-036 (inventory direction)** — a direction-only LONG signal from alpha_engine. **Flag as potential leakage recurrence of H-001/H-036.** Do not trade.
- **90d expected P&L (1% risk, $100k):** On 48 closed trades at 1% risk, avg_pnl 0.6926% → ~$6.93/trade × 48 = **~$333 gross**, minus ~$100/trade costs × 48 = $4,800 → **net negative ~-$4,467.** Even ignoring costs, $333 on $100k over 90 days is noise. **$0 (do not deploy).**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise it hard. Currently 3,635 of 5,913 scans pass smart (61.5% pass rate — the gate is not gating). **Set to a value that cuts pass rate to <10%**, e.g. raise by 15–20 points from current. Also add a `MIN_CLOSED_FOR_PROMOTION = 200` guard so COMMODITY cannot be promoted on 48 trades.
- **Confidence (1-5): 1**

### FOREX
- **Real/noise verdict:** **No PROVEN edge.** The `trust=UNK & fam=regime & dir=LONG` cell has n=29, holdout_pass=**false** (train_n=3 — the "train" set is 3 trades, so the train/holdout split is meaningless), bonferroni_pass=**false**. The prompt warns about a FOREX `consensus` cell — **it is not in this data**; the only FOREX cell is `regime_terminal`. That cell has train_pf=0.0 on n=3, which means the "edge" is entirely in the holdout — a classic **single-window artifact**. Class WR 43.29% on 529 decisive trades is a **losing class**. 23,770 of 24,570 scans pass smart (96.7% pass rate — the gate is a no-op). This is the worst-gated class in the funnel.
- **90d expected P&L (1% risk, $100k):** Class-level: 529 decisive, WR 43.29%, so net negative. At 1% risk and ~0.5% avg move, expect **~-$2,000 to -$3,000** net of costs. The "best" cell (n=29) at 1% risk → ~$5.20/trade × 29 = $151 gross, costs ~$2,900 → **deeply negative.** **$0 (do not deploy; this class is bleeding).**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — the 96.7% pass rate is the bug. **Raise until pass rate <15%.** Also add a hard `MIN_TRAIN_N = 30` guard in the edge-promotion logic so cells with train_n=3 cannot be labeled "best."
- **Confidence (1-5): 1**

### EQUITY
- **Real/noise verdict:** **This is the one that looks like leakage.** The PROVEN cell `trust=UNK & conf=C<0.60 & fam=mean_reversion` has **WR 98.44% (63/64), PF 172.684, holdout PF 99.0**. A PF of 172 is not a trading edge — it is a **data artifact**. Possible causes: (i) mean-reversion exits booked at the reversion target with no adverse excursion modeled (look-ahead on the exit fill); (ii) single-symbol concentration — 64 trades could be one ticker's mean-reversion episodes; (iii) `conf=C<0.60` is the *lowest* confidence bucket, which is backwards — low-confidence picks should not have the highest WR. **This is almost certainly leakage or a fill-model bug.** The prompt's warning about "suspiciously high PF" applies here far more than to CRYPTO. **Do not trade. Investigate the exit-fill model before anything else.** Note also: 5,680 opened vs 234 passed_smart — the smart gate is rejecting 96% of EQUITY and the opened trades are bypassing it entirely.
- **90d expected P&L (1% risk, $100k):** If the PF=172 were real, 64 trades × 1.5291% × $1,000 = **~$979 gross** — trivially small because n is small. But it is **not real**; expected realized P&L is **unknown and likely negative** once the fill bug is fixed. **$0 (do not deploy until leakage audit passes).**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` is not the issue — the issue is the **exit-fill / P&L attribution model**. The gate change is to add a `MAX_PF_SANITY = 20` guard in the edge-promotion code that **rejects any cell with PF > 20 as a suspected data error** rather than promoting it to PROVEN. That single guard would have caught this.
- **Confidence (1-5): 1** (the edge is fake; confidence that it's fake is 5)

### ETF
- **Real/noise verdict:** **No edge.** n_closed=10, WR 20%. Nothing to say. Not a sample.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — irrelevant at n=10. The gate change is a **minimum-sample guard**: do not display ETF edge stats until n_closed >= 100.
- **Confidence (1-5): 1**

### BOND
- **Real/noise verdict:** **No edge.** n_closed=32, WR 37.5%, `passed_smart=0` (the smart gate rejects 100% of BOND — so the 682 opened trades are all bypassing it). No PROVEN cells.
- **90d expected P&L (1% risk, $100k):** **$0** (negative class).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — since passed_smart=0 already, the gate is working; the problem is `opened=682` bypassing it. Fix the **opened-path** to respect the smart gate, not the threshold.
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict:** **No edge, and a data-hygiene problem.** 1,389 scanned, 1,386 opened, 3 closed, 0 wins. The `UNKNOWN` class is a **classification failure** — 1,386 trades opened with no asset class. This is not a strategy, it's a routing bug.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** Not a threshold — add a **hard reject in `production_scanner.py`**: if `asset_class == UNKNOWN`, do not open. Route to a quarantine queue.
- **Confidence (1-5): 1**

### FUTURES
- **Real/noise verdict:** **No edge.** n_closed=16, WR 43.75%. `passed_verified_alpha=1`. The falsified **H-005 (futures_momentum_anti_signal)** is directly relevant — do not re-derive momentum inversion here.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to cut the 147/200 (73.5%) pass rate. But at n=16 closed, the real fix is the minimum-sample guard.
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict:** **No edge.** n_closed=4, WR 25%. 1,381 of 1,744 pass smart (79% pass rate — gate is a no-op).
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to cut pass rate below 20%.
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict:** **No edge.** n_closed=8, WR 25%. `passed_verified_alpha=2` on 29 scans — the only class where verified-alpha is non-trivial relative to scan count, but n=8 closed is nothing.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — irrelevant at this n. Minimum-sample guard.
- **Confidence (1-5): 1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: NONE.** There is not a single class in this dataset where the evidence supports deploying real capital at $100k notional. The closest candidate is **CRYPTO's `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell** — it has holdout_pass=true, bonferroni_pass=true, and a plausible (not absurd) PF of 4.135 on n=181. But at $100k notional per trade, realistic slippage+fees (~$100/trade) exceed the ~$15.73/trade gross edge, so it is **only viable at small notional or institutional costs**. If you must deploy something, deploy **CRYPTO at $10k notional/trade (0.1% risk), not $100k**, and only after a second 90-day window confirms the cell. Expected P&L at that size: **~$285 gross, ~$1,810 costs → still negative.** So: **do not deploy.**

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

- **FOREX** — 96.7% smart-pass rate (gate is a no-op), class WR 43.29%, best cell has train_n=3. **Mutate the gate first** (`SMART_PICKS_MIN_SCORE_FOREX` up until pass rate <15%), then re-evaluate in 30 days. If still losing, kill.
- **EQUITY** — the PF=172 cell is a **leakage/fill-model bug**, not an edge. **Mutate the exit-fill model and add `MAX_PF_SANITY=20`**, then re-run. Do not kill the class until the bug is fixed and re-measured — the 70.68% class WR on 133 trades is actually the second-best class WR in the dataset and may be real once the fake cell is removed.
- **COMMODITY** — 48 closed trades, best cell holdout_pass=false, and the signal shape matches falsified H-001/H-036. **Mutate** by raising `SMART_PICKS_MIN_SCORE_COMMODITY` and adding a `MIN_CLOSED_FOR_PROMOTION=200` guard. If it cannot clear 200 closed trades in 90 days, it is not a tradeable class.

**The single most important fix, system-wide:** `passed_high_conviction = 0` in every class. The HC gate in `hc_filter.js` (`score>=80, conf>=0.75, trust>=60`) is unreachable because the winning cells are all `trust=UNK`. **Lower `HC_TRUST_MIN` from 60 to 0 and raise `HC_SCORE_MIN` from 80 to 85.** Until that is fixed, the dashboard's highest-conviction tab is structurally empty and the funnel's top stage is dead — which means every "PROVEN" label below it is being computed on a population that never reaches the top of the funnel. That is the bug to fix before any sizing decision.

**Brutal summary:** 1 of 10 classes (CRYPTO) has a cell that survives holdout+bonferroni, and even that cell is cost-negative at $100k notional. 1 class (EQUITY) has a cell that is almost certainly leakage. 8 classes have no edge at all. The funnel is not gating (pass rates 61–97% in the classes that matter), the HC gate is empty, and the verified-alpha stage is dead. **Do not deploy real money on this dataset.** Fix the HC gate, add the `MAX_PF_SANITY` and `MIN_CLOSED_FOR_PROMOTION` guards, and re-run in 30 days.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real edge. n=181, WR_shrunk=75.62, PF=4.135 with clean holdout_pass + bonferroni_pass. No obvious leakage flags in the reported cell.
- 90d expected P&L (1% risk, $100k): ~$8,400 (181 trades × $1k risk × 0.57 edge expectancy after 0.2% slippage).
- Gate change: `hc_filter.js` MIN_CONF = 0.72
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Sample-noise / leakage. PF=172 on n=64 is statistically impossible in live equity flow; single-symbol concentration or look-ahead almost certain.
- 90d expected P&L (1% risk, $100k): -$2,100 (overall WR 70% collapses under realistic slippage and position sizing).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. All “best_pf” cells fail holdout_pass and bonferroni_pass; n too low for claimed PF.
- 90d expected P&L (1% risk, $100k): -$4,800 (overall WR 43%).
- Gate change: `hc_filter.js` MIN_CONF = 0.80
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf cells fail holdout.
- 90d expected P&L (1% risk, $100k): $0 (edge does not exist).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_COMMODITY = 55
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: No edge. Zero proven cells, tiny n.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: No edge. n=10 closed.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `hc_filter.js` MIN_SCORE = 85
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: No edge. n=16 closed.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_FUTURES = 60
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: No edge. n=4 closed.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `hc_filter.js` MIN_CONF = 0.80
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: No edge. n=8 closed.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_MEME = 75
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: No edge. n=3 closed.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: `hc_filter.js` MIN_CONF = 0.80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-passed edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its metrics are incompatible with live execution and should be mutated or removed before any further capital allocation. All other classes have no actionable edge.
