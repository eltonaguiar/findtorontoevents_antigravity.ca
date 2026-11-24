# Surface review: `/audit` vs `/audit3` (2026-11-19)

Reviewed live at 2026-11-19 ~05:15Z:
`https://findtorontoevents.ca/audit3/` (31,535 B, ledger 227 KB),
`https://findtorontoevents.ca/audit/` (1,437,176 B),
`/audit/data/money_ready_verdict.json` (50 KB) and the dashboard payload
(`dashboard_data.json`, 26 MB, generated 04:04:16Z).

**In plain terms:** audit3 is the honest scoreboard, but it is scoring roughly a
fifth of the game and doesn't say so. `/audit` scores more of the game but keeps
tiles its own payload contradicts. Neither can answer "is anything worth real
money" with a single number a reader can trust, because they do not agree on the
denominator.

---

## 1. Headline: audit3 is concise because it is narrower, not because it is tighter

| Quantity | `/audit` payload | audit3 |
|---|---|---|
| closed picks in existence | **16,330** | — |
| "valid" closed picks | **7,901** | — |
| excluded for integrity | **7,502** (46%) | — |
| auto-expired excluded | **9,100** | — |
| resolved rows | 8,731 | — |
| rows actually scored | — | **3,500** |
| window | all history | 2026-02-21 → 2026-11-19 (246 days) |
| tested cells | — | 45 |
| verdict | 0 money-ready | 0 PROVEN, 11 KILL, 34 WEAK, 126 INSUFFICIENT |

audit3 judges **21.4% of all closed picks**. The other 78.6% are too old, excluded
for integrity, or auto-expired. A clean recent window is a defensible choice, but
the page never states it and the excluded cohorts are analysed nowhere. Two matter:

- **7,502 integrity-excluded** is 46% of the book. Excluding nearly half the sample
  is itself a selection decision. If those rows are worse than the kept ones (ghost
  rows, WON-vs-PnL contradictions), the retained 3,500 flatter the system; if they
  are mostly benign expiries, the exclusion is buying no honesty and costing power.
- **9,100 auto-expired** — the resolver records **3,467 expired zero-pnl rows**, 44
  stale exits beyond the planned stop, 23 clamped losses and 3 rows missing
  `closed_at`. A zero-PnL expiry is not a neutral observation: the trade neither hit
  TP nor SL, and dropping those rows changes the win rate.

**Action A1:** publish an "excluded cohorts" panel with counts and reasons, and state
in the audit3 header which fraction of the book it is judging.

---

## 2. The two surfaces disagree about the same asset classes

| Class | `/audit` (money_ready_verdict) | audit3 (net of flat slippage) | Divergence |
|---|---|---|---|
| CRYPTO | n=3,724, WR 35.8%, PF 0.917 | n=1,851, WR 39.8%, PF 0.72 | PF differs 0.20 |
| EQUITY | n=256, WR 60.2%, PF 0.970 | n=761, WR 45.9%, PF 1.05 | n differs 3×, WR 14pp |
| ETF | n=52, WR **1.9%**, PF **0.020** | n=584, WR 43.1%, PF 0.98 | unreconcilable |
| FOREX | n=623, WR 31.9%, PF 0.653 | n=211, WR 34.1%, PF 0.69 | close |
| COMMODITY | n=232, WR 40.5%, PF 1.042 | n=55, WR 14.5%, PF 0.12 | opposite signs |

The ETF row is the tell: 1.9% WR and PF 0.02 on n=52 cannot coexist with 43.1% and
0.98 on n=584 unless the two surfaces select different rows — or one is wrong. Until
that is explained, no ETF conclusion on either page is loadable.

**Action A2:** one canonical resolved view (`resolved_closed_picks_net`) with class
slippage applied and exclusions explicitly flagged, queried by both surfaces. The
schema spec already defines the columns this needs.

---

## 3. What `/audit` already computes that audit3 should absorb

### 3.1 Measured slippage (audit3 uses a flat class constant)

| Class | n | measured slippage | avg PnL/trade | slippage as % of PnL | flag |
|---|---|---|---|---|---|
| CRYPTO | 11,341 | 0.0997% | +0.268% | **37%** | CRITICAL |
| ETF | 602 | 0.0500% | +0.021% | **234%** | CRITICAL |
| FUTURES | 19 | 0.1500% | −0.199% | 75% | CRITICAL |
| BOND | 35 | 0.0500% | −0.189% | 26% | CRITICAL |
| COMMODITY | 135 | 0.1500% | −1.112% | 13% | WARNING |
| EQUITY | 1,696 | 0.0500% | −0.373% | 13% | WARNING |
| FOREX | 692 | 0.0200% | −0.225% | 9% | — |

78 strategies flagged, 36 critical. The good news: audit3's flat assumptions
(CRYPTO 0.15%, ETF 0.08%) sit *above* measured (0.0997%, 0.05%), so its kills are
conservative — no false kills from cost modelling. The bad news: a single class
number cannot express "ETF edge is 234% consumed by slippage", which is the most
actionable cost fact on either page.

**Action A3:** per-strategy measured slippage where available, class constant as the
fallback.

### 3.2 Walk-forward out-of-sample, by class

| Class | folds | OOS WR | OOS Sharpe |
|---|---|---|---|
| EQUITY | 33 | 46.2% | **+0.608** |
| ETF | 53 | 45.4% | +0.212 |
| CRYPTO | 32 | 38.4% | **−2.077** |
| FOREX | 3 | 44.0% | −4.382 |
| COMMODITY | 3 | 0.0% | −97.571 |
| BOND | 30 | 38.3% | −263.324 (degenerate) |

