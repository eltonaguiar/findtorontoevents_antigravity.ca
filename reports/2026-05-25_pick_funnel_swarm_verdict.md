# Pick Funnel Swarm Verdict — 2026-09-30 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260930T041122Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three system-wide observations that dominate everything below:

1. **The funnel is broken at the top.** `passed_high_conviction = 0` for *every* class. `passed_proven = 0` for *every* class. The HC gate in `hc_filter.js` (score≥80, conf≥0.75, trust≥60) is filtering out 100% of picks. Either the gate is mis-wired, or the scoring pipeline never emits score≥80 / trust≥60. Either way, the "HIGH CONVICTION" tier is currently a null set — every "edge" below is being surfaced *outside* the intended gate.
2. **`trust=UNK` dominates every PROVEN cell.** Every single "proven" edge in CRYPTO and EQUITY is `trust=UNK`. That means the trust dimension is not discriminating — it's a constant. Any cell that includes `trust=UNK` is *identical* to the same cell without it (see CRYPTO cells 1 and 2: identical n, wins, PF). This is a red flag for a broken trust-scoring path, not an edge.
3. **`score_dec=S50` / `S40` are the only score deciles that appear.** That's suspicious — it suggests the score distribution is degenerate (everything lands in one or two deciles), which means "score" is not a real ranking variable in the current pipeline.

---

### INDEX
- Real/noise verdict: **NOISE / INSUFFICIENT DATA.** n_closed=5. WR=20% on 5 decisive trades. 1758 scanned → 1750 opened → 8 closed. The 99.5% open-to-close gap means the "closed" sample is a tiny, non-random survivor set (likely time-stopped or manually closed). No edge claim is possible. `passed_smart=1552` on 1758 scanned (88%) means the Smart floor is essentially a pass-through for INDEX — it is not filtering.
- 90d expected P&L (1% risk, $100k): **$0** (do not trade; sample is meaningless).
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` — raise until `passed_smart/scanned` drops below ~30%. Current 88% pass rate means the floor is doing nothing.
- Confidence (1-5): **1**

### FOREX
- Real/noise verdict: **NOISE.** n_closed=475, WR=42.95% — *below* breakeven for typical R:R. `top_edges_proven` is empty. The best cell (`rr=RR1.0-1.5 & fam=mean_reversion & dir=LONG & source=multi_asset_copytrader`, n=44, WR=59.09%, PF=2.945) **fails Bonferroni** (`bonferroni_pass: false`) and has `wr_z=1.206` — that's a ~1.2σ result, i.e. p≈0.11 one-sided, and after multiple-testing correction it's noise. The holdout (n=17) is too small to confirm. The `consensus` source you flagged: I see `multi_asset_copytrader` here, not `consensus` — but the same logic applies: n=44 with a 1.2σ z-score is not an edge, it's a coin flip that got lucky on 26 of 44. **Do not size this.**
- 90d expected P&L (1% risk, $100k): **$0** (no proven edge; the "best" cell is Bonferroni-failed).
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` — currently 21652/22641 = 95.6% pass rate. Raise aggressively; a 95% pass rate is not a gate, it's a formality. Target ≤40% pass.
- Confidence (1-5): **1**

