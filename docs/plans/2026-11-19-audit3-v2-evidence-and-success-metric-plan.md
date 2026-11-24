# audit3 v2 — evidence registry, success metric, and the full surface map

**Status:** plan (P0 shipped 2026-11-19)
**Owner surface:** `/audit3` (`alpha_engine/audit3_tribunal.py` + `audit_dashboard/audit3.html`)
**Constraint:** audit2 and its Google/`agy` swarm are off limits. audit3 touches
none of their files, workflows or pages.

---

## 0. The principle we are now enforcing

> Innocent until proven guilty. Absence of proof of edge is not proof of harm.

Every strategy, symbol, section, instrument type and risk level starts in
`NOT PROVEN — keep observing`. Promotion requires statistical proof of edge;
retirement requires statistical proof of harm (net expectancy CI entirely below
zero, surviving Benjamini–Hochberg). Nothing is deleted for being unproven.

This matters because the useful finding is usually a **sub-population**: a
section whose aggregate loses money can still contain one asset class that wins
again and again. The ledger now carries a section × class matrix so that case is
visible instead of averaged away.

---

## 1. What "success" means (metric hierarchy)

Right now the dashboard answers "win rate". That is the wrong primary metric: a
30%-WR option-style payoff can be excellent, and a 70%-WR strategy equal to
buy-and-hold can be worthless. audit3 v2 scores in this order.

| Level | Metric | Definition | Why |
|---|---|---|---|
| **M0** | Evidence exists | Resolved rows with entry, exit, timestamp, symbol | No claim without data |
| **M1a** | Benchmark-relative return | Cell net return − benchmark net return over the **same window** | Did we beat just holding the index? |
| **M1b** | Selection alpha | Pick net return − **same-symbol** buy-and-hold over the same entry→exit window | Answers "did we identify the right thing to hold?" |
| **M1c** | Timing alpha | Pick net return − exposure-matched benchmark (fraction of window invested) | Separates stock-picking from market-timing |
| **M2** | Risk-adjusted | Sharpe, Deflated Sharpe, PF, max drawdown, Calmar | Return per unit of pain |
| **M3** | Robustness | Chronological split-half, regime slices, BH q, concentration | Is it repeatable or a lucky month? |
| **M4** | Cost realism | Net after per-class slippage + fee + spread sensitivity | Does it survive contact with a broker? |
| **M5** | Capacity | Edge decay vs size / liquidity bucket | Can it hold real capital? |

**Benchmarks by class** (declared in the ledger, never tuned per cell):

- CRYPTO → BTC-USD buy & hold, plus an equal-weight top-10 basket
- EQUITY → SPY; sector cells additionally vs their sector ETF
- ETF → SPY, and vs the ETF's own buy & hold for rotation strategies
- FOREX → carry basket / DXY-neutral cash
- COMMODITY → front-month roll yield proxy, else flat
- BOND → AGG / TLT buy & hold
- MUTUAL_FUND → category average (survivorship-adjusted)
- PENNY / MEME → **base rate of the universe**, not an index (see §5)

M1b is the headline number for the "we picked the right thing" question. A pick
that returns +40% while the symbol returned +60% over the same window is a
**failure of selection**, and today's ledger cannot see that. It will after P2.

**Decision rule:** a cell is `PROVEN_EDGE` only if M1b (selection alpha) is
positive with CI excluding zero, M2–M4 pass, and BH holds. Positive raw return
with zero selection alpha means "the market did it", and is labelled
`BETA_ONLY`, not proven.

---

## 2. Evidence we already have (inventoried 2026-11-19)

### 2.1 MySQL `ejaguiar1_backtests` (reachable, read-only)

| Table | Rows | Content | Use |
|---|---|---|---|
| `bt_backtest_runs` | 285 | 94 distinct strategies, but **all tagged CRYPTO**; 943 trades total | Seed evidence; class tagging is wrong and must be rebuilt from `symbol` |
| `bt_backtest_trades` | 32,676,918 | Per-trade rows (symbol, direction, entry/exit, pnl_pct, strategy, asset_class) | The real prize — but full scans time out; needs indexed, windowed queries |
| `at_large_backtest_results` | 1,105 | archetype, symbol, params_json, sharpe, sortino, PF, MDD, equity curve, trade log | Parameter-level evidence, already cost-adjusted |
| `at_incubator_backtest_results` | 1,285 | Same shape + `backtest_type` | Mutation/incubator evidence |
| `eagle2_consensus_picks` / `eagle2_methodology` | 15 / 10 | Consensus methodology records | Prior art for the promotion gate |
| `bt_backtest_runs` by strategy | — | `opposite_day` 14 runs/WR 13.9%, `extreme_fear` 10/51%, `Funding Rate Carry` 11/36.4%, `ensemble` 18/32.4% | Immediately testable cells |

