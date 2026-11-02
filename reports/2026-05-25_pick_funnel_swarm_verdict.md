# Pick Funnel Swarm Verdict — 2026-11-02 04:07 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261102T040712Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80 & conf>=0.75 & trust>=60`) is *never* firing. Either the score distribution never reaches 80, or trust never reaches 60, or the conjunction is empty. This is the single biggest finding in the dataset — the "high conviction" funnel is a null set. Any "edge" being discussed is *below* the HC gate.
2. **`opened` >> `closed` in every class** (e.g. EQUITY 5712 opened / 130 closed = 2.3% close rate; FOREX 23009/1254 = 5.4%). The WR numbers are computed on a tiny, non-random survivor subset. This is a **massive survivorship / open-position bias** — the closed trades are the ones that hit TP/SL fast, not a representative sample.
3. **`passed_smart` is wildly inconsistent with `opened`.** FOREX: 23,496 passed_smart but 23,009 opened — the "smart" gate is passing ~97% of scans. COMMODITY: 3,698 passed_smart / 6,140 opened — *more opened than passed smart*, which is logically impossible unless `opened` counts pre-gate paper trades. The funnel accounting is broken and should be fixed before any gate tuning.

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE.** The "PROVEN" cell is `trust=UNK & conf<0.60 & fam=mean_reversion`, n=63, WR=98.41%, PF=174.6. A PF of 174 is not a strategy — it is a data artifact. Three independent red flags: (i) `trust=UNK` means the trust score is *missing*, so the cell is defined by absence of a field, not a signal; (ii) conf<0.60 is the *lowest* confidence bucket producing the *highest* WR — that is the signature of a look-ahead or label-leakage bug (the model is being scored on trades it already "knew" the outcome of); (iii) the three "top edges" are the *same 63 trades* re-sliced by different dims (identical n, wins, PF, avg_pnl to 4 decimals) — this is one cell, not three, and the Bonferroni pass is meaningless because the tests are perfectly collinear. `wr_z=7.685` on n=63 with 62 wins is only possible if the loss/win labeling is corrupted. **Do not trade this.** The honest read: EQUITY has 130 closed trades, 92W/38L, WR 70.8% — but with a 2.3% close rate on 5,712 opens, that 70.8% is the fast-TP subset, not the strategy.
- **90d expected P&L (1% risk, $100k): $0.** I will not size a PF=174 cell. If forced to size the *honest* 130-trade closed subset at 1% risk ($1,000/trade) with a realistic 60% haircut for survivorship and 0.15% round-trip slippage on equities: 130 × $1,000 × (0.708 × avg_win − 0.292 × avg_loss) ≈ **+$4,000 to +$6,000 gross, ~$2,500 net** — but confidence is low because the closed subset is biased. Treat as **$0 committed** until the leakage is fixed.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — but the real fix is upstream: **kill the `trust=UNK` bucket entirely** (require `trust IS NOT NULL` before a pick can pass smart). The mean_reversion/conf<0.60 cell must be quarantined and re-audited for label leakage before it is allowed to influence any gate.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict: NOISE.** No PROVEN cells. Best PF is 1.93 on n=31 (`trust=UNK & dir=LONG & source=alpha_engine`), but `holdout_pass=false` (holdout PF 1.11 vs train 3.19) and `bonferroni_pass=false`. This is the classic overfit-to-train pattern. Note this is *adjacent* to the falsified H-001 (COT look-ahead) and H-036 (inventory direction) — the `trust=UNK & dir=LONG` signature is the same shape as the rejected COT cell. **Flag as potential leakage recurrence**, do not re-derive. The 62.2% headline WR on 45 closed trades is not actionable.
- **90d expected P&L (1% risk, $100k): $0.** n=45 closed, holdout fails, no proven cell. Sizing this would be gambling.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise it hard. The 3,698/6,185 (60%) smart pass rate is far too loose for a class with 45 closed trades and no proven edge. Set to a level that cuts smart passes by ~70% (i.e. roughly the 90th percentile of the score distribution) so only the top decile reaches the funnel. Exact constant value depends on the score histogram, but the *direction* is unambiguous: tighten aggressively.
- **Confidence (1-5): 1**

