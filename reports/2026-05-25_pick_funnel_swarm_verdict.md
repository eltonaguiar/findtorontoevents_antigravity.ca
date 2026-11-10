# Pick Funnel Swarm Verdict — 2026-11-10 04:06 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261110T040600Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` across every single class.** The HC gate (`score>=80 & conf>=0.75 & trust>=60`) has fired **zero** times in 90 days. That is not a filter — that is a dead gate. Every "edge" below is therefore *pre-HC* and would never have reached a real-money book under current rules.
2. **`opened` ≫ `passed_smart` in most classes** (EQUITY 5760 opened vs 231 smart; FOREX 23327 vs 23972 — the only class where smart≈opened). The funnel is not actually gating; it's logging. "Opened" is essentially "scanned minus a rounding error."
3. **`trust=UNK` dominates every PROVEN cell.** Every single proven edge in FOREX, CRYPTO, and EQUITY is `trust=UNK`. That means the trust dimension is unpopulated for the winning trades — the "edge" is defined by a *missing* field, which is a classic leakage signature (the trades that win are the ones where trust scoring failed to run).

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** `conf=C<0.60 & fam=mean_reversion` with n=60, WR=98.33%, PF=171.14 is not an edge — it is a bug. A PF of 171 means average win is ~171× average loss; that is only possible if losses are being truncated (stop never hit / marked as win on timeout / PnL sign error) or if the "loss" bucket is empty by construction. `holdout_pf=99.0` is the sentinel value for "zero losses in holdout" — 29/29 holdout wins is not a strategy, it's a data pipeline that doesn't record losses. `wr_z=7.487` and `bonferroni_pass=true` are meaningless when the underlying PnL distribution is degenerate. **Do not trade this. Investigate the loss-recording path in `production_scanner.py` first.** The 112 closed / 5760 opened ratio (1.9%) also means 98% of "opened" equity trades never resolved — the WR is computed on a 2% survivor sample.
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** If forced to model the reported numbers naively: 112 trades × 1% × $100k × (0.6964×avg_win − 0.3036×avg_loss). With avg_pnl_pct=1.6163 on the winning cell and a plausible 1:1 R, naive estimate ≈ **+$4,200**, but this is fiction given the PF=171 degeneracy. Realistic post-fix estimate: **−$1,500 to +$800**, i.e. indistinguishable from zero.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — but the real fix is upstream: add a **loss-recording assertion** in `production_scanner.py` that rejects any closed trade with `pnl_pct == 0` or missing stop-hit flag. Until PF<20 is enforced as a sanity ceiling, no equity gate value matters.
- **Confidence (1-5):** **1**

### COMMODITY
- **Real/noise verdict:** **NOISE.** No PROVEN cells (n_closed=39, below the n≥20-per-cell threshold for most dims). Best PF overall is `trust=UNK & dir=LONG & source=alpha_engine` at n=28, WR=64.29%, PF=2.138 — but `holdout_pf=1.137` and `holdout_pass=false`, `bonferroni_pass=false`. Train PF 4.02 → holdout 1.14 is textbook overfit decay. Also note H-001 (COT leakage) and H-036 (inventory gate rejected) are both in this class — the class has a documented history of leakage. 3572/5751 passed_smart (62%) is a gate that isn't gating.
- **90d expected P&L (1% risk, $100k):** **$0.** 39 closed trades is not a sample. Naive: 39 × 1% × $100k × (0.6923×0.845 − 0.3077×0.845) ≈ **+$1,270**, but holdout PF 1.14 says the true edge is ~0. **Expected: −$200 to +$400.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **75** (from current, which is clearly permissive given 62% pass rate). This class should be in observation, not deployment.
- **Confidence (1-5):** **2**

### FOREX
- **Real/noise verdict:** **SUSPICIOUS — likely leakage or single-source concentration.** The PROVEN cell is `trust=UNK & conf=C>=0.90 & fam=regime` / `source=regime_terminal`, n=40, WR=85%, PF=9.267, `holdout_pf=99.0` (sentinel = zero holdout losses, n=10). Three red flags: (1) `trust=UNK` on the winning cell — trust scoring didn't run; (2) `source=regime_terminal` — a single source, and "terminal" naming suggests a terminal-state/end-of-bar signal that may be look-ahead; (3) holdout n=10 with 0 losses is not evidence. The `wr_z=4.427` is computed on a sample where the loss distribution is degenerate. **This is the cell the prompt flagged as suspicious, and it is.** The class-level WR of 51.75% (n=1268, decisive 429) is the honest number — and 51.75% at 1:1 R is a losing strategy after costs. The "edge" is 40 trades out of 429 decisive (9%) and is almost certainly a `regime_terminal` artifact.
- **90d expected P&L (1% risk, $100k):** **Negative.** Class-level: 429 decisive × 1% × $100k × (0.5175 − 0.4825) × avg_R ≈ **−$1,500 to −$3,000** after spread/slippage (FX spreads 0.5–1.5 pips on majors, wider on crosses). The 40-trade "edge" cell, if real, would add ~+$2,400 — but I do not believe it is real. **Net expected: −$1,000 to −$2,500.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **78**, AND add a hard rule in `quality_gates.py`: **reject any pick where `trust == UNK`**. That single rule kills the entire "proven" FOREX edge, which is the correct outcome — if trust scoring can't run, the pick shouldn't trade.
- **Confidence (1-5):** **2** (that the edge is fake); **4** (that the class-level 51.75% is the real number)

