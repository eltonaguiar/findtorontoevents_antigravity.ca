# Pick Funnel Swarm Verdict — 2026-10-06 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261006T041119Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** trades across 90 days and ~51k scanned. Either the gate is mis-wired, or the scoring distribution never reaches 80. This is the single biggest finding in the dataset — the "HIGH CONVICTION" funnel is a dead branch.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (1821) and a trickle in FOREX/FUTURES/MEME pass. The verified-alpha stage is effectively CRYPTO-only.
3. **`opened` >> `passed_smart` in most classes** (EQUITY 5510 opened vs 251 smart; FOREX 21631 vs 22076; BOND 525 vs 3). The funnel counters are not measuring the same population — "opened" is clearly counting a different (pre-gate or legacy) stream. Any WR computed on `closed` is therefore **not** the WR of the smart/HC-gated population. Treat all WR numbers as descriptive of the *opened* book, not the *gated* book.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The "PROVEN" cell `fam=mean_reversion & score_dec=S40` shows n=67, WR=98.51%, PF=216.95. A 98.5% win rate on 67 trades with PF 217 is not a market edge — it is a **marking/exit bug**. Most likely: mean-reversion exits booked at the entry-side limit (look-ahead on the fill) or PnL computed on unrealized marks that never hit a stop. The train/holdout split (PF 107 → 99) is *too* stable, which is the signature of a deterministic accounting artifact, not alpha. Also note `trust=UNK` dominates — the "edge" lives entirely in untrusted picks, which is backwards. **Reject.**
- **90d expected P&L (1% risk, $100k):** If taken literally at face value: 67 trades × 1% × $100k × (avg_pnl 1.29% / 1% risk) ≈ **+$86k**. This number is fiction. Realistic expectation after fixing the accounting bug: **$0 to −$5k** (EQUITY decisive WR 68% on n=157 is plausible but the sample is tiny and the "edge" cell is contaminated).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current floor to **≥ 55** and add a hard `trust != UNK` requirement in `quality_gates.py`. The mean_reversion/S40/UNK cell must be excluded, not promoted.
- **Confidence (1-5):** **1** (that the edge is real). 4 that it's a bug.

### INDEX
- **Real/noise verdict:** **NOISE.** n_closed=5, WR=20%. No PROVEN cells. `passed_smart=1565` of 1850 scanned but only 8 closed — the class is essentially **not trading**, it's accumulating open positions. Nothing to evaluate.
- **90d expected P&L (1% risk, $100k):** **−$1.2k** (5 decisive trades, 1W/4L at 1% risk ≈ −3R ≈ −$3k gross, call it −$1.2k after the one win). Statistically meaningless.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise aggressively to ≥ 70** to stop the 1565-pick bleed, or disable INDEX smart picks entirely until close-rate > 30%.
- **Confidence (1-5):** **1**.

### FOREX
- **Real/noise verdict:** **NOISE, and the "best PF" cell is a classic leakage recurrence.** `conf=C>=0.90 & fam=regime & source=regime_terminal`: n=54, WR=68.5%, PF=3.197, **but train_pf=0.298 (n=17) vs holdout_pf=14.149 (n=37)**. That train/holdout inversion is the textbook signature of **regime_terminal leaking future regime labels into the confidence score** — the "confidence" is derived from the same regime state that determines the outcome. `holdout_pass=false`, `bonferroni_pass=false`. This is the same failure mode as H-001 (COT look-ahead) and H-035 (funding timing sign instability). **Reject.** The class-level WR of 43.45% on n=527 decisive is the honest number, and it's below breakeven for typical FX cost structures.
- **90d expected P&L (1% risk, $100k):** 527 decisive × 1% × $100k × (0.4345 − 0.5) ≈ **−$34.5k** before costs; with ~0.5bp round-trip slippage on 21k opened, add roughly **−$10k to −$15k** more. Call it **−$45k to −$50k**. FOREX is a net loser.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥ 65** AND add `source != regime_terminal` exclusion in `quality_gates.py`. The regime_terminal source must be quarantined pending a timestamp audit (same fix that killed H-001).
- **Confidence (1-5):** **1** (edge real). 5 that regime_terminal is leaking.

