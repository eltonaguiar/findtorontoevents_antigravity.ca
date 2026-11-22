# Pick Funnel Swarm Verdict — 2026-11-21 04:42 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261121T044137Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

## Pre-analysis sanity checks (read this first)

Before per-class verdicts, three structural red flags dominate everything below:

1. **`passed_high_conviction = 0` across ALL 11 asset classes.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** trades in 90 days. Either the gate is mis-wired (trust never reaches 60, or score never reaches 80), or the scoring pipeline is broken. This is the single biggest finding in the dataset — the "HIGH CONVICTION" funnel is a dead branch. Any "edge" discussion below is about the *Smart* funnel, not HC.

2. **`passed_verified_alpha` is 0 for 9 of 11 classes.** Only CRYPTO (2693) and FOREX (9) and FUTURES (1) and MEME (2) pass. The verified-alpha gate is effectively CRYPTO-only.

3. **`opened` >> `passed_smart` in every class.** EQUITY: 227 passed_smart but 5671 opened. COMMODITY: 3817 passed_smart, 5783 opened. FOREX: 26941 passed_smart, 26177 opened. **The Smart gate is not actually gating anything** — trades are being opened that never passed it. Either the funnel is measuring two different populations (scanner vs. execution), or the gate is bypassed downstream. This invalidates the naive reading of "passed_smart → opened → closed" as a causal chain.

4. **`closed` is catastrophically small relative to `opened`** in most classes: EQUITY 112/5671 (2%), COMMODITY 46/5783 (0.8%), INDEX 1/2057 (0.05%), FOREX 1394/26177 (5.3%). Only CRYPTO (23%) and FOREX (5%) have meaningful closure. **The WR numbers for EQUITY, COMMODITY, INDEX, ETF, BOND, FUTURES, MEME, UNKNOWN are computed on a tiny, non-random survivor subset** — likely the trades that hit TP fast. This is survivorship bias, not edge.

5. **`trust=UNK` dominates every "proven" cell.** Every single PROVEN cell in EQUITY, CRYPTO, and every best-PF cell in COMMODITY/FOREX has `trust=UNK`. That means the trust dimension is not populated for the trades that are winning — the "edge" is defined on a dimension the system doesn't actually measure. This is a **labeling artifact**, not a discovered edge.

6. **The EQUITY "proven" cell is a single-cell triple-count.** All three "top edges" for EQUITY are the *same 37 trades* re-sliced by different dims (`trust=UNK & rr>=2.0 & fam=mean_reversion` ≡ `rr>=2.0 & fam=mean_reversion & dir=LONG` ≡ `rr>=2.0 & fam=mean_reversion & source=alpha_engine`). n=37, wins=36, PF=132. **PF=132 on 37 trades with 97% WR is not an edge — it's a data bug.** A PF of 132 means average win is 132× average loss. That is only possible if losses are near-zero (stop never triggered, or PnL recorded as 0 on losers) or if the "loss" bucket is mislabeled. Combined with `train_n=11, holdout_n=26` and `holdout_pf=99.0` (the 99.0 cap is a sentinel for "no losses in holdout"), this is almost certainly **look-ahead / same-bar exit leakage** or a PnL accounting bug. Do not trade this.

---

### EQUITY
- **Real/noise verdict:** **NOISE / DATA BUG.** The "proven" cell (n=37, WR 97.3%, PF 132) is a single 37-trade cluster triple-counted across three dims. PF=132 with 97% WR is not achievable in a real mean-reversion book — it implies losses are being recorded as ~0 or exits are same-bar. `holdout_pf=99.0` is the sentinel cap, meaning zero losses in the 26-trade holdout — a red flag, not a confirmation. The class-level WR of 73.2% is computed on 112 closed out of 5671 opened (2% closure) — pure survivorship. **No tradeable edge here.** The `trust=UNK` label on the winning cell means the edge is defined on an unpopulated dimension.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not size. If forced to model the naive 73% WR on 112 trades at 1% risk with 1.5:1 R:R: ~$1,200 gross, but the sample is non-random and the PF is a bug — expected realized is negative after slippage. **$0 is the honest number.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — but the real fix is upstream: **`HC_TRUST_MIN` in `hc_filter.js` is unreachable (0 HC passes in 90d).** Lower `HC_TRUST_MIN` from 60 to 40 *and* add a hard `MIN_CLOSED_TRADES_FOR_EDGE = 30` guard so the 37-trade cell can't be promoted. The single highest-leverage change: **`HC_TRUST_MIN = 40`** (unblocks the dead HC branch) — but only after fixing the PnL accounting bug that produces PF=132.
- **Confidence (1-5):** **1**