### CRYPTO
- Real/noise verdict: **MIXED — one cell looks real, two look like the same cell restated.**
  - `conf=C0.75-0.80 & dir=LONG & score_dec=S50`: n=181, WR=72.38%, WR_shrunk=70.15%, PF=3.053, holdout PF=2.832 (n=40), `wr_z=6.022`, Bonferroni pass. **This is the strongest cell in the entire report.** n=181 is adequate, holdout holds, z=6.0 survives multiple testing. The `trust=UNK` variant is *identical* (same n, same wins) — confirming trust is a constant, not a discriminator.
  - `conf=C0.75-0.80 & dir=LONG & source=alpha_engine`: n=249, WR=64.26%, PF=2.47, holdout PF=2.019 (n=63), z=4.5, Bonferroni pass. **Also real**, but note it's a *superset* of the first cell (the first cell is the S50 slice of this one). These are not independent edges — they're nested.
  - **Leakage check:** The `ml` source you flagged does not appear in the top cells here — the top cells are `alpha_engine` and `score_dec=S50`. But the pattern (conf 0.75–0.80 + LONG + one score decile) is exactly the shape of a **confidence-band artifact**: if the model's confidence is calibrated such that 0.75–0.80 is the "sweet spot" and 0.80+ is overconfident, that's a real calibration finding, not leakage. However, the fact that *only* S50 appears (not S40, S60, S70) suggests the score decile is collinear with the confidence band — i.e., you may be looking at one signal sliced two ways. **Treat as one edge, not two.**
  - **Single-symbol concentration:** not visible in the aggregate, but with n=181 across 90 days in crypto, you should verify no single token (e.g. a memecoin that 10x'd) accounts for >20% of wins. The `MEME` class separately shows WR=25% — so if the S50/LONG cell is secretly memecoin-heavy, it's fragile.
- 90d expected P&L (1% risk, $100k): **~$2,300–$3,400** on the S50/LONG cell alone. Math: 181 trades × 1% risk = $1,000 risked per trade × avg_pnl_pct 1.2839% of notional... actually let me be precise. At 1% risk per trade on $100k = $1,000 risked. With PF=3.05 and WR=72%, expectancy per trade ≈ (0.72 × avg_win) − (0.28 × avg_loss). Using avg_pnl_pct=1.2839% as the *return on notional* per trade: 181 × 1.2839% × $100k = **$232,400 gross** — but that's if you size at full notional, not 1% risk. At 1% risk with a typical 1:1.5 R:R, per-trade expectancy ≈ 0.72×1.5R − 0.28×1R = 0.80R = $800/trade × 181 = **~$144,800**. That number is absurdly high and should make you suspicious — it implies the avg_pnl_pct is being computed on notional, not on risk. **Realistic estimate: $15k–$40k** over 90 days if the edge is real and slippage is 5–10 bps. I'd underwrite to **$20k** and treat anything above as a data artifact.
- Gate change: `HC_MIN_CONF` in `hc_filter.js` — currently 0.75. The edge lives *exactly* at 0.75–0.80. Lower the HC confidence floor to **0.74** (or widen the band) so the S50/LONG cell actually reaches HC. Right now `passed_high_conviction=0` means this edge is invisible to the HC tier.
- Confidence (1-5): **3** (the S50/LONG cell is the only thing in this report I'd put money behind, and only after verifying no single-symbol concentration).

### EQUITY
- Real/noise verdict: **LEAKAGE / LOOK-AHEAD — DO NOT TRADE.** The cell `trust=UNK & fam=mean_reversion & score_dec=S40`: n=67, WR=98.51%, PF=**214.55**, holdout PF=99.0. A PF of 214 is not an edge — it's a bug. Real strategies top out around PF 3–5. PF 214 means either (a) losses are being recorded as ~0 or wins are being recorded at absurd multiples, (b) the "closed" set is survivorship-filtered (only winners get closed), or (c) there's a timestamp/look-ahead issue where the entry price is set after the move. The `wr_z=7.941` is meaningless when the underlying P&L distribution is degenerate. **This is the single most dangerous cell in the report** because it looks "proven" by every automated check (Bonferroni pass, holdout pass) — the checks are passing because the data is broken, not because the edge is real. Flag for immediate data-integrity audit.
- 90d expected P&L (1% risk, $100k): **$0** (do not trade; PF=214 is a data error, not an edge).
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` — currently 249/5621 = 4.4% pass rate, which is actually the *only* sane pass rate in the report. But the mean_reversion/S40 cell is passing through it, so the gate is not catching the broken cell. Add a **PF sanity cap** (reject any cell with PF>10 as a data error) before this reaches the dashboard.
- Confidence (1-5): **1** (and a data-integrity ticket).

### ETF
- Real/noise verdict: **NOISE.** n_closed=8. No edges. 293/338 = 87% Smart pass rate — gate is a pass-through.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` — raise until pass rate <30%.
- Confidence (1-5): **1**

### BOND
- Real/noise verdict: **NOISE.** n_closed=31, WR=45.16%. Best cell n=20, WR=55%, PF=1.636, `bonferroni_pass: false`, `holdout_pass: false`, train_pf=0.348 (train was *losing*). The holdout "pass" is n=12 — meaningless. 3/542 = 0.55% Smart pass rate is the only gate in the report that's actually restrictive, but it's restricting to a sample too small to conclude anything.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: none — the gate is already tight. The issue is sample size, not the gate.
- Confidence (1-5): **1**

### COMMODITY
- Real/noise verdict: **NOISE — and note the H-001/H-036 history.** `top_edges_proven` is empty. Best cell (`trust=UNK & rr=RR1.5-2.0 & fam=mean_reversion`, n=20, WR=60%, PF=4.601) has `holdout_pass: false` (n=2 holdout) and `bonferroni_pass: false`. The `alpha_engine` mean_reversion cell (n=32, WR=62.5%, PF=3.971) also fails both. Given H-001 (COT look-ahead) and H-036 (inventory direction) were both killed in this exact class, **any mean_reversion signal here should be treated as a potential leakage recurrence until proven otherwise.** The `trust=UNK` prefix again signals a broken trust dimension.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` — 3403/5950 = 57% pass rate. Raise to cut pass rate to <25%, and add a hard block on `fam=mean_reversion` in COMMODITY pending re-validation against H-001/H-036.
- Confidence (1-5): **1**

### FUTURES
- Real/noise verdict: **NOISE.** n_closed=18, WR=27.78%. No edges. H-005 already killed the momentum inversion hypothesis here. 110/167 = 66% Smart pass rate.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` — raise to cut pass rate <30%.
- Confidence (1-5): **1**

### UNKNOWN
- Real/noise verdict: **NOISE / DATA HYGIENE FAILURE.** n_closed=7, WR=0%. 1396 scanned, 1389 opened, 7 closed. The fact that 1396 instruments have no asset class is itself the finding — fix the classifier before analyzing this bucket.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: none — fix the asset-class classifier upstream.
- Confidence (1-5): **1**

### MEME
- Real/noise verdict: **NOISE.** n_closed=4. No edges. 11/22 = 50% Smart pass rate on a tiny sample.
- 90d expected P&L (1% risk, $100k): **$0**.
- Gate change: none — sample too small.
- Confidence (1-5): **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO, and only the `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell.** It is the only cell in the entire report with n≥100, WR_shrunk≥70%, PF≥3, holdout PF≥2.8, z≥6, and Bonferroni pass. Even here, underwrite to ~$20k/90d, not the $140k+ the raw math implies, and verify no single-symbol concentration before sizing. The `alpha_engine` source cell is the same edge restated — do not double-count.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL.md (mutate before kill): EQUITY.** The mean_reversion/S40 cell is not an edge — it's a data-integrity failure (PF=214, WR=98.5%). Do not kill the class; mutate the *data pipeline* first: audit how `closed` is determined, how P&L is computed, and whether the S40 decile is a survivorship artifact. If the pipeline is fixed and the edge disappears, then kill. If it survives at PF 1.5–3, re-promote.

**Second demotion: FOREX.** 42.95% WR on n=475 is a losing class. The "best" cell fails Bonferroni. Mutate the Smart floor (currently 95.6% pass rate — not a gate) before considering kill.

**Third: COMMODITY.** Given H-001 and H-036 were both killed here, and the surviving "edges" are all `mean_reversion` with `trust=UNK` and failed Bonferroni, treat this as a leakage-recurrence watchlist. Mutate the trust-scoring path (why is everything UNK?) before re-testing.

**Cross-cutting fixes required before any of this is trustworthy:**
- `passed_high_conviction=0` everywhere → `hc_filter.js` is mis-wired or the scoring pipeline never emits score≥80/trust≥60. Fix this before trusting any HC-tier claim.
- `trust=UNK` on every PROVEN cell → trust dimension is a constant. Either fix the trust scorer or drop the dimension.
- `score_dec` only ever S40/S50 → score distribution is degenerate. The "score" variable is not ranking.
- Add a **PF>10 sanity cap** to the edge-detection pipeline — it would have caught the EQUITY PF=214 cell automatically.

**Bottom line: one real edge (CRYPTO S50/LONG), one data-integrity emergency (EQUITY), and seven classes with no demonstrable edge.** Do not scale anything except CRYPTO, and do not trust the EQUITY numbers until the pipeline is audited.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real. n=181 closed, WR_shrunk 70.15%, PF 3.05 with clean holdout (2.83) and bonferroni pass. No obvious single-symbol concentration flagged.
- 90d expected P&L (1% risk, $100k): ~$8,400 (181 trades × $1k risk × ~0.046 expectancy after 0.2% slippage).
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` = 50
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Sample-noise / leakage. 66/67 wins and PF 214 on mean-reversion S40 cell is statistically impossible without single-symbol concentration or look-ahead.
- 90d expected P&L (1% risk, $100k): $0 (edge is spurious; live results will collapse).
- Gate change: `EQUITY_MEAN_REVERSION_MIN_TRUST` = 70
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. No proven cells; best_pf_overall fails bonferroni and has tiny holdout n.
- 90d expected P&L (1% risk, $100k): -$2,800 (costs eat the marginal edge).
- Gate change: `HC_FILTER_MIN_CONF` = 0.78
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: Noise. All cells fail holdout; known COT leakage history makes any mean-reversion signal suspect.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `SMART_PICKS_MIN_TRUST_COMMODITY` = 65
- Confidence (1-5): 4

**### BOND**
- Real/noise verdict: Noise. n=20 cell fails holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `HC_FILTER_MIN_SCORE` = 55
- Confidence (1-5): 3

**### ETF / FUTURES / INDEX / UNKNOWN / MEME**
- Real/noise verdict: Noise. All n_closed <20 or zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `SMART_PICKS_MIN_SCORE` = 60 (global)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-passed edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL — its “edge” is almost certainly leakage and must be mutated before any further capital allocation. All other classes have no actionable edge.
