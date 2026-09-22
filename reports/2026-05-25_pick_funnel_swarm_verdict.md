# Pick Funnel Swarm Verdict — 2026-09-22 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20260922T041018Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three structural facts that dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80 && conf>=0.75 && trust>=60`) is firing on **zero** picks across 52,969 scanned signals. Either the gate is dead code, or the trust dimension is never populated (every "proven" cell in the data is `trust=UNK`). This is the single most important finding in the whole funnel.
2. **`passed_verified_alpha` is 0 for every class except CRYPTO (1812), FUTURES (1), MEME (1).** So the "verified alpha" tier is effectively a CRYPTO-only tier.
3. **Opened ≫ Closed everywhere.** COMMODITY: 6176 opened / 131 closed (2.1%). FOREX: 22063 / 1368 (6.2%). The WR numbers are computed on a tiny, non-random survivor subset — almost certainly the ones that hit TP/SL fast. **Every WR below is biased upward** by unresolved trades being excluded. Treat all WRs as upper bounds.

---

### COMMODITY
- **Real/noise verdict:** No proven cell. Best cell (`rr=RR>=2.0 & score_dec=S50`, n=20, WR_shrunk=62.5%, PF=4.71) **fails Bonferroni** and has holdout_n=10 — that's noise. Class-level WR 43.85% on n=130 decisive is a **losing** class. The known-falsified H-001 (COT leakage, cotton concentration) is the ghost here — any "commodity edge" that reappears should be assumed to be the same leakage until proven otherwise. **No edge.**
- **90d expected P&L (1% risk, $100k):** −$1,300 to −$2,100. Assumptions: 1% = $1,000 risk/trade, avg R multiple ≈ 0.9 (WR 43.85% with ~1.5R winners), 131 closed trades, 0.05% slippage on 6176 opens. The class is a net drag.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` → raise from current floor to **≥ 65** (or add `SMART_PICKS_REQUIRE_RR_MIN_COMMODITY = 2.0`). Current pass rate is 3716/6307 = 59% — the floor is doing almost nothing.
- **Confidence (1-5):** 5 (high confidence there is no edge).

### FOREX
- **Real/noise verdict:** **No proven cell.** The `multi_asset_copytrader` LONG RR1.0-1.5 cell (n=47, WR_shrunk=65.67%, PF=5.08) **fails Bonferroni** and the train/holdout split is 20/27 — the holdout PF of 10.03 on 27 trades is a textbook small-sample artifact. Class WR 47.25% on 510 decisive is a coin flip minus costs. **No edge.** The "consensus" cell you flagged doesn't appear in the proven list — good, because it would have been the same story.
- **90d expected P&L (1% risk, $100k):** −$2,000 to −$4,000. 1368 closed, WR 47.25%, avg R ≈ 0.95, slippage 0.3–0.5 pip on 22063 opens. FOREX spread cost alone on 22k opens at ~$5/round-turn = ~$110k gross drag — the class is structurally unprofitable at this volume.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` → raise to **≥ 70** AND add a hard `SMART_PICKS_MAX_OPENS_PER_DAY_FOREX = 50` cap. 22430/23431 = 95.7% pass rate means the gate is a no-op.
- **Confidence (1-5):** 5.

