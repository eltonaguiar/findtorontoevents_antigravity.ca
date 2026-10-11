# Pick Funnel Swarm Verdict — 2026-10-11 04:12 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261011T041205Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before per-class verdicts, three structural observations that color everything below:

1. **`passed_high_conviction = 0` across every class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** picks in 90 days. Either the gate is dead code, or the scoring pipeline never produces the joint condition. Either way, the "HIGH CONVICTION" funnel stage is currently a no-op and cannot be credited with any edge.
2. **`passed_verified_alpha` is near-zero everywhere except CRYPTO (1923).** So the "verified alpha" stage is effectively a CRYPTO-only filter. For every other class, the funnel is `scanned → passed_smart → opened` with no intermediate quality gate.
3. **`opened` >> `passed_smart` in several classes** (COMMODITY 6043 vs 3606; FOREX 22494 vs 22957 ≈ equal; EQUITY 5623 vs 233; BOND 531 vs 3; UNKNOWN 1395 vs 161; INDEX 1887 vs 1587). This means the "opened" counter is **not downstream of `passed_smart`** — it's counting a different population (likely all scanner emissions, not gated ones). Any P&L attribution that assumes "opened ⊆ passed_smart" is wrong. This is a measurement bug, not an edge.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** 77 decisive trades total. Best cell (`trust=UNK & rr>=2.0 & source=alpha_engine`) has n=23, `bonferroni_pass=false`, train_n=10. A PF of 6.97 on n=23 with a 10-trade train set is not an edge — it's three lucky trades. Note the registry already killed the COT hypothesis (H-001) for look-ahead leakage and H-036 for inventory direction. The `rr>=2.0` cell is plausibly a **survivorship artifact**: high-RR setups that didn't hit stop get marked as wins when the 90d window closes, inflating WR. No PROVEN cells. Do not trade.
- **90d expected P&L (1% risk, $100k):** ~$0. With 77 closed trades at 1% risk and WR 54.5% but unknown avg R, the honest answer is the sample is too small to size. If forced: 77 trades × 1% × $100k × (0.545×avg_win_R − 0.455×1R). Without avg_win_R the number is uncomputable; the `avg_pnl_pct=2.02` on the best cell implies ~+$1.5k gross, but that cell is n=23 and not Bonferroni-passing. **Report $0 as the defensible estimate.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise it until `passed_smart` drops below ~500 (currently 3606/6120 = 59% pass rate, which is not a filter). Target ~15% pass rate.
- **Confidence (1-5):** 1

