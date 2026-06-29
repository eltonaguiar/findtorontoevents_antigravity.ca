# Pick Funnel Swarm Verdict — 2026-06-29 05:37 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260629T053642Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

**NOTE:** All numbers are rounded to the nearest dollar or percent.  
Risk per trade = 1 % of a $100 k account = $1 000.  
Profit‑factor (PF) is interpreted as PF = gross profit / gross loss, so the expected net profit per trade ≈ (PF − 1) × $1 000.  
Slippage is assumed to be 0.1 % of notional (≈ $100 per trade) and is already baked into the observed PF values.

---

### CRYPTO
- **Real/noise verdict:** **Real** – both “PROBATION & RR1.5‑2.0 & LONG” (n = 334, WRₛₕᵣᵤₙₖ = 64.4 %, PF = 1.99, z = 5.58, Bonferroni = PASS) and “PROBATION & C<0.60 & LONG” (n = 377, WRₛₕᵣᵤₙₖ = 61.7 %, PF = 1.51, z = 4.79, Bonferroni = PASS) survive all statistical guards. No obvious look‑ahead or single‑symbol concentration is visible from the summary; a deeper symbol‑level audit is still recommended.
- **90d expected P&L (1 % risk, $100 k):**  
  *Cell 1:* 334 trades × ($1 000 × (1.992‑1)) ≈ $331 k  
  *Cell 2:* 377 trades × ($1 000 × (1.51‑1)) ≈ $192 k  
  **Combined ≈ $523 k** (gross, before taxes/fees).  
  This assumes the same risk‑size per trade and that the observed PF already incorporates average slippage.
- **Gate change:** `SMART_PICKS_MIN_RR_CRYPTO = 1.5` (raise the minimum risk‑/‑reward band to the proven “RR1.5‑2.0” slice). This will filter out lower‑RR picks that dilute the edge while keeping the high‑PF cell intact.
- **Confidence (1‑5):** **5**

---

### EQUITY
- **Real/noise verdict:** **Noise** – the only high‑PF cell (“trust=UNK & score = S40 & source=alpha_engine”) has n = 37, passes the hold‑out but fails Bonferroni (multiple‑testing) and is far below the 20‑trade threshold for a “PROVEN” edge. The result is likely sample‑noise or a fleeting opportunistic burst.
- **90d expected P&L:** $0 (no statistically‑validated edge to size).
- **Gate change:** Raise the HC filter confidence threshold for EQUITY from 0.75 to **0.85** (`HC_CONFIDENCE_MIN_EQUITY = 0.85`). This will prune the few high‑score but under‑sampled picks.
- **Confidence:** **2**

---

### COMMODITY
- **Real/noise verdict:** **Noise** – no “PROVEN” cells; the best PF (1.207) comes from a 107‑trade slice that fails hold‑out (0 hold‑out trades) and has a WRₛₕᵣᵤₙₖ ≈ 50 %. The edge is not statistically reliable.
- **90d expected P&L:** $0
- **Gate change:** Tighten the trust band to exclude “PROBATION” for COMMODITY (`SMART_TRUST_MIN_COMMODITY = "HIGH"`). This removes the weak‑trust cells that dominate the current results.
- **Confidence:** **2**

---

### FOREX
- **Real/noise verdict:** **Noise** – the top PF cell (PF = 3.62) has a win‑rate of only 7.9 % and a massive negative z‑score (‑20.9). The hold‑out passes but the win‑rate and WRₛₕᵣᵤₙₖ are far below any meaningful edge. The PF is inflated by a few large winners (e.g., the “multi_asset_copytrader” source) and is likely driven by concentration in a single currency pair.
- **90d expected P&L:** $0
- **Gate change:** Increase the HC filter confidence requirement for FOREX from 0.75 to **0.90** (`HC_CONFIDENCE_MIN_FOREX = 0.90`). This will eliminate the low‑confidence, high‑PF but win‑rate‑poor cells.
- **Confidence:** **2**

---

