# Pick Funnel Swarm Verdict — 2026-10-07 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261007T041135Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (score≥80, conf≥0.75, trust≥60) is firing on literally nothing. Either the gate is mis-wired, or the scoring distribution never reaches 80, or trust is capped below 60. This is the single biggest finding in the dataset — the "HIGH CONVICTION" funnel is dead.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1775) and FOREX (3) and FUTURES (1) and MEME (1) produce any. The verified-alpha stage is effectively a CRYPTO-only gate.
3. **`opened` >> `passed_smart` in every class** (e.g. EQUITY 5517 opened vs 252 passed_smart; FOREX 21674 vs 22107 — that one is inverted). The funnel is not actually gating opens. Whatever `passed_smart` is, it is not the binding constraint on what gets opened. This means every "edge" claim below is about a *label*, not about *what we traded*.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell is `fam=mean_reversion & score_dec=S40` with n=67, WR=98.51%, PF=216.95. A 98.5% win rate on 67 trades with PF 217 is not a real edge — it is a **labeling artifact**. Almost certainly: (a) mean_reversion trades are being closed on a mean-touch that is mechanically guaranteed by the entry definition (buy dip, mark win when price ticks back to VWAP), or (b) `score_dec=S40` is a post-hoc bucket that correlates with the exit rule. The holdout "passing" (PF 99 on n=27) is not reassuring — it means the artifact is stable, not that the edge is real. Compare to the class-level WR of 68.39% on n=155: the "edge" cell is 67 of those 155 trades, i.e. **43% of all EQUITY closes are in one suspicious bucket**. This is the classic signature of a mean-reversion exit rule that books tiny wins and lets losers run — PF 217 with avg_pnl 1.29% and WR 98.5% implies avg loss is ~-0.006%, which is impossible unless losses are being truncated or mislabeled. **Flag as leakage recurrence.**
- **90d expected P&L (1% risk, $100k):** Do not deploy. If forced to mark-to-model the artifact: 67 trades × 1% × 1.29% avg = **~$860** gross, but this is fictional because the loss side is broken. Realistic expectation if the exit rule is fixed: **negative**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — but the real fix is upstream. The mean_reversion family needs an exit-rule audit before any score gate matters. Set `SMART_PICKS_MIN_SCORE_EQUITY = 55` (from current effective ~40) to stop the S40 bucket from dominating, but treat this as a band-aid.
- **Confidence (1-5):** 1

### COMMODITY
- **Real/noise verdict:** **NOISE.** Best cell is `rr=RR>=2.0 & source=alpha_engine`, n=23, WR=73.91%, shrunk 62.79%, PF 4.98. But `holdout_pass: false`, `bonferroni_pass: false`, and the train PF (2.99) vs holdout PF (44.36) divergence on n=9 holdout is a textbook small-sample blowup. n=23 is below any reasonable threshold. Class-level WR is 53.66% on n=82 — barely above coin-flip, and the "edge" cell is 28% of all closes. Given [H-001] (COT leakage) and [H-036] (inventory gate rejected) are already in the registry, this class has a documented history of fake edges. **No proven edge.**
- **90d expected P&L (1% risk, $100k):** ~$0 to slightly negative. At 53.66% WR with unknown R:R, expect **-$200 to +$150** depending on payoff asymmetry. Not deployable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **65** (from current effective ~50) to cut the 3313 passed_smart down toward the ~300 that actually have signal. The 3313/5742 = 58% pass rate is absurd for a "smart" gate.
- **Confidence (1-5):** 2

