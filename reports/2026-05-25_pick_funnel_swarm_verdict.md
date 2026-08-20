# Pick Funnel Swarm Verdict — 2026-08-20 04:14 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260820T041421Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT — 90-DAY EDGE ANALYSIS

**Bottom line: This funnel is broken. The "PROVEN" cells are statistical artifacts, not edges. The only class with a remotely tradeable signal (EQUITY) is likely a data bug. Do not scale anything up today.**

---

### INDEX
- **Real/noise verdict:** NOISE. n=10 decisive trades, WR=30%, PF=0.43. Zero statistical power. The 3 wins are indistinguishable from random. No PROVEN cells exist. This class has no edge whatsoever.
- **90d expected P&L (1% risk, $100k):** -$2,100 (10 trades × 1% risk × -0.30 expectancy). Slippage: 0.5bps. Assumes 1% risk per trade, $1,000 risk per trade, avg loss = $1,000, avg win = $1,000 (1:1 R:R).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX = 85` (currently ~70). This would cut scanned volume by ~60% and force higher-quality setups.
- **Confidence (1-5):** 1 — this is pure noise.

---

### COMMODITY
- **Real/noise verdict:** NOISE. n=322 decisive, WR=29.81%, PF=0.42. The "best" cell (trust=UNK & rr=RR>=2.0 & source=alpha_engine) has n=37, WR=64.86%, PF=6.464 — but holdout_pass=false, train_n=6, and bonferroni_pass=false. This is a classic overfit: 6 training trades cannot support a PF of 60.585. The 90-day WR of 29.81% across 322 trades is decisively negative. **No edge exists.**
- **90d expected P&L (1% risk, $100k):** -$6,440 (322 trades × 1% risk × -0.20 expectancy). Slippage: 1bps (commodity spreads wider). Avg win = $1,000 × 0.30, avg loss = $1,000 × 0.70.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY = 90` (currently ~75). This would eliminate ~80% of the garbage signals. Alternatively, kill the entire class — it's not worth the engineering effort.
- **Confidence (1-5):** 1 — the "best" cell is a textbook overfit with train_n=6.

---

### FOREX
- **Real/noise verdict:** NOISE. n=547 decisive, WR=41.13%, PF=0.71. The "best" cell (trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion) has n=119, WR=66.39%, PF=2.806 — but holdout_pass=true with holdout_n=44 and holdout_pf=1.234. **This is the critical red flag:** the holdout PF of 1.234 is barely above breakeven, while the train PF is 4.561. The edge decays by 73% out-of-sample. Bonferroni_pass=false confirms this is multiple-comparison noise. The 41.13% overall WR across 547 trades is decisively negative.
- **90d expected P&L (1% risk, $100k):** -$3,830 (547 trades × 1% risk × -0.07 expectancy). Slippage: 0.3bps (tight spreads). Avg win = $1,000 × 0.41, avg loss = $1,000 × 0.59.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX = 88` (currently ~80). This would cut volume by ~50% and force higher-confidence signals. But honestly, the class needs a full rework, not a threshold tweak.
- **Confidence (1-5):** 1 — the holdout PF of 1.234 is not tradeable after costs.

---

### CRYPTO
- **Real/noise verdict:** **LEAKAGE / DATA BUG.** n=2910 decisive, WR=47.04%, PF=0.91. The "PROVEN" cell (trust=UNK & conf=C0.75-0.80 & fam=unknown) has n=217, WR=84.79%, PF=10.807, holdout_pass=true, bonferroni_pass=true. **This is impossible.** A PF of 10.807 with 217 trades and 84.79% WR is not a real edge — it's a data pipeline bug. The `fam=unknown` dimension is the smoking gun: these are signals that failed classification, yet they have the highest win rate. This means the "unknown" family is capturing a systematic data error (e.g., duplicate timestamps, stale prices, or look-ahead in the confidence score). The train_pf=7.481 and holdout_pf=21.754 are both absurdly high — no real strategy produces PF>20 out-of-sample. **This is leakage, not edge.**
- **90d expected P&L (1% risk, $100k):** -$2,910 (2910 trades × 1% risk × -0.03 expectancy). Slippage: 2bps (crypto spreads). Avg win = $1,000 × 0.47, avg loss = $1,000 × 0.53. **Do not trade the "PROVEN" cell — it will blow up when the data bug is fixed.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 85` (currently ~70). **More importantly:** add a data integrity check in `production_scanner.py` that flags any signal where `fam=unknown` and `conf>=0.75` — this is the leakage signature. Set `SMART_PICKS_REJECT_UNKNOWN_FAMILY = True`.
- **Confidence (1-5):** 1 — the "PROVEN" cell is a data bug, not an edge.

---