### INDEX
- **Real/noise verdict:** **Noise** – only 8 closed trades, WR = 62.5 % but PF = 1.0  (break‑even). Sample size far too small for any claim.
- **90d expected P&L:** $0
- **Gate change:** Raise the minimum score for INDEX to the same level as CRYPTO (`SMART_PICKS_MIN_SCORE_INDEX = SMART_PICKS_MIN_SCORE_CRYPTO`). This will stop the system from surfacing low‑volume, low‑edge picks.
- **Confidence:** **1**

---

### ETF
- **Real/noise verdict:** **Noise** – 22 closed trades, WR = 9 % and PF ≈ 0.9. No edge.
- **90d expected P&L:** $0
- **Gate change:** Disable ETF scanning altogether (`ENABLE_ETF_SCANNING = False`) until a statistically‑significant edge emerges.
- **Confidence:** **1**

---

### UNKNOWN
- **Real/noise verdict:** **Noise** – 6 closed trades, WR = 0 %, PF = 0.0. Pure noise.
- **90d expected P&L:** $0
- **Gate change:** Set trust minimum to “HIGH” for UNKNOWN assets (`SMART_TRUST_MIN_UNKNOWN = "HIGH"`).
- **Confidence:** **1**

---

### BOND
- **Real/noise verdict:** **Noise** – 21 closed trades, WR = 14 %, PF ≈ 0.5. No edge.
- **90d expected P&L:** $0
- **Gate change:** Raise the minimum R:R band to 1.5 (`SMART_PICKS_MIN_RR_BOND = 1.5`) to filter out low‑reward picks.
- **Confidence:** **1**

---

### FUTURES
- **Real/noise verdict:** **Noise** – 16 closed trades, WR = 56 % but PF ≈ 1.0 and no proven cell. Sample too small.
- **90d expected P&L:** $0
- **Gate change:** Exclude “PROBATION” trust for FUTURES (`SMART_TRUST_MIN_FUTURES = "HIGH"`).
- **Confidence:** **1**

---

### MEME
- **Real/noise verdict:** **Noise** – single trade, WR = 100 % but n = 1, PF = ∞ (division by zero). Not a statistical edge.
- **90d expected P&L:** $0
- **Gate change:** Disable MEME class scanning (`ENABLE_MEME_SCANNING = False`).
- **Confidence:** **1**

---

## SYSTEM‑WIDE Conclusion
- **Scale‑up today:** **CRYPTO** – the two “PROBATION & RR1.5‑2.0 & LONG” cells have robust statistical backing (large n, Bonferroni‑passed, high WRₛₕᵣᵤₙₖ, PF ≈ 2). Deploy the suggested risk‑size (1 % per trade) on a $100 k account; expected net profit ≈ $523 k over the next 90 days if the market regime remains similar.
- **Demote / mutate:** **FOREX** – despite a superficially high PF, the win‑rate is abysmal, the Z‑score is strongly negative, and the edge appears to be driven by a few outlier trades (likely single‑pair concentration). According to the *MUTATION_THREE_AXIS_PROTOCOL*, lower the confidence gate to 0.90 and re‑evaluate; if performance does not improve, suspend FOREX scanning entirely.  

All other asset classes show no statistically‑significant edge and should remain at their current (mostly disabled) gate settings until new, well‑validated signals emerge.

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

Here is the brutally honest audit of your 90-day pick funnel, asset class by asset class.

---