### INDEX
- **Real/noise verdict:** **NOISE.** n_closed=5. WR=20%. There is no edge. There is not even a sample. The 1502/1806 passed_smart rate (83%) is a gate that is not gating.
- **90d expected P&L (1% risk, $100k):** **-$400** (5 trades, 1 loss-heavy). Meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **70** and add a minimum-n guard. Better: disable INDEX opens until n≥50.
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** **NOISE / LEAKAGE.** The `regime` / `regime_terminal` cell (n=54, WR=68.52%, PF 3.20) has `holdout_pass: false`, `bonferroni_pass: false`, and — critically — **train PF 0.298 on n=17 vs holdout PF 14.15 on n=37**. That is not an edge; that is a regime-terminal source that was almost certainly introduced mid-window and is being evaluated on data it was fit to. The user's prompt specifically flags "FOREX `consensus`" — the data shows `regime_terminal`, which is the same family of concern. Class-level WR is 43.08% on n=1354 — **below coin-flip**. The 22107/23028 = 96% passed_smart rate is the most damning number in the entire dataset: the FOREX smart gate passes 96% of everything. It is not a gate.
- **90d expected P&L (1% risk, $100k):** At 43.08% WR, 1354 closes, 1% risk: **negative**. Rough estimate **-$3,000 to -$8,000** depending on payoff. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — this is the highest-leverage single change in the whole system. Raise from effective ~30 to **70**. That alone would cut 22107 → a few hundred and force the regime_terminal source to prove itself on a real sample.
- **Confidence (1-5):** 1

### CRYPTO
- **Real/noise verdict:** **PARTIALLY REAL, but the headline cell is suspicious.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell: n=170, WR=71.18%, shrunk 68.95%, PF 3.29, **holdout_pass: true, bonferroni_pass: true, wr_z=5.52**. This is the only cell in the entire dataset that survives Bonferroni and has a holdout that doesn't blow up (train PF 3.72 → holdout PF 2.15, a *decay* not a blowup — that's what a real edge looks like). n=170 is the largest proven cell. **However:** the user flagged "CRYPTO `ml`" — the data shows `alpha_engine`, not `ml`. If there is a separate `ml` source with PF >5, it is not in this JSON and should be treated as unverified. The `alpha_engine` cell is the one real candidate here. Caveat: `trust=UNK` on the same cell means trust scoring is not contributing — the edge is conf+score+source only.
- **90d expected P&L (1% risk, $100k):** 170 trades × 1% risk × 1.34% avg_pnl = **~$2,280** gross on the proven cell. Class-wide at 45.24% WR on 2441 closes is **negative** (~-$5,000 to -$15,000). The edge is real but narrow — it is ~7% of CRYPTO closes. **Deploy only the proven cell, not the class.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise to **60** (from effective ~50) to concentrate on the S50+ bucket, AND add a hard filter: `source == 'alpha_engine' AND conf >= 0.75`. The 3354/12785 = 26% pass rate is closer to sane than FOREX but still too loose.
- **Confidence (1-5):** 3

