# 06 — OVERALL + STATISTICAL Consolidation (5 peer agents)

**Consolidated:** 2026-11-14 · **Sources:** finpredict (v1) · finpredict-v2 · finpredict-v3 · finpredict-v4 · ML childlike-airport
**Role:** truth/statistics/honesty/survivorship/multiple-testing/metrics-liveness/summary_picks/money_ready/data-contract layer of the master plan.
**Rule:** every number below is attributed to its peer; nothing is re-derived or invented.

---

## 1. Consensus verdict + key numbers

**Verdict: `FAIL` — not money-ready, not statistically sound, and not demonstrably profitable.** All five peers agree. The published performance is a **multiple-testing + survivorship + resolver-artifact + stale-price composite**, not a genuine edge.

### Headline (v1/v2/v3/v4 — agreed four-way)

| Metric | Value |
|---|---:|
| Overall win rate | **41.8 %** |
| Profit factor | **0.94** |
| Sharpe (annual) | **−1.31** |
| Compounded equal-weight PnL | **−99 %** |
| Money-ready classes | **0 / 9** |

### Fleet truth (v2 — canonical policy-clean, net-of-slippage ledger)

| Metric | Value |
|---|---:|
| n (deduped, policy-clean) | **22,941** |
| Win rate | **42.21 %** |
| Profit factor | **0.2657** |
| WR z vs 50 % | **−23.60** (p ≈ 3.6×10⁻¹²³) |
| Best honest class (money_ready intrabar) | CRYPTO WR 35.87 %, PF 0.9196, expectancy −0.0592, bootstrap CI entirely negative |

### Multiple-testing (v2, quantified)

- **N = 658** distinct strategies scored in live `pf_registry` (682 asset×strategy pairs; 2,218 strategy×symbol cells). Declared space ~361 families + 84 baby + 231 mutations ≈ 676 pre-genome — 658 is conservative.
- Expected false positives at α=0.05: **32.9**. Bonferroni z_crit = **3.788** (α_B = 7.599×10⁻⁵).
- **21 strategies clear Bonferroni — all 21 are the single-source 90–100 %-WR artifact cluster** (`single_source_pct = 1.00`, `top_source = file:mysql:at_pick_outcomes`, `is_single_source_artifact = True`). Correlated re-emissions violate the independence assumption → data artifact, not 21 edges.
- BH-FDR q=0.05 rejects for 22/76 (n≥30), again all in the same cluster.
- Per-class significance (Bonferroni |z|crit = 2.773, two-sided): **CRYPTO z=−22.69, FOREX z=−6.02, EQUITY z=−3.03 survive — significantly BELOW 50 %.** No class survives with a *positive* edge (ETF PF 1.84 is n=15).
- **PBO = 0.0 is degenerate** (T=20 × S=80 matrix, `ORDER BY strategy`, no time alignment; contradicts 69/80 OVERFIT_LIKELY). **DSR uses n_trials=80 instead of 658** (under-corrects). **Reality Check never ran** (`arch` missing).

### Survivorship

- **63 % never resolve**: 90,523 / 143,156 `trading_picks` rows are open.
- **Only 49 % of closed picks pass integrity gates**: 16,126 → **7,914 valid** (`integrity_excluded` 7,567 + `auto_expired_excluded` 8,888).
- **22,947 constant-PnL ghost rows** (top cohort DOGEUSDT LONG pnl 1.3226, n=3,569, distinct_entries=1).
- Headline stats are computed on survivors, so the true population is worse than displayed.

### Metrics liveness (v2)

- Core payload fresh (1.63 h) but the metric columns are structurally empty for the active universe: **EDGE 0/20, Track 2/20, FWD WR 2/20, FWD N 20/20 (90 % zero)**, `sym_track_total` 0/20.
- 19/20 curated picks `pnl_pct == 0.0` (7 exact `current == entry`); 3,584/4,148 raw rows null `current_price`.

### summary_picks (impossible math)

- **7 classes report WR > 100 %** (INDEX 1,141.2 %, FUTURES 363.9 %, COMMODITY 240.2 %, ETF 232.9 %, EQUITY 162.4 %, FOREX 147.0 %, BOND 127.8 %); 9 classes have `wins+losses > resolved`. Root cause: `tools/sync_summary_picks_json.py:63-65` counts wins/losses over all PnL rows while `resolved` counts terminal statuses, then divides at `:161`. Not in the trust hierarchy.

### money_ready (independent surfaces agree)

