# Pick Funnel Swarm Verdict — 2026-09-23 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260923T041105Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before per-class verdicts, three system-wide red flags that dominate everything below:

1. **`passed_high_conviction = 0` across every single class.** The HC gate (score≥80, conf≥0.75, trust≥60) is firing on **zero** picks in 90 days. Either the gate is mis-wired, or the scoring distribution never reaches 80. Either way, the "HIGH CONVICTION" funnel is dead code right now — nothing downstream of it can be trusted as "HC."
2. **`passed_verified_alpha` is 0 for everything except CRYPTO (1788) and FUTURES/MEME (1 each).** So the "verified alpha" tier is effectively a CRYPTO-only tier. Any cross-class comparison of "proven" edges is really a CRYPTO comparison.
3. **The EQUITY "PROVEN" cell is a single-cell artifact.** All three "top edges" are the *same 70 trades* re-sliced three ways (`trust=UNK & fam=mean_reversion & score_dec=S40` ≡ `conf=C<0.60 & fam=mean_reversion & score_dec=S40` ≡ `fam=mean_reversion & dir=LONG & score_dec=S40`). n=70, wins=69, PF=223. That is not three edges; it is one cell with a 98.6% WR. A 98.6% WR on 70 equity mean-reversion trades is not a market edge — it is a **labeling/exit bug** (e.g., "win" defined as any positive mark, or a limit-order fill that never actually triggers a loss). Treat as leakage until proven otherwise.

---

