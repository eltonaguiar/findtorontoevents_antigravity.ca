# Per-Asset-Class Pick Analysis — 2026-04-21

**Source:** `audit_trail/data/dashboard_payload.json` (picks.active=47, picks.recent_closed=3,500; 0 null pnl) + `alpha_engine/data/strategy_performance.json` (186 keys).
**Scope:** read-only analysis; no production files modified.

## TL;DR

1. **CRYPTO is the whole portfolio's bleed:** -1,323.8 cum pnl% on 1,668 closed, dragging the overall book to -1,097.4% cum (PF 0.73, WR 31.4%). Every other class is either flat or positive.
2. **Two CRYPTO strategies own 88% of the CRYPTO damage:** `copy_hl_lb_None` (-806.4% on 278 trades, median per-trade -4.5%) and `st_fear_greed_contrarian` (-358.8% on 627 trades, 100% LONG, 24.6% WR).
3. **CRYPTO active book is 29 LONG / 4 SHORT** — still long-biased despite the -1,323% cum — and 4 of the 33 active CRYPTO picks sit on symbols with WR<25% on n>=30 (DOGE, SUI, OP, LINK).
4. **EQUITY is the only clear edge:** 50.0% WR, PF 1.43, cum +226.5% on 338 trades, driven by CVX (+58 cum / 74% WR) and Breakout Momentum.
5. **Flat-close "resolver bug" indicator is NOT the issue** — flat% is 1.77% system-wide and the worst single strategy is FOREX `non_crypto_consensus` at 5.9%; the losses are real, not resolver artifacts.

---

## Overall

| metric | value |
|---|---|
| n_active | 47 |
| n_closed | 3,500 |
| wr_pct | 31.37 |
| pf | 0.731 |
| mean_pnl_pct | -0.3136 |
| cum_pnl_pct | **-1,097.44** |
| max_drawdown_pct | -1,660.27 |
| flat_close_pct | 1.77 |

Class counts (closed): CRYPTO 1,668 · FOREX 848 · COMMODITY 552 · EQUITY 338 · ETF 74 · BOND 17 · UNKNOWN 3.

---

## CRYPTO

| metric | value |
|---|---|
| n_active | 33 |
| n_closed | 1,668 |
| wr_pct | 32.73 |
| pf | **0.587** |
| mean_pnl_pct | -0.7936 |
| cum_pnl_pct | **-1,323.80** |
| max_drawdown_pct | -1,660.27 |
| flat_close_pct | 0.06 |
| flagged_active | 4 |

**Top 5 strategies by n_closed:**

| strategy | n | wr% | cum% |
|---|---:|---:|---:|
| st_fear_greed_contrarian | 627 | 24.6 | -358.82 |
| copy_hl_lb_None | 278 | 32.0 | -806.39 |
| luxalgo_confluence | 122 | 38.5 | -6.79 |
| st_obv_support_divergence | 110 | 42.7 | -36.86 |
| macd_rsi_confluence | 66 | 34.8 | -41.49 |

**Top 5 symbols by n_closed:**

| symbol | n | wr% | cum% |
|---|---:|---:|---:|
| BTCUSDT | 151 | 33.1 | -23.11 |
| ETHUSDT | 106 | 41.5 | -12.18 |
| SOLUSDT | 104 | 38.5 | -8.86 |
| SUIUSDT | 82 | 23.2 | -83.82 |
| AVAXUSDT | 67 | 16.4 | -50.49 |

**Top 3 drags (strategies):** copy_hl_lb_None -806.4 (n=278); st_fear_greed_contrarian -358.8 (n=627); macd_rsi_confluence -41.5 (n=66).
**Top 3 drags (symbols):** DYDXUSDT -202.0 (n=4, blowup); TIAUSDT -132.6 (n=15); OPUSDT -118.0 (n=62).

**Active flags (4/33):** DOGEUSDT LONG (strong-consensus; sym WR 23.1% n=65), SUIUSDT LONG (super-signal via alpha_engine; sym WR 23.2% n=82), OPUSDT LONG (ml_enhanced ensemble_stack; sym WR 19.4% n=62), LINKUSDT LONG (claude_ml_conservative_mut; sym WR 17.5% n=57). Active direction mix: **29 LONG / 4 SHORT**.

