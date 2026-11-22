# Pick Funnel Swarm Verdict — 2026-11-22 04:41 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261122T044128Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

## Pre-flight sanity checks (read this first)

Before per-class verdicts, three structural red flags invalidate most of the "PROVEN" cells:

1. **`passed_high_conviction = 0` across every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) never fires. Every "PROVEN" cell below is therefore *not* an HC pick — it's a Smart-pick or lower. The dashboard's headline "HC" funnel is empty; the edge analysis is being run on a population the HC gate rejects. That's a gate-calibration bug, not an edge.

2. **`passed_verified_alpha` is 0 for EQUITY/COMMODITY/INDEX/ETF/BOND/UNKNOWN/PREDICTION_MARKET**, yet the EQUITY "PROVEN" cell is `source=alpha_engine`. Either the verified-alpha counter is broken, or the source label is being applied to non-verified picks. Either way, the EQUITY edge is **unverified by the pipeline's own definition**.

3. **`opened` >> `passed_smart`** in every class (e.g. EQUITY 5781 opened vs 226 passed_smart; FOREX 25923 vs 26719 — ok; CRYPTO 9664 vs 4057). The funnel is leaking: picks are being opened that never passed the Smart gate. The "edge" cells are computed on the *opened* population, not the *passed* population. This is the single biggest integrity issue in the dataset.

4. **`closed` << `opened`** everywhere (EQUITY 116/5781 = 2%; FOREX 1377/25923 = 5%; CRYPTO 2152/9664 = 22%). The 90-day window is dominated by open positions. WR is computed on the tiny closed subset — survivorship/selection bias is severe, especially for EQUITY and INDEX.

5. **`decisive` == `closed`** in every class. No timeouts, no scratches, no breakeven. That means the "WR_decisive_only" is just WR — the label is cosmetic. Fine, but don't let it imply robustness.

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE-SUSPECT.** The three "PROVEN" cells are the *same 36 trades* re-sliced three ways (`trust=UNK & rr>=2.0 & mean_reversion`, `rr>=2.0 & mean_reversion & LONG`, `rr>=2.0 & mean_reversion & alpha_engine`). n=36, 35 wins, PF=128. A PF of 128 on 36 trades is not an edge — it's a **data artifact**. Three independent tells: (i) `trust=UNK` on every winning cell means the trust gate is not filtering these; (ii) `passed_verified_alpha=0` yet `source=alpha_engine` — the source label is unverified; (iii) 35/36 wins with `avg_pnl_pct=1.59%` implies the 1 loss was ~-0.01% — that's a **stop-loss that never triggered / look-ahead exit**. This is the same failure mode as H-001 (COT look-ahead): a single dominant cell with implausible PF. Treat as **leakage recurrence**, not edge. The 73% headline WR is on 116 closed out of 5781 opened — 2% fill rate, survivorship-dominated.
- **90d expected P&L (1% risk, $100k): $0.** Do not size this. If forced to mark-to-model the 36-trade cell at 1% risk with a *realistic* 55% WR and 1.5 PF (i.e. de-leaked), expected P&L ≈ +$1,800 over 90d — but the confidence interval includes zero and the leakage flag dominates. **Recommend $0 deployed.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current (effectively ~0, since 5781 opened vs 226 passed) to **75**, AND add a hard `trust != UNK` requirement in `quality_gates.py` for EQUITY. The `trust=UNK` cells are where the fake edge lives.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict: NOISE.** `top_edges_proven` is empty — correct. The `best_pf_overall` cell (`trust=UNK & rr>=2.0 & LONG`, n=22, WR 59%, PF 3.03) **fails Bonferroni** (`bonferroni_pass: false`) and has `wr_z=0.85` — statistically indistinguishable from a 50% coin. n=22 is far below the n>=20 threshold's spirit. Also: `passed_smart=3730/5748 = 65%` pass rate is absurdly permissive — the Smart gate is not gating. And H-001 (COT leakage) and H-036 (inventory) both live in this class; the class has a documented history of fake edges. Do not trust the 60% headline WR on 45 closed.
- **90d expected P&L (1% risk, $100k): $0.** No proven cell. The 22-trade cell at 1% risk with 59% WR and PF 3.0 would model to ~+$2,200, but Bonferroni fail + n=22 + class history = do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70** (currently passing 65% of scans is not a gate). Also cap `rr>=2.0` cells to require `trust != UNK`.
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict: NOISE (n=1).** One closed trade, one win, 100% WR. This is not a statistic. `passed_smart=1542/2104 = 73%` pass rate — the gate is a rubber stamp. `opened=2103` vs `closed=1` — 0.05% fill. Nothing to evaluate.
- **90d expected P&L (1% risk, $100k): $0.** Cannot size n=1.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **75**; the 73% pass rate is the tell that the floor is too low. Also investigate why 2103 opened but only 1 closed (exit logic broken for INDEX).
- **Confidence (1-5): 1**

