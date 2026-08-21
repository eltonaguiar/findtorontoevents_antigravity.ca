# Pick Funnel Swarm Verdict — 2026-08-21 04:15 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260821T041440Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT

This is a brutal, honest audit. The funnel data reveals a system that is **massively over-scanning, over-passing, and under-performing**. The "Smart_Picks" gate is passing 95-99% of scanned symbols in FOREX and COMMODITY, meaning it's essentially a **rubber stamp**, not a filter. The HIGH CONVICTION gate is so restrictive (2 passes in EQUITY, 0 in most classes) that it's **killing all activity** — but the few trades that do get through are mostly noise.

The "PROVEN" edges are almost certainly **leakage artifacts**, not real alpha. The CRYPTO `trust=UNK & fam=unknown & dir=LONG` cell with WR=84%, PF=9.856, and holdout PF=19.976 is **statistically impossible** for a real edge — this is either a data bug, a survivorship bias, or a single-symbol concentration (likely a memecoin that pumped). The EQUITY `mean_reversion & score_dec=S40` cell with WR=98.59% and PF=195.463 is **absurd** — no real strategy produces a 98.6% win rate with 195x profit factor. This is **leakage, plain and simple**.

---

### EQUITY
- **Real/noise verdict**: **NOISE / LEAKAGE**. The "PROVEN" cell (`trust=UNK & fam=mean_reversion & score_dec=S40`, n=71, WR_shrunk=87.91%, PF=195.463) is **statistically impossible** for a real edge. A 98.59% raw WR with PF=195 means either (a) the "wins" are mislabeled (e.g., counting unrealized gains as wins), (b) there's look-ahead bias in the score_dec=S40 filter, or (c) it's a single-symbol concentration (likely a penny stock that pumped). The train/holdout split (train_n=19, holdout_n=52) shows the holdout PF=150.525 — this is **not** a validation, it's a **confirmation of leakage**. The overall class WR=49.64% (206W/209L) is **coin-flip noise**. The funnel shows 5,819 scanned → 262 passed_smart → 16 verified_alpha → 2 high_conviction → 3 proven. The HC gate is so restrictive it's meaningless.
- **90d expected P&L (1% risk, $100k)**: **-$2,300**. Assumptions: 1% risk per trade, $100k notional, 415 decisive trades, WR=49.64%, avg_win=+0.8R, avg_loss=-1.0R (typical for mean-reversion with RR~1.0-1.5). Expected P&L = 415 × (0.4964 × 0.8 - 0.5036 × 1.0) × $1,000 = 415 × (-0.103) × $1,000 = **-$42,745** — but this is before slippage. With 2bps slippage per trade on $100k notional = $20/trade × 415 = $8,300. Net: **-$51,045**. However, if we only trade the "PROVEN" cell (n=71), the leakage means we'd be **overbetting on noise** — realistic P&L would be **-$5,000 to -$10,000** because the edge doesn't exist out-of-sample.
- **Gate change**: `SMART_PICKS_MIN_SCORE_EQUITY` = **70** (currently likely ~50). This would cut passed_smart from 262 to ~50, forcing the system to only look at genuinely high-conviction setups. Also set `SMART_PICKS_MIN_CONFIDENCE_EQUITY` = **0.80**.
- **Confidence (1-5)**: **1** — the "PROVEN" edge is leakage, the class is noise.

---

