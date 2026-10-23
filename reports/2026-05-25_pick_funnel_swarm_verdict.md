# Pick Funnel Swarm Verdict — 2026-10-23 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261023T040941Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Read this first:** The funnel is broken in a way that makes most of the "PROVEN" cells untrustworthy. Look at the numbers before any per-class verdict:

- `passed_high_conviction = 0` in **every single class**. The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on literally zero picks across 90 days and ~54k scans. Either the gate is mis-wired, or the scoring distribution never reaches 80. Either way, the "HIGH CONVICTION" funnel stage is dead code right now.
- `passed_verified_alpha = 0` for EQUITY, COMMODITY, BOND, INDEX, ETF, UNKNOWN, FUTURES(≈0). Only CRYPTO (2027) and a trickle of FOREX (3) / MEME (2) / FUTURES (1) pass. So "verified alpha" is effectively a CRYPTO-only gate.
- `opened` ≈ `scanned` in every class (e.g. FOREX 23,519 opened / 24,820 scanned = 95%). The "Smart_Picks" filter is not filtering. It's a pass-through. The funnel is a funnel in name only.
- `closed` is tiny relative to `opened` (FOREX 1,301/23,519 = 5.5%; EQUITY 134/5,659 = 2.4%). The 90-day WR is computed on a **5% survivorship-biased sample** of what was actually opened. Open trades that are underwater don't count as losses yet.

That last point is the single most important caveat for every P&L number below: **the WRs are on closed trades only, and the closed set is heavily biased toward trades that hit TP fast.** Realized P&L on the full opened book will be materially worse than the closed-book WR implies.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell is `fam=mean_reversion & score_dec=S40 & conf<0.60` with n=63, WR=98.41%, PF=236.7. A PF of 236 is not a strategy — it's a bug. Three independent red flags: (1) `score_dec=S40` means these are the *lowest-scored* picks in the decile, yet they win 98% of the time — that's the signature of a look-ahead or a mislabeled outcome (e.g. TP/SL inverted, or "win" defined as "price moved at all"). (2) `conf<0.60` winning 98% is the opposite of every prior in the system. (3) `holdout_pf=99.0` is the sentinel value for "no losing trades in holdout" — with n=24 holdout and 0 losses, that's not a holdout pass, that's a holdout that never got stressed. `wr_shrunk=86.75%` is still absurd. This cell is almost certainly a **labeling/leakage artifact**, not an edge. Do not trade it. The class-level WR of 70.15% on n=134 is also suspect for the same reason (tiny closed sample, survivorship).
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** If forced to model the class-level 70% WR on 134 closed trades at 1% risk with 1:1 R:R and 0.15% round-trip slippage: 94 wins × $1,000 − 40 losses × $1,000 − 134 × $150 ≈ **+$33,900**, but this is a fantasy number because (a) the closed sample is 2.4% of opened, (b) the "edge" driving it is the leakage cell. Realistic expectation on the full book: **negative to flat.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise it hard. Currently the class passes 227/5,793 (3.9%) to "smart" but opens 5,659/5,793 (97.7%). The gate is not binding. Set `SMART_PICKS_MIN_SCORE_EQUITY = 65` (from whatever it is now, likely ~40) and add a hard `if fam == 'mean_reversion' and score_dec == 'S40': reject` until the 98% WR cell is forensically explained. Also fix the HC gate — 0 HC picks in 90 days means `hc_filter.js` thresholds are unreachable; drop `score>=80` to `score>=70` or the gate is theater.
- **Confidence (1-5):** **1** — the headline edge is a bug, not a signal.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** No PROVEN cells. Best cell is `trust=UNK & dir=LONG & source=alpha_engine`, n=40, WR=55.0%, shrunk 53.33%, PF=1.92, but `bonferroni_pass=false` and `wr_z=0.632` — that's a coin flip with a lucky tail. The momentum cells (n=21) have holdout PF 0.866 — they fail out of sample. And note the known-falsified H-001 (COT leakage, 85% cotton concentration) and H-036 (inventory gate, WR 46.1% n=1051) — this class has a **history of leakage-driven fake edges**, and the current "best" cell is `trust=UNK` which is exactly the bucket where leakage hides. Class WR 57.89% on n=57 closed is not distinguishable from 50% at this sample size (95% CI ≈ ±13pp).
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** Modeling the 57.89% WR on 57 closed trades at 1% risk, 1:1 R:R, 0.20% slippage (commodities are wider): 33 × $1,000 − 24 × $1,000 − 57 × $200 ≈ **+$7,600**, but n=57 is too small to trust and the class has a documented leakage history. Treat as **$0 expected, high variance.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — the class passes 3,732/5,927 (63%) to smart and opens 5,870/5,927 (99%). The gate is doing nothing. Raise `SMART_PICKS_MIN_SCORE_COMMODITY` to **70** and add a hard `trust != 'UNK'` requirement (the only "edge" cell is UNK, which is the leakage bucket). If that kills the class, it should be killed — see system-wide.
- **Confidence (1-5):** **1** — no proven edge, documented leakage history, gate is non-binding.

