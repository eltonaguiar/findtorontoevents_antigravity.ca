# Audit dashboard investigation — consolidated findings (2026-11-15)

**Target:** `https://findtorontoevents.ca/audit/` · **Method:** live payload extraction (embedded + `data/dashboard_data.json`, 25 MB, gen `2026-11-16T04:09Z`, repo_sha `caf1f53c03`), sidecar HTTP probes, Playwright console/network capture, repo wiring + git-history trace, deploy-mechanism analysis.
**Subtasks:** T1 payload audit (completed in-thread after subagent stalled+cancelled) · T2 deploy-gap (`reports/audit_dashboard_deploy_gap_2026-11-15.md`) · T3 browser JS check · T5 fix batch A (`updates/2026-11-15-audit-dashboard-fix-batch-a.md`) · T6 DB Health trace · T7 post-deploy verification (partial).

---

## 1. Feeding verdict — WIRED / prediction markets / hypothesis tracker

| Source | On live? | Evidence | Verdict |
|---|---|---|---|
| **WIRED picks** (`wired_in_childlike`) | ✅ | 3 picks in `picks.active_raw`: `wired_in_childlike::XLV/LLY/SHY::2026-11-13`; sidecars HTTP 200 (Last-Modified 04:17Z); wired via `dashboard_generator.py:4289` + `universal_pick_resolver.py:265` (commit `770a3f1a30a`) | **Feeding — but gated**: `trust_tier=WATCH, trust_score=2, paper_only` excludes them from default Active Picks (22 of 4,105 raw). View via **"Show All Picks"** toggle. Closed file is empty (111 B) — nothing closed yet, by design. |
| **Prediction markets** (Kalshi/Polymarket/consensus) | ✅ | **24 rows / 6 sources**: `kalshi_signal_agent` 7 (fresh 03:32Z: BTC/ETH/SOL…), `prediction_market_consensus` 6, `polymarket_whale_tracker` 4, `prediction_market` 2, `kalshi_mtf_consensus` 3, `prediction_market_agents` 2. All PM workflows green (polymarket-signals 03:15Z, pm-agents 02:23Z). Verified Alpha box = **3 active** (`pm_kalshi_signals`), realized WR 43.1% on 877 trades | **Feeding** — same trust-gate as WIRED for the default view |
| **Hypothesis/theories tracker** | ❌ | Registry `reports/hypothesis_registry.json` (316 KB, used by h004/h103 workflows) is **never deployed** to `/audit/data`; zero wiring in `dashboard_generator.py`; only static H-119 text on the page | **Not wired — never was.** Requires new sidecar deploy + template fetch if wanted |

## 2. Broken items — root cause + status