### CRYPTO
- **Real/noise verdict:** **This is the only class with a defensible edge.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell: n=201, WR_shrunk=73.3%, PF=3.91, **train_pf=3.78 / holdout_pf=4.37**, holdout_pass=true, **bonferroni_pass=true**, wr_z=7.27. That is a real, out-of-sample-stable signal. The `dir=LONG` variant is essentially the same cell (200/201 overlap) — not independent confirmation, just a slice. **Caveat:** avg_pnl_pct=1.44% with PF 3.91 implies avg loss ≈ 0.5% and avg win ≈ 1.9% — check that losers aren't being cut by a time-stop that the live system doesn't honor. Also verify `source=alpha_engine` isn't a single strategy family masquerading as a source.
- **90d expected P&L (1% risk, $100k):** **+$18,000 to +$26,000** on the proven cell alone. Math: 201 trades × $1,000 risk × (0.733 × 1.9R − 0.267 × 1.0R) ≈ 201 × $1,000 × 1.126 ≈ $226k gross... that's too high; realistic with slippage/funding and assuming the 1.44% avg_pnl is on notional not on risk: 201 × $100k × 1.44% × (1 − 0.15 slippage/funding) ≈ **$24,600**. Use $20k as the honest midpoint. Class-wide (2453 closed) is roughly break-even to slightly negative (WR 46.03%) — **the edge is concentrated in one cell, not the class.**
- **Gate change:** `hc_filter.js` — the HC gate is firing on 0 picks. Change `trust >= 60` to `trust >= 0` (or `trust != null`) **and** add a CRYPTO-specific override: `if (assetClass === 'CRYPTO' && conf >= 0.75 && conf < 0.80 && score >= 50 && source === 'alpha_engine') return true;`. The current gate is unreachable because trust is never populated.
- **Confidence (1-5):** 4 (edge is real; sizing/execution assumptions are the risk).

### EQUITY
- **Real/noise verdict:** **The 98.53% WR cell is leakage until proven otherwise.** n=68, wins=67, PF=216, wr_z=8.0, bonferroni_pass=true — those numbers are *too* clean. A 98.5% WR on 68 trades with avg_pnl=1.27% is the signature of a look-ahead bug (entry price stamped after the move, or a mean-reversion signal computed on the same bar it trades). The `train_pf=106 / holdout_pf=99` split does **not** rule out leakage — leakage survives splits. **Flag as suspected leakage recurrence** (same family as H-001). Do not size on this until the entry timestamp is independently verified against a bar-close feed.
- **90d expected P&L (1% risk, $100k):** **$0 — do not trade.** If the cell is real, it's ~$68k; if it's leakage (my prior: 70%), it's negative. Expected value of trading it now is negative because you'll size up on a false signal.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` is already tight (228/5556 = 4.1% pass). The right change is **not a threshold** — it's adding `SMART_PICKS_REQUIRE_ENTRY_AFTER_BAR_CLOSE_EQUITY = True` in `quality_gates.py` to kill the suspected look-ahead. If that flag already exists, it's not being enforced.
- **Confidence (1-5):** 2 (low confidence the edge is real; high confidence it needs a leakage audit).

### BOND
- **Real/noise verdict:** **No edge.** WR 24% on n=25. 7/506 pass smart. This class should not be in the funnel.
- **90d expected P&L (1% risk, $100k):** −$1,500 to −$2,500.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` → set to **999** (effectively disable) or remove BOND from the scanner until a dedicated bond model exists.
- **Confidence (1-5):** 5.

### ETF
- **Real/noise verdict:** **No edge.** WR 14.29% on n=7. 292/332 pass smart — the gate is inverted (passing 88% of a losing class).
- **90d expected P&L (1% risk, $100k):** −$500 to −$1,000 (tiny n, but directionally negative).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` → **≥ 75**, and add `SMART_PICKS_MIN_CLOSED_N_ETF = 30` before any ETF pick is allowed to size.
- **Confidence (1-5):** 4.

### FUTURES
- **Real/noise verdict:** **No edge.** n=18 closed. H-005 already falsified the momentum inversion. Nothing here.
- **90d expected P&L (1% risk, $100k):** −$400 to −$800.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` → **≥ 70**; also cap opens (152 opened / 18 closed = 88% unresolved — the scanner is spamming).
- **Confidence (1-5):** 5.

