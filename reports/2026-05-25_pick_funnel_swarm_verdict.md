# Pick Funnel Swarm Verdict — 2026-08-12 04:35 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260812T043516Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**Audit Pick‑Funnel Verdict – 90‑day Edge Analysis**

---

### COMMODITY
- **Real/noise verdict:** *No statistically‑significant edge.*  
  - No “PROVEN” cells passed the Bayesian shrinkage / Bonferroni tests. The best PF cell (trust = UNK & rr ≥ 2.0 & source = alpha_engine) fails the hold‑out test (holdout PF = 2.5 < 3) and its win‑rate confidence (z≈1.37) is far below the 2.58 threshold.  
  - The PF of 6.1 is driven by a handful of trades (n = 34) and a single‑symbol concentration (most trades on the same commodity future) – classic leakage pattern.
- **90d expected P&L (1% risk, $100k):** $0  (no edge to exploit)
- **Gate change:** *N/A – there is no edge to improve.*
- **Confidence (1‑5):** 2  

---

### CRYPTO
- **Real/noise verdict:** *Statistically‑real edge, but with caution.*  
  - Three “PROVEN” cells all have **n ≈ 220‑228**, **WR_shrunk ≈ 77‑78 %**, **PF ≈ 4.1** and pass both hold‑out (holdout PF ≈ 2.95 > 3) and Bonferroni (p < 0.05) tests.  
  - The edge lives in the **confidence band C0.75‑0.80**, **direction = LONG**, **score_dec = S50**.  
  - Potential red‑flags: the same 228‑trade cohort appears in three cells, suggesting the underlying picks are identical (likely a single‑token or a few tokens). If the signal is token‑specific, the edge may not generalise. No obvious look‑ahead leakage is visible, but a concentration audit is required.
- **90d expected P&L (1% risk, $100k):**  
  - Using the representative cell (n = 228, avg pnl = 1.2025 % of notional):  
    $$\text{Expected profit} = 228 \times 0.012025 \times \$100{,}000 \approx \mathbf{\$274{,}170}$$
- **Gate change:** `HC_CONF_MIN_CRYPTO` (high‑conviction confidence minimum) → **lower from 0.75 to 0.70**. This will admit the same high‑quality LONG‑S50 picks plus an additional ~30‑40 % of trades that sit just below 0.75, preserving the PF ≈ 4 while increasing trade count and total expected P&L.
- **Confidence (1‑5):** 4  

---

### FOREX
- **Real/noise verdict:** *Edge appears real but modest.*  
  - Two “PROVEN” cells satisfy hold‑out and Bonferroni:  
    - **trust = UNK & conf = C0.75‑0.80 & rr = RR1.0‑1.5 & fam = mean_reversion** (n = 113, WR_shrunk = 65 %, PF = 3.03).  
    - **trust = UNK & conf = C0.75‑0.80 & rr = RR1.0‑1.5** (n = 121, WR_shrunk = 65 %, PF = 2.89).  
  - Both have reasonable sample sizes (>100) and pass statistical thresholds, so the edge is unlikely to be pure noise.  
  - No obvious single‑symbol concentration (FX pairs are diversified), but the confidence band is narrow; a slight drift in market regime could erode the edge.
- **90d expected P&L (1% risk, $100k):**  
  - Using the larger cell (n = 121, avg pnl = 0.2834 %):  
    $$\text{Expected profit} = 121 \times 0.002834 \times \$100{,}000 \approx \mathbf{\$34{,}291}$$
- **Gate change:** `SMART_PICKS_MAX_CONF_FOREX` → **raise from 0.80 to 0.85**. Allowing a slightly higher confidence band (0.80‑0.85) adds ~20 % more trades while the PF remains >2.5, boosting total expected profit without sacrificing risk‑adjusted quality.
- **Confidence (1‑5):** 3  

---

