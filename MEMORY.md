# Long-term memory — vanilla-handsaw / kilo

**Last updated:** 2026-11-23T01:34Z

## Headline (measured, paper only)
- **0 / 6 asset classes** survive deflation; **0 / 69 ranked picks** pass G1–G5.
- Best credible DSR: **0.159 @ n≥30 → 0.136 @ n≥50 → 0.021 @ n≥100**. The 0.9999 DSR is n=22 (below floor).
- SR* at programme N: **1.62 (N=90) → 2.03 (N=658)**.
- Only defensible real-money answer: **buy a low-cost broad index ETF** (active MF = 17.6× the ETF over 10y). Break-even bar for any active strategy: **+3.34%/yr excess at $1k tickets, +0.80%/yr at $25k**.

## Traps discovered (do not repeat)
1. **BH over bootstrap p-values** → 21 fake "survivors", all at the p=0.0005 resolution floor. Saturation, not signal.
2. **Mean-only paired bootstrap** falsely passed H-119 (+20.6%/yr). Median CI + sign test (p=0.45) kills it. Two-hurdle rule now requires **mean AND median** CI to exclude zero.
3. My **12.07 bp spread** cited "13 names" that were **never persisted** → LOW_CONFIDENCE. Use copilot 4.97 bp primary, 12.87 bp conservative bound.
4. **Trial N is object-dependent**: registry 108 / cells 362 / symbols 658 / copilot 146. Every claim must state which.
5. **EQUITY/ETF universe is survivorship-biased** (0 delisted names). CRYPTO perps are PIT-clean.

## Constraint
**Trial debt is binding.** Stop running new backtests. Spend trials only on (a) an unspent data axis and (b) forward-only, pre-registered measurement (1 trial, not 5).

## Open pre-registration
**H-2026-11-23-01** — turn-of-month long bias, CRYPTO, frozen 2026-11-23 before any measurement. Harness `tools/tom_forward_clock.py` refuses pre-freeze dates, emits `n_records=0`. Registry now 109 (was 108). Expected: KILL.

## Blocked / missing inputs
- PIT fundamentals tool exists at commit `c0d48e28968` (copilot's branch) but is **NOT present on this branch** — any path check will flag it as missing by design; do not cite it as if local.
- Survivorship-free universe needs delisted-name history.
- FX backfill needs DB creds (dbpasses.txt — never read).

## Key files
`docs/edge_research/DISTANCE_TO_INVESTABLE.md`, `reports/REPORT_INDEX.json`, `reports/deflation_programme.json`, `reports/cost_ladder.json`, `reports/two_hurdle_kill.json`, `updates/2026-11-23-two-hurdle-kill-rule.md`.

## Rules
Never read dbpasses.txt. Never push other authors' commits. Every fix has a matching `.MD`. Zero real money until forward gate (n≥100, two-hurdle pass). Verify any artefact path resolves at the commit named before citing it.

## G3 / DSR (corrected 2026-11-23T02:26Z)
- Production `deflated_sharpe` uses **sr0 = K(N)/sqrt(n)** per strategy (K=3.134 at N=658).
  The bar FALLS with sample size: n=30→SR≥0.94, n=100→SR≥0.49, n=219→SR≥0.33.
- **0/69 fail on small n + weak SR** (median n≈35, SR≈0.1–0.2), NOT an impossible bar.
- Validated: n=100, SR=0.5 → real DSR **0.9516** (passes).
- Shortlist within 100 trades: **AUDJPY** (n34, SR.724, **+14**) and **CVX** (n35, SR.449, +83) —
  BOTH unmeasurable (AUDJPY: FOREX frozen, fx_prices dead; CVX: no EQUITY hold-times). Actionable shortlist EMPTY.
- Criteria for a future strategy to clear G3: **n≥100 AND per-trade SR≥0.50**, report effective N, still pass G1/G2/G4/G5.
- `reports/sr_star_table.json` is a CROSS-strategy metric (σ=0.649) — NOT the G3 denominator. Canonical: `reports/g3_bar_analysis_corrected.json`.

## Data-integrity landmine (2026-11-23T03:58Z)
**STALE-BRANCH ONLY, corrected 2026-11-23T07:15Z:** my branch's 2,204-row closed_picks was 88% barrier-quantised placeholders, but **current origin/main has 505 rows, 0 dateless-on-barrier (clean)**. The 88% alarm is retracted for main. Still filter to `entry_date IS NOT NULL` as hygiene. Tools: `tools/label_closed_pick_outcomes.py`.
On MAIN data: forex_rsi2 n77 DSR@61 0.968 but net -7.3bp after FOREX cost; all classes net-negative; EQUITY n=1 dated.

## Operator ranking standard (now required)
Rank on the **95% LOWER BOUND of net return**, not the point estimate; n≥30 hard floor; per-pick
MECHANISM/COUNTERPARTY/WHY-SYMBOL/WHY-NOW/KILL; "my scan ranked it" is not a mechanism; empty list is
respectable. `tools/rank_on_lower_bound.py` (strategy LB) and `tools/rank_picks_lower_bound.py` (symbol LB).

## Contract facts
Index MF ≈ 0.995–0.998 correlated with SPY and return ~11.6%/yr → same beta, fees decide. SGOV ~3.9%/yr = cash hurdle.
Contest ledger hashes were unstable due to **CRLF** (not fabrication) — resolved 10/10 at 3eac5c2; use LF-normalised sha.
Operators: `tools/cross_review_picks.py` flags n=0 / net<cost across agents.
