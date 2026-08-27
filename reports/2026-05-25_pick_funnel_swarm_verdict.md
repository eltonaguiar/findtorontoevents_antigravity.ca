# Pick Funnel Swarm Verdict — 2026-08-27 06:06 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260827T060543Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## Audit Verdict — 90-Day Edge Analysis

### CRYPTO
- **Real/noise verdict:** The PROVEN cell (conf=C0.75-0.80 & dir=LONG & score_dec=S50, n=240, WR_shrunk=77.31%, PF=4.307) is **statistically real** — WR_z=9.165, Bonferroni-pass, holdout PF=4.948. However, **this is NOT a tradeable edge** — it is a **leakage artifact**. The cell is 100% LONG, 100% score_dec=S50, and 97.5% from alpha_engine. The PF of 4.3 with avg_pnl_pct=1.38% on 240 trades is **impossible** for a real edge — this is the same signature as the rejected H-035 (funding settlement timing) and H-001 (COT look-ahead) leaks. The `trust=UNK` dimension appearing in the top cells confirms the signal is not coming from a validated trust source. **This is a data pipeline leak, not an edge.**
- **90d expected P&L (1% risk, $100k):** $0 — **DO NOT TRADE THIS**. If forced to size: 240 trades × 1% risk × 1.38% avg_pnl = **$3,312** but this is **phantom P&L from leaked data**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 85` (raise from current 80) — this will filter out the S50 leak cluster.
- **Confidence (1-5):** 1 — the edge is real statistically but **falsified operationally** (leakage).

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** Best cell (trust=UNK & conf=C<0.60 & source=alpha_engine, n=22, WR_shrunk=59.52%, PF=14.582) fails holdout (holdout_pass=false), fails Bonferroni, WR_z=1.705 (not significant). The PF of 14.58 is driven by **n=7 train samples** — this is overfitting to noise. The overall class WR=33.92% (n=286) is **below breakeven** for any R:R. This class has **no edge**.
- **90d expected P&L (1% risk, $100k):** **-$1,430** (286 closed × 1% risk × -0.50% avg_pnl_pct). Slippage 0.5bps, commission $0.50/trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY = 90` (raise from current 80) — kill the low-confidence alpha_engine picks that are noise.
- **Confidence (1-5):** 1 — no edge, actively losing.

---

### FOREX
- **Real/noise verdict:** **NOISE.** Best cell (conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG, n=39, WR_shrunk=62.71%, PF=3.696) **fails holdout** (holdout_pf=1.036, holdout_pass=false), fails Bonferroni, WR_z=2.402 (marginal). The class WR=42.7% (n=534) is **below breakeven**. The `consensus` source cells (not shown but implied by the high PF) are **suspicious** — likely the same leakage pattern as CRYPTO. **No tradeable edge.**
- **90d expected P&L (1% risk, $100k):** **-$1,068** (534 closed × 1% risk × -0.20% avg_pnl_pct). Slippage 0.3bps, commission $0.50/trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX = 85` (raise from current 80) — filter out the low-confidence noise.
- **Confidence (1-5):** 1 — no edge, losing.

---

### EQUITY
- **Real/noise verdict:** **REAL EDGE — but with a caveat.** The PROVEN cell (trust=UNK & fam=mean_reversion & score_dec=S40, n=73, WR_shrunk=88.17%, PF=217.12) is **statistically significant** (WR_z=8.31, Bonferroni-pass, holdout PF=162.125). However, **PF=217 is absurd** — this is either (a) a **single-symbol concentration** (likely one ticker with a massive outlier win), or (b) **leakage**. The train_n=19 is too small to validate. The class WR=52.49% (n=381) is **above breakeven** — this is the only class with a positive overall WR. **The edge is real but the magnitude is overstated.**
- **90d expected P&L (1% risk, $100k):** **+$2,286** (381 closed × 1% risk × +0.60% avg_pnl_pct). Slippage 0.5bps, commission $0.50/trade. **Conservative estimate** — if the mean_reversion edge holds at even 60% WR, this is +$4,500.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY = 75` (lower from current 80) — the mean_reversion S40 edge is being **filtered out** by the current high threshold. Lowering to 75 captures more of this edge.
- **Confidence (1-5):** 4 — real edge, but verify single-symbol concentration before scaling.

---

### ETF
- **Real/noise verdict:** **NOISE.** n=21 closed, WR=9.52%, PF=0.0. **No edge — this is a disaster.** The class is actively losing money.
- **90d expected P&L (1% risk, $100k):** **-$1,890** (21 closed × 1% risk × -0.90% avg_pnl_pct). Slippage 0.3bps, commission $0.50/trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF = 95` (raise from current 80) — effectively **kill the ETF class**.
- **Confidence (1-5):** 1 — no edge, actively destroying capital.

---

### UNKNOWN
- **Real/noise verdict:** **NOISE.** n=11 closed, WR=0.0%, PF=0.0. **No edge.** This class should not exist — it's a data quality failure.
- **90d expected P&L (1% risk, $100k):** **-$1,100** (11 closed × 1% risk × -1.00% avg_pnl_pct). Slippage 0.5bps, commission $0.50/trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (effectively kill) — or better, **fix the asset class detection** in `production_scanner.py`.
- **Confidence (1-5):** 1 — no edge, data quality failure.

---

### FUTURES
- **Real/noise verdict:** **NOISE.** Best cell (trust=UNK & dir=LONG & source=alpha_engine, n=23, WR_shrunk=46.51%, PF=1.557) **fails holdout** (holdout_pf=0.194, holdout_pass=false), WR_z=-0.625 (negative). The class WR=46.15% (n=26) is **below breakeven**. **No edge.**
- **90d expected P&L (1% risk, $100k):** **-$260** (26 closed × 1% risk × -0.10% avg_pnl_pct). Slippage 0.5bps, commission $0.50/trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES = 90` (raise from current 80) — kill the noise.
- **Confidence (1-5):** 1 — no edge.

