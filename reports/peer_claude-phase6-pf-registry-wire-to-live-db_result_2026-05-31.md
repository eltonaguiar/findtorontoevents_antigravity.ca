# Design — Wire `pf_registry.json` to live `trading_picks` DB

**Date:** 2026-05-31
**Author:** peer_claude phase6
**Scope:** docs-only — investigation + design + risk register. **No code change.**
**Phase 4 Layer 2 finding:** registry's `n` for live-DB strategies is 0-1
vs 314-1969 in `ejaguiar1_stocks.trading_picks` (≈100% drift, not 20-80%).

---

## 1. Generator + source-list config (found)

- **Generator:** `tools/build_pf_registry.py` (1066 lines).
- **JSON source list (canonical):** imported at
  `tools/build_pf_registry.py:143-166` from
  `audit_trail/dashboard_generator.py:3589` (`JSON_PICK_SOURCES`).
- **Static fallback:** `_FALLBACK_SOURCE_FILES` at `tools/build_pf_registry.py:136-140`
  (3 files: `alpha_engine/`, `battleground/` closed_picks ledgers).
- **Per-source ingestion loop:** `tools/build_pf_registry.py:560-619` reads each
  `*/data/closed_picks.json`, appends rows tagged with `_origin_file`.
- **DB loader already exists (opt-in, currently OFF):**
  `_load_mysql_rows()` at `tools/build_pf_registry.py:392-460`. Gated by
  env var `PF_REGISTRY_INCLUDE_DB=1` (default off). Window controlled by
  `PF_REGISTRY_DB_DAYS` (default 90). Bridges schema:
  `category → asset_class`, `_origin_file = "mysql:trading_picks:Nd"`.
- **Tournament DB loader (already ON in CI):** `_load_tournament_picks_rows()`
  at `tools/build_pf_registry.py:463+`, gated by
  `PF_REGISTRY_INCLUDE_TOURNAMENT_DB=1` — flipped on at
  `.github/workflows/audit-dashboard.yml:504`.
- **Production registry build (CI):** `.github/workflows/audit-dashboard.yml:513`
  runs `python tools/build_pf_registry.py` hourly, and **does not export
  `PF_REGISTRY_INCLUDE_DB`** (verified via grep). So the live registry
  never sees `trading_picks` for the 5 strategies below.

## 2. Quantified drift (5 strategies, 2026-05-31 17:00Z snapshot)

| Strategy | Registry n (`by_asset_class_strategy`) | Live DB closed n | Last 90d | Drift |
|---|---:|---:|---:|---:|
| `luxalgo_confluence` | 0 | 1969 | 1969 | **+100%** |
| `forex_rsi2_mean_reversion` | 1 (FOREX) | 664 | 664 | **+99.8%** |
| `futures_momentum` | 0 | 599 | 599 | **+100%** |
| `myfxbook_retail_contrarian` | 0 | 364 | 364 | **+100%** |
| `ig_contrarian_sentiment` | 0 | 314 | 314 | **+100%** |

Total invisible-to-registry closed picks across just these 5 strategies:
**3,909**. All inside the default 90d DB window, so the cap is not the
bottleneck — the env-var gate is.

The earlier Phase 4 "20-80% drift" estimate understates the impact for
strategies that emit *exclusively* to `trading_picks` (no JSON-mirror
ledger). For strategies that double-emit (some `alpha_engine` paper picks
write to both `paper_trading/data/closed_picks.json` AND `trading_picks`),
drift is the 20-80% Phase 4 measured.

## 3. Proposed fix

### Option A (recommended) — flip the existing gate ON in CI

**Diff:** 1 line in `.github/workflows/audit-dashboard.yml`, in the
`env:` block at `:485-504` (right next to the existing
`PF_REGISTRY_INCLUDE_TOURNAMENT_DB: '1'` flag at line 504):

```yaml
          # 2026-05-31: wire trading_picks DB cohort into pf_registry. Mirror
          # of the PF_REGISTRY_INCLUDE_TOURNAMENT_DB flip at :504. Default-off
          # design preserved — set to '0' or delete to revert. Days window
          # honored by PF_REGISTRY_DB_DAYS (default 90).
          PF_REGISTRY_INCLUDE_DB: '1'
```

No source code touched. The DB loader is already wired
(`tools/build_pf_registry.py:620-639`), already bridges
`category→asset_class`, already tags `_origin_file=mysql:trading_picks:Nd`,
and already feeds the existing dedup / flicker / policy-clean pipeline.

### Option B (deferred) — make trading_picks an additional canonical source

Change the default at `tools/build_pf_registry.py:620` from
`if os.environ.get("PF_REGISTRY_INCLUDE_DB") == "1":` to default-ON
(only opt-out via `PF_REGISTRY_INCLUDE_DB=0`). Rejected for this PR
because it changes default behavior across all consumers without a
shadow-mode comparison window first.

## 4. Risk register

The DB loader feeds the existing dedup / classify / policy pipeline, so
risks are downstream-numeric, not structural:

