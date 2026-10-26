# Pick Funnel Swarm Verdict — 2026-10-26 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261026T041130Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is *never* firing. Either the trust dimension is capped below 60 for everything (note every "proven" cell is `trust=UNK`), or the score/conf thresholds are unreachable. This is the single biggest finding — the funnel's top tier is dead.
2. **`opened` ≈ `scanned` in every class** (e.g. FOREX 23,418 opened of 24,724 scanned = 94.7%). The "Smart" gate is not filtering. `passed_smart` is a rubber stamp.
3. **`closed` is a tiny fraction of `opened`** (FOREX 1,306/23,418 = 5.6%; COMMODITY 51/5,908 = 0.9%). The 90-day WRs are computed on a *survivorship-biased* sliver — trades that resolved fast. Long-dated open positions are invisible. Every WR below is suspect for this reason.

---

### COMMODITY
- **Real/noise verdict:** NO EDGE. Best cell (`trust=UNK & dir=LONG & source=alpha_engine`) is n=34, WR_shrunk 51.85%, PF 1.77 but `wr_z=0.34` and `bonferroni_pass=false` — indistinguishable from noise. Holdout PF 1.30 on n=17 is not evidence. The 56.86% headline WR is on n=51 closed of 5,908 opened — pure survivorship. This class also carries the H-001 COT leakage scar; the `trust=UNK & dir=LONG` signature is exactly the shape that leaked before. Treat as **no edge, possible leakage recurrence**.
- **90d expected P&L (1% risk, $100k):** $0 (do not trade). If forced at the point estimate: 34 trades × 1% × $100k × (0.5294×R_win − 0.4706×R_loss) with R≈1.5:1 → ~+$1.1k, but the CI straddles zero and holdout PF<1.5. **Expected value ≈ $0 ± $3k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise from current (effectively ~0, since 3,684/5,959 pass) to **75**, and add a hard `trust != UNK` requirement. Currently 62% of scanned pass Smart; that is not a gate.
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** NO EDGE — and the "best" cell is a **textbook leakage flag**. `trust=UNK & conf=C>=0.90 & dir=LONG` shows `train_n=4, train_pf=0.0, holdout_n=24, holdout_pf=99.0, holdout_pass=false`. A train PF of 0.0 with a holdout PF of 99 means the train/holdout split is degenerate — 4 training trades cannot validate anything, and the 24 "holdout" wins are almost certainly a single regime window (likely one currency pair, one directional move). `wr_z=3.78` is inflated by the tiny train set. The class-level 43.07% WR on 534 decisive of 23,418 opened is the honest number: **losing**. `passed_smart=23,886/24,724 = 96.6%` — the gate is off.
- **90d expected P&L (1% risk, $100k):** **Negative.** At 43.07% WR with typical 1:1 R, EV per trade ≈ −0.14% × $100k = −$140; × 534 decisive ≈ **−$75k** on the closed book. Even crediting the suspicious cell at face value (+$0.59% avg × 28 × $1k risk ≈ +$165) it's noise. **Expected: −$50k to −$75k.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **70** AND add `min_confidence=0.65` AND require `trust != UNK`. The 96.6% pass rate is the whole problem; this class is being spammed.
- **Confidence (1-5):** 1 (that there is no edge); the "best cell" is a leakage artifact, not an edge.

