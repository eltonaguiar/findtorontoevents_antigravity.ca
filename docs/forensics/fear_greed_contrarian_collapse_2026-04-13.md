# st_fear_greed_contrarian Collapse — Forensic Report

Investigator: Claude (Opus 4.6, read-only forensic)
Date: 2026-04-13
Branch: `chore/forensic-fear-greed-contrarian`
Reproduction: `tools/forensic/fear_greed_reproduce.py`

## TL;DR

The reported collapse ("202 picks, 44.6% WR, PF 0.68, -30.3% PnL in 48h")
and the earlier "#1 performer at 83% WR" are **two different populations
of picks sharing a strategy tag**. The paper-trading strategy
`paper_trading/strategies/fear_greed_contrarian.py` has only ever produced
a handful of trades (29 in `universal_resolved_picks`, 32 in
`claudes_test_state`, 1 in `closed_picks`; 62 combined, 25.8% WR, PF 0.61
lifetime). The "elite 80.9% WR, 584 wins, +1042.91 PnL" number comes from
a **different feeder system (`claude_gainer_st`)** which re-tags its
gainer-scanner output with `strategy=st_fear_greed_contrarian` as a
conviction label, on symbols (`APT, UNI, DOT, SOL, OP`) that the real
strategy file never trades (its whitelist is `BTC/ETH/SOL/BNB/XRP`).
The "collapse" is therefore **not a regime shift, data-source drift, code
bug, or overfit** of the F&G logic — it is a **strategy-tag aliasing
artifact**. The underlying edge that degraded is the `claude_gainer_st`
scanner, which is mis-labelled under a fear-greed banner.

**Diagnosis: (e) Something else — strategy-tag aliasing / label
collision, compounded by (d) a historical WR that was never this
strategy's to begin with.**
**Evidence grade: DECISIVE on aliasing; STRONG on "no F&G-side bug".**

## Reproduction

Script: `tools/forensic/fear_greed_reproduce.py` (stdlib-only,
stand-alone). Run from repo root:

```
python tools/forensic/fear_greed_reproduce.py
```

Three ledgers searched for any strategy name containing `fear_greed`,
`feargreed`, or `fng`:

| Ledger | File | Variants found | Rows | WR | PF | Expectancy | Lifetime span |
|---|---|---|---|---|---|---|---|
| `closed_picks` | `alpha_engine/data/closed_picks.json` | `st_fear_greed_contrarian (Revival)` ×1 | 1 | 0.0% | 0.0 | -6.93% | 2026-03-29 only |
| `universal_resolved` | `audit_trail/data/universal_resolved_picks.json` | `st_fear_greed_contrarian` ×29 | 29 | **44.83%** | **1.671** | +0.51% | 2026-03-23 → 2026-04-12 |
| `claudes_test_state` | `audit_dashboard/data/claudes_test_state.json` | `st_fear_greed_contrarian` ×30, `fear_greed_contrarian_btc` ×1, `fear_greed_contrarian_eth` ×1 | 32 | 9.38% | 0.222 | -1.05% | 2026-03-13 → 2026-04-04 |
| **Combined** | — | — | **62** | **25.81%** | **0.605** | -0.41% | — |

The "202 picks, 44.6% WR, PF 0.68" is **not** reproducible from any
individual ledger. The closest match is the aggregate across ledgers
(PF 0.605 rounds to 0.6) and the universal ledger's 44.83% WR. The
number almost certainly came from the audit dashboard's cross-system
`strategy_performance` aggregation (see §Hypothesis E below), which
sums picks tagged with the same `strategy` field across multiple feeder
systems — inflating the count because the tag is used by both the
actual paper-trading strategy and by `claude_gainer_st` conviction
labelling.

The "#1 performer, 83% WR" claim maps exactly onto the dashboard
aggregation at `dashboard_data.json systems[21]/strategies[0]`:
```
system name = "claude_gainer_st"
strategy    = "st_fear_greed_contrarian"
resolved    = 722
wins        = 584       (WR 80.9%)
total_pnl   = 1042.91
top_symbols = APTUSDT, UNIUSDT, DOTUSDT, SOLUSDT, OPUSDT
last_signal = 2026-04-12 02:24:54
```