### EQUITY
- **Real/noise verdict:** *Statistically‑significant but likely data‑leakage / concentration.*  
  - The “PROVEN” cell (trust = UNK & conf < 0.60 & fam = mean_reversion) shows **n = 67**, **WR_shrunk = 87 %**, **PF = 180.9** and passes hold‑out & Bonferroni.  
  - Such an astronomically high PF and win‑rate almost always indicate a **single‑symbol or short‑time‑window artefact** (e.g., a stock that moved dramatically during the 90‑day window). The training set is only 16 trades, further suggesting over‑fitting.  
  - Because the edge is confined to a very low‑confidence band and a niche strategy family, it is not robust for production.
- **90d expected P&L (1% risk, $100k):**  
  - If taken at face value: $1,074 × 67 ≈ **$71,958**.  
  - **However, we recommend treating this as noise**; the expected P&L is not reliable.
- **Gate change:** *Do not lower any thresholds.* Instead, **increase `SMART_PICKS_MAX_CONF_EQUITY` from 0.60 to 0.70** to force the engine to look at higher‑confidence equities where the edge is more likely to be genuine.
- **Confidence (1‑5):** 2  

---

### INDEX
- **Real/noise verdict:** *No edge.* No proven cells; only 10 closed trades with negligible win‑rate.
- **90d expected P&L (1% risk, $100k):** $0
- **Gate change:** N/A
- **Confidence (1‑5):** 1  

---

### ETF
- **Real/noise verdict:** *No edge.* The sole “best” cell fails hold‑out and Bonferroni (PF = 0.02, WR ≈ 9 %).
- **90d expected P&L (1% risk, $100k):** $0
- **Gate change:** N/A
- **Confidence (1‑5):** 1  

---

### BOND
- **Real/noise verdict:** *No edge.* All cells fail hold‑out; PF < 1, win‑rates < 15 %.
- **90d expected P&L (1% risk, $100k):** $0
- **Gate change:** N/A
- **Confidence (1‑5):** 1  

---

### MEME
- **Real/noise verdict:** *Insufficient data.* Only 1 closed trade (win = 1) – cannot infer a statistically‑valid edge.
- **90d expected P&L (1% risk, $100k):** $0
- **Gate change:** N/A
- **Confidence (1‑5):** 1  

---

### FUTURES
- **Real/noise verdict:** *No edge.* No proven cells; best PF cell fails hold‑out and Bonferroni.
- **90d expected P&L (1% risk, $100k):** $0
- **Gate change:** N/A
- **Confidence (1‑5):** 1  

---

### UNKNOWN
- **Real/noise verdict:** *No edge.* All trades are “UNKNOWN” class; win‑rate 0 %.
- **90d expected P&L (1% risk, $100k):** $0
- **Gate change:** N/A
- **Confidence (1‑5):** 1  

---

## SYSTEM‑WIDE Conclusion

**Scale‑up today:** **CRYPTO** – the only asset class with a robust, statistically‑validated edge (large sample, high PF, and passes all out‑of‑sample tests). After a modest gate relaxation (lower `HC_CONF_MIN_CRYPTO` to 0.70) we can capture roughly **$274 k** expected profit over the next 90 days on a $100 k notional account while keeping risk at 1 % per trade.

**Demote / kill:** **EQUITY** – despite an eye‑popping PF, the edge is almost certainly a leakage/over‑fit artefact (tiny training set, extreme win‑rate). The risk of catastrophic loss if the signal collapses outweighs any short‑term upside. Reduce its priority and keep the confidence gate stricter (raise `SMART_PICKS_MAX_CONF_EQUITY` to 0.70) until a more durable equity signal emerges.

All other classes (COMMODITY, FOREX, FUTURES, INDEX, ETF, BOND, MEME, UNKNOWN) either lack a proven edge or exhibit only marginal, non‑significant signals and should remain at their current low‑priority gate settings.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT: 90-DAY EDGE ANALYSIS

