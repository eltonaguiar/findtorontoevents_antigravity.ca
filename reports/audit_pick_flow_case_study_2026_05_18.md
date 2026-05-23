# /audit Pick-Flow Case Study — Past Week per Asset Class

**Window:** 2026-05-11 .. 2026-05-18 · **Source:** live MySQL `ejaguiar1_stocks`
(`at_raw_picks`, `at_filter_log`, `at_consensus_picks`) + `alpha_engine/data/closed_picks.json`
· **Tooling:** `.claude/skills/audit-pick-flow/scripts/pick_flow_funnel.py`

> Companion to the `audit-pick-flow` skill. Reproduce with
> `python .claude/skills/audit-pick-flow/scripts/pick_flow_funnel.py --days 7 --live`.

## 1. The funnel, all classes (picks recorded 2026-05-11..18)

| Class | Raw emitted | Gate rejections | Top reject reason | Consensus survivors | Closed (by `closed_at`) |
|-------|------------:|----------------:|-------------------|--------------------:|------------------------:|
| CRYPTO | ~13,270 | 6,787 | staleness (5,396) | 35 open / 112 resolved | 271 |
| EQUITY | 570 | 226 | no_consensus (203) | 2 open | 0 (resolved w/ pnl=0) |
| FOREX | 203 | 136 | no_consensus (112) | 0 | 8 |
| FUTURES | 176 | 133 | no_consensus (89) | 0 | 0 |
| MEMECOIN | ~380 | — | — | 0 | 1 |
| ETF | 32 | 114 | no_consensus | 0 | 0 |
| PENNY_STOCK | 27 | — | — | 0 | 0 |
| UNKNOWN | 99 | 590 | demoted_system / staleness | 0 | 0 |

**Headline:** CRYPTO is 95%+ of all pick volume. Every non-crypto class emits 30-570
picks/week but almost none survive to consensus, and their closed picks resolve to
`pnl_pct = 0.0` placeholders — the known non-crypto resolver gap.

## 2. Per-class autopsy

### CRYPTO — high volume, negative edge
- 8,685 picks recorded in the window already carry `status=CLOSED`: 3,022 wins → **34.8% WR**,
  avg `pnl_pct` **−14.98%**. A further 877 are `status=LOST` at avg **−77.8%** (catastrophic
  stop-throughs / liquidation-style exits), 523 `WON` at +6.2%.
- Closed strictly by `closed_at` in-window: n=271, **WR 30.6%, PF 0.17** (gross win 1,180
  vs gross loss 6,753).
- `closed_picks.json` cumulative view (kilo cross-check, 8,421 closed all-time): CRYPTO
  6,884 picks, **WR 32.8%, PF 0.41**, total −1,057% PnL. A handful of `ml_enhanced_*`
  per-symbol strategies show 56-96% WR on tiny n — these are the per-symbol curve-fit
  artifacts M-105 already de-boosted; not real edge.
- **Verdict:** sub-floor. Volume is not the problem — *unfiltered* volume is. The drag is
  concentrated in low-quality source systems and the `LOST`-status tail.

### EQUITY — thin, unresolved
- 570 raw / week, 543 still `OPEN`. 14 `CLOSED` + 13 `EXPIRED` all resolved with
  `pnl_pct = 0.000` — placeholder, not a real outcome. `closed_picks.json`: 44 closed,
  WR 36.4%, PF 0.71 on micro-magnitude pnl (best +0.05%, worst −0.07%).
- 203 rejected for `no_consensus` — equity emitters don't agree often enough to publish.
- **Verdict:** insufficient resolved data to judge. The bottleneck is the resolver
  (non-crypto live-close gap), not the gates.

### FOREX — sub-floor, correctly throttled
- 203 raw, 167 `OPEN`. Resolved: 8 `WON` (+1.7% avg) vs 8 `LOST` (−10.6% avg) — losers
  4× the size of winners. FOREX LONG is hard-blocked at the active gate (SHORT-only).
- **Verdict:** matches the charter "FOREX genuinely sub-floor" status. Throttle is working;
  no edge to harvest yet.

### FUTURES / ETF / BOND / MEMECOIN — too small to call
- FUTURES 176 raw, 0 resolved. ETF 32 raw. BOND emitted ~0 (1 closed all-time, a loss).
  MEMECOIN ~380 raw, mostly `CLOSED` at −10.6% avg.
- **Verdict:** below the n≥50-per-class floor. Not enough clean data for any verdict.

### COMMODITY — the inflated outlier
- `closed_picks.json`: 354 closed, WR 60.2%, PF 2.28 — but driven entirely by
  `cot_positioning` (n=133, 78% WR) and `cftc_cot_commercial_signal` (n=131, 75% WR).
  COT is a **killed family** (M-107) and the COMMODITY tile is flagged COT-dedup-inflated
  in `CLAUDE.md`. The CTA strategies in the same class run 0-13% WR.
- **Verdict:** the headline number is an artifact. Do not size on it.

## 3. Where picks die — the rejection profile

`at_filter_log`, past 7 days, top reasons:

| Reason | Count | Meaning |
|--------|------:|---------|
| `staleness` | 5,396 (CRYPTO) + 294 (UNKNOWN) + 44 (FUTURES) | pick older than freshness window before it could publish |
| `no_consensus` | 1,141 CRYPTO + 203 EQUITY + 114 ETF + 112 FOREX + 89 FUTURES | only one source emitted it — no agreement |
| `demoted_system` | 294 (UNKNOWN) | source system demoted |
| `wr_suppressed` | 46 (UNKNOWN) | strategy win-rate below suppression floor |
| `banned_purge` | 42 (UNKNOWN) | banned strategy/symbol |
| `concentration_cap` | 40 (CRYPTO) | per-symbol share over class cap |
| `regime_mismatch` | 25 (CRYPTO) | direction fights the BTC regime |

**Reading:** the two dominant rejects — staleness and no_consensus — are *plumbing*,
not edge filters. The pipeline emits faster than it can corroborate, so most picks rot
before a second source confirms them. Edge-quality gates (regime, concentration, wr) fire
on only a few percent of volume.

## 4. Single-pick trace (worked example)

```
$ python .claude/skills/audit-pick-flow/scripts/trace_pick.py --symbol BTCUSDT --limit 1
```
shows, for the most recent BTCUSDT pick: source_system, strategy, every `at_filter_log`
rejection with reason, whether it reached `at_consensus_picks`, and the resolved outcome.
Use this for any "why is X (not) on the page" question.

## 5. Conclusions

1. **CRYPTO is the only class with a statistically meaningful sample, and it is
   sub-floor** (WR ~33%, PF 0.17-0.41). Every other class is either unresolved
   (EQUITY, FUTURES, ETF, BOND) or correctly throttled (FOREX) or artifact-inflated
   (COMMODITY).
2. **The funnel loses most picks to plumbing** (staleness, no_consensus), so the
   gate stack barely gets to act as a *quality* filter — it mostly acts as a
   *freshness* filter.
3. **The non-crypto resolver gap blinds us** — picks closed at `pnl_pct=0.0` make
   EQUITY/FOREX/FUTURES/ETF/BOND impossible to judge. This is the highest-leverage
   data fix (see roadmap Phase 0).
4. There is **no asset class currently clearing the Tier-2 money-ready bar** on
   clean, resolved, non-artifact data. This is consistent with the standing
   no-edge verdict (`project_edge_verdict_2026_05_18`).