### CRYPTO
- **Real/noise verdict:** **The one cell that survives scrutiny — with caveats.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`: n=185, WR 78.92%, WR_shrunk 76.1%, PF 4.22, **train_pf 6.16 (n=100) / holdout_pf 2.68 (n=85), holdout_pass=true, wr_z=7.87, bonferroni_pass=true**. This is the only cell in the entire dataset with a genuine train/holdout split that both pass and a Bonferroni-corrected z that large. The PF 4.22 is high but *not* the 99.0 leakage signature — it degrades honestly from 6.16→2.68 out of sample, which is what a real edge looks like when it decays. **Caveat:** the cell is defined by `score_dec=S50` (a score decile) and `conf=0.75-0.80` — narrow bands that could be overfit to the 90d window. The `trust=UNK` prefix on the identical cell means trust is uninformative here. **Verdict: plausibly real, needs a 2nd out-of-sample window before scaling.** The class-level 44.81% WR is dragged down by the 2,234 non-edge trades; the edge is concentrated in ~185 of 2,419 closed.
- **90d expected P&L (1% risk, $100k):** 185 trades × 1% × $100k × (0.7892×R_win − 0.2108×R_loss). At PF 4.22 the implied R_win/R_loss ≈ 1.13 (since PF = WR×Rw/(LR×Rl) → 4.22 = 0.789×Rw/(0.211×Rl) → Rw/Rl ≈ 1.13). EV per trade ≈ 0.789×1.13 − 0.211×1.0 = 0.68% of risk = $680. × 185 = **+$126k**. Apply a 50% haircut for holdout decay (2.68 vs 6.16) and slippage: **~+$60k to +$90k**. This is the only class where the number is positive and defensible.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — currently 3,641/12,977 = 28% pass, which is *too loose* relative to the edge cell. Tighten to **isolate the edge**: set `SMART_PICKS_MIN_SCORE_CRYPTO = 55` AND add `SMART_PICKS_CONF_BAND_CRYPTO = (0.75, 0.80)` as a hard filter, plus require `source == 'alpha_engine'`. This routes capital to the one proven cell and starves the 2,234 noise trades.
- **Confidence (1-5):** 3 (real but narrow; needs 2nd window)

### BOND
- **Real/noise verdict:** NO EDGE. `passed_smart=0/683` — the gate correctly rejects everything, yet `opened=650` (95% of scanned). So the gate says "no" and the executor opens anyway. 39.39% WR on n=33. No proven cells. This is a **funnel integrity bug**, not a strategy.
- **90d expected P&L (1% risk, $100k):** Negative. 33 decisive × ~−0.2% EV ≈ **−$6k to −$10k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — the gate is already 0-pass; the fix is **downstream**: enforce `if passed_smart == 0: do not open`. Add `ENFORCE_SMART_GATE_BOND = True`. The bug is that `opened` ignores `passed_smart`.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** **LEAKAGE — do not trade.** The "proven" cell `trust=UNK & conf=C<0.60 & fam=mean_reversion` shows **WR 98.44% (63/64), PF 171.93, train_pf 92.4, holdout_pf 99.0**. A PF of 172 and a holdout PF of 99.0 is the exact signature of look-ahead bias or a mis-priced fill (e.g. entry at the close of the signal bar, or a limit fill that couldn't have happened). `wr_z=7.75` and `bonferroni_pass=true` are *consequences* of the leakage, not evidence against it — Bonferroni corrects for multiple comparisons, not for a broken P&L calculation. The class-level 70.15% WR on n=134 is also implausibly high for equity mean-reversion. **This is the H-001 pattern repeating in a new class.** Flag as leakage recurrence.
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** If the 98.44% were real, 64 trades × 1% × $100k × ~1.5% avg = ~+$96k, but it is not real. Realistic post-fix estimate: **−$5k to +$5k (no edge).**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — currently 227/5,799 = 3.9% pass (appropriately tight), but the leakage is *inside* the passed set. Add `EQUITY_REQUIRE_NEXT_BAR_ENTRY = True` and `EQUITY_MAX_PF_SANITY = 10.0` (reject any cell with PF>10 as a data bug). The gate change is a **sanity cap**, not a threshold.
- **Confidence (1-5):** 1 (that it's leakage); 0 that it's an edge.

### INDEX
- **Real/noise verdict:** NO EDGE / NO DATA. n=4 closed. 25% WR. `passed_smart=1,419/1,811` (78%) but `opened=1,807`. Nothing to evaluate.
- **90d expected P&L (1% risk, $100k):** **$0** (insufficient sample; do not trade).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **70**; currently 78% pass is not a gate. Also `MIN_CLOSED_FOR_EDGE_INDEX = 30` before any capital.
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** NO EDGE. n=16 closed, 43.75% WR. Carries the H-005 anti-signal scar. No proven cells.
- **90d expected P&L (1% risk, $100k):** Negative, ~**−$3k** on 16 trades.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **70**; 151/203 = 74% pass is not a gate.
- **Confidence (1-5):** 1

### ETF
- **Real/noise verdict:** NO EDGE. n=10 closed, 20% WR. `passed_smart=298/353` (84%). Nothing.
- **90d expected P&L (1% risk, $100k):** **−$2k** (n=10, noise).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **70**; 84% pass is not a gate.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** NO EDGE — and a **data-hygiene failure**. 1,411 scanned, 1,408 opened, 0 wins / 3 losses. `passed_smart=149/1,411` (10.6%) yet 1,408 opened. The `UNKNOWN` bucket is where unclassified symbols land; it should be **blocked at the gate**, not traded.
- **90d expected P&L (1% risk, $100k):** **−$3k** (n=3, all losses).
- **Gate change:** `BLOCK_UNKNOWN_ASSET_CLASS = True` in `quality_gates.py` — hard-reject any pick whose class resolves to UNKNOWN. This is the highest-ROI single line in the file.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** NO EDGE. n=8 closed, 25% WR. `passed_verified_alpha=2` but no proven cells. Too small to evaluate; do not trade.
- **90d expected P&L (1% risk, $100k):** **−$1k** (n=8, noise).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **75** and require `MIN_CLOSED_FOR_EDGE_MEME = 30` before capital.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only the one cell.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` is the only signal in the entire 90-day dataset with a genuine train/holdout split that both pass, a Bonferroni-corrected z of 7.87, and an honest out-of-sample PF decay (6.16→2.68) rather than a leakage spike. Deploy at **half-size** (0.5% risk/trade) for the first 30 days, cap at the 185-trade cell, and require a **second out-of-sample window** (e.g. the prior 90d) to confirm before going to full 1% sizing. Expected 90d P&L at full size: **+$60k to +$90k**; at half size: **+$30k to +$45k**.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): EQUITY.** The 98.44% WR / PF 172 cell is a leakage artifact, not an edge — but the *family* (`mean_reversion`, `conf<0.60`) may still be salvageable once the P&L calculation is fixed. Mutate the entry-timing axis (next-bar entry, no limit fills) and the sanity-cap axis (reject PF>10), re-run the 90d, and only kill if the mutated cell still fails holdout. Do **not** deploy EQUITY capital in the meantime.