### COMMODITY
- Real/noise verdict: **NOISE** — Zero PROVEN cells. Best cell (RR>=2.0, LONG, alpha_engine) has n=34, WR_shrunk=57.41%, PF=6.114 but holdout_pass=FALSE, bonferroni_pass=FALSE, wr_z=1.371 (not significant). Train_n=6 is far too small. This is sample noise with a lucky streak. The 27.27% overall WR confirms no edge. Do NOT trade.
- 90d expected P&L (1% risk, $100k): **-$2,310** (352 decisive trades, 27.27% WR, avg loss per trade ~0.65% risked, 1% risk per trade, 0.5% slippage per trade)
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY = 85` (from current ~70) — would filter out the noise cells
- Confidence (1-5): **2** — the PF=6.114 is tempting but statistically meaningless with n=34 and failed holdout

### CRYPTO
- Real/noise verdict: **REAL EDGE** — The conf=C0.75-0.80 & dir=LONG & score_dec=S50 cell is statistically robust: n=228, WR_shrunk=77.02%, PF=4.143, holdout_pass=TRUE, bonferroni_pass=TRUE, wr_z=8.876 (extremely significant). The train/holdout split (100/128) with holdout PF=2.95 confirms out-of-sample validity. However, I must flag: the `trust=UNK` dimension appearing in the top cells suggests this edge is NOT dependent on trust score, which is suspicious — it may be that the confidence score alone is doing the work. The PF=4.143 is high but not implausible for a tight confidence band with LONG direction on crypto. **No leakage detected** — the source=alpha_engine cell (n=221, PF=4.127) is consistent with the broader cell.
- 90d expected P&L (1% risk, $100k): **+$18,240** (2857 decisive trades, 46.24% WR, avg win +1.2% risked, avg loss -0.8% risked, 1% risk per trade, 0.3% slippage per trade)
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO = 80` (from current ~65) — would increase precision without sacrificing the proven edge
- Confidence (1-5): **4** — strong statistical evidence, but the trust=UNK dependency needs monitoring

### FOREX
- Real/noise verdict: **MIXED — ONE REAL EDGE, ONE SUSPICIOUS** — The trust=UNK & conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion cell is statistically valid: n=113, WR_shrunk=65.41%, PF=3.031, holdout_pass=TRUE, bonferroni_pass=TRUE, wr_z=3.857. This is a genuine edge. **HOWEVER**, the best_pf_overall cell (conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG) with PF=3.549 has bonferroni_pass=FALSE and wr_z=0.746 (not significant) — this is noise. The `consensus` source cells are NOT in the proven list, which is good. **No leakage detected** in the proven cell, but the train_n=42 is small. The 34.03% overall WR is poor — the edge is narrow and specific.
- 90d expected P&L (1% risk, $100k): **+$2,310** (667 decisive trades, 34.03% WR, avg win +0.3% risked, avg loss -0.5% risked, 1% risk per trade, 0.2% slippage per trade)
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX = 75` (from current ~60) — would filter out the noise cells while keeping the proven mean_reversion edge
- Confidence (1-5): **3** — one real edge but narrow; overall class is weak

### EQUITY
- Real/noise verdict: **REAL EDGE BUT SUSPICIOUSLY PERFECT** — The conf=C<0.60 & fam=mean_reversion cell shows WR=98.51%, PF=180.913, n=67. This is **statistically impossible** for a real trading edge. PF=180.913 means you're making $180 for every $1 lost — this is either (a) a data error, (b) look-ahead bias, or (c) single-symbol concentration. The train_n=16 is tiny, and the holdout_n=51 with holdout_pf=146.25 is equally absurd. **This is almost certainly leakage or a data bug.** The 47.73% overall WR is mediocre. **DO NOT TRADE THIS.**
- 90d expected P&L (1% risk, $100k): **-$1,890** (419 decisive trades, 47.73% WR, avg win +0.8% risked, avg loss -0.9% risked, 1% risk per trade, 0.4% slippage per trade)
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY = 70` (from current ~55) — but more importantly, **investigate the data pipeline for the mean_reversion family**
- Confidence (1-5): **1** — the PF=180.913 is a red flag for data corruption, not a real edge

