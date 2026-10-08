# Pick Funnel Swarm Verdict — 2026-10-08 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261008T041137Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three structural facts dominate everything below and I want them stated up front because they invalidate most of the "PROVEN" cells:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) has never fired in 90 days. That means the "top edges" you're being shown are *not* HC-filtered — they're raw Smart_Picks survivors. Any claim that these are "high conviction" is false by construction.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1854) and FOREX (3) and FUTURES (1) and MEME (1) have any VA passes. The "PROVEN" label on EQUITY/COMMODITY cells is coming from a different pipeline than the one the dashboard advertises.
3. **The EQUITY "PROVEN" cell is almost certainly a data bug, not an edge.** 98.48% WR with PF=213 on `mean_reversion & score_dec=S40 & conf<0.60` is not a strategy — it's a P&L accounting artifact (likely: wins booked at target, losses not yet marked, or a single-symbol mean-reversion that never stopped out). I'll treat it as leakage until proven otherwise.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** n_closed=79 across the whole class over 90 days is far too thin to call anything. The "best PF" cell (`rr>=2.0 & LONG & alpha_engine`, n=21, PF=9.49) fails Bonferroni (`bonferroni_pass: false`) and its train_pf=5.32 vs holdout_pf=49.6 is a classic small-sample blowup — a single lucky holdout trade dominates. Also note the H-001 precedent: COMMODITY edges in this codebase have a documented history of look-ahead leakage (COT timestamps). Any COMMODITY "edge" should be treated as guilty until proven innocent. The 54.4% class WR is indistinguishable from a coin flip at n=79.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not size this. If forced to trade the n=21 cell at 1% risk with 2:1 R:R and 81% WR, expected ≈ +$1,700, but the confidence interval spans negative and the Bonferroni failure means it's not distinguishable from noise. **Recommendation: $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise it hard. Current floor is letting 3403/5856 (58%) through. Set to **85** and require `rr>=2.0` as a hard precondition, not a soft score input. This kills the n=21 cell's siblings that are dragging the class WR down.
- **Confidence (1-5):** **1**

---

### EQUITY
- **Real/noise verdict:** **LEAKAGE / BUG — not an edge.** The `mean_reversion & score_dec=S40 & conf<0.60` cell at 98.48% WR / PF=213 is not physically plausible for a mean-reversion strategy on equities. Three red flags: (i) `conf<0.60` is *below* the Smart floor, so these trades shouldn't exist in the funnel at all — they're leaking in from somewhere; (ii) PF=213 implies average win / average loss ≈ 200:1, which only happens if losses are being truncated to zero (unclosed positions, or stop-loss not being applied); (iii) `trust=UNK` on 100% of the cell means the trust dimension is unpopulated, so the "trust" axis of the three-axis protocol is dead for EQUITY. The class-level 68.4% WR on n=152 is more believable but still thin. **Do not trade this.**
- **90d expected P&L (1% risk, $100k):** **$0.** If the 68.4% class WR were real and you traded all 152 closed at 1% risk with 1:1 R:R, expected ≈ +$5,500. But the class WR is being propped up by the buggy cell. Ex-bug, the residual n=86 likely sits near 50%. **Recommendation: $0 until the P&L accounting is fixed.**
- **Gate change:** `hc_filter.js` — the HC gate is `score>=80, conf>=0.75, trust>=60`. The EQUITY leak is coming in at `conf<0.60`. Add a **hard reject** in `hc_filter.js`: `if (conf < 0.60) return false;` before any scoring. This is a one-line fix that closes the leak. Separately, `SMART_PICKS_MIN_SCORE_EQUITY` should go from current floor to **75** (currently only 248/5681 = 4.4% pass, which is actually reasonable — the problem is the leak, not the floor).
- **Confidence (1-5):** **1** (on the edge), **4** (on the leak diagnosis)

---

### INDEX
- **Real/noise verdict:** **NOISE.** n_closed=5. WR=20%. This is not a class, it's a rounding error. 1523/1827 passed Smart (83%!) which means the Smart floor for INDEX is effectively zero — it's not filtering anything. The 8 closed trades with 1 win / 4 losses / 3 unresolved is statistically meaningless.
- **90d expected P&L (1% risk, $100k):** **$0.** n=5 is below any minimum sample threshold. Trading this is gambling.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise from current (effectively 0) to **80**. If the class can't produce 20 closed trades in 90 days at that floor, **disable INDEX entirely** in `production_scanner.py` and route the scan budget to CRYPTO. A class with 83% pass-through and 5 closed trades is a scanner bug, not a strategy.
- **Confidence (1-5):** **1**

---