**Known defect:** every `bt_backtest_runs` row says `CRYPTO`, including `NZDUSD=X`.
Class must be derived from `symbol`, not trusted from the column. This is
evidence-integrity issue #1 and is cheap to fix.

### 2.2 Backtest JSON already in the repo (77 files matching backtest/results)

High-value ones:

- `audit_dashboard/data/equity_baby_strategies_backtest.json` (442 KB) — equity
  baby strategies, VIX-regime and sector-rotation variants.
- `reports/strategy_bt_crypto_2026-06-11.json` (331 KB) — split R1/R2 protocol,
  cost in bps, top-symbol concentration.
- `reports/strategy_bt_{equity,forex,commodity,bond,futures}_2026-06-11.json` —
  same protocol per class, already includes falsification checks.
- `reports/backtest_path_forward.json` and `_2xcost.json` — `trial_count_N`,
  `cost_mult`, `var_sr_used`: **already Deflated-Sharpe aware**; reuse its
  `trial_count_N` as the multiplicity input instead of re-deriving it.
- `copy_trader_intel/data/backtest_results.json`, `consensus_backtest.json`,
  `quality_backtest_results.json` — copytrader evidence with walk-forward summary.
- `audit_dashboard/data/bond_connors_rsi2_backtest.json`, `hyro_*`,
  `cost_adjusted_walkforward_backtest.json`, `btc_utc_hour_backtest.json`,
  `piotroski_fscore_backtest.json` (value), `etf_sector_rotation_*.json`,
  `equity_momentum_*`, `donchian_52w_volume_backtest.json`.
- `baby_strategies/*_backtest_results.json` — per-strategy lab results.

These are **not** currently joined to the live ledger. That is the cheapest
large win: they already carry n, WR, PF, Sharpe, costs and (sometimes) split-half.

### 2.3 Registries and docs

- `docs/ALL_STRATEGIES.md` — 1,695 lines, 700+ strategies by asset class.
  **Last updated 2026-03-17** (8 months stale) and referenced from
  `updates/index.html` as the central registry.
- `docs/DB_SCHEMA_stocks_backtests_2026-05-15.md` — 5,991-line schema doc for
  `ejaguiar1_stocks` (322 tables) and `ejaguiar1_backtests`.
- `reports/hypothesis_registry.json` — 99 hypotheses, but **16 different status
  spellings** (`FORWARD_OBSERVATION`, `FORWARD_SHADOW`, `forward-shadow`,
  `REGISTERED-UNTESTED`, `PRE-REGISTERED`, …). Needs a canonical enum, or the
  tracker cannot count anything reliably.
- `RECOVERY_PROTOCOL.MD` — **does not exist in this repo.** It is only referenced
  from `WIRED_IN/*` prompts and `.kilo` worktrees. Either recreate it or drop the
  references; a recovery protocol that lives in prompts is not a protocol.

### 2.4 Other `eltonaguiar` repos worth importing

| Repo | Signal |
|---|---|
| `STOCKSUNIFY`, `STOCKSUNIFY2` | TypeScript stock unification UI + data — likely separate symbol/universe logic |
| `CLAWSOFDOOM` | Python; the `claws_of_doom` alias appears in the live trust registry with a 20.6% WR ledger |
| `mikestocks`, `michael2stocks`, `mikestocks_april272025` | Older stock experiments — historical prior art |
| `combined-book-edge-proof` | Explicitly "reference backtest, statistical gates, and paper pilot" — **directly reusable gates** |
| `AIModelBenchmarks` | Free-local vs free-cloud vs paid model benchmarks — relevant to ML strategy attribution |
| `findmutualfunds2` (in-tree dir) | Mutual-fund screener |
| `skyrocket_detector/` (in-tree package) | `feature_engine`, `label_builder`, `model`, `train` — a supervised skyrocket detector already exists |
| `trading_strategies_skyrocket.md`, `penny_stock_research_report.md` | Narrative prior art for penny/skyrocket hypotheses |

---

## 3. Surface-by-surface plan

Every surface gets the same record shape, so one page can compare them:

```
{surface, instrument_type, asset_class, risk_level, n, M1a, M1b, M1c,
 M2_sharpe, M2_dsr, M2_pf, M2_mdd, M4_net_exp, M5_capacity, verdict,
 evidence_provenance[], reconstructed}
```

### 3.1 Active / Closed / Smart Picks / Money-Ready (Tier-2)

- **Now:** closed ledger scored per strategy×symbol×direction, plus the new
  section × class matrix.
- **P1:** replace reconstructed proxies with **native stamps** — have
  `audit_trail/dashboard_generator.py` write `sections: ["smart_picks",
  "money_ready", …]` and the gate decisions onto each closed row. Then the
  matrix stops being a proxy. (Read-only change to the generator's payload; no
  edits to audit2 pages.)
