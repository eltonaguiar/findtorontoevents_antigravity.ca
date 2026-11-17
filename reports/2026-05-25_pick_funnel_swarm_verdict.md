# Pick Funnel Swarm Verdict — 2026-11-17 04:41 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261117T044115Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is dead code in production. Nothing has ever cleared it. That is the single biggest finding in this dataset.
2. **`passed_verified_alpha` is 0 for 7 of 10 classes.** Only CRYPTO (2508), FOREX (9), FUTURES (1), MEME (3) produce any. The verified-alpha gate is effectively a CRYPTO-only filter.
3. **The funnel is inverted.** `opened` ≈ `scanned` for every class (e.g. FOREX 25,599 opened / 26,949 scanned = 95%). The "smart" gate is not filtering — it is a rubber stamp. `passed_smart` for FOREX is 26,296/26,949 = **97.6% pass rate**. That is not a gate, that is a pass-through.

---

### INDEX
- Real/noise verdict: **Noise / no edge.** n_closed=1. A single trade with WR=100% is not a sample, it is an anecdote. `passed_smart`=1546/2054 (75%) but `opened`=2053 — the gate is not doing anything and there is no closed-trade evidence to evaluate. Do not trade this class.
- 90d expected P&L (1% risk, $100k): **$0** (n=1, no statistical basis; any number here is fabrication).
- Gate change: `SMART_PICKS_MIN_SCORE_INDEX` — raise from current (effectively ~0) to **70**, and add a hard `MIN_CLOSED_TRADES_FOR_PROMOTION = 30` so INDEX cannot be promoted to "smart" until it has a real sample.
- Confidence (1-5): **1**

