# Pick Funnel Swarm Verdict — 2026-11-26 04:42 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261126T044143Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

## Pre-flight observations (apply to all classes)

1. **`passed_high_conviction = 0` across every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** trades in 90 days. That is not a gate — it's a wall. Either the score distribution never reaches 80, or trust never reaches 60, or conf never reaches 0.75. This is the single biggest structural finding in the funnel and it dominates every per-class answer below.
2. **`passed_verified_alpha` is 0 for 9 of 11 classes.** Only CRYPTO (3608) and MEME (2) and FUTURES (1) and FOREX (9) produce any verified-alpha picks. The verified-alpha gate is effectively CRYPTO-only.
3. **Funnel leakage is severe.** `opened` ≈ `scanned` in most classes (COMMODITY 5618/5672, FOREX 25816/27164, EQUITY 6006/6242, INDEX 2136/2137, PREDICTION_MARKET 368/368, BOND 1259/1291). The "passed_smart" filter is not actually gating opens. This means the WR numbers below are **not** the WR of the smart-picks funnel — they're the WR of the raw scanner.
4. **Close rate is catastrophically low** in several classes: INDEX 1/2136 closed, PREDICTION_MARKET 0/368, UNKNOWN 5/1162, COMMODITY 54/5618, BOND 32/1259. Any WR computed on these is meaningless.
5. **The FOREX "consensus/regime" cell is the exact shape of H-001.** `trust=UNK & conf=C>=0.90 & source=regime_terminal`, n=39, WR=87%, PF=11.5, **holdout_n=2, holdout_pass=false**. This is a textbook leakage recurrence — a single source (`regime_terminal`) with unknown trust, tiny holdout, and PF that no real FX strategy produces. Treat as falsified until proven otherwise.
6. **The EQUITY mean_reversion cell is also suspect.** PF=112.8, WR=96.9%, n=32, holdout_n=22 with holdout_pf=99.0. A PF of 112 means average win / average loss ≈ 112× the loss rate ratio. That is not a strategy; that is either (a) a single-symbol concentration (one ticker that gapped up 30% and never hit stop), (b) a stop that is never triggered because the trade is closed by a time-based exit at a tiny profit, or (c) look-ahead in the entry timestamp. **Flag as leakage recurrence of H-009/H-011 family (EQUITY options-adjacent mean reversion).** Do not scale.
7. **The CRYPTO cell is the only one that survives scrutiny.** n=188, WR_shrunk=63%, PF=1.80, train_pf=1.62, holdout_pf=2.21, holdout_n=71, bonferroni_pass=true, wr_z=3.94. This is a real, modest, replicable edge. It is also the *only* cell in the entire dataset that passes holdout with n>50.

---

### COMMODITY
- **Real/noise verdict:** **Noise / unproven.** n_closed=54 total, best cell n=21, holdout_n=15, holdout_pass=false, bonferroni_pass=false, wr_z=1.53. The 66.7% WR shrinks to 58.5% and the PF of 5.48 is driven by 6 train trades. This is the same shape as H-001 (COT leakage) and H-036 (inventory gate) — both already killed. **Do not trade.** The 61% headline WR is on 54 closed trades out of 5618 opened — a 0.96% close rate. That is not a track record; it's a rounding error.
- **90d expected P&L (1% risk, $100k):** **$0.** No tradeable edge. If forced to size the "best" cell at 1% risk on 21 trades with 58.5% shrunk WR and PF 5.48, expected P&L is ~+$1,100 *in-sample only*, but holdout fails and n is too small to size. **Recommend $0 allocation.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **85** (from current, which is clearly permissive given 3683/5672 = 65% pass rate). Also add a hard `MIN_CLOSED_TRADES_FOR_PROMOTION = 100` before any COMMODITY cell can be labeled PROVEN. The current 54 closed trades cannot support any promotion.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **Leakage recurrence — treat as falsified.** The `regime_terminal` cell (n=39, WR=87%, PF=11.5) has holdout_n=2 and holdout_pass=false. A PF of 11.5 on FX is not a strategy; it is a data artifact. The `trust=UNK` dimension is the tell — unknown trust + extreme confidence + single source = the exact H-001 signature. The class-level WR of 48.57% on 523 decisive trades is **below coin-flip** and is the honest number. **No edge.**
- **90d expected P&L (1% risk, $100k):** **Negative.** At 48.57% WR with typical FX R:R of ~1:1, expected P&L on 523 trades at 1% risk ≈ **−$2,600** (before slippage; after realistic 0.5-pip slippage on 25,816 opens, worse). **Recommend $0 allocation.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise to **80**, and add a hard block: `if source == "regime_terminal" and trust == "UNK": reject`. The 26,618/27,164 = 98% pass rate is the smoking gun — the FOREX smart gate is not gating.
- **Confidence (1-5):** **1**

