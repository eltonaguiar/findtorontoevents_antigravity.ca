# Pick Funnel Swarm Verdict — 2026-10-30 04:08 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261030T040746Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Bottom line up front:** The funnel is broken in a specific, diagnosable way. The HC gate (`score>=80, conf>=0.75, trust>=60`) is **passing zero picks in every single asset class** — 0/0/0/0/0/0/0/0/0/0. That is not a filter, it's a wall. Meanwhile the "PROVEN" cells that survive are almost entirely **trust=UNK** (i.e., the trust dimension is unpopulated, so the trust>=60 gate is structurally impossible to satisfy). The two "real" edges (EQUITY mean_reversion, CRYPTO conf 0.75–0.80) are real *conditional on the data being clean*, but the EQUITY one is almost certainly a single-symbol / single-regime artifact and the CRYPTO one is a narrow, decaying slice. Everything else is noise or too thin to size.

---

### FUTURES
- Real/noise verdict: **Noise / no edge.** n_closed=16, WR 37.5%, no PROVEN cells, no best_pf cells. 187 opened vs 16 closed = 91% of positions never resolved in the window — the "opened" count is a booking artifact, not a tradeable sample. Nothing to size.
- 90d expected P&L (1% risk, $100k): **$0** (do not trade; n=16 is below any defensible threshold).
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **85** and add a hard `min_closed_history=50` precondition before a class is allowed to emit picks at all. Currently 147/203 pass "smart" on a class with 16 closed trades; that's a 92% pass rate on an unvalidated class.
- Confidence (1-5): **1**

### CRYPTO
- Real/noise verdict: **Real but narrow and decaying.** The PROVEN cell `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` has n=179, WR_shrunk 75.9%, PF 4.30, holdout PF 2.70 (holdout_pass=true), wr_z=7.70, bonferroni_pass=true. That is a genuine, out-of-sample-validated edge — **but** note the train→holdout PF decay (6.62 → 2.70) and that the cell is defined by a *narrow confidence band* (0.75–0.80), not "high confidence." The class-wide WR is 45.5% — so the edge is concentrated in ~7% of closed trades (179/2480). The `ml` cells you flagged: I see no `ml` source in the PROVEN list; the suspicious PF is the 4.30 above, which is high but *not* implausible for a 179-trade cell with holdout confirmation. **Flag:** the cell is `trust=UNK` — meaning the trust dimension is unpopulated, so this "edge" is really "alpha_engine + conf 0.75–0.80 + score_dec S50," and the trust label is cosmetic. If trust ever gets populated, this cell may fragment.
- 90d expected P&L (1% risk, $100k): **~$4,800** (see sizing below). 179 trades × 1% risk × avg_pnl 1.60% × WR 78.8% ≈ 179 × $1,000 × 0.016 × 0.788 ≈ $2,260 gross at 1% risk... let me redo: 1% risk = $1,000/trade. Avg win 1.60% of notional = $1,600; avg loss ≈ $1,000 (1R). 141 wins × $1,600 = $225,600; 38 losses × $1,000 = $38,000; net ≈ **$187,600** at 1% risk per trade on $100k. That is the *gross* edge; apply 15% slippage/fees haircut → **~$159,000**. This is the only class where the number is large enough to matter.
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower from current to 50** (the PROVEN cell is `score_dec=S50`, i.e., the edge lives at score decile 50, not at 80+). The HC gate at score>=80 is *excluding the edge*. Also add `HC_MIN_TRUST` fallback: when trust is UNK, substitute `conf>=0.75 AND score_dec in [45,55]` as the HC trigger.
- Confidence (1-5): **4**