### CRYPTO
- **Real/noise verdict:** **PARTIALLY REAL — the only class with a defensible edge.** The cell `conf=C0.75-0.80 & dir=LONG & score_dec=S50 & source=alpha_engine`: n=174, WR=72.99%, wr_shrunk=70.62%, PF=3.427, **train_pf=3.88 (n=140) → holdout_pf=2.188 (n=34), holdout_pass=true, bonferroni_pass=true, wr_z=6.065**. This is the *only* cell in the entire dataset that survives Bonferroni and holds out-of-sample. The holdout PF decay (3.88→2.19) is normal and healthy. Caveats: (i) the cell is defined by `conf=0.75-0.80` — a narrow band, so watch for band-snooping; (ii) `trust=UNK` variant is identical, meaning trust adds nothing here; (iii) 174 trades over 90d on one source is a single-strategy concentration risk. But the statistics are honest. **Accept with position limits.** Note: no `ml` cell appears in the PROVEN list — the prompt's concern about "CRYPTO ml cells" is not borne out by this data; the edge is `alpha_engine`, not `ml`.
- **90d expected P&L (1% risk, $100k):** 174 trades × 1% × $100k × (avg_pnl 1.3826% / 1% risk) ≈ **+$24.1k** gross. Apply 30% haircut for holdout decay (2.19/3.43) and slippage on crypto (5bp round-trip): **+$15k to +$18k**. This is the number I'd actually underwrite.
- **Gate change:** `hc_filter.js` — the HC gate is dead (0 passes). Lower `HC_MIN_SCORE` from 80 to **72** and `HC_MIN_CONF` from 0.75 to **0.72**, keeping `HC_MIN_TRUST` at 60 *only if* trust is populated; given `trust=UNK` dominates the winning cell, **drop the trust requirement to `trust >= 0` (i.e., remove it) for CRYPTO** and rely on the conf+score+source filter. This is the single highest-leverage change in the whole system.
- **Confidence (1-5):** **4**.

### COMMODITY
- **Real/noise verdict:** **NOISE.** Best cell `fam=momentum & score_dec=S50`: n=21, WR=52.38%, wr_shrunk=51.22%, PF=4.447 but **holdout_pass=false, bonferroni_pass=false, wr_z=0.218**. PF 4.4 on a 52% WR means the PF is driven by 2–3 outlier winners — classic fat-tail noise on n=21. This is the same shape as the falsified H-001 (COT) and H-036 (inventory) — momentum on commodities keeps looking good on tiny samples and dying on audit. **Reject.**
- **90d expected P&L (1% risk, $100k):** 86 decisive × 1% × $100k × (0.5116 − 0.5) ≈ **+$1.0k** gross, minus slippage on 5.7k opened ≈ **−$2k to +$1k**. Effectively zero.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥ 60** and require `n_closed >= 30` before any cell is promoted. Do not act on n=21.
- **Confidence (1-5):** **1**.

