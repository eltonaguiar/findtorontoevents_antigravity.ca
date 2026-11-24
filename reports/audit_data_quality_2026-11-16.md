# /audit data-quality audit — 2026-11-16

**Scope:** live `https://findtorontoevents.ca/audit/data/dashboard_data.json` (24,998,669 bytes, `generated_at 2026-11-16T13:06:26Z`, `repo_sha 81fa1a3`) plus the code that labels, gates and renders the picks.
**Method:** every pick-shaped dict in the published payload (7,654 rows) was re-scored from its own fields; claims in `summary`, `asset_class_summary`, `money_ready_verdicts`, `verified_alpha`, `tier2_proven_strategies` and the `_TRUST_PROVEN_*` JS registries were compared against that ledger. No DB writes, no local dashboard regeneration.
**Verdict:** the pipeline is not lying on purpose, but several labels are not evidence-backed and at least three numbers on the page cannot all be true at once.

---

## Severity summary

| # | Finding | Severity | Evidence |
|---|---|---|---|
| 1 | `PROVEN` tag is name-matched from a hand-written JS list, and 97/97 tagged rows fail a PROVEN definition | **P0** | `extreme_fear` = 52 PROVEN rows, ledger WR 9.6% / PF 0.12 |
| 2 | Class verdict and class ledger disagree, in one case by 42 WR points | **P0** | ETF: published WR 2.2%, ledger 44.3% on 567 trades |
| 3 | A stop that should have fired is recorded as a −135% short, clamped to −99% | **P0** | `NEARUSDT` SHORT, entry 1.356 → exit 3.193, SL 1.37973, "STALE 5809h" |
| 4 | Three incompatible total-P&L headlines in the same payload | **P1** | −77.67 / −1,356.44 / −99.0 / −99.9 annualised |
| 5 | `zero_pnl_count: 132` while 3,868 rows carry `pnl_pct 0.0` | **P1** | 2,938 of them EXPIRED crypto |
| 6 | 48.9% of closed picks have an empty `closed_at` | **P1** | 3,343 / 6,843 |
| 7 | 102 rows have a stop on the wrong side of entry | **P1** | `ARBUSDT` LONG entry 0.1261, SL 0.12826 |
| 8 | Crypto is hard-coded LONG-only while SHORT is the only profitable side | **P1** | LONG PF 0.51 / −1,514.8% vs SHORT PF 1.89 / +617.0% |
| 9 | Smart Picks is empty in every class; the score floor is unreachable | **P1** | `smart_picks: []`, 1.9% of crypto picks score ≥65 |
| 10 | `BOND.thresholdPass = true` on a class with zero picks | **P2** | avgScore 0, smartCount 0, all six other classes false |
| 11 | `tier2_proven_strategies` serves a PF 0.11 / MDD 124.7% card | **P2** | `signal_validation`, tier "Below Tier 3" |
| 12 | `verified_alpha` advertises 70.9% WR from ~7-pick samples vs 42.4% realised | **P2** | `avg_sample_size 7.0`, 896 realised trades |
| 13 | 15 rows have a status that contradicts the sign of their P&L | **P2** | LOST +1.24%, +1.56%, +1.93% |

---

## 1 · `PROVEN` is a name lookup, not a measurement

`audit_dashboard/template.html` holds two hand-curated `name → weight` maps, `_TRUST_PROVEN_STRATEGIES` and `_TRUST_PROVEN_SYSTEMS`, and `getTrustTier()` assigns the badge from them plus an auto-trust fallback. The **Proven Only** button filters by name against that assignment — `audit_dashboard/AUDIT_FRONTEND_MANIFEST.md:39` says so outright ("name-match, not a live closed-pick query"). `dashboard_generator.py` copies the resulting tier onto the pick as `trust_tier`.

**All 97 PROVEN rows are emitted by a single source, `ml_bg_system_f`** (ledger n=97, WR 20.6%, PF 0.31). That system is explicitly commented out of `_TRUST_PROVEN_SYSTEMS` as "51.6% WR, PF 1.24 = marginal", so the badge is **not** a name match from that table: the payload's `trust_tier` is written upstream by the generator from a static strategy allowlist plus forward stats, and the UI's `getTrustTier()` re-derives its own tier from the JS registries in parallel. Neither layer re-reads the source's resolved rows, which say 20.6% WR and PF 0.31.