### EQUITY
- Real/noise verdict: **Almost certainly leakage or single-symbol concentration.** The PROVEN cell `trust=UNK & conf=C<0.60 & fam=mean_reversion` has n=64, WR 98.4%, PF **174.9**, wr_z=7.75, holdout PF 99.0. A PF of 175 with 63/64 wins is not a strategy — it is a data artifact. Three red flags: (1) `conf=C<0.60` — the edge is in *low-confidence* picks, which is the opposite of what a real edge looks like; (2) PF 175 implies avg win / avg loss ≈ 175×, which for mean_reversion on equities is impossible without look-ahead (you're entering at the close of the bar you're measuring); (3) the three "different" PROVEN cells are the *same 64 trades* re-sliced by different dims — that's not three edges, it's one cell counted three times. **This is a leakage recurrence of the H-001 pattern** (look-ahead in the feature timestamp). Do not trade it.
- 90d expected P&L (1% risk, $100k): **$0** (do not trade; the number is fake).
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` — **raise to 70** and add a hard `min_conf=0.60` floor (the edge is currently in `conf<0.60`, which is the leakage signature). Also add a `max_pf_sanity=10.0` circuit breaker in `quality_gates.py` that quarantines any cell with PF>10 for manual review before it can be promoted to PROVEN.
- Confidence (1-5): **1** (on the edge being real; 5 on it being leakage)

### COMMODITY
- Real/noise verdict: **Noise.** No PROVEN cells. Best cell `trust=UNK & dir=LONG & source=alpha_engine` n=31, WR_shrunk 54.9%, PF 1.93, **holdout_pass=false** (holdout PF 1.07), bonferroni_pass=false. The train PF 3.37 → holdout 1.07 collapse is the classic overfit signature. This is consistent with the already-killed H-001 (COT leakage) and H-036 (inventory direction) — do not re-derive.
- 90d expected P&L (1% risk, $100k): **$0** (holdout fails; do not size).
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise to 80** and require `holdout_pass=true` before any commodity cell is eligible for the dashboard. Currently 3663/5958 (61%) pass "smart" on a class with 47 closed trades and zero proven edges.
- Confidence (1-5): **1**

### BOND
- Real/noise verdict: **No edge, and the funnel is inverted.** `passed_smart=0` but `opened=725` — meaning 725 bond positions were opened *without passing the smart gate*. That is a booking bug, not a strategy. n_closed=31, WR 38.7%, no PROVEN cells. Nothing here.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: `SMART_PICKS_MIN_SCORE_BOND` — the issue is not the threshold, it's that `passed_smart=0` yet `opened=725`. Fix the booking path so `opened ⊆ passed_smart`. Set `SMART_PICKS_MIN_SCORE_BOND = 60` and **block opening** if not passed.
- Confidence (1-5): **1**

### FOREX
- Real/noise verdict: **Noise, and the "best" cell is a small-sample mirage.** `trust=UNK & conf=C>=0.90 & dir=LONG` n=26, WR 92.3%, PF 16.96 — but **train_n=2, train_pf=0.0, holdout_pass=false**. A cell with 2 training trades and a 24-trade holdout is not a validated edge; it's a single regime (likely one currency pair in one directional move). The class-wide WR is 44.3% on 485 decisive trades — i.e., the class loses money. The `consensus` source you flagged: I see `regime_terminal` as the source in the best cell, not `consensus`; either way, n=26 with train_n=2 is disqualifying. **Flag as potential leakage recurrence** (H-001 pattern: feature timestamp vs. entry timestamp).
- 90d expected P&L (1% risk, $100k): **$0** (holdout fails; n=26 with train_n=2 is not sizeable).
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` — **raise to 75** and add `min_train_n=20` precondition. Currently 23784/24562 (97%) pass "smart" — the gate is doing nothing. A 97% pass rate is not a gate.
- Confidence (1-5): **1**

### INDEX
- Real/noise verdict: **Noise / too thin.** n_closed=4, WR 25%. No PROVEN cells. 1735 opened vs 4 closed — 99.8% unresolved. Not a tradeable sample.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` — **raise to 85** and add `min_closed_history=30`. 1379/1739 (79%) pass smart on 4 closed trades.
- Confidence (1-5): **1**

### MEME
- Real/noise verdict: **Noise / too thin.** n_closed=8, WR 25%. No PROVEN cells. 2/15 pass verified_alpha but 0 proven.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: `SMART_PICKS_MIN_SCORE_MEME` — **raise to 85** and require `min_closed_history=30`. 15/31 (48%) pass smart on 8 closed trades.
- Confidence (1-5): **1**

### ETF
- Real/noise verdict: **Noise / too thin.** n_closed=10, WR 20%. No PROVEN cells. 300/354 (85%) pass smart on 10 closed trades.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` — **raise to 85** and require `min_closed_history=30`.
- Confidence (1-5): **1**

### UNKNOWN
- Real/noise verdict: **Noise / data hygiene failure.** n_closed=3, WR 0%. 1386 opened vs 3 closed. This class should not exist — it means the asset-class classifier is failing on 1389 scans. That's a data-quality bug, not a strategy.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: **Do not add a threshold — fix the classifier.** Route UNKNOWN to a quarantine queue; do not open positions. In `quality_gates.py`, add `if asset_class == "UNKNOWN": return False` at the top of the smart-picks gate.
- Confidence (1-5): **1**

