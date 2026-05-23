# /audit — Additional High-Leverage Fixes — 2026-04-20

**Source:** `audit_dashboard/data/dashboard_data.json` (3,500 recent closed, 37 active at read time).
**Scope:** complements `docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md`; surfaces fixes **not** already in that doc's top-3 list.
Peer-coord note: broadcast sent on agent-bus at start; no conflicting peers responded during the session.

---

## 1. Top-15 PF drag by (source_system, strategy)

Restricted to clusters with n >= 5 closed picks; "status" column resolved against `alpha_engine/strategy_blocklist.py`.

| # | source_system | strategy | n | WR% | total_pnl% | PF | Current status | Recommendation |
|---:|---|---|---:|---:|---:|---:|---|---|
| 1 | copy_trader_intel | copy_hl_lb_None | 233 | 34.3 | **-765.9** | 0.56 | RETIRED (strategy) | **Block source+strategy pair still emitting** — `copy_trader_intel` keeps picking it up; add `(copy_trader_intel, copy_hl_lb_None)` to `_RETIRED_SYSTEM_STRATEGY_PAIRS` and verify upstream filter |
| 2 | claude_gainer_st | st_fear_greed_contrarian | 640 | 26.1 | -260.0 | 0.54 | RETIRED (today) | Confirm feed-hygiene actually rejects; backfill-purge from `recent_closed` cap |
| 3 | claude_gainer_st | st_obv_support_divergence | 86 | 23.3 | -82.7 | 0.18 | PAPER-ONLY | Promote to RETIRED — PF 0.18 on n=86 is catastrophic |
| 4 | kimi_signal_tracking | kimi_signal_tracking | 16 | 18.8 | -54.9 | 0.23 | none | Self-named strategy = missing label; block system+strategy pair |
| 5 | kimi_signal_tracking | (empty) | 26 | 38.5 | -52.6 | 0.60 | none | Reject empty-strategy picks at ingest (`feed_hygiene`) |
| 6 | alpha_engine | copy_hl_lb_None | 45 | 20.0 | -40.5 | 0.44 | RETIRED (strategy) | Second emitter of retired strategy — root-cause why blocklist is leaking |
| 7 | rapid_fire | macd_rsi_confluence | 45 | 33.3 | -37.5 | 0.54 | none | Investigate per `STRATEGY_INVESTIGATION_BEFORE_KILL.md`; candidate for PAPER |
| 8 | luxalgo_filters | luxalgo_confluence | 158 | 37.3 | -26.1 | 0.86 | PAPER-ONLY | Large n, shallow loss — confirm paper-only actually prevents live emission |
| 9 | quan_engine | unknown | 25 | 12.0 | -22.4 | 0.26 | none | Reject `strategy == "unknown"` at ingest |
| 10 | multi_asset_copytrader | smart_money_accumulation | 5 | 20.0 | -18.9 | 0.20 | none | Too few samples, watch |
| 11 | kimi_riseoftheclaw | call-surge-scout | 8 | 25.0 | -14.6 | 0.22 | none | Candidate for PAPER |
| 12 | kimi_riseoftheclaw | betting-against-beta | 13 | 23.1 | -14.0 | 0.24 | none | Candidate for PAPER |
| 13 | kimi_riseoftheclaw | ema-ribbon | 5 | 20.0 | -9.7 | 0.00 | none | Too few samples |
| 14 | kimi_riseoftheclaw | options-flow-scout | 5 | 0.0 | -9.0 | 0.00 | none | Investigate (0 wins) |
| 15 | baby_strats_forward | crypto_mtf_ema_slope_alignment_v1 | 13 | 7.7 | -6.8 | 0.18 | PAPER-ONLY | Paper gating is working; keep |

