# Pick Funnel Swarm Verdict — 2026-09-11 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260911T041059Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Read this first:** The funnel data and the "PROVEN" edge cells tell two different stories, and the gap between them is the actual finding. The funnel shows **zero** picks passing `passed_high_conviction` across all 10 classes over 90 days. The edge-cell report shows "PROVEN" cells with PF of 4.0, 206, and 5.6. Those cannot both be true of the same pipeline. One of them is measuring something the other isn't — and the most likely explanation is that the edge-cell report is computed on a **different population** than the funnel (e.g., all closed trades, not just HC-passed ones), and several of the "PROVEN" cells are almost certainly leakage or single-symbol artifacts.

I'll go class by class, then give the system verdict.

---

### CRYPTO
- **Real/noise verdict:** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell (n=213, WR_shrunk=74.25%, PF=4.03, holdout PF=5.70) is **too clean to trust as-is**. Three red flags: (1) `trust=UNK` is the dominant trust band in the cell — meaning the trust gate is not actually filtering these; (2) the cell is essentially "alpha_engine picks with confidence in a narrow 5-point band" — that's a **source+confidence slice**, not an edge; (3) PF 4.0 with 76% WR on crypto longs over 90d is the signature of a **bull-market beta artifact**, not alpha. The holdout PF *rising* to 5.70 (vs train 3.28) is the opposite of what you'd expect from a real edge — real edges decay out-of-sample. This looks like the holdout window happened to be a strong up-move. **Verdict: likely regime artifact, not proven edge.** Do not scale on this.
- **90d expected P&L (1% risk, $100k):** If you had taken all 213 signals at 1% risk ($1,000/trade) with avg_pnl 1.44% on notional → ~$14.4/trade × 213 ≈ **$3,070 gross**, minus ~0.15% round-trip slippage+fees on $100k notional ($150/trade × 213 = $31,950) → **net negative**. The avg_pnl_pct is on *position* notional, and 1.44% avg on a 1% risk unit is a ~1.4R average — plausible only if the win rate is real. Given the regime-artifact concern, I'd haircut to **$0 to +$1,500** realistic.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise from current (likely 50) to **65**, AND add a hard `trust != UNK` requirement in `hc_filter.js` before the score>=80 check. The CRYPTO edge cell is entirely `trust=UNK`, which means the trust gate is doing nothing for crypto.
- **Confidence (1-5):** 2

---