---

## Sizing / slippage assumptions (for the CRYPTO number)
- Account: $100,000 notional. Risk per trade: 1% = $1,000.
- Position size = $1,000 / (entry − stop). Avg win 1.60% of notional, avg loss ≈ 1R = $1,000 (assumed stop discipline).
- Slippage/fees: 15% haircut on gross P&L (crypto taker fees + slippage on 179 trades).
- No compounding, no leverage beyond 1R, no correlation adjustment (the 179 trades are likely correlated in a few regimes — real-world P&L would be lower).
- **CRYPTO gross ≈ $187,600; net ≈ $159,000.** Treat this as an upper bound; the holdout PF decay (6.62→2.70) suggests the forward number is closer to the holdout, i.e., **~$60–80k** is the honest expectation.

## SYSTEM-WIDE conclusion

**Scale up TODAY: CRYPTO only.** It is the only class with a holdout-validated, bonferroni-passing, n≥100 cell. But scale *narrowly*: only `source=alpha_engine & conf∈[0.75,0.80] & score_dec=S50`, and only after fixing the HC gate so it stops excluding the edge (the current HC gate at score>=80 passes 0 picks — it is structurally incompatible with the only proven cell). Size at 0.5% risk, not 1%, until the holdout PF stabilizes above 2.0 for a full quarter.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill):**
- **EQUITY** — demote to "quarantine / leakage review." The PF=175 cell is a leakage recurrence of H-001. Do not kill the class; mutate the feature-timestamp axis and re-run. If the edge survives timestamp correction, it's real; if it collapses to PF<2, kill.
- **FOREX** — demote to "paper only." 97% smart-pass rate on a 44% WR class is a gate that isn't gating. Mutate the threshold axis (raise to 75) and the sample-size axis (min_train_n=20) before any real money.
- **COMMODITY** — demote to "paper only." Holdout fails; consistent with already-killed H-001/H-036. Mutate the holdout-requirement axis.
- **FUTURES, BOND, INDEX, MEME, ETF, UNKNOWN** — **kill the funnel, not the class.** These have <50 closed trades and/or booking bugs (BOND: 725 opened / 0 passed smart). The correct action is to stop emitting picks until `min_closed_history=50` is met, then re-evaluate. Do not "mutate" a class with n=4.

**The single highest-leverage fix:** the HC gate (`hc_filter.js`: `score>=80, conf>=0.75, trust>=60`) is passing **zero picks across all 10 classes**. That is the loudest signal in this dataset. Either trust is never populated (so `trust>=60` is unsatisfiable) or the score distribution never reaches 80. Fix the trust-population bug first — until then, the HC funnel is a null set and every "passed_high_conviction: 0" is a data bug, not a strategy verdict.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### FUTURES
- Real/noise verdict: No edge. n=16 total closed; zero proven cells. All metrics are noise.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: None (no signal to amplify).
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real but overstated. n=179 cell shows decent holdout stability and PF=4.3 after shrinkage; not obvious single-symbol leakage. Other cells are weaker.
- 90d expected P&L (1% risk, $100k): ~$2,800 (assuming 1.6% avg win, 179 trades, 1% risk, 0.2% slippage per trade, net expectancy ~0.28R).
- Gate change: Raise `HC_MIN_CONF` in `hc_filter.js` from 0.75 to 0.78.
- Confidence (1-5): 3

### EQUITY
- Real/noise verdict: Sample-noise / leakage. n=64 with 98.44% WR and PF=174 is statistically impossible without data snooping, single-symbol concentration, or look-ahead. All three cells are variants of the same flawed mean_reversion bucket.
- 90d expected P&L (1% risk, $100k): -$4,200 (edge collapses out-of-sample; expect ~0.4R loss after slippage).
- Gate change: Set `SMART_PICKS_MIN_SCORE_EQUITY` = 0.92 (effectively disable current mean_reversion path).
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: No edge. n=47 total; best_pf cells fail Bonferroni and holdout. Matches previously rejected inventory/COT hypotheses.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: None.
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No edge. n=31 total; zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise. n=26 cells have train_n=2 and holdout_pass=false. High PF is an artifact of tiny samples.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: No edge. n=4 total.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge. n=8 total.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge. n=10 total.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge. n=3 total.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with any statistically credible cell that survives holdout). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL — its "proven" cells are leakage recurrence and must be mutated (or killed) before any further capital allocation. All other classes have no actionable edge.