### EQUITY
- **Real/noise verdict:** **LEAKAGE — DO NOT TRADE.** The `fam=mean_reversion & score_dec=S40` cell shows WR=98.48% (65/66), PF=218.6, holdout PF=99.0. This is not a real edge; it is a **marking artifact**. A 98% WR with PF>200 on a mean-reversion family is the signature of: (a) trades that never close within the window and get marked to entry, (b) a stop that is never touched because the "loss" branch is unreachable in the harness, or (c) `score_dec=S40` selecting a degenerate subset (e.g., one symbol, one day). The `trust=UNK` and `conf=C<0.60` co-occurrence is a tell — the cell is defined by *missing* metadata, which usually means a single legacy source. **Flag as leakage recurrence.** Also note H-009 and H-011 already killed the options-derived equity signals.
- **90d expected P&L (1% risk, $100k):** **$0.** The 68.2% headline WR on 151 trades is the only number with any signal, and even that is suspect given the leakage above. If the 68% is real and avg R ≈ 1.0, gross ≈ 151 × 1% × $100k × (0.68 − 0.32) ≈ **+$54k**, but I do not believe the 68% survives leakage correction. Report $0.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — currently passing 233/5774 = 4%, which is already tight. The problem is not the floor; it's that the *opened* counter (5623) is 24× the passed_smart counter. Fix the funnel wiring before touching the constant.
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** **NOISE, and the headline is worse than it looks.** 22,957/23,882 = 96% pass rate on `passed_smart` — the gate is not filtering. Decisive WR = 41.98% (225W / 311L) on 536 decisive of 1388 closed — meaning **852 trades (61%) are non-decisive**, which is itself a red flag (breakeven/timeout trades being excluded from WR). The `conf>=0.90 & fam=regime` cell has `train_pf=0.298` and `holdout_pf=14.149` — that is the **opposite** of a stable edge; it's a regime flip inside the window. `holdout_pass=false`, `bonferroni_pass=false`. The registry's H-035 (funding/settlement) was already killed for sign instability; this `regime` cell looks like the same disease. **No PROVEN cells.**
- **90d expected P&L (1% risk, $100k):** **Negative.** 536 decisive × 1% × $100k × (0.42 − 0.58) ≈ **−$86k** if avg R=1. Even at avg R=0.5 the loss is ~−$43k. This class is a **net loser** at current gates.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — must go from ~0 (96% pass) to a level that cuts `passed_smart` by ~90%. Also add a **decisive-rate floor**: reject any strategy family whose 90d decisive rate < 70%, because the 61% non-decisive rate is masking the true WR.
- **Confidence (1-5):** 4 (confident it's noise/losing)

### CRYPTO
- **Real/noise verdict:** **THE ONLY CLASS WITH A PLAUSIBLE EDGE — but verify the `ml`/`consensus` cells first.** The PROVEN cell `conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine` has n=174, WR_shrunk=70.6%, PF=3.46, **holdout_pass=true (holdout_n=46, holdout_pf=3.22)**, `wr_z=6.07`, `bonferroni_pass=true`. That is the only cell in the entire report that survives train/holdout + multiple-testing correction. The `trust=UNK` co-cell is the same population (n=175 vs 174 — one trade difference), so it's not independent confirmation. **Caveat:** the prompt flags CRYPTO `ml` and FOREX `consensus` cells as suspicious; the `ml` cell is not in the top-3 shown, but if it exists with PF>5 on small n, treat it as leakage until proven otherwise. The `alpha_engine` + `conf 0.75-0.80` + `S50` cell is narrow enough to be real but also narrow enough to be a single-strategy artifact — check symbol concentration before sizing.
- **90d expected P&L (1% risk, $100k):** Using the PROVEN cell only: 174 trades × 1% × $100k × (0.706 × avg_win_R − 0.294 × 1R). With `avg_pnl_pct=1.387` and PF=3.46, implied avg_win_R ≈ 1.39/0.706 ≈ 1.97R and avg_loss_R ≈ 1.0R → expectancy ≈ 0.706×1.97 − 0.294×1.0 = **+1.10R per trade**. 174 × 1% × $100k × 1.10 ≈ **+$191k gross**. Apply 30% haircut for slippage/funding/leakage uncertainty → **~$130k net**. This is the only class where I'd write a positive number.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** it slightly to admit more of the `conf 0.75-0.80 / S50 / alpha_engine` population, OR (better) add a **cell-whitelist gate**: only open CRYPTO trades matching the PROVEN cell signature. The current `passed_smart` = 3498/12955 = 27% is too loose; the edge lives in a ~1.3% slice (174/12955).
- **Confidence (1-5):** 3 (real signal, but narrow and needs symbol-concentration check)

### FUTURES
- **Real/noise verdict:** **NOISE.** n=14 closed. H-005 already killed the momentum inversion. Nothing to salvage.
- **90d expected P&L (1% risk, $100k):** ~$0 (14 trades, WR 35.7%, statistically meaningless).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to effectively disable until n≥100.
- **Confidence (1-5):** 5 (confident it's noise)

### ETF
- **Real/noise verdict:** **NOISE.** n=9. WR 22%. No cells.
- **90d expected P&L (1% risk, $100k):** ~$0.
- **Gate change:** Disable ETF picks until n≥100.
- **Confidence (1-5):** 5

### UNKNOWN
- **Real/noise verdict:** **NOISE + data-quality bug.** 1395 opened but only 161 passed_smart and 5 closed. The "UNKNOWN" class is a routing failure, not an asset class. 0% WR on 5 trades.
- **90d expected P&L (1% risk, $100k):** ~$0.
- **Gate change:** Fix the classifier that emits `UNKNOWN`; do not trade it.
- **Confidence (1-5):** 5

### BOND
- **Real/noise verdict:** **NOISE.** n=30, WR 43.3%. `passed_smart=3` but `opened=531` — the funnel is disconnected.
- **90d expected P&L (1% risk, $100k):** ~−$4k (30 trades × 1% × $100k × (0.433−0.567) ≈ −$4k).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to disable; fix opened/passed_smart wiring.
- **Confidence (1-5):** 4

### INDEX
- **Real/noise verdict:** **NOISE.** n=5 decisive (8 closed). WR 20%.
- **90d expected P&L (1% risk, $100k):** ~$0.
- **Gate change:** Disable until n≥100.
- **Confidence (1-5):** 5

### MEME
- **Real/noise verdict:** **NOISE.** n=4. Nothing.
- **90d expected P&L (1% risk, $100k):** ~$0.
- **Gate change:** Disable.
- **Confidence (1-5):** 5

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only the narrow PROVEN cell.**
The `conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine` cell is the only signal in the entire 90-day report that passes train/holdout split, Bonferroni correction, and has n>100. Size it at 0.5% risk (not 1%) until symbol concentration is verified, and cap total CRYPTO exposure at 2% of the $100k book. Expected 90d contribution: **~$65k–$130k** depending on slippage and whether the cell is one-symbol-concentrated.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.**
FOREX is the worst offender: 96% `passed_smart` pass rate (gate is dead), 61% non-decisive trades (WR is being flattered), and a net-negative decisive WR of 42%. Per the protocol, do **not** kill it outright — mutate one axis at a time:
- **Axis 1 (gate):** raise `SMART_PICKS_MIN_SCORE_FOREX` to cut `passed_smart` by 90%.
- **Axis 2 (decisive-rate floor):** reject families with <70% decisive rate.
- **Axis 3 (regime cell):** the `conf>=0.90 & fam=regime` cell has `train_pf=0.298` vs `holdout_pf=14.149` — that's a regime flip, not an edge. Mutate the regime definition or drop the family.

If after three mutation rounds FOREX still shows decisive WR < 50%, kill it.

**Also demote (but as a data-quality fix, not a strategy): EQUITY.** The 98% WR / PF=218 cell is almost certainly leakage (marking artifact or unreachable stop). Do not trade EQUITY until the harness is audited for the `mean_reversion & S40` cell. This is a **leakage recurrence** — flag it in `reports/hypothesis_registry.json` as a new entry (H-0XX) referencing the H-001 COT leakage pattern.

**Structural fixes required before any of this is trustworthy:**
1. `passed_high_conviction = 0` everywhere → the HC gate is dead code. Either fix `hc_filter.js` or remove the stage from the funnel.
2. `opened` > `passed_smart` in 6 of 10 classes → the funnel counters are not wired in series. Fix before any P&L attribution.
3. `passed_verified_alpha` is CRYPTO-only → either extend to other classes or stop reporting it as a funnel stage.

**Bottom line:** one real edge (CRYPTO, narrow), one class to mutate-then-kill (FOREX), one leakage recurrence to investigate (EQUITY), and seven classes that are statistically indistinguishable from noise. Do not invent edges for the other seven.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real edge (n=175, WR_shrunk 70%, PF 3.45, holdout_pass + bonferroni_pass both true; no obvious single-symbol or leakage flags in the reported cell).
- 90d expected P&L (1% risk, $100k): $4,850 (175 trades × 1% risk × 1.38% avg win expectancy after 0.15% slippage; 73% WR).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Sample-noise / leakage (98.5% WR on n=66 with PF=218 is statistically impossible without data bug or single-symbol concentration).
- 90d expected P&L (1% risk, $100k): $0 (edge is falsified by implausible metrics; do not trade).
- Gate change: hc_filter.js: MIN_TRUST = 70
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise (no proven cells; best_pf_overall failed bonferroni).
- 90d expected P&L (1% risk, $100k): -$1,120 (actual 77 closed trades at observed 54.5% WR).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (no proven cells; best_pf_overall failed holdout).
- 90d expected P&L (1% risk, $100k): -$3,450 (actual 536 decisive trades at 42% WR).
- Gate change: hc_filter.js: MIN_CONF = 0.85
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge (n=14 too small, no proven cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 60
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge (n=9 too small, no proven cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 55
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge (n=30 too small, no proven cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 55
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge (n=5 too small, no proven cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 55
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge (n=5 too small, no proven cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 55
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge (n=4 too small, no proven cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 55
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-passed edge). Demote EQUITY, FOREX, COMMODITY, and all low-n classes per MUTATION_THREE_AXIS_PROTOCOL.md (no proven cells after 90d).
