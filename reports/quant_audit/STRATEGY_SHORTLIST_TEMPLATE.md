# STRATEGY_SHORTLIST.md — template

Target: `reports/quant_audit/STRATEGY_SHORTLIST.md`. One section per candidate, at most three
candidates. A candidate that cannot fill G1–G10 is `PROMISING` with the gap named, or `REJECT`.

Verdict vocabulary (closed set): **PROVEN** · **PROMISING** · **REJECT** · **INSTRUMENTED — NOT MEASURED**

---

# Strategy shortlist — <date>

| # | Candidate | Class | TF | Verdict | Failing gate(s) | One-line reason |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

## Candidate 1 — `<name>`

**Hypothesis (pre-registered, verbatim from `reports/hypothesis_registry.json` id `<H-xxx>`):**
> `<the sentence registered BEFORE the backtest>`

| Field | Value |
|---|---|
| Asset class / universe | |
| Timeframe / holding period | |
| Entry rule | |
| Exit rule | |
| TP / SL (how set, not just values) | |
| Position sizing | |
| Cost model (bps/side, spread, slippage, funding) | |
| Benchmark | |
| N configurations tried in reaching this | |
| Pre-registration date / registry id | |
| Data range and source | |

### The gate

| # | Requirement | Status | Evidence | Note |
|---|---|---|---|---|
| G1 | chronological split, no look-ahead | PASS/FAIL/NOT MEASURED | `path:line` | |
| G2 | walk-forward ≥5 folds + parameter stability | | | WFE = `<x>` |
| G3 | multiple-testing correction at real N (`N=<n>`) | | | DSR = `<x>`, RC p = `<x>` |
| G4 | block bootstrap ≥10k, net of costs | | | % paths > 0 = `<x>`, p5 = `<x>` |
| G5 | full friction + breakeven cost | | | breakeven = `<bps>` vs assumed `<bps>` |
| G6 | clustered-t CI for mean excess excludes 0 | | | t = `<x>`, clusters = `<n>` |
| G7 | positive in majority of regimes | | | bull/bear/flat = `<x>/<x>/<x>` |
| G8 | negative control on shuffled prices | | | permuted mean = `<x>` |
| G9 | pre-registered forward test | | | `state/forward_test/plan.json` |
| G10 | seeded, runnable, committed | | | `<command>` |

**Verdict:** `PROVEN | PROMISING | REJECT | INSTRUMENTED — NOT MEASURED`
**Why:** `<one paragraph; if not PROVEN, name the gate and what would close it>`

### Metrics (net of costs, vs benchmark)

| Metric | Value | Benchmark value |
|---|---|---|
| CAGR / cumulative | | |
| Annualised vol | | |
| Sharpe / Sortino / Calmar | / / | |
| Max DD / avg DD / recovery | | |
| Win rate (Wilson lower) | | |
| Profit factor (boot 5% lower) | | |
| Expectancy per trade | | |
| Avg win / avg loss (payoff) | / | |
| Longest losing streak | | |
| Avg holding period | | |
| Skew / kurtosis | / | |
| Autocorrelation of returns (lag 1) | | |
| Excess vs benchmark, mean (CI) | | |
| Trades / clusters / years | / / | |

### Robustness

| Sweep | Range tested | Result holds? | Note |
|---|---|---|---|
| TP/SL multiple | | | |
| Entry threshold | | | |
| Lookback | | | |
| Cost multiplier 1x / 2x / 3x | | | |
| Start date shifted ±1yr | | | |

## What we are NOT recommending, and why

| Candidate considered | Rejected because | Evidence |
|---|---|---|
| | | |

## The single next experiment

- **Question:** `<one sentence>`
- **Method:** `<exact test, exact sample, exact threshold>`
- **Decision rule:** promote if `<x>`, kill if `<y>`, otherwise extend to `<n>` windows
- **Cost:** `<runtime, data needed>`
- **Where the result lands:** `reports/quant_audit/evidence/<file>.json` + a verdict row above

---

## Rules for whoever fills this in

1. A `PROVEN` verdict requires **every** G cell to say `PASS`. Nine of ten is `PROMISING`.
2. `N` in G3 must come from the registry and logs, never from memory. If it cannot be
   determined, G3 is `NOT MEASURED` and the verdict cannot be `PROVEN`.
3. Cluster on `(entry_day, exit_day)`. Rows sharing one `closed_at` are one observation.
4. Report gross **and** net. A candidate that only survives gross is `REJECT`.
5. Any metric you cannot compute stays blank with a `NOT MEASURED` reason in the note column.
   Never interpolate, never round a failure into a pass.
