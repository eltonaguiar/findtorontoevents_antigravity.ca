# Pick Funnel Swarm Verdict — 2026-10-03 04:15 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261003T041509Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before per-class verdicts, three system-wide red flags that color everything below:

1. **`passed_high_conviction = 0` across every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on literally zero picks in 90 days. That means either (a) the gate is mis-wired / thresholds are unreachable given upstream score distributions, or (b) the dashboard is silently failing closed. Either way, the "HIGH CONVICTION" funnel stage is dead code right now. This is the single biggest finding in the dataset.
2. **`passed_verified_alpha` is 0 for 7 of 10 classes** and only non-zero for CRYPTO (1813), FOREX (3), FUTURES (1), MEME (1). The verified-alpha stage is effectively CRYPTO-only.
3. **Opened ≫ closed everywhere.** FOREX: 21,443 opened / 1,364 closed (6.4%). CRYPTO: 10,256 / 2,464 (24%). COMMODITY: 5,691 / 95 (1.7%). The "opened" number is almost certainly counting *signals emitted*, not *positions taken*, and the closed counts are the only ones that matter for edge. Any WR computed on `opened` is meaningless.

---

### COMMODITY
- **Real/noise verdict:** **Noise.** 94 decisive closes over 90d is far too thin to trust any cell. Best cell (`trust=UNK & rr=RR1.5-2.0 & fam=mean_reversion`) has n=20, holdout_n=2, `holdout_pass=false`, `bonferroni_pass=false`, wr_z=0.894. The `fam=mean_reversion & source=alpha_engine` cell (n=32, WR 62.5%, PF 3.97) has holdout_n=5 and fails Bonferroni. **This is exactly the shape of the falsified H-001 COT leakage** — mean-reversion + alpha_engine + tiny holdout + inflated PF. Treat as a leakage recurrence candidate, not an edge. Class-level WR 48.94% is a coin flip.
- **90d expected P&L (1% risk, $100k):** ~**-$1,200** (94 decisive trades × 1% × $100k × (0.4894 − 0.51) ≈ −$1.9k gross, minus ~$0.7k slippage on 94 round-trips at 0.05% notional). Effectively zero-to-negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise from current floor to **≥ 75** and require `rr >= 2.0`. The RR1.5–2.0 bucket is where the fake edge lives; force the scanner to demand wider R:R or drop the pick.
- **Confidence (1-5):** **1**