### FUTURES
- **Real/noise verdict:** **NOISE.** n_closed=16, WR=31.25%. No PROVEN cells. Consistent with the falsified H-005 (futures_momentum anti-signal — inversion doesn't fix it). **Reject.**
- **90d expected P&L (1% risk, $100k):** 16 × 1% × $100k × (0.3125 − 0.5) ≈ **−$3.0k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥ 70** or disable. The class has no demonstrated edge and a known falsified hypothesis in its history.
- **Confidence (1-5):** **1**.

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=31, WR=45.16%, no PROVEN cells. `passed_smart=3` of 556 scanned — the smart gate is essentially rejecting the entire class, which is correct behavior. **Reject.**
- **90d expected P&L (1% risk, $100k):** 31 × 1% × $100k × (0.4516 − 0.5) ≈ **−$1.5k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — leave at current (it's already filtering to 3 picks). No change needed; the gate is working.
- **Confidence (1-5):** **1**.

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=9, WR=22.22%. No PROVEN cells. **Reject.**
- **90d expected P&L (1% risk, $100k):** 9 × 1% × $100k × (0.2222 − 0.5) ≈ **−$2.5k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥ 65**; 294 of 342 passing smart is far too permissive for a class with 22% WR.
- **Confidence (1-5):** **1**.

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA HYGIENE FAILURE.** n_closed=7, WR=0%. 1366 scanned, 1359 opened, 165 passed smart. The fact that 1366 instruments are classified UNKNOWN is itself a bug — these should be routed or dropped, not traded. **Reject.**
- **90d expected P&L (1% risk, $100k):** 7 × 1% × $100k × (0 − 0.5) ≈ **−$3.5k**.
- **Gate change:** `quality_gates.py` — add a hard `asset_class != UNKNOWN` filter at the top of the smart-picks pipeline. Do not trade unclassified instruments.
- **Confidence (1-5):** **1**.

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=4, WR=25%. No PROVEN cells. **Reject.**
- **90d expected P&L (1% risk, $100k):** 4 × 1% × $100k × (0.25 − 0.5) ≈ **−$1.0k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥ 75** or disable. n=4 is not a class.
- **Confidence (1-5):** **1**.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only, and only the `alpha_engine` / `conf=0.75-0.80` / `score_dec=S50` / LONG cell.** It is the sole cell in the entire 90-day dataset that passes Bonferroni, holds out-of-sample (PF 3.88→2.19), and has n≥170. Size it at **0.5% risk per trade** (not 1%) for the first 30 days given the single-source concentration, then step to 1% if live WR stays within 1σ of the 70.6% shrunk estimate. Expected 90d P&L at 0.5% risk: **+$7.5k to +$9k**.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

- **FOREX** — demote to paper-only. The `regime_terminal` source is a **leakage recurrence** of the H-001 pattern (train_pf 0.298 vs holdout_pf 14.149 is the tell). Mutate axis 1 (source): quarantine `regime_terminal`, re-run with timestamp-corrected regime labels. If WR stays <48% after the fix, kill.
- **EQUITY** — demote to paper-only. The `mean_reversion/S40/UNK` cell (WR 98.5%, PF 217) is an **accounting bug**, not an edge. Mutate axis 2 (exit logic): force mark-to-market on every bar and re-run. If WR collapses to ~50%, the bug is confirmed and the class should be killed.
- **COMMODITY** — demote to paper-only. n=21 "edge" with holdout_pass=false is the same shape as the already-falsified H-001 and H-036. Do not re-derive; mutate axis 3 (sample size floor: require n≥30 closed before promotion) and re-audit in 30 days.
- **INDEX, FUTURES, BOND, ETF, UNKNOWN, MEME** — **kill the smart-pick branch** (not the class; keep scanning for data). None has n≥30 decisive with WR>50%. UNKNOWN additionally needs a routing fix before it can be evaluated at all.

**The single most important fix is not per-class — it's the dead HC gate.** `passed_high_conviction = 0` across 51k scans means the dashboard's "HIGH CONVICTION" tab is showing nothing, and the CRYPTO edge above is *not* reaching the user-facing funnel. Fix `hc_filter.js` thresholds (score 80→72, conf 0.75→0.72, drop trust requirement for CRYPTO) **before** any sizing changes. Otherwise you'll scale a class whose edge never reaches the UI.

**Honest bottom line:** 1 of 10 classes has a defensible edge (CRYPTO, confidence 4/5). 2 classes show leakage/bug signatures that must be quarantined (FOREX regime_terminal, EQUITY mean_reversion). 7 classes have no edge and should not receive real capital. The 90-day aggregate across all classes is roughly **−$60k to −$70k** at 1% risk — the system is net-negative outside CRYPTO, and the CRYPTO edge is real but narrow.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### EQUITY**
- Real/noise verdict: Noise/leakage — n=67 but 66 wins, PF=216.95 and WR_shrunk=87% are statistically impossible without single-symbol concentration or look-ahead; violates known rejected hypotheses pattern.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact, do not trade).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

**### INDEX**
- Real/noise verdict: No edge — n=5 decisive, no proven cells, overall WR 20%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 70
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: No edge — top cells fail holdout and Bonferroni; overall WR 43.45% with tiny decisive sample.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF_FOREX = 0.85
- Confidence (1-5): 5

**### CRYPTO**
- Real/noise verdict: Real edge — n=174-175, WR_shrunk~70.3%, PF=3.43, holdout passes, Bonferroni passes; no obvious leakage flags.
- 90d expected P&L (1% risk, $100k): ~$4,800 (175 trades × $1k risk × 1.37% avg pnl, 0.15% slippage, 0.8 fill rate).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

**### COMMODITY**
- Real/noise verdict: No edge — no proven cells, best_pf cells fail holdout/Bonferroni; matches known COT leakage pattern.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 75
- Confidence (1-5): 5

**### FUTURES**
- Real/noise verdict: No edge — n=16 decisive, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 70
- Confidence (1-5): 5

**### BOND**
- Real/noise verdict: No edge — n=31 decisive, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 5

**### ETF**
- Real/noise verdict: No edge — n=9 decisive, no proven cells.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 70
- Confidence (1-5): 5

**### UNKNOWN**
- Real/noise verdict: No edge — n=7 decisive, WR 0%.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

**### MEME**
- Real/noise verdict: No edge — n=4 decisive.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically validated, holdout-passing edge). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL (high risk of leakage recurrence; mutate score floor and re-audit before any further use). All other classes have zero actionable edge.
