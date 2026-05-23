# Are Our Strategies Actually Consistent? A Data-Driven Audit

**Date:** 2026-04-14
**Dashboard:** [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit/)
**Data source:** `audit_dashboard/data/dashboard_data.json` (3,500 `recent_closed` picks, generated 2026-04-14 15:34 UTC)

> ## ⚠️ This post is REPORTING, not REMEDIATION
>
> This document describes **what the ledger says**. It does not describe a fix that was shipped. Every update on 2026-04-14 has been **measurement, visibility, and diagnostics** — not strategy improvement. Specifically:
>
> - **No TP/SL logic was changed.** The levels picks land with today are the same levels they would have landed with yesterday.
> - **No strategy was added, removed, or re-weighted.** The same sources that are losing money are still in the feed.
> - **No filter threshold was loosened or tightened.** `hc_filter.js` gates are byte-identical to the morning state.
> - **No losing source was blocked.** `ml_crypto_pred`, `multi_asset_scanner`, `stocks_competition` raw, etc. still generate picks.
>
> **The two HC paper-trading losses today** (XRPUSDT + ETHUSDT on the TV `HC` account) would have happened regardless of any change shipped on 2026-04-14. They were admitted by the existing HC filter based on historical forward stats (`drawdown_recovery_rsi_xrp` has fwdWR 67% on n=6), and they failed forward because those stats didn't hold. No report or badge prevents that.
>
> To actually improve results, the follow-up work listed in the Roadmap has to ship: null_ml_solo_source timing fix, goldmine inverse wiring, forward-tracking pipeline audit, META score unlock, regime_terminal decay review. None of that shipped today.
>
> **Treat this audit as a mirror, not a cure.**

## TL;DR — the honest answer

**Mostly true — with four sharp exceptions.** Across the full 3,500-trade closed ledger, the portfolio is *barely* positive: **43.7% win rate, profit factor 1.10, +300% sum PnL** (about +0.18% per average trade). That's roughly coin-flip with a slight right tail. So yes, **most strategies are struggling**.

But the aggregate hides extreme bimodality: **four strategies carry the entire book**, and the other ~20 collectively bleed them dry. If you use the `High Conviction` button or the per-class filter guide, you're effectively avoiding the bottom group.

This post shows the data, names names, and gives concrete TP/SL examples.

---

## Portfolio-level view

```
Total closed picks:  3,500
Wins:                1,531  (43.7%)
Losses:              1,969
Profit factor:         1.10
Cumulative PnL:      +300.4%
Average per trade:    +0.09%
```

**43.7% WR is below random for a trading system** (a 50% WR strategy with a 1:1 R:R would be break-even before fees). The 1.10 profit factor comes from a small number of outlier winners (~80%+ single-trade PnL on leveraged forex) rather than consistent base-rate edge.

## By asset class — where the edge lives

| Class | n | WR | PF | Sum PnL | Verdict |
|---|---|---|---|---|---|
| CRYPTO | 1,787 | 45.7% | 1.27 | **+330.4%** | ⚠️ Marginal overall; selective edge via filters |
| FOREX | 717 | 43.4% | 2.03 | **+214.6%** | ⚠️ PF inflated by leverage math (see caveat below) |
| COMMODITY | 316 | 42.1% | 1.08 | +6.3% | 🟡 Essentially break-even |
| EQUITY | 636 | 40.4% | 0.83 | **−239.3%** | ❌ **Losing money** |
| ETF | 19 | 42.1% | 0.28 | −15.1% | ❌ Dead sample |
| FUTURES | 17 | 5.9% | 0.06 | −1.5% | ❌ Catastrophically bad (tiny sample) |
| BOND | 8 | 50.0% | 25.90 | +4.9% | 🟡 Too small to evaluate |

**The EQUITY bucket is the single biggest drag** — 636 picks, PF 0.83, losing −239% cumulatively. That's an average of −0.38% per equity pick. The new High Conviction button hides this cleanly by rejecting any equity pick that doesn't clear the score≥50 + trust≥3 compound gate, but the raw picks remain in the data.

**FOREX PF 2.03 is mostly a measurement artifact.** Example: `EURUSD=X BUY @ 1.14338 TP 1.15094 SL 1.13834` shows `pnl_pct = +66.76%`. A real move from 1.14338 to 1.15094 is +0.66%, so the reported 66.76% is ~100x the true move. The forex pipeline is reporting leverage-adjusted or notional-scaled PnL in the same field as unlevered crypto PnL, and the profit factor inherits the scaling asymmetry. Take FOREX PF 2.03 with heavy skepticism until that scaling is fixed.