### CRYPTO
- **Real/noise verdict:** **Real, but fragile.** The PROVEN cell (`trust=PROBATION & rr=RR1.5-2.0 & dir=LONG`, n=334, WR_shrunk=64.41%, PF=1.99) is statistically robust (z=5.58, Bonferroni pass). The `ml` family cell (PF=1.748) fails holdout and Bonferroni — **do not trade it**. The `conf=C0.60-0.70 & rr=RR1.5-2.0` cell (n=929, PF=1.713) passes holdout but fails Bonferroni; it is *promising but not yet proven*. The PROBATION trust band dominating suggests the edge comes from lower-trust signals that happen to have good R:R — this is a real pattern, not leakage.
- **90d expected P&L (1% risk, $100k):** **$14,957** (334 trades × 1.4957% avg PnL × $1,000 risk per trade). Assumes 1% risk per trade on $100k = $1,000 risk, no slippage beyond 0.1% (crypto liquid), 1:1.5 R:R average. If you only trade the PROVEN cell, you get 334 trades in 90 days — high frequency.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` = **70** (currently 80). The PROVEN edge lives at `score_dec=S50` (score 50-60). Raising the min score to 80 kills your best edge. Lowering to 70 lets more of these PROBATION/LONG/RR1.5-2.0 signals through without flooding garbage.
- **Confidence (1-5):** **4** — Real edge, but PROBATION trust band means it could decay. Monitor weekly.

---

### EQUITY
- **Real/noise verdict:** **Noise.** Zero PROVEN cells. The best cell (`trust=UNK & score_dec=S40 & source=alpha_engine`, n=37, WR_shrunk=68.42%, PF=4.408) fails Bonferroni and has only 37 trades. The holdout PF of 6.72 on n=22 is suspicious — likely a single lucky symbol or tiny sample. The overall WR of 42.5% on 360 decisive trades confirms no edge.
- **90d expected P&L (1% risk, $100k):** **-$540** (360 trades × -0.15% avg PnL × $1,000). Actually negative. Do not trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` = **90** (currently 80). This will kill almost all picks, which is correct — the class has no edge. Only trade if a PROVEN cell emerges.
- **Confidence (1-5):** **1** — No edge. The 42.5% WR is below 50% with high variance.

---

### COMMODITY
- **Real/noise verdict:** **Noise.** Zero PROVEN cells. The best cell (`trust=PROBATION & rr=RR1.5-2.0 & dir=LONG & score_dec=S50`, n=107, WR=50.47%, PF=1.207) is barely above breakeven and fails holdout (n=0). The second-best cell has a *negative* PF (0.869). The overall WR of 34.4% on 968 decisive trades is catastrophic. **This class is destroying capital.**
- **90d expected P&L (1% risk, $100k):** **-$1,682** (968 trades × -0.1682% avg PnL × $1,000). Negative. The best cell barely breaks even.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` = **95** (currently 80). Effectively kill the class. Or better: set `COMMODITY_ENABLED = False` in `production_scanner.py`. The 34.4% WR is not salvageable with gate tweaks.
- **Confidence (1-5):** **1** — No edge. The 34.4% WR is statistically significant *in the wrong direction*.

---

### FOREX
- **Real/noise verdict:** **Noise with a dangerous mirage.** Zero PROVEN cells. The best cells have PF > 3.0 but WR < 32% — this is a *low-win-rate, high-payoff* pattern that looks attractive but is statistically noise. The `rr=RR1.5-2.0 & dir=LONG & source=multi_asset_copytrader` cell (n=616, WR=7.95%, PF=3.617) has a z-score of -20.87 — **that is not an edge, that is a losing strategy that happened to have a few big wins**. The holdout PF of 4.25 on n=435 is suspicious: a 7.95% WR strategy with PF=3.6 implies the wins are massive outliers. This is likely a single lucky trade or data error. **Do not trade FOREX.**
- **90d expected P&L (1% risk, $100k):** **-$2,195** (2,952 trades × -0.074% avg PnL × $1,000). The overall WR of 25.64% is devastating.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` = **95** (currently 80). Kill the class. The `multi_asset_copytrader` source is producing garbage. Consider removing that source entirely.
- **Confidence (1-5):** **1** — No edge. The 25.64% WR is among the worst I've seen. The high-PF cells are statistical artifacts.

---

### INDEX
- **Real/noise verdict:** **Insufficient data.** Only 8 decisive trades. The 62.5% WR is meaningless. Cannot conclude anything.
- **90d expected P&L (1% risk, $100k):** **$0** (do not trade with 8 trades).
- **Gate change:** None. Keep monitoring. Do not scale.
- **Confidence (1-5):** **1** — No data to judge.

---

### ETF
- **Real/noise verdict:** **Noise.** 22 decisive trades, 9.09% WR. That is a 2/22 win rate. The best cell is empty. This class is a disaster.
- **90d expected P&L (1% risk, $100k):** **-$1,800** (22 trades × -0.82% avg PnL × $1,000). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = **95** (currently 80). Kill the class.
- **Confidence (1-5):** **1** — No edge.