- **P2:** selection alpha vs same-symbol hold, so "smart picks" is judged on
  whether it picked the right names, not whether the market rose.

### 3.2 Copytrader

- Exists: `copy_trader_intel/` (hyperliquid, polymarket, bitget, bybit, bingx
  scrapers; consensus + quality backtests; `strategy_clone_generator`).
- Missing: a **per-trader** resolved ledger. Family-level results (WR 35.8%,
  PF 0.30 on n=81) cannot say whether one trader is excellent and 17 are noise.
- Plan: snapshot each trader's public fills, replay them with the same cost
  model, and score per trader × symbol × hold-time. Verdicts per trader, with
  the same BH harm gate. Survivorship: include traders who stopped posting
  (that is a negative signal, not a missing row).

### 3.3 Kalshi / Polymarket

- Exists: `alpha_engine/kalshi_signals.py`, `polymarket_signals.py`,
  `prediction_market_consensus.py`, `copy_trader_intel/polymarket_scraper.py`,
  `audit_dashboard/data/copy_pm_high_certainty_candidates.json`.
- The ledger currently has **n = 1** resolved prediction-market pick, so nothing
  can be judged. Needs its own resolution feed: market id, side, entry price,
  resolution, payout, fee.
- Success metric is different: **Brier score / log-loss and calibration**, not
  win rate. A 90¢ contract that resolves true is a 11% return and a good trade;
  a 10¢ lottery that pays is not evidence of skill. Score: realised edge per
  contract vs market-implied probability, with CI, plus calibration curve.
- Plan: build `prediction_market_ledger.json` from market history; score
  calibration + edge; no promotion from a single resolution.

### 3.4 Reverse-engineering attempts

- What exists: copy-trade clones, `strategy_reverse_engineer.py`,
  `winner_reverse_engineer.py`, `inverse_edge_system.py`, `genome/*` mutation
  engines, luxalgo/confluence replication.
- Risk: reverse-engineered rules are fitted to the winners they were derived
  from — in-sample by construction. They must be scored on **out-of-sample
  forward rows only**, and the derivation window must be recorded.
- Plan: every reverse-engineered strategy carries `derived_from` (symbols, date
  range, n) and is only eligible for `CANDIDATE` on post-derivation rows. This is
  a hard gate, not a note.

### 3.5 Skyrockets / penny / cheap stocks

- Exists: `skyrocket_detector/` (features, labels, model, train),
  `penny_stock_research_report.md`, `trading_strategies_skyrocket.md`,
  `rocket_scanner*.py`, `gainer_predictor_score.py`.
- The metric must be **base-rate relative**. If 4% of all sub-$5 stocks double
  within 60 days, a detector with a 6% hit rate is +50% relative lift; a detector
  with 3% is worse than random. Raw "+300% winner" screenshots prove nothing.
- Plan: build the universe base rate per period (all listed sub-$5 / sub-$1B
  names), then score detector precision@k, lift over base rate, and expectancy
  including the losers (most penny picks go to zero). Evaluate in the
  **aggressive** risk sleeve only, with hard position caps.
- Success for this sleeve is explicitly *not* win rate: it is
  `P(≥2x) / base_rate` and positive net expectancy after 30%+ slippage.

### 3.6 Value / long-term

- Exists: `piotroski_fscore_backtest.json`, `quality-minus-junk` strategy,
  `value_screener_runner.py`, `mf_screener.py`, `findmutualfunds2/`.
- Metric: multi-year holding, so **annualised** return vs SPY, plus
  drawdown and turnover. Selection alpha vs same-symbol hold over years is the
  honest test; a value screen that buys cheap junk and rides a bull market shows
  zero selection alpha.
- Plan: score on 1/3/5-year windows with dividend-inclusive returns; require
  survivorship-correct universe (delisted names included) before any PROVEN.

### 3.7 ML algorithms

- Exists: `ml_battleground/` (5 systems, arena), `crypto_ml_edge/`,
  `ml_gatekeeper/`, `ml_consensus/`, `meta_labeler.py`, `skyrocket_detector/model.py`.
- Risk: leakage. Any ML cell must declare train/validation/test split dates, and
  the test window must be strictly after the training window; feature store
  (`audit_trail/pick_feature_store.py`) already records point-in-time fields.
- Metric: same M1–M4 gates, plus **calibration** of predicted probability and
  stability across retrains. A model that needs monthly retraining to stay
  positive is `CANDIDATE`, never `PROVEN`.

### 3.8 Mutual funds vs ETFs