### COMMODITY
- Real/noise verdict: **Noise.** n_closed=36, WR=66.7% raw but the only "best" cell (`trust=UNK & dir=LONG & source=alpha_engine`, n=27, WR=59.3%, PF=1.77) has `wr_z=0.96` and `bonferroni_pass=false`. Holdout PF 1.34 on n=13 is not evidence. Note the falsified H-001 (COT leakage) and H-036 (inventory gate) — this class has a documented history of leakage-driven fake edges. The 66.7% headline WR is almost certainly a small-sample artifact of 36 trades.
- 90d expected P&L (1% risk, $100k): **~$0 to slightly negative.** At 1% risk ($1k/trade) × 36 trades × avg_pnl 0.62% ≈ **+$220 gross**, minus slippage/commission (~$5-10/trade round-trip on commodity futures) ≈ **−$100 to +$100 net**. Not tradeable.
- Gate change: `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **65** and require `source != alpha_engine` OR `trust != UNK` for promotion (the entire "edge" is concentrated in the UNK-trust alpha_engine bucket, which is exactly the H-001 leakage signature).
- Confidence (1-5): **2**

### FOREX
- Real/noise verdict: **Noise, and the "best" cell is a textbook leakage red flag.** The `trust=UNK & conf=C>=0.90 & fam=regime` cell has n=38, WR=89.5%, PF=14.4 — but `holdout_n=2` and `holdout_pass=false`. A PF of 14.4 on 38 trades with a 2-trade holdout is not an edge, it is a single regime window (likely a trending USD period) captured by `regime_terminal`. The 51.9% overall WR on 449 decisive trades is the honest number: **coin flip minus costs.** `passed_smart`=26,296/26,949 = 97.6% — the gate is not filtering FOREX at all.
- 90d expected P&L (1% risk, $100k): **Negative.** 449 decisive trades × 1% risk = $4,490 at risk-turnover. At 51.9% WR with typical 1:1 R:R, expectancy ≈ −0.4% per trade × $1k = **−$4/trade × 449 ≈ −$1,800 gross**, plus spread (~0.5-1 pip on majors, ~$5-10/trade) ≈ **−$4,000 to −$6,000 net.** The "regime" cell would have printed money in-sample and then given it back — do not size on it.
- Gate change: `SMART_PICKS_MIN_SCORE_FOREX` — raise to **70** AND add `MIN_HOLDOUT_N = 20` to the promotion criteria in `quality_gates.py`. The current gate lets a 2-trade holdout pass a PF=14 cell into "proven." That is the bug.
- Confidence (1-5): **1** (on the edge being real); **5** (on it being noise)

### CRYPTO
- Real/noise verdict: **The only class with a defensible, if modest, edge — and it is NOT the one the dashboard highlights.** The `trust=UNK & rr=RR1.5-2.0 & source=alpha_engine` cell: n=186, WR=58.6%, wr_shrunk=57.8%, PF=1.92, holdout PF=1.36 on n=68, `holdout_pass=true`. That is a real, out-of-sample-confirmed signal — but `bonferroni_pass=false` (multiple-testing corrected, it does not survive). The overall class WR is 44.7% (1001W/1239L on 2240 decisive) — **the class as a whole loses money.** The edge is a narrow sub-slice (RR 1.5-2.0, alpha_engine source, LONG) inside a losing class. The `ml` cells you flagged are not in the top-3 here — good, because they would be the leakage suspects. The RR1.5-2.0 cell is the honest one.
- 90d expected P&L (1% risk, $100k): **Modest positive IF you trade only the proven sub-slice.** 186 trades × 1% risk ($1k) × avg_pnl 1.06% ≈ **+$1,970 gross**. Crypto slippage/fees ~0.1-0.2% round-trip ≈ $2-4/trade × 186 ≈ **−$500**. Net ≈ **+$1,400 to +$1,500** on the sub-slice. Trading the full class (2240 trades at 44.7% WR) would be **−$15,000 to −$20,000.** The gate change below is what converts one into the other.
- Gate change: `SMART_PICKS_MIN_SCORE_CRYPTO` — **do not lower it; instead add a hard sub-slice router**: promote to smart only if `rr_band == "RR1.5-2.0" AND source == "alpha_engine" AND direction == "LONG"`. Set `SMART_PICKS_MIN_SCORE_CRYPTO = 72` (up from current effective ~0) and gate the rest of CRYPTO out of the smart funnel entirely. The class-level WR of 44.7% is the proof the current gate is not filtering.
- Confidence (1-5): **3** (sub-slice only; class-level = 1)

### BOND
- Real/noise verdict: **Noise / negative.** n_closed=31, WR=38.7% — below coin flip. `passed_smart`=1/1153 = 0.09% pass rate, which means the gate is correctly rejecting almost everything, but `opened`=1122 — so 1122 bonds were opened despite the gate rejecting them. That is a funnel integrity bug: the gate is not connected to the open path for BOND. No edge exists here.
- 90d expected P&L (1% risk, $100k): **Negative.** 31 trades × $1k × (38.7% WR at ~1:1) ≈ **−$226 gross**, plus bond spread ≈ **−$300 to −$400 net.**
- Gate change: `SMART_PICKS_MIN_SCORE_BOND` — set to **999** (effectively disable BOND promotion) until `opened` is wired to `passed_smart`. The 1122-opened-vs-1-passed gap is the actual bug, not the score threshold.
- Confidence (1-5): **1**

### EQUITY
- Real/noise verdict: **The 97.4% WR / PF=135 cell is almost certainly leakage or single-symbol concentration.** n=38, wins=37, `wr_z=5.84`, `bonferroni_pass=true`, holdout PF=99 on n=25 — these numbers are *too* good. A PF of 135 on equities over 90 days does not happen without either (a) a look-ahead in the `mean_reversion` signal, (b) a single ticker dominating (37/38 wins smells like one name that trended), or (c) a PnL calculation bug (e.g. counting unrealized marks as wins). The overall class WR of 73.3% on 105 trades is plausible; the 97.4% sub-cell is not. **Flag as suspected leakage recurrence** — this is the same signature as H-001 (concentration + impossible PF). Do not size on it until the 38 trades are decomposed by ticker.
- 90d expected P&L (1% risk, $100k): **Cannot responsibly estimate.** If the cell is real: 38 × $1k × 1.6% ≈ **+$600**. If it is leakage (likely): **$0 realized, and the 105-trade class at 73.3% WR is +$1,500 to +$2,000 gross minus slippage ≈ +$1,200 net** — but that class number is itself suspect given the sub-cell contamination. Treat as **$0 until audited.**
- Gate change: `SMART_PICKS_MIN_SCORE_EQUITY` — add a **`MAX_SINGLE_SYMBOL_CONCENTRATION = 0.20`** check in `quality_gates.py` (reject any cell where one ticker is >20% of n). This is the specific fix for the 37/38 pattern. Score threshold itself is fine at current level.
- Confidence (1-5): **1** (on the 97% cell); **2** (on the 73% class number)

### ETF
- Real/noise verdict: **Noise / negative.** n_closed=8, WR=12.5% (1W/7L). `passed_smart`=272/312 = 87% pass rate — gate is a pass-through. 8 trades is not a sample. The 12.5% WR is alarming but n=8 means it is 1-2 trades from being 25-37%. No edge.
- 90d expected P&L (1% risk, $100k): **Negative.** 8 × $1k × (12.5% WR) ≈ **−$750 gross**, plus ETF spread ≈ **−$800 net.** (Tiny n — do not over-read.)
- Gate change: `SMART_PICKS_MIN_SCORE_ETF` — raise to **70** and add `MIN_CLOSED_TRADES_FOR_PROMOTION = 30` (same constant as INDEX). ETF should not be in the smart funnel at all until it has 30 closed trades.
- Confidence (1-5): **1**

### UNKNOWN
- Real/noise verdict: **Noise / negative.** n_closed=4, WR=0%. `passed_smart`=112/1279 = 8.8% pass rate (the gate is actually filtering here — good), but `opened`=1275 — again, the open path is not wired to the gate. 4 trades, 0 wins. No edge, and the class label itself ("UNKNOWN") is a data-quality smell.
- 90d expected P&L (1% risk, $100k): **−$40 gross** (4 × $1k × 0% WR), ≈ **−$50 net.** Trivial but negative.
- Gate change: `SMART_PICKS_MIN_SCORE_UNKNOWN` — set to **999** (disable) and route UNKNOWN to a `quarantine` bucket in `quality_gates.py` until the classifier assigns a real asset class. Trading "UNKNOWN" is a data bug, not a strategy.
- Confidence (1-5): **1**

### FUTURES
- Real/noise verdict: **Noise.** n_closed=16, WR=37.5%. `passed_smart`=117/164 = 71% pass rate. Note falsified H-005 (futures_momentum_anti_signal — inversion does NOT fix it). 16 trades is not a sample. No edge.
- 90d expected P&L (1% risk, $100k): **Negative.** 16 × $1k × (37.5% WR at ~1:1) ≈ **−$250 gross**, plus futures commission (~$5/trade) ≈ **−$330 net.**
- Gate change: `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **70** and add `MIN_CLOSED_TRADES_FOR_PROMOTION = 30`. Do not promote FUTURES on 16 trades.
- Confidence (1-5): **1**