**Second demotion: FOREX.** The `conf>=0.90 & dir=LONG` cell is a degenerate train/holdout split (train_n=4, train_pf=0.0) — mutate the split axis (require train_n>=30) and the trust axis (require `trust != UNK`) before any re-evaluation. The class-level 43% WR on 534 decisive is the honest number: it is losing money today.

**The meta-finding the user should act on first:** `passed_high_conviction = 0` across all 10 classes means the HC gate in `hc_filter.js` is **dead code** — it never fires, so the dashboard's "HIGH CONVICTION" badge is meaningless. Either the trust dimension never reaches 60 (every proven cell is `trust=UNK`, suggesting trust is unpopulated) or the score/conf thresholds are unreachable. **Fix the trust pipeline before trusting any HC label.** And `opened ≈ scanned` in every class means the Smart gate is not gating — the funnel is a straight pipe from scan to open. The single highest-leverage change in the whole system is not a threshold; it is **enforcing `passed_smart` at the executor** (the BOND bug: 0 passed, 650 opened). Until that is fixed, every WR above is a measurement of the executor, not the gate.

**Do not invent edges to look productive.** Of 10 classes, exactly **one cell** (CRYPTO) survives scrutiny. Two classes (EQUITY, FOREX) show leakage signatures. Six classes (COMMODITY, BOND, INDEX, FUTURES, ETF, UNKNOWN, MEME) have no edge and insufficient sample. That is the honest verdict.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: noise (98% WR on n=64 with conf<0.60 is leakage or single-symbol concentration; holdout PF=99 is impossible)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_CONF_EQUITY = 0.75
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: marginal real (n=185, WR_shrunk=76.1, PF=4.22, holdout_pass=true, bonferroni_pass=true; no obvious leakage flags)
- 90d expected P&L (1% risk, $100k): $3120 (185 trades × 1% risk × 1.581% avg_pnl, 0.2% slippage)
- Gate change: HC_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: noise (holdout_pass=false on all cells; train_n=4 vs holdout_n=24 shows instability)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_CONF_FOREX = 0.85
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: noise (all cells fail bonferroni or have WR_shrunk<52; matches known COT leakage patterns)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_COMMODITY = 70
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise (n=33 total, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_TRUST_BOND = 65
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise (n=4 total, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 60
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise (n=16 total, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_FUTURES = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise (n=10 total, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF_ETF = 0.80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise (n=8 total, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 55
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise (n=3 total, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_TRUST_UNKNOWN = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible edge after holdout). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL (mutate the mean_reversion + low-conf path before any further allocation). All other classes have zero actionable edge.
