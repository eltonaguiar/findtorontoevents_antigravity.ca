# Pick Funnel Swarm Verdict — 2026-10-18 06:13 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261018T061331Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Read this first:** The funnel is broken in a way that makes most of the "PROVEN" cells untrustworthy. Look at the pass-through rates:

| Class | scanned | passed_smart | opened | closed | close_rate |
|---|---|---|---|---|---|
| EQUITY | 5,709 | 217 | **5,572** | 137 | 2.5% |
| FOREX | 24,059 | 23,181 | 22,732 | 1,327 | 5.8% |
| CRYPTO | 13,120 | 3,597 | 10,647 | 2,473 | 23% |
| INDEX | 1,835 | 1,491 | 1,830 | 5 | 0.3% |
| COMMODITY | 5,929 | 3,678 | 5,861 | 68 | 1.2% |

`opened` >> `passed_smart` in EQUITY (5,572 opened vs 217 passed). That means the "opened" counter is not gated by Smart_Picks at all — it's counting every scan. **The funnel is not a funnel.** Any cell-level edge computed on `closed` trades is being computed on a tiny, non-random survivor set (2.5% of EQUITY opens ever close). That is the single biggest statistical problem in this report, and it applies to every class.

Also: `passed_high_conviction = 0` for **every class**. The HC gate (score≥80, conf≥0.75, trust≥60) is dead — nothing in 90 days has cleared it. So the "PROVEN" cells below are *not* HC cells; they're post-hoc slices of the closed set. That's fine for research, but it means the dashboard is currently showing zero HC picks and the "edge" you're being asked to size is not what the dashboard is surfacing.

---

### CRYPTO
- **Real/noise verdict:** The single PROVEN cell is `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`, n=181, WR=74.6%, shrunk 72.1%, PF=3.82, holdout PF=3.10 (n=68), wr_z=6.6, Bonferroni pass. **This is the only cell in the entire report that survives a real holdout and a multiple-testing correction.** It is also the only cell where the three "different" PROVEN rows are literally the same 181 trades re-sliced (trust=UNK, dir=LONG, and the base cell are identical n/wins/PF — the dims are degenerate). So you have **one** edge, not three. Caveats: (i) `score_dec=S50` is a decile bucket — if S50 is the *top* decile of score, this is a score-threshold effect, not a confidence effect, and the conf band is incidental; (ii) `source=alpha_engine` — need to confirm this isn't a single strategy family wearing a source label; (iii) the 23% close rate means 77% of CRYPTO opens never resolve, so the 181 closed trades are a biased sample of the 10,647 opens. **Verdict: probably real, but the effect size is inflated by survivorship in the close pipeline.** Treat PF=3.8 as an upper bound; PF≈2.0–2.5 is the honest planning number.
  - The `ml` cell you flagged is **not in this data** — there is no `source=ml` cell in the CRYPTO top edges. If a prior report cited one, it's not here. The suspiciously-high PF in this class is the 3.82 above, and it's suspicious mainly because of the close-rate bias, not leakage per se.
- **90d expected P&L (1% risk, $100k):** 181 trades × $1,000 risk × (WR×avg_win − LR×avg_loss). With PF=3.82 and WR=74.6%, avg_win/avg_loss ≈ 1.31. Per-trade EV ≈ 0.746×1.31 − 0.254×1.0 = **+0.72R** → $720/trade × 181 = **~$130k gross**. Haircut 40% for survivorship + slippage → **~$78k**. If you only trade the holdout-validated subset (n=68), scale to **~$29k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise to the S50 decile boundary (i.e., require score_dec ≥ S50) **and** add `conf >= 0.75` as a hard floor in `production_scanner.py`. Currently the scanner passes 3,597/13,120 (27%) — far too loose. Tightening to the proven cell's boundary should cut passes to ~1,500 and concentrate on the one real edge.
- **Confidence (1-5): 3** — real signal, but survivorship-inflated and single-cell.

---

### EQUITY
- **Real/noise verdict:** `trust=UNK & fam=mean_reversion & score_dec=S40`, n=65, WR=98.46%, shrunk 87.1%, **PF=233**, holdout PF=99 (n=26), wr_z=7.8, Bonferroni pass. **PF=233 is not a real edge — it is a data artifact.** A PF of 233 means average win is 233× average loss on 65 trades with 64 wins. That is the signature of (a) a stop-loss that is never hit because the "loss" is a tiny time-exit, (b) P&L recorded in a unit that isn't risk-normalized, or (c) a single symbol with a monotonic price path. The three "different" PROVEN rows are again the same 65 trades (trust=UNK, conf<0.60, dir=LONG all identical). **This is leakage or a P&L-accounting bug, not an edge.** Do not size it. The 98.46% WR on mean-reversion LONG with conf<0.60 is exactly the profile of a look-ahead in the entry timestamp or a fill-at-close assumption. Flag for the harness team before any capital.
- **90d expected P&L (1% risk, $100k):** **$0 — do not trade.** If forced to model the reported numbers: 65 × $1,000 × (0.985×233 − 0.015×1) ≈ $14.9M, which is obviously absurd and confirms the artifact.
- **Gate change:** Do not change a gate to *capture* this — change a gate to *block* it. In `quality_gates.py`, add a sanity cap: reject any cell/strategy whose realized PF > 20 over n≥20 until manually reviewed. Separately, `SMART_PICKS_MIN_SCORE_EQUITY` should be raised — 217/5,709 (3.8%) pass rate is fine, but 5,572 opens vs 217 passes means the gate isn't wired to `opened`. Fix the wiring first.
- **Confidence (1-5): 1** — artifact.