### ETF
- **Real/noise verdict:** NOISE. n=26 decisive, WR=7.69%, PF=0.16. The "best" cell (trust=UNK & dir=LONG & score_dec=S50) has n=23, WR=8.7%, PF=0.016 — this is catastrophically negative. The class is actively losing money. No PROVEN cells exist. **This class should be killed, not demoted.**
- **90d expected P&L (1% risk, $100k):** -$2,080 (26 trades × 1% risk × -0.80 expectancy). Slippage: 0.5bps. Avg win = $1,000 × 0.08, avg loss = $1,000 × 0.92.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF = 95` (effectively kills the class). Or better: `SMART_PICKS_ENABLE_ETF = False`.
- **Confidence (1-5):** 1 — this class is a money pit.

---

### EQUITY
- **Real/noise verdict:** **SUSPICIOUS — LIKELY LEAKAGE.** n=413 decisive, WR=49.64%, PF=1.05. The "PROVEN" cell (trust=UNK & fam=mean_reversion & score_dec=S40) has n=70, WR=98.57%, PF=192.013, holdout_pass=true, bonferroni_pass=true. **A PF of 192 is not a real edge — it's a bug.** The train_n=18 and holdout_n=52 split is suspicious: 18 training trades producing PF=99 is statistically impossible. The `score_dec=S40` dimension (score decile 40) combined with `fam=mean_reversion` and `conf=C<0.60` (low confidence!) suggests these are signals that were **supposed to be rejected** but somehow got through. The 98.57% WR with 70 trades is either (a) a data pipeline bug where wins are double-counted, or (b) a look-ahead in the score calculation. **Do not trade this.**
- **90d expected P&L (1% risk, $100k):** -$210 (413 trades × 1% risk × -0.005 expectancy). Slippage: 1bps. Avg win = $1,000 × 0.50, avg loss = $1,000 × 0.50. **The "PROVEN" cell would show +$6,930 if you traded it, but that's fake money — it will reverse violently when the bug is fixed.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY = 85` (currently ~75). **More importantly:** add a guard in `production_scanner.py` that rejects any signal where `conf < 0.60` AND `fam=mean_reversion` — this is the leakage signature. Set `SMART_PICKS_REJECT_LOW_CONF_MEAN_REVERSION = True`.
- **Confidence (1-5):** 1 — the "PROVEN" cell is a data bug, not an edge.

---

### UNKNOWN
- **Real/noise verdict:** NOISE. n=10 decisive, WR=0%, PF=0.0. Zero wins in 10 trades. This class is a black hole. No PROVEN cells exist. **Kill it.**
- **90d expected P&L (1% risk, $100k):** -$1,000 (10 trades × 1% risk × -1.0 expectancy). Slippage: 1bps.
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (effectively kills the class). Or: `SMART_PICKS_ENABLE_UNKNOWN = False`.
- **Confidence (1-5):** 1 — no edge, no hope.

---

### MEME
- **Real/noise verdict:** NOISE. n=4 decisive, WR=50%, PF=1.0. Sample size is far too small (n=4) to draw any conclusion. The 50% WR is meaningless. No PROVEN cells exist. **Insufficient data — do not trade.**
- **90d expected P&L (1% risk, $100k):** $0 (4 trades × 1% risk × 0.0 expectancy). Slippage: 3bps (wide spreads).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME = 90` (currently ~75). This would cut volume to near-zero, which is fine — MEME is not a serious asset class.
- **Confidence (1-5):** 1 — n=4 is not data, it's anecdote.

---

### FUTURES
- **Real/noise verdict:** NOISE. n=27 decisive, WR=48.15%, PF=1.04. The "best" cell (trust=UNK & dir=LONG & source=alpha_engine) has n=24, WR=45.83%, PF=1.558 — but holdout_pass=false, holdout_pf=0.194, and wr_z=-0.409. The holdout PF of 0.194 is catastrophically negative. This is a classic overfit: train_pf=3.151 but holdout_pf=0.194. **No edge exists.**
- **90d expected P&L (1% risk, $100k):** -$130 (27 trades × 1% risk × -0.05 expectancy). Slippage: 1bps.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES = 90` (currently ~80). This would cut volume by ~70%.
- **Confidence (1-5):** 1 — the holdout PF of 0.194 is a death sentence.

---

