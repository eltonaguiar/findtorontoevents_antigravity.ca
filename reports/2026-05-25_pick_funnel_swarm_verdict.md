# Pick Funnel Swarm Verdict — 2026-11-27 04:42 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261127T044142Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

## Pre-analysis sanity checks (applied to every class)

Before per-class verdicts, three structural red flags dominate the whole funnel:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is *never* satisfied. That means the "HIGH CONVICTION" badge on the dashboard is decorative — nothing has ever cleared it. Either the score distribution never reaches 80, or trust never reaches 60 (note: every "PROVEN" cell below is `trust=UNK`). **The HC gate is dead code in practice.**
2. **`passed_smart` ≈ `opened` in almost every class** (FOREX 26604→25801, COMMODITY 3655→5551, EQUITY 222→5979, INDEX 1538→2136). The Smart gate is not filtering — it's a rubber stamp. The only class where Smart actually filters is CRYPTO (12961→5053) and PREDICTION_MARKET (423→18).
3. **`trust=UNK` dominates every "PROVEN" cell.** A "proven" edge that only exists in the *unknown-trust* bucket is a provenance failure, not an edge. It means the signal can't be attributed to a validated source — which is exactly the fingerprint of leakage or a single-source artifact.

---

### FOREX
- **Real/noise verdict:** **NOISE / LIKELY LEAKAGE.** The only "best" cell is `trust=UNK & conf>=0.90 & fam=regime` with n=41, WR 87.8%, PF 12.0. But: holdout_n=4 (four trades!), holdout_pass=false, and the entire edge lives in `trust=UNK`. A PF of 12 on 41 trades with a 4-trade holdout is not an edge — it's a small-sample artifact. The class-level WR is 48.2% (n=531) — a coin flip. The `consensus`/`regime_terminal` source at conf>=0.90 is almost certainly a handful of correlated regime calls on one or two pairs. **Do not trade this.** The 87.8% WR with PF 12 is the classic signature of a look-ahead in the regime label (regime classified *after* the move).
- **90d expected P&L (1% risk, $100k):** **$0 (do not deploy).** If forced to model the "best" cell at 1% risk: 41 trades × $1,000 risk × (0.878×12 − 0.122×1)/12 ≈ **+$3,400** — but with holdout_n=4 this is statistically indistinguishable from zero and the PF is not credible. Realistic expectation: **−$500 to +$500**, i.e. noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current (effectively ~0, since 26604/27144 pass) to **75**, and add a hard `trust != UNK` requirement for any pick to be labeled "proven." Currently the gate passes 98% of scans; it must pass <20%.
- **Confidence (1-5):** **1**

---

### CRYPTO
- **Real/noise verdict:** **PLAUSIBLY REAL — the only credible edge in the funnel.** `trust=UNK & conf=C0.75-0.80 & source=alpha_engine`: n=187, WR 65.2%, WR_shrunk 63.8%, PF 2.05, **holdout_pass=true** (holdout_n=66, holdout PF 2.72), wr_z=4.17, bonferroni_pass=true. This is the one cell that survives every robustness check: large n, shrunk WR still >60%, holdout holds, Bonferroni-corrected. The `trust=UNK` label is a provenance gap, not a disqualifier — the source is `alpha_engine`, which is attributable. **Caveat:** the edge is concentrated in the `conf=0.75-0.80` band and `dir=LONG` — it's a narrow, specific slice, not a broad crypto edge. The class-level WR is 44.4% (n=2094), so the edge is *entirely* in this one cell; everything else is losing. That's fine — but it means sizing must be gated to this cell only.
- **90d expected P&L (1% risk, $100k):** 187 trades × $1,000 risk. At PF 2.05 and WR 65.2%, expectancy per trade ≈ (0.652×2.05 − 0.348×1)/2.05 ≈ **+0.48R** → 187 × $1,000 × 0.48 ≈ **+$89,000**. Apply a 30% haircut for slippage/fees on crypto (wider spreads, funding) → **~+$62,000**. Conservative range: **+$55k to +$90k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** it (currently passing 5053/12961 = 39%, but the edge is in a narrow conf band). More precisely: add a `CONF_BAND_CRYPTO = (0.75, 0.80)` allowlist and a `SOURCE_ALLOWLIST_CRYPTO = {"alpha_engine"}` so only the proven cell is promoted to "proven." The single highest-leverage change: **`HC_MIN_CONF_CRYPTO = 0.75`** (already 0.75) but **`HC_MIN_TRUST_CRYPTO = 0`** (drop the trust>=60 requirement for crypto, since the edge is `trust=UNK`). That single change would make the HC gate actually fire for the one real edge.
- **Confidence (1-5):** **4**