---

### FOREX
- **Real/noise verdict:** `top_edges_proven` is **empty** — nothing passes the PROVEN bar. The best PF cell (`trust=UNK & fam=regime & dir=LONG`, n=31, WR=77.4%, PF=4.08) **fails holdout** (train_pf=0.0 on n=5, holdout_pf=9.49 on n=26) and **fails Bonferroni**. That train/holdout split is the classic small-n overfit: 5 training trades, 26 holdout trades, and the "edge" only exists in the holdout. This is noise. The class-level WR is 42.45% on 530 decisive — **below breakeven for typical FX R:R**. The `consensus` cell you flagged isn't in this data; the suspicious cell is `regime_terminal`, and it's suspicious because of the 5/26 split, not because of a high PF per se.
- **90d expected P&L (1% risk, $100k):** **Negative.** 530 decisive × $1,000 × (0.4245×avg_win − 0.5755×avg_loss). At PF≈0.85 (implied by 42% WR and typical FX R:R), EV ≈ **−$15k to −$25k** on the decisive subset. Do not trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — currently 23,181/24,059 (96%) pass. That is not a gate. Raise to the top decile of score (roughly the S90 boundary) to cut passes to ~2,400, and add a hard `n>=30` requirement before a cell can be promoted to PROVEN. The 96% pass rate is the single worst gate in the system.
- **Confidence (1-5): 1** — no edge; gate is non-functional.

---

### COMMODITY
- **Real/noise verdict:** `top_edges_proven` empty. Best cell `trust=UNK & rr=RR>=2.0 & source=alpha_engine`, n=20, WR=75%, shrunk 62.5%, PF=5.28, holdout PF=3.76 (n=10), **but Bonferroni fail** and wr_z=2.24 (barely 2σ). n=20 with a 10/10 train/holdout split is too thin to call. **Also note H-001 and H-036 are both COMMODITY kills** — the class has a documented history of look-ahead (COT) and harness-rejected inventory signals. This cell smells like the same family: `source=alpha_engine` + high R:R + trust=UNK is exactly the profile that got killed before. **Treat as potential leakage recurrence, not an edge.**
- **90d expected P&L (1% risk, $100k):** **$0 — do not trade.** If the cell were real: 20 × $1,000 × (0.75×5.28 − 0.25×1) ≈ $74k, but n=20 and Bonferroni-fail means the honest estimate is $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — 3,678/5,929 (62%) pass is too loose, but the bigger issue is the class has no validated edge. Per MUTATION_THREE_AXIS_PROTOCOL, **mutate before kill**: tighten to top-quartile score and require `rr >= 2.0` as a hard floor, then re-run the 90d cell analysis. If it still fails Bonferroni, demote.
- **Confidence (1-5): 2** — thin, Bonferroni-fail, prior kill history.

---

### INDEX
- **Real/noise verdict:** n_closed=5. **No edge, no sample.** 1,491/1,835 pass Smart (81%) and 1,830 open but only 5 close — the close pipeline is essentially not running for INDEX. WR 20% on 5 trades is meaningless.
- **90d expected P&L (1% risk, $100k):** **$0 — cannot size n=5.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — 81% pass rate is not a gate. Raise to top-decile score. But the real fix is the close pipeline, not the gate.
- **Confidence (1-5): 1** — no data.

---

### ETF
- **Real/noise verdict:** n_closed=9, WR 22%. **No edge.** 303/353 (86%) pass Smart — gate is non-functional.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to top-decile; 86% pass is the second-worst gate after FOREX.
- **Confidence (1-5): 1.**

---

### BOND
- **Real/noise verdict:** n_closed=33, WR 39.4%, no PROVEN cells. 2/578 pass Smart (0.3%) — gate is *too tight* here, opposite problem. The 545 opens vs 2 passes again shows `opened` isn't gated.
- **90d expected P&L (1% risk, $100k):** **Negative** at 39% WR. **$0 — do not trade.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — 0.3% pass is starving the class. *Lower* to the median score to get a tradeable sample, then re-evaluate. This is the one class where the gate change is loosening, not tightening.
- **Confidence (1-5): 1.**