**The published system rollup does not reconcile to the published picks.** `systems[]` for `ml_bg_system_f` claims **554 closed picks at 42.1% WR / PF 0.89**, while the payload exposes only **97 resolved rows** for the same source at 20.6% / 0.31. Across the 12 systems with at least 10 ledger trades, 2 disagree with their own picks by more than 15 points: `forward_signals` reports 0.0% WR against a 42.1% ledger (Δ42.1), `ml_bg_system_f` Δ21.5. Either the rollup counts rows the payload does not expose, or it counts them differently — either way the badge and the class tiles inherit the error.

97 rows in the live payload carry `tier === PROVEN`. Every one of them fails the definition the page itself publishes (`pick_funnel.html`: WR_shrunk ≥ 55%, PF ≥ 1.5, n ≥ 20):

| Strategy carrying PROVEN | PROVEN rows | Ledger closed | WR | PF | ΣPnL |
|---|---|---|---|---|---|
| `extreme_fear` | 52 | 52 | **9.6%** | **0.12** | **−224.0%** |
| `momentum_breakout` | 34 | 34 | **20.6%** | **0.37** | — |
| `crash_reversal` | 11 | 11 | 72.7% | 3.07 | — (n=11 < 20) |

Every one of the 97 rows belongs to `ml_bg_system_f`; the three strategy names are facets of one emitter, so this is a single mislabelled source rather than three coincidences.

Registry justification strings are themselves stale or category-inappropriate:

- `crypto_vwap_deviation_reversion` — `'+332% total P&L'`, no n, no window, and **zero closed rows** in the published payload.
- `contrarian_liquidity_grab` — `'9/11 active picks profitable, +41.89% unrealized'`. Unrealised marks are being used as proof.
- `extreme_fear` — `'F&G extreme fear DCA — contrarian proven'`, while the ledger says 9.6% WR / −224%.
- 21 of the 26 registry names have **no closed rows at all** in the payload (`crypto_vwap_deviation_reversion`, `drawdown_recovery_rsi`, `multi_period_rsi_confluence_xrp`, `crypto_keltner_compression_expansion`, `keltner_compression_expansion`, `crypto_rsi_whaleconfirmed`, `funding_momentum`, `contrarian_liquidity_grab`, `supertrend_vwma_confluence`, `short_only_contrarian`, `triple_confirmation`, `keltner_rsi2_squeeze`, `simplified_kimi_rsi2`, `supertrend_optimized`, `vwma_momentum`, `fractal_sr_bounce`, `crypto_choppiness_regime_switch`, `crypto_drawdown_convexity_recovery`, `crypto_kalman_trend_residual_reversion`, `crypto_soc_orderflow_absorption`, `crypto_soc_regime_filters_a05`).

Two secondary tags inherit the problem: `research_cohort: verified_alpha` appears on 619 rows while `forward_validated: True` appears on **12 of 4,132** rows.

## 2 · Class verdict vs class ledger

`money_ready_verdicts` is the per-class statistical verdict; the pick ledger is the same data it claims to summarise. They disagree materially:

| Class | Published verdict | Published WR / PF | Ledger (resolved, pnl≠0) | Ledger WR / PF | ΣPnL |
|---|---|---|---|---|---|
| CRYPTO | NOT_READY | 35.8% / 0.92 | n=1,964 | 39.8% / 0.76 | −897.9% |
| EQUITY | NOT_READY | **59.2% / 0.94** | n=739 | **47.1% / 1.15** | +230.6% |
| ETF | INSUFFICIENT_DATA | **2.2% / 0.02** | n=567 | **44.3% / 1.04** | +22.9% |
| FOREX | NOT_READY | 32.0% / 0.65 | n=173 | 40.5% / 0.60 | −31.4% |
| BOND | INSUFFICIENT_DATA | 0.0% / 0.00 | n=35 | 37.1% / 0.59 | −7.7% |
| COMMODITY | WATCH | 40.3% / 1.03 | n=16 | 25.0% / 0.33 | −18.6% |