### CRYPTO
- **Real/noise verdict:** **MOST PLAUSIBLE OF THE PROVEN CELLS, BUT STILL OVERSTATED.** `trust=UNK & conf=C0.75-0.80 & source=alpha_engine`, n=219, WR=63.01%, wr_shrunk=61.92%, PF=1.82, train_pf=2.125, holdout_pf=1.563 (n=127), `holdout_pass=true`, `bonferroni_pass=true`. This is the only cell in the entire dataset where train and holdout are both >1.5 and the holdout n is large (127). That is a *real* signal shape. **However:** (1) `trust=UNK` again — the edge is defined by missing trust; (2) the `best_pf_overall` cell (`rr=RR1.5-2.0`) has `holdout_pf=1.135` and `holdout_pass=false` — so the RR dimension is *not* the edge, the conf+source is; (3) class-level WR is 45.73% (n=2296) — the 219-trade cell is 9.5% of the sample and the other 90% is losing. The edge is real but narrow. **This is the one class where I'd say "probably real, size small."**
- **90d expected P&L (1% risk, $100k):** 219 trades × 1% × $100k × (0.6192×avg_win_R − 0.3808×avg_loss_R). With PF=1.82 and WR=61.9%, implied avg_win/avg_loss ≈ 1.12. Expected R per trade ≈ 0.6192×1.12 − 0.3808×1.0 = **+0.312R**. 219 × 0.01 × $100k × 0.312 = **+$68,300 gross**. Apply 15% slippage/fee haircut (crypto taker fees 0.04–0.10% per side, funding, slippage on alts): **≈ +$58,000**. **But** this assumes you can actually isolate the 219-trade cell — the current funnel opens 10,032 crypto trades, of which 2,309 closed at 45.73% WR. If you trade the *class*, you lose. If you trade *only the cell*, you win. **Realistic deployable estimate: +$45,000 to +$60,000** if the cell filter is enforced.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — but the higher-leverage change is in `hc_filter.js`: **lower `HC_MIN_CONF` from 0.75 to 0.72** *and* add `source == 'alpha_engine'` as a required HC condition. The current HC gate requires conf≥0.75, which excludes the 0.75–0.80 band that is the actual edge — wait, no, 0.75–0.80 *is* included. The real problem is `trust>=60` in HC, and every winning cell is `trust=UNK`. **So: change `HC_MIN_TRUST` from 60 to 0 (or treat UNK as pass) — but ONLY for CRYPTO, and ONLY when `source=alpha_engine`.** That is the single change that would have let the 219-trade edge through the HC gate. Alternatively, and more safely: **`SMART_PICKS_MIN_SCORE_CRYPTO = 72`** with a source whitelist.
- **Confidence (1-5):** **3** (edge is real but narrow and trust-UNK is a smell)

### BOND
- **Real/noise verdict:** **NO EDGE.** n_closed=31, WR=38.71%, no proven cells, no best-PF cells. 1/1071 passed_smart (0.09%) — the gate is essentially closed, which is correct. 1040 opened / 31 closed = 3% resolution. This class should not be traded.
- **90d expected P&L (1% risk, $100k):** **Negative.** 31 × 1% × $100k × (0.3871 − 0.6129) × avg_R ≈ **−$700** (before costs; after costs worse). **Expected: −$700 to −$1,200.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — leave at current (effectively closed). **Do not lower it.** If anything, add `SMART_PICKS_MIN_SCORE_BOND = 95` to formally kill it.
- **Confidence (1-5):** **5** (that there is no edge)

### ETF
- **Real/noise verdict:** **NO EDGE — actively bad.** n_closed=10, WR=10.0% (1 win, 9 losses). 278/319 passed_smart (87%!) — the ETF gate is the most permissive in the system and the results are catastrophic. This is the clearest "gate is broken" signal in the dataset.
- **90d expected P&L (1% risk, $100k):** **Negative.** 10 × 1% × $100k × (0.10 − 0.90) × avg_R ≈ **−$800** (tiny n, but direction is unambiguous). **Expected: −$800 to −$1,000.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **85** immediately. 87% pass rate on a 10% WR class is a gate that is actively harmful.
- **Confidence (1-5):** **5** (that the gate is broken); **3** (on the exact P&L given n=10)