Compared with the true paper-trading aggregation at
`systems[0]/strategies[13]`:
```
system name = "aggregated_picks"
strategy    = "st_fear_greed_contrarian"
resolved    = 4
wins        = 1        (WR 25.0%)
total_pnl   = -2.59
top_symbols = DOTUSDT (0/3), LINKUSDT (1/0)
```

Two universes, one strategy name.

## Timeline

Using `universal_resolved_picks` (the only ledger with enough real
paper-trading history):

- Strategy lifetime: 2026-03-23 20:01 UTC → 2026-04-12 15:28 UTC (≈20 days).
- Peak rolling-48h WR: 2026-03-29 18:07 UTC, WR 100% (n=5) — small sample.
- First rolling-48h drop below 50% with n≥10: 2026-03-27 12:35 UTC,
  WR 0%, n=10 (i.e. the "collapse" had already happened **before** the
  peak 2 days later — the series never built a stable edge).
- Most recent rolling-48h point: 2026-04-12 15:28 UTC, n=5, WR 80%,
  PF 8.98 (tiny sample; not evidence of recovery).
- Code history: only **two** commits have ever touched
  `paper_trading/strategies/fear_greed_contrarian.py`:
  - `cb0202834d` — original "Paper Trading Portfolio System" commit (add).
  - `3c59800e69` — "feat(MiniMax): Add edge-optimized strategies"
    (2026-04-13 01:06 +0800; does **not** modify the F&G file itself,
    but adds a sibling `MiniMaxFGIRegimeStrategy` in the same sweep —
    no actual edit to the F&G strategy logic).

So the paper-trading strategy has been effectively frozen code for the
entire collapse window.

## Hypothesis test: (a) Regime shift

Evidence: **Partial, but not causal.**
`curl https://api.alternative.me/fng/?limit=2` returns `value: 12
(Extreme Fear)` and `value: 16 (Extreme Fear)` today. The strategy's
trigger condition is `current_value <= 20 → LONG`, `>= 80 → SHORT`,
otherwise no pick. So the last ~7 days have likely been **all LONG
entries into extreme-fear crypto**, which (given recent BTC/alt weakness
visible in the data-quality section of `feature_health_report.json`:
`BTCUSDT: 5.3% / 6.8% jumps down`, `BNBUSDT: 10.8% jump down`) means
every pick has been a knife-catch into a falling market.
This contributes to the 44.83% WR in `universal_resolved_picks`,
but it does **not** explain the 202-pick count or the 83% historical
WR — those originate from `claude_gainer_st`, not from F&G triggers.

Verdict: **Contributes to the real strategy's mediocre 44.8% WR, does
not explain the headline number. Not the primary cause.**

## Hypothesis test: (b) Feature drift

Evidence:
- Alternative.me `/fng/` endpoint responds in <1s with valid JSON.
- Values are monotonically updating (`12`, `16` — distinct days).
- `feature_health_report.json:402` lists `market_fear_greed: 100.0% missing`
  — the feature isn't being captured in the ledger at all. That's a
  **data-capture pipeline defect**, not a data-source drift: the F&G
  value is fine, but it's not being stored on picks, so no downstream
  scorer / ML filter has visibility into whether F&G was low or high
  when a pick fired. That is a pre-existing gap, not something that
  "broke" in the last 48h.
- The strategy file has no caching failure path: `@cached(ttl=3600)` +
  `@rate_limited(2.0)` with a single endpoint and **no failover**. This
  violates the project's API-failover rule (3+ fallbacks required). A
  transient outage would simply produce **no picks**, not bad picks.

Verdict: **No drift in the F&G source. The feature-capture gap
(`market_fear_greed` 100% missing) is a real defect but pre-dates the
collapse and is orthogonal to it.**

## Hypothesis test: (c) Code bug

Evidence:
- `git log --follow paper_trading/strategies/fear_greed_contrarian.py`
  shows only 2 commits: original add (`cb0202834d`) and a MiniMax sweep
  (`3c59800e69`) that did **not** modify the F&G file.