Two of these are internally strained even without the ledger: EQUITY at 59.2% WR with PF 0.94 requires average losses far larger than average wins, which the ledger contradicts; ETF at 2.2% WR over a class the ledger says has 567 resolved trades is measuring something else entirely (most likely a tiny recent window, but the page does not say so).

`asset_class_summary` adds a third version: CRYPTO `forwardWR 0.5`, EQUITY `0.0`, FOREX `0.0`, FUTURES `0.049` — all from a different denominator again.

## 3 · P&L integrity

**The clamped loss that hides a broken stop.** `NEARUSDT` SHORT, `clone_hl_copy_lb_None`: entry 1.356, TP 1.3372, SL 1.37973, exit **3.193** (+135% against), status `EXPIRED`, reason `STALE (auto-expired >5809h)`, `pnl_pct −99.0`, `pnl_pct_ingest_clamped: true`, `pnl_pct_pre_clamp: −135.472`. The stop sat 1.7% above entry and was never taken; the pick aged 242 days and then expired. Two identical rows exist. `audit_trail/pnl_ingest_sanity.py` clamps crypto at (−99, +500) — reasonable as an ingest guard, but here it converts "our stop failed" into "we lost 99%", and the pre-clamp value survives only in a side field.

**Four total-P&L numbers.** `summary.total_pnl_pct −77.67`, `total_pnl_pct_sum_raw −1356.44`, `total_pnl_pct_compounded_ew −99.0` (hard-floored at −99 by `dashboard_generator.py:14927`), `total_pnl_pct_geomean_annualized −99.9`. Any one of them may be defensible; presenting all four without labels is not.

**Flat-zero accounting.** `zero_pnl_count` and `flat_count` both report 132, but 3,868 rows carry `pnl_pct === 0.0` — 2,938 EXPIRED crypto, 158 EXPIRED forex, 74 EXPIRED equity, all 10 futures. Those rows are not flat trades, they are unresolved ones wearing a 0. `total_resolved` is computed as wins + losses + 132, so ~3.7k rows sit outside the headline accounting.

**Timestamps.** 3,343 of 6,843 closed picks (48.9%) have `closed_at: ""`; EXPIRED rows also carry `resolved_at: ""` and a prose `exit_reason` (`STALE (auto-expired >5809h)`) instead of a code. Time-to-resolution and decay analysis cannot be reproduced from the payload.

**Status vs sign.** 15 rows are labelled LOST while their P&L is positive (ADATUSDT +1.24%, DOTUSDT +1.56%, LINKUSDT +1.93%, SUIUSDT +0.40%, QQQ +0.34%, ETHUSDT +1.19%). Status and P&L are being written by different paths.

**Stops on the wrong side.** 102 rows fail `LONG: tp > entry > sl` / `SHORT: tp < entry < sl`, e.g. `ARBUSDT` LONG entry 0.1261 / SL 0.12826 (stop above entry), `NZDUSD=X` LONG entry 0.55448 / SL 0.55473, `DOTUSDT` SHORT entry 0.834 / SL 0.816703 (stop below entry). A long with its stop above entry is either a post-move trailing stop persisted as the original, or a sign bug; either way `sl` is not usable for risk sizing on those rows.

## 4 · Algorithms per asset class

**Crypto LONG-only is backwards.** `quality_gates.py:855` sets `SMART_PICKS_CRYPTO_LONG_ONLY = True`, and the gate rejects crypto SHORTs outright. The ledger:

| Direction | n | WR | PF | ΣPnL |
|---|---|---|---|---|
| CRYPTO LONG | 1,356 | 32.7% | 0.51 | **−1,514.8%** |
| CRYPTO SHORT | 608 | **55.6%** | **1.89** | **+617.0%** |

The single most profitable direction in the book is structurally excluded from Smart Picks. (Forex shows the same shape — LONG 38.0% / PF 0.53, SHORT 80.0% / PF 5.97 — on n=10, so treat that one as anecdote.)