| | Mutual fund | ETF |
|---|---|---|
| Price | daily NAV, T+1 fill | intraday, spread |
| Costs | expense ratio + load | spread + commission |
| Signals | end-of-day only | intraday |
| Benchmarks | category average, survivorship-adjusted | SPY / sector ETF |
| Failure mode | survivorship bias (closed funds vanish) | closure/liquidation, tracking error |

Rules: never compare a mutual fund's NAV return to an ETF's intraday return
without aligning to close-to-close. Include expense ratio in net. Include dead
funds in the universe. `MUTUAL_FUND` slippage stays at 8bp but the **holding
period** must be at least one NAV cycle.

### 3.9 Strategy per risk level

Three sleeves, declared floors, same statistics:

| Sleeve | n floor | Max DD | Min PF | DSR | Extra |
|---|---|---|---|---|---|
| Conservative | 200 | 10% | 1.5 | 0.95 | must beat AGG/SPY after costs |
| Balanced | 100 | 20% | 1.4 | 0.90 | selection alpha > 0 |
| Aggressive | 50 | 40% | 1.1 | 0.80 | payoff-aware; penny/skyrocket allowed |

Win rate never gates a sleeve. A 25%-WR, 3:1 payoff strategy belongs in
Aggressive; a 70%-WR strategy with PF 0.9 does not belong anywhere.

---

## 4. Architecture

```
                   ┌──────────────────────────────┐
 live snapshot ───▶│ audit3_tribunal (stdlib)     │──▶ audit3_ledger.json
 backtest JSONs ──▶│  gates + BH + harm + M1–M5   │       │
 MySQL (read-only)│                              │       ▼
 price cache ─────▶└──────────────────────────────┘   /audit3 page
        ▲                                                   │
        └── separate weekly job (audit3-evidence.yml) ◀──────┘
```

- **Hourly/6-hourly job** (exists): live snapshot → ledger → deploy. Stays lite.
- **New weekly job** `audit3-evidence.yml`: read-only DB + repo JSONs + price
  cache → `audit_dashboard/data/audit3_evidence.json`. Separate concurrency
  group, separate cron minute, no overlap with the dashboard build.
- **No full scans of `bt_backtest_trades`** in CI: pre-aggregate by
  (strategy, symbol, asset_class, month) once, store the rollup, query that.
- Every evidence record carries `provenance {file|table, generated_at, hash}`
  so a number can always be traced back.

---

## 5. Phases and acceptance criteria

| Phase | Deliverable | Done when |
|---|---|---|
| **P0 (shipped)** | Doctrine fix, section × class matrix, go-live | 16 tests pass; `/audit3` serves 200 |
| **P1** | Evidence registry: ingest 77 repo JSONs + `bt_backtest_runs`, `at_large`, `at_incubator`; fix `asset_class` derivation; normalise hypothesis statuses; rebuild `ALL_STRATEGIES.md` from the live registries | every ingested record has provenance; class counts match symbol-derived truth; registry has one status enum |
| **P2** | Benchmark + selection alpha: price cache, same-symbol hold, per-class benchmark, `BETA_ONLY` verdict | every scored cell carries M1a/M1b/M1c; benchmark declared in ledger |
| **P3** | Surface ledgers: per-trader copytrader, prediction-market calibration, reverse-engineering OOS gate, skyrocket base rates, value/mutual-fund survivorship | each surface has ≥1 resolved ledger with its own metric |
| **P4** | Risk-level sleeves + promotion ladder (paper → shadow → sized) wired to the registry | no cell can reach sized capital without a registry entry |
| **P5** | Consolidation: `/audit3` is the single truth surface; `/audit` sections get a deprecation map | every old section maps to a cell or is documented as retired |

**P1 start point (cheap, high value):** the 285 `bt_backtest_runs` rows and the
`reports/strategy_bt_*` files already contain n, WR, PF and Sharpe. Ingesting
them is a few hundred lines and immediately triples the evidence base without
touching live scanners.

---

## 6. Explicit non-goals

- Not touching `/audit2`, its pages, its workflows or its swarm.
- Not re-running scanners in CI to manufacture fresh rows.
- Not deleting any strategy, symbol or section from the ledger.
- Not treating a high win rate, a big single winner, or a backtest without costs
  as evidence.
- Not promoting anything to real money from this plan; it only decides what is
  *worth tracking further*.

---

## 7. Open questions for the operator

1. Which benchmark is authoritative for CRYPTO — BTC buy & hold, or an
   equal-weight top-10 basket?
2. Do we have a survivorship-correct mutual-fund universe (`findmutualfunds2`),
   and does it include closed funds?
3. For penny/skyrocket, what is the maximum acceptable position size and
   drawdown in the Aggressive sleeve?
4. Should `combined-book-edge-proof` be imported wholesale as the gate
   reference, or only its statistical modules?
