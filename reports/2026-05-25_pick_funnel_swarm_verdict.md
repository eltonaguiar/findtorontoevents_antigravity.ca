# Pick Funnel Swarm Verdict — 2026-11-25 04:41 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261125T044053Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is *never* satisfied. Either the trust field is never populated (every "proven" cell is `trust=UNK`), or the score/conf distributions never co-occur. This is the single biggest finding — the funnel's top gate is dead code.
2. **`opened` ≈ `scanned` in most classes** (COMMODITY 5612/5664, FOREX 25740/27080, EQUITY 5992/6192, INDEX 2140/2141). The "Smart" gate is not filtering — it is a rubber stamp. `passed_smart` is also near-`scanned` for FOREX (98%) and COMMODITY (65%). The funnel is not a funnel.
3. **Closed-trade coverage is tiny and non-random.** COMMODITY 52/5612 (0.9%), INDEX 1/2140, PREDICTION_MARKET 0/302. Any WR computed on these is a survivorship-biased sample of trades that happened to resolve inside 90d. The "PROVEN" cells are computed on the *closed* subset, not the opened population.

---

### COMMODITY
- **Real/noise verdict:** **NOISE / no proven edge.** `top_edges_proven` is empty. The best cell (`trust=UNK & fam=mean_reversion & dir=LONG`, n=20, WR 65%, PF 5.09) **fails holdout** (holdout_pf 8.6 on n=15 but train_pf 1.58 on n=5 — the "holdout" is 3× the train, so this is not a real train/holdout split, it's a single 20-trade cluster) and **fails Bonferroni** (wr_z=1.34). PF 5.09 on n=20 with avg_pnl 1.02% is a handful of large winners. Given [H-001] and [H-036] both killed COMMODITY signals on this exact dataset, treat any COMMODITY "edge" as a leakage-recurrence candidate until proven otherwise. The 63.5% headline WR is on 52 closed trades out of 5,612 opened — pure survivorship.
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** If forced to model the n=20 cell at 1% risk ($1,000/trade) × 20 trades × 1.02% avg = **~$204 gross**, minus ~0.15% round-trip slippage × 20 × $1,000 = **-$30**, net **~$174** — statistically indistinguishable from zero given the failed holdout and Bonferroni.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise from current (effectively ~0, since 65% pass) to a level that cuts `passed_smart` from 3,675 to **<300** (target ~5% pass rate). Concretely: set the score floor so only the top decile of the score distribution survives; if the current constant is e.g. 50, set it to **75**. The gate is currently not a gate.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **NOISE — and the headline cell is a red flag.** `top_edges_proven` is empty. The best cell (`trust=UNK & conf=C>=0.90 & fam=regime`, n=39, WR 87%, PF 11.5) has **holdout_n=2** — the "holdout" is two trades. `holdout_pass=false`. This is textbook overfit: train_pf 14.1 on n=37, holdout 1.18 on n=2. PF 11.5 on 39 trades with avg_pnl 0.67% means the P&L is dominated by 1–2 outliers. The class-level WR is 48.4% on 510 decisive trades — a coin flip. The `regime_terminal` source producing 87% WR on 39 trades while the class overall is 48% is a **single-source concentration** smell; verify it isn't one symbol (e.g. one JPY pair) or one regime window. This is exactly the pattern [H-035] was killed for (sign instability across walk-forward windows).
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** Class-level: 510 decisive trades × 1% × (48.43% × avg_win − 51.57% × avg_loss). With avg_pnl 0.67% on the "edge" cell but class WR below 50%, the class is **negative EV** before slippage. FOREX round-trip slippage on retail is ~0.5–1.0 pip; at 1% risk this is a meaningful drag. Expected P&L is **negative**, roughly **-$2,000 to -$5,000** over 90d if you traded the class blindly.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — the 98% pass rate (26,535/27,080) is the problem. Raise the floor to cut `passed_smart` to **<1,500** (target ~5%). Also add a **source-diversity cap**: no single `source` may exceed 20% of `passed_smart`. The `regime_terminal` cell is 39 trades of one source masquerading as an edge.
- **Confidence (1-5):** **1**

### CRYPTO
- **Real/noise verdict:** **The only cell that survives scrutiny — but with caveats.** `trust=UNK & conf=C0.75-0.80 & source=alpha_engine`: n=188, WR 64.4%, **wr_shrunk 63.0%**, PF 1.80, **holdout_pass=true** (train_pf 1.61 n=109, holdout_pf 2.15 n=79 — a real split), **bonferroni_pass=true**, wr_z=3.94. This is the one cell in the entire report that passes holdout *and* multiple-testing correction on a non-trivial n. **However:** (i) it is `trust=UNK` — the trust field is unpopulated, so we cannot verify it isn't a single-source artifact; (ii) `source=alpha_engine` is the same source flagged in [H-035] for sign instability — verify this cell is not the same funding/settlement signal in disguise; (iii) PF 1.80 is plausible, not suspicious — unlike FOREX's 11.5. The class-level WR is 44.7% (losing), so the edge is **concentrated in one confidence band (0.75–0.80) and one source**. That is fragile but real.
- **90d expected P&L (1% risk, $100k):** Model the proven cell only. 188 trades × $1,000 risk × 0.64% avg_pnl = **~$1,203 gross**. Slippage: crypto round-trip ~0.10–0.20% at 1% risk = ~$1,000 × 0.15% × 188 = **-$282**. Net **~$920** on $100k over 90d (~0.9% return, ~3.7% annualized). Modest but positive. **Do not extrapolate to the full 10,291 opened** — the edge is 188 trades, not 10k.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — currently 4,587/12,408 pass (37%). The proven cell lives at **conf 0.75–0.80**, which is *below* the HC gate's 0.75 floor but the HC gate also requires score>=80 and trust>=60 (never met). **Fix the trust field first** (populate it so `trust>=60` is meaningful), then set `SMART_PICKS_MIN_SCORE_CRYPTO` to isolate the 0.75–0.80 band. If the constant is currently ~50, set to **65** and add a hard `conf in [0.75, 0.80]` allowlist for the alpha_engine source.
- **Confidence (1-5):** **3** (the only class above 2)

### EQUITY
- **Real/noise verdict:** **SUSPICIOUS — likely leakage or single-symbol concentration.** The "proven" cell (`trust=UNK & rr=RR>=2.0 & fam=mean_reversion`, n=32, WR 96.9%, **PF 112.8**) is not a real edge — PF 112 means average win is ~112× average loss on 32 trades. That is either (a) a single enormous winner, (b) a look-ahead in the R:R labeling (RR>=2.0 cells are *defined* by outcome, so selecting on RR>=2.0 and then measuring WR is **selection on the dependent variable** — this is the leakage), or (c) a stale-price artifact. `wr_shrunk 78.85%` on n=32 with wr_z=5.3 and bonferroni_pass=true is *statistically* clean but *economically* implausible. **Flag as leakage recurrence:** the RR>=2.0 conditioning is a classic post-hoc filter. The class-level WR 72% on 118 decisive trades out of 5,992 opened (2% coverage) is survivorship. [H-009] and [H-011] were both killed on EQUITY — this smells like the same family.
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** The PF 112 cell is not investable (you cannot replicate a 112× PF; it is an artifact). If you naively sized the 32 trades at 1% risk × 1.57% avg = **~$502 gross**, but the true edge is almost certainly zero or negative once the RR>=2.0 selection bias is removed. Treat as **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — currently 222/6,192 pass (3.6%), which is actually the *tightest* gate in the system. The problem is not the gate, it's the **RR>=2.0 conditioning in the edge-finder**. Change the edge-finder to require RR bands to be *ex-ante* (set at entry) not *ex-post* (realized). In `quality_gates.py`, add `EQUITY_REQUIRE_EXANTE_RR = True` and reject any cell whose RR band is computed from realized P&L.
- **Confidence (1-5):** **1**

### PREDICTION_MARKET
- **Real/noise verdict:** **NO DATA.** 302 scanned, 18 passed_smart, **0 closed**. Cannot evaluate. Do not size.
- **90d expected P&L (1% risk, $100k):** **$0** (no closed trades).
- **Gate change:** None — fix the resolution/close pipeline first. `passed_smart` 18/302 (6%) is the only sane gate in the report; leave it.
- **Confidence (1-5):** **1** (no evidence either way)

### BOND
- **Real/noise verdict:** **NOISE / negative.** WR 38.7% on 31 decisive trades. `passed_smart` 1/1,268 — the gate is essentially closed, which is correct. No proven cells. This class is losing and correctly filtered.
- **90d expected P&L (1% risk, $100k):** **Negative.** 31 trades × 1% × (38.7% × avg_win − 61.3% × avg_loss) ≈ **-$1,500 to -$2,500** if traded. Do not trade.
- **Gate change:** None needed — `SMART_PICKS_MIN_SCORE_BOND` is already doing its job (1/1,268). **Do not loosen it.**
- **Confidence (1-5):** **2** (confident it's noise)

### ETF
- **Real/noise verdict:** **NOISE.** n=12 closed, WR 41.7%, no proven cells. `passed_smart` 267/308 (87%) — gate is a rubber stamp, but with 12 closed trades there's nothing to evaluate.
- **90d expected P&L (1% risk, $100k):** **$0** (n too small; negative EV if extrapolated).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to cut 267→<30. But first fix the close pipeline (12/296 = 4% coverage).
- **Confidence (1-5):** **1**

### FUTURES
- **Real/noise verdict:** **NOISE.** n=16 closed, WR 37.5%, no proven cells. [H-005] already killed FUTURES momentum. `passed_smart` 104/145 (72%) — rubber stamp.
- **90d expected P&L (1% risk, $100k):** **Negative** (~-$800 if traded).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to cut 104→<15. Do not re-derive [H-005].
- **Confidence (1-5):** **1**

### INDEX
- **Real/noise verdict:** **NO DATA.** 1 closed trade, 100% WR. Statistically meaningless. `passed_smart` 1,542/2,141 (72%) — rubber stamp.
- **90d expected P&L (1% risk, $100k):** **$0** (n=1).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to cut 1,542→<100. Fix close pipeline (1/2,140 = 0.05% coverage).
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **NOISE / negative.** WR 0% on 5 closed. This is a data-hygiene bucket — 1,180 scanned items with no asset class. `passed_smart` 96/1,180 (8%) is fine, but the class should not exist. Route these to a real class or drop them.
- **90d expected P&L (1% risk, $100k):** **$0** (n=5, all losses).
- **Gate change:** Not a gate — a **data fix**: add `ASSET_CLASS_REQUIRED = True` in `production_scanner.py` so UNKNOWN never reaches the funnel.
- **Confidence (1-5):** **1**

### MEME
- **Real/noise verdict:** **NOISE.** n=5 closed, WR 40%. `passed_verified_alpha` 2/12 — tiny. No proven cells.
- **90d expected P&L (1% risk, $100k):** **$0** (n=5).
- **Gate change:** None — n too small to gate on. Leave as-is or drop the class.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the one cell.**
`trust=UNK & conf=C0.75-0.80 & source=alpha_engine` is the only cell in the entire 90-day report that passes holdout (n=79, PF 2.15) *and* Bonferroni (wr_z=3.94) on a non-trivial sample. Expected ~$920 net on $100k over 90d at 1% risk. **Caveats before scaling:** (1) populate the `trust` field so `trust=UNK` becomes a real filter — right now every "proven" cell is trust-blind; (2) confirm the 188 trades are not single-symbol concentrated (check top-3 symbol share < 40%); (3) confirm `source=alpha_engine` here is not the [H-035] funding/settlement signal in disguise. If any of those three fail, **demote CRYPTO to paper-only** and the answer becomes "scale nothing."

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.**
FOREX is the largest funnel (27,080 scanned, 25,740 opened) with the worst signal-to-noise: 48.4% WR on 510 decisive trades, a 98% Smart pass rate (gate is dead), and a "best" cell whose holdout is n=2. It is consuming the most compute and capital for a coin-flip outcome. **Mutate before kill:** (Axis 1) raise `SMART_PICKS_MIN_SCORE_FOREX` to cut pass rate to <5%; (Axis 2) add a source-diversity cap (no source >20% of passed_smart) to break the `regime_terminal` concentration; (Axis 3) require `holdout_n >= 30` before any FOREX cell can be labeled PROVEN. If after 30 days the mutated FOREX funnel still shows WR < 52% on n>=100, **kill it** — do not re-derive [H-035].

**Second demotion: EQUITY.** The PF 112 cell is a leakage artifact (RR>=2.0 is selection on the dependent variable). Mutate the edge-finder to use ex-ante RR, then re-evaluate. Do not size EQUITY until that fix lands.

**

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)