### COMMODITY
- **Real/noise verdict:** **NOISE.** No PROVEN cells. Best PF cell is n=23, WR 65.2%, shrunk 58.1%, PF 3.56, but `bonferroni_pass=false` and `wr_z=1.46` (not significant). Holdout n=13 is too small. The class-level 63% WR is on 46 closed out of 5783 opened (0.8% closure) — extreme survivorship. Note H-001 (COT leakage) and H-036 (inventory gate rejected) are both COMMODITY — this class has a documented history of leakage-driven fake edges. **Do not trust the 65% WR.**
- **90d expected P&L (1% risk, $100k):** **$0.** 46 closed trades is below any reasonable inference threshold. Even at face value (63% WR, ~1.27% avg PnL on 46 trades at 1% risk): ~$580 gross, but the sample is non-random and the class has two prior leakage kills. **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise it, because 3817/5829 (65%) pass Smart, which is not a gate. Set to a value that yields ~5-10% pass rate. But the honest change is **`MIN_CLOSED_TRADES_FOR_EDGE = 30`** applied per-class — COMMODITY has 46, barely clears, and the sub-cells don't.
- **Confidence (1-5):** **1**

### INDEX
- **Real/noise verdict:** **NO EDGE — INSUFFICIENT DATA.** 1 closed trade out of 2057 opened (0.05% closure). WR=100% on n=1 is meaningless. 1542/2058 pass Smart (75%) — the gate is not gating. **Cannot evaluate.**
- **90d expected P&L (1% risk, $100k):** **$0.** n=1.
- **Gate change:** **`SMART_PICKS_MIN_SCORE_INDEX`** — raise aggressively; 75% pass rate is not a filter. But the real issue is closure rate: 0.05% closed means the exit logic is broken for INDEX. Fix exits before touching the entry gate.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **NOISE / LEAKAGE SUSPECT.** No PROVEN cells. The best-PF cell (`trust=UNK & conf>=0.90 & fam=regime`, n=38, WR 89.5%, PF 14.4) has **`holdout_n=2`** and `holdout_pass=false`. PF=14.4 on 38 trades with 89% WR is the same signature as the EQUITY bug — losses near-zero. `bonferroni_pass=true` is misleading because the holdout is 2 trades. The class-level WR is 50.3% on 477 decisive — that's the honest number, and it's a coin flip. **The 89% WR regime cell is almost certainly leakage or a stop-recording bug.** Note: the prompt flags "FOREX consensus" — the `regime_terminal` source at conf>=0.90 is the suspect; treat as leakage recurrence until proven otherwise.
- **90d expected P&L (1% risk, $100k):** **~$0 to slightly negative.** 477 decisive trades at 50.3% WR with typical 1:1 R:R and 1% risk = ~$0 gross, minus slippage (~0.5-1 pip per side on 477 trades ≈ -$2,000 to -$4,000). **Net negative.** The 89% regime cell is not investable (holdout n=2).
- **Gate change:** **`SMART_PICKS_MIN_SCORE_FOREX`** — 26941/27571 (97.7%) pass Smart. This is the worst gate in the system. Raise to a value yielding <10% pass. Also add **`HC_CONF_MIN`** enforcement — the regime cell at conf>=0.90 is where the leakage lives; require `holdout_n >= 20` before any cell is promoted.
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **NO EDGE — NEGATIVE.** WR 38.7% on 31 decisive trades. Below coin flip. 1/1215 pass Smart (0.08%) — the gate is *too tight* here, or BOND is structurally unprofitable in this regime. **No edge; actively losing.**
- **90d expected P&L (1% risk, $100k):** **Negative, ~-$600 to -$1,200.** 31 trades at 38.7% WR, 1% risk, 1:1 R:R ≈ -$700 gross, plus slippage. **Negative.**
- **Gate change:** **`SMART_PICKS_MIN_SCORE_BOND`** — currently 1/1215 pass, which means the gate is either mis-configured or BOND is being scanned but not traded. Per MUTATION_THREE_AXIS_PROTOCOL, **mutate before kill**: try loosening the gate to see if a sub-population has edge, but the 38.7% WR says the class is a demote candidate.
- **Confidence (1-5):** **2** (confident it's negative)

### CRYPTO
- **Real/noise verdict:** **MIXED — one cell is plausibly real, the rest is noise.** The PROVEN cell `trust=UNK & conf=C0.75-0.80 & source=alpha_engine` (n=197, WR 63.5%, shrunk 62.2%, PF 1.75, train_pf 1.66, holdout_pf 1.91, holdout_n=90, `bonferroni_pass=true`, `wr_z=3.78`) is the **only cell in the entire dataset that survives a real holdout with meaningful n.** PF 1.75 is believable (not 132, not 14). This is the one candidate for a real edge. **Caveat:** `trust=UNK` again — the edge is defined on an unpopulated dimension, so it's really "conf 0.75-0.80 & alpha_engine & LONG" (the three cells are the same 197 trades re-sliced). The class-level WR of 44.9% on 2165 decisive is the honest baseline — the 63% cell is a *sub-population* that beats it. That's a real conditional edge, but it's narrow. The prompt flags "CRYPTO ml cells" — the `ml` source is not in the proven cells; the proven cell is `alpha_engine`. Treat any `ml`-sourced high-PF cell as leakage suspect (not shown here, but flag it).
- **90d expected P&L (1% risk, $100k):** **~$3,000-$4,500 gross on the proven cell only.** 197 trades × 1% risk × 0.63% avg PnL (from `avg_pnl_pct=0.6335`) ≈ **$1,250 gross** at 1% risk. At 2% risk (still reasonable for a proven cell): **~$2,500.** Minus slippage (~0.1% per side on 197 trades ≈ -$400). **Net ~$850-$2,100.** The class-level 44.9% WR is a loser — only the 197-trade cell is investable.
- **Gate change:** **`SMART_PICKS_MIN_SCORE_CRYPTO`** — 3948/11672 (34%) pass Smart, which is too loose given class WR is 44.9%. But the highest-leverage change is to **route the proven cell explicitly**: add a `PROVEN_CELL_OVERRIDE` in `production_scanner.py` that boosts score for `conf in [0.75, 0.80] & source == alpha_engine & dir == LONG`, and **raise `SMART_PICKS_MIN_SCORE_CRYPTO` to filter out the 44.9% WR mass.** Concretely: **`SMART_PICKS_MIN_SCORE_CRYPTO = 65`** (up from current, which is clearly permissive given 34% pass rate).
- **Confidence (1-5):** **3** (the 197-trade cell is the only thing in this dataset I'd put money behind, and only at reduced size)

### PREDICTION_MARKET
- **Real/noise verdict:** **NO DATA.** 0 closed. 134 scanned, 11 pass Smart, 134 opened, 0 closed. **Cannot evaluate.** The 0 closure rate is a bug — PM trades should resolve.
- **90d expected P&L (1% risk, $100k):** **$0.** No closed trades.
- **Gate change:** Fix the resolution/closure pipeline before any gate change. **`SMART_PICKS_MIN_SCORE_PREDICTION_MARKET`** is irrelevant until trades close.
- **Confidence (1-5):** **1**

### ETF
- **Real/noise verdict:** **NO EDGE — NEGATIVE.** WR 12.5% on 8 decisive trades. 1 win, 7 losses. n=8 is too small to conclude, but the direction is bad. 268/304 (88%) pass Smart — gate is not gating.
- **90d expected P&L (1% risk, $100k):** **Negative, ~-$500.** 8 trades at 12.5% WR, 1% risk ≈ -$600 gross. **Negative.**
- **Gate change:** **`SMART_PICKS_MIN_SCORE_ETF`** — 88% pass rate is not a filter. Raise aggressively. But n=8 means the real fix is closure rate (8/296 = 2.7%).
- **Confidence (1-5):** **2** (confident it's negative, low confidence in magnitude)

### UNKNOWN
- **Real/noise verdict:** **NO EDGE — NEGATIVE.** WR 0% on 5 decisive trades. 0 wins, 5 losses. This is a **data hygiene failure** — 1230 scanned, 1225 opened, 5 closed, all losers. "UNKNOWN" asset class should not exist in a production funnel. **Kill the bucket, not the trades.**
- **90d expected P&L (1% risk, $100k):** **Negative, ~-$500.** 5 trades, all losers, 1% risk.
- **Gate change:** **Add `ASSET_CLASS_REQUIRED = True`** in `production_scanner.py` — reject any pick without a valid asset class before it reaches the funnel. This is a hygiene gate, not an edge gate.
- **Confidence (1-5):** **3** (confident the bucket is broken)

### FUTURES
- **Real/noise verdict:** **NO EDGE.** WR 37.5% on 16 decisive. 6 wins, 10 losses. n=16 too small, direction negative. Note H-005 (futures_momentum_anti_signal) is a documented FUTURES kill — this class has a history of failed hypotheses. **No edge.**
- **90d expected P&L (1% risk, $100k):** **Negative, ~-$400.** 16 trades at 37.5% WR, 1% risk.
- **Gate change:** **`SMART_PICKS_MIN_SCORE_FUTURES`** — 109/154 (71%) pass Smart, too loose. Raise. But per MUTATION_THREE_AXIS_PROTOCOL, FUTURES is a **demote candidate** given H-005 and the 37.5% WR.
- **Confidence (1-5):** **2**

### MEME
- **Real/noise verdict:** **NO EDGE — INSUFFICIENT DATA.** WR 40% on 5 decisive. n=5. 12 scanned, 4 pass Smart, 7 opened, 5 closed. **Cannot evaluate.** MEME is

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage. n=37 closed trades with WR 97.3% and PF 132 is statistically impossible in live markets; violates every known distribution for mean-reversion. Holdout PF=99 also indicates contamination (single-symbol concentration or timestamp error). All three cells are the same trades.
- 90d expected P&L (1% risk, $100k): $0 (edge is fictitious; any real deployment would hit immediate slippage and reversal).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 92
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise. No proven cells. Best cells fail Bonferroni, n=23, WR_shrunk only 58%. Matches pattern of previously rejected COT-style leakage.
- 90d expected P&L (1% risk, $100k): -$1,200 (negative expectancy once costs applied).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85
- Confidence (1-5): 4

### INDEX
- Real/noise verdict: Insufficient data. n_closed=1, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise. No proven cells. Best cells have holdout_n=2 and fail holdout_pass. High PF driven by tiny sample.
- 90d expected P&L (1% risk, $100k): -$4,800
- Gate change: HC_MIN_CONF_FOREX = 0.92
- Confidence (1-5): 4

### BOND
- Real/noise verdict: No edge. n_closed=31, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real. n=197 closed, WR_shrunk 62.21, PF 1.75, holdout_pass true, Bonferroni true. Only class with credible volume and statistical controls. Still modest edge after costs.
- 90d expected P&L (1% risk, $100k): +$8,400 (197 trades × 1% risk × ~0.63% avg edge, 0.15% slippage assumed).
- Gate change: HC_MIN_TRUST_CRYPTO = 55
- Confidence (1-5): 3

### PREDICTION_MARKET
- Real/noise verdict: No edge. n_closed=0.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_PREDICTION_MARKET = 75
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No edge. n_closed=8.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 88
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No edge. n_closed=5, WR 0%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No edge. n_closed=16.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 82
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No edge. n_closed=5.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 90
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically controlled, non-rejected edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its cells are leakage recurrence, not edge. All other classes have zero actionable edge; further mutation is waste.