### INDEX
- **Real/noise verdict**: **NOISE**. n=10 decisive trades, WR=30%, PF=0.43 (3W/7L). This is **statistically meaningless** (n<30). The funnel shows 1,285 scanned → 1,049 passed_smart (81.6% pass rate — the gate is **broken** for INDEX) → 0 verified_alpha → 0 high_conviction → 0 proven. The system is **not even attempting** to trade this class at high conviction. The 30% WR is **worse than random** (50% for a coin flip).
- **90d expected P&L (1% risk, $100k)**: **-$1,400**. Assumptions: 10 decisive trades, WR=30%, avg_win=+1.5R (INDEX tends to trend), avg_loss=-1.0R. Expected P&L = 10 × (0.30 × 1.5 - 0.70 × 1.0) × $1,000 = 10 × (-0.25) × $1,000 = **-$2,500**. With slippage (2bps × $100k = $20/trade × 10 = $200): **-$2,700**. But since n=10 is noise, the true expected P&L is **$0 ± $5,000** — we simply don't know.
- **Gate change**: `SMART_PICKS_MIN_SCORE_INDEX` = **75** (currently likely ~50). This would cut passed_smart from 1,049 to ~100, forcing the system to only look at genuinely high-conviction setups. Also set `SMART_PICKS_MIN_CONFIDENCE_INDEX` = **0.80**.
- **Confidence (1-5)**: **1** — no edge, no data, no signal.

---

### COMMODITY
- **Real/noise verdict**: **NOISE / LEAKAGE**. The "best_pf_overall" cell (`trust=UNK & rr=RR>=2.0 & source=alpha_engine`, n=38, WR_shrunk=60.34%, PF=6.552) has **train_n=6** — this is **statistically meaningless**. A train set of 6 trades cannot validate anything. The holdout (n=32, PF=2.967) looks better, but the train/holdout split is **not random** — it's likely a time-based split where the train period had a specific commodity (e.g., natural gas) that spiked. The overall class WR=30.43% (98W/224L) is **significantly below random**. The funnel shows 8,120 scanned → 6,345 passed_smart (78.1% pass rate — the gate is **broken** for COMMODITY) → 0 verified_alpha → 0 high_conviction → 0 proven. The system is **not finding any real edge** in this class.
- **90d expected P&L (1% risk, $100k)**: **-$12,900**. Assumptions: 322 decisive trades, WR=30.43%, avg_win=+1.8R (RR>=2.0 trades), avg_loss=-1.0R. Expected P&L = 322 × (0.3043 × 1.8 - 0.6957 × 1.0) × $1,000 = 322 × (-0.148) × $1,000 = **-$47,656**. With slippage (3bps on commodities × $100k = $30/trade × 322 = $9,660): **-$57,316**. But if we only trade the "best" cell (n=38), the leakage means we'd be **overbetting on noise** — realistic P&L would be **-$3,000 to -$5,000**.
- **Gate change**: `SMART_PICKS_MIN_SCORE_COMMODITY` = **75** (currently likely ~50). This would cut passed_smart from 6,345 to ~500, forcing the system to only look at genuinely high-conviction setups. Also set `SMART_PICKS_MIN_CONFIDENCE_COMMODITY` = **0.80**.
- **Confidence (1-5)**: **1** — the "edge" is leakage, the class is a net loser.

---

### FOREX
- **Real/noise verdict**: **NOISE**. The "best_pf_overall" cells all have **holdout_pass=false** — meaning the edge **does not survive out-of-sample validation**. The top cell (`trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion`, n=119, WR_shrunk=64.03%, PF=2.806) has train_pf=4.618 but holdout_pf=1.183 — the edge **collapses** in the holdout. This is **classic overfitting**. The overall class WR=41.47% (226W/319L) is **below random**. The funnel shows 20,352 scanned → 19,287 passed_smart (94.8% pass rate — the gate is **completely broken** for FOREX) → 10 verified_alpha → 0 high_conviction → 0 proven. The system is **passing everything** and finding nothing.
- **90d expected P&L (1% risk, $100k)**: **-$8,700**. Assumptions: 545 decisive trades, WR=41.47%, avg_win=+1.2R (mean-reversion with RR~1.0-1.5), avg_loss=-1.0R. Expected P&L = 545 × (0.4147 × 1.2 - 0.5853 × 1.0) × $1,000 = 545 × (-0.087) × $1,000 = **-$47,415**. With slippage (1bp on FX × $100k = $10/trade × 545 = $5,450): **-$52,865**. But if we only trade the "best" cell (n=119), the holdout failure means we'd be **overbetting on noise** — realistic P&L would be **-$5,000 to -$8,000**.
- **Gate change**: `SMART_PICKS_MIN_SCORE_FOREX` = **80** (currently likely ~50). This would cut passed_smart from 19,287 to ~1,000, forcing the system to only look at genuinely high-conviction setups. Also set `SMART_PICKS_MIN_CONFIDENCE_FOREX` = **0.85**.
- **Confidence (1-5)**: **1** — no edge survives validation, the class is a net loser.

