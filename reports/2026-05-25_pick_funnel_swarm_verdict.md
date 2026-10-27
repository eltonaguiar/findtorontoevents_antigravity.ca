# Pick Funnel Swarm Verdict — 2026-10-27 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261027T040958Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on *zero* trades in 90 days. That is not a filter — that is a dead gate. Whatever edge exists is *not* being surfaced by the HC funnel.
2. **`passed_verified_alpha` is 0 for 8 of 10 classes.** Only CRYPTO (2062) and a trickle of FOREX/FUTURES/MEME pass. The "verified alpha" stage is effectively a CRYPTO-only gate.
3. **The funnel is inverted.** `opened` ≈ `scanned` for most classes (EQUITY 5690/5823, FOREX 23256/24562, COMMODITY 5904/5952). The "smart" gate is not gating — it is a rubber stamp. Only CRYPTO (3649/12963) and EQUITY (228/5823) actually filter.

That inversion is the single most important finding. It means the "edges" below are being computed on a population that was *never actually filtered*, so any cell that looks good is a survivor of the raw scanner, not of the gate.

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE.** The `conf=C<0.60 & fam=mean_reversion` cell (n=63, WR=98.41%, PF=170.0) is a textbook leakage signature. PF=170 with avg_pnl=1.53% is mathematically impossible for a real mean-reversion strategy — it implies ~62 wins of +1.5% against 1 loss of ~-0.005%. That is not a strategy, that is a **stop-loss that never triggers / a take-profit that always fills / a look-ahead on the exit bar**. The train/holdout split (90.5 / 99.0) is *too* stable — real edges decay on holdout; this one got *better*, which is the classic fingerprint of a leak that persists across the split because the leak is in the exit logic, not the entry. Also note `trust=UNK` — the cell is defined by *missing* trust data, which is a data-quality artifact, not a signal. **Reject. Do not trade.** Flag as leakage recurrence per H-001 pattern (look-ahead in exit/bar timing).
- **90d expected P&L (1% risk, $100k): $0** — do not deploy. If you *did* deploy at face value you'd "expect" ~$96k on 63 trades, which is the tell that it's fake.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — currently the gate passes 228/5823 (3.9%) but `opened` is 5690, meaning the gate is bypassed downstream. Set the *downstream* open gate to require `passed_smart == True` (i.e., wire the smart flag into the open path, not just the dashboard). Concretely: `SMART_PICKS_MIN_SCORE_EQUITY = 55` **and** enforce it at open, not just display.
- **Confidence (1-5): 1** (the edge is fake; the gate is broken).