- The F&G strategy file has not been edited in the collapse window.
- The per-pick generation logic uses a single `api.binance.com`
  endpoint (also a failover-rule violation, but would manifest as
  missed picks, not bad picks).
- The strategy's internal logic is tiny (~40 lines) and has no hidden
  state.

Verdict: **No code change in the strategy file across the collapse
window. Not a code bug in the F&G strategy itself.**

## Hypothesis test: (d) Data leakage / overfit

Evidence:
- The "elite 83% WR / 584 wins" number is reported in
  `audit_dashboard/data/dashboard_data.json` as
  `strat_fwd_wr: 80.6, strat_fwd_pf: 6.14, forward_wr: 80.9,
  forward_pnl: 1042.91, wins: 584`. These are **forward** stats, not
  backtest stats, so they are not literally overfit on historical data.
- However, they are **aggregated across feeder systems** that share the
  `st_fear_greed_contrarian` tag — including `claude_gainer_st`,
  `super_signals`, `alpha_engine`, `mercury2`, `dna_winner_picks` etc.
  (see the `source_systems` list: 25–29 entries per aggregated row).
- `strategy_distinct_symbols: 0` is set on every aggregated row, which
  should be a red flag — 584 wins on zero distinct symbols is
  impossible unless the symbol field is being stripped during
  aggregation.
- `strat_last10_wr: 40.0` and `_low_wr_penalty: True,
  _degradation_delta_pp: 0.3` are already flagged in the dashboard
  data, showing the downstream scorer noticed the recent 10-pick window
  had dropped from 80% to 40%.
- The actual paper-trading strategy shows `hf_conviction_reasons:
  ['tier_s_fear_greed_proven_core_symbol']` and
  `hf_conviction_tier: 'S'` on picks aggregated under this tag — the
  conviction tier is **inherited** from the historical 80.9% number, so
  picks from other sources get an undeserved S-tier boost because they
  carry the tag.

Verdict: **Not classical overfit, but a sibling defect: the historical
80.9% WR was built from a pool of picks that is NOT the same pool as
the picks now being measured. The edge was never real at the strategy
level — it was the `claude_gainer_st` scanner's edge, temporarily
aliased under this tag.**

## Hypothesis test: (e) Something else — strategy-tag aliasing

Evidence (DECISIVE):
1. Two separate entries in `dashboard_data.json` systems array use the
   same `strategy: st_fear_greed_contrarian` name:
   - `systems[0] "aggregated_picks"` → 4 resolved, 25% WR, -2.59 PnL,
     symbols DOT/LINK.
   - `systems[21] "claude_gainer_st"` → 722 resolved, 80.9% WR, +1042.91,
     symbols APT/UNI/DOT/SOL/OP.
2. The real strategy file `paper_trading/strategies/fear_greed_contrarian.py`
   only trades symbols `BTC, ETH, SOL, BNB, XRP` (first 5 of
   `SENTIMENT_TOKENS`, see lines 7–10 + 44). APT, UNI, OP are **not in
   the whitelist** — they cannot have come from the F&G strategy file.
3. `forward_pnl: 1042.91, forward_wr: 80.9` is repeated verbatim on 294
   distinct dashboard rows — every pick that ever carried the tag
   inherits the same headline number, including ones from completely
   unrelated feeder systems.
4. Several rows carry `hf_conviction_reasons: ['fear_greed_blocked_symbol']`
   — meaning a downstream filter already noticed the tag was firing on
   symbols outside the F&G whitelist.
5. The user-reported number "202 picks, 44.6% WR, PF 0.68" is closest
   to the **combined-ledger aggregate in our reproduction**
   (combined rows 62, WR 25.8%, PF 0.61) scaled up by the
   `claude_gainer_st` 48h contribution — i.e. the audit dashboard is
   computing its 48h stats over the union of the real F&G strategy
   picks + the `claude_gainer_st` picks wearing the same tag, and the
   `claude_gainer_st` scanner's recent 48h has been losing hard.