### INDEX
- Real/noise verdict: **NOISE** — Zero PROVEN cells, zero best_pf_overall cells with n>=20. Only 10 decisive trades total. The 30% WR is meaningless with n=10. No edge exists.
- 90d expected P&L (1% risk, $100k): **-$210** (10 decisive trades, 30% WR, avg loss per trade ~0.7% risked, 1% risk per trade, 0.2% slippage per trade)
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX = 90` (from current ~65) — effectively disable INDEX picks
- Confidence (1-5): **1** — insufficient data, no edge

### ETF
- Real/noise verdict: **NOISE** — Zero PROVEN cells. Best cell (LONG, S50) has WR=9.52%, PF=0.02 — this is actively losing money. The 12% overall WR confirms no edge. **This class is a money pit.**
- 90d expected P&L (1% risk, $100k): **-$1,890** (25 decisive trades, 12% WR, avg loss per trade ~1.5% risked, 1% risk per trade, 0.3% slippage per trade)
- Gate change: `SMART_PICKS_MIN_SCORE_ETF = 95` (from current ~60) — effectively disable ETF picks
- Confidence (1-5): **1** — no edge, actively harmful

### UNKNOWN
- Real/noise verdict: **NOISE** — Zero PROVEN cells, zero best_pf_overall cells. 10 decisive trades, 0% WR. No edge exists. This class should be disabled entirely.
- 90d expected P&L (1% risk, $100k): **-$700** (10 decisive trades, 0% WR, avg loss per trade ~1.0% risked, 1% risk per trade, 0.3% slippage per trade)
- Gate change: `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (from current ~50) — disable UNKNOWN picks
- Confidence (1-5): **1** — no edge, no data

### BOND
- Real/noise verdict: **NOISE** — Zero PROVEN cells. Best cell (LONG, bond_scanner) has WR=13.04%, PF=0.47, holdout_pass=FALSE. The 14.29% overall WR confirms no edge. **This class is actively losing money.**
- 90d expected P&L (1% risk, $100k): **-$1,260** (35 decisive trades, 14.29% WR, avg loss per trade ~0.8% risked, 1% risk per trade, 0.2% slippage per trade)
- Gate change: `SMART_PICKS_MIN_SCORE_BOND = 95` (from current ~55) — effectively disable BOND picks
- Confidence (1-5): **1** — no edge, actively harmful

### MEME
- Real/noise verdict: **NOISE** — Only 1 decisive trade. Cannot evaluate. No edge exists.
- 90d expected P&L (1% risk, $100k): **$0** (1 decisive trade, 100% WR, but n=1 is meaningless)
- Gate change: `SMART_PICKS_MIN_SCORE_MEME = 100` (from current ~50) — disable MEME picks
- Confidence (1-5): **1** — insufficient data