**Root cause (most likely):** The CRYPTO book is structurally long and structurally wrong. `copy_hl_lb_None` (copy-trade leaderboard, no mirror window) has a median per-trade pnl of -4.5% and 133/278 trades beyond -5%, i.e. stops are set wide and the strategy is holding through drawdown. `st_fear_greed_contrarian` is 100% LONG with 24.6% WR on 627 trades — a LONG-only contrarian into a regime where "extreme fear" kept getting more extreme. Together these two account for -1,165 of the -1,324 cum. The four drag symbols (DYDX/TIA/OP/SUI/AVAX) are long-only alts with compounded single-trade blowups (DYDXUSDT -202% cum on only 4 trades = position sizing/leverage failure, not signal quality).

**Tweaks (concrete):**
1. **Retire or LONG-disable `st_fear_greed_contrarian`.** WR 24.6% on n=627 is well past the "investigate-before-kill" threshold; a 627-trace LONG-only track with PF<0.6 is not a volatility issue. Minimum: cap it to SHORT signals and regimes where BTC 4h is red (per LONG-source-bias feedback).
2. **Gate `copy_hl_lb_None` behind a per-trade max-loss circuit.** Median -4.5% / p10 -15.2% / min -54% indicates no stop respected. Add a hard -3% SL floor and a drawdown halt if the mirror trader is >10% down on the day; sizing cap per-pick to 0.5R until PF crosses 1.0 on a rolling 100-trade window.
3. **Drop the 4 flagged active LONGs (DOGE/SUI/OP/LINK)** or flip to pair-only with an index hedge. These symbols have >=30-trade WR under 25% in the current regime; on a -1,323% cum book you don't get to buy more of the symbols losing you the most.

---

## EQUITY

| metric | value |
|---|---|
| n_active | 9 |
| n_closed | 338 |
| wr_pct | **50.00** |
| pf | **1.430** |
| mean_pnl_pct | 0.6701 |
| cum_pnl_pct | **+226.49** |
| max_drawdown_pct | -99.55 |
| flat_close_pct | 0.89 |
| flagged_active | 0 |

**Top 5 strategies:** Bollinger MR (n=53, WR 45.3%, cum +22.2); Classic Momentum (n=38, WR 39.5%, cum -2.0); Breakout Momentum (n=37, WR **59.5%**, cum +37.6); stocks_rsi2_pullback (n=18, WR 61.1%, cum +12.9); quality-minus-junk (n=16, WR 56.2%, cum +5.4).

**Top 5 symbols:** XOM (n=42, WR 52.4%, cum +2.5); **CVX (n=27, WR 74.1%, cum +58.0)**; MRK (n=18, WR 66.7%, cum +20.3); JNJ (n=17, WR 17.6%, cum -25.6); AMD (n=16, WR 50.0%, cum +22.5).

**Top 3 drags:** smart_money_accumulation -18.9 (n=5); kimi_signal_tracking -17.3 (n=4); goldmine_6x_consensus -16.7 (n=4). Symbol drag: JNJ -25.6 (n=17), NIO -15.8 (n=8). Active book is dominated by `regime_terminal` (7 of 9); no flags.

**Root cause:** EQUITY is the functional part of the book. Mean per-trade +0.67%, PF 1.43. Drag is concentrated in tiny-n experimental strategies (all three drag-strats have n<=5) and a single loser symbol (JNJ, 17.6% WR on n=17).

**Tweaks:**
1. **Scale Breakout Momentum + stocks_rsi2_pullback.** Both clear 55% WR with positive cum on n>=18; they're the repeatable edges and should get more sizing budget reallocated from CRYPTO.
2. **Kill JNJ from the universe or require SHORT-only.** 17.6% WR / -25.6 cum on n=17 is an adverse-selection signal; the strategy pool systematically mis-prices it.
3. **Don't add picks from the three drag strategies** (smart_money_accumulation, kimi_signal_tracking, goldmine_6x_consensus) until they cross n=20 with positive cum in paper.

---

## FOREX