### FUTURES
- **Real/noise verdict:** **NO EDGE.** n_closed=16, WR=37.5%, no proven cells. H-005 (futures_momentum_anti_signal) is already in the rejected registry — this class has a documented failed hypothesis. 128/179 passed_smart (72%) — gate too permissive.
- **90d expected P&L (1% risk, $100k):** **Negative.** 16 × 1% × $100k × (0.375 − 0.625) × avg_R ≈ **−$400**. **Expected: −$400 to −$600.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **80**.
- **Confidence (1-5):** **4** (no edge)

### MEME
- **Real/noise verdict:** **NO EDGE.** n_closed=9, WR=33.33%. 14/26 passed_smart (54%). Sample too small to conclude anything except "don't trade it."
- **90d expected P&L (1% risk, $100k):** **Negative.** 9 × 1% × $100k × (0.333 − 0.667) × avg_R ≈ **−$300**. **Expected: −$300 to −$500.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **85** (or disable entirely; n=26 scanned is not a class, it's noise).
- **Confidence (1-5):** **4** (no edge)

### INDEX
- **Real/noise verdict:** **INSUFFICIENT DATA.** n_closed=1. 1585/2083 passed_smart (76%) — gate too permissive, but with 1 closed trade there is nothing to say. Do not trade.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1, no estimate possible).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **80** pending data.
- **Confidence (1-5):** **1** (no data)

### UNKNOWN
- **Real/noise verdict:** **NO EDGE / DATA HYGIENE FAILURE.** n_closed=3, WR=0%. 126/1318 passed_smart. The existence of an "UNKNOWN" asset class with 1318 scanned and 1315 opened is itself a bug — these should be rejected at ingestion, not classified.
- **90d expected P&L (1% risk, $100k):** **$0** (n=3).
- **Gate change:** Add an ingestion rule in `production_scanner.py`: **reject any pick where `asset_class == 'UNKNOWN'`**. This is not a threshold change; it's a data-integrity fix.
- **Confidence (1-5):** **5** (that this class should not exist)

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the `source=alpha_engine & conf∈[0.75,0.80]` cell.** It is the only cell in the entire 90-day dataset with (a) n≥200, (b) train_pf>2 and holdout_pf>1.5, (c) holdout n>100, (d) `bonferroni_pass=true`. Expected 90d P&L on the isolated cell at 1% risk / $100k: **+$45k to +$60k**. Size at **0.5% risk per trade** for the first 30 days (not 1%) given the `trust=UNK` smell, then step to 1% if live WR holds ≥58%.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

- **EQUITY** — the PF=171 / WR=98.3% / holdout_pf=99.0 cell is a **loss-recording bug**, not an edge. Mutate axis 1 (data integrity: assert losses are recorded) before any gate change. Do not deploy.
- **FOREX** — the `regime_terminal` cell is the leakage recurrence the prompt warned about. Mutate axis 2 (source isolation: run `regime_terminal` in shadow for 30 days, compare to live) before touching `SMART_PICKS_MIN_SCORE_FOREX`. The honest class-level 51.75% WR is a losing strategy after FX spreads.
- **ETF** — 87% pass rate on a 10% WR class is the single most broken gate in the system. Mutate axis 3 (threshold: `SMART_PICKS_MIN_SCORE_ETF

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. n=60, WR_shrunk=86.25, PF=171.14 is statistically impossible without data error or look-ahead; matches known rejected hypotheses patterns.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid; real slippage + costs would produce net loss).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf_overall cells fail holdout and Bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Likely leakage. n=40, WR_shrunk=73.33, PF=9.267 with holdout_pf=99 on n=10 is unrealistic; regime_terminal source shows classic single-source overfitting.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid)
- Gate change: HC_MIN_CONF = 0.92
- Confidence (1-5): 5

**### CRYPTO**
- Real/noise verdict: Marginal but plausible. n=219, WR_shrunk=61.92, PF=1.82 passes holdout/Bonferroni; best_pf_overall fails holdout so ignore.
- 90d expected P&L (1% risk, $100k): ~$2,800 (assume 1% risk/trade, 0.15% slippage, ~180 qualifying trades)
- Gate change: ALPHA_ENGINE_MIN_TRUST = 55
- Confidence (1-5): 3

**### BOND**
- Real/noise verdict: Noise. n=31 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: Noise. n=10 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: Noise. n=3 total.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: Noise. n=1 total.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: Noise. n=16 total, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: Noise. n=9 total.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: CRYPTO (only class with statistically defensible cells and sufficient n).  
Demote: EQUITY (clear leakage signature; remove from production until root cause fixed per MUTATION_THREE_AXIS_PROTOCOL).
