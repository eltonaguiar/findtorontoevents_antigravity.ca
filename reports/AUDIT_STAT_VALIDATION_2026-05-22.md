# /audit Dashboard — Stat-Validation Audit (2026-05-22)

**Scope:** independent validation of every headline stat on `findtorontoevents.ca/audit`,
triggered by operator skepticism of the tier/asset-class PnL cards. Method: 5-subagent
swarm + Grok skeptic pass, each finding reproduced against the source ledger
(`audit_dashboard/data/dashboard_data.json`).

**Bottom line:** the impressive numbers are not real returns. No asset class shows a
proven, leakage-free statistical edge. This is consistent with the existing
"Honest Status" banner on `/updates` (0/8 cohorts admissible, 2026-05-18).

---

## Part 1 — The tier / asset-class cards are NOT returns (P0)

The cards showing crypto All-Tiers **+692%**, B-Tier +448%, A-Tier +165%, EQUITY +292%,
FOREX +19% compute "Overall PnL" as a **naive arithmetic sum** of per-trade `pnl_pct`,
each clamped ±500%. They never compound.

- Crypto card loop: `audit_dashboard/template.html:6337-6345` — `totalPnl += capped`.
- Non-crypto card: same pattern at `template.html:5926-5934`.
- ~2806 crypto trades × ~0.25% avg ≈ 700% → matches the +692% card.
- The generator **already** computes the honest figure: `summary.total_pnl_pct_compounded_ew = 50.59`
  vs `total_pnl_pct_sum_raw = 2258.52`. The cards just never called it.

### Honest numbers (from `performance.asset_class_health`, post-resolver-v2)

| Class | Card "Overall PnL" | Honest `total_pnl_pct` | PF / WR / n |
|---|---|---|---|
| CRYPTO | +692% | **+23.4%** | PF 1.35 / WR 48.2% / n=1085 |
| EQUITY | +292% | **−0.08%** (negative — card sign is wrong) | PF 0.92 / WR 36.4% / n=55 |
| FOREX | +19% | **+0.09%** | PF 1.37 / WR 53.5% / n=155 |
| COMMODITY | — | +0.37% | PF 1.30 / WR 50.8% / n=61 |

System-wide compounded equal-weight return: **+50.6%**, not +692%.

### Other display flaws
- **Recency truncation:** cards aggregate a 3,500-row recent slice of 6,778 valid closed
  trades (`dashboard_generator.py:231 MAX_CLOSED_PICKS=3500`), silently dropping ~3,278
  older trades. Four different crypto trade-counts appear in one payload (2832 / 2806 /
  1085 / 10345).
- **Unrealized mixed into "realized":** the bold "Overall PnL" row added open-position
  mark-to-market (`overallPnl = totalPnl + unrealizedPnl`).
- **Mirror duplicates:** `headline_mirror_duplicates_removed: 885` are deduped from the
  headline only — per-card aggregation read the raw `recent_closed` array.

### Fix shipped (this session)
`template.html` — both card renderers now show a bold **"Compound Return (EW)"** as the
honest headline (via `compoundEwCappedPct`), and the old sum is relabeled
**"Σ Trade % (sum)"** with a tooltip stating it is not a return. Unrealized is shown as a
separate "Unrealized (open)" row, no longer folded into the headline. JS syntax verified
(`node --check`). Reaches production on the next `audit-dashboard.yml` run.

---

## Part 2 — Internal incoherence (P0/P1)

- **`by_asset_class` aggregates are internally inconsistent.** FUTURES claims `closed=214`
  but `wins+losses=2`; CRYPTO claims `closed=10345` but `wins+losses=6003`. The `closed`
  count and the wins/losses it is supposedly derived from disagree by 2–4×. Any card
  reading `by_asset_class` shows numbers that cannot be reconstructed from any trade list.