---

## The four consistent winners (by source system, min n=30)

These are the strategies that **actually carry edge** on the closed-pick ledger. If you listen to only these, your book looks like a real trading system. If you also listen to everything else, you get the 43.7% aggregate WR.

| Source system | n | WR | PF | Sum PnL | TP hits | SL hits | Expired |
|---|---|---|---|---|---|---|---|
| **claude_gainer_st** | 466 | **56.4%** | **1.94** | **+232.9%** | 103 | 91 | **272** |
| **luxalgo_filters** | 87 | **58.6%** | **2.11** | +88.6% | 2 | 2 | 0 |
| **super_signals** | 130 | **54.6%** | 1.30 | +42.1% | 0 | 0 | 0 |
| **multi_asset_copytrader** | 747 | 46.2% | **1.53** | +55.5% | 0 | 0 | 6 |

Notes:

- **claude_gainer_st** is the single strongest source, delivering +232% on 466 trades with a 2:1 R:R skew. But **58% of its picks (272/466) expire before reaching TP or SL** — the edge is coming from the 194 that do resolve to a level, not from holding-to-outcome.
- **luxalgo_filters** has the highest WR (58.6%) but only 4 of 87 picks report explicit TP/SL hits. The rest are resolved via `WON`/`LOST` binary labels (see the data-quality section below).
- **super_signals** and **multi_asset_copytrader** together have **0 reported TP_HIT and 0 reported SL_HIT events across 877 trades**. Their outcomes are resolved entirely via `WON`/`LOST` labels without attribution to a TP or SL level. This is a **critical data gap** — we know they're profitable, but we can't tell you whether they're profitable because the TP is set well or because the strategy avoids losing trades entirely.

## The five consistent losers

| Source system | n | WR | PF | Sum PnL |
|---|---|---|---|---|
| **ml_crypto_pred** | 113 | **16.8%** | 0.30 | **−131.0%** |
| **multi_asset_scanner** | 71 | **16.9%** | 0.49 | −10.3% |
| **stocks_competition** | 379 | 38.0% | 0.76 | **−220.2%** |
| **alpha_engine_fast** | 80 | 40.0% | 0.52 | −11.1% |
| **cta_replicator** | 41 | 36.6% | 0.73 | −2.1% |

- **stocks_competition** is the single biggest money-bleeder in the entire book (−220% on 379 trades). This is the source that specializes in the EQUITY class and explains most of the EQUITY bucket's −239%.
- **ml_crypto_pred** has a 16.8% WR — significantly worse than random. The inverse of this strategy (SHORT when it says LONG) would have ~83% WR theoretically. Candidate for `inverse_ml_crypto_pred` via the mutation-before-kill protocol.
- **multi_asset_scanner** at 16.9% WR on 71 trades is the second-worst WR in the book.

Combined drain from these five: roughly **−375% cumulative PnL** across 684 trades. The book's +300% overall is only positive because the top four winners contribute ~+420%, offsetting the losers by ~45 points.

---

## TP/SL examples — concrete trades

### Crypto winner with clean arithmetic

```
HYPEUSDT  LONG
  entry:  0.050472
  TP:     0.054510  (+8.0%)
  SL:     0.048453  (−4.0%)
  R:R:    2.00
  exit:   TP_HIT
  source: copy_trader_intel / copy_hl_lb
```

This is what "working" looks like. Clean 2:1 reward:risk, entry held, TP hit.

### Crypto winner from claude_gainer_st

```
ARBUSDT  LONG
  entry:  0.1094
  TP:     0.12010  (+9.8%)
  SL:     0.10329  (−5.6%)
  R:R:    1.75
  exit:   +11.15% WIN
  source: claude_gainer_st
```

### Crypto loser — SL was closer than the actual loss

```
ALGOUSDT  SHORT
  entry:  0.1020
  TP:     0.10098  (+1.0% target)
  SL:     0.10282  (−0.8% stop distance)
  R:R:    1.25
  exit:   −10.39% LOSS
  source: alpha_engine
```