| metric | value |
|---|---|
| n_active | 3 |
| n_closed | 848 |
| wr_pct | 25.59 |
| pf | 0.927 |
| mean_pnl_pct | -0.0155 |
| cum_pnl_pct | -13.13 |
| max_drawdown_pct | -58.21 |
| flat_close_pct | 4.36 |
| flagged_active | **3/3** |

**Top 5 strategies:** forex_rsi2_mean_reversion (n=523, WR 28.3%, cum **+34.6**); non_crypto_consensus (n=85, WR **0.0%**, cum +0.01); Breakout Momentum (n=32, WR 34.4%, cum -17.5); cta_cross_asset_tsmom (n=24, WR 8.3%, cum -0.8); kimi_signal_tracking (n=22, WR 36.4%, cum -35.3).

**Top 5 symbols:** AUDUSD=X (n=81, WR 24.7%, cum -37.3); AUDJPY=X (n=78, WR 19.2%, cum -1.7); GBPJPY=X (n=77, WR 23.4%, cum +6.4); **USDCAD=X (n=75, WR 24.0%, cum +44.4)**; USDJPY=X (n=71, WR 18.3%, cum +24.0).

**Top 3 drags:** kimi_signal_tracking -35.3 (n=22); Breakout Momentum -17.5 (n=32); forex_carry_momentum -8.0 (n=8). Symbol drag: AUDUSD=X -37.3, NZDJPY=X -21.9, EURJPY=X -13.7.

**Active flags (3/3):** USDCHF=X LONG (`non_crypto_consensus` — WR 0.0% n=85); USDJPY=X LONG (sym WR 18.3% n=71); USDCAD=X LONG (`non_crypto_consensus` + sym WR 24.0% n=75). **Every active FOREX pick is flagged.**

**Contradiction to flag:** `non_crypto_consensus` has cum=+0.01 on n=85 with WR=0.0% — meaning no wins above the 1% threshold but also essentially no aggregate pnl. Either the strategy is exit-capped to near-break-even (a resolver or TP-at-entry bug), or it's only traded inside a very tight band. The +0.01 cum label makes it look harmless; the 0% WR makes it unambiguously broken. Treat the WR as the truth.

**Root cause:** The profitable engine is `forex_rsi2_mean_reversion` (+34.6 on 523 trades) and USDCAD/USDJPY symbols (+44.4 / +24.0). Everything else is noise or worse. The class looks near flat only because 523 good trades are subsidising 300+ bad ones.

**Tweaks:**
1. **Retire `non_crypto_consensus` from FOREX entirely.** WR 0.0% on n=85 is the clearest kill-on-sight signal in the file; it's currently producing 2 of the 3 active FOREX picks.
2. **Drop all 3 active FOREX LONGs** and re-issue only if they come from forex_rsi2_mean_reversion with USDCAD/USDJPY/GBPJPY (the three profitable symbols). Current flagged rate is 3/3; zero picks passing the dashboard sanity filter is worse than no picks.
3. **Raise R:R floor to 1.5+ on any strategy with n>=30 and WR<30%** (kimi_signal_tracking, Breakout Momentum, cta_cross_asset_tsmom, forex_carry_momentum) — PF<1 with sub-30 WR can only be fixed by widening the TP relative to SL.

---

## COMMODITY

| metric | value |
|---|---|
| n_active | 2 |
| n_closed | 552 |
| wr_pct | 21.56 |
| pf | 1.096 |
| mean_pnl_pct | 0.0133 |
| cum_pnl_pct | +7.35 |
| max_drawdown_pct | -28.70 |
| flat_close_pct | 3.26 |
| flagged_active | 0 |

**Top 5 strategies:** futures_momentum (n=443, WR 23.9%, cum **+17.4**); cta_commodity_momentum_term (n=46, WR 8.7%, cum -4.3); cta_cross_asset_tsmom (n=32, WR 15.6%, cum +1.9); cta_golden_cross_200 (n=11, WR 0.0%, cum 0.0); cot_positioning (n=5, WR 0.0%, cum -0.1).
**Top 5 symbols:** SI=F (n=182, WR 22.0%, cum -4.0); HG=F (n=124, WR 15.3%, cum +6.9); PL=F (n=122, WR 22.1%, cum +5.7); GC=F (n=91, WR 27.5%, cum -0.5); KC=F (n=9, WR 11.1%, cum -0.1).