- **Resolver writer bug (confirmed).** `status` (WON/LOST) contradicts `pnl_pct` sign on
  20+ rows of `recent_closed`. DB-Health panel already flags this ("WON-vs-PnL
  contradiction YES"). Outcome resolver is effectively dead (resolving ~0 picks/hr).

---

## Part 3 — The three broken fundamentals

1. **DB-Health ghost rows — real DB corruption.** `tools/db_health_check.py:146`
   `check_ghost_rows()` finds 36,085 constant-`pnl_pct` rows live (11 cohorts), mostly
   `meta_strategy` MEMECOIN templates. The "655k" footnote is a **stale hardcoded string**
   (`dashboard_enhancements.js:665`), not live data — traces to
   `reports/wave0_census_final_2026-05-08.md`. Quarantine is **incomplete**: only 4 of ~5
   cohorts are in `BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES` (`quality_gates.py:2911`); the
   largest `meta_strategy` cohort (~1.6M rows) is explicitly deferred and **still pollutes
   WR/PF/MDD aggregates**. P1 sweep open.
2. **Top-5 Rank Backtest (EQUITY) empty — silent CI failure.**
   `audit_dashboard/data/top_n_rank_backtest.json` carries
   `error: "pymysql not importable in this environment"`, generated 2026-05-21T18:02.
   `audit-dashboard.yml:286` *does* run `pip install pymysql` — but as
   `pip install pymysql -q 2>/dev/null || true`, which **silently swallows install
   failure**. The panel is empty because pymysql failed to install and the error was
   suppressed, not because there are no EQUITY picks. Recommended fix: surface the install
   failure (drop `2>/dev/null || true`) or install pymysql once in a job-level setup step.
3. **ML-Gatekeeper A/B sleeve — never-wired feature.** The OLD sleeve has data
   (`ml_gatekeeper/data/active_picks.json`, 50 picks); the NEW sleeve file
   (`active_picks_ab_new.json`) was never produced by any pipeline — the code itself
   documents it as a "permanent 404" (`dashboard_enhancements.js:452-455`). `ab_summary.json`
   shows `n_ab_tagged: 0`. Panel is half-empty by design. Needs a plain-language ELI5
   explainer (current copy is dense jargon: "hash-bucket split md5 mod 2, one-sided
   z-test p<0.10, WR delta ≥2pp").

---

## Part 4 — Winner-pattern hunt: the "edge" is a LEAKAGE ARTIFACT (P0 — read this)

A tag-correlation scan of 3,452 resolved picks initially found a strong signal:
`sym_track_wr` (symbol track-record WR) top-quartile picks realized **76.5% WR** vs
**16.8%** bottom-quartile (60-pt spread); `trust_tier=PROVEN` 62.6% vs ~44%.

**This is not a tradeable edge. It is data leakage.** Verified:

- `sym_track_wr` is built by `_build_strategy_symbol_track_stats`
  (`dashboard_generator.py:5425-5473`) over `resolved_closed` — **all** closed picks,
  **no time filter** — then stamped onto every pick (`dashboard_generator.py:15563-15708`).
  Each pick is tagged with the all-time WR of its `(strategy, symbol)` bucket, a window
  that **includes that very pick and every pick after it**. Not point-in-time.
- **Smoking gun:** for 81 of 139 `(strategy,symbol)` groups (n≥5), the stamped
  `sym_track_wr` is numerically identical (≤0.6pp) to that group's *own* realized WR;
  105/139 within 5pp. "High sym_track_wr predicts wins" reduces to "buckets that won a
  lot, won a lot." Tautological.
- Same leakage in `trust_score`/`trust_tier` (`stamp_pick_quality.py:181-206,393` — all-time
  per-strategy aggregate, no time cutoff) and `strat_fwd_wr`. `at_issue_trust_tier` is
  largely backfilled from the live leaky value (`dashboard_generator.py:312-326`), so it
  is not an independent pre-trade snapshot.
- The spread is also driven by a few mega-buckets (`unknown/ONDOUSDT` = 233 picks), not a
  stable cross-section — `unknown` is a known PF-0.35 drag per CLAUDE.md.

### What IS genuinely true (low-information but honest)
- "STRONG" star / "3+ consensus" badge: **anti-predictive** — STRONG-consensus picks
  realize **40.5% WR, below the 46% baseline**. The star tells you nothing good.
- Advertised "FWD WR 80%": picks with `forward_wr≥80` realize only **~63-65%** — a
  persistent ~20-29pp gap. The forward number is inflated.
- LONG beats SHORT (~9pp); `grade=F` → 20.6%; `regime_bonus=−30` → 37.6%. These are
  descriptive, partially leaky, and not validated walk-forward.

### To find a REAL edge (next step — thread lightly)
Re-derive `sym_track_wr` **point-in-time**: for each pick, compute the `(strategy,symbol)`
WR using only picks with `timestamp` strictly *before* that pick. Re-run the quartile
analysis. If the 60-pt spread survives a true walk-forward recomputation, it is real;
until then it is a mirage. Cutoff would go in `dashboard_generator.py:5425` and
`stamp_pick_quality.py:181`. Any edge claim must additionally clear
`edge_stability_harness.is_admissible()` on the canonical deduped net-of-slippage ledger
(per the M-107 / pre-registration rule) before it is documented as "proven".

### RESULT — point-in-time recompute run (2026-05-22)

`_stamp_pit_sym_track` was run over the live `recent_closed` ledger and the leakage +
quartile analysis re-run on both fields:

| Metric | Leakage rate | Q1 → Q4 realized WR | Q4−Q1 spread |
|---|---|---|---|
| `sym_track_wr` (all-time, leaky) | **0.511** (67/131) | 20.5% → 76.8% | **56.3 pts** |
| `sym_track_wr_pit` (point-in-time) | **0.100** (13/130) | 36.0% → 61.5% | **25.5 pts** |

- **Leakage confirmed & removed:** the point-in-time metric's leakage rate falls from
  0.51 to 0.10 — below the 0.20 health threshold. `sym_track_wr_pit` is leakage-free.
- **~31 of the 56 "edge" points were pure leakage.** A **~25-point residual signal
  survives** — point-in-time symbol track record does carry forward information
  (poor-prior symbols realize ~36% WR, strong-prior ~61.5%).
- **But it is NOT a clean ranker:** Q2 (47.3%) ≈ Q3 (46.1%) — only the Q1/Q4 extremes
  separate. It is an "avoid bad-track symbols / lean into strong-track" effect, not a
  smooth gradient.
- **Verdict:** the advertised "76.5% monotonic edge" was a mirage; the real residual is
  weaker, non-monotonic, and not yet validated after costs. It is worth a proper
  walk-forward + `edge_stability_harness` pass before any "edge" claim — but it is not
  nothing. (Computed over the 3,500-row `recent_closed` window as its own history; the
  full-ledger pipeline value will be marginally stronger.)

---

## Fixes shipped vs recommended

| Item | Status |
|---|---|
| Card headline → compounded "Compound Return (EW)", sum relabeled "Σ Trade %" | **Shipped** (`template.html`) |
| Unrealized split out of the "realized" headline | **Shipped** |
| `updates/index.html` progress card | **Shipped + deployed** |
| Metric regression test suite (pytest + node) | **Shipped** — `tests/test_audit_metric_invariants.py`, `test_card_metrics.js`, `test_metric_leakage_guard.py` |
| `pymysql` CI silent-failure (Top-5 backtest) | **Shipped** — `audit-dashboard.yml:286` now emits a `::warning` instead of `2>/dev/null \|\| true` |
| Ghost-row "655k" stale footnote | **Shipped** — `dashboard_enhancements.js` now reads live `ghost_rows.total_ghost_rows` |
| ML-Gatekeeper ELI5 copy | **Shipped** — plain-English explainer added, technical detail collapsed |
| `by_asset_class` wins/losses ≠ closed coherence bug | **Shipped** — `dashboard_generator.py` now counts `closed` only for valid resolved picks + adds `flat`; `closed == wins+losses+flat`. Live until next pipeline regen of `dashboard_data.json`. |
| Point-in-time recompute of `sym_track_wr` | **Shipped** — `_stamp_pit_sym_track` in `dashboard_generator.py` stamps a leakage-free `sym_track_wr_pit` / `sym_track_total_pit` *shadow* column (strictly-earlier history only); leaky `sym_track_wr` left intact for comparison. Verified leakage-free + regression-tested. |
| `meta_strategy` ghost cohort quarantine | **Verified, pending sign-off** — see below |

### `meta_strategy` ghost cohort — DB verification (2026-05-22)
A live DB inspection (`ejaguiar1_stocks.bt_backtest_trades`) confirmed the cohort:
- **1,953,574 rows** total — CRYPTO 1,842,087 + MEMECOIN 111,487. Source:
  `meta_strategy/data/meta_strategy.db::permutation_signals`.
- `pnl_pct` is **not exactly constant** (130 distinct values) but **87% is a binary
  synthetic template**: `−3.0` (971,678 rows) and `+5.0` (728,257 rows). Within each,
  only ~450–646 distinct entry prices across ~90–102 symbols → ~1,500 duplicate rows per
  entry price. Classic ghost signature.
- `meta_strategy` is **historical backtest noise** — it is in `_GHOST_SYSTEMS` (marked
  "FILE MISSING"), has no live pick file, and feeds nothing in the production pick path.
- The dashboard's own `check_ghost_rows` **never saw the 1.84M CRYPTO slice** — its
  CRYPTO scan dies on shared-host `/tmp` exhaustion (`db_health.json` shows the lost
  connection), so only the 36K MEMECOIN slice is currently reported.

**Mandatory diff result — quarantine NOT needed (premise disproved 2026-05-22):**
A 2-engine swarm chose "Option A: class-scoped block in `quality_gates.py`". Per the
swarm's own "diff before ship" rule, the with/without check was run first — and it
disproved the premise:
- `meta_strategy` appears **0 times** in the published `dashboard_data.json`.
- `asset_class_health.CRYPTO.n` is 1085 and `by_asset_class.CRYPTO.closed` is 10,345 —
  nowhere near the 1.84M-row cohort; the aggregates demonstrably never ingested it.
- `meta_strategy` is already in `dashboard_generator.py::_GHOST_SYSTEMS` (line 4314) and
  is skipped at three collection callsites (8562 / 10322 / 10359). The dashboard
  generator does **not** read `bt_backtest_trades` at all.

**Conclusion:** the ghost cohort does NOT pollute the dashboard's performance
aggregates — it is already excluded. A `quality_gates.py` block (Option A) would change
nothing on `/audit` and was therefore NOT shipped — the mandatory diff correctly
prevented a no-op kill in the gate path. The cohort only inflates the raw
`bt_backtest_trades` table and the `db_health` ghost-row *metric*. Residual, separate
(non-dashboard-aggregate) work:
- **(1) Shipped** — `db_health_check.py::check_ghost_rows` now retries down a sample
  ladder (`500K → 150K → 50K`) per asset class. The CRYPTO scan previously blew the
  shared-host `/tmp` budget on the `GROUP BY` + `COUNT(DISTINCT)` temp table at 500K and
  contributed 0; it now falls back to a smaller sample so the cohort is still counted
  (ghost cohorts are dense enough to detect at 50K). The effective sample per class is
  reported in `per_class_sample`.
- **(2) Open** — DB hygiene: the offline `meta_strategy` permutation backtester should
  stop dumping ~1.95M synthetic rows into the shared `bt_backtest_trades` table. This is
  an operational cleanup on the `meta_strategy` subsystem, not a dashboard code change.

Neither affects `/audit` headline numbers.

### Swarm-guided next steps (deferred items)
A 2-engine swarm review (DeepSeek + xAI) advised the two remaining items NOT be done as quick patches:
- **Ghost quarantine:** confirm `pnl_pct` is exactly constant across the `meta_strategy` cohort and that no live strategy still writes that template, then diff WR/PF aggregates with vs without the block before committing.
- **Leakage recompute:** add `sym_track_wr_pit` / `trust_score_pit` as *shadow* columns computed point-in-time (only picks strictly earlier than each pick's timestamp), compare distributions against the leaky originals for one cycle, then cut over. A silent in-place change would invalidate prior research notes and surprise stakeholders when the apparent edge vanishes. `tests/test_metric_leakage_guard.py` already contains a reference `point_in_time_sym_wr()` implementation.
Also recommended: a CI data-quality gate that fails if `closed != wins+losses+flat` or if any `pnl_pct` series is perfectly flat for >N rows.

**Refs:** `audit_dashboard/data/dashboard_data.json`, `audit_dashboard/template.html`,
`audit_trail/dashboard_generator.py`, `audit_trail/stamp_pick_quality.py`,
`audit_trail/quality_gates.py`, `tools/top_n_rank_backtest.py`, `tools/db_health_check.py`.