### FOREX
- **Real/noise verdict: NOISE / LEAKAGE-SUSPECT.** `top_edges_proven` is empty — correct, because the `best_pf_overall` cell (`trust=UNK & conf>=0.90 & regime`, n=39, WR 87%, PF 11.5) **fails holdout** (`holdout_pass: false`, holdout_n=3). A PF of 11.5 on n=39 with a 3-trade holdout is the textbook signature of **overfit-to-train + tiny holdout**. `wr_z=4.64` looks impressive but is driven by the same 39 trades; Bonferroni passes only because the cell count is small. The class-level WR is 50.31% on 479 decisive — a coin flip. The 87% cell is a **single-strategy (`regime_terminal`) concentration**; if that one strategy is a look-ahead (e.g. regime label computed with future data), the whole cell collapses. This is the FOREX analogue of H-001. **Do not deploy.**
- **90d expected P&L (1% risk, $100k): $0.** The 39-trade cell at 1% risk, 87% WR, PF 11.5 would model to ~+$8,000 — but holdout fail + n=3 holdout + single-strategy concentration = **do not size**. If you must, cap at 0.25% risk → ~+$2,000 expected, with a fat left tail.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **70** (currently 26719/27300 = 98% pass — the gate is effectively disabled). Also add a `holdout_n >= 20` requirement before any cell is labeled PROVEN in the edge report.
- **Confidence (1-5): 1**

### CRYPTO
- **Real/noise verdict: WEAK-BUT-PLAUSIBLE, with a leakage caveat.** This is the only class where the PROVEN cell has: n=192 (adequate), `wr_shrunk=62.7%` (shrunk, not raw), `pf=1.80` (believable, not 128), `train_pf=1.64` vs `holdout_pf=2.08` (holdout *better* than train — no overfit signature), `holdout_n=84` (real holdout), `wr_z=3.90`, `bonferroni_pass=true`. The three cells are again the same 192 trades re-sliced (`trust=UNK & conf=0.75-0.80 & alpha_engine`, `conf=0.75-0.80 & LONG & alpha_engine`, `trust=UNK & conf=0.75-0.80 & LONG & alpha_engine`) — so it's **one edge, not three**. The edge is: **alpha_engine LONG, confidence 0.75-0.80, trust=UNK**. The `trust=UNK` is a concern (the trust gate isn't filtering), but the holdout behavior is the strongest evidence in the entire dataset. **Caveat:** the user flagged "CRYPTO ml cells look suspiciously high" — the cells shown are *not* ml, they're `alpha_engine`; if there's a separate `ml` cell with PF>10, it's not in this JSON and should be treated as leakage until proven otherwise. The 44.6% class-level WR is dragged down by the 1180 losses in the non-edge population — the edge is a *slice*, not the class.
- **90d expected P&L (1% risk, $100k): +$3,400 to +$4,200.** Sizing: 1% risk = $1,000/trade; 192 trades; edge WR 62.7% shrunk, avg win ~1.0R, avg loss ~0.6R (PF 1.80 implies avg_win/avg_loss ≈ 1.8 × (1-WR)/WR ≈ 1.07). Expected R/trade ≈ 0.627×1.07 − 0.373×1.0 ≈ +0.30R. 192 × 0.30 × $1,000 = **+$57,600 gross** — but that's if every trade is sized at full 1% and fills at mid. Apply: (i) 0.5% slippage on entry+exit (≈0.1R/trade drag → −$19,200), (ii) 60% of the 192 are actually fillable at the stated conf band (rest are stale) → scale to 115 trades → **+$34,500 gross, −$11,500 slippage → +$23,000 net**. Then apply a 50% haircut for `trust=UNK` uncertainty and the fact that `passed_high_conviction=0` means the HC gate disagrees → **+$11,500 net expected, 90d**. Round to **+$10,000–$12,000**. This is the only class where I'd put a non-zero number.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** from current to **72** (to let more of the 0.75-0.80 conf band through, since that's where the edge lives), AND in `hc_filter.js` change `HC_MIN_CONF` from **0.75 to 0.72** so the HC gate actually fires on this band (currently 0 HC picks — the gate is mis-calibrated above the edge). Also add `trust=UNK` → `trust=MEDIUM` promotion path so the edge isn't stuck in UNK.
- **Confidence (1-5): 3**

### ETF
- **Real/noise verdict: NOISE (n=10).** 3W/7L, 30% WR, no proven cells. `passed_smart=266/300 = 89%` pass rate — gate disabled. Nothing here.
- **90d expected P&L (1% risk, $100k): $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **75**; 89% pass rate is the tell.
- **Confidence (1-5): 1**

### BOND
- **Real/noise verdict: NOISE (n=31, 38.7% WR).** `passed_smart=1/1226 = 0.08%` pass rate — the gate is *too tight* here (opposite problem), yet 1195 still opened. The funnel is broken: picks open that the Smart gate rejects. No proven cells. 38.7% WR is a losing class.
- **90d expected P&L (1% risk, $100k): $0** (negative edge — do not deploy).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **lower** to **55** (from effectively ~90, given 0.08% pass) so the gate actually admits the class, OR **kill the class** per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill: first try lowering the floor and re-measuring; if WR stays <45% at n>=50, kill).
- **Confidence (1-5): 1**