**Top 3 drags:** cftc_cot_commercial_signal -5.5 (n=4); cta_commodity_momentum_term -4.3 (n=46); mean_reversion_bollinger -3.1 (n=2). Symbol drag: CL=F -5.25 (n=6).

**Contradiction to flag:** The class-level 21.6% WR looks awful but PF is 1.10 and cum is positive — meaning winners are significantly larger than losers. This is the expected CTA/trend signature (low hit rate, high payoff); metrics are internally consistent but the dashboard TL;DR should not rank this class by WR.

**Root cause:** futures_momentum is carrying the class (+17.4 on 443 trades) via large-winner metals trades (HG copper +6.9, PL platinum +5.7). The CTA cousin strategies (cta_commodity_momentum_term, cta_cross_asset_tsmom, cta_golden_cross_200) all underperform the main `futures_momentum` on the same asset set — they appear to be redundant variants fighting the leader.

**Tweaks:**
1. **Consolidate CTA variants.** Keep `futures_momentum`; demote or kill `cta_commodity_momentum_term` (WR 8.7% n=46, cum -4.3) and `cta_golden_cross_200` (WR 0% n=11) per the mutate-before-kill protocol.
2. **Remove CL=F from the universe** or require confluence. WR likely under 10% on n=6 with cum -5.25 is a thin-n red flag but the only net-negative drag in the class.
3. **Don't judge this class by WR** in the dashboard TL;DR; expose PF and cum explicitly. A 21% WR with PF 1.10 is healthy trend behaviour.

---

## ETF

| metric | value |
|---|---|
| n_active | 0 |
| n_closed | 74 |
| wr_pct | 48.65 |
| pf | 1.029 |
| mean_pnl_pct | 0.0349 |
| cum_pnl_pct | +2.58 |
| max_drawdown_pct | -48.87 |
| flat_close_pct | 2.70 |
| flagged_active | 0 |

**Top 5 strategies:** quality-minus-junk (n=11, WR 45.5%, cum -4.4); intermarket-flow-scout (n=10, WR 60.0%, cum **+10.0**); quick_engine (n=5, WR 60.0%, cum +0.4); proven_vwap_mean_reversion (n=4, WR 50.0%, cum +1.3); betting-against-beta (n=4, WR 25.0%, cum -4.0).
**Top 5 symbols:** XLE (n=14, WR 50.0%, cum -2.7); QQQ (n=12, WR 58.3%, cum +3.2); IWM (n=12, WR 41.7%, cum -8.8); GLD (n=9, WR 44.4%, cum -1.0); SPY (n=9, WR 44.4%, cum -0.3).

**Top 3 drags:** hyperopt_connors_rsi2 -6.6 (n=2); goldmine_1x_consensus -5.8 (n=1); options-flow-scout -5.5 (n=3). Symbol drag: IWM -8.8, SLV -5.5.

**Root cause:** The class is near break-even with a -48.9% internal max drawdown on only 74 trades — so a few big ETF losers (likely IWM and SLV) carved deep local DDs that recovered. PF 1.03 on n=74 is statistically indistinguishable from coin-flip; the class lacks scale to conclude edge.

**Tweaks:**
1. **Grow the closed sample before concluding edge.** n=74 is below the minimum for any hard decision.
2. **Prioritize intermarket-flow-scout** (60% WR / +10.0 cum on n=10) — smallest but cleanest positive signal in the class.
3. **Stop running `hyperopt_connors_rsi2` and `goldmine_1x_consensus` on ETFs** — net-negative on tiny samples is the usual "over-fit by hyperopt" warning sign.

---

## BOND

| metric | value |
|---|---|
| n_active | 0 |
| n_closed | 17 |
| wr_pct | 47.06 |
| pf | 1.601 |
| mean_pnl_pct | 0.1673 |
| cum_pnl_pct | +2.84 |
| max_drawdown_pct | -3.47 |
| flat_close_pct | 5.88 |
| flagged_active | 0 |