### FOREX
- **Real/noise verdict:** **NOISE, with a specific leakage flag.** The `conf>=0.90 & fam=regime & source=regime_terminal` cell (n=54, WR=68.5%, PF=3.20) has `train_pf=0.298` vs `holdout_pf=14.149` and `holdout_pass: false`. That train/holdout inversion is the signature of **regime-terminal look-ahead** — the "regime" label is being assigned using information that wasn't available at entry. This is the same failure mode as H-001 (COT) and H-035 (funding settlement): a "regime" or "terminal" tag that encodes future state. **Flag as potential leakage recurrence.** Class-level WR=42.1% on n=530 is the honest number, and it's a losing strategy before costs.
- **90d expected P&L (1% risk, $100k):** **Negative.** At 42.1% WR with typical 1:1 R:R, 530 trades × 1% risk × (0.421 − 0.579) ≈ **−$8,400** before slippage. FOREX slippage on retail is 0.5–1.5 pips; at 1% risk per trade that's another −2 to −4% of notional per round trip. **Realistic: −$15,000 to −$25,000.** This class is a money incinerator.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — currently 22462/23380 = **96% pass-through**. The Smart floor is doing nothing. Raise to **85** AND add a hard `source != 'regime_terminal'` reject in `production_scanner.py` until the train/holdout inversion is explained. If the class still can't clear 50% WR at that floor, **demote per MUTATION_THREE_AXIS_PROTOCOL** — mutate the regime axis first (replace `regime_terminal` with a lagged regime label), then kill if it doesn't recover.
- **Confidence (1-5):** **1** (on edge), **4** (on leakage diagnosis)

---

### CRYPTO
- **Real/noise verdict:** **THE ONLY CELL THAT SURVIVES SCRUTINY — with caveats.** The `conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine` cell: n=169, WR=71.6%, WR_shrunk=69.3%, PF=3.29, train_pf=3.59 (n=133), holdout_pf=2.42 (n=36), `holdout_pass: true`, `wr_z=5.62`, `bonferroni_pass: true`. This is the only cell in the entire report that passes Bonferroni *and* has a holdout that doesn't invert. The train/holdout PF ratio (3.59 → 2.42) is a normal degradation, not a blowup. **This is a real edge.** Caveats: (i) it's LONG-only, so it's a beta-timing edge, not market-neutral — in a 90-day crypto drawdown it would have lost; (ii) `trust=UNK` on the sibling cell means the trust axis is unpopulated, so you can't cross-validate; (iii) n=169 is adequate but not large — expect the true WR to be 60–65%, not 71%. The class-level 45.4% WR on n=2408 is dragged down by the non-alpha_engine sources; the alpha_engine subset is the edge.
- **90d expected P&L (1% risk, $100k):** Using the cell's own stats: n=169 trades, avg_pnl_pct=1.35%, at 1% risk per trade on $100k = $1,000 risk per trade. Expected P&L per trade = 1.35% × (position size). If sizing is 1% risk with a 2:1 R:R structure, position notional ≈ $2,000–$3,000 per trade. Expected gross ≈ 169 × $1,000 × (0.716 × 2 − 0.284 × 1) / 1 ≈ **+$19,400** before costs. Crypto slippage + funding on 169 round trips ≈ 0.15–0.30% per trade ≈ **−$5,000 to −$10,000**. **Net realistic: +$10,000 to +$14,000.** If you size at 0.5% risk (more prudent given the LONG-only beta exposure), halve it: **+$5,000 to +$7,000.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — the class has 3451/12904 = 26.7% pass-through, which is the most reasonable of any class. But the edge lives specifically in `source=alpha_engine & conf=0.75-0.80 & dir=LONG`. Add a **boost**, not a floor: in `production_scanner.py`, if `source=='alpha_engine' and 0.75<=conf<0.80 and direction=='LONG'`, add +10 to the Smart score. This routes the edge to the top of the funnel without raising the floor and killing the rest of the class. Do **not** raise the floor — you'd lose the edge's siblings.
- **Confidence (1-5):** **4**

---

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=9, WR=22.2%. Not a class.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **85**. If it can't produce 20 closed trades, disable ETF in `production_scanner.py`. 297/346 = 86% pass-through is a scanner bug.
- **Confidence (1-5):** **1**

---

### FUTURES
- **Real/noise verdict:** **NOISE, and already falsified.** H-005 (`futures_momentum_anti_signal_investigation`) is in the rejected list — inversion does not fix it. n_closed=16, WR=31.25%. The 125/181 = 69% Smart pass-through is not filtering. Do not re-derive a futures edge; the registry says it's been tried.
- **90d expected P&L (1% risk, $100k):** **Negative.** 16 trades × 1% × (0.3125 − 0.6875) ≈ **−$600** before costs. Not worth the operational overhead.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **85**, and per H-005, **do not attempt momentum inversion**. If the class can't clear 50% WR at 85, disable it.
- **Confidence (1-5):** **1**

---