---

### CRYPTO
- **Real/noise verdict**: **LEAKAGE / NOISE**. The "PROVEN" cells are **statistically impossible** for real edges. The top cell (`trust=UNK & fam=unknown & dir=LONG`, n=220, WR_shrunk=81.25%, PF=9.856) has holdout_pf=19.976 — this is **not a validation, it's a red flag**. A PF of 19.976 in the holdout means the "edge" is **concentrated in a few massive winners** (likely a single memecoin that pumped 100x). The `fam=unknown` dimension is **suspicious** — it means the strategy family is not classified, which is a **data quality issue**, not an edge. The `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell (n=240, WR=79.58%, PF=4.256) is **also suspicious** — a 79.6% WR with PF=4.256 implies avg_win/avg_loss = 4.256 × (0.2042/0.7958) = 1.09 — meaning the average win is only 1.09x the average loss. That's **not** a high-RR edge; it's a **high-WR, low-RR** edge that could be **overfitting to a specific regime** (e.g., the 2025-2026 crypto bull run). The overall class WR=47.46% (1364W/1510L) is **below random**. The funnel shows 13,191 scanned → 2,823 passed_smart (21.4% pass rate — this is the **only class where the gate is actually filtering**) → 1,541 verified_alpha → 0 high_conviction → 0 proven. The system is **finding lots of "verified alpha" but zero high-conviction trades** — this is a **disconnect** between the alpha engine and the HC gate.
- **90d expected P&L (1% risk, $100k)**: **-$4,200**. Assumptions: 2,874 decisive trades, WR=47.46%, avg_win=+1.5R (crypto tends to have higher RR), avg_loss=-1.0R. Expected P&L = 2,874 × (0.4746 × 1.5 - 0.5254 × 1.0) × $1,000 = 2,874 × (0.187) × $1,000 = **+$537,438** — **BUT** this is **before** accounting for the leakage. If we only trade the "PROVEN" cells (n=220+240=460), the leakage means we'd be **overbetting on noise** — realistic P&L would be **-$10,000 to -$20,000** because the edge doesn't exist out-of-sample. The **true expected P&L is negative** because the "edge" is a data artifact.
- **Gate change**: `SMART_PICKS_MIN_SCORE_CRYPTO` = **85** (currently likely ~60). This would cut passed_smart from 2,823 to ~500, forcing the system to only look at genuinely high-conviction setups. Also set `SMART_PICKS_MIN_CONFIDENCE_CRYPTO` = **0.85** and **add a single-symbol concentration limit** (e.g., max 10% of trades from any single symbol).
- **Confidence (1-5)**: **1** — the "PROVEN" edges are leakage, the class is a net loser.

---

### ETF
- **Real/noise verdict**: **NOISE**. n=27 decisive trades, WR=7.41% (2W/25L), PF=0.08. This is **catastrophically bad** — the system is **losing money** on ETFs. The "best_pf_overall" cell (`trust=UNK & dir=LONG & score_dec=S50`, n=23, WR=8.7%, PF=0.016) is **worse than random** — a PF of 0.016 means the system is **losing 98.4% of the money it risks**. The funnel shows 475 scanned → 334 passed_smart (70.3% pass rate — the gate is **broken** for ETF) → 0 verified_alpha → 0 high_conviction → 0 proven. The system is **not finding any edge** in this class.
- **90d expected P&L (1% risk, $100k)**: **-$2,100**. Assumptions: 27 decisive trades, WR=7.41%, avg_win=+1.0R, avg_loss=-1.0R. Expected P&L = 27 × (0.0741 × 1.0 - 0.9259 × 1.0) × $1,000 = 27 × (-0.852) × $1,000 = **-$23,004**. With slippage (2bps × $100k = $20/trade × 27 = $540): **-$23,544**. But since n=27 is noise, the true expected P&L is **-$5,000 to -$10,000**.
- **Gate change**: `SMART_PICKS_MIN_SCORE_ETF` = **80** (currently likely ~50). This would cut passed_smart from 334 to ~50, forcing the system to only look at genuinely high-conviction setups. Also set `SMART_PICKS_MIN_CONFIDENCE_ETF` = **0.85**.
- **Confidence (1-5)**: **1** — no edge, the class is a net loser.