**The score floor is unreachable, so every surface is empty.** `SMART_PICKS_MIN_SCORE` and its per-class variants are 65 (CRYPTO), 40 (EQUITY/FOREX), 30 (COMMODITY), 45 (FUTURES), 35 (BOND), frozen "until 2026-08-18" (`quality_gates.py:414`) — a date now three months past. Measured against the live book:

| Class | Floor | Median score | Share ≥ 65 |
|---|---|---|---|
| CRYPTO | 65 | 46.0 | 1.9% |
| EQUITY | 40 | 37.0 | 2.6% |
| ETF | — | 39.0 | 0.5% |
| FOREX | 40 | 38.0 | 0.7% |
| COMMODITY | 30 | 47.5 | 0.0% |

Overall 67 of 3,906 scored rows (2%) clear 65. Result: `smart_picks: []`, `smartCount: 0` in all seven classes, `thresholdPass: false` everywhere except the empty BOND class, and `active: 10` out of `active_raw: 4,122`.

**R:R does not behave monotonically, and the gate cuts across the bad band.** Realised outcomes by planned R:R:

| RR band | n | WR | PF | ΣPnL |
|---|---|---|---|---|
| 0 – 1.0 | 49 | 67.3% | 1.66 | +30.4% |
| 1.0 – 1.5 | 121 | 28.9% | 0.40 | −285.8% |
| 1.5 – 2.5 | 3,241 | 42.4% | 0.92 | −427.0% |
| 2.5 – 3.5 | 46 | 13.0% | 0.56 | −27.4% |
| 3.5 + | 36 | 55.6% | 1.95 | +18.7% |

`SMART_PICKS_MIN_RR 1.5 / MAX_RR 3.5` admits 93% of the book and excludes the two small positive buckets. n<130 outside the middle band, so this is a flag to investigate, not proof of an edge.

**Forward-WR thresholds are met by nobody**: CRYPTO needs 0.62 (has 0.50), EQUITY 0.50 (0.00), FOREX 0.46 (0.00), COMMODITY 0.50 (0.00), FUTURES 0.50 (0.049 from 10 picks that are all 0.00 placeholders). No class is promotion-eligible, and FUTURES' number is computed from unresolved rows.

## 5 · Surfaces that mislead without being wrong

- **`active: 10` vs `active_raw: 4,122`.** The page's "active picks" table is a top-10 cut of a 4,122-row book; the count beside it reads as the book size.
- **`tier2_proven_strategies.cards[0]` = `signal_validation`**, tier "Below Tier 3", WR 4.9%, PF 0.11, **MDD 124.7%**, ΣPnL −119.74%, `n 102` vs `n_closed 511`, `is_stale: true`. It is served under a key named `proven_strategies`; only `is_strict_tier2`/`flagged_dropouts` distinguish it. An MDD over 100% is itself a red flag on the drawdown computation.
- **`verified_alpha`** reports `realized` 896 trades / 42.4% WR / −193.18% ΣPnL / −0.22 expectancy next to `audited.avg_wr_pct 70.9` with `avg_sample_size 7.0`. The 70.9 is an average of very small samples and will be read as the headline.
- **`smart_picks_snapshot_summary`** shows 74.2% WR on 62 picks (39 batches) directly above all-time −77.67%. No window label on the card.
- **Metadata:** `payload_lag_seconds 2269`, `last_policy_change_at 2026-04-09` (seven months), and `data_freshness.last_dashboard_build 13:10:51` is *later* than `generated_at 13:06:26` — the freshness block is written after the payload it describes.

## 6 · Missing fields

No gaps in the core pick contract: `symbol`, `direction`, `entry_price`, `take_profit`, `stop_loss`, `confidence`, `score`, `pnl_pct`, `strategy`, `source_system`, `asset_class`, `status`, `exit_price` are present on all 7,654 rows. Real gaps:

| Field | Gap |
|---|---|
| `closed_at` | empty on 3,343 / 6,843 closed (48.9%) |
| `entry_time` | `""` on stale rows (timestamp survives in `signal_time`) |
| `resolved_at` | empty on EXPIRED rows |
| `ml_score` | null throughout (`SMART_PICKS_MIN_ML_SCORE` already disabled for this reason) |
| `after_cost_net_per_trade`, `wilson_lb_wr`, `is_ac_survivor` | null throughout |