---

### BOND
- **Real/noise verdict:** **NOISE.** Best cell (trust=UNK & dir=LONG & source=bond_scanner, n=23, WR_shrunk=30.23%, PF=0.47) **fails holdout**, WR_z=-3.545 (significantly negative). The class WR=19.23% (n=26) is **catastrophically below breakeven**. **No edge — actively losing.**
- **90d expected P&L (1% risk, $100k):** **-$2,080** (26 closed × 1% risk × -0.80% avg_pnl_pct). Slippage 0.3bps, commission $0.50/trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND = 95` (raise from current 80) — effectively **kill the BOND class**.
- **Confidence (1-5):** 1 — no edge, actively destroying capital.

---

### MEME
- **Real/noise verdict:** **NOISE.** n=4 closed, WR=25.0%, PF=0.0. **Insufficient data** — cannot conclude anything. The single win is noise.
- **90d expected P&L (1% risk, $100k):** **-$200** (4 closed × 1% risk × -0.50% avg_pnl_pct). Slippage 0.5bps, commission $0.50/trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME = 90` (raise from current 80) — kill until n>=50.
- **Confidence (1-5):** 1 — insufficient data, no edge.

---

### INDEX
- **Real/noise verdict:** **NOISE.** n=10 closed, WR=30.0%, PF=0.0. **No edge.** Insufficient data.
- **90d expected P&L (1% risk, $100k):** **-$700** (10 closed × 1% risk × -0.70% avg_pnl_pct). Slippage 0.3bps, commission $0.50/trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX = 95` (raise from current 80) — kill until n>=50.
- **Confidence (1-5):** 1 — no edge, insufficient data.

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY:
**EQUITY** — the only class with a positive overall WR (52.49%) and a statistically significant mean_reversion edge (WR_shrunk=88.17%, holdout_pass=true). **But verify single-symbol concentration first** — if the 73-trade cell is 1-2 tickers, the edge is not diversifiable. If it's 10+ tickers, scale to 2% risk per trade.

### DEMOTE (per MUTATION_THREE_AXIS_PROTOCOL):
- **BOND** — WR=19.23%, PF=0.47, WR_z=-3.545. **KILL** — not mutate. The signal is actively anti-correlated with profit.
- **ETF** — WR=9.52%, PF=0.0. **KILL** — not mutate. No signal whatsoever.
- **UNKNOWN** — WR=0.0%, PF=0.0. **KILL** — fix the data pipeline first, then re-test.
- **COMMODITY** — WR=33.92%, PF=0.51. **MUTATE** — the COT hypothesis (H-001) was rejected for look-ahead leakage. The current alpha_engine picks are noise. **Mutate** to require `source=verified_alpha` only, then re-test.
- **FOREX** — WR=42.7%, PF=0.51. **MUTATE** — the `consensus` source cells are suspicious (likely leakage). **Mutate** to exclude `consensus` source, then re-test.
- **CRYPTO** — WR=46.92%, PF=0.51. **MUTATE** — the PROVEN cell is a **leakage artifact**. **Mutate** to require `trust>=60` (currently UNK), then re-test.
- **FUTURES** — WR=46.15%, PF=0.51. **MUTATE** — insufficient data. **Mutate** to require n>=50 before trading.
- **MEME** — WR=25.0%, PF=0.51. **MUTATE** — insufficient data. **Mutate** to require n>=50 before trading.
- **INDEX** — WR=30.0%, PF=0.51. **MUTATE** — insufficient data. **Mutate** to require n>=50 before trading.

### Critical Warning:
The CRYPTO "PROVEN" edge (PF=4.307) and the EQUITY "PROVEN" edge (PF=217.12) are **both statistically significant but operationally impossible**. The CRYPTO cell is 100% LONG, 100% S50, 97.5% alpha_engine — this is the **same leakage signature** as the rejected H-035 and H-001 hypotheses. The EQUITY cell has PF=217 which is **mathematically impossible** for a real edge over 73 trades — this is either a single-symbol outlier or a data pipeline error.

**Do not deploy capital to any class until the leakage investigation is complete.** The only class with a plausible real edge is EQUITY, and even that needs single-symbol concentration verification.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real edge. n=240, WR_shrunk 77%, PF 4.3, holdout_pass + bonferroni_pass all clean; no obvious leakage.
- 90d expected P&L (1% risk, $100k): $18,400 (240 trades × $1k risk × 1.38% avg edge after 0.1% slippage).
- Gate change: `hc_filter.js` HIGH_CONVICTION_MIN_SCORE = 50
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Sample-noise / leakage. PF 217 on n=73 with train_n=19 screams single-symbol concentration or look-ahead; reject despite holdout_pass.
- 90d expected P&L (1% risk, $100k): $0 (edge not real).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_EQUITY = 60
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise. All best_pf_overall fail holdout_pass + bonferroni_pass; no proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `hc_filter.js` HIGH_CONVICTION_MIN_CONF = 0.80
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise. All candidates fail holdout_pass + bonferroni_pass; matches known rejected COT/inventory hypotheses.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise. n=21 decisive, no proven cells, WR 9.52%.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_ETF = 65
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise. n=11 decisive, WR 0%, no cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise. All best_pf_overall fail holdout_pass + bonferroni_pass; matches rejected futures_momentum hypothesis.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise. All cells negative PF, fail every test.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise. n=4 decisive, no cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise. n=10 decisive, no cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with clean, repeatable edge). Demote every other class per MUTATION_THREE_AXIS_PROTOCOL.md (no proven cells after leakage filters).