| # | Symptom (as seen) | Root cause | Status |
|---|---|---|---|
| 1 | Money Ready Verdict box: **"No data available / unknown"** | Sidecar `money_ready_verdict.json` contains **2× bare `"dsr_score": NaN`** (lines 1270/1329) → JS `JSON.parse` throws (`dashboard_freshness.js:175`). Payload's own `money_ready_verdicts` (10 classes) is fine | Fix `2c958cb3f5b` (strict-JSON generators) **on main but not yet effective** — last regen 04:07:54Z ran pre-fix code. **Re-verify after next run** |
| 2 | Strategy IC Analysis: **"Failed to load"** | Producer `build_ic_analysis.py` **never existed** (documented masked-failure #7, `pick-funnel-nightly.yml`); live file is a stale orphan (Last-Modified 2026-05-29, contains bare `Infinity`) | Retirement committed (`8ab22db96c7` hides card + removes deploy line) — **not yet deployed**; orphan needs **manual FTP delete on all 3 sites** (untracked → glob never removes it) |
| 3 | `forward_clock.js`, `excess_column.js` → **404** (script tags fail) | Files exist in `audit_dashboard/` but were **missing from every deploy list** | **✅ FIXED in working tree** (batch A, uncommitted) — `deploy_audit_files.py` + all 3 per-site lists in `audit-dashboard.yml` |
| 4 | Console **TypeError** `dashboard_enhancements.js:156` — `renderOperatorReviewToday`, `null.name` | `p.source_strategies` contains a **null element**; deployed JS byte-identical to local (not a stale-deploy issue) | **✅ FIXED in working tree** (batch A) — `.filter(Boolean)` guard |
| 5 | `strategy_tribunal_latest.json` → **404** (Tribunal "latest" data) | Producer `tools/strategy_kill_tribunal.py` exists + is in deploy lists, but **no CI step runs it** / file absent in `data/` | **Open** — needs generator step in workflow (or manual run pre-deploy) |
| 6 | HYPE chart CORS errors (CryptoCompare blocked; KuCoin via `allorigins.win` → **408**) | Third-party APIs don't send CORS headers; public proxy times out | **Open** — cosmetic (chart-only); needs server-side proxy or drop the widget |
| 7 | DB Health box: **Ghost Rows 22,947** vs page note **"✅ Ghost rows: 0 (was 22,947)"** | Box is **fresh and truthful**: live `db_health.json` gen 03:52Z really reports 22,947 yellow-tier ghosts in `bt_backtest_trades` (top cohorts `MEMECOIN/meta_strategy/DOGEUSDT`, e.g. n=3,569 with `distinct_entries=1`). The "✅ 0" note is a **misleading 2026-05-31 claim**; `cleanup_ghost_rows.py` caps at **1,000 deletes/run** vs 22,947 present | **Open** — real regression/untouched population; cleanup needs raised cap/repeated runs + note corrected |

## 3. Info-box verification (vs the pasted snapshot)

| Box | Verdict |
|---|---|
| DB Health (PnL Integrity 99.5% 130/24,158; Ghost 22,947; FV Freshness 0h @02:26:30; WON-contradiction "no") | ✅ All numbers trace to fresh live JSON — **correct as displayed** (except the contradictory "✅ 0" note, see #7) |
| Data freshness | ✅ Working as designed: Dashboard Data 1h10m ("DATA STALE" = >1h flag), Edge Stability 3h19m, AI Leaderboard 18h55m, **Swarm Paper Picks 162d** ⚠ (over-3-day warning correctly shown) |
| Active/Closed counts | ⚠️ Time-skewed, not wrong: page embed (03:03Z) showed *20 of 4,209 · closed 1,661 · WR 44.1%*; fresh external JSON (04:09Z) = *22 active · 4,105 raw · recent_closed 3,500 · valid_closed 7,788 · total_closed 16,267 · WR 40.9%*. Multiple closed-count definitions coexist (headline 1,661 vs valid 7,788 vs total 16,267) — tooltips explain exclusions (`integrity_excluded` 7,536, `auto_expired_excluded` 8,881) but the headline-vs-fresh WR gap (44.1→40.9) deserves a look |
| Money Ready / per-class table / truth-layer / ML-calibration / kill-tribunal panels | ✅ Render; Money Ready **sidecar** broken (item 1); Tribunal **latest** 404 (item 5) |
| Verified Alpha | ✅ 3 active, source_mix `pm_kalshi_signals:3` (page showed 0 at 03:03 — data moved) |

## 4. JS errors (Playwright capture, 0 uncaught exceptions / 14 console issues)

- 3× 404: `strategy_tribunal_latest.json`, `forward_clock.js`, `excess_column.js` → items 3 & 5 (fixed/pending)
- 1× runtime TypeError → item 4 (fixed)
- CORS/ERR_FAILED ×~10: CryptoCompare (HYPE histohour) + allorigins/KuCoin 408 → item 6
- Everything else clean: `dashboard_data.json` 200, all other sidecars load, no page errors

## 5. Fixes awaiting your review (uncommitted, per instructions)

`3 files changed, 16 insertions(+), 4 deletions(-)` — `audit_dashboard/dashboard_enhancements.js` (null-guard), `tools/deploy_audit_files.py` (2 entries), `.github/workflows/audit-dashboard.yml` (2 files × 3 site lists). Verified: `node --check` OK, `ast.parse` OK, `yaml.safe_load` OK, no conflicts with other agents. Doc: `updates/2026-11-15-audit-dashboard-fix-batch-a.md`. **Commit/merge decision is yours** (they only take effect after merge + next `audit-dashboard` run).

## 6. T7 — pending verifications (after next audit-dashboard run)

1. `curl -s .../audit/data/money_ready_verdict.json | grep -c NaN` → must be **0**; Money Ready box shows data
2. `curl -s -o /dev/null -w "%{http_code}" .../audit/forward_clock.js` (and `excess_column.js`) → **200**
3. Strategy IC card **hidden** (retirement deployed); orphan deleted on all 3 sites
4. Re-run console check → TypeError gone; 404 count down to `strategy_tribunal_latest.json` only (until item 5 fixed)
5. `dashboard_data.json` regenerates with repo_sha containing the batch-A merge

## 7. Decisions needed from you

1. **WIRED/PM gated display** — keep as-is (view via "Show All Picks"), exempt `paper_only` sources from the gate, or add a dedicated shadow-cards panel?
2. **Hypothesis tracker** — wire `hypothesis_registry.json` to the dashboard (new sidecar + template fetch)?
3. **Swarm Paper Picks box** — 162d stale: refresh the feed or retire the box?
4. **Ghost rows** — raise `DEFAULT_MAX_DELETES` / run cleanup repeatedly to clear 22,947, and correct the "✅ 0" note?
5. **`strategy_tribunal_latest.json`** — add generator step to `audit-dashboard.yml`?
6. **HYPE chart** — add a server-side proxy or drop the widget?