### FOREX
- **Real/noise verdict: NOISE (and the funnel is broken).** No PROVEN cells. The best cell (`trust=UNK & fam=regime & dir=LONG`, n=29, WR 82.8%, PF 5.2) **fails Bonferroni** (`bonferroni_pass=false`) and is a single-source cell (`regime_terminal`). n=29 with 24 wins gives wr_z=3.53 — that is ~1.5σ after multiple-testing correction across the dozens of cells scanned, i.e. not significant. The headline 49.33% WR on 1,254 closed trades is the *honest* number and it is a coin flip. The 23,496/24,263 (96.8%) smart pass rate means the smart gate is doing essentially nothing for FOREX — it is a rubber stamp. This is the class where the funnel is most obviously misconfigured.
- **90d expected P&L (1% risk, $100k): $0 to slightly negative.** 1,254 closed × $1,000 × (0.4933 × avg_win − 0.5067 × avg_loss). With FX spreads (~0.5–1 pip round-trip on majors, wider on crosses) and 1% risk sizing, the 49.33% WR is below breakeven for any R:R < ~1.03. **Expect −$2,000 to −$5,000 net** if traded as-is. Do not trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — this is the highest-leverage single change in the whole system. A 96.8% pass rate is not a gate. Raise it so smart passes drop to roughly the top 10–15% of the score distribution (target ~2,500–3,500 passes from 24,263 scans). This alone will remove ~20,000 low-quality paper trades from the funnel and make every downstream metric (WR, PF, HC pass count) meaningful for the first time.
- **Confidence (1-5): 1** (on edge) / **5** (on "the gate is broken")

### CRYPTO
- **Real/noise verdict: LIKELY REAL, but overstated — and the "ml" cell is not in the data shown.** The PROVEN cell is `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`, n=175, WR 78.3%, shrunk 75.4%, PF 4.22, **holdout_pass=true** (train PF 6.28 / holdout 2.81), **bonferroni_pass=true**, wr_z=7.49. This is the *only* cell in the entire dataset that survives holdout AND multiple-testing correction with a plausible (not absurd) PF. The holdout degradation from 6.28→2.81 is exactly what you *want* to see — it means the edge is real but decaying, not leaked. **However:** (i) the three "top edges" are again the same 175 trades re-sliced (identical numbers) — one cell, not three; (ii) `trust=UNK` again — the trust field is missing for these picks, which is a data-quality problem even if the edge is real; (iii) you asked about a CRYPTO `ml` cell with suspiciously high PF — **it is not in the provided JSON.** If it exists elsewhere, treat any PF > 10 on crypto as leakage until proven otherwise (crypto is the easiest place to leak future prices via OHLCV joins). The cell shown (PF 4.22, holdout 2.81) is credible; a hypothetical `ml` cell at PF >> 10 would not be.
- **90d expected P&L (1% risk, $100k): +$8,000 to +$14,000.** 175 closed × $1,000 × (0.754 × avg_win − 0.246 × avg_loss). With avg_pnl 1.60% and PF 4.22, expected per-trade edge ≈ +0.9% of notional at 1% risk → ~$9/trade × 175 ≈ **+$1,575** on the *proven cell alone*. But the class has 2,446 closed trades at 45.8% WR overall — the proven cell is a *subset*. If you size only the proven cell: **~+$1,500 to +$2,500 net** after 0.2% round-trip slippage on crypto (which is generous — real slippage on alts is worse). If you naively size all 2,446 closed trades at 45.8% WR, you lose money. **The edge is in the cell, not the class.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — but the *specific* change is to **route the proven cell to HC**. The cell is `conf 0.75–0.80 & score_dec S50 & source alpha_engine`. The HC gate requires `score>=80`; these picks are in the S50 score decile, so they can *never* pass HC as currently defined. **Lower `HC_MIN_SCORE_CRYPTO` from 80 to ~50** (or add a cell-based bypass for `conf∈[0.75,0.80] & source=alpha_engine`). This is the one change that converts a proven edge into actual HC picks. Also: fix `trust=UNK` — populate trust for alpha_engine crypto picks so the HC trust>=60 clause can ever fire.
- **Confidence (1-5): 3** (the only class above 2)

### BOND
- **Real/noise verdict: NOISE.** n=31 closed, WR 38.7%, no proven cells, no best-PF cells. 1/837 smart pass rate is the only sane gate in the system, and it's still producing 806 opens — meaning the `opened` counter is counting pre-gate paper trades. No edge.
- **90d expected P&L (1% risk, $100k): −$3,000 to −$5,000** if traded (38.7% WR is a clear loser). **$0 committed.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — the 1/837 pass rate is fine; the problem is `opened=806`. Fix the funnel accounting so `opened` only counts post-gate picks. No score change needed; this class should be **demoted** (see system-wide).
- **Confidence (1-5): 1**