### MEME
- Real/noise verdict: **Noise.** n_closed=6, WR=33.3%. `passed_verified_alpha`=3 — the only class besides CRYPTO/FOREX/FUTURES with any verified-alpha picks, but n=6 closed is meaningless. MEME is a lottery-ticket class; do not confuse a 2W/4L sample with an edge.
- 90d expected P&L (1% risk, $100k): **Negative.** 6 × $1k × (33.3% WR) ≈ **−$334 gross**, plus meme slippage (wide) ≈ **−$400 net.**
- Gate change: `SMART_PICKS_MIN_SCORE_MEME` — set to **999** (disable) until `MIN_CLOSED_TRADES_FOR_PROMOTION = 30` is met. MEME should not be in the smart funnel.
- Confidence (1-5): **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — but only the `rr=RR1.5-2.0 & source=alpha_engine & dir=LONG` sub-slice, at reduced size (0.5% risk, not 1%) until the sub-slice clears 300 closed trades.** It is the only cell in the entire dataset with (a) n≥100, (b) holdout_pass=true on n≥50, (c) a plausible PF (1.92, not 14 or 135), and (d) a mechanism (RR-band + source) that is not obviously a leakage signature. Expected 90d P&L on the sub-slice at 1% risk: **~+$1,400 net.** At 0.5% risk: **~+$700.** That is the honest number — small, but real.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.** It is the largest funnel (26,949 scanned, 25,599 opened) with the worst signal-to-noise (51.9% WR, PF=14 cell that fails holdout on n=2). The mutation to try before kill: **replace the `regime_terminal` source with a holdout-gated version** — require `holdout_n >= 20 AND holdout_pass == true` before any FOREX cell is promoted to "proven." If that mutation does not produce a holdout-passing cell in 30 days, kill FOREX from the smart funnel entirely. Do not kill it today; the 51.9% WR is close enough to 50% that a real regime filter *could* exist, but the current `regime_terminal` implementation is not it.

