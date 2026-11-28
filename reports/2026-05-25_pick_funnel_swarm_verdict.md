# Pick Funnel Swarm Verdict — 2026-11-28 04:41 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261128T044117Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before per-class verdicts, three cross-cutting observations that shape every number below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is *never* firing. Either the score distribution never reaches 80, or trust never reaches 60, or the gate is dead code. This is the single biggest finding in the funnel — the "HIGH CONVICTION" tier is a null set. Every "edge" below is therefore a *Smart Picks* edge, not an HC edge.
2. **`opened` >> `passed_smart` in most classes** (EQUITY 5973 opened vs 223 smart; FOREX 25584 vs 26417 — wait, FOREX opened < smart, which means the funnel is *inverted* there). The funnel is not actually gating opens on Smart Picks. The "passed_smart" count is decorative.
3. **`passed_verified_alpha` is 0 for 8 of 11 classes.** Only CRYPTO (4131), FOREX (9), FUTURES (1), MEMECOIN (2) have any. The verified-alpha tier is essentially CRYPTO-only.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell is `trust=UNK & rr=RR1.5-2.0 & fam=mean_reversion` with n=34, WR=97.06%, PF=113.5. A PF of 113 on 34 trades is not a strategy — it is a data artifact. Three red flags: (i) `trust=UNK` means the trust field is *missing*, so the cell is defined by absence of a filter, not presence of one; (ii) the three "different" PROVEN cells are the *same 34 trades* re-sliced by three different dims (identical n, wins, PF, holdout — this is one cell, not three independent confirmations); (iii) PF=113 with avg_pnl=1.52% implies avg_loss ≈ 0.013% — that is a stop-loss that never triggers, i.e. a look-ahead or fill-assumption bug. The holdout "pass" (PF=99 on n=10) is meaningless at that sample size. **Do not trade this.** The class-level WR of 41.6% (n=238) is the honest number, and it is a losing class.
- **90d expected P&L (1% risk, $100k):** **−$1,400 to −$2,200.** At 41.6% WR with a 1.5–2.0 R:R assumption, expectancy per trade ≈ 0.416×1.75 − 0.584×1.0 = −0.31R. 238 closed × 1% × −0.31R ≈ −$740 on closed trades; extrapolated to the 5973 opened at the same rate, the drag is far larger. The "PROVEN" cell is not investable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current (likely 60–65) to **75**, AND add a hard `trust != UNK` requirement in `quality_gates.py`. The UNK-trust cell is where the fake edge lives; excluding it removes the leakage and forces the class to earn its keep on real trust scores.
- **Confidence (1-5):** **1** — the "edge" is a bug, the class WR is sub-coinflip, and the funnel is not actually gating.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** No PROVEN cells. Best PF cell is `trust=UNK & rr>=2.0 & mean_reversion` at n=22, WR=68.2%, PF=5.85 — but `holdout_pass=false`, `bonferroni_pass=false`, `wr_z=1.705` (below 2). This is exactly the shape of the falsified [H-001] COT leakage: small n, UNK trust, mean_reversion, huge PF, fails holdout. **Flag as potential leakage recurrence** — do not re-derive. Class WR 58.9% on n=56 is the only mildly positive signal, and n=56 is too small to act on.
- **90d expected P&L (1% risk, $100k):** **+$300 to +$600** on the 56 closed trades at 58.9% WR and ~1.5R avg — but the confidence interval spans zero. Not investable at size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise to 70** and require `trust != UNK`. The current 3617/5556 pass rate (65%) is far too permissive for a class with n=56 closed trades; you are opening 5500 positions to learn from 56 outcomes.
- **Confidence (1-5):** **2** — directionally positive WR but statistically indistinguishable from noise, and the top cell matches a known-falsified leakage pattern.

---