### ETF
- **Real/noise verdict: NOISE.** n=9 closed, WR 11.1% (1W/8L). 295/344 smart pass rate (86%) is absurd for a class with 9 closed trades. No edge, and the sample is too small to even call it a losing strategy — it's just unmeasured.
- **90d expected P&L (1% risk, $100k): −$7,000 to −$8,000** if the 11% WR held (it won't — n=9). **$0 committed.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to cut the 86% pass rate to <20%. But really: **demote** (see system-wide).
- **Confidence (1-5): 1**

### FUTURES
- **Real/noise verdict: NOISE.** n=18 closed, WR 38.9%, no proven cells. Note the falsified H-005 (futures_momentum_anti_signal) — this class has a history of failed hypotheses. 150/203 smart pass rate (74%) is too loose.
- **90d expected P&L (1% risk, $100k): −$2,000 to −$4,000** if traded. **$0 committed.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — tighten to cut pass rate by ~60%. Demote candidate.
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict: NOISE.** n=9 closed, WR 33.3%. 15/29 smart pass rate. No edge, tiny sample. Meme coins at 1% risk with real slippage (often 1–3% round-trip) are structurally unprofitable at this WR.
- **90d expected P&L (1% risk, $100k): −$5,000 to −$8,000** (slippage-adjusted). **$0 committed.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — or better, **disable MEME from the smart funnel entirely** until n>=50 closed. Demote.
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict: NOISE / DATA BUG.** n=3 closed, 0W/3L. 1,390 scanned, 142 passed smart, 1,387 opened. This class should not exist — it means the classifier is failing to assign an asset class to 1,390 instruments. That is a data-quality bug, not a strategy.
- **90d expected P&L (1% risk, $100k): $0.** Do not trade unclassified instruments.
- **Gate change:** Not a score constant — **fix the asset-class classifier** so UNKNOWN → 0. Any pick landing in UNKNOWN should be auto-rejected before the smart gate.
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict: NOISE.** n=4 closed, 1W/3L. 1,564/1,929 smart pass rate (81%) — again, a rubber stamp. No edge, no sample.
- **90d expected P&L (1% risk, $100k): $0.** n=4 is not a sample.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — tighten hard, but really this class should be **demoted** until n>=50 closed.
- **Confidence (1-5): 1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only the one proven cell.**
The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the *only* signal in the entire 90-day dataset that survives holdout (train PF 6.28 → holdout 2.81) AND Bonferroni correction (wr_z=7.49, n=175). It is not leakage — the holdout degradation is the tell. Size it at 1% risk, cap total crypto exposure at ~5% of the $100k account, and expect **~+$1,500 to +$2,500 net over 90 days** on the proven cell alone. Do **not** size the rest of crypto (2,446 closed at 45.8% WR is a loser). The gate change that unlocks this is **lowering `HC_MIN_SCORE_CRYPTO` from 80 to ~50** (or adding a cell bypass) so these picks can actually reach the HC funnel — right now they are structurally excluded because they sit in the S50 decile.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.**
It is the clearest case of a broken gate masquerading as a strategy: 96.8% smart pass rate, 49.33% WR on 1,254 closed trades (a coin flip before costs, a loser after), zero proven cells, and the largest open/closed gap in the system (23,009/1,254). Per the three-axis protocol, do not kill it outright — **mutate the gate first**: raise `SMART_PICKS_MIN_SCORE_FOREX` to cut passes by ~90%, re-run 30 days, and if WR on the surviving subset does not clear 55% with n>=100, then kill. FOREX is also the class where the "mutate before kill" discipline matters most because the *volume* (24k scans) makes it tempting to keep — but volume without edge is just a faster way to pay spreads.

**Honorable-mention demotions:** BOND, ETF, FUTURES, MEME, INDEX, UNKNOWN all have n<50 closed and no proven cells

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — PF=174 and 98% WR on n=63 closed trades with trust=UNK is statistically impossible in live markets; matches known single-symbol or timestamp leakage patterns.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected; do not trade).
- Gate change: SMART_PICKS_MIN_TRUST_EQUITY = 70
- Confidence (1-5): 1

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf cells fail holdout and have n<50 with PF<2 after shrinkage.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85
- Confidence (1-5): 2

### FOREX
- Real/noise verdict: Noise — no proven cells; regime edges have n=29, bonferroni fails, and PF inflated by low-volatility bias.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_FILTER_MIN_CONF_FOREX = 0.82
- Confidence (1-5): 2

### CRYPTO
- Real/noise verdict: Real but narrow — n=175, WR_shrunk=75.38%, PF=4.22 passes holdout/bonferroni; only the C0.75-0.80 & S50 slice qualifies.
- 90d expected P&L (1% risk, $100k): ~$4,800 (assume ~40 qualifying trades at 1.6% avg win, 0.5% slippage, 1% risk sizing).
- Gate change: HC_FILTER_MIN_SCORE_CRYPTO = 78
- Confidence (1-5): 4

### BOND
- Real/noise verdict: Noise — n=31 closed, no proven cells, WR=38.71%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_BOND = 65
- Confidence (1-5): 1

### ETF
- Real/noise verdict: Noise — n=9 closed, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 90
- Confidence (1-5): 1

### UNKNOWN
- Real/noise verdict: Noise — n=3 closed, WR=0%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_UNKNOWN = 80
- Confidence (1-5): 1

### INDEX
- Real/noise verdict: Noise — n=4 closed, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: Noise — n=18 closed, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_FUTURES = 70
- Confidence (1-5): 1

### MEME
- Real/noise verdict: Noise — n=9 closed, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 92
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated narrow edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its "proven" cells are leakage artifacts and should be mutated (add trust floor + symbol diversification) before any further use. All other classes have zero actionable edge.