---

### PREDICTION_MARKET
- **Real/noise verdict:** **NO EDGE — INSUFFICIENT DATA.** 423 scanned, 18 passed smart, **0 closed**. Zero closed trades means zero evidence. The 18 "smart" picks are unproven. Do not deploy.
- **90d expected P&L (1% risk, $100k):** **$0** (no closed trades; cannot estimate).
- **Gate change:** `SMART_PICKS_MIN_SCORE_PREDICTION_MARKET` — leave as-is but **add a minimum-closed-trades requirement (n>=30) before any PM pick is labeled "proven."** Currently the funnel opens 423 and closes 0 — the settlement/close pipeline is broken for PM. Fix the close pipeline before touching the gate.
- **Confidence (1-5):** **1**

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** Best cell `trust=UNK & fam=mean_reversion & source=alpha_engine`: n=22, WR 63.6%, WR_shrunk 57.1%, PF 4.16 — but **holdout_pass=false, bonferroni_pass=false, wr_z=1.28**. n=22 is below the n>=20 threshold's spirit (it barely clears it), and the holdout fails. This is exactly the profile of the **H-001 COT leakage recurrence** (look-ahead in a mean-reversion commodity signal). Flag it: a mean-reversion commodity cell with PF 4 on n=22 and a failed holdout is the same fingerprint as the falsified COT hypothesis. **Do not trade.**
- **90d expected P&L (1% risk, $100k):** **$0.** If modeled: 22 × $1,000 × ~0.3R ≈ +$6,600, but holdout failure and Bonferroni failure make this indistinguishable from noise. Realistic: **−$1,000 to +$2,000**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70** and add `REQUIRE_HOLDOUT_PASS_COMMODITY = True`. Currently 3655/5603 = 65% pass; must drop to <15%.
- **Confidence (1-5):** **1**

---

### EQUITY
- **Real/noise verdict:** **SUSPICIOUS — LIKELY LEAKAGE.** `trust=UNK & fam=mean_reversion & dir=LONG`: n=64, WR **96.9%**, WR_shrunk 85.7%, **PF 109.7**, holdout_pass=true (holdout_n=17, holdout PF 99.0), wr_z=7.5, bonferroni_pass=true. A PF of 109 is not a real edge — it is a **data artifact**. The tell: `avg_pnl_pct=1.55%` with PF 109 means the loss side is essentially zero (near-zero losing trades, tiny average loss). That is the signature of **look-ahead in the mean-reversion entry** (entering after the reversal is confirmed) or **survivorship/single-symbol concentration** (62 of 64 wins on one ticker). The `trust=UNK` label confirms provenance is broken. **This is the single most dangerous cell in the report** — it looks the most "proven" and is the most likely to be fake. Treat as leakage until proven otherwise.
- **90d expected P&L (1% risk, $100k):** **$0 (do not deploy).** If the PF were real: 64 × $1,000 × ~1.5R ≈ +$96,000 — but a PF of 109 is physically implausible for equity mean-reversion. Realistic expectation if deployed: **large negative** once the leakage is corrected (cf. H-001: 85% WR → 30% WR after timestamp fix).
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise to **75** AND add `REQUIRE_TRUST_KNOWN_EQUITY = True` (reject `trust=UNK`). Currently 222/6215 = 3.6% pass — the gate is already tight, but the *proven* label is being applied to `trust=UNK` cells. The fix is in the **proven-labeling logic**, not the score gate: **`PROVEN_REQUIRES_TRUST = "KNOWN"`**.
- **Confidence (1-5):** **1** (that it's real); **5** (that it's leakage)

---

### BOND
- **Real/noise verdict:** **NO EDGE.** n=29 closed, WR 34.5%, no proven cells, no best-PF cells. Losing class.
- **90d expected P&L (1% risk, $100k):** **negative** (~−$2,000 to −$4,000 if traded at 1% risk on 29 trades at 34.5% WR).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **80** (currently 4/1295 pass, so effectively already tight; the issue is the 1266 opened vs 4 smart — the open pipeline bypasses the gate). Fix: **`OPEN_REQUIRES_SMART_PASS = True`**.
- **Confidence (1-5):** **1**

---