This is a **red flag**: the SL was 0.8% away from entry but the trade lost 10.4%. The stop either wasn't enforced, or the pick was held past the stop level on a price gap, or the pnl_pct field is recording a leveraged number. Either way, it's an inconsistency between the published R:R geometry and the actual realized PnL. Happens frequently on `alpha_engine` crypto picks.

### Equity winner — the picture when it works

```
OPEN (Opendoor)  LONG
  entry:  4.445
  TP:     4.8006
  SL:     4.2672
  exit:   TP_HIT, +22.61%
  source: stocks_competition / Classic Momentum
```

**Note this is from `stocks_competition`**, the same source that is the single biggest loser overall (−220% aggregate). The point isn't that stocks_competition is worthless — it's that its *Classic Momentum* strategy sometimes produces genuine winners, but the source's other sub-strategies lose badly enough to drag the whole pool to PF 0.76.

### Equity loser — max-hold protection failed

```
IONQ  LONG
  entry:  34.32
  TP:     39.47
  SL:     31.57
  intended hold: 3 days
  actual  hold: 22 days
  exit:   "Max hold exceeded (22d > 3d)", −14.63%
  source: multi_asset_institutional / penny_deep_oversold
```

The pick was held **7× longer than its own max_hold rule**, drifted below entry, and still never hit SL — it was closed on a time-exit overrun. Same pattern on RIOT (−11.80%), same strategy. This isn't a bad strategy; it's a **broken exit-management pipeline** for the strategy.

## What exit labels actually look like

This is the split across all 3,500 closed picks:

```
LOST         557   (16%)  ← binary label, no TP/SL attribution
EXPIRED      480   (14%)  ← time-based close, no TP/SL
WON          454   (13%)  ← binary label
SL_HIT       452   (13%)
SL           388   (11%)  ← alt label for same event
TP_HIT       256    (7%)
TP           204    (6%)
TIME_EXIT     85    (2%)
TIME          82    (2%)
WIN           49    (1%)
other        593   (17%)
```

**Only ~912 of 3,500 picks (26%) explicitly hit a TP or SL level.** The majority are resolved via binary `WON`/`LOST` labels or time-based exits. That's the single biggest consistency problem: most strategies don't actually let their own TP/SL geometry play out, and we can't tell after the fact whether a `WON` pick won because the strategy was right or because it got lucky on a time-exit.

Per asset class:

| Class | TP hits | SL hits | Expired | TP:SL ratio |
|---|---|---|---|---|
| CRYPTO | 514 | 735 | 453 | 0.70 |
| FOREX | 248 | 310 | 80 | 0.80 |
| EQUITY | 91 | 197 | 185 | 0.46 |
| COMMODITY | 131 | 161 | 9 | 0.81 |

**Crypto hits SL 1.4x more than TP. Equity hits SL 2.2x more than TP.** A strategy needs asymmetric payoff (R:R > 2:1) to be profitable on that TP:SL ratio, and most of our active strategies are set to R:R ~1.5-2.0. That's why PF on the raw book is 1.10 instead of something respectable.

## Data-quality issues worth calling out

1. **FOREX PnL scaling bug.** Reported `pnl_pct` on forex picks is 50–100× the actual underlying move. Examples: AUDUSD=X +95.58%, EURUSD=X +66.76%, GBPJPY=X +76.13%. These are leveraged notional PnL being recorded in the same field as unlevered crypto PnL. The FOREX +PF 2.03 aggregate is therefore not directly comparable to CRYPTO PF 1.27.
2. **Issue #186 — LOST labels are binary outcomes, not exit reasons.** 557 picks are tagged `LOST` without a distinction between SL_HIT, time-expiration, manual close, or delisting. Only 2 of those 557 have positive PnL (they shouldn't), confirming the label at least doesn't misclassify signs — but the attribution problem prevents any TP/SL tuning analysis on that 16% of the book.
3. **`super_signals` and `multi_asset_copytrader` report zero TP_HIT / zero SL_HIT on 877 trades.** Their exit labels are all in the `WON`/`LOST` binary space. You can't tune their TP/SL without wiring proper exit attribution upstream in those source systems.
4. **Time-exit overrun.** `multi_asset_institutional`'s `penny_deep_oversold` strategy has a documented max-hold of 3 days but at least 2 sample picks (IONQ, RIOT) were held 22+ days before closing. The exit manager is not enforcing the strategy's own max-hold rule.

## So — is nothing consistent?

