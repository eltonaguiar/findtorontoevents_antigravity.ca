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
- PIT fundamentals tool (`tools/edgar_pit_fundamentals.py`) exists at commit `c0d48e28968` but is **not on this branch**.
- Survivorship-free universe needs delisted-name history.
- FX backfill needs DB creds (dbpasses.txt — never read).

## Key files
`docs/edge_research/DISTANCE_TO_INVESTABLE.md`, `reports/REPORT_INDEX.json`, `reports/deflation_programme.json`, `reports/cost_ladder.json`, `reports/two_hurdle_kill.json`, `updates/2026-11-23-two-hurdle-kill-rule.md`.

## Rules
Never read dbpasses.txt. Never push other authors' commits. Every fix has a matching `.MD`. Zero real money until forward gate (n≥100, two-hurdle pass). Verify any artefact path resolves at the commit named before citing it.
