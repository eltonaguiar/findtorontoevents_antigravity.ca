# 2026-11-15 — forward-test registration, intraday benchmark fallback, crypto driver decomposition

Follow-up round on the WIRED_IN submission (PR #779). Three requested items, all measured.

**Files:** `tools/pick_excess.py` (extended), `tools/forward_tracker.py` (registration),
`state/forward_test/plan.json` (registration), `WIRED_IN/2026-11-15_0128_buffy/{EXCESS_RETURNS.md,
FORWARD_TEST.md, README.md, artifacts/}`, `reports/pick_excess_returns.json`.

---

## 1. `vwap-reversion-scout` put on a pre-registered forward clock

**What was wrong:** the strongest-looking live rule had only a retrospective number (+1.96pp over
SPY, clustered t = 1.99) from a ledger that had already been read several times. Nothing about that
can promote a rule — the sample that motivates a hypothesis cannot also confirm it.

**What changed:** registered in `DEFAULT_PLAN` (`tools/forward_tracker.py`) and in
`state/forward_test/plan.json` with `hold_type: long` (median hold 145h ≈ 6 days selects the slow
clock), `trades_per_year: 48`, an explicit `kill_rule`, and a `baseline` block recording the prior
(28 picks, 25 windows, +1.96pp, t 1.99, 60.7% excess win rate) so nobody can quietly re-read the prior
as a result.

**Verified:** `forward_tracker.py status` lists all three strategies at `CONTINUE` with 0 trades and
0 days elapsed; `forward_tracker.py selftest` still passes **8/8**. The ledger has **not** been seeded
with the 28 historical picks — backfilling would destroy the only property that makes it forward.

## 2. Same-day picks are now measurable (hourly benchmark fallback)

**What was wrong:** 1,056 picks were excluded as `window_collapsed` because entry and exit resolved to
the same trading day, so no daily benchmark window existed. Those picks were reported as unmeasurable,
which is honest but leaves 32% of the closed book with no excess number at all.

**Root cause of the exclusion:** the tool resolved benchmark prices on a *daily* grid only, while the
ledger stores `timestamp` / `entry_time` / `closed_at` with **clock times**. The data was always
sufficient; the resolver was not.

**What changed:** `fetch_hourly()` + `class Hourly` fetch and cache Yahoo 60-minute bars, and the
collapse branch now falls back to "last hourly bar at or before each timestamp", requiring strictly
increasing bar times. Unresolvable picks remain in `window_collapsed` and are still **never** scored
as zero excess. Each scored pick carries `resolution: daily|hourly`; the payload carries
`resolution_counts`.

**Measured result:** **852 of 1,056** previously excluded picks are now scored (daily 2,145 + hourly
852 = 2,997 of 3,263, 91.8% coverage; 204 remain genuinely unseparable).

**Honesty check that mattered:** the crypto class mean moved from **−1.29pp** to **−0.795pp**. That is
**coverage dilution, not improvement** — the multi-day subset still reproduces **−1.290pp exactly**,
and the 808 recovered sub-day crypto picks average −0.173pp. Both numbers are now published side by
side in `EXCESS_RETURNS.md` §2 so the shift cannot be mistaken for a fix.

## 3. Crypto shortfall decomposed by strategy

**What was unknown:** "CRYPTO is −0.8pp per pick" is not actionable — it does not say which rule to stop.

**What changed:** `by_strategy_class` aggregation and a `crypto_decomposition` block in the artifact
(strategy × class, ranked by cumulative excess, with share of total).

**Finding:** the shortfall is concentrated, not diffuse. **`MomentumEMA` alone is 58.2%** of
−1,451.6pp (−11.56pp per pick, **t = −7.84**, 37 windows, excess win rate **4.1%**). Adding the next
five names (`clone_hl_copy_lb_None`, `hs_Auros_66M`, `clone_hl_copy_PensionFund_24M`,
`st_fear_greed_contrarian`, `hs_ABC_41M`) overshoots the whole total — the other 48 crypto strategies
**net +39.4pp**. `luxalgo_confluence` is 64% of crypto picks but only 2.6% of the shortfall.

So the crypto book is not broadly bad: a handful of rules are, and one of them is large and
statistically measurable. Six crypto rules are weakly positive on ≥8 windows, all insignificant
(best: funding-rate-reversal +0.95pp, t 0.16).

## 4. Bug found and fixed while doing this

`cluster_t()` reported a t-statistic for **any** number of windows ≥ 2. A 2-window clone group printed
**t = −63.47**, which is arithmetic, not evidence — two similarly bad days that a batch of clones fired
on. Same defect class as the earlier `t = −169,292` on a single window.

Fixed with `MIN_CLUSTERS = 5`: below five independent windows `t_cluster` is `null`, and the convention
is recorded in the JSON payload. This is why several rows in `EXCESS_RETURNS.md` §3 carry `n/a`
instead of a large t.

---

## Verification

| Check | Result |
|---|---|
| `forward_tracker.py status` | 3 strategies, all `CONTINUE`, 0 trades — registration is live |
| `forward_tracker.py selftest` | **8/8** rule cases |
| `pick_excess.py` | exit 0; 2,997 scored, 852 hourly, 204 genuinely collapsed |
| Coverage arithmetic | 2,997 + 266 excluded = 3,263 rows; matches ledger count |
| Multi-day crypto subset reproduces prior run | **−1.290pp** vs published −1.29pp |
| Hourly cache | `SPY_60m_2025_2026.csv` 3,265 bars, `BTC-USD_60m_2025_2026.csv` 16,359 bars |
| Doc figures re-derived from artifact | 0 mismatches (script check) |
| Relative links in `WIRED_IN/2026-11-15_0128_buffy/` | 0 broken |

**Not verified / limits:** `state/forward_test/status.json` is generated and deliberately not
committed. Hourly bars are unadjusted, correct for same-series sub-day differences. The forward test
has **zero** trades — it produces no verdict until the clocks in `FORWARD_TEST.md` §3 elapse.
