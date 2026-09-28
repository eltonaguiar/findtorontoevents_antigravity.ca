# Pick Funnel Swarm Verdict — 2026-09-28 04:12 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260928T041145Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three cross-cutting observations that shape everything below:

1. **The funnel is broken upstream of HC.** `passed_high_conviction = 0` in *every* class. The `hc_filter.js` gate (score≥80, conf≥0.75, trust≥60) is not firing on any closed trade in 90 days. Either the gate is dead code, or the score/trust distributions never reach those thresholds. Either way, the "HIGH CONVICTION" label on the dashboard is currently decorative.
2. **`opened` >> `passed_smart` in most classes** (EQUITY 5404 opened vs 253 passed_smart; FOREX 21410 vs 21745 — the only class where they roughly match). This means the "Smart Picks" gate is *not* the gate that actually controls what gets opened. The funnel diagram is lying about causality.
3. **`passed_verified_alpha` is 0 for EQUITY, FOREX, COMMODITY, BOND, ETF, INDEX, UNKNOWN** — i.e. the "verified alpha" tier is essentially CRYPTO-only (1790) plus a rounding error elsewhere. Any claim of a multi-asset edge library is false.

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE.** The three "PROVEN" cells are the *same 67 trades* sliced three ways (`trust=UNK & fam=mean_reversion & score_dec=S40` ≡ `conf=C<0.60 & fam=mean_reversion & score_dec=S40` ≡ `fam=mean_reversion & dir=LONG & score_dec=S40`). WR=98.5%, PF=214, avg_pnl=+1.27% per trade. A 98.5% WR on mean-reversion longs is not a strategy — it's a **labeling artifact**. Most likely causes: (i) `score_dec=S40` is a post-hoc bucket that correlates with "trade already won" (look-ahead in the decile assignment), (ii) mean-reversion exits are being marked as wins on any touch of a tight TP while losers are held open and never closed (survivorship in `closed`), or (iii) single-symbol concentration — 67 trades in one name. The `wr_z=7.94` and `bonferroni_pass=true` are meaningless when the underlying cell is a tautology. **Treat as falsified.**
- **90d expected P&L (1% risk, $100k): $0.** Do not size this. If you *did* size it naively at 1% risk × 162 closed trades × 1.27% avg = ~$2,050 gross, but the number is fictional.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **≥70** AND add a hard requirement that `trust != UNK` for any pick to enter the Smart funnel. The current funnel passes 253/5566 (4.5%) but opens 5404 — the gate is bypassed. Fix the bypass before tuning the constant.
- **Confidence (1-5): 1**