**Leakage finding:** retired strategies `copy_hl_lb_None` still account for **-806.4%** of closed PnL (rows 1 + 6). The block exists in `_RETIRED_STRATEGIES` but two `source_system`s (`copy_trader_intel`, `alpha_engine`) are bypassing it. Root-cause: blocklist is checked on emission but these picks predate retirement or the guard was added mid-ledger.

---

## 2. Survivorship analysis — is PF 0.76 a legacy artifact?

| Window | n | WR% | total_pnl% | PF |
|---|---:|---:|---:|---:|
| All 3,500 (with pnl) | 3,304 | 39.0 | -1,115.7 | **0.716** |
| Last 30d (closed_at) | 3,074 | 39.3 | -996.0 | 0.728 |
| Last 7d (closed_at) | 2,295 | 36.3 | -1,087.4 | 0.669 |
| **All-time excluding RETIRED+PAPER strategies & composite pairs** | 2,309 | **45.0** | **+155.0** | **1.105** |

**Finding:** the bleed is NOT legacy — the last 7 days is actually **worse** (PF 0.669) than all-time. But removing already-blocklisted strategies flips aggregate from -1,116% / PF 0.72 to **+155% / PF 1.10**. That means the live product *would already be PnL-positive* if the blocklist were actually preventing emission. This validates fix #1 above: the blocklist is **leaking**, not incomplete.

---

## 3. Dead/stale active picks

Active = 37. Stale (> 24h since `entry_time`) = **1** (`aggregated_picks:币安人生USDT` moderate-consensus, age 61.8h, pnl -5.56%). Low count — not a systemic issue today, but `entry_time` is null on 14/37 actives (38%), which hides staleness. Add ingest-side backfill of `entry_time` from `timestamp`.

---

## 4. Data-quality patterns NOT in the parent audit

| # | Issue | Count | Note |
|---|---|---:|---|
| A | Closed picks with no `exit_price` | 4 | small, but any >0 breaks replay |
| B | Closed picks with null/empty `strategy` | 26 | all from `kimi_signal_tracking` |
| C | Closed picks with `strategy == "unknown"` or `strategy == source_system` (self-named) | **185** | top clusters: `non_crypto_consensus/self` 82, `kimi_signal_tracking/self` 16+26, `quan_engine/unknown` 25, `kimi_riseoftheclaw/unknown` 14, `regime_terminal/unknown` 10 |
| D | Active picks with 2+ source_systems emitting same (symbol, direction) | 6 / 37 pairs | cross-system duplicate surfacing |
| E | Active pick with `exit_price` set | 0 | parent audit said 1; not reproducible today |
| F | Active picks missing `entry_time` | 14 / 37 | blocks staleness detection |
| G | `ml_score` coverage on `recent_closed` | **0 / 3,500** | field is stripped or never snapshotted at close |
| H | `at_issue_strat_fwd_wr` coverage on closed | 333 / 3,500 (9.5%) | at-issue stamping is only partially wired |

Issue C (185 self-named/unknown strategies) + B (26 empty) = **211 picks / 6%** with no strategy identity, meaning any strategy-level analytics silently lose 6% of samples.

---

## 5. Schema — fields to ADD to `_CLOSED_PICK_KEEP_FIELDS`

Current allowlist misses several fields that are present on `active` picks but **stripped before writing to `recent_closed`**, making retroactive feed replay impossible:

| Field | Active coverage | Closed coverage | Why add |
|---|---:|---:|---|
| `ml_score` | 37/37 | 0/3,500 | Blocks any downstream ML-filter backtest (parent audit rec #2 relies on this) |
| `hf_conviction_tier` | 20/37 | 0/3,500 | HC feed is the only positive-edge cohort — must persist through close |
| `va_cohort_id` + `va_cohort_wr_pct` | 15/37 + 8/37 | 0/3,500 | Verified-Alpha retro-audit currently impossible |
| `sym_track_wr` (+ total/wins/losses) | 8/37 | 0/3,500 | Track% feed has zero closed-side telemetry (parent audit flagged as "incomplete") |
| `agreement_count` / `consensus_count` | 37/37 | 0/3,500 | Consensus-feed edge cannot be measured |
| `paper_trade` flag | 37/37 | 0/3,500 | Paper-only strategies pollute live aggregate without this |
| `entry_time` | 23/37 | 0/3,500 | Closed picks only have `timestamp` + `closed_at`; no explicit open time |
| `display_tier` | 37/37 | 0/3,500 | Front-end tier mapping unstable across releases |

Minimum add recommended: **`ml_score`, `hf_conviction_tier`, `va_cohort_id`, `sym_track_wr`, `paper_trade`, `entry_time`** (6 fields). These directly enable audit recommendation #2 (at-issue stamping).

---

## 6. Workflow / cron health gaps affecting edge detection

Last 80 runs on `main`, by failure count:

| Workflow | Failures | Impact on audit |
|---|---:|---|
| **ALPHA ENGINE - Dynamic Runner (Cloud or Local)** | **41** | This is the forward-validation + blocklist-enforcement loop. 41 failures = blocklist may never be re-checked against new picks → explains leakage in §1 |
| Unified Audit Dashboard | 15 | Dashboard data staleness risk |
| Deploy findtorontoevents.ca core site | 4 | User-facing /audit page updates |
| CI Tests | 3 | Regression safety net |
| Quick Guess ML Agent | 3 | `ml_score` population — explains §4-G (0% coverage on closed) |
| Alpha Engine - Weekly Validation Suite | 2 | `strat_fwd_*` refresh; stale forward stats |
| Walk-Forward Backtest (Weekly) | 1 | Paper-to-live gate inputs |

**Highest-leverage:** Alpha Engine Dynamic Runner failing 41x correlates directly with the blocklist-leak finding in §2 — fixing this one workflow likely flips aggregate PF from 0.72 to 1.10 without any new code in the engine.

---

## 7. Ranked top-5 additional fixes (impact vs effort)

| Rank | Fix | Impact | Effort | Why |
|---:|---|---|---|---|
| 1 | **Repair `ALPHA ENGINE - Dynamic Runner` workflow (41 failures)** and audit why `copy_hl_lb_None` is still emitted by `copy_trader_intel` + `alpha_engine` (§2 leakage) | **Huge** — likely flips product from PF 0.72 to 1.10 | Low–Medium | Blocklist exists; just not enforced. Investigate before expanding `BLOCKED_SOURCE_SYSTEMS` per repo rule |
| 2 | **Add 6 fields to `_CLOSED_PICK_KEEP_FIELDS`** (ml_score, hf_conviction_tier, va_cohort_id, sym_track_wr, paper_trade, entry_time) | High | Trivial | 1-line change in `audit_trail/dashboard_generator.py`; unblocks parent audit rec #2 and future Track%/VA audits |
| 3 | **Promote `st_obv_support_divergence` to RETIRED** (currently PAPER) and **add `(copy_trader_intel, copy_hl_lb_None)` + `(alpha_engine, copy_hl_lb_None)` to `_RETIRED_SYSTEM_STRATEGY_PAIRS`** | High | Low | Follows `STRATEGY_INVESTIGATION_BEFORE_KILL.md`; PF 0.18 on n=86 is proven-negative-EV |
| 4 | **Ingest-side rejection of anonymous picks**: `strategy in ("", "unknown")` OR `strategy == source_system` (self-named). 211 such picks / 6% of ledger | Medium | Low | In `feed_hygiene.is_valid_active_pick`; also backfill existing rows with proper strategy name from source |
| 5 | **Backfill `entry_time` on active picks** from `timestamp` when null (14/37 missing) so staleness detection works; and **FOREX pnl unit contract test** at ingest (parent audit already flagged but no test exists yet) | Medium | Low | Unblocks dead-pick gating and fixes silent stat corruption |

---

*Research only — no files committed. Generated 2026-04-20 from dashboard_data.json.*