## 7 · What this audit did not establish

- `money_ready_verdicts` internals were not traced to compute; the WR/PF disagreement is reported as an observed contradiction, not as a proven bug in the verdict function.
- Deduplication by `(symbol, strategy, direction, entry_price, closed_at)` found **0** duplicate groups across 3,534 resolved rows — the only exact pair is the `NEARUSDT` one. An earlier count of 624 "duplicates" was an artefact of `opened_at` being absent everywhere; it is withdrawn.
- Whether crypto SOL/ETH-style large single-trade moves are legitimate was not adjudicated beyond the one stop-failure case.
- No DB-side (`at_raw_picks`, `at_signal_outcomes`) reconciliation was run; this is payload-and-code only.

## 8 · Recommended order of work

1. **Stop calling it PROVEN.** Either gate the badge on the published definition (n≥20, WR≥50, PF≥1.5 computed from `at_signal_outcomes`) or rename the button to "Curated watchlist" and drop the tier from the pick payload. Today 97 rows assert an edge the ledger denies.
2. **Reconcile the four P&L totals** into one labelled primary number plus defined alternates; remove the −99 floor from the *headline* (keep it at ingest only, with `pnl_pct_pre_clamp` surfaced).
3. **Fix the stop-failure class**: any row with `exit_reason` starting `STALE` and |pnl| > SL distance is a resolver defect, not a trade. Backfill `closed_at` for the 48.9%.
4. **Re-open the frozen gate review** (`SMART_PICKS_MIN_SCORE_*`, freeze expired 2026-08-18) and test `SMART_PICKS_CRYPTO_LONG_ONLY` against the SHORT ledger before it stays on.
5. **Make class verdicts cite their window and denominator** on the card; make `thresholdPass` false when `activeCount == 0`.
6. **Patch status/sign contradictions (15) and wrong-side stops (102)** at the writer, then re-emit.

## 6 · Asset-class validation, missing classes, and the mega-cap question

Recomputed from the same live payload (7,654 rows). Resolved = WON/LOST/CLOSED/
TP_HIT/SL_HIT with |pnl| > 0.01%.

| Class | rows | resolved n | WR | PF | avg/trade | ΣPnL | worst | share within ±3% |
|---|---|---|---|---|---|---|---|---|
| CRYPTO | 5,437 | 1,964 | 39.8% | 0.76 | −0.46% | −897.9% | −26.04% | 54.0% |
| EQUITY | 935 | 739 | 47.1% | **1.15** | +0.31% | **+230.6%** | −24.60% | 40.6% |
| ETF | 618 | 567 | 44.3% | 1.04 | +0.04% | +22.9% | −10.30% | 76.7% |
| FOREX | 495 | 173 | 40.5% | 0.60 | −0.18% | −31.4% | −2.50% | 99.4% |
| COMMODITY | 82 | 16 | 25.0% | 0.33 | −1.16% | −18.6% | −6.80% | 93.8% |
| BOND | 48 | 35 | 37.1% | 0.59 | −0.22% | −7.7% | −1.28% | 100% |
| FUTURES | 15 | 0 | — | — | — | — | — | — |

**Is any class "generally safe"?** No, but two are *low-variance* for a bad
reason: BOND (all 35 trades inside ±3%, worst −1.28%) and FOREX (99.4% inside
±3%, worst −2.50%) lose because their stops are tight, not because they win —
PF 0.59 / 0.60. ETF is the least destructive class with a positive sum (worst
−10.3%, PF 1.04). EQUITY is the only class with positive expectancy *and* PF
> 1.1; it also carries the second-worst tail (−24.6%).

**Class subsets that actually clear PF 1.1 (n ≥ 45):** `XLF` 53.3% WF / PF 1.70
(n=45), `QQQ` PF 1.22 (n=80), `SOXX` 1.18 (n=37), `XLE` 1.14 (n=58), `XLK` 1.13
(n=64). The ETF aggregate is dragged down by `IWM` (PF 0.58, −26.9%, n=65) and
`GLD` (0.82). The copytrader cohort — 267 rows, 63 resolved — is the best
non-class cohort: WR 54.0%, PF 1.35, +11.1%.

