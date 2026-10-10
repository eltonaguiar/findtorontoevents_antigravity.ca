# Pick Funnel Swarm Verdict — 2026-10-10 04:11 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261010T041139Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on literally zero picks across 90 days and ~58k scans. Either the gate is mis-wired, or the scoring pipeline never produces a pick that satisfies all three simultaneously. This is the single biggest finding in the dataset — the "HIGH CONVICTION" funnel is a dead branch.
2. **`passed_verified_alpha` is 0 for everything except CRYPTO (1927) and a rounding-error trickle elsewhere.** The verified-alpha gate is effectively CRYPTO-only.
3. **`opened` >> `passed_smart` in most classes** (EQUITY 5609 opened vs 231 passed_smart; FOREX 22333 vs 22805 — ok that one's fine; BOND 532 vs 3; UNKNOWN 1375 vs 161). This means the "Smart" gate is *not* the gate that actually controls what gets opened. Something upstream is bypassing it. Any edge analysis on `passed_smart` cells is therefore analyzing a filter that isn't binding.

---

### EQUITY
- **Real/noise verdict: NOISE / LEAKAGE.** The "PROVEN" cell `fam=mean_reversion & score_dec=S40` shows WR=98.48% (65/66), PF=218.6, holdout PF=99.0. A PF of 218 is not a strategy — it is a data artifact. Three red flags: (i) `trust=UNK` on 100% of the cell, meaning trust scoring never ran; (ii) `conf=C<0.60` — the *lowest* confidence bucket producing the *highest* WR is the classic signature of a look-ahead or a mislabeled outcome; (iii) n=66 with 65 wins and avg_pnl=+1.32% is inconsistent with any real mean-reversion distribution (you'd expect fat left tails). This is almost certainly the same class of bug as H-001 (COT look-ahead): outcome labels computed with future information, or a stop/target inversion. **Do not trade this.** Also note: 5609 opened vs 231 passed_smart — the gate isn't binding, so the 151 closed trades are a non-random subsample.
- **90d expected P&L (1% risk, $100k): $0** — refuse to size a leaked cell. If forced to mark-to-model the *reported* numbers: 151 trades × 1% × avg +1.32% ≈ **+$1,990**, but this is fiction.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current value to **65** AND add a hard `trust != UNK` requirement in `quality_gates.py`. The UNK-trust cells are where the leakage lives.
- **Confidence (1-5): 1**

### COMMODITY
- **Real/noise verdict: NOISE (and a known-falsified family).** `top_edges_proven` is empty. Best PF cell is `rr>=2.0 & source=alpha_engine`, n=24, WR_shrunk=65.9%, PF=7.47, **bonferroni_pass=false**, train_n=11. n=11 in train is not a train set, it's an anecdote. This is the same shape as H-001 (COT) and H-036 (inventory) — small-n commodity cells that look great until timestamps are fixed. Treat as a potential leakage recurrence, not an edge.
- **90d expected P&L (1% risk, $100k): $0** (n=80 closed total; even at reported 55% WR the CI spans zero).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **70**, and require `source != alpha_engine` OR `rr >= 2.5` (the current RR>=2.0 threshold is where the false positives cluster).
- **Confidence (1-5): 1**

### FOREX
- **Real/noise verdict: NOISE, and the funnel is broken.** 22,805 of 23,721 scans "pass smart" — a 96% pass rate is not a filter, it's a pass-through. Overall WR 41.95% on n=1388 closed is a *losing* book. The best cell (`conf>=0.90 & fam=regime`, n=54, PF=3.20) has **train_pf=0.298** and **holdout_pf=14.15** — that is the textbook signature of regime-split overfitting, not edge. `holdout_pass=false`, `bonferroni_pass=false`. The `consensus`/`regime_terminal` source you flagged: yes, suspicious — a 0.30→14.15 PF flip across a 17/37 split is not a strategy, it's a coin that landed heads 37 times.
- **90d expected P&L (1% risk, $100k): −$4,200** (1388 closed × 1% × −0.30% avg, using the reported 41.95% WR and typical 1:1.2 RR). This class is a net loser as currently gated.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **75** (from whatever it is; the 96% pass rate proves it's too low) AND add `min_confidence=0.80` to the FOREX branch. The regime family should be quarantined pending a walk-forward re-test.
- **Confidence (1-5): 1**

### CRYPTO
- **Real/noise verdict: WEAK BUT PLAUSIBLY REAL — the only class with a defensible cell.** `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine`: n=175, WR_shrunk=70.3%, PF=3.46, **holdout_pass=true** (holdout PF=2.97, n=43), **bonferroni_pass=true**, wr_z=5.97. This is the only cell in the entire report that survives multiple-testing correction *and* holds out. Caveats: (i) `trust=UNK` on the top cell — trust scoring isn't running for CRYPTO either; (ii) the cell is defined by `score_dec=S50`, a decile bucket, which is fragile to score-distribution drift; (iii) 1927 verified-alpha picks but 0 HC picks means the HC gate is mis-tuned for CRYPTO specifically. The `ml` source you flagged isn't in the top cells shown — if it's producing PF>5 elsewhere, treat it as leakage until proven otherwise.
- **90d expected P&L (1% risk, $100k): +$8,900** on the proven cell alone (175 trades × 1% × avg +1.38% × 0.70 shrinkage haircut ≈ +$8,900). Full-class realistic estimate: **+$3,000 to +$6,000** after slippage and the 45% WR drag from non-cell trades.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower** to **50** (to capture the S50 decile explicitly) AND add `min_confidence=0.75` + `source=alpha_engine` as a compound requirement. This is the one place where *loosening* the score floor while *tightening* the source/conf gate is correct.
- **Confidence (1-5): 3**

### ETF
- **Real/noise verdict: NOISE.** n=9 closed, WR=22.2%. No cells. Not enough data to say anything.
- **90d expected P&L (1% risk, $100k): −$700** (9 trades × 1% × −0.78% avg).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **80** (effectively disable until n>=50).
- **Confidence (1-5): 1**

### FUTURES
- **Real/noise verdict: NOISE, and H-005 already killed the family.** n=14 closed, WR=35.7%. `futures_momentum` is formally rejected. Do not re-derive.
- **90d expected P&L (1% risk, $100k): −$900** (14 × 1% × −0.64%).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **85** (disable).
- **Confidence (1-5): 1**

### UNKNOWN
- **Real/noise verdict: NOISE / DATA HYGIENE FAILURE.** 1380 scanned, 1375 opened, 5 closed, 0 wins. This bucket should not exist. Every pick here is a routing bug.
- **90d expected P&L (1% risk, $100k): −$500** (5 × 1% × −1.0%).
- **Gate change:** Add a hard reject in `quality_gates.py`: `if asset_class == "UNKNOWN": return False`. No constant to tune — this is a routing fix.
- **Confidence (1-5): 1**

### BOND
- **Real/noise verdict: NOISE.** n=30, WR=43.3%. 3 passed_smart out of 562 scanned but 532 opened — the gate is bypassed entirely.
- **90d expected P&L (1% risk, $100k): −$400** (30 × 1% × −0.13%).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — raise to **80**.
- **Confidence (1-5): 1**

### INDEX
- **Real/noise verdict: NOISE.** n=5 closed. 1593 passed_smart out of 1901 scanned (84% pass rate — not a filter).
- **90d expected P&L (1% risk, $100k): −$600** (5 × 1% × −1.2%).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **75**.
- **Confidence (1-5): 1**

### MEME
- **Real/noise verdict: NOISE.** n=4. Nothing to say.
- **90d expected P&L (1% risk, $100k): −$300** (4 × 1% × −0.75%).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **90** (disable).
- **Confidence (1-5): 1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only, and only the `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell.** It is the only cell in the entire 90-day report that passes Bonferroni, holds out (PF 2.97 on n=43), and has a plausible mechanism (mid-confidence alpha_engine signals in a specific score decile). Size at 0.5% risk (not 1%) for the first 30 days to confirm live WR tracks the 70% shrunk estimate. Expected: **+$3k–$6k over 90d at $100k notional.**

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **FOREX** — the 96% smart-pass rate and 41.95% WR make this the worst offender. Mutate the score floor and confidence gate before killing; the regime family may have a real signal buried under a broken gate.
- **EQUITY** — the 98% WR / PF 218 cell is a leakage recurrence (same shape as H-001). Mutate: fix trust scoring (currently UNK on the winning cell), then re-run. If WR drops to ~55%, the family is salvageable; if it drops to ~50%, kill.
- **COMMODITY** — H-001 and H-036 already killed the two main families. Mutate the RR gate (2.0 → 2.5) and re-test; if no cell survives Bonferroni, kill.

**Do NOT scale:** ETF, FUTURES, UNKNOWN, BOND, INDEX, MEME — all have n<30 closed and no surviving cells.

**The single highest-leverage fix is not a gate constant — it's the HC gate.** `passed_high_conviction = 0` across 58k scans means the entire "HIGH CONVICTION" product surface is empty. Before tuning any per-class floor, verify that `hc_filter.js` is actually being invoked server-side and that `score>=80, conf>=0.75, trust>=60` is achievable by *any* pick in the pipeline. If trust scoring returns UNK for most picks (as the CRYPTO and EQUITY cells suggest), the `trust>=60` clause is unsatisfiable and the HC gate is structurally dead. Fix that first; every per-class tuning below it is secondary.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Possible signal but PF suspiciously high for live alpha_engine output; holdout passes but n=175 concentrated on narrow conf/score band risks overfitting or single-exchange concentration.
- 90d expected P&L (1% risk, $100k): $2,420 (175 trades at ~1.38% avg edge, 1% risk, 0.15% slippage, 0.10% commission).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 55
- Confidence (1-5): 2

### EQUITY
- Real/noise verdict: Noise/leakage — 98.5% WR and PF=218 on n=66 is statistically impossible in live equity without data error or single-symbol concentration.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 70
- Confidence (1-5): 1

### COMMODITY
- Real/noise verdict: Noise — no proven cells; best_pf_overall fails Bonferroni and shows train/holdout instability.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 65
- Confidence (1-5): 1

### FOREX
- Real/noise verdict: Noise — no proven cells; regime cells fail holdout and show classic consensus leakage pattern.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: HC_MIN_CONF_FOREX = 0.92
- Confidence (1-5): 1

### ETF
- Real/noise verdict: Noise — n=9 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: Noise — n=14 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 1

### BOND
- Real/noise verdict: Noise — n=30 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 70
- Confidence (1-5): 1

### INDEX
- Real/noise verdict: Noise — n=5 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 1

### UNKNOWN
- Real/noise verdict: Noise — n=5 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 1

### MEME
- Real/noise verdict: Noise — n=4 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none (no class meets stable, leakage-free criteria with sufficient n).  
Demote per MUTATION_THREE_AXIS_PROTOCOL.md: EQUITY and FOREX first (clear leakage signatures and zero holdout-proven cells); follow with ETF/INDEX/MEME/UNKNOWN for zero activity.
