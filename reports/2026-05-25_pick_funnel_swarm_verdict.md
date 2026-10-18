# Pick Funnel Swarm Verdict — 2026-10-18 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261018T040942Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Read this first:** The funnel is broken in a way that makes most of the "PROVEN" cells untrustworthy. `passed_high_conviction = 0` across **every** asset class. That means the HC gate (`score>=80, conf>=0.75, trust>=60`) is either mis-wired, never evaluated, or the trust dimension is never populated (note every top cell is `trust=UNK`). Any "edge" that survives to the dashboard is therefore *not* the edge the HC gate was designed to surface — it's whatever leaked through the smart-picks floor. Treat the numbers below as **descriptive of the current (broken) funnel**, not as validated edges.

Also note the funnel arithmetic is internally inconsistent: EQUITY `opened=5575` but `passed_smart=218`; FOREX `opened=22739` but `passed_smart=23186`. The "opened" counter is clearly counting *scans that produced a trade record*, not *picks that passed a gate*. This is a data-integrity bug, not a strategy result.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The three "PROVEN" cells are the *same 65 trades* re-sliced three ways (`trust=UNK & fam=mean_reversion & score_dec=S40` ≡ `conf=C<0.60 & fam=mean_reversion & score_dec=S40` ≡ `fam=mean_reversion & dir=LONG & score_dec=S40`). n=65, WR=98.46%, PF=233. This is not an edge — it is a **single-cell artifact**. PF=233 with avg_pnl=1.43% implies avg_loss ≈ 0.006%, which is physically impossible for equities after any realistic slippage. Diagnosis: (i) `score_dec=S40` is almost certainly a *post-hoc* bucket that only contains trades whose outcome was already known (look-ahead in the decile assignment), (ii) `trust=UNK` means the trust dimension is unpopulated, so the "cell" is really just "all mean-reversion longs in one score decile," and (iii) 64/65 wins with a 1.43% average gain is the signature of a **stop that was never hit because the trade was closed at a favorable mark** — i.e., mark-to-model, not mark-to-market. Do not trade this. It is the same failure mode as H-001 (COT look-ahead) and H-009/H-011 (options leakage).
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** If forced to model the *reported* numbers: 65 trades × 1% × 1.43% avg = **~$930**, but this is fiction. Realistic post-slippage expectation on the underlying mean-reversion family (which is the only non-leaked signal here) is **negative to flat**; the 137 closed trades at 70% WR are dominated by the 65 leaked ones. Excluding them: 72 trades, 32W/41L ≈ 44% WR — **no edge**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current floor to **≥ 55** AND add a hard `trust != UNK` requirement in `hc_filter.js` (`if (p.trust === 'UNK' || p.trust == null) return false;`). The single biggest lift is killing the `trust=UNK` bucket, which is where 100% of the "edge" lives.
- **Confidence (1-5):** **1** (the edge is fake; confidence that it's fake is 5).

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** `top_edges_proven` is empty. The best cell (`trust=UNK & rr=RR>=2.0 & source=alpha_engine`, n=20, WR=75%, PF=5.28) **fails Bonferroni** (`bonferroni_pass: false`) and has `train_n=10` — a 10/10 train split is not a walk-forward, it's a coin flip. n=20 is below any reasonable significance threshold for a 4-dim cell. The 68 closed trades at 55.88% WR / PF implied ~1.0 is the honest number: **no edge**. This is consistent with H-001 (COT leakage killed) and H-036 (inventory direction rejected) — the commodity book has no surviving signal.
- **90d expected P&L (1% risk, $100k):** **~$0 to −$400.** 68 trades × 1% × (55.88% × avg_win − 44.12% × avg_loss). With PF≈1.0 and 1% risk, expected ≈ 0; after ~5bps slippage × 68 trades ≈ **−$340**. Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥ 60** (currently passing 3684/5939 = 62% of scans, which is absurdly permissive). The gate is not filtering; it's rubber-stamping.
- **Confidence (1-5):** **2** (confident there's no edge; less confident the exact gate value is optimal).

---

### INDEX
- **Real/noise verdict:** **NOISE / INSUFFICIENT SAMPLE.** n_closed=5. WR=20%. This is not a class — it's a rounding error. `passed_smart=1494/1837` (81%) means the gate is doing nothing. No edge, no sample, no conclusion possible.
- **90d expected P&L (1% risk, $100k):** **−$300** (5 trades, 1W/4L at 1% risk ≈ −3% × $100k × 1% = −$300, plus slippage). Statistically meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥ 65** and add a **minimum-n guard**: do not surface INDEX picks until the class has ≥ 30 closed trades in the trailing 90d. Right now the dashboard is showing a 5-trade class as if it were tradeable.
- **Confidence (1-5):** **1**.

---

### FOREX
- **Real/noise verdict:** **NOISE — and the "best" cell is a textbook leakage recurrence.** `top_edges_proven` is empty (correct). The `best_pf_overall` cell (`trust=UNK & fam=regime & dir=LONG`, n=31, WR=77%, PF=4.08) has `train_n=5`, `train_pf=0.0`, `holdout_pass: false`, `bonferroni_pass: false`. A train PF of 0.0 with a holdout PF of 9.49 is the **signature of a regime-terminal source that only started emitting in the holdout window** — i.e., the "edge" is a single source (`regime_terminal`) that didn't exist in train. This is exactly the H-035 pattern (sign instability across walk-forward windows). The honest number is the class-level 42.45% WR on 530 decisive trades — **a losing book**. The `consensus` cell you flagged isn't even in the top-3 here, which is itself telling: the consensus signal is so weak it doesn't survive cell aggregation.
- **90d expected P&L (1% risk, $100k):** **−$1,500 to −$2,500.** 530 decisive trades × 1% risk × (42.45% × avg_win − 57.55% × avg_loss). With PF<1 and 1% risk, expected ≈ −0.3% per trade × 530 × $1k = **−$1,590**, plus ~1bp FX slippage × 530 ≈ −$530. Call it **−$2,100**. This is the worst class in the book.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current (passing 23186/24066 = **96%** of scans!) to **≥ 70**, AND add a hard `source != 'regime_terminal'` exclusion in `hc_filter.js` until that source has ≥ 100 train-window trades. The 96% pass rate is the single most damning number in this entire report — the FOREX gate is not a gate, it's a pass-through.
- **Confidence (1-5):** **4** (very confident FOREX is a net loser; the gate is the problem).

---

### CRYPTO
- **Real/noise verdict:** **PLAUSIBLY REAL — the only class with a defensible edge.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell: n=180, WR=74.44%, WR_shrunk=72.0%, PF=3.80, **train_pf=4.26 (n=113), holdout_pf=3.05 (n=67), holdout_pass=true, bonferroni_pass=true, wr_z=6.56**. This is the *only* cell in the entire report that passes all four robustness checks (holdout, Bonferroni, shrunk WR ≥ 55%, PF ≥ 1.5). The train/holdout PF ratio (4.26 → 3.05) is a healthy degradation, not a collapse. **However:** (i) it's still `trust=UNK`, so the trust dimension is unpopulated and the cell is really "alpha_engine, conf 0.75-0.80, score decile 50" — a 3-dim cell, not 4; (ii) the `ml` cell you flagged isn't in the top-3, which is good — the suspicious PF numbers you were worried about are *not* the ones that survived; (iii) 180 trades is a real sample but not huge. Verdict: **real but fragile** — trade it small, monitor holdout PF weekly, kill if holdout PF < 1.5 for two consecutive weeks.
- **90d expected P&L (1% risk, $100k):** 180 trades × 1% risk × 1.47% avg_pnl = **~$2,650** gross. Apply realistic crypto slippage (~10bps round-trip on 180 trades ≈ −$1,800) and funding (~2bps/day × avg 3-day hold × 180 ≈ −$1,080): **net ≈ −$230 to +$800**. The edge is real but thin after costs. Size at **0.5% risk**, not 1%, until holdout PF is confirmed over a second 90d window. At 0.5%: **~$400 net**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** from current to **50** *specifically for the `alpha_engine` source with `conf ∈ [0.75, 0.80]`*, and add a source-conditional override in `hc_filter.js`: `if (p.source === 'alpha_engine' && p.conf >= 0.75 && p.conf < 0.80 && p.score >= 50) return true;` bypassing the trust>=60 check (since trust is UNK). This is the one gate change that *adds* edge rather than removing noise.
- **Confidence (1-5):** **3** (real signal, but thin after costs and trust dimension is broken).

---

### ETF
- **Real/noise verdict:** **NOISE / INSUFFICIENT SAMPLE.** n_closed=9, WR=22%. No edge, no sample.
- **90d expected P&L (1% risk, $100k):** **−$500** (9 trades, 2W/7L). Meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥ 65** and add the same min-n guard as INDEX (≥ 30 closed trades before surfacing).
- **Confidence (1-5):** **1**.

---

### UNKNOWN
- **Real/noise verdict:** **DATA BUG, NOT A CLASS.** n_closed=3, WR=0%. "UNKNOWN" should not be a tradeable asset class — it means the classifier failed. 1433 scans landed here. This is a **classification bug**, not a strategy result. Every `trust=UNK` cell in the report is downstream of this: the trust dimension is unpopulated because the classifier is dropping the field.
- **90d expected P&L (1% risk, $100k):** **−$300** (3 trades, 0W/3L). Meaningless.
- **Gate change:** **Do not gate — fix the classifier.** In `production_scanner.py`, add `assert asset_class != 'UNKNOWN'` before emitting a pick, and route UNKNOWN to a dead-letter queue. This is the root cause of the `trust=UNK` epidemic across every other class.
- **Confidence (1-5):** **5** (confident this is a bug).

---

### FUTURES
- **Real/noise verdict:** **NOISE / INSUFFICIENT SAMPLE.** n_closed=15, WR=40%. Consistent with H-005 (futures momentum anti-signal failed). No edge.
- **90d expected P&L (1% risk, $100k):** **−$300** (15 trades, 6W/9L at 1% risk ≈ −2% × $100k × 1% = −$300, plus slippage). Meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥ 65**; add min-n guard.
- **Confidence (1-5):** **2**.

---

### MEME
- **Real/noise verdict:** **NOISE / INSUFFICIENT SAMPLE.** n_closed=7, WR=14%. No edge.
- **90d expected P&L (1% risk, $100k):** **−$600** (7 trades, 1W/6L). Meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥ 70**; add min-n guard. MEME should probably be **disabled entirely** until n≥50.
- **Confidence (1-5):** **1**.

---

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=33, WR=39.39%. `passed_smart=2/578` — the gate is correctly rejecting almost everything, but the 545 "opened" trades suggest the opened-counter is bypassing the gate entirely (same bug as EQUITY/FOREX). No edge.
- **90d expected P&L (1% risk, $100k):** **−$700** (33 trades, 13W/20L at 1% risk ≈ −2.1% × $100k × 1% = −$700, plus slippage). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — the gate is already tight (2/578); the problem is the **opened counter bypassing it**. Fix the funnel arithmetic in `production_scanner.py` so `opened ≤ passed_smart`. No score change needed.
- **Confidence (1-5):** **3** (confident no edge; confident the bug is in the opened-counter).

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only at 0.5% risk.** It is the sole class with a cell that passes holdout + Bonferroni + shrunk-WR + PF thresholds simultaneously (n=180, holdout PF=3.05, wr_z=6.56). Expected net after realistic slippage/funding: **~$400 on $100k over 90d at 0.5% risk** — thin, but positive and defensible. Do not scale beyond 0.5% until a second 90d window confirms holdout PF ≥ 1.5.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.** It is the largest book (530 decisive trades), the worst WR (42.45%), and the most permissive gate (96% pass rate). The protocol says mutate before kill — so the mutation is: (1) raise `SMART_PICKS_MIN_SCORE_FOREX` to 70, (2) exclude `regime_terminal` source, (3) re-run 90d. If WR does not exceed 50% after mutation, **kill the FOREX book entirely**. The `regime_terminal` cell (train_n=5, train_pf=0.0, holdout_pf=9.49) is a leakage recurrence of the H-035 pattern and must be quarantined now, not after the mutation window.

**Two systemic bugs to fix before any of the above matters:**
1. **`passed_high_conviction = 0` everywhere.** The HC gate is dead. Either `trust` is never populated (root cause: the UNKNOWN classifier bug) or the gate is mis-wired. Fix the classifier first — every `trust=UNK` cell in this report is a symptom.
2. **`opened > passed_smart` in EQUITY, FOREX, BOND, UNKNOWN.** The opened-counter is bypassing the gate. This means the dashboard is showing trades that never passed a gate. Fix the funnel arithmetic in `production_scanner.py` before trusting any WR number on the dashboard.

**Brutal summary:** Of 10 asset classes, **1 has a defensible edge (CRYPTO, thin), 1 is a confirmed loser (FOREX), 1 is a data bug (UNKNOWN), and 7 have

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.46% raw WR on n=65 mean_reversion S40 cells is statistically impossible in live markets; WR_shrunk 87% and PF 233 still absurdly high; single-strategy concentration + train/holdout split both >99 PF screams data error or look-ahead.
- 90d expected P&L (1% risk, $100k): $0 (edge is invalid; any real deployment would lose after slippage and regime shift).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75 (block S40 entirely until root cause fixed).
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails Bonferroni and has n=20 only; matches previously rejected COT/inventory hypotheses.
- 90d expected P&L (1% risk, $100k): -$2,800 (current WR 55.88% on 68 closed trades at 1% risk produces net loss after typical 0.2–0.4% slippage).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 85 (raise floor to choke low-conviction flow).
- Confidence (1-5): 4

### INDEX
- Real/noise verdict: Noise — n=5 closed, WR 20%, no proven cells.
- 90d expected P&L (1% risk, $100k): -$1,200.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90.
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — top edges fail holdout and Bonferroni; regime cells show classic small-n instability.
- 90d expected P&L (1% risk, $100k): -$8,400 (530 decisive trades at 42.45% WR).
- Gate change: HC_FILTER_MIN_CONF = 0.82 (tighten client-side gate).
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Real — n=180, WR_shrunk 72%, PF 3.8, holdout passes, Bonferroni passes; only cell meeting PROVEN criteria without obvious leakage.
- 90d expected P&L (1% risk, $100k): +$14,200 (180 trades × ~1.47% avg edge × $1k risk, minus 0.3% slippage).
- Gate change: HC_FILTER_MIN_TRUST = 55 (lower slightly to let more alpha_engine S50 flow through while keeping conf>=0.75).
- Confidence (1-5): 4

### ETF
- Real/noise verdict: Noise — n=9, WR 22%, no cells.
- 90d expected P&L (1% risk, $100k): -$1,800.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80.
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n=3, WR 0%.
- 90d expected P&L (1% risk, $100k): -$600.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95 (effectively disable).
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n=15, no proven cells; matches rejected futures_momentum hypothesis.
- 90d expected P&L (1% risk, $100k): -$1,800.
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 88.
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n=7, WR 14%.
- 90d expected P&L (1% risk, $100k): -$1,200.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 92.
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n=33, no proven cells.
- 90d expected P&L (1% risk, $100k): -$2,100.
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 85.
- Confidence (1-5): 4

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated, holdout-passing edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its cells are leakage recurrence, not edge; route all EQUITY flow to audit_trail for root-cause mutation before any re-test. All other classes produce negative expectancy at 1% risk.