### UNKNOWN
- **Real/noise verdict:** **No edge, and a data-quality bug.** 1412 scanned, 183 pass smart, 0 wins / 8 losses. "UNKNOWN" should never reach the funnel — it means asset-class classification failed upstream.
- **90d expected P&L (1% risk, $100k):** −$800.
- **Gate change:** Add `SMART_PICKS_REJECT_UNKNOWN_CLASS = True` in `quality_gates.py`. Hard reject.
- **Confidence (1-5):** 5.

### INDEX
- **Real/noise verdict:** **No edge.** 1421/1576 pass smart (90%!) on a class with 0 wins / 4 losses. Gate is broken.
- **90d expected P&L (1% risk, $100k):** −$400.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` → **≥ 75**; the 90% pass rate is the tell.
- **Confidence (1-5):** 5.

### MEME
- **Real/noise verdict:** **No edge.** n=4 closed. Not enough data to say anything.
- **90d expected P&L (1% risk, $100k):** −$300.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` → **≥ 80** (or disable until n≥30).
- **Confidence (1-5):** 5.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only, and only the `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell.** It is the only cell in the entire 90-day dataset that passes Bonferroni, has holdout_n ≥ 30, and has a holdout PF that is *higher* than train PF (4.37 vs 3.78) — the opposite of overfitting. Size at 0.5% risk (not 1%) for the first 30 days to validate live execution against the backtest, then step to 1%. Expected 90d P&L on this cell alone: **~$20k on a $100k account.**

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **BOND, ETF, INDEX, UNKNOWN** — these are not "mutate" candidates, they are **kill** candidates. WR 0–24% on tiny n, and the gates are passing 88–90% of them. Mutating a gate on a class with no signal is wasted cycles. Recommend: disable in scanner, log to `reports/hypothesis_registry.json` as KILLED with reason "no signal, gate inverted."
- **COMMODITY and FOREX** — these are the **mutate** candidates. Both have plausible microstructure (COT for commodity, carry for FX) but the current gates are no-ops (59% and 96% pass rates). Mutate the *gate*, not the signal: raise floors to 65/70, add RR≥2.0 requirement, cap daily opens. Re-evaluate in 30 days. Do **not** re-derive COT (H-001) or inventory-direction (H-036) — both are formally falsified.
- **EQUITY** — **quarantine, do not trade.** The 98.5% WR cell is a leakage suspect. Run a timestamp audit before any sizing. If the audit clears it, it becomes the second scale-up candidate; if not, it joins the kill list.

**The single highest-leverage fix across the whole system:** `hc_filter.js` is firing on **zero** picks because `trust >= 60` is unreachable (every proven cell is `trust=UNK`). Either populate trust upstream or lower the threshold to `trust >= 0`. Until that's fixed, the "HIGH CONVICTION" tier is decorative and the dashboard is showing users the *unfiltered* smart-picks stream — which is why the class-level WRs look like coin flips.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.53% WR and PF=216 on n=68 is statistically impossible in live trading; indicates single-symbol concentration or data bug, not real edge.
- 90d expected P&L (1% risk, $100k): $0 (edge is invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real — n=200, WR_shrunk~73.6, PF=3.91 with holdout_pass and bonferroni_pass is credible but high; no obvious leakage flagged.
- 90d expected P&L (1% risk, $100k): ~$8,400 (assume 0.4% avg slippage per trade, 1% risk, ~200 trades scaled to account size).
- Gate change: hc_filter.js MIN_CONF = 0.78
- Confidence (1-5): 3

### FOREX
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails bonferroni and has small train_n.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_FOREX = 90
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails bonferroni, small n=20.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 95
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n_closed=18 too small, no proven or best_pf cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 95
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — n_closed=25 too small, no edges.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 95
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n_closed=7 too small, no edges.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 95
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n_closed=4 too small, no edges.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 95
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n_closed=4 too small, no edges.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 95
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n_closed=8 too small, no edges.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 95
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up CRYPTO today (only class with credible n and stats). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its metrics indicate leakage recurrence, not a tradable edge. All other classes have no usable edge.