### EQUITY
- **Real/noise verdict:** **Leakage recurrence — do not trade.** PF=112.8, WR=96.9%, holdout_pf=99.0 on n=22. This is the H-009/H-011 family signature (EQUITY mean-reversion with implausible PF). Either single-symbol concentration (one ticker dominating the 32 trades) or a stop/exit artifact. The class-level WR of 71.9% on 121 decisive trades is *plausible* but the cell-level PF is not. **Flag as leakage recurrence; do not scale.** The 223/6242 = 3.6% smart-pass rate is the only healthy gate in the entire funnel — but it's gating the wrong thing (it's letting through the leakage cell).
- **90d expected P&L (1% risk, $100k):** **$0 on the PROVEN cell** (leakage). If the class-level 71.9% WR on 121 trades is real (it may be — EQUITY mean reversion in a trending market can work), expected P&L at 1% risk ≈ **+$4,300**, but this is *not* what the PROVEN cell claims and should not be sized off the cell. **Recommend $0 until the cell is re-derived with symbol-level dedup and timestamp audit.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — keep at current (3.6% pass rate is fine), but add `MAX_SINGLE_SYMBOL_SHARE = 0.20` to the PROVEN-cell promotion logic. The PF=112 cell almost certainly violates this.
- **Confidence (1-5):** **2** (class WR plausible, cell WR not)

### ETF
- **Real/noise verdict:** **Noise.** n_closed=14. Below any threshold for inference. WR=42.86%. No PROVEN cells. **No edge.**
- **90d expected P&L (1% risk, $100k):** **Negative, ~−$200** on 14 trades at 1% risk. **Recommend $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **85** (263/304 = 86.5% pass rate is absurdly permissive for a 14-trade sample). Also: **do not compute WR on n<30** — display "insufficient sample" instead.
- **Confidence (1-5):** **1**

### CRYPTO
- **Real/noise verdict:** **REAL — the only real edge in the dataset.** n=188, WR_shrunk=62.98%, PF=1.80, train_pf=1.62, holdout_pf=2.21, holdout_n=71, holdout_pass=true, bonferroni_pass=true, wr_z=3.94. The cell is `trust=UNK & conf=C0.75-0.80 & source=alpha_engine` (LONG). This is a *modest* edge — not the PF=11 fantasy of FOREX — and it survives holdout, Bonferroni, and shrinkage. The `trust=UNK` is a concern but the holdout_n=71 with holdout_pf=2.21 is the strongest validation in the entire report. **This is the one to scale.**
- **90d expected P&L (1% risk, $100k):** At 1% risk ($1,000/trade), 188 trades, avg_pnl_pct=0.6438% per trade on notional → **~+$12,100** gross. Apply 0.10% round-trip slippage on 188 trades (~$1,880) and 0.05% fees (~$940) → **net ≈ +$9,300**. If we size at 1.5% risk (justified by holdout_pf=2.21), **net ≈ +$14,000**. **Recommend sizing at 1% for first 30 days, then 1.5% if live WR tracks ≥60%.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **lower to 70** (from current, which is clearly too high given 4790/12698 = 37.7% pass rate but only 3608 verified-alpha). The edge lives in the `conf=C0.75-0.80` band, which is *below* the HC gate's 0.75 floor — so the HC gate is structurally excluding the only real edge. **Also: `hc_filter.js` `HC_MIN_CONF` = 0.75 → 0.72** to admit the C0.75-0.80 band that carries the edge. This is the single highest-leverage change in the entire funnel.
- **Confidence (1-5):** **4**

### PREDICTION_MARKET
- **Real/noise verdict:** **No data.** 0 closed trades out of 368 opened. Cannot evaluate. **No edge claim possible.**
- **90d expected P&L (1% risk, $100k):** **$0** (no closes).
- **Gate change:** `SMART_PICKS_MIN_SCORE_PREDICTION_MARKET` — **do not change**; instead fix the close pipeline. 0/368 closed is a plumbing bug, not a gate issue. **Recommend: block opens until close pipeline is verified.**
- **Confidence (1-5):** **1** (no data)