### EQUITY
- **Real/noise verdict:** **Almost certainly leakage / single-symbol artifact.** The "PROVEN" cell `trust=UNK & fam=mean_reversion & score_dec=S40` shows **n=68, wins=67, WR=98.53%, PF=218.3, wr_z=8.0**. A 98.5% WR with PF 218 is not a real equity edge — it is a data-integrity failure. Three independent tells: (i) all three "top edges" are the *same 68 trades* sliced three ways (trust/conf/dir are collinear here), (ii) `train_pf=99.05` and `holdout_pf=99.0` are suspiciously identical — classic sign of a capped/truncated PnL field or a stop that never triggers, (iii) `trust=UNK` dominating means the trust scorer isn't even seeing these. Class-level WR 69.09% on n=165 is the only number here I'd half-believe, and even that is likely inflated by the same 68 trades. **Do not trade this.**
- **90d expected P&L (1% risk, $100k):** If you naively trusted the headline WR: ~**+$28k**. Realistic (strip the 68 leakage trades, use residual n=97 at ~50% WR): **~-$500**. Report the honest number: **$0 to -$500**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — **raise to ≥ 70** AND add a hard `trust != UNK` requirement in `quality_gates.py`. The UNK-trust bucket is where the leakage lives; excluding it kills the fake edge and forces the trust scorer to actually run.
- **Confidence (1-5):** **1** (that the edge is real); **5** (that it's leakage)

### INDEX
- **Real/noise verdict:** **Noise.** n=5 decisive. WR 20% on 5 trades is statistically indistinguishable from 50%. No cells qualify (n<20). Nothing to say.
- **90d expected P&L (1% risk, $100k):** ~**-$1,500** (5 trades × 1% × $100k × (0.20 − 0.51) ≈ −$1.55k). Sample too small to act on either direction.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise to ≥ 80** and require `conf >= 0.70`. With only 1,801 scans and 8 closes, INDEX is barely being traded; better to gate hard and let it accumulate clean samples than to keep emitting.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **Noise, and the "best" cell is a textbook leakage pattern.** `trust=UNK & conf=C>=0.90 & fam=regime` shows n=54, WR 68.5%, PF 3.20 — but `train_pf=0.298` (train_n=17) vs `holdout_pf=14.149` (holdout_n=37). A 47× jump between train and holdout is not an edge, it's a regime shift or a timestamp bug. `holdout_pass=false`, `bonferroni_pass=false`. Class-level WR 44.55% on n=514 is the honest number: **losing**. The `regime_terminal` source is the only thing generating the "edge" and it's almost certainly look-ahead (regime labels computed with future data). **This is the FOREX `consensus`/regime cell you flagged — confirmed suspicious.**
- **90d expected P&L (1% risk, $100k):** ~**-$8,900** (514 decisive × 1% × $100k × (0.4455 − 0.51) ≈ −$3.3k, plus slippage ~$5.6k on 1,364 round-trips at 0.04% — FOREX spreads are the killer here). Net negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — **raise to ≥ 70** AND add `source != "regime_terminal"` to the exclusion list in `quality_gates.py` until the regime labeler is audited for look-ahead. The 21,850/22,807 pass rate (95.8%) is absurd — the gate is barely filtering.
- **Confidence (1-5):** **1**

### CRYPTO
- **Real/noise verdict:** **The only cell in the entire dataset that survives scrutiny — with caveats.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`: n=181, WR 72.4%, WR_shrunk 70.2%, PF 3.45, `train_pf=3.05` (n=143), `holdout_pf=5.51` (n=38), `holdout_pass=true`, `bonferroni_pass=true`, wr_z=6.02. Train and holdout are *both* strong and in the same direction — that's the opposite of the FOREX pattern. **Caveats:** (i) `trust=UNK` again — the trust scorer isn't running on these, (ii) the cell is defined by `conf` and `score_dec` bands that may be post-hoc selected, (iii) 181 trades over 90d in one conf band is plausible but check for single-symbol concentration (BTC/ETH dominance would inflate this). Class-level WR 45.53% on n=2,429 is *below* coin-flip — meaning the edge is entirely concentrated in this one cell and the rest of CRYPTO is bleeding. **This is a real, narrow edge sitting inside a losing class.**
- **90d expected P&L (1% risk, $100k):** If you had traded *only* the 181-trade cell: 181 × 1% × $100k × (0.724 − 0.51) ≈ **+$38.7k gross**, minus slippage ~$3.6k (181 × 2 × 0.10% × $100k) ≈ **+$35k net**. If you traded the whole class: 2,429 × 1% × $100k × (0.4553 − 0.51) ≈ −$13.3k, minus slippage ~$48k → **deeply negative**. The lesson: **the class is a loser; one cell is a winner.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **raise to ≥ 50** (matching `score_dec=S50`) AND add a hard filter in `hc_filter.js`: `if (source === 'alpha_engine' && conf >= 0.75 && conf < 0.80 && score >= 50) return HIGH_CONVICTION;` — i.e., **promote this specific cell to HC** since the generic HC gate is firing on zero. Also fix the HC gate itself: `score>=80` is unreachable given the observed score distribution; lower to `score>=50` with the conf/trust conditions intact.
- **Confidence (1-5):** **4** (this is the one to act on)

### FUTURES
- **Real/noise verdict:** **Noise.** n=18 decisive, WR 27.78%. No cells qualify. H-005 already killed the momentum inversion hypothesis; nothing here contradicts that.
- **90d expected P&L (1% risk, $100k):** ~**-$4,200** (18 × 1% × $100k × (0.278 − 0.51) ≈ −$4.2k). Small sample, but directionally bad.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to ≥ 80** and require `conf >= 0.70`. With 176 scans in 90d, FUTURES is barely a live class; gate hard until sample accumulates.
- **Confidence (1-5):** **1**

### ETF
- **Real/noise verdict:** **Noise.** n=9. Nothing to evaluate.
- **90d expected P&L (1% risk, $100k):** ~**-$2,600** (9 × 1% × $100k × (0.222 − 0.51) ≈ −$2.6k).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — **raise to ≥ 75**. 293/339 pass rate (86%) is too permissive for a class with 9 closes.
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **Noise, and a data-hygiene problem.** n=7, WR 0%. The fact that 1,384 scans land in UNKNOWN means the classifier is failing on ~5% of the universe. Fix the classifier before evaluating.
- **90d expected P&L (1% risk, $100k):** ~**-$3,600** (7 × 1% × $100k × (0.0 − 0.51) ≈ −$3.6k).
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` — **set to 999 (effectively block)** until the classifier routes these to a real class. Do not trade UNKNOWN.
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **Noise.** n=33, WR 42.42%. Best cell (`trust=UNK & dir=LONG & score_dec=S50`) has n=20, `holdout_pass=false`, `bonferroni_pass=false`, and `train_pf=0.65` vs `holdout_pf=34.3` — the same train/holdout inversion pattern as FOREX. Not real.
- **90d expected P&L (1% risk, $100k):** ~**-$2,500** (33 × 1% × $100k × (0.424 − 0.51) ≈ −$2.8k, plus small slippage).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **raise to ≥ 75**. 3/546 pass rate is already tight; the issue is the 513 opened vs 33 closed — investigate why 480 BOND signals never closed (stale positions?).
- **Confidence (1-5):** **1**

### MEME
- **Real/noise verdict:** **Noise.** n=4. Nothing to evaluate.
- **90d expected P&L (1% risk, $100k):** ~**-$1,000** (4 × 1% × $100k × (0.25 − 0.51) ≈ −$1.0k).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **raise to ≥ 80**. 11/23 pass rate on a 23-scan class is noise-fitting.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY: CRYPTO — but only the `alpha_engine` × `conf∈[0.75,0.80)` × `score_dec=S50` cell.** This is the only cell in the entire 90-day dataset that passes Bonferroni, has train and holdout PF in the same direction, and has n≥180. Expected edge: ~+$35k on a $100k account at 1% risk over 90d, *if* the cell holds. Before scaling: (1) verify no single-symbol concentration (BTC/ETH > 40% of the 181 trades would be a red flag), (2) confirm `trust=UNK` isn't hiding a broken trust scorer, (3) paper-trade for 2 weeks to confirm live WR ≥ 65%. Size at 0.5% risk initially, not 1%.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

- **FOREX** — the `regime_terminal` source is producing a train/holdout inversion (0.298 → 14.149) that is the signature of look-ahead. **Mutate axis 1 (source):** disable `regime_terminal`, re-run 90d, see if any residual edge survives. If not, kill. Do not scale.
- **EQUITY** — the 98.5% WR / PF 218 cell is leakage. **Mutate axis 2 (trust):** require `trust != UNK` and re-run. If the class WR collapses to ~50%, the "edge" was entirely the UNK bucket and the class should be demoted to paper-only.
- **COMMODITY** — H-001 and H-036 already killed the two obvious hypotheses; the residual mean-reversion cell is the same shape as H-001. **Mutate axis 3 (family):** drop `mean_reversion` from COMMODITY entirely and see if anything else survives. If not, kill.

**Do not scale:** INDEX, FUTURES, ETF, BOND, MEME, UNKNOWN — all have n<35 decisive and no Bonferroni-passing cell. They are not classes with edges; they are classes with samples too small to have edges.

**Fix before anything else:** the `passed_high_conviction = 0` bug. A gate that fires on zero picks in 90 days is not a gate, it's a bug. Either the thresholds are unreachable or the wiring is broken. Until that's fixed, the "HIGH CONVICTION" label on the dashboard is meaningless and the CRYPTO cell above cannot be promoted through the normal funnel.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: Noise/leakage — 98.5% WR on n=68 with PF=218 is statistically impossible in live trading; identical cells across trust/conf/dir point to single-symbol concentration or data bug.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 75.
- Confidence (1-5): 5

### CRYPTO
- Real/noise verdict: Marginally real — n=180+, WR_shrunk=70.5, PF=3.45 with holdout_pass and bonferroni_pass is credible but PF remains high enough to warrant ongoing monitoring for alpha_engine source concentration.
- 90d expected P&L (1% risk, $100k): ~$8,200 (181 trades × ~1.36% avg_pnl at 1% risk, 0.2% slippage).
- Gate change: HC_MIN_CONF = 0.78.
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise — no PROVEN cells; best_pf_overall cells fail holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65.
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise — no PROVEN cells; best_pf_overall cells fail holdout.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_MIN_TRUST = 70.
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise — no PROVEN cells; best_pf_overall cells fail holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 60.
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise — n_closed=5, no edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None (disable scanner).
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise — n_closed=18, no edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None (disable scanner).
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise — n_closed=9, no edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None (disable scanner).
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise — n_closed=7, no edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None (disable scanner).
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise — n_closed=4, no edges.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: None (disable scanner).
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically defensible PROVEN cells). Demote EQUITY immediately per MUTATION_THREE_AXIS_PROTOCOL.md — its metrics indicate leakage recurrence rather than edge. All other classes have no actionable edge; leave at current gates or disable.