### ETF
- **Real/noise verdict:** **NO EDGE — INSUFFICIENT DATA.** n=14 closed, WR 42.9%. Below n>=20 threshold. No proven cells.
- **90d expected P&L (1% risk, $100k):** **$0** (n too small; ~−$500 if traded).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — leave, but add `MIN_CLOSED_FOR_PROVEN = 30`.
- **Confidence (1-5):** **1**

---

### FUTURES
- **Real/noise verdict:** **NO EDGE.** n=15 closed, WR 33.3%. Note H-005 (futures momentum anti-signal) is already falsified — do not re-derive. No proven cells.
- **90d expected P&L (1% risk, $100k):** **negative** (~−$1,500 if traded).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **80**; add `REQUIRE_HOLDOUT_PASS_FUTURES = True`.
- **Confidence (1-5):** **1**

---

### INDEX
- **Real/noise verdict:** **NO EDGE — INSUFFICIENT DATA.** n=1 closed (100% WR on one trade). Statistically meaningless.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — leave; add `MIN_CLOSED_FOR_PROVEN = 30`.
- **Confidence (1-5):** **1**

---

### UNKNOWN
- **Real/noise verdict:** **NO EDGE.** n=5 closed, WR 0%. This bucket is a data-hygiene failure — 1151 scanned, 1146 opened, 5 closed, all losses. The `UNKNOWN` class should not exist; it's a routing bug.
- **90d expected P&L (1% risk, $100k):** **negative** (~−$500).
- **Gate change:** **`REJECT_UNKNOWN_CLASS = True`** in `quality_gates.py` — drop any pick whose asset class resolves to UNKNOWN before it reaches the funnel.
- **Confidence (1-5):** **1**

---

### MEME
- **Real/noise verdict:** **NO EDGE — INSUFFICIENT DATA.** n=5 closed, WR 40%. Below threshold.
- **90d expected P&L (1% risk, $100k):** **$0** (n=5).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — leave; add `MIN_CLOSED_FOR_PROVEN = 30`.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the `conf=0.75-0.80 & source=alpha_engine & dir=LONG` cell.** It is the only cell in the entire 90-day funnel that survives all four robustness checks (n=187, shrunk WR 63.8%, holdout_pass=true, Bonferroni_pass=true). Expected 90d P&L at 1% risk on $100k: **~+$55k to +$90k** (modeled +$89k, 30% haircut → ~+$62k). Size at 1% risk per trade, cap the cell at 187 trades/90d, and **do not** extend sizing to the rest of crypto (class WR is 44.4% — the edge is entirely in this one slice).

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): EQUITY.** The `trust=UNK & fam=mean_reversion & dir=LONG` cell (PF 109.7, WR 96.9%) is the most dangerous artifact in the report — it looks the most proven and is the most likely leakage (cf. H-001 COT: 85% WR → 30% WR after timestamp fix). **Mutate before kill:** (1) re-run with `trust=KNOWN` only, (2) re-run with per-symbol concentration cap (max 20% of cell n per symbol), (3) re-run with entry timestamp shifted to next-bar-open. If the edge survives all three, it's real; if it collapses (expected), kill it. Do **not** deploy equity capital until the mutation passes.

**Also demote (kill, no mutation needed):** FOREX (`regime`/`consensus` at conf>=0.90 — holdout_n=4, PF 12 is a small-sample artifact), COMMODITY (H-001 leakage recurrence fingerprint), BOND, FUTURES, UNKNOWN, and all n<20 classes (ETF, INDEX, MEME, PREDICTION_MARKET).

**Funnel-level fix (highest leverage of all):** `passed_high_conviction = 0` across every class means the HC gate never fires. The single most impactful change is **`HC_MIN_TRUST = 0`** in `hc_filter.js` (drop the trust>=60 requirement, since every real edge is `trust=UNK`) — this would make the HC badge actually reflect the one real edge (CRYPTO) instead of being permanently empty. Second: **`OPEN_REQUIRES_SMART_PASS = True`** in `quality_gates.py` — currently `opened` ≈ `scanned` in most classes, meaning the Smart gate is bypassed at open time. Fixing that alone would cut ~40,000 low-quality opens/90d.

**Bottom line:** 1 of 11 classes has a real, robust edge (CRYPTO, one cell). 1 class (EQUITY) has a spectacular-looking cell that is almost certainly leakage. 9 classes have no edge. Do not invent edges to fill the table — the honest read is that this funnel is a single-cell crypto strategy wearing ten other asset classes as decoration.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)