### COMMODITY
- **Real/noise verdict: NOISE.** No PROVEN cells. Best PF overall is 1.93 (n=31, WR_shrunk 54.9%) but **holdout_pf=1.16, holdout_pass=false, bonferroni_pass=false**. That is a coin flip with a lucky train window. The `trust=UNK` again — same data-quality artifact. Given H-001 (COT leakage) and H-036 (inventory rejected) are already in the registry, this class has a documented history of fake edges; treat the 1.93 PF as the *same* family of artifact until proven otherwise. WR 60.4% on n=48 closed is within noise (95% CI roughly 45–74%).
- **90d expected P&L (1% risk, $100k): $0** — no deployable edge. (If you forced the 1.93 PF cell: ~31 trades × 1% × 0.69% avg = ~$2.1k, but holdout says it's ~0.)
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — the gate passes 3665/5952 (62%), which is not a gate. Raise to `SMART_PICKS_MIN_SCORE_COMMODITY = 65` to cut the pass rate to roughly the EQUITY level (~4–10%) and force the class to actually discriminate.
- **Confidence (1-5): 1.**

### FOREX
- **Real/noise verdict: NOISE / LEAKAGE.** The `conf=C>=0.90 & dir=LONG & source=regime_terminal` cell (n=28, WR=85.7%, PF=8.89) **fails holdout** (`holdout_pass=false`, `train_n=4`, `train_pf=0.0`). train_n=4 means the "train" split is 4 trades — the train/holdout split is meaningless. `bonferroni_pass=true` is a false comfort: Bonferroni on a cell with n=28 and a 4-trade train is not a real multiple-testing correction, it's a p-value on a tiny sample. The `consensus`/`regime_terminal` source is exactly the kind of single-source concentration you flagged. **Reject.** Also: FOREX overall WR is 43.07% on 534 decisive — the class is a net loser; the "edge" cell is a 28-trade island inside a 534-trade ocean of losses.
- **90d expected P&L (1% risk, $100k): $0** — do not deploy. (Face value: 28 × 1% × 0.59% = ~$1.65k, but holdout says negative.)
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — gate passes 23748/24562 (96.7%). This is the worst offender. Set `SMART_PICKS_MIN_SCORE_FOREX = 70` to cut pass rate to <10% and stop the class from opening 23k trades on a 43% WR.
- **Confidence (1-5): 1.**

### CRYPTO
- **Real/noise verdict: MOSTLY REAL, with one caveat.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the only cell in the entire dataset that passes **all** robustness checks: n=183, WR_shrunk=75.86%, PF=4.18, **holdout_pf=2.675 (holdout_pass=true)**, wr_z=7.76, bonferroni_pass=true. Holdout decay from 6.06 → 2.68 is *healthy* (real edges decay). This is the one edge I'd believe. **Caveat:** the three "PROVEN" cells are the *same 183 trades* sliced three ways (conf+score+source, +trust, +dir) — they are not three independent edges, they are one edge with redundant dimension labels. Do not triple-count. Also `trust=UNK` appears again — the edge is defined partly by missing trust, so verify the trust field isn't systematically null for alpha_engine (if it is, the "trust" dimension is a no-op and the real edge is just `conf 0.75-0.80 + score_dec S50 + alpha_engine`).
- **90d expected P&L (1% risk, $100k):** 183 trades × 1% risk × avg_pnl 1.5769% = **~$2,886** at face value. Apply holdout haircut (use holdout_pf 2.675 vs train 6.06 → ~44% of train edge survives): **~$1,270 realistic**. With 0.1% slippage per side on 183 trades (~$366 drag): **~$900 net**. Range: **$900–$2,900**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — currently passes 3649/12963 (28%). The edge lives at `conf 0.75-0.80` specifically, which is *below* the HC gate's 0.75 floor but the HC gate also requires score>=80 and trust>=60, and trust is UNK → HC never fires. **Fix the HC gate, not the smart gate:** in `hc_filter.js`, change `trust >= 60` to `trust >= 60 || trust === 'UNK'` (or better, backfill trust for alpha_engine so UNK disappears). That single change would let the one real edge through the HC funnel. Alternatively set `SMART_PICKS_MIN_SCORE_CRYPTO = 60` and add a `conf` band filter `0.75 <= conf < 0.80`.
- **Confidence (1-5): 3** (real but thin, single-source, and the HC gate is blocking it).

### ETF
- **Real/noise verdict: NOISE.** n=10 closed, WR=20%. No PROVEN cells. Statistically meaningless.
- **90d expected P&L (1% risk, $100k): $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — passes 299/354 (84%). Raise to `SMART_PICKS_MIN_SCORE_ETF = 70`; or better, **disable ETF opening entirely** until n>=50 closed (sample too small to gate).
- **Confidence (1-5): 1.**

### BOND
- **Real/noise verdict: NOISE.** `passed_smart = 0` — the smart gate rejects 100% of bonds, yet `opened = 664`. The gate is being bypassed. WR 38.2% on n=34. No edge.
- **90d expected P&L (1% risk, $100k): $0** (negative if traded: 34 × 1% × ~-0.3% ≈ -$100).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — it's already 0-pass; the bug is that `opened` ignores it. **Enforce `passed_smart` at open** (same fix as EQUITY). If you must set a constant: `SMART_PICKS_MIN_SCORE_BOND = 60` and wire it to the open path.
- **Confidence (1-5): 1.**

### UNKNOWN
- **Real/noise verdict: NOISE / DATA BUG.** n=3 closed, WR=0%. This class should not exist — it's a classification failure upstream. 1391 opened, 3 closed means 1388 trades are stuck open (or never resolved). That's a **reconciliation bug**, not a strategy.
- **90d expected P&L (1% risk, $100k): $0.**
- **Gate change:** Not a gate — fix the classifier so `UNKNOWN` is empty. If forced: `SMART_PICKS_MIN_SCORE_UNKNOWN = 999` (block all).
- **Confidence (1-5): 1.**

### INDEX
- **Real/noise verdict: NOISE.** n=4 closed, WR=25%. No PROVEN cells. Meaningless.
- **90d expected P&L (1% risk, $100k): $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX = 70` (currently passes 1404/1793 = 78%, not a gate).
- **Confidence (1-5): 1.**

### FUTURES
- **Real/noise verdict: NOISE.** n=16 closed, WR=43.75%. No PROVEN cells. H-005 already killed the momentum inversion. Nothing here.
- **90d expected P&L (1% risk, $100k): $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES = 65` (passes 149/201 = 74%).
- **Confidence (1-5): 1.**

### MEME
- **Real/noise verdict: NOISE.** n=8 closed, WR=25%. No PROVEN cells. Sample too small to say anything.
- **90d expected P&L (1% risk, $100k): $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME = 75` (passes 13/29 = 45%; tighten).
- **Confidence (1-5): 1.**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the one cell.**
The `conf 0.75–0.80 & score_dec S50 & source=alpha_engine` cell is the only signal in the entire 90-day dataset that survives holdout, Bonferroni, and shrinkage. It is one edge, not three (the three "PROVEN" rows are the same 183 trades). Realistic 90d P&L at 1% risk / $100k: **~$900–$2,900**, and I'd size at half-Kelly (0.5% risk) until the next 90d confirms holdout_pf stays >2.0. **Do not scale the other CRYPTO cells** — they're the same trades relabeled.

**Demote per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill): FOREX.**
FOREX is the clearest demote: 23,256 opened on a 43.07% WR, the "edge" cell fails holdout with a 4-trade train, and the smart gate passes 96.7% of scans. Mutate first (per protocol): (1) raise `SMART_PICKS_MIN_SCORE_FOREX` to 70, (2) enforce `passed_smart` at open, (3) re-run 30d. If WR stays <48% after mutation, kill. **Do not kill yet** — the protocol says mutate before kill, and the gate is so broken that the class has never actually been tested with a real filter.

**Second demote: EQUITY.** The 98.4% WR / PF=170 cell is leakage, not edge. Mutate: enforce `passed_smart` at open (currently 228 pass but 5690 open — the gate is bypassed), then re-audit. If the mean_reversion cell collapses to ~50% WR after the exit-logic leak is fixed, kill the family.

**Structural fixes that matter more than any single constant:**
1. **`passed_high_conviction = 0` everywhere is a P0 bug.** The HC gate is dead. Either `trust` is systematically UNK (backfill it) or the `score>=80` floor is unreachable (lower to 70 and re-measure). A gate that fires zero times in 90 days is not a gate.
2. **`opened ≈ scanned` for 7 of 10 classes** means the smart gate is display-only. Wire `passed_smart` into the open path. This one change would have prevented ~30k of the ~40k trades opened in the last 90 days.
3. **`UNKNOWN` class with 1391 opened / 3 closed** is a reconciliation bug — 1388 trades are unaccounted for. Fix before trusting any WR number.

**Brutal summary:** 9 of 10 asset classes have no edge. 1 (CRYPTO) has one real, thin, single-source edge worth ~$1–3k per 90d at 1% risk. The funnel is inverted (gates don't gate), the HC gate is dead (0 fires), and the two "best" cells (EQUITY PF=170, FOREX PF=8.9) are leakage and tiny-sample artifacts respectively. Do not deploy capital on anything except the CRYPTO cell, and fix the gate wiring before the next audit or you'll keep re-discovering the same fake edges.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: noise/leakage — 98% WR on n=63 mean_reversion is statistically impossible without single-symbol concentration or look-ahead; PF=170 is fabrication-level
- 90d expected P&L (1% risk, $100k): $0 (edge invalid)
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: noise — no proven cells; best_pf cells fail bonferroni and holdout
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 80
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise — all best_pf cells fail holdout_pass; no proven cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF = 0.85
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: real but narrow — n=183, WR_shrunk=75.86, PF=4.18 with holdout_pass=true and bonferroni_pass=true; no obvious leakage flags
- 90d expected P&L (1% risk, $100k): $12400 (183 trades × 1% risk × ~1.58% avg edge after 0.2% slippage)
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50
- Confidence (1-5): 4

### ETF
- Real/noise verdict: noise — n=10 total, no proven cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 70
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise — zero passed_smart, no proven cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 60
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise — n=3, zero wins
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 90
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise — n=4, no proven cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 75
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise — n=16, no proven cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 70
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise — n=8, no proven cells
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 85
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically credible edge). Demote EQUITY and COMMODITY per MUTATION_THREE_AXIS_PROTOCOL (mutate filters before any further capital allocation). All other classes have no usable edge.
