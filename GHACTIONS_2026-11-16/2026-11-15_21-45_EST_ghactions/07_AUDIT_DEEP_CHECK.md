# 07 — /audit Deep Check (boxes, JS errors, WIRED_IN feeds, silent fails)

**STAMP:** 2026-11-15_21-45_EST_ghactions · checks 04:01–04:08 UTC · three deep-dive sweeps +
live browser/endpoint probes. Companions: `05_FOLLOWUP_RESULTS.md`, `06_GHA_BEST_PRACTICES_APPROACH.md`.

## 1. Are the WIRED_IN additions feeding the dashboard?

| Item | Verdict | Live evidence |
|---|---|---|
| Prediction-market consensus (`prediction_market_consensus.py`) | **FEEDING** | 2 active rows `pmconsensus_BNBUSDT_*` (02:25Z), `systems[102]` active |
| Kalshi signals (`kalshi_signal_agent` via orchestrator) | **FEEDING** | 4 rows `pm_kalshi_signals_*` (02:25Z), `systems[99]` active |
| Polymarket wallet-copy (`polymarket_scraper`) | **FEEDING** | 2 rows `copy_pm_*` (02:25Z), `systems[101]` active |
| Polymarket whale tracker | FEEDING (thin) | 2 mirrored rows; system card `empty` |
| Polymarket momentum agent | **REGISTERED-NOT-FEEDING** | 0 rows — dies behind the `|| echo non-fatal` swallow at `audit-dashboard.yml:129` (the silent-fail class) |
| `alpha_engine` reverse-engineered PM signals (polymarket_signals.py / kalshi_signals.py) | **NOT-WIRED (registry gap)** | files deploy to site but are absent from `JSON_PICK_SOURCES` (name collision: registry maps "polymarket_signals" to the copy_trader file); `polymarket-signals.yml:83` `git add` silently no-ops on gitignored files |
| Theories/hypothesis trackers (build_tracker.py, repo_mine.py, tools/hypothesis/h0xx, portfolio_theories.py) | **NOT-WIRED** | outputs (`predictions_tracker.csv`, `reports/h0XX_*.json`, `theory_portfolios.json`) have zero consumers; they read /audit as input — dependency points the wrong way |
| wired_in_childlike shadow cards | **FEEDING (paper-only)** | 3 OPEN rows `wired_in_childlike::XLV/LLY/SHY`, `systems[127]`; static since 11-15 by design; excluded from headline per-class selection by `_PAPER_ONLY_SYSTEMS` |
| Intrabar truth / forward tracking | **FEEDING** | `intrabar_truth_by_class.json` fresh 02:58Z → `asset_class_health` sizing (34 payload strings); `forward_clock.js` renders (0 ledger trades — pre-registration guard working as designed) |

**Wiring needed (1 line each):** debug momentum agent behind its swallow · add 2 `JSON_PICK_SOURCES`
entries for the alpha_engine PM files (and `git add -f` or drop the commit pretense) · give each
hypothesis/theory tracker a sidecar + `dashboard_generator` consumer + template panel.

## 2. Broken / contradictory boxes — root causes (all verified)

| Box | Root cause | Truth | Fixed in this commit |
|---|---|---|---|
| Strategy IC Analysis "Failed to load" | **Producer never existed** (`pick-funnel-nightly.yml:73` documents it) + FTP orphan artifact carries bare `Infinity` → JS `r.json()` rejects | file exists (42KB) — parse-fail, not 404 | Card retired (`hidden`); dead deploy line dropped |
| Money Ready Verdict "No data" | Producer dumps `allow_nan=True` → 2× bare `NaN` in fresh (03:02Z) artifact → parse reject; **also silently degrades the intrabar sizing gate** (`money_ready_filter.js:91` falls back to `{}` = gate passes everything) | data fresh & correct; serialization broken | **Cherry-picked `3f583c83658c`** (strict JSON `_json_safe` + `allow_nan=False` at both dump sites; 8/8 tests) from rescue branch `fix/js-reference-accuracy-audit` |
| Ghost rows tile "22,947" vs truth banner "0" | **Truth banner is a hardcoded 2026-05-31 claim**; live `db_health.json` (02:47Z) still counts 22,947 ghost rows + 130 mismatches — the May repair cleared the *canonical view*, rows persist (2026-11-14 MASTER_AUDIT; quarantine-not-delete policy; cleanup tool caps at 1,000/cohort) | **tile is right, banner is wrong** | Banner reworded to "quarantined from canonical view — live raw count in DB Health tile" (both sites) |
| Swarm Paper Picks "162d" | Feed **deliberately decommissioned 2026-06-12** ("no edge; 91% never resolved"); tile outlived its dead source; live FTP serves the frozen orphan | correct data about a dead feed | Tile entry pruned from `dashboard_freshness.js` |
| Freshness sweep | Dashboard Data OK (03:03Z) · Edge Stability OK (01:42Z) · AI Leaderboard stamp fresh but **input book frozen** (`swarm_picks_OLD.json`) · IC badge dead | — | IC/Money-Ready handled above |

## 3. JS console (11 errors) — all identified

- 3× 404: `excess_column.js`, `forward_clock.js` (**deployed template references files that exist only
  on unmerged rescue branch `wired-in/buffy-2026-11-15`** — half-merged WIRED instrumentation), and
  `strategy_tribunal_latest.json` (Kill Tribunal box fell back to a hardcoded 2026-05-05 quote).
- HYPE/ARBUSDT active-pick sparklines broken: CryptoCompare CORS ×4 + allorigins→Kucoin fallback FAIL.
- `Operator Review Today` **JS TypeError** (`null.name`) — exactly the bug fixed (unmerged) on
  rescue branch `fix/assetclass-cache-live-core-stats`.

## 4. Silent-fail highlights (full sweep in the session record)

- **6 green-no-op runs**: Claude Gainer + Mercury 2 scanners skipped for missing `.joblib` (green),
  Outcome Resolver dropped a MySQL backfill mid-pipeline (green), CI Tests' coverage/known-drift warn-only,
  sports scraper self-documents "green only because continue-on-error".
- 300 `continue-on-error` sites / 69 files · ~1,400 `|| true` masks · 9 bare `git push` + 9 `|| echo`
  push sites that silently drop data on non-FF (**commit-race = top failure driver: 13 of 22 recent
  failures died at Commit/Push**).
- Fixed in this batch (earlier commit): 13 job timeouts on the 10 worst hang-prone workflows.

## 5. Fix → verification map

| Fix | Verification |
|---|---|
| strict-JSON cherry-pick | tests 8/8 pass; artifact regenerates hourly (first fixed stamp ~05:03Z) → Money Ready tile + major-goal tiles + **sizing gate** light up; check curl strict-parse + tile |
| truth-banner reword | render check (banner no longer claims "0") |
| IC card retire + deploy line drop | box absent; no fetch of corrupt orphan |
| swarm tile prune | freshness strip shows 4 tiles, no 162d warning |
| 13 job timeouts | next runs of the 10 workflows complete or kill-at-timeout instead of hanging 6h |

**Next repair batch (documented, not yet done):** safe_push routing for the 19 push sites ·
`excess_column.js` + `forward_clock.js` deploy rescue from `wired-in/buffy-2026-11-15` · Operator
Review panel fix from `fix/assetclass-cache-live-core-stats` · PM registry gap + momentum-agent
swallow · hypothesis/theory tracker wiring · `strategy_tribunal_latest.json` producer.