Verdict: **DECISIVE — the strategy tag `st_fear_greed_contrarian` is
aliased across at least 2 feeder systems, and the dashboard aggregates
them as one strategy. The "83% → PF 0.68 collapse" is the
`claude_gainer_st` scanner's recent performance showing through the
alias, not a collapse of the F&G contrarian logic.**

## Recommendation

**Do NOT kill `st_fear_greed_contrarian`.** The actual
`paper_trading/strategies/fear_greed_contrarian.py` code is harmless,
tiny, and has fired only ~30 real picks. Killing the tag will
mis-target the problem and remove a legitimate (small-sample) sentiment
input.

Instead, in follow-up PRs:

1. **Fix the tag collision.** Rename the paper-trading strategy's
   emitted tag to something unambiguous (e.g. `pt_fng_contrarian_v1`)
   and stop `claude_gainer_st` from reusing `st_fear_greed_contrarian`
   as a conviction label. Aggregation must be keyed on
   `(source_system, strategy)`, not `strategy` alone. See the Hedge-Fund
   investigation protocol in `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
   before any kill decision.
2. **Audit `claude_gainer_st`'s real 48h WR under its own name.** That
   is the actual system losing money. Run it through
   `tools/mutation_analysis.py` per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.
3. **Patch the F&G strategy's API failover** to comply with the
   3+ fallback rule: Binance mirrors → CoinGecko → KuCoin → CryptoCompare
   (see `CLAUDE.md` "API Failover Rule"). Currently uses one
   `api.binance.com` + one `api.alternative.me`.
4. **Restore `market_fear_greed` feature capture** on picks — the
   feature is 100% missing in `feature_health_report.json`, so no ML
   filter can use it. Out of scope for this PR.
5. **Investigate the `high_conviction_gate_passed: True` false-positive.**
   Several aggregated rows pass the gate because they inherit the
   alias's 80.9% WR — the gate is being fed cross-contaminated history.

This PR is READ-ONLY: no strategy code, filter, or gate is touched.

## Appendix: data source paths

Absolute paths on disk (Windows):

- Strategy definition:
  `E:\findtorontoevents_antigravity.ca\paper_trading\strategies\fear_greed_contrarian.py`
- Closed-picks ledger (3,331+ rows, 1 FG match):
  `E:\findtorontoevents_antigravity.ca\alpha_engine\data\closed_picks.json`
- Universal resolved picks (3,864 rows, 29 FG matches, PRIMARY source):
  `E:\findtorontoevents_antigravity.ca\audit_trail\data\universal_resolved_picks.json`
- Claude's test state (per-portfolio history, 32 FG matches):
  `E:\findtorontoevents_antigravity.ca\audit_dashboard\data\claudes_test_state.json`
- Feature health (F&G feature 100% missing):
  `E:\findtorontoevents_antigravity.ca\alpha_engine\data\feature_health_report.json`
- Dashboard aggregation (where the 80.9% headline lives):
  `E:\findtorontoevents_antigravity.ca\audit_dashboard\data\dashboard_data.json`
  - `systems[0]/strategies[13]` — real paper-trading result (25% WR, -2.59)
  - `systems[21]/strategies[0]` — aliased claude_gainer_st result (80.9% WR, +1042.91)

Reproduction numbers (as of 2026-04-13):

| Source | N | WR | PF | Expectancy | Window |
|---|---|---|---|---|---|
| closed_picks.json | 1 | 0% | 0 | -6.93% | 2026-03-29 |
| universal_resolved_picks.json | 29 | 44.83% | 1.671 | +0.51% | 2026-03-23 → 04-12 |
| claudes_test_state.json | 32 | 9.38% | 0.222 | -1.05% | 2026-03-13 → 04-04 |
| **Combined (true strategy footprint)** | **62** | **25.81%** | **0.605** | **-0.41%** | 31 days |
| dashboard systems[21] (aliased) | 722 | 80.9% | 6.14 | +1.44% | reports only |
| dashboard systems[0] (real agg) | 4 | 25.0% | n/a | -0.65% | reports only |

Live F&G index today: `value=12 (Extreme Fear)`, `value=16 (Extreme Fear)`
— strategy is currently LONG-biased into a falling crypto market.
