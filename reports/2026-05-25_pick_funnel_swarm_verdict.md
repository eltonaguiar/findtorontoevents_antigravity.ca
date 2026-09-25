# Pick Funnel Swarm Verdict — 2026-09-25 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260925T041040Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is dead code in production. Every "edge" you're about to read about is *below* your own HC bar. That's the headline.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1791) and a trickle of FOREX/FUTURES/MEME have any verified-alpha flow. The funnel is essentially Smart-Picks-only.
3. **`trust=UNK` dominates every "PROVEN" cell.** The trust dimension is not discriminating — it's a constant. Any cell that includes `trust=UNK` is really just the other dims.

---

### INDEX
- Real/noise verdict: **Noise / no edge.** n_closed=5. WR 20% on 5 trades is statistically meaningless (95% CI roughly 0.5%–71%). `passed_smart=1519` of 1717 scanned (88%) means the Smart floor is not filtering INDEX at all — it's a rubber stamp. 1709 opened vs 8 closed means 99.5% of "opened" positions never resolved in 90d, which is itself a data-integrity red flag (stale open positions inflating the funnel).
- 90d expected P&L (1% risk, $100k): **-$400** (5 decisive trades × 1% × -0.8R avg, but honestly the sample is too small to quote a number — treat as $0 ± noise).
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` → raise to **75** (currently effectively ~0 given 88% pass rate). If no INDEX cell clears n>=20 in 90d, the correct move is to **stop opening INDEX picks entirely** until the scanner produces resolvable signals.
- Confidence (1-5): **1**

### COMMODITY
- Real/noise verdict: **Noise.** No PROVEN cells. Best PF cell (`rr=RR1.5-2.0 & score_dec=S50 & source=alpha_engine`) has train_pf=10.6, holdout_pf=0.68 — textbook **overfit that failed holdout**. WR_shrunk=50.0 exactly, wr_z=0.0, bonferroni_pass=false. This is the shape of a cell that got lucky on 12 train trades. Also note H-001 (COT leakage) and H-036 (inventory direction) are already falsified — do not chase commodity "edges" here.
- 90d expected P&L (1% risk, $100k): **-$1,320** (116 decisive × 1% × -0.114R avg from 43.1% WR at ~1:1 R:R).
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` → raise to **72**. 3599/6140 = 58.6% pass rate is too loose. Also add a hard `source != 'cot_positioning'` exclusion given H-001.
- Confidence (1-5): **2** (confident it's noise)

### BOND
- Real/noise verdict: **Noise, and one actively bad cell.** `trust=UNK & dir=LONG & source=bond_scanner` has n=20, WR=10%, PF=0.052, wr_z=-3.58. That's a *statistically significant loser*. The other cell (`score_dec=S50`) has train_pf=0.25, holdout_pf=3.75 — sign flip, no edge. `passed_smart=6` of 525 scanned (1.1%) means the Smart floor is doing its job on BOND, but the 492 opened trades are coming from somewhere else (probably a bypass path).
- 90d expected P&L (1% risk, $100k): **-$1,320** (33 decisive × 1% × -0.4R avg).
- Gate change: **Kill `source=bond_scanner` for LONG direction** — add to `quality_gates.py` a `BLOCKED_SOURCES_BOND = {'bond_scanner'}` or equivalent. This is the single highest-confidence negative signal in the whole dataset.
- Confidence (1-5): **4** (confident bond_scanner LONG is a loser)

### FOREX
- Real/noise verdict: **Mostly noise, one borderline cell.** The `multi_asset_copytrader` LONG RR1.0-1.5 cell has n=46, WR_shrunk=56.1%, PF=2.84, holdout_pass=true — but **bonferroni_pass=false** and wr_z=1.18. That's a ~1.2σ result across a search space of dozens of cells. Expected false-positive rate at that z across ~50 cells is high. The PF=2.84 is driven by a few large winners (avg_pnl 0.34% with 58.7% WR implies fat right tail). **Not proven.** Also: 21779/22763 = 95.7% Smart pass rate — the Smart floor is not filtering FOREX at all.
- 90d expected P&L (1% risk, $100k): **-$1,080** (486 decisive × 1% × -0.11R avg from 44.65% WR). If you *only* traded the copytrader LONG cell: ~+$1,600 on 46 trades, but with bonferroni=false I would not size to it.
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` → raise to **70** (from effective ~0). 95.7% pass rate is the single biggest funnel leak in the system.
- Confidence (1-5): **2**

### EQUITY
- Real/noise verdict: **The 98.55% WR cell is almost certainly leakage or single-symbol concentration.** n=69, wins=68, PF=220.8, wr_z=8.07. A PF of 220 is not a real trading edge — it's either (a) one symbol that gapped and got marked as 69 correlated trades, (b) a look-ahead in the `score_dec=S40` bucket (S40 is a *low* score decile — why would the lowest-scoring decile have the highest WR?), or (c) a mean_reversion family that's marking-to-market on intraday noise. The fact that `trust=UNK`, `conf=C<0.60`, and `dir=LONG` all produce *identical* n=69/wins=68/PF=220.8 confirms these are the **same 69 trades** sliced three ways — not three independent confirmations. **Do not trade this.** Flag as potential leakage recurrence per H-001 pattern.
- 90d expected P&L (1% risk, $100k): **+$1,670** on the headline 66.87% WR (166 decisive × 1% × +0.1R avg) — but I'd haircut this to **~$0** because the 68-win cell is suspect and likely dominates the aggregate.
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` → raise to **65** (256/5545 = 4.6% pass rate is actually reasonable, so the leak is downstream). The real fix is in `hc_filter.js`: add a **`maxTradesPerSymbol` cap of 3 per 24h** to prevent the 69-trade single-symbol concentration that's producing the fake PF=220.
- Confidence (1-5): **2** (confident the 98.55% cell is fake; less confident about the aggregate)

### CRYPTO
- Real/noise verdict: **The only class with a plausibly real edge — but the PF numbers are still inflated.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell: n=188, WR_shrunk=72.1%, PF=3.68, train_pf=3.55, holdout_pf=4.11, wr_z=6.71, bonferroni_pass=true. This is the **only cell in the entire dataset that passes Bonferroni**. That said: PF=3.68 on crypto with 72% WR is high but not impossible for a mean-reversion/breakout hybrid in a trending regime. The concern is **regime dependence** — 90d of crypto is one regime. The holdout split (154 train / 34 holdout) is temporal but short. I'd size this at **half-Kelly**, not full.
- 90d expected P&L (1% risk, $100k): On the proven cell only (188 trades × 1% × ~+0.4R avg): **+$7,500**. On the full CRYPTO book (2412 decisive × 1% × +0.02R avg from 45.6% WR): **+$4,800**. The proven cell is where the money is.
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` → **lower to 55** *only for* `source=alpha_engine & conf in [0.75, 0.80] & score_dec=S50`, and **raise to 75 for everything else**. This is a two-tier gate, not a single constant. In `hc_filter.js`, the HC threshold of `score>=80` is why `passed_high_conviction=0` — **lower HC score floor to 70 for CRYPTO only**, keep conf>=0.75 and trust>=60.
- Confidence (1-5): **4**

### ETF
- Real/noise verdict: **Noise.** n_closed=7, WR=14.3%. `passed_smart=293/333 = 88%` — Smart floor is a rubber stamp here too. No PROVEN cells, no best_pf cells. Nothing to see.
- 90d expected P&L (1% risk, $100k): **-$600** (7 decisive × 1% × -0.7R avg).
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` → raise to **75**, or **disable ETF scanning** until n_closed >= 30. 7 closed trades in 90d is not a strategy, it's a rounding error.
- Confidence (1-5): **1**

### FUTURES
- Real/noise verdict: **Noise.** n_closed=17, WR=29.4%. No PROVEN cells. H-005 already falsified the momentum anti-signal. `passed_smart=108/168 = 64%` pass rate is loose.
- 90d expected P&L (1% risk, $100k): **-$1,200** (17 decisive × 1% × -0.4R avg).
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` → raise to **72**. Also add `min_closed_trades_for_live = 30` guard so FUTURES doesn't open live positions until it has a track record.
- Confidence (1-5): **2**

### UNKNOWN
- Real/noise verdict: **Actively broken.** n_closed=7, WR=0.0%, 1401 opened. `passed_smart=179/1408 = 12.7%` — the Smart floor is filtering, but 1401 trades are still opening. This is a **classification bug**: 1408 scanned picks have no asset class. Every one of these should be blocked at ingestion.
- 90d expected P&L (1% risk, $100k): **-$700** (7 decisive × 1% × -1.0R avg, all losses).
- Gate change: In `production_scanner.py`, add `if asset_class == 'UNKNOWN': return None` before scoring. **Hard block.** This is not a gate tuning issue, it's a data hygiene issue.
- Confidence (1-5): **5** (confident this is a bug, not an edge)

### MEME
- Real/noise verdict: **Noise.** n_closed=4. Nothing to evaluate. `passed_smart=11/21 = 52%`.
- 90d expected P&L (1% risk, $100k): **-$200** (4 decisive × 1% × -0.5R avg).
- Gate change: `SMART_PICKS_MIN_SCORE_MEME` → raise to **80** (MEME should be the strictest class, not the loosest). Or disable until n_closed >= 30.
- Confidence (1-5): **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only, and only the `source=alpha_engine & conf∈[0.75,0.80] & score_dec=S50` cell.** It is the only cell in the entire 90-day dataset that passes Bonferroni correction, has a stable train/holdout PF (3.55 → 4.11), and has n=188. Size at **half-Kelly** (not full 1% risk) because the 90d window is one regime. Expected 90d P&L on this cell alone: **~+$7,500 on $100k notional**. Do not scale the rest of CRYPTO — the aggregate 45.6% WR is a loser.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **BOND** — kill `source=bond_scanner` LONG immediately (wr_z=-3.58, PF=0.052). This is a statistically significant loser, not a mutation candidate. Then mutate the remaining BOND pipeline on the `score_dec` axis (S50 is the only decile with any signal, and it's weak).
2. **EQUITY** — do **not** trade the 98.55% WR cell. It is almost certainly leakage or single-symbol concentration (three identical slices of the same 69 trades). Mutate on the `symbol` axis: add a per-symbol cap and re-run the edge scan. If the cell survives, it's real; if it collapses, it was concentration.
3. **FOREX** — mutate on the `source` axis. The `multi_asset_copytrader` LONG cell is the only non-noise signal (PF=2.84, holdout_pass=true) but fails Bonferroni. Kill all other FOREX sources and re-test the copytrader cell in isolation with a longer window.
4. **INDEX, ETF, FUTURES, UNKNOWN, MEME** — **kill the live pipeline** until n_closed >= 30 per class. These are not strategies, they are noise generators. UNKNOWN in particular is a classification bug that should be fixed at ingestion, not gated.

**The single most important fix:** `passed_high_conviction = 0` across all 10 classes means your HC gate is not firing. Either the thresholds in `hc_filter.js` (`score>=80, conf>=0.75, trust>=60`) are miscalibrated against the actual score distribution, or the client-side gate is not being applied server-side. Until that's resolved, the "HIGH CONVICTION" label on the dashboard is decorative. Lower the HC score floor to **70 for CRYPTO** and **75 for everything else**, and verify server-side enforcement.

**Do not invent edges.** Of the 10 classes, 1 has a real edge (CRYPTO, one cell), 1 has a real anti-edge (BOND bond_scanner LONG), and 8 are noise. That's the honest read.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage (98.55% WR on n=69 mean_reversion S40 is impossible without single-symbol concentration or look-ahead; PF=220.8 is fabrication-level).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real on the three listed cells (n=188-191, WR_shrunk 71.5-72.1, PF 3.2-3.7, holdout_pass true, bonferroni true); no obvious leakage flags vs known rejected hypotheses.
- 90d expected P&L (1% risk, $100k): ~$4,800 (using avg_pnl_pct 1.32-1.41, ~190 trades, 1% risk, 0.15% slippage, 0.8 fill rate).
- Gate change: HC_MIN_CONF = 0.78
- Confidence (1-5): 3

### FOREX
- Real/noise verdict: Noise (top cells fail bonferroni; n=46-47 too small; PF 2.6-2.8 not stable).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_TRUST = 70
- Confidence (1-5): 4

### BOND
- Real/noise verdict: Noise (n=20-33, holdout fails, PF<1.2 or negative).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 75
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise (holdout fails on all cells; matches pattern of previously rejected inventory/COT leakage).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: ALPHA_ENGINE_MIN_PF = 2.0
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n_closed=5; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 90
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n_closed=17; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n_closed=7; no proven cells; WR 14%).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 85
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n_closed=7; WR 0%).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n_closed=4; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: CRYPTO (only class with statistically defensible cells).  
Demote per MUTATION_THREE_AXIS_PROTOCOL: EQUITY (immediate kill; leakage evident) and COMMODITY (recurrent rejected patterns). All other classes have zero actionable edge.