### CRYPTO
- **Real/noise verdict:** **REAL, but the "PROVEN" cell is mislabeled.** The PROVEN cell `trust=UNK & conf=C0.75-0.80 & source=alpha_engine` has n=189, WR=65.6%, WR_shrunk=64.1%, PF=2.105, holdout PF=2.902 (n=67), wr_z=4.29, bonferroni_pass=true. **This is the only cell in the entire dataset that survives every statistical test.** However: (i) it is `trust=UNK` again — the edge is "alpha_engine picks with conf 0.75–0.80 and no trust score," which is a *source* edge, not a trust edge; (ii) the three "PROVEN" cells are again the same 189 trades re-sliced (identical n/wins/PF) — one edge, not three; (iii) PF=2.1 is plausible for crypto, not suspicious. **This is the one real edge in the report.** The class-level WR of 44.4% (n=2102) is dragged down by the non-alpha_engine picks; the alpha_engine conf-0.75-0.80 subset is the signal.
- **90d expected P&L (1% risk, $100k):** **+$3,800 to +$4,500.** 189 trades × 1% × expectancy. At 65.6% WR and PF 2.1, expectancy ≈ 0.656×2.1R_loss − 0.344×1R_loss ≈ +0.66R per trade → 189 × 1% × 0.66 ≈ +$1,250 on the PROVEN cell alone. Scaled to the full 2102 closed at the class WR of 44.4% and PF implied ~1.1, the class is roughly breakeven; the alpha_engine conf-0.75-0.80 subset is where the money is. Realistic 90d P&L if you *only* traded that cell: **+$1,200 to +$1,800** net of slippage.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower to 55** *only if* you simultaneously add a hard filter `source == 'alpha_engine' AND 0.75 <= conf < 0.80`. The edge is narrow and source-specific; the current gate is too blunt. Alternatively, add `HC_MIN_TRUST_CRYPTO = 0` (i.e. allow UNK trust for crypto alpha_engine) — the HC gate is currently blocking the only real edge because trust is UNK.
- **Confidence (1-5):** **4** — the only cell that passes holdout + Bonferroni + shrunk-WR. Still only n=189, so size at half-Kelly.

---

### PREDICTION_MARKET
- **Real/noise verdict:** **NO EDGE — UNTESTABLE.** 474 scanned, 18 passed smart, **0 closed**. There is no outcome data. Cannot evaluate. Do not trade.
- **90d expected P&L (1% risk, $100k):** **$0** (no closed trades).
- **Gate change:** `SMART_PICKS_MIN_SCORE_PREDICTION_MARKET` — **do not change**; instead fix the settlement pipeline so trades close. A class with 0 closed trades in 90 days is a data-plumbing bug, not a strategy problem.
- **Confidence (1-5):** **1** — no data.

---

### BOND
- **Real/noise verdict:** **NOISE / LOSING.** No PROVEN cells, no best-PF cells at all (n=29 < 20 threshold per cell). Class WR 34.5% on n=29. This is a losing class with insufficient sample to even form a cell. 1277 opened, 29 closed — the funnel is opening 44× more than it closes, which means most bond picks never resolve (likely held to expiry or never triggered).
- **90d expected P&L (1% risk, $100k):** **−$400 to −$600.** 29 trades × 1% × (0.345×1.5 − 0.655×1.0) ≈ 29 × 1% × −0.17R ≈ −$50 on closed; but the 1277 opened at the same expectancy is a much larger drag if they ever close.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **raise to 80** (effectively disable) until n_closed >= 100. The class is not ready for capital.
- **Confidence (1-5):** **1** — losing and under-sampled.

---

### FOREX
- **Real/noise verdict:** **SUSPICIOUS — LIKELY LEAKAGE.** The best-PF cell `trust=UNK & conf>=0.90 & fam=regime & source=regime_terminal` has n=41, WR=87.8%, PF=12.0, wr_z=4.84, bonferroni_pass=true — **but holdout_pass=false** (holdout PF=3.66 on n=4). A PF of 12 on 41 trades with a 4-trade holdout is the classic signature of a regime-terminal source that is *peeking at the terminal state* (i.e. the "regime" label is assigned after the outcome is known). This is the FOREX `consensus`-style cell the prompt warned about. **Flag as potential look-ahead.** The class-level WR of 48.6% (n=541) is the honest number and is a coinflip. Also note the funnel inversion: 25584 opened vs 26417 passed_smart — the gate is not actually filtering.
- **90d expected P&L (1% risk, $100k):** **−$200 to +$200** at class WR 48.6% (essentially zero). The "PROVEN-adjacent" regime cell is not investable because holdout failed.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — **raise to 75** and add `source != 'regime_terminal'` exclusion in `quality_gates.py`. The regime_terminal source is the leakage vector; the 26417/26943 (98%) pass rate is the tell that the gate is doing nothing.
- **Confidence (1-5):** **1** — coinflip class with a leakage-shaped top cell.

