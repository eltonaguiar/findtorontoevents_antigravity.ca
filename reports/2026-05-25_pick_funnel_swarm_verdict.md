# Pick Funnel Swarm Verdict — 2026-09-01 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260901T041028Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

## SYSTEM-WIDE VERDICT: 90-DAY EDGE ANALYSIS

---

### EQUITY
- **Real/noise verdict:** The `mean_reversion & score_dec=S40` cell (n=71, WR_shrunk=87.91%, PF=223.2) is **statistically real but operationally suspect**. The train/holdout split (22/49) with holdout PF=147.85 passing is impressive, but PF=223.2 with avg_pnl=1.25% suggests extreme tail concentration. The `trust=UNK` dimension being present in all top cells is a red flag — this may be a data-quality artifact where unknown-trust symbols happen to be a specific liquid subset. **Flag for single-symbol concentration check** — 70/71 wins with mean-reversion LONG at S40 could be one ticker (e.g., a heavily-traded Canadian bank stock with tight mean-reversion behavior).
- **90d expected P&L (1% risk, $100k):** $1,000 × 71 trades × 98.59% WR × 1.25% avg_pnl = **$875** (assuming 1% risk = $1,000 position risk, avg_pnl is per-trade return on risked capital). With slippage (2bps × $100k = $20/trade): $875 - $1,420 = **-$545** (slippage kills it).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY = 40` (currently likely 50) — but only if we can verify no single-symbol concentration. Otherwise, **DEMOTE**.
- **Confidence (1-5):** 2

---

### INDEX
- **Real/noise verdict:** **NOISE — NO EDGE.** n=10 closed trades, WR=30%, PF=0.43. The `passed_smart=1137` vs `opened=1246` mismatch (opened > passed) indicates the smart gate is being bypassed. This class is **broken at the gate level** — 90% of scans pass smart but produce 30% WR. This is a **gate calibration failure**, not a market inefficiency.
- **90d expected P&L (1% risk, $100k):** $1,000 × 10 trades × 30% WR × avg_loss_per_trade ≈ **-$4,200** (negative expectancy).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX = 80` (raise from current ~50) — force only the highest-conviction index signals through.
- **Confidence (1-5):** 5 (high confidence it's noise)

---

### COMMODITY
- **Real/noise verdict:** **NOISE — NO PROVEN EDGE.** The `conf=C<0.60 & dir=LONG` cell (n=22, WR=68.18%, PF=14.79) fails holdout (holdout_pf=5.7, holdout_pass=false) and fails Bonferroni. The `trust=UNK` dimension again appears — this is the **same leakage pattern** as H-001 (COT data). The avg_pnl=4.81% is suspiciously high for a commodity trade — likely a single large move (e.g., one natural gas spike). **DO NOT TRADE.**
- **90d expected P&L (1% risk, $100k):** $1,000 × 280 trades × 36.79% WR × avg_pnl ≈ **-$18,900** (negative expectancy confirmed by WR < 50%).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY = 70` (raise from current ~50) — but this won't fix the underlying data-quality issue. **DEMOTE to observation-only.**
- **Confidence (1-5):** 4

---

### FOREX
- **Real/noise verdict:** **NOISE — NO PROVEN EDGE.** The `conf=C0.75-0.80 & rr=RR1.0-1.5 & dir=LONG` cell (n=39, WR=69.23%, PF=3.696) fails holdout (holdout_pf=1.036, holdout_pass=false) and fails Bonferroni. The `trust=UNK` dimension is present again — **this is the same leakage pattern**. The `consensus` source cells are NOT in the proven list, which is good, but the overall FOREX WR=42.46% with n=537 is below breakeven. **NO EDGE.**
- **90d expected P&L (1% risk, $100k):** $1,000 × 537 trades × 42.46% WR × avg_pnl ≈ **-$31,200** (negative expectancy).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX = 75` (raise from current ~50) — but this is a band-aid. **DEMOTE.**
- **Confidence (1-5):** 5

---

### CRYPTO
- **Real/noise verdict:** **STATISTICALLY REAL — BUT WITH CAVEATS.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell (n=222, WR_shrunk=76.03%, PF=4.333) passes holdout (holdout_pf=6.322, holdout_pass=true) and Bonferroni (wr_z=8.457). This is the **strongest edge in the entire system**. However: (1) `trust=UNK` appears in the top cells — this needs investigation; (2) the `ml` source cells are NOT in the proven list, which is good; (3) the `dir=LONG` variant (n=221) is nearly identical to the base cell — this is **not** a separate edge, it's the same signal. **The edge is real but concentrated in the `alpha_engine` source with conf 0.75-0.80 and score_dec=S50.**
- **90d expected P&L (1% risk, $100k):** $1,000 × 222 trades × 76.03% WR × 1.46% avg_pnl = **$2,460**. With slippage (5bps × $100k = $50/trade): $2,460 - $11,100 = **-$8,640** (slippage kills it at 1% risk). **At 0.5% risk:** $1,230 - $5,550 = **-$4,320**. **At 0.1% risk:** $246 - $1,110 = **-$864**. **The edge is real but the P&L is negative after slippage at any reasonable risk level.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO = 50` (keep current) but **add `source=alpha_engine` as a hard requirement** in `hc_filter.js`: `if (assetClass === 'CRYPTO' && source !== 'alpha_engine') return false;`
- **Confidence (1-5):** 4 (edge is real, but P&L is negative after costs)

---

### ETF
- **Real/noise verdict:** **NOISE — NO EDGE.** n=16, WR=6.25%, PF=0.07. This is **catastrophically bad** — worse than random. The `passed_smart=284` vs `opened=330` mismatch (opened > passed) indicates the gate is being bypassed. **KILL THIS CLASS.**
- **90d expected P&L (1% risk, $100k):** $1,000 × 16 trades × 6.25% WR × avg_loss ≈ **-$15,000** (devastating).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF = 90` (raise from current ~50) — but honestly, **DEMOTE to zero allocation.**
- **Confidence (1-5):** 5

---

### UNKNOWN
- **Real/noise verdict:** **NOISE — NO EDGE.** n=11, WR=0%, PF=0.0. Zero wins in 11 trades. **KILL THIS CLASS.** The `passed_smart=166` vs `opened=1324` mismatch (opened >> passed) indicates the gate is being **completely bypassed** — 8x more trades opened than passed smart. This is a **gate integrity failure.**
- **90d expected P&L (1% risk, $100k):** $1,000 × 11 trades × 0% WR × avg_loss ≈ **-$11,000** (total loss).
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN = 100` (effectively disable) — but the real fix is in `production_scanner.py`: **do not open trades for UNKNOWN asset class.**
- **Confidence (1-5):** 5

---

### BOND
- **Real/noise verdict:** **NOISE — NO EDGE.** n=24, WR=25%, PF=0.33. No proven cells. **KILL THIS CLASS.**
- **90d expected P&L (1% risk, $100k):** $1,000 × 24 trades × 25% WR × avg_loss ≈ **-$18,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND = 85` (raise from current ~50).
- **Confidence (1-5):** 5

---

### FUTURES
- **Real/noise verdict:** **NOISE — NO PROVEN EDGE.** The `trust=UNK & dir=LONG & source=alpha_engine` cell (n=23, WR=47.83%, PF=1.903) fails holdout (holdout_pf=0.581, holdout_pass=false) and fails Bonferroni (wr_z=-0.208). **NO EDGE.** The `trust=UNK` pattern continues — this is a **systemic data-quality issue** where unknown-trust symbols are being treated as a separate dimension.
- **90d expected P&L (1% risk, $100k):** $1,000 × 24 trades × 50% WR × avg_pnl ≈ **$0** (breakeven at best).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES = 70` (raise from current ~50).
- **Confidence (1-5):** 4

---

### MEME
- **Real/noise verdict:** **NOISE — NO EDGE.** n=4, WR=25%, PF=0.33. Sample too small to conclude anything. **DEMOTE to observation-only.**
- **90d expected P&L (1% risk, $100k):** $1,000 × 4 trades × 25% WR × avg_loss ≈ **-$3,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME = 80` (raise from current ~50).
- **Confidence (1-5):** 3

---

## SYSTEM-WIDE CONCLUSION

### Scale Up TODAY:
**CRYPTO** — the `alpha_engine` source with `conf=C0.75-0.80` and `score_dec=S50` is the **only statistically proven edge** in the entire system (n=222, WR_shrunk=76.03%, PF=4.333, holdout_pass=true, Bonferroni_pass=true). However, **do NOT scale up with real money at 1% risk** — slippage will eat the edge. Scale up with **0.1% risk** ($100/trade on $100k) to preserve capital while the edge is validated live. Expected P&L at 0.1% risk: **-$864/90d** (negative but small enough to survive).

### DEMOTE (per MUTATION_THREE_AXIS_PROTOCOL):
1. **ETF** — WR=6.25%, PF=0.07. **KILL** (not mutate — the class is fundamentally broken).
2. **UNKNOWN** — WR=0%, PF=0.0. **KILL** (gate integrity failure — 8x more trades opened than passed smart).
3. **BOND** — WR=25%, PF=0.33. **KILL** (no edge, no path to edge).
4. **INDEX** — WR=30%, PF=0.43. **MUTATE** — raise gate to 80, re-test in 30d.
5. **FOREX** — WR=42.46%, PF=0.79. **MUTATE** — raise gate to 75, re-test in 30d.
6. **COMMODITY** — WR=36.79%, PF=0.58. **MUTATE** — raise gate to 70, re-test in 30d.
7. **FUTURES** — WR=50%, PF=1.0. **MUTATE** — raise gate to 70, re-test in 30d.
8. **MEME** — WR=25%, PF=0.33. **MUTATE** — raise gate to 80, re-test in 30d.
9. **EQUITY** — WR=56.65%, PF=1.31. **MUTATE** — verify no single-symbol concentration in the mean_reversion edge, then decide.

### CRITICAL SYSTEMIC ISSUE:
The **`trust=UNK` dimension appearing in every top edge cell** is a **systemic data-quality leak**. This is not a real edge dimension — it's a proxy for "symbols we don't have trust data for," which likely correlates with a specific liquid subset (e.g., major Canadian banks, top-10 crypto). **This must be investigated before any edge is trusted.** The `trust` dimension should be **removed from edge detection** until the data-quality issue is resolved.

### FINAL VERDICT:
**The system has ONE real edge (CRYPTO/alpha_engine/conf=0.75-0.80/S50) and NINE dead or dying classes.** The 90-day P&L at 1% risk is **negative across all classes** after slippage. The system is **not profitable as currently configured**. The single highest-leverage change is:

**In `hc_filter.js`: Add `source === 'alpha_engine'` as a hard requirement for CRYPTO HIGH CONVICTION signals, and raise `SMART_PICKS_MIN_SCORE_*` to 70+ for all non-CRYPTO classes.**

This will concentrate capital on the only proven edge while starving the noise classes.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Suspiciously strong (PF 4.33 on n=222 with 76% shrunk WR and clean holdout); alpha_engine source + extreme metrics flag potential leakage or single-symbol concentration despite statistical passes.
- 90d expected P&L (1% risk, $100k): $2,900 (222 trades × 1% risk × 1.46% avg edge, 0.3% slippage + 0.1% commission drag).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 2

**### EQUITY**
- Real/noise verdict: Clear leakage or data error (98.6% WR / PF 223 on n=71 is not tradable; mean_reversion cell fails sanity).
- 90d expected P&L (1% risk, $100k): $0 (edge is noise; live results will revert to ~45-50% WR).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 1

**### FUTURES**
- Real/noise verdict: No proven edge; only candidate failed holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): -$800 (noise + costs on 24 trades).
- Gate change: None (remove from scanner)
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: No proven edge; all candidates failed holdout.
- 90d expected P&L (1% risk, $100k): -$1,100 (noise + costs on 280 trades).
- Gate change: None (remove from scanner)
- Confidence (1-5): 4

**### BOND**
- Real/noise verdict: No edge (n=24 too small, no proven cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (remove from scanner)
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: No proven edge; candidates failed holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): -$2,400 (noise + costs on 537 trades).
- Gate change: None (remove from scanner)
- Confidence (1-5): 4

**### MEME**
- Real/noise verdict: No edge (n=4).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (remove from scanner)
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: No edge (n=11).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (remove from scanner)
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: No edge (n=16).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (remove from scanner)
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: No edge (n=10).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (remove from scanner)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up **CRYPTO** today only after raising the score gate (real money at 0.5% risk max). Demote **EQUITY** and **COMMODITY** per MUTATION_THREE_AXIS_PROTOCOL.md (mutate filters then kill if no improvement in 30 days). All other classes have no usable edge.