**Missing classes.**
* `MUTUAL_FUND`: was **0 rows, 0 payload strings** and not a registered
  class; it is now registered (2026-11-16) with a daily-NAV data path and
  appears as `INSUFFICIENT_DATA` / `thresholdPass=false` until picks exist
  — see `updates/2026-11-16-mutual-fund-asset-class-nav.md`.
* `SPORTS` exists as 2 rows only — no class surface.
* `PENNY_STOCK` / `MEME` / `CHEAP_STOCKS` appear in `money_ready_verdicts` but
  have no rows in `picks` — verdicts on empty universes.
* **Prediction markets: emitted, never resolved.** POLYMARKET 13 rows, KALSHI
  14 rows, **0 resolved in either** — they cannot be validated in this payload.
  The synthetic-stats path in `stamp_pick_quality.py` (`n=max(source_count,5)`,
  `wr=max(consensus_wr,0.50)`) was removed on 2026-11-16: an empty ledger now
  stays `n=0` / `UNKNOWN` (see `updates/2026-11-16-pm-contract-resolution.md`).
  All 27 live PM rows are spot trades derived from PM signals
  (`pm_pick_kind=spot_derived`), not binary contracts — none is evidence about
  a contract market.

**Mega-caps ("stocks that only go up").**

| Symbol | rows | active | resolved n | WR | PF | ΣPnL |
|---|---|---|---|---|---|---|
| AAPL | 86 | 7 | 78 | 55.1% | **1.74** | **+52.7%** |
| JPM | 62 | 2 | 60 | 53.3% | 1.21 | +11.9% |
| META | 58 | 8 | 47 | 46.8% | 1.23 | +21.1% |
| AMZN | 70 | 5 | 65 | 41.5% | 0.99 | −0.7% |
| GOOGL | 62 | 4 | 55 | 41.8% | 0.81 | −18.6% |
| NVDA | 1 | 1 | 0 | — | — | — |
| MSFT | 2 | 2 | 0 | — | — | — |
| MCD | **0** | 0 | 0 | — | — | — |
| V | 5 | 2 | 0 | — | — | — |
| COST | 11 | 3 | 1 | 0% | 0 | −0.1% |

Only AAPL has both a real sample and a real edge; NVDA/MSFT/MCD have no
resolved history at all, so no claim about them is supportable from this
payload.

**Crypto direction test (pre-registered before flipping anything).** Flipping
`SMART_PICKS_CRYPTO_LONG_ONLY` admits nothing today: of 132 active crypto
SHORTs, 5 pass score>=65 → 5 pass confidence → 4 pass R:R → **0** pass
`forward_validated` (LONG: 5 → 3 → 3 → 0). The gate's binding constraint is
forward validation. The flag is now env-overridable for the A/B, and blocked
SHORTs are tagged `_smart_crypto_short_blocked` so the cost is measurable.


## 7 · forward_validated is emitter-set, and the gate funnel is the real blocker

`forward_validated` was written by emitters (several hardcode `False`); only 11 of
789 active picks carried it while 38 had a 20+ trade strategy ledger. It is now
decided by the ledger (n>=20, WR>=45%, PF>=1.0) in
`audit_trail/forward_validation.py` via the stamper: 40 picks promoted (FOREX 27,
EQUITY 8, ETF 5), 51/789 validated.

That does **not** populate Smart Picks: `passes_active_gate` accepts 32 of 789
(4.1%) and 0 of the 40 promoted picks pass it. The blockers are
`equity_vix_gate_high_vix` (all equities, VIX>22), the FOREX directional gate
(all FOREX longs), `TP_MAGNITUDE_IMPLAUSIBLE` (class TP caps) and crypto M-036.
Cohort evidence: ETF 565 resolved 44.4%/PF 1.04 (XLF 54.5%/1.70 best, IWM
35.4%/0.58 worst); copytraders 63 resolved 54.0%/1.35 with `copy_trader_clones`
16 resolved 75.0%/4.43; prediction markets 27 active, 0 resolved.
Detail: `updates/2026-11-16-forward-validated-ledger-recompute.md`.