---

### BOND
- **Real/noise verdict:** **Noise.** 21 decisive trades, 14.29% WR. Best cell empty. Same as ETF.
- **90d expected P&L (1% risk, $100k):** **-$1,500** (21 trades × -0.71% avg PnL × $1,000).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = **95** (currently 80). Kill.
- **Confidence (1-5):** **1** — No edge.

---

### FUTURES
- **Real/noise verdict:** **Insufficient data.** 16 decisive trades, 56.25% WR. The 9/7 win/loss split is not statistically significant. The rejected hypothesis H-005 confirms no edge here.
- **90d expected P&L (1% risk, $100k):** **$0** (do not trade).
- **Gate change:** None. Keep monitoring per H-005 rejection.
- **Confidence (1-5):** **1** — No data, and prior hypothesis rejected.

---

### MEME
- **Real/noise verdict:** **Insufficient data.** 1 decisive trade, 100% WR. Meaningless.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** None.
- **Confidence (1-5):** **1** — No data.

---

### UNKNOWN
- **Real/noise verdict:** **Noise.** 6 decisive trades, 0% WR. Best cell empty. The 329 opened vs 6 closed suggests these are mostly open positions — likely garbage signals that never triggered.
- **90d expected P&L (1% risk, $100k):** **-$600** (6 trades × -1.0% avg PnL × $1,000).
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` = **95** (currently 80). Kill.
- **Confidence (1-5):** **1** — No edge.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money:** **CRYPTO only.** The PROVEN cell (`PROBATION/LONG/RR1.5-2.0`) has 334 trades, 64.41% shrunk WR, PF=1.99, and passes all statistical tests. At 1% risk per trade, this would generate ~$15k/month on $100k. No other class has a single PROVEN cell.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL.md:** **COMMODITY, FOREX, ETF, BOND, UNKNOWN** — all five should be **mutated before kill**. Specifically:
- **COMMODITY**: Mutate by removing all `COT_positioning` signals (rejected H-001) and all `inventory_direction_gate` signals (rejected H-036). If WR does not exceed 45% in 30 days, kill.
- **FOREX**: Mutate by removing the `multi_asset_copytrader` source entirely. If WR does not exceed 40% in 30 days, kill.
- **ETF, BOND, UNKNOWN**: Kill immediately. No mutation path — WR below 15% is not salvageable.

**EQUITY, INDEX, FUTURES, MEME**: Keep in observation mode. Do not allocate capital. Re-evaluate in 90 days when sample sizes grow.

**Final brutal truth:** Your system is a one-trick pony. CRYPTO carries the entire P&L. The other 9 asset classes are either noise or capital destroyers. If CRYPTO decays, the system is dead. Diversify by finding a second PROVEN edge — or accept that you are a crypto-only shop.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real. Two cells meet PROVEN criteria (n=334/377, WR_shrunk 64.41/61.71, PF 1.992/1.51, both holdout_pass + bonferroni_pass true); no obvious leakage flags in the reported stats.
- 90d expected P&L (1% risk, $100k): ~$4,800 (334 + 377 trades at ~1.2–1.5% avg edge after 0.15% slippage, 1% risk per trade).
- Gate change: `hc_filter.js` HIGH_CONVICTION_MIN_SCORE = 65 (currently 80).
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Noise. No PROVEN cells; best_pf cells have tiny train_n (15) and inconsistent holdout.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None (no edge to protect).
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise. No PROVEN cells; all best_pf cells fail holdout_pass and show PF < 1.3 with negative avg_pnl.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. No PROVEN cells; best_pf cells show extreme WR_z negatives and tiny effective edge after shrinkage.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

**### INDEX / ETF / BOND / FUTURES / MEME / UNKNOWN**
- Real/noise verdict: Noise. All n_closed ≤ 22; zero PROVEN cells and no statistically credible edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None.
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified PROVEN cells that survived holdout + multiple-testing correction). Demote FOREX and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL (mutate filters to zero allocation; they contribute only noise and negative expectancy). All other classes already at zero edge.