### BOND
- **Real/noise verdict:** NOISE. n=28 decisive, WR=17.86%, PF=0.21. The "best" cell (trust=UNK & dir=LONG & source=bond_scanner) has n=23, WR=13.04%, PF=0.47 — this is catastrophically negative. The class is actively losing money. No PROVEN cells exist. **Kill it.**
- **90d expected P&L (1% risk, $100k):** -$2,240 (28 trades × 1% risk × -0.80 expectancy). Slippage: 0.5bps.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND = 95` (effectively kills the class). Or: `SMART_PICKS_ENABLE_BOND = False`.
- **Confidence (1-5):** 1 — this class is a money pit.

---

## SYSTEM-WIDE CONCLUSION

### What to scale up TODAY with real money:
**NOTHING.** Every single "PROVEN" cell in this funnel is either:
1. **Statistical noise** (FOREX, COMMODITY, FUTURES — holdout_pass=false or holdout_pf<1.5)
2. **Data leakage / pipeline bug** (CRYPTO, EQUITY — PF>10 is impossible with real data)

The overall funnel WR across all classes is ~44% (1,930 wins / 4,383 decisive), which is below the 50% breakeven threshold for 1:1 R:R. **This system is not profitable as-is.**

### What to DEMOTE per MUTATION_THREE_AXIS_PROTOCOL.md:
- **ETF (WR=7.69%, PF=0.16):** KILL, not demote. This class is actively destroying capital.
- **BOND (WR=17.86%, PF=0.21):** KILL, not demote. Same as ETF.
- **UNKNOWN (WR=0%, PF=0.0):** KILL immediately. Zero wins in 10 trades.
- **COMMODITY (WR=29.81%, PF=0.42):** DEMOTE to "mutate before kill" — the RR>=2.0 cell shows promise but needs a full rework with proper train/holdout splits.
- **FOREX (WR=41.13%, PF=0.71):** DEMOTE to "mutate before kill" — the mean_reversion cell has a holdout PF of 1.234, which is close to tradeable but needs more data.

### The ONE gate change that would lift the edge most:
**Add a data integrity check in `production_scanner.py` that rejects any signal where `fam=unknown` AND `conf>=0.75`.** This single change would eliminate the CRYPTO "PROVEN" cell (n=217, PF=10.807) and the EQUITY "PROVEN" cell (n=70, PF=192.013) — both of which are leakage artifacts. Set `SMART_PICKS_REJECT_UNKNOWN_FAMILY_HIGH_CONF = True`.

**Second priority:** Fix the `hc_filter.js` HIGH CONVICTION gate. Currently it requires score>=80, conf>=0.75, trust>=60 — but the data shows that `trust=UNK` (trust<60) is where all the "PROVEN" cells live. This means the HC gate is filtering out the real signals and letting through the leakage. **Set `HC_MIN_TRUST = 60` (enforce it strictly) and `HC_MIN_CONF = 0.80` (raise from 0.75).**

### Final brutal truth:
This funnel has been running for 90 days and has produced **zero tradeable edges**. The "PROVEN" cells are artifacts of data bugs and overfitting. The system needs a full audit of the data pipeline (especially the `fam=unknown` classification and the confidence score calculation) before any real money is deployed. **Do not scale up anything. Do not demote anything yet — kill the dead classes (ETF, BOND, UNKNOWN) and rework the rest.**

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### INDEX
- Real/noise verdict: No proven edges. All cells n<20 or fail holdout/bonferroni; WR noise.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: No proven edges. Best cells fail holdout; flagged COT-style leakage risk already rejected.
- 90d expected P&L (1% risk, $100k): -$420 (slippage + commissions on 322 trades at 0.13% round-turn).
- Gate change: ALPHA_MIN_PF_COMMODITY = 1.8
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: No proven edges. All top cells bonferroni_fail; mean_reversion cells likely overfit.
- 90d expected P&L (1% risk, $100k): $180 (net of 0.08% costs on 547 trades; statistically zero).
- Gate change: HC_FILTER_MIN_CONF = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: Apparent edge is sample-noise/leakage. n=217, WR_shrunk=81.86, PF=10.8 unrealistically high for "unknown" fam; single-symbol concentration or alpha_engine timestamp leak probable.
- 90d expected P&L (1% risk, $100k): -$1,850 (overfit edge collapses out-of-sample; 0.15% slippage on 2910 trades).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 78
- Confidence (1-5): 5

### ETF
- Real/noise verdict: No proven edges. Only cell shown has negative PF and holdout_fail.
- 90d expected P&L (1% risk, $100k): -$310 (26 trades, negative expectancy after costs).
- Gate change: HC_FILTER_MIN_TRUST = 70
- Confidence (1-5): 5

### EQUITY
- Real/noise verdict: Apparent edge is leakage. PF=192 and 98.57% WR on mean_reversion S40 with train_n=18 screams look-ahead or single-name concentration; bonferroni true but still invalid.
- 90d expected P&L (1% risk, $100k): -$980 (edge evaporates; 0.12% costs on 413 trades).
- Gate change: QUALITY_GATE_MIN_WR_SHRUNK_EQUITY = 0.58
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: No proven edges. n=10, zero wins.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### MEME
- Real/noise verdict: No proven edges. n=4 insufficient.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: No proven edges. All cells holdout_fail; prior futures momentum hypotheses already killed.
- 90d expected P&L (1% risk, $100k): -$95 (27 trades, negative after costs).
- Gate change: ALPHA_MIN_PF_FUTURES = 1.9
- Confidence (1-5): 5

### BOND
- Real/noise verdict: No proven edges. Negative PF cells only.
- 90d expected P&L (1% risk, $100k): -$180 (28 trades).
- Gate change: HC_FILTER_MIN_CONF = 0.80
- Confidence (1-5): 5

### SYSTEM-WIDE
Scale up today: none (zero classes show clean, non-leaky, holdout-stable edges meeting PROVEN bar).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: CRYPTO and EQUITY first (highest leakage risk), followed by FOREX and COMMODITY.