- `money_ready_verdict`: **0/9 money-ready**. `audit_surface_truth`: "0/9 classes money-ready on policy-clean closed picks." `forward_track`: 0/8 sleeves promotion-ready. MA walk-forward: **0 golden**. `anti_overfit_audit`: 69/80 OVERFIT_LIKELY.

---

## 2. Unique per-peer contributions

| Peer | Unique contribution |
|---|---|
| **v1 (finpredict)** | Backbone merged doc; honesty-metrics quick wins (QW-1 binomial CI + excluded counts, QW-2 `edge_ratio`, QW-3 `INSUFFICIENT` at `forward_trades==0`, QW-5 outlier clamp+flag, QW-7 visibility-floor exposure); push of its own audit to main. |
| **v2 (finpredict-v2)** | Most precise root causes with `file:line` (P0-1..P0-9); statistical math (N=658, Bonferroni/Šidák, E[FP]=32.9); survivorship row accounting (34,540→22,941); `summary_picks` denominator bug; **DATA_CONTRACT** (strict JSON, quote provenance, honesty rules H1/H2, metric population envelope, validation ladder); 4-reviewer peer synthesis + veto list. |
| **v3 (finpredict-v3)** | Only **runnable artifact**: `tools/pi_data_hygiene.py` + tests (exit 1 on findings, CI-gateable); payload-lag banner; dual-cohort (RAW vs gate-passing) disclosure; auto-expired tagged-cohort preservation. |
| **v4 (finpredict-v4)** | Raw-DB truth vs dashboard inflation (CRYPTO dashboard PF 1.801 vs raw 0.371 ≈ 5×; Smart-Picks PF 9.69 = 91.7 % single source with 3 closed rows; EQUITY filter inverts 0.70 vs 5.56); `at_signal_outcomes` intrabar truth **254 d stale**; 4,220 TIME_EXIT limbo (6.2 % resolved); Alpha Engine dead (9 cancelled + 1 failure); 8-gate "minimum viable evidence" bar; honest reality-check (5–15 %). |
| **ML (childlike-airport)** | SQLite `live_picks.db` 128/129 picks 172 d stale; 8 PnL sign contradictions + 15 magnitude mismatches; `audit_trail.db` 9 tables empty; `consensus_active_picks.json` empty; **ML code is mathematically sound — the inverted-confidence finding is a *data* bug, not a code bug**; three divergent data stores (SQLite/MySQL/JSON) disagree. |

---

## 3. Consolidated fixes (adopt for master plan)

