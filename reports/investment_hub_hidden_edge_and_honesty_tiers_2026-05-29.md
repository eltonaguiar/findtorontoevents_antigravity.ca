# Investment Hub Hidden-Edge Audit + Metric Honesty Tiers — 2026-05-29

**Scope:** Audit every pick source behind findtorontoevents.ca's "Investment Hub" (Other Stuff → Links → Investment Hub) for **profitable strategies NOT integrated into `/audit`**; cross-check with peer AIs; and define a peer-reviewed honest-reporting tier system for all metrics.

**Method:** 4 parallel subagents (one per Hub area) ran live read-only queries against `ejaguiar1_stocks`, computed vetted WR/PF (dedup + concentration + outlier-cap + min-n + staleness), and cross-referenced each strategy against the `/audit` funnel (`at_raw_picks.source_system`, 236 distinct sources) and `pf_registry.json`. Every number below comes from a query that was actually run — no dashboard cells trusted.

---

## 1. Headline finding

**There is no production-grade hidden edge in the Investment Hub.** The integration gap is real (most of it never flows into `/audit`), but the gap is not hiding profit — it is hiding the **absence of outcome tracking.** The dominant state across the Hub is "picks emitted, never resolved to a win/loss."

| Hub area | Backing tables (rows) | In `/audit`? | Vetted edge? |
|----------|----------------------|--------------|--------------|
| Stocks | `alpha_picks` (5043), `stock_picks` (7239), `penny_picks` (1029) | No | **None.** alpha_picks/stock_picks have NO outcome columns; penny_picks is a loser (16.3% WR / PF 0.39, n=331). |
| Mutual Funds | `mf2_fund_picks` (600), `mf2_tracked_picks` (75) | No (no MUTUAL_FUND class) | **None.** Only 35 closed trades exist (pooled PF 0.47); main feed never NAV-resolved; stale since Feb. |
| Crypto Pairs / Forex | `cr_pair_picks` (1008), `fxp_pair_picks` (1248) | No | **Unverifiable.** No outcome columns; `*_backtest_trades` companion tables are EMPTY; `*_algo_performance` is synthetic garbage. |
| Goldmines / Miracle / Sim | `gm_unified_picks` (1846), `miracle_picks2/3`, `simulation_picks` | No (separate from the `goldmine_unified` rows already in `at_raw_picks`) | **One "promising-not-valid" candidate** (below); everything else NO-EDGE. |

### The one candidate worth a fresh forward-test (not a wire-up)
`gm_unified_picks / ADX Trend Strength` — WR 74.3% / PF 3.29 on n=70 decisive. **Disqualified from any promotion:** n<100, crypto-concentrated, STALE (newest 2026-02-16), and ~40% of "wins" are **soft-resolved** (max-hold, not a TP hit). Hard-only it's 31W/14L (69%, n=45). Worth a clean forward-test before it could ever be ingested.

---

## 2. Data-quality landmines (the honest-reporting case study)

These are exactly why every metric needs an honesty label:

1. **Unresolved picks shown as "picks."** `alpha_picks` (5043) + `stock_picks` (7239) + `cr_pair_picks` (1008) + `fxp_pair_picks` (1248) + `mf2_fund_picks` (600) = **~14,200 picks with no win/loss tracking.** Any WR/PF for them is impossible to state honestly.
2. **Fabricated summary values.** `fxp_algo_performance` reports `FX Carry Trade avg_return = +999,999.9999%` — a `decimal(10,4)` column-max sentinel from an overflowed backtest stub. `cr_algo_performance` shows +95,692%. **These must never be cited.**
3. **Soft-resolution inflation.** `miracle_picks2 / Mean Reversion Sniper` displays 62.5% WR / PF 2.04 but has **ZERO actual winners** — 8 losers + 40 `expired` rows scored by PnL sign. The "edge" is an artifact of treating expiry as a win.
4. **Empty companion tables.** `cr_backtest_trades`, `fxp_backtest_trades`, `fx_backtest_trades` (and `_results`) exist with the right schema but **0 rows** — the resolver was never wired.

---

## 3. swarm-pr-review consensus (focused audit-integrity cluster)

Four open PRs reviewed (read-only, evidence-backed, no comments posted). **All four: REQUEST_CHANGES, HIGH confidence, LOW fabrication risk.** Common theme = honesty gaps, which reinforces the tier framework.

