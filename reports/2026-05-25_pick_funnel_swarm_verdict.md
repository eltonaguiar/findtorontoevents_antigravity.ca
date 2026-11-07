# Pick Funnel Swarm Verdict — 2026-11-07 04:06 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261107T040623Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below and I want them stated up front because they change how you should read every number:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80 & conf>=0.75 & trust>=60`) is *never* firing. The "top edges" you're being shown are **not** HC-gated picks — they're the raw `passed_smart` / `passed_verified_alpha` population. So any "edge" here is an edge in the *unfiltered* funnel, not the product you're actually shipping to users. That's a critical distinction.
2. **The funnel is inverted.** `opened` >> `passed_smart` in most classes (CRYPTO 10,317 opened vs 3,769 passed_smart; FOREX 22,926 vs 23,501; EQUITY 5,856 vs 234). That means the "smart" gate is *not* the binding constraint on what gets opened — something upstream is opening trades that never passed the smart floor. The gate you're auditing is largely decorative.
3. **The "PROVEN" cells are almost all the same trade.** CRYPTO's three "proven" cells are identical (n=241, 157 wins, PF 2.28) — they're the same 241 trades sliced three ways. EQUITY's three are the same 61 trades. This is not three independent edges; it's one cell reported three times. Treat each class as having **at most one** candidate edge.

---

### CRYPTO
- **Real/noise verdict:** The single candidate cell is `conf=C0.75-0.80 & source=alpha_engine` (n=241, WR 65.15%, shrunk 63.98%, PF 2.28, holdout PF 1.40, wr_z 4.70, Bonferroni pass). This is the **only** cell in the entire dataset that survives holdout + multiple-testing correction with a plausible (not absurd) PF. It is *probably real but fragile*: holdout PF 1.40 vs train 3.55 is a 60% degradation — classic overfit-to-train signature, and the holdout is only 131 trades. The `trust=UNK` tag on the winning cell is a red flag: the edge lives in picks whose trust score is *unknown*, i.e. the trust gate is not selecting them. **No `ml` cell appears in the proven list** — the prompt's worry about "CRYPTO ml cells with suspiciously high PF" is not supported by this data; the high-PF cells here are `alpha_engine`, not `ml`. Do not invent an ml edge. The 46% overall WR with 2,400 closed is the honest base rate; the 65% cell is a real sub-population but small.
- **90d expected P&L (1% risk, $100k):** Assume 1% = $1,000 risk/trade, avg win ≈ +1.05% of notional on winners, avg loss ≈ −1.0% (R:R ~1:1 implied by PF 2.28 at 65% WR). Per-trade EV ≈ 0.65×(+$1,050) − 0.35×(−$1,000) ≈ **+$332/trade**. Over 241 trades ≈ **+$80k gross**, minus slippage/fees at 0.05% round-trip on $100k = $50/trade × 241 = −$12k, minus the 40% holdout degradation haircut → realistic **+$35k–$45k**. I'd size to the holdout PF, not train: **~$40k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — but the real fix is upstream. The binding problem is `opened` (10,317) >> `passed_smart` (3,769). Set the open-gate to *require* `passed_smart` (currently it doesn't). If forced to name one constant: raise `SMART_PICKS_MIN_SCORE_CRYPTO` from its current value to **78** and add a hard `conf>=0.75` requirement at open time so the 65%-WR cell is the *only* thing that opens. That alone cuts opened from 10,317 → ~241 and lifts blended WR from 46% toward 65%.
- **Confidence (1-5):** 3 — real but train/holdout gap and UNK-trust tag keep it from a 4.

### COMMODITY
- **Real/noise verdict:** **Noise / not proven.** n_closed=40, no cell passes holdout (`holdout_pass: false` on all three), no Bonferroni pass, wr_z 1.3 max. The 67.5% WR on 40 trades is exactly the kind of small-n mirage that dies on holdout (holdout PF 1.14 and 0.65). And note H-001: the last time COMMODITY looked good it was COT look-ahead leakage with 85% cotton concentration. The `trust=UNK & dir=LONG & source=alpha_engine` cell (n=29) is the same shape as the falsified pattern — **flag as potential leakage recurrence**, do not trade.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not size. If you forced it: 29 trades × EV ≈ +$150 = +$4.3k gross, but holdout PF < 1.2 and n=29 → expected value indistinguishable from zero after slippage. **$0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **85** (effectively disable until n≥100 closed with holdout pass). The class has 5,985 scanned but only 40 closed; the gate isn't the problem, the *exit/close* pipeline is (5,945 opened, 40 closed = 0.7% close rate). Fix close-rate before touching the score gate.
- **Confidence (1-5):** 1.