---

### FUTURES
- **Real/noise verdict:** n_closed=15, no PROVEN cells, best_pf_overall empty. **No edge.** H-005 already killed futures momentum. 149/200 (75%) pass Smart — non-functional gate.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to top-quartile; 75% pass is too loose.
- **Confidence (1-5): 1.**

---

### MEME
- **Real/noise verdict:** n_closed=7, WR 14%. **No edge, no sample.** 13/29 pass Smart.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to top-quartile, but honestly this class should be demoted per protocol.
- **Confidence (1-5): 1.**

---

### UNKNOWN
- **Real/noise verdict:** n_closed=3, WR 0%. **No edge.** 154/1,433 pass Smart. The existence of an UNKNOWN class with 1,433 scans is itself a data-quality bug — these should be classified or dropped before scoring.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** Not a score gate — fix the classifier so UNKNOWN doesn't reach the scanner. In `production_scanner.py`, drop `asset_class == UNKNOWN` before scoring.
- **Confidence (1-5): 1.**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the one cell.**
The `conf=0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the only slice in the entire 90-day report that survives a holdout (PF 3.10 on n=68) and a Bonferroni correction (wr_z=6.6). Size it at **0.5% risk per trade, not 1%**, until the close-rate bias is quantified — the 23% close rate means the 181 closed trades are a biased sample of 10,647 opens, and the honest PF is probably 2.0–2.5, not 3.8. Expected 90d P&L at 0.5% risk: **~$39k** (half the 1% estimate). Do not scale the other CRYPTO cells — they're the same 181 trades re-sliced.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill): FOREX.**
It has the worst gate in the system (96% pass rate — not a gate), the largest scan volume (24,059), a sub-breakeven WR (42.45%), and its only "best" cell fails holdout and Bonferroni. Per the protocol, **mutate first**: raise `SMART_PICKS_MIN_SCORE_FOREX` to the top-decile boundary and add an `n>=30` promotion requirement, then re-run 90d. If it still shows no PROVEN cell, kill. Do not kill outright today — the protocol requires the mutation pass first.

**Second demotion candidate: EQUITY.** The PF=233 cell is an artifact, not an edge, and the `opened` counter (5,572) vs `passed_smart` (217) proves the gate isn't wired to the open path. Fix the wiring and add a PF>20 sanity cap before any EQUITY capital.

**Do not trade today:** EQUITY (artifact), FOREX (no edge), COMMODITY (Bonferroni-fail + prior kill history — flag as potential H-001/H-036 recurrence), INDEX/ETF/BOND/FUTURES/MEME/UNKNOWN (n too small or negative EV).

**The meta-finding:** `passed_high_conviction = 0` across all 10 classes in 90 days means the HC gate in `hc_filter.js` (score≥80, conf≥0.75, trust≥60) is either misconfigured or the trust dimension is never populated (every PROVEN cell is `trust=UNK`). Before any of the above matters, verify that `trust` is actually being computed — if every pick is UNK, the trust≥60 condition can never fire, and the HC gate is dead by construction. That is the highest-leverage fix in the entire system, and it's a one-line check, not a gate change.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real edge. n=181, WR_shrunk 72%, PF 3.8 with clean holdout + Bonferroni pass; alpha_engine conf band is stable.
- 90d expected P&L (1% risk, $100k): $2,650 (181 trades × ~1.47% avg edge after 0.15% slippage, 1% risk units).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Sample noise / leakage. PF=233 and 98% WR on n=65 mean_reversion is statistically impossible without single-symbol concentration or look-ahead; reject.
- 90d expected P&L (1% risk, $100k): -$1,400 (edge collapses out-of-sample; expect ~40% WR on fresh data).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 2

### FOREX
- Real/noise verdict: Noise. All candidate cells fail holdout and Bonferroni; n=31 with tiny train set.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 1

### COMMODITY
- Real/noise verdict: Noise. Best cells fail Bonferroni; n=20 too small and already flagged in prior COT leakage cases.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 55
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: No edge. n=15 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 60
- Confidence (1-5): 1

### MEME
- Real/noise verdict: No edge. n=7 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 70
- Confidence (1-5): 1

### BOND
- Real/noise verdict: No edge. n=33 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 55
- Confidence (1-5): 1

### ETF
- Real/noise verdict: No edge. n=9 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 60
- Confidence (1-5): 1

### INDEX
- Real/noise verdict: No edge. n=5 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 60
- Confidence (1-5): 1

### UNKNOWN
- Real/noise verdict: No edge. n=3 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 65
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-passed edge). Demote EQUITY first under MUTATION_THREE_AXIS_PROTOCOL (high suspicion of leakage + unrealistic metrics). All other classes have no actionable edge; do not increase allocation.
