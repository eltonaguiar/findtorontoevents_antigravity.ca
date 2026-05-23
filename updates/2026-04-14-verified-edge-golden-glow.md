# New: Verified Edge Badge — "Golden Glow" for picks with real history

**Date:** 2026-04-14
**Dashboard:** [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit/)
**Companion post:** [Strategy Consistency Audit](2026-04-14-strategy-consistency-audit.md) — the data that motivated this.

> ## ⚠️ THIS IS A VISIBILITY FEATURE, NOT A STRATEGY IMPROVEMENT
>
> Read this first. This feature **does not improve pick quality** and **did not prevent today's two HC paper-trading losses** (XRPUSDT + ETHUSDT on the TradingView `HC` paper account). Nothing about this change makes a pick more likely to win.
>
> What it does: **surface the gap between closed-ledger edge and live-pick edge as a per-row badge**, so you can see at a glance that the active feed currently contains zero picks with verified track records. Today the EDGE column is a row of em-dashes. That is honest and intentional.
>
> What it does NOT do: (1) change any filter threshold, (2) alter any TP/SL level, (3) remove any losing source, (4) replace any strategy, (5) block any pick from the active feed, (6) change what the HC button admits. It is a CSS class + a client-side index, nothing more.
>
> **If you trusted GOLDEN-looking picks today, you would still have seen the same 2 losses, because no pick today carries a GOLDEN badge.** The feature's job is to make that absence obvious, not to conjure winners out of thin air.
>
> **To actually improve pick quality would require strategy-level work** — fixing the `null_ml_solo_source` scoring timing bug (see drift remediation post), wiring goldmine inverse (PR #208) to the live scanner, investigating why `drawdown_recovery_rsi_xrp` (the strategy that produced today's XRPUSDT loser) has a historical fwdWR of 67% but the two recent closes failed, and auditing the exit logic that stopped both today's losing picks. None of that shipped in this PR. This PR made the **measurement instrument**, not the **strategy**.

## The problem this solves

When you open the Active Picks tab, you see ~70-100 picks coming from ~20 source systems. A handful of those systems carry real edge (see the companion audit post for the specific 4), but the rest are collectively below coin-flip. Nothing in the UI told you *pick-by-pick* whether the system that generated it has actually won on this exact symbol before.

You asked:

> "If we have winners — a symbol/strategy combo — it should be tagged in a golden glow or something, and a certain label for ones that survive backtest + forward test."

This post documents exactly that feature, ships today, and tells you where to look for it.

## What shipped

A new **EDGE** column + row-level glow in the Active Picks table, driven by a client-side index built from the 3,500-pick closed ledger.

### The criteria

Two tiers. Picks either earn one, the other, or neither.

#### 🏆 GOLDEN (crown badge + pulsing gold row glow)

- **Symbol-specific history**: the exact (strategy, symbol) combo has **n ≥ 5 closed trades with WR ≥ 60% and PF ≥ 2.0** in `audit_dashboard/data/dashboard_data.json → picks.recent_closed`
- **AND Strategy overall is not decayed**: the strategy's full-ledger track record across all symbols is **n ≥ 30 with WR ≥ 50% and PF ≥ 1.3**

Both halves must pass. This maps to "survives backtest AND forward test" — the closed ledger IS the forward-test history (these are real closed trades, not synthetic backtests), and the dual gate ensures the combo didn't just get lucky on a small sample while the parent strategy is otherwise bleeding.

#### ✓ VERIFIED (green check badge + green border row glow)

- **Strategy overall is proven**: n ≥ 30, WR ≥ 55%, PF ≥ 1.5 across all symbols
- No symbol-specific combo requirement — used when a pick uses a proven strategy on a symbol that doesn't yet have enough combo history

#### — (em-dash, no glow, dimmed cell)

- Neither the (strategy, symbol) combo nor the strategy overall meets the bar
- **This is the honest default today** for the vast majority of active picks

## Where you'll see it

### 1. The new **EDGE** column in Active Picks

Open **[findtorontoevents.ca/audit](https://findtorontoevents.ca/audit/)** → **Active Picks** tab. Scroll the column headers and you'll find a new column labeled **EDGE** (default visible). It renders one of three values:

- `👑 GOLDEN` — animated gold gradient badge with a crown icon
- `✓ VERIFIED` — green rounded badge with a checkmark
- `—` — dimmed dash

Hover any badge for a tooltip showing the exact stats used for that classification (n, WR, PF on the combo and on the strategy-wide record).

Click the **EDGE** column header to **sort** — GOLDEN rises to the top, then VERIFIED, then blank.

### 2. Row-level visual glow

Rows with a GOLDEN pick get an **animated pulsing gold background gradient** and a thick gold inset border. You can spot them from across the room scrolling the table — they literally pulse. VERIFIED rows get a subtle green gradient and border, but no animation.

### 3. The column gear

If you don't see the EDGE column, open the ⚙️ column settings button on the Active Picks toolbar and enable `EDGE`. It ships default-on but your localStorage preferences can override.

### 4. The honest reality today

**When you click the button and scroll the table today, you will most likely see ZERO golden rows.** That's not a bug — it's the finding the companion audit post surfaced:

- The closed ledger has **43 golden (strategy, symbol) combos** and **5 verified strategies**
- But today's 74 active picks don't use any of those exact combos OR strategies
- Translation: we have historical proof of edge, but the systems that currently generate picks aren't the systems that proved edge

The empty GOLDEN column is the feature working as intended — it makes the gap between closed-book edge and active-book edge **visible pick-by-pick** instead of hidden behind an aggregate win-rate number.

## What historical winners exist (for context)

These are the 43 combos currently flagged as GOLDEN in the closed ledger. If any of them ever generate a new active pick, it will glow gold in your table:

### Top GOLDEN combos (selected)

| Symbol | Strategy | n | WR | PF | Sum PnL |
|---|---|---|---|---|---|
| **ARBUSDT** | `st_multi_day_momentum` | 28 | 67.9% | 3.55 | +72.2% |
| **XOM** (stock) | `Breakout Momentum` | 10 | 80.0% | 4.17 | +34.4% |
| **MRK** (stock) | `Classic Momentum` | 10 | 80.0% | 8.83 | +34.1% |
| **CVX** (stock) | `Breakout Momentum` | 9 | 88.9% | 5.97 | +33.0% |
| **SOLUSDT** | `st_rsi_momentum_confluence` | 11 | 100% | 99.0 | +20.4% |
| **BNBUSDT** | `st_fear_greed_contrarian` | 14 | 92.9% | 95.85 | +19.2% |
| **XRPUSDT** | `st_obv_support_divergence` | 8 | 100% | 99.0 | +18.7% |
| **ADAUSDT** | `st_obv_support_divergence` | 7 | 100% | 99.0 | +16.1% |
| **OPUSDT** | `st_fear_greed_contrarian` | 21 | 61.9% | 3.42 | +16.5% |
| **STXUSDT** | `luxalgo_confluence` | 7 | 85.7% | 11.17 | +16.0% |

(Full list: 43 combos in the closed ledger as of 2026-04-14 snapshot.)

### The 5 VERIFIED strategies

| Strategy | n | WR | PF | Sum PnL |
|---|---|---|---|---|
| `st_obv_support_divergence` | 81 | 75.3% | 8.72 | +107.8% |
| `luxalgo_confluence` | 87 | 58.6% | 2.11 | +88.6% |
| `st_multi_day_momentum` | 39 | 56.4% | 2.75 | +66.1% |
| `strong consensus (alpha_engine, ml_crypto_pred)` | 106 | 59.4% | 1.58 | +60.6% |
| `st_rsi_momentum_confluence` | 90 | 67.8% | 1.52 | +35.9% |

## How the index is built

- Runs **once per page load**, client-side, from `D.picks.recent_closed` (the same data the dashboard already loads for closed picks).
- No server change required.
- Index rebuilds automatically when the dashboard regenerates (hourly workflow cycle) because the closed-picks ledger is refreshed on each generation.
- Code path: `buildVerifiedEdgeIndex()` → `window._verifiedEdgeIndex` → `getVerifiedTier(pick)` → rendered in the EDGE column and applied as a row CSS class.
- Check `console.log` — you'll see a line at load time:

```
[verified-edge] indexed 3500 closed picks → 43 golden (strategy,symbol) combos, 5 verified strategies
```

## Interaction with existing filters

- **HIGH CONVICTION button**: the HC filter is separate and runs on its own criteria (`hc_filter.js` gates + per-class validated edge). A pick can be GOLDEN without passing HC, or pass HC without being GOLDEN. These are independent signals by design. Best practice: click HC first to narrow to the ~3 picks that meet conviction criteria today, then check their EDGE column — if any of them also glow gold, those are the strongest candidates in the entire system.
- **Smart Picks tab**: same filtering logic applies to smart_picks — rows that meet GOLDEN criteria will glow in that table too.
- **Column sort**: clicking the EDGE header sorts GOLDEN > VERIFIED > blank, so the highest-quality rows rise to the top regardless of score.

## What to do when you see a glow

1. **GOLDEN row**: this is a pick where both the (strategy, symbol) combo and the parent strategy have statistically meaningful positive track records. **High priority for paper trading, manual follow-up, or TradingView account placement.** The `HC` paper account on TV should prioritize these over non-verified HC picks.
2. **VERIFIED row**: the strategy is proven but this specific symbol is untested. **Medium priority.** Treat as a normal HC-gate pick with the extra comfort that the strategy isn't a loser.
3. **Blank (—)**: the default state. **No extra signal.** Don't avoid these picks just because they're unlabeled — absence of GOLDEN just means no proof yet, not proof of no edge. But when in doubt, sort by EDGE desc and take the top rows.

## Why this matters for the "no edge" observation

The companion [Strategy Consistency Audit](2026-04-14-strategy-consistency-audit.md) showed the book is 43.7% WR / PF 1.10 — nearly coin-flip — with extreme bimodality between 4 good sources and 20+ bad ones. This new feature **takes that same insight down to the pick level**:

- Raw Active Picks feed: ~74 picks, ~0 verified winners → "feels like coin flip"
- After HC button: ~3 picks, still mostly blank EDGE → "edge via gates, not history"
- After finding a GOLDEN row: this exact pick has been a winner this many times on this exact symbol → "real confidence"

If the book ever has meaningful edge again, it'll be because GOLDEN rows start appearing in the active feed and stay there week over week. We'll know — no more guessing.

## What's next

1. **Alerting on GOLDEN appearance**: if a GOLDEN pick ever enters the active feed, trigger a Slack/Discord ping and auto-place it on the TradingView `HC` paper account. No code yet — design phase.
2. **Weekly GOLDEN count trend**: add a sparkline to the health monitor (`tools/hc_health_monitor.py`) showing `n_golden_active` per run, so we can watch it climb (or stay at 0).
3. **"Unlock" alerting**: if a strategy *used to* be VERIFIED but has since dropped below the threshold (decay), flag it so we don't keep trusting stale winners.

## Tech notes

- **File changed**: `audit_dashboard/template.html` (new index + CSS keyframes + column + row class)
- **Deploy**: follows the standard hourly `audit-dashboard.yml` workflow. Live on `findtorontoevents.ca/audit` approximately 1 hour after merge.
- **Browser compatibility**: uses only standard HTML/CSS/JS features present in every modern browser; no new dependencies.
- **Cost**: the index build is O(n) over closed picks (~3500) at load time. Sub-50ms on typical browsers.