### INDEX
- **Real/noise verdict:** **No edge, no sample.** n_closed=1. 100% WR on one trade is meaningless. 2,015 opened, 1 closed — the close pipeline is broken for INDEX. Nothing to evaluate.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1, not estimable).
- **Gate change:** None on score — fix the close pipeline first. If forced: `SMART_PICKS_MIN_SCORE_INDEX` = **80** and require `passed_smart` at open (currently 2,015 opened vs 1,590 passed_smart — 425 opened without passing).
- **Confidence (1-5):** 1.

### FOREX
- **Real/noise verdict:** **Noise.** `top_edges_proven: []` — zero cells pass. The best-PF cell (`multi_asset_copytrader`, n=28, PF 5.22) has `holdout_n: 2` and `holdout_pass: false` and `bonferroni_pass: false`. A PF of 5.2 on 28 trades with a 2-trade holdout is **not an edge, it's a rounding artifact**. The prompt's worry about "FOREX consensus cells with suspiciously high PF" — the high-PF cell here is `multi_asset_copytrader`, not `consensus`, and it's clearly noise. Overall WR 51.16% on 1,245 closed is a coin flip minus costs = negative expectancy. 22,926 opened vs 23,501 passed_smart vs 3 verified_alpha — the verified-alpha gate is essentially off.
- **90d expected P&L (1% risk, $100k):** **Negative.** 51.16% WR at ~1:1 R:R with 0.05% slippage → EV ≈ −$100/trade × 1,245 ≈ **−$125k** if you traded the whole book. Do not trade.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **82** and, critically, require `passed_verified_alpha` at open (currently 22,926 opened vs 3 verified — the verified gate is bypassed). This is the single biggest leak in the funnel.
- **Confidence (1-5):** 1.

### EQUITY
- **Real/noise verdict:** **Almost certainly leakage / look-ahead.** The cell `conf=C<0.60 & fam=mean_reversion` shows n=61, WR 98.36%, **PF 171.5**, holdout PF 99.0, wr_z 7.55, Bonferroni pass. A PF of 171 is not a trading edge — it is a data-integrity bug. 60/61 wins with avg_pnl +1.59% and a *low* confidence band (<0.60) is the signature of **look-ahead in the mean-reversion exit** (e.g., exit priced at a bar the strategy couldn't have seen, or a fill assumption that captures the reversion perfectly). The fact that it's `conf=C<0.60` — the *lowest* confidence bucket — producing the *highest* PF is the tell: the model is least sure and most right, which only happens when the label leaks. **Flag as leakage recurrence.** Do not trade. This is the same failure mode as H-001 (COT look-ahead) and H-009/H-011 (killed equity options signals).
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** If the PF were real it'd be absurd (+$1.5M+), which is itself proof it's not real. **$0.**
- **Gate change:** Not a score gate — **kill the mean_reversion family in EQUITY** until the exit-price timestamp is audited. If forced to a constant: `SMART_PICKS_MIN_SCORE_EQUITY` = **80** and add `fam != mean_reversion` to the open filter. Also note 5,856 opened vs 234 passed_smart — 96% of equity opens bypass the smart gate.
- **Confidence (1-5):** 1 (that it's leakage — high confidence it's *not* a real edge).

### ETF
- **Real/noise verdict:** **No edge, tiny sample.** n_closed=9, WR 11.11% (1 win, 8 losses). 288 passed_smart but 327 opened and only 9 closed. Nothing to salvage; the 11% WR is a small-n disaster, not a signal.
- **90d expected P&L (1% risk, $100k):** **Negative** if traded (−$7k on 9 trades at 1% risk). **$0** recommended.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` = **85** (disable) until close-rate fixed.
- **Confidence (1-5):** 1.

### FUTURES
- **Real/noise verdict:** **Noise.** n_closed=16, WR 37.5%, no proven cells, no best-PF cells. H-005 already falsified futures momentum inversion. Nothing here.
- **90d expected P&L (1% risk, $100k):** **Negative** (−$4k on 16 trades). **$0** recommended.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` = **85** (disable).
- **Confidence (1-5):** 1.

### MEME
- **Real/noise verdict:** **Noise.** n_closed=9, WR 33.33%, no proven cells. 27 scanned total — not a class, a rounding error.
- **90d expected P&L (1% risk, $100k):** **$0** (n=9, not estimable; negative if traded).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` = **90** (effectively off).
- **Confidence (1-5):** 1.

### BOND
- **Real/noise verdict:** **Noise / negative.** n_closed=31, WR 38.71%, no proven cells. 978 scanned, 1 passed_smart, 947 opened — the smart gate is bypassed entirely and the class loses.
- **90d expected P&L (1% risk, $100k):** **Negative** (−$7k on 31 trades). **$0** recommended.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` = **85** (disable) and require `passed_smart` at open.
- **Confidence (1-5):** 1.

### UNKNOWN
- **Real/noise verdict:** **Noise.** n_closed=3, WR 0%. 1,337 scanned, 132 passed_smart, 1,334 opened — the "UNKNOWN" bucket is where unclassified picks go to die. This is a **data-hygiene bug**, not a class.
- **90d expected P&L (1% risk, $100k):** **$0** (n=3).
- **Gate change:** Not a score gate — **route UNKNOWN to a quarantine queue** and block open. If forced: `SMART_PICKS_MIN_SCORE_UNKNOWN` = **999** (hard block).
- **Confidence (1-5):** 1.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only — and only the single `conf=C0.75-0.80 & source=alpha_engine` cell, at reduced size (~$40k expected 90d P&L, not the $80k gross).** It is the only cell in the entire dataset that survives holdout + Bonferroni with a plausible PF (2.28, holdout 1.40). Everything else is either noise (FOREX, COMMODITY, FUTURES, MEME, BOND, ETF, INDEX, UNKNOWN) or leakage (EQUITY mean_reversion PF 171). Do not scale CRYPTO broadly — the 46% blended WR on 2,400 closed is the honest number; the 65% cell is a narrow sub-population.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **EQUITY** — demote to *mutate*: the mean_reversion family must be quarantined and its exit-price timestamp audited before any capital. PF 171 is a bug, not an edge. This is the highest-priority integrity fix in the whole funnel.
- **FOREX** — demote to *mutate*: 22,926 opened vs 3 verified_alpha means the verified gate is bypassed; fix the open-gate wiring, then re-measure. 51% WR is a coin flip minus costs.
- **COMMODITY** — demote to *mutate*: close-rate is 0.7% (40/5,945); the class can't be evaluated until exits fire. Flag the `trust=UNK & dir=LONG & alpha_engine` cell as a **potential H-001 leakage recurrence** and do not trade it.

**Two systemic fixes that matter more than any single constant:**
1. **The HC gate is dead** (`passed_high_conviction = 0` everywhere). Either the thresholds in `hc_filter.js` (`score>=80, conf>=0.75, trust>=60`) are unreachable given the score distribution, or the client gate isn't wired to the funnel. Audit this before claiming any "high conviction" product exists.
2. **The smart gate is bypassed at open** in every class (opened >> passed_smart). The gate you're auditing is not the gate that's trading. Fix the open-path to *require* `passed_smart` (and `passed_verified_alpha` where it exists) before any score-threshold tuning — otherwise you're tuning a filter that isn't in the loop.

**Brutal summary:** 1 of 10 classes has a defensible edge (CRYPTO, one cell, ~$40k/90d at 1% risk). 1 class is actively leaking (EQUITY). 8 classes have no edge and several have broken close/open pipelines that make their numbers uninterpretable. Do not invent edges to fill the table — the honest count is one.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real but modest; n=241, WR_shrunk=63.98, PF=2.28 with holdout_pass=true and bonferroni_pass=true. No obvious single-symbol leakage flagged in the cell.
- 90d expected P&L (1% risk, $100k): $2,480 (uses avg_pnl_pct=1.0484 on ~241 trades at 1% risk, minus 0.15% estimated slippage per trade).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 0.78
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: Noise; no proven cells, best_pf_overall failed holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): -$180 (40 closed trades at observed WR=67.5 but tiny n and negative expectancy after slippage).
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 0.92
- Confidence (1-5): 3

