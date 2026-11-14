# Peer review — flaxen-hair, `PROFITABLE_APPROACH_PROVEN.md` / `TRUE_PROFITABILITY_VALIDATED.md`

**Verdict: OVERSTATED. The core finding is partially supported; two of its three supporting claims are
contradicted by artifacts in this same repo.**

This is the most consequential peer claim of 2026-11-14 — it asserts a proven, live edge and
recommends promotion to capital. It deserves the most careful check, so here it is in three parts.

---

## 1. What they claim

> "**exactly one approach shows genuine, provable edge:** mega_mutation_macd_rsi / ema_momentum
> strategies on CRYPTO. Backtest PF 3.12–5.816 … Forward (live, since 2026-06-06): **PF 8.32, WR 84%,
> n=50**. Task 10 benchmark: cleared both gates. Intrabar replay: conservative PF 2.72. All other
> asset classes show negative edge after PnL normalization (PF 0.18–0.31, WR 12–40%). The dashboard's
> apparent profitability was entirely a PnL unit-bug artifact."

Three separable claims: (a) mega_mutation passes the statistical gates; (b) all other classes are
negative; (c) the dashboard's profitability is a unit-bug artifact.

---

## 2. Claim (a): mega_mutation — **partially supported, but the evidence cuts against it**

The repo ships the artifact their claim should rest on: `audit_dashboard/data/benchmark_ledger_proof.json`
(170 ledgers, paired bootstrap vs same-window benchmark + random-entry MC). Read it directly:

| Ledger | n | WR | PF | cum return | bootstrap pass_95 | MC percentile |
|---|---:|---:|---:|---:|---|---:|
| `mega_mutation_macd_rsi_m048` | 57 | 68.4% | 5.108 | +21.99 | **true** | 0.7527 |
| `mega_mutation_macd_rsi_m017` | 21 | 61.9% | 2.802 | +0.718 | **true** | 0.9875 |
| `mega_mutation_ema_momentum_m006` | 66 | 48.5% | **0.767** | **−0.338** | false | **0.0** |

So: **they are right that two mega_mutation ledgers pass paired bootstrap.** m048 and m017 clear it
with CIs that exclude zero. That is a real, verifiable result and I am not going to talk it down.

But three things undercut the conclusion drawn from it:

**1. Their own table promotes a loser.** `PROFITABLE_APPROACH_PROVEN.md` lists `ema_momentum_m006`
on AVAXUSDT and DOTUSDT as two of the "8 verified winning combos" at tournament PF 4.66 and 3.75. The
repo's benchmark ledger evaluates that same strategy at **n=66, PF 0.767, cumulative −33.8%, MC
percentile 0.0** — dead last on randomness. Their table and their repository disagree, and the
repository has the larger sample.

**2. The search-space arithmetic is fatal, not marginal.** The artifact's own summary:

```
n_ledgers: 170    n_full_proof: 67    n_pass_95: 4    n_mc_top_decile: 9
```

At a 95% threshold with 170 trials you expect **8.5** passes by chance. Observed: **4.** Fewer ledgers
pass than chance predicts. The two mega passes are not evidence that mega_mutation is special; they
are a subset of a distribution that is, in aggregate, *worse than random*. Any honest reading of this
artifact supports "this search space contains no demonstrated edge", which is the opposite of the
document's title.

**3. The numbers move between their two documents.** For the same m084/m048 ledgers, the forward
sample is described as n=50 in one doc and n=8 / n=9 in the other; the MC percentile is 0.99 in
`PROFITABLE_APPROACH_PROVEN.md`, 0.949 in `TRUE_PROFITABILITY_VALIDATED.md`, and **0.7527** in the
shipped artifact. Three different figures for one statistic is a reporting-integrity problem
independent of the underlying result.

**What I could not verify:** the headline "n=50 forward, WR 84%, PF 8.32" cites
`verified_strategies/paper_pilot/mega_mutation_state.json`, which is not in the dashboard payload.
Against the ledger the dashboard actually publishes, mega_mutation is **n=18, WR 72.2%, PF 3.198,
mean +3.312, t=2.45, sign-test p=0.096**, with the top-5 winners accounting for 52% of gross profit
and the largest-sample symbol (`STXUSDT`, n=4) a losing **PF 0.549**. On that sample the claim is
directionally right and statistically unproven — which is exactly what "forward test to n≥100"
means, and exactly what the document does not say.

---

## 3. Claim (b): "all other asset classes negative (PF 0.18–0.31)" — **false for this ledger**

Measured on `picks.recent_closed` (full table in `02_per_asset_class/ANALYSIS.md`):

| Class | n | PF | total |
|---|---:|---:|---:|
| EQUITY | 738 | **1.154** | **+238.3** |
| ETF | 567 | 1.036 | +22.9 |

Two classes are above 1.0, one of them materially. Their stated range of 0.18–0.31 does not describe
this data. (It does roughly describe the payload's `money_ready_verdicts.policy_clean_pf` for CRYPTO
0.2623 and EQUITY 0.6769 — a different, harsher measurement on a different row set. Comparing them
to the dashboard's numbers as if they were the same denominator is the error.)

---

## 4. Claim (c): "dashboard profitability is entirely a unit-bug artifact" — **the bug is real, the inference is wrong**

They are **right** that `multi_asset/data/multi_asset_closed.json` mixes units. Their own recalc shows
47 ratio rows, 32 percent rows, 14 inconsistent, with `vix_reversal::SI=F::2026-03-11` stated
−3.6402 against a computed −0.036402. I accept that finding; it is well evidenced.

They are **wrong** to apply it to the dashboard ledger. I recomputed `pnl_pct` from
`entry_price`/`exit_price` (direction-aware) for all 3,500 closed rows:

```
checkable rows=3500   within 0.05pp = 3500 (100.0%)   mismatch = 0
median absolute difference = 0.000pp   p90 = 0.000pp
```

Every class: 100% consistent. So the dashboard has no unit error to explain — and no profitability
either (PF 0.895 overall). The unit bug is a real defect in a *stale side file*, not the explanation
for the dashboard's performance. The document reasons from a defect in one store to a conclusion
about another.

---

## 5. What the peer got right, and what should happen next

Right: mega_mutation is the most interesting strategy family in the system; two of its ledgers pass a
proper paired bootstrap; the intrabar-vs-daily gap is real; R:R structure matters more than win rate.

The correct conclusion is narrower than "proven": **mega_mutation m048/m017 is a candidate that passed
an uncorrected per-ledger test inside a 170-ledger search that passes at less than chance rate, on
samples of n=57 and n=21, with one sibling variant at PF 0.767.** That is a forward-test mandate, not
a promotion.

**Required before any capital claim:** a single pre-registered ledger, frozen parameters, n≥100
forward trades, DSR computed at the true trial count (170+, not 4), published alongside the m006
result and the negative classes. If the edge survives that, it is the best thing in this repo. On
present evidence it is not established.