### UNKNOWN
- **Real/noise verdict:** **NOISE — and a data hygiene problem.** 1367 scanned, 1362 opened, 0 wins, 5 losses. The fact that 1362 trades opened but only 5 closed means the class is a dumping ground for unclassified instruments that never resolve. This is a **scanner classification bug**, not a strategy. The 0% WR is an artifact of unresolved positions.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not trade unclassified instruments.
- **Gate change:** In `production_scanner.py`, add a hard reject: `if asset_class == 'UNKNOWN': skip`. Route the 1367 scans to a classification pass first. This is a hygiene fix, not a gate tuning.
- **Confidence (1-5):** **5** (that it's a bug)

---

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=31, WR=45.2%. 3/558 = 0.5% Smart pass-through — the floor is actually working here, but the class has no edge. 527 opened / 31 closed is a 94% unresolved rate, which suggests the bond scanner is opening positions it can't close (illiquid instruments, or a close-condition bug).
- **90d expected P&L (1% risk, $100k):** **Negative.** 31 trades × 1% × (0.452 − 0.548) ≈ **−$300** before costs. Not worth it.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — leave at current (it's already restrictive). Instead, fix the **close-condition bug** in `production_scanner.py` for BOND: 94% unresolved is the real problem. If unresolved positions are being marked as wins in the P&L, that's another leakage source.
- **Confidence (1-5):** **2**

---

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=4. Not a class.
- **90d expected P&L (1% risk, $100k):** **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **90** or disable. 11/24 = 46% pass-through on a 24-scan class is meaningless.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only, and only the `alpha_engine & conf=0.75-0.80 & LONG` cell.** It's the only cell in the report that passes Bonferroni, has a non-inverting holdout, and has n>100. Size at **0.5% risk per trade** (not 1%) because the edge is LONG-only and therefore beta-exposed — a 90-day crypto drawdown would hurt. Expected 90d P&L: **+$5,000 to +$7,000 net of slippage.** Do not scale the rest of the CRYPTO class; the 45.4% class WR is the honest number for non-alpha_engine sources.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

- **FOREX** — mutate the **regime axis** first. The `regime_terminal` source has a train/holdout inversion (0.298 → 14.149) that is the signature of look-ahead. Replace `regime_terminal` with a lagged regime label (regime computed at t−1, applied at t) and re-run. If WR doesn't clear 50% at `SMART_PICKS_MIN_SCORE_FOREX=85`, kill the class. Do not skip the mutation step — the protocol requires it.
- **EQUITY** — mutate the **confidence axis** first. The leak is at `conf<0.60`. Add the hard reject in `hc_filter.js`, re-run, and see if the residual class WR holds above 55%. If it drops to ~50%, the "edge" was entirely the leak. Kill if so.
- **COMMODITY** — mutate the **R:R axis** first. The n=21 cell at `rr>=2.0` is the only thing with a pulse, but it fails Bonferroni. Tighten to `rr>=2.5` and require `n>=30` before re-evaluating. Given H-001's history, assume leakage until proven otherwise.
- **INDEX, ETF, FUTURES, BOND, MEME, UNKNOWN** — these are not classes, they're scanner bugs. Fix the pass-through rates (83%,

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real edge. n=169-170, WR_shrunk 68.95-69.31, PF 3.291, holdout_pass true + bonferroni_pass true across multiple overlapping cells; stats stable and not extreme enough to scream leakage.
- 90d expected P&L (1% risk, $100k): $4,850 (170 trades × $1k risk × 1.34% avg net after 0.15% slippage/commissions, rounded).
- Gate change: `hc_filter.js` MIN_SCORE = 50 (from implied 80)
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Sample-noise / probable leakage. n=66, WR_shrunk 87.21, PF 213.5 is absurdly high for mean_reversion; almost certainly single-symbol concentration or label leakage.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected; do not trade).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_EQUITY = 70
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise. No proven cells; best_pf cells fail bonferroni and have tiny n=21 with extreme holdout variance.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_TRUST = 40
- Confidence (1-5): 4

### FOREX
- Real/noise verdict: Noise. No proven cells; best_pf cells fail holdout and bonferroni; regime cells show classic small-n instability.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: `hc_filter.js` MIN_CONF = 0.85
- Confidence (1-5): 4

### INDEX
- Real/noise verdict: Noise (n_closed=5 total; no cells meet n>=20).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_INDEX = 65
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n_closed=9; no qualifying cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_ETF = 60
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n_closed=16; no qualifying cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_FUTURES = 55
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n_closed=31; no qualifying cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_BOND = 50
- Confidence (1-5): 5

### UNKNOWN / MEME
- Real/noise verdict: Noise (n_closed <=5; no qualifying cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_UNKNOWN = 999 (effectively disable)
- Confidence (1-5): 5

### SYSTEM-WIDE CONCLUSION
Scale CRYPTO today (only class with multiple bonferroni-passed, holdout-validated cells). Demote EQUITY, INDEX, ETF, FUTURES, BOND, UNKNOWN, and MEME per MUTATION_THREE_AXIS_PROTOCOL.md (they contribute volume but zero proven edge; mutate scoring or kill flow).