### FUTURES
- **Real/noise verdict:** **NOISE.** n_closed=16, WR=31.25%. [H-005] already killed the momentum inversion. No edge.
- **90d expected P&L (1% risk, $100k):** **-$600** (16 trades, 31% WR). Meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **75**, or disable until n≥50.
- **Confidence (1-5):** 1

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=9, WR=22.22%. No edge, no sample.
- **90d expected P&L (1% risk, $100k):** **-$500**. Meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **70**.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** **NOISE.** n_closed=5, WR=0%. The fact that 1386 instruments are classified UNKNOWN and 1381 of them opened is a data-hygiene failure, not a trading signal.
- **90d expected P&L (1% risk, $100k):** **-$500**. Meaningless.
- **Gate change:** Add a hard reject in `quality_gates.py`: `if asset_class == 'UNKNOWN': return False`. Do not trade unclassified instruments.
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=31, WR=45.16%. Below coin-flip. 3/556 passed_smart — the gate is over-restrictive here and under-restrictive everywhere else, which suggests the per-class floor map is miscalibrated.
- **90d expected P&L (1% risk, $100k):** **-$300**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — lower to **40** to actually let the 3 that pass through, but add a minimum-n guard before any BOND edge is claimed.
- **Confidence (1-5):** 1

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=4. Not a sample.
- **90d expected P&L (1% risk, $100k):** **-$200**. Meaningless.
- **Gate change:** Disable MEME opens until n≥30.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money:** **CRYPTO, and only the `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell.** It is the only cell in the entire 90-day dataset that passes Bonferroni, has a holdout that decays rather than explodes, and has n≥100. Expected 90d P&L on that cell alone at 1% risk: **~$2,280**. Size it at 0.5% risk initially (not 1%) until the next 30-day window confirms the holdout PF stays ≥1.5.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **FOREX** — the 96% passed_smart rate is a broken gate, not a strategy. Mutate `SMART_PICKS_MIN_SCORE_FOREX` from ~30 → 70 and re-run 30d. If WR stays <50%, kill.
2. **EQUITY** — the mean_reversion/S40 cell is a leakage recurrence (98.5% WR, PF 217). Mutate the exit rule first; if the cell collapses to <55% WR, kill the family.
3. **COMMODITY** — already has two killed hypotheses in the registry ([H-001], [H-036]). Mutate `SMART_PICKS_MIN_SCORE_COMMODITY` 50 → 65; if the RR≥2.0 cell doesn't survive a real holdout, kill.
4. **INDEX, FUTURES, ETF, BOND, MEME, UNKNOWN** — insufficient n. Do not kill; **freeze opens** until n≥50 per class. UNKNOWN should be hard-rejected immediately (data hygiene, not strategy).

**The single most important fix is not a gate value — it is that `passed_high_conviction = 0` everywhere.** The HC gate in `hc_filter.js` (score≥80, conf≥0.75, trust≥60) is either mis-wired or the scoring distribution never reaches 80. Until that is diagnosed, the "HIGH CONVICTION" label on the dashboard is decorative. Fix that before tuning any per-class floor.

**Brutal summary:** 9 of 10 asset classes have no edge. 1 (CRYPTO) has a narrow, real, Bonferroni-surviving edge in ~7% of its closes. The funnel is not gating (opened >> passed_smart in most classes), the HC gate is dead, and the two "best" cells (EQUITY mean_reversion, FOREX regime_terminal) are leakage artifacts. Do not scale anything except the CRYPTO alpha_engine cell.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Real. n=169-170, WR_shrunk 68.95-69.31%, PF 3.291, holdout_pass true + bonferroni true across cells. Stats are credible for crypto volatility; no obvious single-symbol or leakage flags in the reported cells.
- 90d expected P&L (1% risk, $100k): ~$8,400. Assumes ~55-60 additional qualifying trades at the edge parameters, 1% risk ($1k) per trade, 0.15% slippage/commissions, using the reported 1.34% avg_pnl_pct.
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` = 50
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Noise / leakage. n=67 with 66 wins, WR_shrunk 87%, PF 216.95 is statistically impossible without data error, single-symbol concentration, or look-ahead. Flag as recurrence risk.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected).
- Gate change: `EQUITY_MIN_TRUST` = 70
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise. No proven cells; all best_pf_overall fail holdout_pass and bonferroni. Small effective n after filters.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `HC_FILTER_MIN_CONF` = 0.85
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf_overall fails holdout and bonferroni. n=23 too small and unstable.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `SMART_PICKS_MIN_RR_COMMODITY` = 2.5
- Confidence (1-5): 5

**### BOND / ETF / FUTURES / INDEX / UNKNOWN / MEME**
- Real/noise verdict: Noise. All have n_closed ≤31, zero proven cells, and best_pf_overall either absent or fail statistical gates.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `HC_FILTER_MIN_SCORE` = 65
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up **CRYPTO** today (only class with statistically validated, holdout-passing edges). Demote **EQUITY** per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion S40 path immediately; the PF=216 result is a clear leakage candidate). All other classes have no actionable edge—do not allocate.