**Top strategies:** futures_momentum (n=8, WR 50%, cum +4.9); betting-against-beta (n=5, WR 40%, cum -1.9); pairs-trading (n=2).
**Top symbols:** ZN=F (n=8, WR 50%, cum +4.9); TLT (n=7, WR 42.9%, cum -2.5); HYG (n=2).

**Top 3 drags:** betting-against-beta -1.9; rs-breakout-scout -1.1; pairs-trading +0.4 (no meaningful third negative drag). Symbol drag: TLT -2.5.

**Root cause:** n=17 is too small to draw conclusions. PF 1.60 looks great but rests on 8 ZN=F trades. TLT is a -2.5 drag but the sample (n=7) is noise.

**Tweaks:** (1) Grow sample before concluding; (2) keep futures_momentum running on ZN=F; (3) no active decisions needed.

---

## UNKNOWN

| metric | value |
|---|---|
| n_active | 0 |
| n_closed | 3 |
| wr_pct | 100.0 |
| pf | inf |
| cum_pnl_pct | +0.23 |

3 trades (AMD, DNA, RIVN) mistagged as UNKNOWN — they're all equities under `regime_*` strategies. **Tagging bug** — `regime_accumulation` / `regime_mild_bull` strategies aren't mapping to EQUITY in whatever the source-aware inference path is (cf. the Session 3 crypto-tagging fix at `dashboard_generator.py:4836-4851`, which needs an equivalent equity-side hook for regime_* strategies).

---

## Cross-Class Observations

- **CRYPTO is -120% of total book loss** (-1,323 / -1,097 = 121%); EQUITY (+226) is the only meaningful offset. Everything else is a rounding error at book level. Any capital-allocation rebalance has to start here.
- **LONG-bias is systemic in losing classes.** CRYPTO active 29L/4S, FOREX active 3L/0S. Both classes have their worst drag strategies running LONG-only (`st_fear_greed_contrarian` 100% LONG in CRYPTO; `non_crypto_consensus` is 100% LONG on USDCAD/USDCHF). This matches the `feedback_long_source_bias.md` note.
- **Flat-close is not the bug here.** System-wide flat% = 1.77%; worst strategy is FOREX `non_crypto_consensus` at 5.9%. The resolver isn't the problem — the strategies are losing on the merits. The real "flat" red flag is `non_crypto_consensus` WR=0.0% / cum=+0.01 on n=85, which is a different shape of bug (TP at entry? pnl zeroing?) worth a separate trace.
- **Tagging regressions remain:** 3 UNKNOWN picks (AMD/DNA/RIVN) and 85 `non_crypto_consensus` picks whose cum=+0.01 / WR=0% profile both look like pipeline issues, not signal issues. The crypto-tagging fix (dashboard_generator.py:4836-4851) is a template for the equity-side regime_* fix.

---

## Reproduce

```python
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"e:/findtorontoevents_antigravity.ca")
data = json.loads((ROOT / "audit_trail" / "data" / "dashboard_payload.json").read_text(encoding="utf-8"))
picks = data["picks"]
active, closed = picks["active"], picks["recent_closed"]

def norm(p):
    ac = p.get("asset_class")
    return "UNKNOWN" if (not ac or str(ac).strip().upper() in ("NULL","NONE")) else str(ac).strip().upper()

by = defaultdict(list)
for p in closed:
    v = p.get("pnl_pct")
    if v is None: continue
    by[norm(p)].append(float(v))

for cls, pnls in sorted(by.items()):
    wins = [x for x in pnls if x > 0.01]; losses = [x for x in pnls if x < -0.01]
    wr = 100 * len(wins) / len(pnls)
    pf = sum(wins) / abs(sum(losses)) if losses else float("inf")
    print(f"{cls:10} n={len(pnls):4d} wr={wr:5.1f}% pf={pf:6.3f} cum={sum(pnls):+8.2f}")
```

Full reproducible scripts: `tmp_analysis/analyze_picks.py` and `tmp_analysis/extra_probes.py` (this session). Output: `tmp_analysis/analysis_output.json`.

---

*Analysis run: 2026-04-21. Read-only. No production files modified.*