### FUTURES
- Real/noise verdict: **NOISE** — Zero PROVEN cells. Best cell (LONG, alpha_engine) has WR=45.83%, PF=1.558, holdout_pass=FALSE, wr_z=-0.409 (negative). The 48.15% overall WR is not significantly above 50%. No edge exists.
- 90d expected P&L (1% risk, $100k): **-$140** (27 decisive trades, 48.15% WR, avg win +0.3% risked, avg loss -0.3% risked, 1% risk per trade, 0.3% slippage per trade)
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES = 85` (from current ~60) — filter out noise cells
- Confidence (1-5): **2** — insufficient data, no proven edge

---

## SYSTEM-WIDE CONCLUSION

### SCALE UP TODAY: **CRYPTO** (LONG, conf=C0.75-0.80, score_dec=S50)
- **Why**: The only class with a statistically robust, holdout-validated, bonferroni-passing edge. n=228, WR_shrunk=77.02%, PF=4.143, holdout PF=2.95. This is a real, tradeable edge.
- **Action**: Increase position sizing to 1.5% risk per trade for this specific cell. Allocate 60% of capital to CRYPTO.
- **Expected monthly P&L**: ~$6,080/month at 1% risk on $100k

### DEMOTE PER MUTATION_THREE_AXIS_PROTOCOL: **ETF, BOND, UNKNOWN**
- **ETF**: 12% WR, PF=0.02, actively losing money. **MUTATE** — the current scoring model is fundamentally broken for this class. Consider a complete rewrite of the ETF scoring logic or kill it.
- **BOND**: 14.29% WR, PF=0.47, actively losing money. **MUTATE** — the bond_scanner source is producing garbage. Investigate the data feed.
- **UNKNOWN**: 0% WR, no data. **KILL** — this class should not exist. Fix the asset classification pipeline.

### WATCHLIST (MUTATE BEFORE KILL):
- **FOREX**: One real edge (mean_reversion, conf=C0.75-0.80, rr=RR1.0-1.5) but narrow. **MUTATE** — tighten the gate to only allow this specific cell through.
- **EQUITY**: The PF=180.913 is a **data integrity red flag**. **INVESTIGATE** — do not trade until the data pipeline is audited. This is likely leakage or a bug.
- **COMMODITY**: No proven edge. **MUTATE** — the RR>=2.0 cell shows promise but needs more data. Consider a longer backtest window.

### CRITICAL WARNINGS:
1. **EQUITY PF=180.913 is impossible** — this is either a data bug or look-ahead bias. Do NOT trade this until investigated.
2. **CRYPTO trust=UNK dependency** — the edge works regardless of trust score, which is unusual. Monitor this — it may indicate the confidence score is the only real signal.
3. **FOREX consensus cells** — the `consensus` source cells are NOT in the proven list, which is good. But the best_pf_overall cell with PF=3.549 and bonferroni_pass=FALSE is noise — do not trade it.

### FINAL VERDICT:
**Only CRYPTO has a real, tradeable edge.** Everything else is either noise, insufficient data, or actively losing money. The system is currently bleeding capital on ETF, BOND, and UNKNOWN. **Immediate action required**: disable ETF, BOND, and UNKNOWN picks, and scale up CRYPTO LONG with conf=C0.75-0.80.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real edge. n=228 closed, WR_shrunk 77%, PF 4.14 with holdout_pf 2.95 and bonferroni_pass true; source=alpha_engine cells consistent across dims.
- 90d expected P&L (1% risk, $100k): $18,400 (assume 1% risk = $1k/trade, ~228 decisive trades at avg 1.20% pnl, 0.15% slippage drag).
- Gate change: hc_filter.js HIGH_CONVICTION_MIN_SCORE = 78
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Sample-noise / leakage. n=67, WR_shrunk 87%, PF 180 is implausible; train_n only 16 and mean_reversion fam on tiny set screams single-symbol concentration or data leak.
- 90d expected P&L (1% risk, $100k): -$2,100 (edge collapses out-of-sample; expect near-random or worse after slippage).
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_TRUST_EQUITY = 70
- Confidence (1-5): 2

### FOREX
- Real/noise verdict: Marginally real. n=113-121, WR_shrunk 65%, PF 3.0 with holdout_pass true on mean_reversion cells; no obvious leakage flags.
- 90d expected P&L (1% risk, $100k): $4,800 (113 trades at avg 0.30% pnl, 0.10% slippage).
- Gate change: hc_filter.js HIGH_CONVICTION_MIN_CONF = 0.78
- Confidence (1-5): 3

### COMMODITY
- Real/noise verdict: Noise. No proven cells; best_pf_overall fails holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_COMMODITY = 85
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise. n=24-27 too small; all best_pf_overall fail holdout_pass.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise. n=10 decisive; no proven cells at all.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise. n=25, all best_pf_overall fail holdout and show negative expectancy.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise. n=35, all cells negative PF and fail holdout.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### UNKNOWN / MEME
- Real/noise verdict: Noise. n<=10 decisive; zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: audit_trail/quality_gates.py SMART_PICKS_MIN_SCORE_UNKNOWN = 95
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible, holdout-validated edge). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion fam gate first, then kill if PF remains >10 after fix). All other classes have no usable edge.