1. **Asset-class double-count.** If a strategy emits the *same closed
   pick* both to `paper_trading/data/closed_picks.json` AND to
   `trading_picks` (with float-jitter on `entry_price`), the existing
   dedup key
   `(strategy, symbol, direction, entry_date, round(entry_price, 2))`
   should collapse them. **Validation gate:** before flip, dry-run with
   `PF_REGISTRY_INCLUDE_DB=1` locally and diff `counts.dedup_collapsed`
   vs the published registry. Acceptance: collapse ratio should jump,
   not fall.
2. **PF numbers shift for the 5 high-volume strategies above.** Every
   downstream consumer of `pf_registry.json` will see new `n`/`pf`/`wr`
   on next refresh:
   - `audit_trail/dashboard_generator.py` — asset_class_health verdict
   - `tools/strategy_tier_tracker.py` — tier table
   - `tools/reconcile_pf_registry.py` — vs /audit reconciliation
   - `tools/ci_gate_money_ready_vs_registry.py` — CI gate
   - `tools/build_top10_strategies_per_class.py` — top-10 promotion list
   - `alpha_engine/emitter_whitelist.py` — emitter whitelist gate
   - `alpha_engine/strategies/crypto_paper_pilot.py` — pilot reads PF
   - `audit_dashboard/incidents.html` — incident banner cites PF
   - `tools/edge_stability_harness.py` — stability checks
   - `tools/strategy_density_analysis.py` — density audit
   These all already read from `pf_registry.json`; no API change. They
   will simply see corrected numbers (registry → live truth).
3. **Concentration flags may flip.** `_compute_source_concentration`
   at `:105-126` counts `source_system` per strategy. When
   `trading_picks` rows arrive, `top_source` may change from e.g.
   `battleground` to `paper_trading` (or `unknown` if `source_system`
   is null in the DB), and `is_single_source_artifact` may flip.
   **Pre-flip check:** SQL-audit how many `trading_picks` rows have
   `source_system IS NULL` — null rows fall to the `_origin_file`
   fallback which would tag them `file:trading_picks` and create a new
   pseudo-source. If null-count is high, recommend a `source_system`
   backfill PR before flipping.
4. **CI gate `ci_gate_money_ready_vs_registry.py` may go red on
   first run.** The gate compares `money_ready_verdict.json` to
   `pf_registry.json`. If both refresh in the same CI job (audit-dashboard.yml
   runs `money_ready_snapshot.py` BEFORE `build_pf_registry.py` at
   `:509,513`), the verdict was computed from the OLD JSON-only registry
   while the new registry has DB rows → gate fails on the same run that
   shipped the fix. **Mitigation:** flip in a maintenance window where
   the next 2 hourly runs are observed, OR re-order so
   `money_ready_snapshot.py` runs AFTER `build_pf_registry.py` (separate
   PR, out of scope here).
5. **`PF_REGISTRY_DB_DAYS=90` default silently drops historical picks.**
   Not a regression for the 5 strategies measured (all closed picks are
   inside 90d), but `luxalgo_confluence` is a strategy that has been
   running >90d in other periods. Consider raising to 365 in a
   follow-up after the 90d default proves stable.
6. **DB unavailability fails open.** `_load_mysql_rows()` already returns
   `(rows=[], meta={error: ...})` on connect/fetch failure (`:428-442`),
   so a DB outage falls back to JSON-only registry without crashing the
   build. This is the desired behavior — registry stays buildable from
   the dashboard cache during MySQL maintenance.

## 5. Acceptance criteria for the eventual code PR (Option A)

- [ ] One-line `.yml` env var added at `.github/workflows/audit-dashboard.yml`
      near line 504.
- [ ] Local dry-run with `PF_REGISTRY_INCLUDE_DB=1 python tools/build_pf_registry.py`
      shows nonzero `n` for the 5 strategies above.
- [ ] `reconcile_pf_registry.py` run against the new registry exits 0
      (asset_class_health and registry stay within reconcile tolerance).
- [ ] `audit_dashboard/data/pf_registry.json` `source_files` includes a
      `mysql://trading_picks?days=90` entry with `loaded > 0`.
- [ ] First post-flip CI run observed manually; if
      `ci_gate_money_ready_vs_registry.py` fails, re-run after the next
      `money_ready_snapshot.py` regenerates.

## 6. Out of scope for this PR

- Code change to flip the gate (Option A). That is a separate one-line
  workflow PR after this design is approved.
- Default-ON behavior (Option B).
- Schema-level fix to `trading_picks.source_system` null rows (separate
  data-quality PR).
- Raising `PF_REGISTRY_DB_DAYS` from 90 to 365.

## 7. Files referenced

- `tools/build_pf_registry.py:136-169` — source list resolution + fallback
- `tools/build_pf_registry.py:392-460` — `_load_mysql_rows()` DB loader
- `tools/build_pf_registry.py:560-619` — per-source JSON ingestion loop
- `tools/build_pf_registry.py:620-639` — opt-in DB merge block (the gate)
- `audit_trail/dashboard_generator.py:3589` — `JSON_PICK_SOURCES`
- `.github/workflows/audit-dashboard.yml:485-513` — production CI build
- `audit_dashboard/data/pf_registry.json` — published output (the
  artifact every downstream consumer reads)