### BOND
- **Real/noise verdict:** **Noise / negative.** WR=37.5% on 32 decisive trades. 3/1291 = 0.23% smart-pass rate — the gate is correctly rejecting almost everything, but the 1259 opens that leaked through are losing. **No edge.**
- **90d expected P&L (1% risk, $100k):** **Negative, ~−$800** on 32 trades at 1% risk with 37.5% WR. **Recommend $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **raise to 90** (effectively disable BOND until a real edge is found). The 0.23% pass rate is already near-disabled; make it explicit.
- **Confidence (1-5):** **1**

### FUTURES
- **Real/noise verdict:** **Noise.** n_closed=16, WR=37.5%. H-005 (futures momentum anti-signal) already failed. **No edge.**
- **90d expected P&L (1% risk, $100k):** **Negative, ~−$400** on 16 trades. **Recommend $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to 85** (101/142 = 71% pass rate is too permissive for a 16-trade sample).
- **Confidence (1-5):** **1**

### INDEX
- **Real/noise verdict:** **No data.** 1 closed trade out of 2136 opened. WR=100% on n=1 is meaningless. **No edge claim possible.**
- **90d expected P&L (1% risk, $100k):** **$0** (n=1).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise to 85** (1538/2137 = 72% pass rate is too permissive). Also fix close pipeline (1/2136 is a bug).
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **Noise / negative.** WR=0% on 5 decisive trades. 94/1167 = 8% smart-pass rate. **No edge.**
- **90d expected P&L (1% risk, $100k):** **Negative, ~−$500** on 5 trades. **Recommend $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_UNKNOWN` — **raise to 95** (effectively block UNKNOWN class entirely until classification is fixed). The 1167 UNKNOWN scans are a data-quality bug, not a tradeable class.
- **Confidence (1-5):** **1**

### MEME
- **Real/noise verdict:** **Noise.** n_closed=5. WR=40%. **No edge.**
- **90d expected P&L (1% risk, $100k):** **Negative, ~−$100** on 5 trades. **Recommend $0.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **raise to 90** (4/12 = 33% pass rate on n=12 is meaningless).
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only.**
- The `trust=UNK & conf=C0.75-0.80 & source=alpha_engine & dir=LONG` cell is the only PROVEN cell that survives holdout (n=71, holdout_pf=2.21), Bonferroni, and shrinkage (WR_shrunk=63%). It is a *modest* edge (PF 1.80), not a fantasy edge — which is exactly why it's credible.
- **Sizing:** 1% risk per trade, $100k notional, 188 trades/90d → **~+$9,300 net** after slippage/fees. Scale to 1.5% after 30 days if live WR ≥60%.
- **Critical gate change to unlock it:** `hc_filter.js` `HC_MIN_CONF` = 0.75 → **0.72**, and `SMART_PICKS_MIN_SCORE_CRYPTO` → **70**. The edge lives in the C0.75-0.80 band that the HC gate currently excludes. This is the single highest-leverage change in the funnel.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
- **FOREX** — the `regime_terminal` cell is an H-001 leakage recurrence (holdout_n=2, holdout_pass=false, PF=11.5). Mutate the source dimension first (drop `regime_terminal`, re-run), then kill if WR stays <50%. Do not scale.
- **EQUITY** — the PF=112 mean_reversion cell is an H-009/H-011 leakage recurrence. Mutate by adding `MAX_SINGLE_SYMBOL_SHARE=0.20` and re-deriving; if PF drops below 3, kill the cell. The class-level 71.9% WR on 121 trades is *plausible* but unproven — do not size off it.
- **COMMODITY** — H-001 and H-036 already killed the two obvious edges; the remaining 54 closed trades cannot support any promotion. Mutate by raising `SMART_PICKS_MIN_SCORE_COMMODITY` to 85 and requiring `MIN_CLOSED_TRADES_FOR_PROMOTION=100`; if no cell clears, kill the class.

**Structural fixes required before any further scaling:**
1. **`passed_high_conviction = 0` across all 11 classes** is a broken gate, not a strict one. Fix `hc_filter.js` thresholds or the score distribution — a gate that fires on zero trades in 90 days is not doing its job.
2. **Funnel leakage:** `opened ≈ scanned` in

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)