**No. Four things are consistent. Most other things are not.**

| What's consistent | Evidence |
|---|---|
| `claude_gainer_st` is profitable | 56.4% WR / PF 1.94 / +232.9% on n=466 |
| `luxalgo_filters` is profitable | 58.6% WR / PF 2.11 on n=87 |
| `super_signals` is profitable | 54.6% WR / PF 1.30 on n=130 |
| `multi_asset_copytrader` is profitable | 46.2% WR / PF 1.53 on n=747 |
| CRYPTO with Score≥50 + Trust≥3 | PF 1.98 on n=689 (per MERCURYPROMPT.md) |
| EQUITY with Score≥50 + Trust≥3 | PF 2.62 on n=119 (per MERCURYPROMPT.md) |
| FOREX with FwdWR≥50% | PF 1.62 on n=466 (per MERCURYPROMPT.md) |

| What's NOT consistent | Evidence |
|---|---|
| `ml_crypto_pred` | 16.8% WR, PF 0.30, −131% |
| `multi_asset_scanner` | 16.9% WR on n=71 |
| `stocks_competition` raw | 38% WR, PF 0.76, **−220%** |
| `alpha_engine_fast` | 40% WR, PF 0.52 |
| The EQUITY pool as a whole | 40.4% WR, PF 0.83, **−239%** |
| ETF (19 picks) | PF 0.28 |
| FUTURES (17 picks) | 5.9% WR |
| `alpha_engine` SHORT R:R 1.25 setups on crypto | See the ALGOUSDT SHORT example — realized loss 12× the stated SL distance |
| Equity time-exit management | IONQ/RIOT held 22 days on a 3-day max_hold rule |

## What to do about it (if you use the dashboard for signals)

1. **Use the HIGH CONVICTION button.** It's been wired to the per-class validated-edge filter ([PR #200, 2026-04-14](2026-04-14-codebuff-session-progress.md)). It drops you from 74 actives to 2–6 picks, all of which sit in the cohort with proven edge. It hides the bottom 70% of sources that are collectively losing money.
2. **If you want more picks** than the High Conviction button surfaces, open the `Trusted` filter OR manually filter the Active Picks table by `FWD WR ≥ 45%` and `Score ≥ 40`. The new **FWD WR** and **FWD N** columns (PR #211 shipping today) let you sort by the same field the HC filter evaluates.
3. **Never click a pick from these sources without an independent reason:** `ml_crypto_pred`, `multi_asset_scanner`, raw `stocks_competition`, `alpha_engine_fast`, `cta_replicator`, or any pick with `regime_terminal` on EQUITY showing fwdWR<45%.
4. **Treat forex PF claims with suspicion** until the pnl_pct scaling bug is fixed.
5. **Treat any `alpha_engine` crypto pick with R:R < 1.5** as high risk — the realized loss on those setups has been consistently larger than the stop distance implies.

## What's in the pipeline to fix this

- `inverse_goldmine_stocks` baby strategy ([PR #208, 2026-04-14](2026-04-14-drift-remediation-session.md)) — validates whether flipping a 21% WR loser yields a ~79% WR winner. First forward-test results in ~7-14 days.
- `inverse_ml_crypto_pred` is a natural follow-up candidate (16.8% WR → theoretical 83% inverse). Not shipped yet.
- Exit-attribution fix for `super_signals` and `multi_asset_copytrader` — proper TP_HIT/SL_HIT labeling instead of binary WON/LOST.
- FOREX pnl_pct scaling fix.
- Max-hold enforcement for `multi_asset_institutional` strategies.
- META score unlock via `multi_asset_copytrader` penalty trace — the single near-miss equity pick that would prove EQUITY can have HC edge.

---

## Bottom line

The claim *"strategies have all been struggling, nothing seems actually consistent"* is **directionally right but specifically wrong**. Most strategies are struggling. A specific named set of four are not. The High Conviction button is the tool that separates the two groups cleanly. If you're looking at the raw Active Picks feed and feeling like nothing is reliable, that's because **the raw feed is ~43.7% WR and contains loser-heavy sources**, but the filtered view removes them. Use the filters.

*Generated from `audit_dashboard/data/dashboard_data.json` (3,500 closed picks, 2026-04-14). All source systems, WR, PF, and sample sizes are pulled directly from the published ledger. Individual trade examples are real closed picks verifiable in the Closed Picks tab.*
