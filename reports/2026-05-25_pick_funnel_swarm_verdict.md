# Pick Funnel Swarm Verdict — 2026-10-24 04:09 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261024T040921Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**TL;DR:** Only **CRYPTO** has a defensible, holdout-validated edge. **EQUITY**'s "98% WR" cell is almost certainly a leakage artifact (see below). Everything else is noise, thin samples, or already-falsified territory. Do not scale anything except CRYPTO, and even there size conservatively.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** n=55 closed is far too thin to prove anything. Best cell (`trust=UNK & dir=LONG & source=alpha_engine`) has n=38, WR_shrunk=51.7%, PF=1.78, but **holdout PF=1.27** and `bonferroni_pass=false`. The 56.4% headline WR is within 1σ of coin-flip at n=55. Also note: this is exactly the class where H-001 (COT leakage) and H-036 (inventory gate) were already killed — any "edge" here should be treated as a leakage-recurrence suspect until proven otherwise. The `trust=UNK` dominance (all top cells) is a red flag: it means the "edge" is concentrated in picks with *no* trust signal, which is the opposite of what a real edge looks like.
- **90d expected P&L (1% risk, $100k):** **~$0 to −$400.** At 1% risk ($1k/trade) × 55 trades × (0.5636 − 0.5) × avg R ≈ breakeven after slippage. With realistic commodity slippage (2–4 bps + spread on futures/CFDs), expected value is **negative**. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise from current floor to **≥ 70** (or equivalent 0.70 confidence floor). The current funnel passes 3,707/5,940 (62%) of scans to "smart" — that is not a filter, that is a pass-through. Tighten until passed_smart/scanned < 15%.
- **Confidence (1-5):** **1**

---

### INDEX
- **Real/noise verdict:** **NOISE / UNMEASURABLE.** n=4 closed. WR=25%. There is literally nothing to conclude. Any "edge" claim here is fabrication.
- **90d expected P&L (1% risk, $100k):** **−$300 to −$600** (4 trades × $1k × (0.25−0.5) × ~1.5R avg loss). Statistically meaningless but directionally negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥ 75**. 1,378/1,745 (79%) pass rate is absurd; the gate is doing nothing. Also add a **minimum-closed-trades guard** before any INDEX pick is surfaced as "smart" (n<30 → suppress).
- **Confidence (1-5):** **1**

---