### 3.1 Honesty metrics + CI gate
- Emit `win_rate_ci_low/high` + `excluded_pct` beside WR (Wilson helper already exists) and render `n / excluded / CI` in the UI (v1 QW-1).
- Dual-cohort disclosure: publish RAW and GATE-PASSING headline counts together (v3 #4).
- Gate the hygiene guardian in CI: run `tools/pi_data_hygiene.py` as a pre-publish step in `audit-dashboard.yml`, fail the job on findings (v3 #1 — only runnable deliverable).

### 3.2 `edge_ratio`
- Re-emit `edge_ratio` into `summary` (value already computed at `tools/hyro_pick_performance_validator.py:549`) or delete the orphaned hyrotrader column (v1 QW-2).

### 3.3 `INSUFFICIENT` labels
- Emit `INSUFFICIENT`/`null` when `forward_trades == 0` (and `n<30` per contract §7); render a label instead of a blank/misleading 0 % (v1 QW-3; contract "display: INSUFFICIENT").
- Fix the vacuous PASS bug: `active_count==0 or resolved_n<30 → INSUFFICIENT_DATA` / `NOT_BUILT` (BOND renders green PASS with 0 picks — v2).

### 3.4 Outlier clamp / flag surfacing
- Add `outlier_clamped_count` to summary + flagged-rows list; the clamp+flag machinery already exists (`audit_trail/pnl_ingest_sanity.py`, `universal_pick_resolver.py:1470`) but is invisible (v1 QW-5).

### 3.5 UNQUOTED contract (never fabricate 0.00 %)
- Emit `quote_status: UNQUOTED` + `pnl_pct: null` when no quote was observed this build; never `pnl_pct == 0.0` as a substitute (v2 P0-5, contract honesty rules H1/H2). UI renders a grey `UNQUOTED` badge.
- v3 #3: when both Binance and yfinance fail, set `current_price=None` + a `price_freshness` flag instead of falling back to entry; relabel the banner as *signal* age and co-display *price* age.

### 3.6 Dedup + prune + CI assertion
- Reuse the existing registry key (don't invent a second one) and dedup `active_raw` before publish; prune EXPIRED rows >30 d into an append-only `expired_archive/YYYY-MM.jsonl`; CI: `unique(ids)==len(rows)`, EXPIRED share ≤5 %, no `(symbol,strategy,direction)` group with >5 identical-PnL rows (v2 P0-8).

### 3.7 Data contract (v2 DATA_CONTRACT.md — normative)
- Strict JSON (`allow_nan=False`; no NaN/Infinity — currently crashes `money_ready_verdict`/`strategy_ic_analysis`).
- `unknown ≠ zero`; provenance on every payload; ISO-8601 UTC instants with `entry_at_precision: DATE` for date-only rows.
- Quote provenance: `quote_status`/`quote_at`/`quote_source`/`quote_age_minutes`.
- PnL status enum `REALIZED/UNREALIZED/UNQUOTED/VOID`; `pnl_status==UNQUOTED ⇒ pnl_pct is null`.
- Metric population envelope (n vs n_emitted vs coverage_pct; `INSUFFICIENT` at n<30; `SINGLE_SOURCE_ARTIFACT` at single_source_pct≥0.95).
- `summary_picks` single terminal-status population (`wins+losses+flat == resolved`).
- Sidecar freshness manifest (`generated_at`, `max_age_hours`, `stale_policy`); `hyrotrader_picks.json` must gain a timestamp or be marked `static: true`.
- Three-release migration (additive → normalize → enforce).

### 3.8 CI unblock (root-cause fixes, v2)
- P0-1: guard forex direction bucket (`KeyError: 'LONG'`, `alpha_engine/scanner.py:2942` — 93 failed runs/24 h).
- P0-3: fix Python 3.14 masquerade (`update-environment: false` in 197 workflows makes `pandas==2.1.4` source-build against system 3.14).
- P0-4: space audit-dashboard cron to ≥ p95 runtime (61/168 cancels in 7 d).

### 3.9 Security (v2 P0-9)
- Rotate hardcoded Google API keys (`STOCKSUNIFY/…/stock-api-keys.ts` ×2, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js`); add `dbpasses.txt`/`*dbpasses*` to `.gitignore`.

---

## 4. Conflicts (must be settled before implementation)

1. **quote-status enum — 2-value vs 5-value.**
   - v2 `DATA_CONTRACT.md §2.2`: `quote_status ∈ {QUOTED, UNQUOTED}` (+ `quote_source` carries the origin).
   - v2 `REVIEW_SYNTHESIS.md` (unified fix contract): `quote_status ∈ {LIVE, LAST_CLOSE, STALE, UNQUOTED, PLACEHOLDER}`.
   - *Resolution needed:* pick one; recommend the contract's 2-value `quote_status` plus a separate `quote_freshness` band (avoids re-splitting H1/H2 honesty logic).

2. **pnl null vs label for unmeasurable outcomes.**
   - v2/v3 (honesty): `pnl_pct = null` + `pnl_status = UNQUOTED/VOID` (never 0.0).
   - v4 `MF-4` (destructive SQL, **vetoed**): `UPDATE … SET status='LOST', pnl_pct=0.0` for TIME_EXIT limbo; `QW-1` force `EXPIRED→LOST`.
   - *Resolution:* adopt null/UNQUOTED/VOID; **reject** v4's mass 0.0 rewrite and the `EXPIRED→LOST` relabel (both on the v2 veto list). Represent "never produced a measurable outcome" as VOID, not LOST.

3. **Dedup key — three variants.**
   - v2 `DATA_CONTRACT §6`: `(strategy, symbol, direction, trade_date, round(entry_price, 4))`.
   - v2 `REVIEW_SYNTHESIS`: ID key for exact dups + economic key `(symbol, strategy, direction, entry_time, entry_price)`.
   - `tools/build_pf_registry.py:818-835` (existing): `(strategy, symbol, direction, trade_date, round(entry_price, 2))`.
   - *Resolution:* keep the existing registry key as the canonical (don't fork it); decide `entry_time` vs `trade_date` and `2dp` vs `4dp` once. Recommend: `trade_date` + 4dp to match the contract, applied in both `build_pf_registry` and `dashboard_generator`.

4. **Headline PF magnitude — 0.94 vs 0.2657.**
   - v1/v3/v4 headline PF **0.94** (on 7,914 gate-passing survivors).
   - v2 canonical policy-clean PF **0.2657** (on 22,941, net-of-slippage).
   - *Resolution:* not a real disagreement — different populations (survivor subset vs full policy-clean). Publish **both with labels**; the sign/direction is identical (both negative).

5. **v4 "empty dashboard" claim.**
   - v4 `INDEX.md`/`dashboard_data_report.md`: "0 active picks, 26-day-old dashboard" — based on the **stale repo copy** of `dashboard_data.json`.
   - v1/v2/v3 (live HTTP): 20 curated / 4,148 raw / 3,500 recent-closed, generated 14:30Z.
   - *Resolution:* the live site has 20 active picks; do not propagate "empty dashboard." v4 is internally contradictory (its own deep-dives say 20 active / live 14:30Z).

---

## 5. UNVERIFIED (across all peers)

- Distribution of PnL among the **90,523 unresolved** `trading_picks` rows — magnitude of open-pick survivorship bias cannot be computed.
- Fraction of the **24,172 `at_pick_outcomes`** rows resolved *before* the `RESOLVER_ENTRY_ANCHORED` look-ahead fix landed (most plausible mechanism for the 90–100 %-WR cluster).
- Whether every aggregator honours `_wr_excluded`/`_wr_excluded_reason` for `FORCE_CLOSED_TOXIC` rows.
- **Workflow failure root causes** for mid-retry runs (Sports smoke / CI Tests / Market Beating) — per-step logs admin-only.
- **Kalshi / prediction-market snapshot staleness** — code real, feeds dead, output path unresolved.
- Exact full-sample **EQUITY PF** — three aggregators disagree (8.86 / positive-sum / 0.70).
- `summary_picks` provenance/consumers — no `fetch()` reference found; whether any tab consumes it beyond diagnostics.
- Fair-market vs arbitrary `FORCE_CLOSED`/`TIME_EXIT` exits.
- **234 closed FUTURES rows** in JSON feeds (ML peer) — not independently reproduced.
- `chat_transcript_2026-11-14.md` — not on disk (Windows host).
- deepAI/inspect-wt and hilarious-seer peer archives — **unreviewable** from this host (branches not pushed to origin).

---

## 6. P0 order (execution sequence)

Adopt **v2 `P0_QUICK_WINS.md` as the execution order** (v2 peer-review synthesis hand-off). Ranked by impact ÷ risk:

| Step | Fix | Peer | Effort |
|---|---|---|---|
| **1** | P0-1 Guard forex direction bucket (`KeyError: 'LONG'`) — unblocks 93 runs/24 h | v2 | 30 min |
| **2** | P0-3 Fix Python 3.14 masquerade (`update-environment: false`) | v2 | 2 h |
| **3** | P0-4 Space audit-dashboard cron to real runtime (stop cancel cascade) | v2 | 15 min |
| **4** | P0-2 `summary_picks` single population + clamp/assert | v2 | 2 h |
| **5** | P0-6 Populate `sym_track_*` from closed ledger (Track column) | v2 | 1 h |
| **6** | P0-5 `UNQUOTED` contract — never publish fake 0.00 % | v2 (+v3 #3) | 4 h |
| **7** | P0-7 Sidecar freshness manifest + hide-if-stale | v2 | 6 h |
| **8** | P0-8 Dedup key + prune + CI assertion | v2 | 8 h |
| **9** | P0-9 Rotate hardcoded API keys + `.gitignore` | v2 | 0.5 d |

**Sequencing:** CI unblock first (P0-1 → P0-4, no data consumers), then the one-generator-run stats fixes (P0-2/P0-6), then payload-contract fixes (P0-5/P0-7/P0-8), then security (P0-9) with the operator.

**Fold in as cross-cutting (non-sequenced, same PR as the relevant P0):** honesty metrics + binomial CI (v1 QW-1), `edge_ratio` (v1 QW-2), `INSUFFICIENT` labels (v1 QW-3), outlier clamp surfacing (v1 QW-5), CI hygiene guardian (v3 #1), data contract (v2 DATA_CONTRACT.md — additive Release A first).

**Do not apply (v2 peer-review veto list):** `DELETE` ghost rows · `UPDATE TIME_EXIT→LOST, pnl_pct=0.0` · `EXPIRED_FORCE` mass rewrite · invert the ML confidence gate · unblock FUTURES/COMMODITY without a real feed · add `MUTUAL_FUND` to canonical classes before an emitter exists · re-enable the audit-dashboard `push:` trigger. **Do not start Phase 3 (strategy kill/keep or real-money sizing) until Phase 0 truth fixes and Phase 1 data-consistency gates are green.**