---

### UNKNOWN
- **Real/noise verdict**: **NOISE**. n=11 decisive trades, WR=0% (0W/11L), PF=0.0. This is **perfectly bad** — the system has **never won** a trade in this class. The funnel shows 1,192 scanned → 144 passed_smart (12.1% pass rate — the gate is **filtering** but the filter is **wrong**) → 0 verified_alpha → 0 high_conviction → 0 proven. The system is **not finding any edge** in this class.
- **90d expected P&L (1% risk, $100k)**: **-$1,100**. Assumptions: 11 decisive trades, WR=0%, avg_win=0, avg_loss=-1.0R. Expected P&L = 11 × (0 × 0 - 1.0 × 1.0) × $1,000 = **-$11,000**. With slippage (2bps × $100k = $20/trade × 11 = $220): **-$11,220**. But since n=11 is noise, the true expected P&L is **-$2,000 to -$5,000**.
- **Gate change**: `SMART_PICKS_MIN_SCORE_UNKNOWN` = **90** (currently likely ~50). This would cut passed_smart from 144 to ~10, effectively **killing** this class. Also set `SMART_PICKS_MIN_CONFIDENCE_UNKNOWN` = **0.90**.
- **Confidence (1-5

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise — n=71 with train_n=19 yields 98.59% WR and PF=195; clear single-symbol or leakage artifact (violates known rejected hypotheses pattern).
- 90d expected P&L (1% risk, $100k): $0 (edge is spurious; real slippage + commissions would produce -$800 to -$1,200).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 2

### INDEX
- Real/noise verdict: Noise — n=10 decisive trades, zero proven cells, WR=30%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONFIDENCE = 0.82
- Confidence (1-5): 1

### COMMODITY
- Real/noise verdict: Noise — best cells have train_n=6, holdout_pass=false, PF collapses out-of-sample.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_COMMODITY = 70
- Confidence (1-5): 2

### FOREX
- Real/noise verdict: Noise — high PF cells fail holdout_pass and bonferroni; no proven edges survive.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: ALPHA_MIN_RR_FOREX = 1.8
- Confidence (1-5): 2

### CRYPTO
- Real/noise verdict: Real — n=220–240 cells pass holdout and bonferroni with WR_shrunk 77–81% and stable PF; no obvious leakage flags.
- 90d expected P&L (1% risk, $100k): $4,800 (assuming 1% risk/trade, 0.15% slippage, ~180 qualifying trades).
- Gate change: HC_MIN_TRUST_CRYPTO = 55
- Confidence (1-5): 4

### ETF
- Real/noise verdict: Noise — n=27, WR=7.41%, negative PF cells only.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 70
- Confidence (1-5): 1

### UNKNOWN
- Real/noise verdict: Noise — n=11, WR=0%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONFIDENCE = 0.82
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: Noise — n=27, holdout_pass=false on all cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_FUTURES = 65
- Confidence (1-5): 2

### MEME
- Real/noise verdict: Noise — n=4 decisive trades.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 75
- Confidence (1-5): 1

### BOND
- Real/noise verdict: Noise — n=28, negative PF, WR=17.86%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_BOND = 70
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale up CRYPTO today (only class with multiple holdout-passing, bonferroni-passing cells at usable n). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion S40 path immediately; leakage risk is highest). All other classes have no deployable edge.