---

### ETF
- **Real/noise verdict:** **NOISE / LOSING.** No PROVEN cells, no best-PF cells (n=22 < 20 per cell threshold, and even the class is n=22). Class WR 27.3% — the worst in the report. 1437 opened, 22 closed. Not investable.
- **90d expected P&L (1% risk, $100k):** **−$300 to −$500.** 22 trades × 1% × (0.273×1.5 − 0.727×1.0) ≈ 22 × 1% × −0.32R ≈ −$70 on closed; the 1437 opened is a much larger latent drag.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — **raise to 80** (disable) until n_closed >= 100. 27% WR is not a strategy.
- **Confidence (1-5):** **1** — worst WR in the report.

---

### FUTURES
- **Real/noise verdict:** **NOISE.** No PROVEN cells, no best-PF cells (n=15). Class WR 33.3% on n=15. Note [H-005] already falsified the futures momentum anti-signal — do not re-derive. 133 scanned, 118 opened, 15 closed — the funnel is opening almost everything.
- **90d expected P&L (1% risk, $100k):** **−$150 to −$250.** 15 trades × 1% × (0.333×1.5 − 0.667×1.0) ≈ 15 × 1% × −0.17R ≈ −$25 on closed; latent drag from 118 opened.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to 80** (disable) until n_closed >= 100. Also note [H-005] is already killed; do not re-open.
- **Confidence (1-5):** **1** — losing, under-sampled, and adjacent to a falsified hypothesis.

---

### INDEX
- **Real/noise verdict:** **NO EDGE — UNTESTABLE.** n_closed=1, WR=100%. A single trade is not a sample. 2137 scanned, 2136 opened, 1 closed — the settlement pipeline is broken for INDEX.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1, meaningless).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **do not change**; fix settlement so trades close. A class with 1 closed trade in 90 days is a plumbing bug.
- **Confidence (1-5):** **1** — no data.

---

### MEMECOIN
- **Real/noise verdict:** **NOISE.** n_closed=5. No PROVEN cells, no best-PF cells. Class WR 40% on n=5. 11 scanned, 6 opened, 5 closed. Not investable at any size.
- **90d expected P&L (1% risk, $100k):** **−$50 to −$100** (n=5, noise).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEMECOIN` — **raise to 85** (effectively disable). n=5 is not a class.
- **Confidence (1-5):** **1** — no data.

---

### MEME
- **Real/noise verdict:** **NO EDGE — UNTESTABLE.** 1 scanned, 1 opened, 0 closed. Likely a typo/duplicate of MEMECOIN. Merge or delete.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** **Delete the class** (or alias to MEMECOIN). It is a data-entry artifact.
- **Confidence (1-5):** **1** — no data.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only the `source=alpha_engine & conf∈[0.75,0.80)` subset.** It is the only cell in the entire 90-day report that passes holdout, Bonferroni, and shrunk-WR simultaneously (n=189, WR_shrunk=64.1%, PF=2.1, holdout PF=2.9). Size at **half-Kelly** (≈0.5% risk per trade, not 1%) because n=189 is still modest and the edge is source-specific. Expected 90d P&L on that cell alone: **+$1,200 to +$1,800** on a $100k account. Do **not** scale the full CRYPTO class — the class-level WR of 44.4% is a coinflip; the edge is the alpha_engine conf-band, not "crypto."

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

- **ETF** — worst WR (27.3%), n=22. Mutate: raise `SMART_PICKS_MIN_SCORE_ETF` to 80 and require `trust != UNK`; if n_closed < 100 after 30 days, kill.
- **BOND** — 34.5% WR, n=29. Mutate: raise `SMART_PICKS_MIN_SCORE_BOND` to 80; fix settlement (1277 opened vs 29 closed is a plumbing bug); kill if n_closed < 100 after 30 days.
- **FUTURES** — 33.3% WR, n=15, adjacent to falsified [H-005]. Mutate: raise `SMART_PICKS_MIN_SCORE_FUTURES` to 80; do not re-open [H-005].
- **FOREX** — 48.6% WR (coinflip) with a leakage-shaped `regime_terminal` cell (PF=12, holdout failed). Mutate: exclude `source=regime_terminal`, raise `SMART_PICKS_MIN_SCORE_FOREX` to 75. If the class WR stays < 52% after 30 days, kill.
- **EQUITY** — 41.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)