**Second demotion candidate: EQUITY.** The 97.4% WR / PF=135 cell is a leakage recurrence (same signature as H-001: concentration + impossible PF + bonferroni_pass=true on a cell that should not survive multiple testing). Mutate before kill: add `MAX_SINGLE_SYMBOL_CONCENTRATION = 0.20` and re-run. If the cell collapses to <60% WR after concentration-capping, it was leakage — kill the `mean_reversion` family for EQUITY and keep the 73.3% class-level number as the honest baseline.

**The one gate change that lifts edge most system-wide:** add `MIN_HOLDOUT_N = 20` and `MIN_CLOSED_TRADES_FOR_PROMOTION = 30` as hard constants in `audit_trail/quality_gates.py`, applied to every asset class. Right now the funnel promotes cells on n=2 holdouts (FOREX) and n=1 closed trades (INDEX) into "proven." That single change would have blocked every false edge in this report and left only the CRYPTO sub-slice standing — which is exactly the correct outcome.

**The `passed_high_conviction = 0` finding is the meta-bug.** The HC gate in `hc_filter.js` (score>=80, conf>=0.75, trust>=60) has never fired. Either the thresholds are

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### INDEX
- Real/noise verdict: noise (n_closed=1, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 1

### COMMODITY
- Real/noise verdict: noise (n=36 too small; best cells fail bonferroni and have low wr_z)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_TRUST_COMMODITY = 70
- Confidence (1-5): 2

### FOREX
- Real/noise verdict: noise (high PF cells have holdout_n=2 and holdout_pass=false; tiny holdout makes PF=14 meaningless)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF_FOREX = 0.92
- Confidence (1-5): 2

### CRYPTO
- Real/noise verdict: marginal at best (n=186 decent but bonferroni=false, PF only 1.92 after shrinkage, no proven cells)
- 90d expected P&L (1% risk, $100k): $0 (cannot size real money on non-proven cells)
- Gate change: ALPHA_ENGINE_MIN_RR_CRYPTO = 1.8
- Confidence (1-5): 3

### BOND
- Real/noise verdict: noise (n_closed=31, zero proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 75
- Confidence (1-5): 1

### EQUITY
- Real/noise verdict: noise/leakage (PF=135 and 97% WR on train_n=13 is statistically impossible without single-symbol concentration or look-ahead; holdout_pf=99 flags fabrication)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: QUALITY_GATE_MIN_HOLDOUT_N = 40
- Confidence (1-5): 1

### ETF
- Real/noise verdict: noise (n_closed=8, no cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 1

### UNKNOWN
- Real/noise verdict: noise (n_closed=4, empty edges)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_TRUST_UNKNOWN = 65
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: noise (n_closed=16, no proven cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 70
- Confidence (1-5): 1

### MEME
- Real/noise verdict: noise (n_closed=6, no cells)
- 90d expected P&L (1% risk, $100k): $0
- Gate change: ALPHA_ENGINE_MIN_RR_MEME = 2.5
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale up today: none (CRYPTO has volume but no proven edge after shrinkage/bonferroni).  
Demote: EQUITY (clear leakage signature in the mean_reversion cell; violates every statistical sanity check and matches patterns in rejected hypotheses).
