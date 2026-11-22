# mega_mutation quarantined — the last candidate fails (2026-11-22)

Reproducer: `python3 tools/mega_mutation_falsification.py --draws 3000`
Artifacts: `reports/mega_mutation/falsification.json`
Wired into: `reports/weekly_scorecard/` (`Source: mega_mutation | QUARANTINE`)

---

## Why this mattered

After the ledger mine, exactly one emitter out of 67 survived: **`mega_mutation`**,
+135 bp/trade, n=105, 67 days, 55L/50S. If it held, the programme had one
candidate. If it fell, the programme has **no positive-expectancy emitter at all**
and the honest recommendation is T-bills at 3.5%.

It fell.

## The battery

Eight tests. Six feed the gate. The first version of this tool used four and
printed **4/4 PASS** — which was too lenient. The concentration output in the same
run was already telling me three single-trade days made 22% of the P&L, and I had
not turned that into a test. Adding the tests that can fail for reasons *other
than* "the number is small" changed the verdict.

| # | test | result |
|---|---|---|
| 1 | max-statistic null (best of 20 random sources, 3,000 draws) | **PASS** — observed +134.98 vs null p99 +114.71, p=0.0010 |
| 2 | cluster bootstrap on the mean (symbol-day clusters) | **PASS** — CI [+40.90, +231.49] |
| 3 | out-of-sample clock (≥20 prior picks before the month) | **PASS** — 73 OOS picks, +126.25 bp |
| 4 | breakeven vs measured cost | **PASS** — breakeven 135 bp ≫ 42 bp RT |
| 5 | **median CI** | **FAIL** — [+193.43 median], CI **[−224.38, +289.98]**, includes zero |
| 6 | **duplicate re-emissions** | **FAIL** — 8 groups, **16/105 rows** |

**4/6 → QUARANTINE.**

## What the failures actually are

### Median CI includes zero
Mean +134.98, **median +193.43**, sd 489.48. The distribution is enormous
(p25 −265.7, p75 +480.6, min −718.5, max +1254.2) because it is a TP/SL system:
outcomes cluster near +900…+1250 bp or −640…−720 bp, and almost nothing lands in
between. In a distribution that wide the mean and the median disagree about
significance, and the row-level median CI crosses zero. **Both point estimates
must agree before a label above QUARANTINE is defensible.**

### 16 of 105 rows are duplicate re-emissions
```
AVAXUSDT SHORT entry 9.409   on ['2026-04-30', '2026-04-30']   <- same day, twice
JUPUSDT  LONG  entry 0.1698  on ['2026-04-30', '2026-04-30']
DOTUSDT  LONG  entry 1.2769  on ['2026-05-05', '2026-05-06']
AVAXUSDT LONG  entry 6.487   on ['2026-07-10', '2026-08-16']
```
Two of these are **the same position emitted twice on the same day**. This is
15% of the sample. It inflates n and it inflates the mean, in a source whose
entire case rests on a mean.

### And the one that cannot be tested here
TP-first rate is **56.4%** where a driftless random walk with the realised TP/SL
distances (TP ~546 bp, SL ~378 bp) implies **40.9%**. Binomial
P(≥53 of 94 | p=0.409) = **1.7 × 10⁻³**.

That is either genuine directional skill or TP/SL levels placed with hindsight.
**This ledger has no `created_at`, so it cannot distinguish them.** Provenance is
UNMEASURED for this artifact, exactly as for the other 66 emitters.

So even a 6/6 pass could only ever have reached **CANDIDATE** here. The test that
separates skill from hindsight is the one this data cannot run.

## Verdict

| item | previous | now |
|---|---|---|
| `mega_mutation` | CANDIDATE (+135 bp, survived falsification pass) | **QUARANTINE** |
| any positive-expectancy emitter | 1 of 67 | **none established** |
| recommended deployment | T-bills while watching one candidate | **T-bills at 3.5%** |

The weekly scorecard now prints this row and carries the note that no
positive-expectancy emitter is established anywhere in the programme.

## What would un-quarantine it

1. **Provenance.** Rows with `created_at` proving the pick existed before its
   outcome. Without it, the TP-first result stays ambiguous forever.
2. **Genuinely distinct trades.** De-duplicate on (symbol, side, entry, open
   timestamp) before any statistic is computed — 16 rows cannot count twice.
3. **A forward clock.** Live picks accruing after this analysis, with the same
   TP/SL configuration fixed in advance.
4. **A measured alt-perp spread.** AVAX/JUP/WIF/DOT spreads are UNMEASURED; the
   42 bp figure used above is from BTC/ETH/SOL and is optimistic for alts.

Until 1 lands, no amount of statistical work on this artifact can promote it. That
is not a limitation of the tests — it is a limitation of the evidence.