### FOREX
- **Real/noise verdict:** **NOISE, and the "best" cell is a textbook leakage pattern.** The `trust=UNK & conf=C>=0.90 & dir=LONG` cell shows PF=8.885, WR=85.7%, but **train_n=4, holdout_n=24, holdout_pass=false, train_pf=0.0**. That is: the "edge" only exists in the holdout, with essentially no training data. This is the classic signature of **look-ahead / survivorship / single-regime concentration** — not a real edge. `top_edges_proven` is **empty** for FOREX, which is the honest answer. The 43% headline WR across 1,308 closed trades is a **losing** class. The `consensus`/`regime_terminal` source concentration (all 28 wins in one source, one direction, one confidence band) is a single-strategy artifact, not a diversified edge.
- **90d expected P&L (1% risk, $100k):** **−$1,500 to −$2,500.** 1,308 closed × $1k × (0.4305 − 0.5) × ~1.2R avg ≈ −$1,100 gross, plus FX spread/slippage (~1–2 bps round-trip on 23k opens) ≈ **−$2k**. This class is bleeding.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **≥ 80** AND add a hard **`MAX_FOREX_OPEN_PER_DAY` cap** (e.g. 50). 23,974/24,829 (96.6%) pass rate means the gate is a no-op. The real fix is upstream: the scanner is emitting 24k FOREX signals in 90d — that is ~270/day, which is noise generation, not signal.
- **Confidence (1-5):** **1** (high confidence it's noise)

---

### EQUITY
- **Real/noise verdict:** **LEAKAGE — DO NOT TRADE.** The `conf=C<0.60 & fam=mean_reversion` cell shows WR=98.46%, PF=172.3, n=65, holdout_pass=true, bonferroni_pass=true. **This is not a real edge.** Red flags, in order of severity:
  1. **PF=172** is physically impossible for a real strategy over 65 trades. Even a perfect 64/65 with tiny losses gives PF ~50–80 max. PF>100 means the loss side is near-zero — i.e., **losses are being dropped, mis-timed, or the exit is look-ahead** (e.g., "close at next bar's high" or a stop that never triggers because it's set from future data).
  2. **`conf=C<0.60`** — the edge is in *low-confidence* picks. Real edges concentrate in high-confidence. Low-conf + high-WR is the signature of a **selection artifact** (e.g., only low-conf picks that happened to win got logged, or the confidence field is post-hoc).
  3. **`trust=UNK`** — same pattern as COMMODITY. Edge lives where there's no trust signal.
  4. **`fam=mean_reversion` + `dir=LONG` + `source=alpha_engine`** — all three "proven" cells are the *same 65 trades* re-sliced. That's one cell, not three independent confirmations. Bonferroni on correlated slices is not Bonferroni.
  5. **`avg_pnl_pct=1.50%`** with 98% WR implies the strategy is capturing ~1.5% per trade with near-zero drawdown — that is the exact profile of a **look-ahead exit** (e.g., "sell at the day's high").
  
  **Verdict: treat as H-001-style leakage recurrence. Do not deploy. File a hypothesis-registry entry to investigate the EQUITY mean_reversion exit logic for look-ahead.**
- **90d expected P&L (1% risk, $100k):** **$0 (do not deploy).** If the leakage were real, the naive math would be ~$65k, which is exactly why it's dangerous — it will not replicate live. **Expected live P&L: negative** (you'll trade the 2% losers at full size and the "wins" will evaporate).
- **Gate change:** **Do not change a threshold — fix the leak.** In `alpha_engine/production_scanner.py`, audit the `mean_reversion` exit path for look-ahead (specifically: any use of `next_bar_high`, `future_close`, or `shift(-1)` in the exit/stop logic). Until that's cleared, set `SMART_PICKS_MIN_SCORE_EQUITY` to **≥ 85** to suppress the class entirely (233/5,799 = 4% pass is already tight, but the 65 leaked trades are inside it).
- **Confidence (1-5):** **5** (high confidence it's leakage, not edge)

---

### CRYPTO
- **Real/noise verdict:** **REAL — the only defensible edge in the funnel.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell: n=186, WR=79.0%, WR_shrunk=76.2%, PF=4.24, **train_pf=6.21 (n=101), holdout_pf=2.68 (n=85), holdout_pass=true, wr_z=7.92, bonferroni_pass=true.** This is the profile of a real edge:
  - Holdout PF (2.68) is *lower* than train (6.21) — that's **healthy degradation**, not leakage (leakage shows holdout ≈ train or holdout > train).
  - n=186 is large enough for the z-score to be meaningful.
  - The edge is in a **specific, narrow band** (conf 0.75–0.80, score_decile S50) — not "all low-conf" or "all UNK trust." That specificity is what real edges look like.
  - **Caveat:** `trust=UNK` still appears in the cell. The edge is real *conditional on* the alpha_engine source + that conf/score band, but the trust signal is not adding information. That's fine — it means trust scoring is broken for CRYPTO, not that the edge is fake.
  - **Second caveat:** PF=4.24 with WR=79% implies avg win / avg loss ≈ 1.1 — i.e., the edge is **WR-driven, not R:R-driven**. That's fragile to regime change (a WR edge can flip fast). Size accordingly.
  - The `ml` cell mentioned in the prompt is **not in the data provided** — I can't validate it. If it exists with PF>10, treat it as leakage-suspect until holdout-validated like the cell above.
- **90d expected P&L (1% risk, $100k):** **~+$8,000 to +$12,000.** Math: 186 trades × $1k risk × (0.79 − 0.5) × ~1.1R avg ≈ **+$5,900 gross** on the proven cell alone. But the class has 2,455 closed trades at 44.9% WR overall — the proven cell is a *subset*. Realistic deployable estimate: if you gate to the proven cell (conf 0.75–0.80, S50, alpha_engine), you capture ~186 trades/90d at ~+$6k, minus slippage (~5–10 bps on crypto, ~$1.5k) ≈ **+$4.5k to +$6k**. If you deploy the *whole* CRYPTO class at 1% risk, you get 2,455 × $1k × (0.449 − 0.5) × 1.2R ≈ **−$15k** — i.e., the class is net-negative *without* the gate. **The gate is the edge.**
- **Gate change:** In `hc_filter.js`, the HIGH CONVICTION gate is `score>=80, conf>=0.75, trust>=60`. **The `trust>=60` clause is killing the proven cell** (which is `trust=UNK`). Change to: **`trust>=60 OR (source=='alpha_engine' AND conf in [0.75,0.80] AND score_dec=='S50')`** — i.e., add an explicit bypass for the validated cell. Alternatively, in `quality_gates.py`, add `SMART_PICKS_CRYPTO_CONF_BAND = (0.75, 0.80)` and `SMART_PICKS_CRYPTO_SCORE_DEC = 'S50'` as a hard allow-list. **This is the single highest-leverage change in the whole funnel.**
- **Confidence (1-5):** **4** (real edge, but WR-driven and regime-fragile — not a 5)

---

### ETF
- **Real/noise verdict:** **NOISE.** n=9 closed, WR=22%. Unmeasurable and negative.
- **90d expected P&L (1% risk, $100k):** **−$200 to −$400.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥ 80**; 302/354 (85%) pass rate is a no-op. Add min-closed-trades guard (n<30 → suppress).
- **Confidence (1-5):** **1**

---

### BOND
- **Real/noise verdict:** **NOISE.** n=33, WR=39.4%. `passed_smart=0` — the smart gate already rejects all BOND picks, yet 597 still opened. That's a **funnel integrity bug**: picks are opening that the gate rejected. Investigate `production_scanner.py` for a bypass path.
- **90d expected P&L (1% risk, $100k):** **−$350 to −$500.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — the gate is already at 0 pass, so the fix is **not a threshold** — it's a **hard block**: `if asset_class == 'BOND' and passed_smart == 0: skip_open()`. The 597 opens are a bug, not a signal.
- **Confidence (1-5):** **1**

---

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA HYGIENE FAILURE.** n=3, WR=0%. 1,397 opens with 3 closes means 1,394 positions are stuck open — that's a **lifecycle bug**, not a strategy. `passed_smart=150` but `opened=1,397` — again, opens bypassing the gate.
- **90d expected P&L (1% risk, $100k):** **−$150 to −$300** (3 trades), but the real cost is the 1,394 stuck positions tying up capital and skewing every downstream metric.
- **Gate change:** **Not a threshold — a data fix.** In `production_scanner.py`, add `if asset_class == 'UNKNOWN': reject()` at the top of the pick-emit path. UNKNOWN should never reach the funnel.
- **Confidence (1-5):** **1**

---

### FUTURES
- **Real/noise verdict:** **NOISE.** n=16, WR=43.75%. `top_edges_proven` empty. Also: H-005 (futures momentum anti-signal) was already killed — do not re-derive.
- **90d expected P&L (1% risk, $100k):** **−$100 to −$200.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥ 75**; 151/202 (75%) pass is too loose. Add min-closed-trades guard.
- **Confidence (1-5):** **1**

---

### MEME
- **Real/noise verdict:** **NOISE.** n=8, WR=25%. Unmeasurable.
- **90d expected P&L (1% risk, $100k):** **−$200 to −$400.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥ 85** (meme is high-variance; only take the top decile). 13/30 pass is already tight but the 22 opens vs 13 passed_smart shows a bypass.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only through the validated cell.**
- The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the only holdout-validated, Bonferroni-passing, large-n edge in the entire funnel. Deploy at **0.5% risk per trade** (not 1%) for the first 30 days to confirm live replication, then scale to 1% if holdout PF holds ≥2.0. Expected 90d P&L at 1% risk: **+$4.5k to +$6k** on the gated subset. Do **not** deploy the full CRYPTO class — it's net-negative without the gate.
- **Critical prerequisite:** fix the `hc_filter.js` `trust>=60` clause that currently excludes the proven cell (it's `trust=UNK`). Without that fix, the edge is invisible to the HC gate and you'll deploy the losing 2,455-trade class instead of the winning 186-trade cell.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **FOREX** — 1,308 closed, 43% WR, net-negative, and the "best" cell is a train_n=4 leakage artifact. Mutate the scanner to cap emissions at ~50/day and raise `SMART_PICKS_MIN_SCORE_FOREX` to 80. If after 30 days the gated subset still shows WR<50%, kill the class.
- **EQUITY** — **do not mutate the gate; mutate the exit logic.** The 98% WR cell is a leakage recurrence (PF=172 is physically impossible). File a hypothesis-registry entry, audit `mean_reversion` exits for look-ahead, and suppress the class (`SMART_PICKS_MIN_SCORE_EQUITY ≥ 85`) until cleared. This is the most dangerous item in the funnel because it *looks* like the best edge — deploying it live would be the single worst decision available.
- **COMMODITY** — already has two killed hypotheses (H-001, H

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### COMMODITY
- Real/noise verdict: Noise. No proven cells; best_pf_overall cells have low WR_shrunk (~50%), marginal PF, tiny n, and fail bonferroni. Matches known COT leakage patterns.
- 90d expected P&L (1% risk, $100k): $0 (or -$800 after realistic slippage/commissions on 55 closes).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 72
- Confidence (1-5): 4

### INDEX
- Real/noise verdict: Noise. n=4 closed; zero proven edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 75
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise. "Proven" cells have train_n=4, holdout_pass=false, and PF inflated by tiny sample. No stable edge.
- 90d expected P&L (1% risk, $100k): -$1,200 (negative expectancy after costs on 532 decisive trades).
- Gate change: HC_MIN_CONFIDENCE = 0.82
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Sample-noise / leakage. 98.46% WR on n=65 with PF=172 is statistically impossible without look-ahead bias or single-symbol concentration. Holdout numbers are suspiciously perfect.
- 90d expected P&L (1% risk, $100k): $0 (edge does not exist out-of-sample).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 80
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginal but suspicious. n=186 cell shows decent shrunk WR and holdout PF>2, yet PF=4.24 remains high enough to flag potential ml leakage or regime overfitting.
- 90d expected P&L (1% risk, $100k): $4,800 (conservative 0.8R per trade after 0.2% slippage on 2437 closes).
- Gate change: ALPHA_MIN_SCORE_CRYPTO = 62
- Confidence (1-5): 3

### ETF
- Real/noise verdict: Noise. n=9 closed; no edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 70
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise. n=33 closed; no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 65
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise. n=3 closed; zero edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise. n=16 closed; no proven edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 78
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise. n=8 closed; no edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none (CRYPTO is the least-bad but still requires further walk-forward validation). Demote per MUTATION_THREE_AXIS_PROTOCOL: EQUITY (clear leakage, kill immediately) followed by FOREX and COMMODITY.