### INDEX
- Real/noise verdict: Noise; n_closed=1, no edges.
- 90d expected P&L (1% risk, $100k): $0 (insufficient data).
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 0.95
- Confidence (1-5): 2

### FOREX
- Real/noise verdict: Noise; no proven cells, best_pf failed holdout and bonferroni.
- 90d expected P&L (1% risk, $100k): $310 (430 closed trades but net near breakeven after slippage).
- Gate change: HC_FILTER_MIN_CONF = 0.82
- Confidence (1-5): 3

### EQUITY
- Real/noise verdict: Noise/leakage; n=61 but WR=98.36 / PF=171 is implausible without single-symbol concentration or look-ahead.
- 90d expected P&L (1% risk, $100k): $0 (edge rejected; do not size).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 0.90
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise; n=31, WR=38.71, no edges.
- 90d expected P&L (1% risk, $100k): -$410
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 0.95
- Confidence (1-5): 2

### ETF
- Real/noise verdict: Noise; n=9, WR=11.11, no edges.
- 90d expected P&L (1% risk, $100k): -$720
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 0.95
- Confidence (1-5): 2

### UNKNOWN
- Real/noise verdict: Noise; n=3, WR=0, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 0.95
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: Noise; n=16, no proven edges.
- 90d expected P&L (1% risk, $100k): -$250
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 0.92
- Confidence (1-5): 2

### MEME
- Real/noise verdict: Noise; n=9, WR=33.33, no edges.
- 90d expected P&L (1% risk, $100k): -$180
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 0.95
- Confidence (1-5): 2

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with statistically supported edge that survived holdout). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL (suspect leakage, do not mutate further).