| PR | Title | Core finding |
|----|-------|--------------|
| **#36** | remove claude_gainer_st carve-outs | Carve-out removal correct, but bundles broken baby-monitor infra: `is_baby_monitored()` checks `pick['origin']` which `_signal_to_dict()` never sets → shadow-mode never fires; `_sizing_override='zero'` has **no enforcement** outside quality_gates.py; `claude_gainer_st` still has +15 in `_SOURCE_SYSTEM_SCORES:5758`. **Split the PR.** |
| **#34** | revoke falsified COMMODITY FV exempt | Primary revoke correct, but **two other frozensets still whitelist the falsified sources**: `_COMMODITY_TRUSTED_SOURCES:9195` and `_CONV_TRUSTED:9488` (both still list `multi_asset_cot`/`multi_asset_copytrader`). Incomplete fix. |
| **#33** | AI tournament CI leaderboard | n≥30 gate + impossible-resolution exclusion correct, but **tier badges use RAW WR/PF, not CI-adjusted** → models show T2 while CI-PF lower bound < 1.0 (honesty gap). Committed diagnostics JSON is stale (RED, 0 picks, 23/39 models). |
| **#35** | wire AdaptiveKeltnerReversion | Wire-up is real (paper_trading), numbers backed by JSON, but `forward_validated` never set → **passes_smart_gate silently rejects every pick**; `KeltnerVWAPConfluence` (WR 42.5%, PF 1.34) is sub-T2 yet co-registered without a probation label; backtest 82d stale, no fee/slippage model. |

(20+ PRs are open; this was the data-quality-relevant cluster. The rest can be reviewed on request.)

---

## 4. Metric Honesty Tiers (deliverable — peer-reviewed)

New artifacts:
- **`audit_dashboard/data/metric_honesty_tiers.json`** — machine-readable source the dashboard tooltips render from.
- **`docs/METRIC_HONESTY_TIERS.md`** — human definitions + peer-review log.

Six labels answer "how much do I trust this number?": 🟢 Institutional-grade · 🔵 Production-viable · 🟡 Promising-not-valid-yet · 🟠 Unverified (no resolved outcomes) · 🔴 No-edge · ⛔ Disputed/contaminated. Thresholds inherit from `PERFORMANCE_CHARTER.md`; the **decisive-outcome rule** (only hard TP/SL resolutions count; OPEN never counts; soft-resolution counted separately) is the load-bearing definition.

**Peer-reviewed in 2 rounds, 7 distinct models** via `/PeerReviewSwarmOptions` (`consult_multi --fanout reasoning4` then `diverse5`):
- Round 1 (nvidia/kimi, nous/Hermes-405B, fireworks/kimi): 3/3 → keep n≥200; **zero-soft for green**; keep Unverified/Disputed as two tiers; staleness = hard gate for green. Biggest loophole = TP/SL payoff-asymmetry gaming.
- Round 2 (groq/qwen, fireworks/kimi, together/llama): derived the **un-gameable expectancy gate** — break-even WR `BE = 1/(1+R:R)`; require Wilson-lower-bound WR > BE (positive expectancy on the CI lower bound). Added loss-tail/PF-binding gate. This replaced the arbitrary "R:R<0.5 AND WR>65%" trigger.

---

## 5. Recommendations (priority order)

1. **P0 — stop displaying unverified picks as if resolved.** Tag the ~14.2k untracked Hub picks 🟠 *Unverified*; never show a WR/PF for them. Add a DISPUTED ⛔ banner to `*_algo_performance` (999,999% sentinel) and the `miracle_picks2` soft-resolution cohorts.
2. **P0 — finish the incomplete revocations** flagged by PR #34 (`_COMMODITY_TRUSTED_SOURCES`, `_CONV_TRUSTED`) and the PR #33 tier-badge raw-vs-CI honesty gap.
3. **P1 — wire an outcome resolver** for the Hub feeds (pattern: `alpha_engine/outcome_resolver.py`). The `*_backtest_trades` schemas already exist and are empty — populate them. Only *then* can these areas be assessed for edge.
4. **P1 — fresh forward-test** `ADX Trend Strength` (the lone candidate) on post-April data, hard-resolved only, before any `/audit` ingestion.
5. **P2 — render the honesty tooltips** from `metric_honesty_tiers.json` on `/audit` + Hub pages (deferred under the remote-ops freeze; no deploy performed).

---

*Generated 2026-05-29. All edits local/uncommitted (remote-ops freeze respected). Reproducers for every figure are embedded in the per-area subagent outputs and the JSON `current_live_examples`.*