### PREDICTION_MARKET
- **Real/noise verdict: NO DATA (n=0 closed).** 138 scanned, 11 passed_smart, 138 opened, 0 closed. The class is a black hole — nothing resolves. Cannot evaluate.
- **90d expected P&L (1% risk, $100k): $0** (no closed trades).
- **Gate change:** `SMART_PICKS_MIN_SCORE_PREDICTION_MARKET` — leave at current, but **fix the resolution pipeline** (0/138 closed is a data bug, not a gate issue). No gate change will help until trades resolve.
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict: NOISE (n=5, 0W/5L, 0% WR).** 1218 scanned, 102 passed_smart, 1213 opened, 5 closed, all losses. The `UNKNOWN` bucket is where mis-classified picks go to die. 0% WR on n=5 is not significant, but the 1213 opened vs 102 passed_smart is a **funnel integrity failure** — 1111 picks opened that never passed the Smart gate.
- **90d expected P&L (1% risk, $100k): $0** (negative).
- **Gate change:** Add a hard **`asset_class != UNKNOWN`** requirement in `quality_gates.py` before any pick can be opened. This is the single highest-leverage integrity fix in the dataset.
- **Confidence (1-5): 1**

### FUTURES
- **Real/noise verdict: NOISE (n=16, 37.5% WR).** No proven cells. H-005 (futures momentum anti-signal) already failed in this class. `passed_smart=107/152 = 70%` pass rate — gate permissive. 37.5% WR is a losing class.
- **90d expected P&L (1% risk, $100k): $0** (negative).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **75**; 70% pass rate is too loose. Per MUTATION_THREE_AXIS_PROTOCOL, this class is a **demote candidate** (H-005 already failed; WR 37.5% at n=16).
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict: NOISE (n=5, 40% WR).** 12 scanned, 4 passed_smart, 7 opened, 5 closed. `passed_verified_alpha=2` — interesting but n=5 is nothing. No proven cells.
- **90d expected P&L (1% risk, $100k): $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — leave at current; n too small to calibrate. Do not deploy.
- **Confidence (1-5): 1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the `alpha_engine LONG, conf 0.75-0.80` slice, at 0.5% risk (not 1%) until the `trust=UNK` issue is resolved.** It is the only cell in the entire dataset with: adequate n (192), shrunk WR (62.7%), believable PF (1.80), a real holdout (n=84) that *improved* on train, and Bonferroni pass. Expected 90d P&L at 1% risk ≈ **+$10,000–$12,000 net of slippage and a 50% UNK haircut**; at 0.5% risk ≈ **+$5,000–$6,000**. The gate change to make this actionable: lower `HC_MIN_CONF` in `hc_filter.js` from 0.75 to 0.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage. n=36 is tiny; WR_shrunk 80% and PF=128 are impossible without single-symbol concentration or look-ahead (train/holdout split shows 36.4→99 PF jump). Matches known rejected patterns.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact; real deployment would hit slippage/widening and collapse to ~45% WR).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 92
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise. n_closed=10; zero proven cells. No statistical signal.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 95
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real on the listed cells. n=192, WR_shrunk=62.74, PF=1.8 with holdout pass and bonferroni pass is the only credible result in the file. No obvious leakage.
- 90d expected P&L (1% risk, $100k): ~$2,800 (192 trades × 1% risk × 0.64% avg edge after 0.15% slippage/commissions).
- Gate change: HC_MIN_CONFIDENCE = 0.78
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise. n=39 cells show high PF but holdout fails (3 trades); bonferroni pass is meaningless on tiny holdout. Matches rejected regime/consensus leakage patterns.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FOREX = 88
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise. n=22 cells have WR_shrunk=54.76, bonferroni fails, and known COT/inventory leakage history.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 90
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise. n_closed=5; zero cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise. n_closed=16; zero cells. Matches rejected futures momentum hypothesis.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 92
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise. n_closed=5; zero cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise. n_closed=31; zero cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 95
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise. n_closed=1; zero cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 95
- Confidence (1-5): 5

### SYSTEM-WIDE
Scale CRYPTO today (only cell with credible n + holdout pass). Demote EQUITY and FOREX per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the alpha_engine scoring path before any further live exposure). All other classes have no deployable edge.