This is the most decision-relevant table in the payload and it is on neither page's
headline. EQUITY is the only class with a positive OOS Sharpe on a real fold count;
CRYPTO — 60% of the volume — is negative out-of-sample across 32 folds.

### 3.3 Two kill lists that do not reconcile

kill_switch reports **42 kills of 56 evaluated** (75.0%); audit3 reports **11**. The two lists share **1** strategy names (futures_momentum). They are built from different cohorts under different gates (kill_switch covers 181
registered strategies, 56 with enough data; audit3 scores 45 cells on the 3,500-pick window),
so divergence is expected. What is not expected is publishing two kill lists that a reader
cannot reconcile: "killed" then means "killed by one particular pipeline", which nobody
states. Either reconcile the vocabularies or label each list with the pipeline that made it.

### 3.4 Gate pressure

- 134 picks before quality gates → **15 active**, 119 filtered (`signal_to_trade_pct` 33.9%).
- PCG5 shadow: 134 evaluated, **119 would be rejected (89%)**.
- 89 names **demoted** from "PROVEN" in the last run by the badge audit.
- Verified-alpha cohort: 1 active pick, 2,098 realized trades at 45.0% WR, expectancy
  +0.13% — the only positive expectancy on the page, on the least-audited cohort
  (n=2 audited).

---

## 4. Contradictions on `/audit` itself (fix before quoting any tile)

1. **Smart picks show two realities.** `smart_picks_feed.total_scored = 0` and
   `picks.smart_picks = []`, while `smart_picks_snapshot_summary` reports **95 picks,
   68.4% WR, 45 resolved batches**. One tile is stale or mis-scoped; a reader sees
   "nothing scored" and "68% win rate" on the same page.
2. **`tier2_proven_strategies` contains no proven strategy.** Its three cards are
   `signal_validation` (`dead`, n=102), `mega_mutation` (`monitoring`, n=105) and
   `rl_agent` (`empty`, n=0). The label promises the opposite of its content.
3. **EQUITY's 60.2% WR with PF 0.97 is not skill.** Average win 3.95% vs average loss
   3.08% breaks even near 44% WR, so 60% WR at PF<1 means the exit geometry harvests
   small wins and eats larger losses in the tail. Win rate is the wrong headline; a
   payoff-asymmetry tile would tell the truth in one number.
4. **Three vintages on one page.** `analyst_leaderboard`/`analyst_active_calls` last
   updated `2026-03-26`, `walkforward` regenerated 02:47, `money_ready_verdict` 04:03,
   payload 04:04 — presented as one current view.

---

## 5. Actions, in the order that changes decisions fastest

| # | Action | Why it matters | Effort |
|---|---|---|---|
| **A1** | Excluded-cohort panel + "judging X of Y picks" on audit3 | 78.6% of the book is unaccounted for | S |
| **A2** | One `resolved_closed_picks_net` view both surfaces query | ETF 1.9% vs 43.1% WR makes both pages untrustworthy | M |
| **A3** | Per-strategy measured slippage in audit3 | replaces a class constant with the actual cost | S |
| **A4** | Surface **selection alpha** as the per-class headline; demote raw PF | only metric separating skill from beta; already measured: CRYPTO LONG −0.442%/pick, ETF −0.272%/pick | M |
| **A5** | One smart-picks number, one definition | two contradictory tiles on one page | S |
| **A6** | Retire the `tier2_proven_strategies` panel until a card is `alive` | a "proven" panel with `dead`/`empty` cards teaches readers to ignore labels | XS |
| **A7** | Port walk-forward OOS + kill-switch reconciliation into audit3 | OOS Sharpe is the decision metric; two unreconciled kill lists | M |

---

## 6. What the numbers say a winning strategy has to look like

- **CRYPTO directional picks are the problem, not the product.** 3,724 resolved,
  PF 0.917, OOS Sharpe −2.08 across 32 folds, selection alpha −0.442%/pick versus
  holding the same coin. No exit tweak repairs a minus-2 Sharpe.
- **ETF intraday is a cost artefact.** Measured slippage consumes 234% of per-trade
  PnL. Only monthly-cadence rotation survives that, and audit3's −0.272%/pick alpha
  says even that is currently negative.
- **EQUITY is the only class with positive OOS Sharpe (+0.61, 33 folds)** and a
  near-break-even PF. That is where a premium pod belongs — trend/momentum or PEAD
  with symmetric, tested exits — not another crypto scanner.
- **FOREX cannot be judged**: PF 0.653 on 623 picks, 3 walk-forward folds, and a price
  table ending 2026-02-09. Retire it from the money path until backfilled.
- **The barbell is the only structure these numbers support**: low-cost beta core, a
  small premia sleeve in the one class with positive OOS statistics, and no
  speculative sleeve until selection alpha is positive in two regimes.

The shortest path from "0 money-ready" to something sizeable is therefore not a new
strategy. It is: **agree the denominator (A2), state what is excluded (A1), make
selection alpha the headline (A4), and put the next research pod where OOS Sharpe is
already positive (EQUITY) instead of where 60% of the volume is.**

---

## 7. Limitations

- Everything here is what the surfaces *publish* at 04:04Z; I did not re-run scanners
  or re-resolve picks.
- Cross-surface class comparisons are indicative, not like-for-like: cohorts differ
  (16,330 vs 3,500 rows) and cost models differ (measured vs flat).
- `BOND`/`COMMODITY` walk-forward Sharpe values are degenerate (3 folds, huge std) and
  are not evidence either way.
- audit3's doctrine (innocent until proven guilty) means its `WEAK` verdicts are not
  negative findings; nothing here overturns them.