---

### BOND
- **Real/noise verdict:** **NOISE / NEGATIVE.** WR 39.39% on n=33 closed. No PROVEN cells, no best-PF cells at all (n<20 threshold). `passed_smart = 0` — the Smart gate rejects 100% of bonds, yet 553 still get opened. That means the "opened" path bypasses Smart_Picks entirely for bonds. This class is **losing money and the gate that should stop it isn't wired to the open path.** 39% WR is below breakeven at any R:R near 1:1.
- **90d expected P&L (1% risk, $100k):** **Negative.** 13 × $1,000 − 20 × $1,000 − 33 × $150 ≈ **−$11,950** on the closed book. On the full 553 opened, extrapolating the 39% WR: roughly **−$40k to −$60k** depending on how many open positions are underwater. This class is a **bleeder.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — but the real fix is upstream: **wire the open path to respect `passed_smart`.** Right now `passed_smart=0` and `opened=553` is a contradiction. Set `SMART_PICKS_MIN_SCORE_BOND = 55` AND add `if not passed_smart: skip_open` in `production_scanner.py`. If bonds can't clear 55, they shouldn't open.
- **Confidence (1-5):** **1** — actively losing, gate bypassed.

---

### INDEX
- **Real/noise verdict:** **NOISE.** n=4 closed. WR 25%. Statistically meaningless — 4 trades is not a sample. `passed_smart=1,394/1,749` (80%) but `opened=1,745` (99.8%) — gate non-binding again. No PROVEN cells, no best-PF cells. Do not draw any conclusion from 4 trades.
- **90d expected P&L (1% risk, $100k):** **$0 / indeterminate.** 1 win × $1,000 − 3 × $1,000 − 4 × $150 ≈ **−$2,600** on the closed book, but n=4 is noise. Full-book expectation unknown; treat as **$0 with wide error bars.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **65** and require `passed_smart` before open. But honestly, with n=4 closed, the right move is to **freeze INDEX opens** until you have ≥30 closed trades to evaluate. Set `SMART_PICKS_MIN_SCORE_INDEX = 999` (effectively disable) pending data.
- **Confidence (1-5):** **1** — no sample, no edge, gate non-binding.

---

### FOREX
- **Real/noise verdict:** **NOISE / LIKELY LEAKAGE.** The "best PF" cells are all the *same* cell viewed through different dims: `conf>=0.90 & dir=LONG & source=regime_terminal`, n=28, WR=85.71%, PF=8.885. Three red flags: (1) `train_pf=0.0, train_n=4` — the training split has **4 trades and zero wins**, yet the holdout has 24 trades and 24 wins (`holdout_pf=99.0` sentinel). That's not a holdout pass, that's a **temporal split where all the wins landed in holdout** — the classic signature of a regime that only existed in the last ~30 days, or of a timestamp bug. (2) `holdout_pass=false` is explicitly set despite the 99.0 PF — the harness itself is flagging this. (3) `source=regime_terminal` with `conf>=0.90` and 85% WR on n=28 is exactly the profile of the H-001 COT leakage pattern (high-confidence, single-source, recent-window-only). **This is not a proven edge; it's a 28-trade recent-window artifact.** The class-level WR 42.72% on n=529 is the honest number, and it's below breakeven.
- **90d expected P&L (1% risk, $100k):** **Negative.** Class WR 42.72% on 529 decisive closed trades. At 1% risk, 1:1 R:R, 0.10% slippage (FX tight): 226 × $1,000 − 303 × $1,000 − 529 × $100 ≈ **−$129,900** on the closed book. Even if you cherry-pick the 28-trade "edge" cell at 85% WR: 24 × $1,000 − 4 × $1,000 − 28 × $100 ≈ **+$17,200**, but that's a 28-trade recent-window bet on a cell the harness itself marked `holdout_pass=false`. **Do not deploy.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — the class passes 23,966/24,820 (96.6%) to smart and opens 23,519 (94.8%). The gate is a **rubber stamp**. Raise `SMART_PICKS_MIN_SCORE_FOREX` to **70** and add a hard `if source == 'regime_terminal' and conf >= 0.90: require train_n >= 30` guard. Also: the `holdout_pass=false` flag on the only "edge" cell should auto-block it from the HC funnel — wire that flag into `hc_filter.js`.
- **Confidence (1-5):** **1** — class is losing, "edge" cell fails its own holdout, gate is non-binding.

---