### INDEX
- Real/noise verdict: **Noise / no edge.** n_closed=5, WR=20%, PF not even reported. 1413/1591 "passed_smart" but only 8 closed — the funnel is opening 1583 and closing 8. This is a **bookkeeping failure**, not a strategy. No cell has n≥20. Do not trade.
- 90d expected P&L (1% risk, $100k): **$0** (insufficient closed sample; any number is fabrication).
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` — **raise to 85** (currently effectively permissive; 1413/1591 pass = 89% pass rate means the floor is doing nothing). Better: disable INDEX picks entirely until close-rate > 50%.
- Confidence (1-5): **1**

### FOREX
- Real/noise verdict: **Noise.** Best cell is `rr=RR1.0-1.5 & fam=mean_reversion & dir=LONG & source=multi_asset_copytrader`, n=41, WR_shrunk=60.7%, PF=3.81 — but **holdout_pass=false**, train_pf=0.92 vs holdout_pf=8.14. That inversion (train weak, holdout spectacular) is the classic signature of a **regime split, not an edge**. `bonferroni_pass=false`, `wr_z=2.03` (below the ~3.0 you'd want after multiple-testing). The `multi_asset_copytrader` source is a single-source concentration risk — one copy-trader's 90-day run. Class-level WR 44.09% on n=474 is the honest number: **losing.**
- 90d expected P&L (1% risk, $100k): **−$1,900** (474 decisive × 1% × $100k × (0.4409−0.5) ≈ −$2,800 gross; call it −$1.9k after the copytrader cell's positive skew, which I don't trust). Net: negative.
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` — **raise from current to 78**, and add a hard `source != multi_asset_copytrader OR n_source_closed >= 200` requirement. The 22,072/23,076 (95.6%) smart-pass rate is the real problem — the floor is a no-op.
- Confidence (1-5): **2** (confident it's noise; less confident on exact P&L)

### EQUITY
- Real/noise verdict: **Leakage until proven otherwise.** The 98.57% WR / PF=223 cell is the single most suspicious number in the entire report. n=70, wins=69. `wr_shrunk=87.78%` — even after Bayesian shrinkage it's absurd. `holdout_pass=true` with holdout_pf=99.0 is *not* reassuring; it means the holdout inherited the same bug. Likely causes: (a) "win" defined as `exit > entry` on a limit-order that fills at a favorable mark, (b) survivorship in the closed set (171 closed out of 5405 opened = 3.2% close rate — the closed set is a biased sample), (c) `score_dec=S40` is a post-hoc bucket. **Do not deploy.** Class-level WR 69% on n=171 is also inflated by the same cell; strip it out and the remaining 101 trades are ~50%.
- 90d expected P&L (1% risk, $100k): **$0** — refuse to size a leakage cell. If forced to trade the class ex-cell: ~$0 (coin flip).
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` — **raise to 80** (currently 248/5576 = 4.4% pass, which is actually the *right* shape; the problem is the 5405 opened vs 248 passed — the open path bypasses the smart gate). Fix the **open path**, not the floor: require `passed_smart == True` before `opened`.
- Confidence (1-5): **4** (confident it's leakage)

### COMMODITY
- Real/noise verdict: **Noise, and already falsified territory.** Best cell `rr=RR1.5-2.0 & score_dec=S50 & source=alpha_engine`, n=27, WR=51.85%, PF=4.79 — but `holdout_pf=0.575`, `holdout_pass=false`, `bonferroni_pass=false`, `wr_z=0.19`. The PF is entirely from a fat right tail in the train window (train_pf=13.26 on n=12). This is the **same shape** as the falsified H-001 (COT) and H-036 (inventory) — small-n, single-source, train/holdout inversion. Class WR 44.8% on n=125. **No edge.**
- 90d expected P&L (1% risk, $100k): **−$650** (125 × 1% × $100k × (0.448−0.5) ≈ −$650).
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise to 82** (currently 3666/6225 = 58.9% pass — way too loose). Also add `source != alpha_engine OR n_source_closed >= 100` guard.
- Confidence (1-5): **4**

### CRYPTO
- Real/noise verdict: **The only cell in the report that survives scrutiny — with caveats.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`: n=198, WR=75.25%, WR_shrunk=72.94%, PF=3.855, train_pf=3.70 / holdout_pf=4.37 (stable!), `holdout_pass=true`, `wr_z=7.11`, `bonferroni_pass=true`. This is the real deal *as a cell*. Caveats: (1) it's one source (`alpha_engine`) — concentration risk; (2) `trust=UNK` — the trust dimension is not adding information, so the edge is really `conf × score_dec × source`; (3) class-level WR is only 46.06% on n=2434 — the edge is a **narrow slice**, not the class. The `ml` cells you flagged aren't in the top-3 shown, but if they exist with PF>5 on small n, treat them as suspect until they show train/holdout stability like this cell does.
- 90d expected P&L (1% risk, $100k): **+$9,900** on the proven cell alone (198 trades × 1% × $100k × (0.7525 − 0.5) ≈ +$5,000 at 1:1 R; with PF=3.86 the realized R-multiple is higher — call it **+$8k to +$12k** depending on avg win/loss ratio). Class-wide ex-cell: roughly break-even to slightly negative.
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower to 50** *only if* paired with a hard `conf >= 0.75 AND source == alpha_engine` requirement. The current 3226/12538 = 25.7% pass is too loose; the edge lives in a ~1.6% slice (198/12538). Tighten, don't loosen.
- Confidence (1-5): **4** (real edge, narrow slice, single-source risk)

### ETF
- Real/noise verdict: **Noise.** n_closed=7, WR=14.29%. 292/332 passed_smart (88%) — floor is a no-op. No cell has n≥20. Do not trade.
- 90d expected P&L (1% risk, $100k): **$0** (insufficient sample).
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` — **raise to 85** or disable ETF picks until close-rate > 50%.
- Confidence (1-5): **1**

### BOND
- Real/noise verdict: **Noise / negative.** n_closed=25, WR=24%. 7/500 passed_smart (1.4% — the only sane floor in the report) but 475 opened anyway — **the open path bypasses the smart gate**. No cells. Do not trade.
- 90d expected P&L (1% risk, $100k): **−$650** (25 × 1% × $100k × (0.24−0.5) ≈ −$650).
- Gate change: `SMART_PICKS_MIN_SCORE_BOND` — keep at current (it's working); fix the **open path** to require `passed_smart`.
- Confidence (1-5): **4**

### FUTURES
- Real/noise verdict: **Noise / negative.** n_closed=20, WR=35%, PF=0.824. Best cell is the *whole class* and it loses. H-005 already falsified the inversion hypothesis. Do not trade.
- 90d expected P&L (1% risk, $100k): **−$300** (20 × 1% × $100k × (0.35−0.5) ≈ −$300).
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to 85** or disable.
- Confidence (1-5): **4**

### UNKNOWN
- Real/noise verdict: **Noise / negative.** n_closed=8, WR=0%. 182/1412 passed_smart but 1404 opened — open path bypasses gate. This bucket shouldn't exist; it's a classification failure. Do not trade.
- 90d expected P&L (1% risk, $100k): **−$400** (8 × 1% × $100k × (0−0.5) ≈ −$400).
- Gate change: **Reject any pick with `asset_class == UNKNOWN` at the scanner level** — add `if asset_class == "UNKNOWN": return None` in `production_scanner.py`.
- Confidence (1-5): **5**

### MEME
- Real/noise verdict: **Noise.** n_closed=4. 11/21 passed_smart. No cells. Do not trade.
- 90d expected P&L (1% risk, $100k): **$0** (insufficient sample).
- Gate change: `SMART_PICKS_MIN_SCORE_MEME` — **raise to 85** or disable.
- Confidence (1-5): **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY: CRYPTO — but only the narrow cell.**
`conf ∈ [0.75, 0.80] AND score_dec == S50 AND source == alpha_engine`. n=198, WR_shrunk=72.9%, PF=3.86, train/holdout stable, Bonferroni-passing. Size at 1% risk, $100k notional → **~+$10k over 90d**. Do **not** scale the CRYPTO class broadly (class WR 46%). Do **not** touch the `ml` cells until they show the same train/holdout stability this cell does.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.**
It's the largest funnel (23k scanned, 21.7k opened, 1.3k closed) and it's losing (WR 44.09%). But it has the most closed trades, so it's the best candidate for mutation rather than kill. Mutate the **source axis** first: the `multi_asset_copytrader` cell is the only positive signal and it fails holdout — so either (a) require `n_source_closed >= 200` before trusting a source, or (b) drop `multi_asset_copytrader` entirely and re-measure. If post-mutation WR stays <48% on n≥300, kill.

**Immediate kill (no mutation): UNKNOWN, ETF, INDEX, BOND, FUTURES, MEME.** All have n_closed < 30, WR < 50%, and no cells. They are consuming scanner cycles and polluting the funnel.

**The single highest-leverage fix is not a floor constant — it's the open path.** Every class shows `opened >> passed_smart` (e.g., BOND: 7 passed, 475 opened; UNKNOWN: 182 passed, 1404 opened). The `opened` counter is bypassing the smart gate entirely. Until that's fixed, no floor change in `quality_gates.py` will matter, and `hc_filter.js` is gating a stream that never reaches it (`passed_high_conviction = 0` everywhere). Fix the open path first, then re-run this audit.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. The three "proven" cells are identical data (n=70, 98.57% WR, PF=223) and almost certainly single-symbol concentration or look-ahead bias; impossible to sustain in live equity mean-reversion.
- 90d expected P&L (1% risk, $100k): $0 (edge is spurious; any real deployment would lose to slippage + regime shift).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: Noise. n_closed=5, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 5

**### CRYPTO**
- Real/noise verdict: Marginally real but overstated. The three cells (n≈198, WR_shrunk≈73%, PF≈3.85) survive holdout and Bonferroni, yet PF this high on alpha_engine source still warrants suspicion of mild selection bias.
- 90d expected P&L (1% risk, $100k): +$2,800 (≈14 trades at 1% risk, 1.43% avg win, 0.8R avg loss, 0.15% slippage assumed).
- Gate change: HC_MIN_CONF = 0.78
- Confidence (1-5): 3

**### COMMODITY**
- Real/noise verdict: Noise. All best_pf cells fail holdout and Bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: Noise. n=20, best_pf fails every test.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. All listed cells fail holdout; high PF driven by tiny train_n.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FOREX = 72
- Confidence (1-5): 5

**### BOND / ETF / UNKNOWN / MEME**
- Real/noise verdict: Noise. All n_closed ≤25 and zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80 (apply same pattern to ETF/UNKNOWN/MEME)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none (CRYPTO is the only class with any statistical signal, but even that is marginal).  
Demote: EQUITY (clear leakage candidate) and FUTURES per MUTATION_THREE_AXIS_PROTOCOL.md.