### FOREX
- **Real/noise verdict:** The `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell (n=137, WR_shrunk=64.33%, PF=2.77, holdout PF=1.65) is the **most credible** of the "PROVEN" cells — holdout PF *decayed* from 3.19 to 1.65, which is what a real edge looks like. But two problems: (1) `trust=UNK` again dominates — the trust gate is not filtering; (2) FOREX mean-reversion at RR 1.0-1.5 is a **well-known crowded trade** and the 90d window may have been range-bound. The `dir=LONG` sub-cell (n=46, PF=4.61) has `bonferroni_pass: false` — **do not cite it as proven**. The parent cell is the only one worth considering.
- **90d expected P&L (1% risk, $100k):** 137 trades × avg_pnl 0.277% on $100k notional = $277/trade × 137 ≈ **$37,900 gross**. Slippage on FX is ~0.5-1 pip round-trip; at 1% risk ($1k) with typical 20-30 pip stops, that's ~$30-50/trade → ~$5,500 total. **Net ≈ $32,000.** But this assumes the 0.277% avg holds — with holdout PF at 1.65, realistic net is **$15,000-$25,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — the FOREX funnel shows 22,558/23,551 passed_smart (95.8%!). That gate is not a gate. Raise to **70** and require `fam=mean_reversion` OR `rr>=1.0` as a hard precondition. Also: `hc_filter.js` trust>=60 is being bypassed by `trust=UNK` — add explicit `trust !== 'UNK'` rejection.
- **Confidence (1-5):** 3

---

### EQUITY
- **Real/noise verdict:** **This is the smoking gun.** `fam=mean_reversion & score_dec=S40` with n=65, WR=98.46%, PF=**206.35**, holdout PF=**119.15**. A PF of 206 is not an edge — it is a **data integrity failure**. Possible causes: (a) look-ahead in the mean-reversion signal (entering at the close of the signal bar), (b) survivorship/delisting bias, (c) a single symbol dominating (65 trades, 64 wins — check if it's one ticker), (d) PnL calculation using mid instead of fill, (e) the "loss" is a near-zero scratch being counted as a win. **Do not trade this. Do not cite this. Investigate the harness.** This is exactly the pattern the H-001 COT leakage showed before it was fixed.
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** If the PF were real (it isn't), 65 × 1.26% × $100k = $81,900 gross. That number is the tell: it's absurd.
- **Gate change:** **None — this is a bug, not a gate problem.** The correct action is to add a **sanity assertion in `quality_gates.py`**: reject any cell where `pf > 20` or `wr_shrunk > 90%` with `n < 100` as `SUSPECT_LEAKAGE` and exclude from the edge report. The gate change is to the *reporting* layer, not the pick layer.
- **Confidence (1-5):** 1 (confidence that it's real); 5 (confidence it's leakage)

---

### COMMODITY
- **Real/noise verdict:** No PROVEN cells. Best PF overall is `rr=RR>=2.0 & score_dec=S50` (n=21, WR_shrunk=63.41%, PF=5.62, `bonferroni_pass: false`). n=21 is below the n>=20 threshold's spirit and Bonferroni fails. **Not proven.** The funnel WR of 44.7% (n=132 decisive) is the honest number — **no edge**. Note H-001 (COT leakage) and H-036 (inventory direction) are both already killed for this class; do not re-derive.
- **90d expected P&L (1% risk, $100k):** At 44.7% WR with unknown avg R, likely **-$2,000 to -$5,000** net of costs. Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — the funnel shows 4,059/6,452 passed_smart (62.9%). That's too loose. Raise to **70** and require `rr>=2.0` as a hard precondition (the only sub-cell with any signal).
- **Confidence (1-5):** 2

---

### BOND
- **Real/noise verdict:** n=20 closed, WR=20%, no PROVEN cells, no best-PF cells. **No edge. Full stop.** 383 scanned → 16 passed_smart → 0 HC → 363 opened. The funnel is inverted: almost everything that passes smart gets opened, and almost nothing wins.
- **90d expected P&L (1% risk, $100k):** **Negative.** 20 trades at 20% WR with unknown R → likely **-$3,000 to -$6,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **80** (effectively disable until a real edge is found). Or set `SMART_PICKS_ENABLE_BOND = False`.
- **Confidence (1-5):** 1

---

### INDEX
- **Real/noise verdict:** n=4 decisive, WR=0%. 1,411/1,566 passed_smart (90.1%). **No edge, no sample.** The smart gate is a rubber stamp.
- **90d expected P&L (1% risk, $100k):** **-$1,000 to -$2,000** (tiny sample, all losses).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **80** or disable. 90% pass rate is not a gate.
- **Confidence (1-5):** 1

---

### ETF
- **Real/noise verdict:** n=7 decisive, WR=14.3%. 290/329 passed_smart (88.1%). **No edge, no sample.**
- **90d expected P&L (1% risk, $100k):** **-$1,500 to -$3,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **80** or disable.
- **Confidence (1-5):** 1

---

### FUTURES
- **Real/noise verdict:** n=18 decisive, WR=38.9%. No PROVEN cells. H-005 already killed the momentum inversion hypothesis. **No edge.**
- **90d expected P&L (1% risk, $100k):** **-$2,000 to -$4,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **75**.
- **Confidence (1-5):** 1

---

### UNKNOWN
- **Real/noise verdict:** n=9 decisive, WR=0%. 189/1,444 passed_smart (13.1% — actually the tightest gate in the system, ironically). **No edge, and the class itself is a data-quality failure** — 1,444 picks with no asset class is a routing bug.
- **90d expected P&L (1% risk, $100k):** **-$1,000 to -$2,000**.
- **Gate change:** **Fix the classifier, not the gate.** Add a hard reject in `production_scanner.py` for `asset_class == UNKNOWN` before scoring.
- **Confidence (1-5):** 1

---

### MEME
- **Real/noise verdict:** n=4 decisive, WR=25%. **No edge, no sample.** Do not trade.
- **90d expected P&L (1% risk, $100k):** **-$500 to -$1,000**.
- **Gate change:** Disable. `SMART_PICKS_ENABLE_MEME = False`.
- **Confidence (1-5):** 1

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money:** **FOREX**, and only FOREX, and only the `conf=C0.75-0.80 & rr=RR1.0-1.5 & fam=mean_reversion` cell. It is the only cell in the entire report where the holdout PF *decayed* (3.19 → 1.65) rather than *inflated* — that's the signature of a real, decaying edge rather than a regime artifact. Size it at **0.5% risk per trade** (not 1%) for the first 30 days, cap at 20 concurrent positions, and require `trust != UNK`. Expected 90d P&L at 0.5% risk: **~$8,000-$12,000**. If holdout PF holds above 1.3 after 30 days, scale to 1%.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **EQUITY** — but not via mutation. This is a **harness integrity failure**, not a strategy failure. The PF=206 cell must be quarantined and the PnL calculation audited before any mutation. Mutating a strategy on top of a broken harness will produce false positives. **Freeze EQUITY picks, audit the harness, then decide.**
2. **COMMODITY** — mutate the `rr>=2.0` axis (the only sub-cell with signal, n=21, PF=5.62 but Bonferroni-failed). Try `rr>=2.5` and `score_dec=S60`. If n drops below 15, kill.
3. **CRYPTO** — mutate the `trust` axis. The entire edge cell is `trust=UNK`, which means the trust gate is dead for crypto. Either fix the trust classifier or add `source=alpha_engine & conf>=0.75` as a hard precondition. Do not scale the current cell — it's a bull-market artifact.
4. **BOND, INDEX, ETF, FUTURES, MEME, UNKNOWN** — **kill the smart gate** (raise to 80+ or disable). These classes have no edge and their smart gates are passing 60-90% of scans, which is not a gate. Per the protocol, mutate once (tighten to 80) before full kill; if 90d forward WR stays below 50%, kill.

**The single most important finding:** `passed_high_conviction = 0` across all 10 classes over 90 days, while the edge report shows "PROVEN" cells with n=213. **These two facts are incompatible.** Either (a) the HC gate is broken and never fires, or (b) the edge report is computed on a population that never reaches HC. Either way, the HC gate is currently doing nothing, and the "PROVEN" edges are being measured on picks that the live system would never have surfaced. **Fix the HC gate before trusting any edge cell.** The `hc_filter.js` thresholds (score>=80, conf>=0.75, trust>=60) are almost certainly unreachable given the score distributions — check the actual score histogram; if p99 score is 72, the gate is dead code.

**Do not deploy real money on CRYPTO or EQUITY this quarter.** FOREX only, small size, 30-day probation.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### BOND
- Real/noise verdict: noise — n=20 closed, zero proven cells, WR 20%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise — n=4 closed, zero proven cells, WR 0%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: noise — zero proven cells; best_pf cells fail Bonferroni and n too low for stability.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise — top cells show moderate PF but holdout degradation and bonferroni failures; no stable proven edge after known leakage patterns.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge exists)
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: noise — PF 4.0+ on conf=0.75-0.80 & S50 cells is suspiciously high; likely single-symbol concentration or alpha_engine leakage given holdout inflation.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge exists)
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: noise — PF 206 on mean_reversion S40 is statistically impossible without leakage or single-name concentration; matches pattern of previously killed equity hypotheses.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise — n=7 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — n=18 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — n=9 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n=4 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: none (no edge exists)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none.  
Demote per MUTATION_THREE_AXIS_PROTOCOL: EQUITY and CRYPTO (both show clear signs of leakage or concentration; mutate the alpha_engine scoring path and SMART_PICKS_MIN_SCORE thresholds before any further allocation). All other classes already have no usable edge.