### FOREX
- **Real/noise verdict: NOISE.** `top_edges_proven` is **empty** — the pipeline itself refuses to certify anything. Best PF cell is `rr=RR1.0-1.5 & fam=mean_reversion & dir=LONG & source=multi_asset_copytrader`, n=44, WR=59%, PF=2.87, but `bonferroni_pass=false` and `wr_z=1.21`. That's a t-stat of ~1.2 on n=44 — indistinguishable from noise. Class-level WR is 45.6% on 494 decisive trades, which is *below* breakeven for typical R:R. The `multi_asset_copytrader` source is a single-source concentration risk (all 44 trades from one copier). **No edge.**
- **90d expected P&L (1% risk, $100k): -$1,800 to -$3,500.** At 45.6% WR with typical 1:1 R:R and 1% risk, expectancy per trade ≈ -0.09R. 494 decisive × -0.09 × $1,000 = **-$4,450** before slippage; call it **-$2,000 to -$4,000** net of the few winners. Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥75** AND add `source != multi_asset_copytrader` exclusion until that source is independently validated. Currently 21745/22727 (95.7%) pass Smart — the gate is a rubber stamp.
- **Confidence (1-5): 4** (confident it's noise)

### CRYPTO
- **Real/noise verdict: MOSTLY REAL, but the PF=3.6 is inflated.** The cell `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` has n=184, WR=73.9%, WR_shrunk=71.6%, PF=3.6, train_pf=3.40, holdout_pf=4.28, `bonferroni_pass=true`, `wr_z=6.49`. This is the **only cell in the entire report that survives holdout + Bonferroni + shrinkage**. That said: (i) PF=3.6 with avg_pnl=+1.40% implies avg_loss ≈ -0.39% — that's a **very tight stop**, which is exactly the profile that produces leakage via intrabar stop/TP ordering. Verify the backtester isn't assuming TP-before-SL on the same bar. (ii) `source=alpha_engine` is one source; check symbol concentration (BTC/ETH dominance would inflate). (iii) The `ml` cells you flagged aren't in this report — if they exist elsewhere with PF>5, treat as leakage until proven otherwise. **Conditionally real, pending stop/TP ordering audit.**
- **90d expected P&L (1% risk, $100k): +$8,000 to +$14,000.** 184 trades × 1% risk × expectancy. At WR=71.6% shrunk and PF=3.6, expectancy ≈ +0.55R per trade → 184 × 0.55 × $1,000 = **+$101,200 gross** — but that's absurd and tells you the PF is overstated. Realistic haircut: assume true PF ≈ 1.8–2.2 after fixing stop/TP ordering and slippage → expectancy ≈ +0.25R → **+$46,000**. Apply 50% haircut for regime decay and single-source risk → **+$8k to +$14k** is the honest range. Do not deploy at the headline number.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** to admit more of this cell (currently 3290/12720 = 25.9% pass Smart, but only 184 trades in the winning cell). More importantly, add `HC_MIN_CONF_CRYPTO = 0.75` and `HC_MIN_TRUST_CRYPTO = 60` as *hard* gates so the winning cell actually reaches HC (currently 0 HC passes — the winning cell is being filtered out by something downstream).
- **Confidence (1-5): 3**

### COMMODITY
- **Real/noise verdict: NOISE.** `top_edges_proven` empty. Best cell `trust=UNK & rr=RR1.5-2.0 & fam=mean_reversion` has n=24, WR=54%, PF=7.28 — but `holdout_pass=false` (holdout n=5, PF=10.36 on 5 trades is meaningless) and `bonferroni_pass=false`. Class WR=42.9% on 112 decisive. **No edge.** Note: H-001 (COT leakage) and H-036 (inventory gate) are already falsified — do not re-derive.
- **90d expected P&L (1% risk, $100k): -$1,500 to -$2,500.** 112 decisive × -0.15R × $1,000 ≈ **-$1,680**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥75** AND require `rr >= 1.5` as a hard precondition (the only cell with any signal is RR1.5-2.0). Currently 3475/6001 (57.9%) pass Smart — far too loose.
- **Confidence (1-5): 4**

### FUTURES
- **Real/noise verdict: NOISE.** n_closed=17. WR=29.4%. `top_edges_proven` empty, `best_pf_overall` empty. H-005 already falsified the anti-signal inversion. **No edge, insufficient sample.**
- **90d expected P&L (1% risk, $100k): -$500 to -$1,000.** 17 trades × -0.4R × $1,000 ≈ **-$680**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥80** (effectively pause the class until n≥100 closed). 107/166 (64.5%) pass Smart on 17 closed trades is statistically meaningless.
- **Confidence (1-5): 5** (confident it's noise)

### BOND
- **Real/noise verdict: NOISE, and one cell is actively toxic.** `trust=UNK & dir=LONG & source=bond_scanner` has n=20, WR=10%, PF=0.052, `wr_z=-3.58`. That's a **statistically significant loser**. The other cell (`trust=UNK & dir=LONG & score_dec=S50`) has `holdout_pass=false`. Class WR=41.2% on 34 decisive. **No edge; one source is a confirmed negative.**
- **90d expected P&L (1% risk, $100k): -$800 to -$1,500.** 34 trades × -0.2R × $1,000 ≈ **-$680**, plus the bond_scanner cell alone at -0.9R × 20 = **-$1,800**. Net **-$1,500 to -$2,500**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **≥80** AND add `source != bond_scanner` exclusion. 4/529 (0.8%) pass Smart already, so the gate isn't the problem — the *opened* count (495) is. Fix the bypass.
- **Confidence (1-5): 5**

### ETF
- **Real/noise verdict: NOISE.** n_closed=7, WR=14.3%. 293/334 (87.7%) pass Smart on 7 closed trades. **No edge, insufficient sample.**
- **90d expected P&L (1% risk, $100k): -$300 to -$600.** 7 trades × -0.5R × $1,000 ≈ **-$350**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥80** (pause until n≥50).
- **Confidence (1-5): 5**

### INDEX
- **Real/noise verdict: NOISE.** n_closed=5, WR=20%. 1491/1691 (88.2%) pass Smart on 5 closed trades. **No edge.**
- **90d expected P&L (1% risk, $100k): -$200 to -$400.** 5 trades × -0.5R × $1,000 ≈ **-$250**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥80** (pause).
- **Confidence (1-5): 5**

### UNKNOWN
- **Real/noise verdict: NOISE / DATA HYGIENE FAILURE.** n_closed=7, WR=0%. 176/1409 (12.5%) pass Smart, 1402 opened. The class name itself is a bug — these should be classified or dropped. **No edge.**
- **90d expected P&L (1% risk, $100k): -$350 to -$700.** 7 trades × -0.7R × $1,000 ≈ **-$490**.
- **Gate change:** Add a hard `asset_class != UNKNOWN` filter in `production_scanner.py` before scoring. This is a data-quality gate, not a threshold.
- **Confidence (1-5): 5**

### MEME
- **Real/noise verdict: NOISE.** n_closed=4. **No edge, insufficient sample.**
- **90d expected P&L (1% risk, $100k): -$100 to -$300.** 4 trades × -0.5R × $1,000 ≈ **-$200**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥85** (pause).
- **Confidence (1-5): 5**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only, and only the `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell.** It is the only cell in the entire 90-day report that survives holdout, Bonferroni, and Bayesian shrinkage simultaneously. Size at **0.25% risk per trade** (not 1%) until the stop/TP ordering audit clears, cap at 5 concurrent positions, and require `source=alpha_engine` explicitly. Expected 90d P&L at 0.25% risk: **+$2k to +$3.5k** — small, but real.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **FOREX** — 95.7% Smart pass rate is a rubber stamp; 45.6% WR is below breakeven. Mutate: tighten `SMART_PICKS_MIN_SCORE_FOREX` to ≥75, exclude `multi_asset_copytrader`, re-run 30d. If WR doesn't cross 52%, kill.
- **COMMODITY** — 57.9% Smart pass rate, 42.9% WR, both prior hypotheses (H-001, H-036) already falsified. Mutate: require `rr>=1.5` + `trust != UNK`. If no cell survives, kill.
- **BOND** — `bond_scanner` source is a statistically significant loser (wr_z=-3.58). Mutate: exclude that source entirely, re-run. If the remaining 14 trades don't show WR≥55%, kill.

**KILL immediately (no mutation warranted):** FUTURES, ETF, INDEX, UNKNOWN, MEME — all have n_closed < 20 and no surviving cell. Pausing them costs nothing and removes noise from the dashboard.

**The single most important fix is not a threshold — it's the funnel bypass.** `opened` >> `passed_smart` in 8 of 10 classes means the gates you're tuning are not the gates that control live capital. Until that's fixed, every constant in `quality_gates.py` is theater. Fix the bypass first, then re-run this audit.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — PF=214 on n=67 with 98.51% WR is statistically impossible without single-symbol concentration or look-ahead; all three cells are the same 67 trades.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — no PROVEN cells; best PF cells fail Bonferroni and have n<50 with unstable holdout.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: HC_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Marginally real on the three listed cells (n=183-184, WR_shrunk 71-72%, PF=3.6, holdout passes) but PF still high enough to warrant leakage check on alpha_engine source.
- 90d expected P&L (1% risk, $100k): ~$8200 (184 trades × ~1.4% avg edge after 0.2% slippage, 1% risk sizing).
- Gate change: ALPHA_ENGINE_MIN_CONF_CRYPTO = 0.78
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: Noise — no PROVEN cells; best PF cells have n=23-24, holdout fails, bonferroni fails.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 4

### FUTURES
- Real/noise verdict: Noise — n_closed=17 total, zero PROVEN or stable cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n=34 total, best cells fail holdout and show negative expectancy.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: HC_MIN_TRUST_BOND = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n_closed=7, zero qualifying cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n_closed=7, zero qualifying cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n_closed=4, zero qualifying cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n_closed=5, zero qualifying cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with any statistically credible cells that survive holdout). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its "edge" is a data artifact, not a tradable signal. All other classes have no actionable edge.
