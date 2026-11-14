# Focus decision

## Decision

**No 1-2 classes can honestly be labeled profitable today.** The evidence supports choosing research priorities, not claiming proven returns.

### Priority 1: EQUITY research

Test a diversified cross-sectional factor sleeve with dividend-adjusted, survivorship-free data and monthly rebalancing. Use a risk-matched total-return benchmark. Reports of positive closed-pick economics conflict with the official verdict and `pf_registry`; the current record therefore does not prove equity alpha.

**Promotion gate:** pre-register the exact universe, features, rebalance, costs, benchmark, and trial ID. Require at least 500 independent closed observations where applicable, positive net benchmark excess in an untouched holdout, predeclared stability across both holdout halves, and no material single-name/source concentration. A test failure means “not proved,” not “change the benchmark.”

### Priority 2: CRYPTO, conditional on data integrity

First reconcile the spot/perpetual sources, actual exit writers, stop fills, and replay rows. Then test (a) daily trend and (b) funding carry separately. The stop-fill correction does not itself make crypto profitable; the reported improvement to roughly breakeven is retrospective and its forward evidence is not established.

**Promotion gate:** post-fix genuine forward observations; fees, spreads, funding, leverage, and liquidation included; bear-inclusive holdout; benchmark excess over spot/cash; independent trial count. Do not use synthetic/replay picks as forward outcomes.

### Runner-up: FUTURES only after data is ready

Managed-futures trend/carry is a reasonable research candidate, but there is no promotion path until a genuine continuous-contract series, rolls, margins, and transaction costs are available. Do not relabel crypto proxies as commodities/futures.

## Do not prioritize yet

- **ETF:** resolve overlap with equity and show net expected move exceeds realized costs first.
- **FOREX:** fix class contamination, date-only timestamps, quote provenance, and benchmark.
- **COMMODITY:** no proxy feed; COT parameter selection/OOS boundary requires audit.
- **BOND:** current samples and price provenance are insufficient.
- **Mutual funds:** separate passive investment baseline, not a live prediction class.

## Decision rule

The goal is to **find** one or two profitable classes, not to promise them. If both Equity and Crypto fail pre-registered, net, benchmark-relative tests, the correct decision is to keep both blocked and preserve a passive benchmark sleeve rather than mine until a metric turns positive.