### CRYPTO
- **Real/noise verdict:** **THE ONLY CELL THAT SURVIVES SCRUTINY — with caveats.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`, n=184, WR=79.35%, shrunk 76.47%, PF=4.273, `train_pf=6.148 (n=101)`, `holdout_pf=2.744 (n=83)`, `holdout_pass=true`, `wr_z=7.962`, `bonferroni_pass=true`. This is the **only** cell in the entire dataset that passes train/holdout split, Bonferroni correction, and has a plausible (not absurd) PF. The holdout PF of 2.744 on n=83 is the strongest evidence in the report. **Caveats:** (1) `trust=UNK` — the edge lives in the unknown-trust bucket, which is where leakage hides; you must verify the trust-scoring pipeline isn't dropping the good picks into UNK. (2) `score_dec=S50` is the *middle* decile — the edge is in the middle of the score distribution, not the top, which is counterintuitive and worth a forensic check (is the score decile computed pre- or post-filter?). (3) `source=alpha_engine` only — this is a single-source edge; if alpha_engine has a timestamp bug, the whole thing collapses. (4) The class-level WR 45.08% on n=2,420 is **below breakeven** — the edge is concentrated in one cell (184/2,420 = 7.6% of closed trades), and the other 92% are bleeding. **Verdict: real edge in one cell, but the class as a whole is a loser.** The play is to *isolate* the cell, not to scale the class.
- **90d expected P&L (1% risk, $100k):** **Positive, but only on the isolated cell.** On the 184-trade edge cell at 1% risk, 1:1 R:R, 0.25% slippage (crypto): 146 × $1,000 − 38 × $1,000 − 184 × $250 ≈ **+$62,000**. On the full class (2,420 closed, 45.08% WR): 1,091 × $1,000 − 1,329 × $1,000 − 2,420 × $250 ≈ **−$843,000** — the class is a massive loser. **The only deployable number is the +$62k on the isolated cell**, and that assumes the cell is real (see caveats). Realistic haircut for the UNK-trust and single-source risk: **+$30k to +$45k** on the isolated cell.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — but the real fix is a **cell-level allowlist**, not a score threshold. Add to `production_scanner.py`: `if source == 'alpha_engine' and 0.75 <= conf < 0.80 and score_dec == 'S50': boost_to_HC = True`. And in `hc_filter.js`, the HC gate is currently `score>=80, conf>=0.75, trust>=60` — but the edge cell has `trust=UNK`, so it would be **rejected by HC**. That's the bug: **the HC gate is filtering out the only proven edge.** Change `hc_filter.js` to `trust >= 60 OR (source == 'alpha_engine' and conf in [0.75, 0.80) and score_dec == 'S50')`. That single change routes the proven cell into HC and is the highest-leverage gate edit in the entire system.
- **Confidence (1-5):** **3** — real train/holdout/Bonferroni pass, but UNK-trust and single-source caveats keep it from a 4.

---

### ETF
- **Real/noise verdict:** **NOISE.** n=9 closed, WR 22.22%. No PROVEN cells, no best-PF cells. `passed_smart=304/356` (85%) but `opened=347` (97.5%) — gate non-binding. 9 trades is not a sample.
- **90d expected P&L (1% risk, $100k):** **Negative / indeterminate.** 2 × $1,000 − 7 × $1,000 − 9 × $150 ≈ **−$6,350** on closed book. n=9 is noise. Treat as **$0 expected, wide bars.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **65** and require `passed_smart` before open. With n=9, consider freezing like INDEX.
- **Confidence (1-5):** **1** — no sample.

---

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA-QUALITY BUG.** n=3 closed, WR 0%. `scanned=1,399` but `passed_smart=151` (10.8%) and `opened

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage. n=63, WR_shrunk=86.75, PF=236.7 is statistically impossible without single-symbol concentration or look-ahead; holdout_pass true does not override the extreme PF.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 2

**### COMMODITY**
- Real/noise verdict: Noise. No proven cells; best_pf_overall cells fail bonferroni or have WR_shrunk <55 after shrinkage.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 1

**### BOND**
- Real/noise verdict: No edge. Zero proven cells and tiny decisive n=33.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None (class has insufficient data)
- Confidence (1-5): 1

**### INDEX**
- Real/noise verdict: No edge. n=4 decisive trades.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 1

**### FOREX**
- Real/noise verdict: Noise. top_edges_proven empty; listed cells have holdout_pass=false and extreme PF on tiny train_n=4, consistent with leakage.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF_FOREX = 0.92
- Confidence (1-5): 2

**### CRYPTO**
- Real/noise verdict: Real. n=184, WR_shrunk=76.47, PF=4.273, holdout_pass=true, bonferroni_pass=true across three overlapping cells; survives shrinkage and walk-forward.
- 90d expected P&L (1% risk, $100k): ~$9,800 (184 trades × 1% risk × avg 1.60% edge after 0.15% slippage, 45% avg win size).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 52
- Confidence (1-5): 4

**### ETF**
- Real/noise verdict: No edge. n=9 decisive.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 1

**### UNKNOWN**
- Real/noise verdict: No edge. n=3.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 1

**### MEME**
- Real/noise verdict: No edge. n=7.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 1

**### FUTURES**
- Real/noise verdict: No edge. n=16 decisive, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: None
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with verified, holdout-passed edge meeting PROVEN criteria). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its PF=236.7 is a clear leakage recurrence and should be mutated (raise score floor + add symbol-concentration gate) before any further allocation. All other classes produce zero usable edge.
