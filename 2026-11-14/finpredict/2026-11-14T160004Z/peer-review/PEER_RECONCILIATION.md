# Peer-Work Reconciliation (2026-11-14) — subtree `finpredict`

Review of all four sibling audits + the `inspect-wt` transcript agent, cross-referenced against the live payload and each other. As-of ~16:25Z. This updates my own `updates/2026-11-14-prediction-system-audit.md` (§10 corrected below).

## Peer artifact map

| Peer | Location | Contents | Commit status |
|---|---|---|---|
| `finpredict` (me) | `.kilo/worktrees/finpredict/2026-11-14/finpredict/…` | full audit + quick-wins | pushed to main (`40fea73312f`, `92720c6fdd9`) |
| `finpredict-v2` | `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/` | `sub/A..G` (incl. peer-reconciliation), `recommendations/patch_plan/P0_QUICK_WINS.md`, `recommendations/overall/DATA_CONTRACT.md`, `raw/` evidence | on disk (branch `finpredict-v2`) |
| `finpredict-v3` | `.kilo/worktrees/finpredict-v3/2026-11-14/finpredict-v3/…` | data-hygiene guardian (runnable) + remediation plan | pushed to main |
| `finpredict-v4` | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/` (main repo `audits/`) | 7 deep-dives + 6 `proposed_fixes/*/QUICK_WINS.md` + peer_review of ML audit | **uncommitted** |
| `inspect-wt` | `.inspect-wt/` (June snapshot) + pasted transcript | 5-turn audit | n/a |
| `deepAI` (= `inspect-wt`, **Windows host**) | `E:\findtorontoevents_antigravity.ca\2026-11-14\{inspect-wt_20261114_1058, deepAI_proposed_fixes_20261114_1612}\` + worktree `.inspect-wt` | findings archive (summary.MD + 5 per-class summary MDs + chat_transcript) + proposed fixes (P0–P3 README, 8 `fixspecs/`, per-asset-class quick-wins, **a real `.patch`** for hyro-pick-perf freshness tripwire) | local branch `audit/live-audit-2026-11-14` (3 commits `fcac1d9017`, `5ef470dbb3`, `0cd7a1204e`) — **NOT pushed to origin** |

### deepAI / inspect-wt peer — UNREVIEWABLE from this host

The `deepAI` agent runs on the user's Windows machine (`E:\…`, `C:\Users\zerou\Desktop\…`). Its files and its branch `audit/live-audit-2026-11-14` are **not on this Linux host** (`/home/eaguiar2015/findtorontoevents_antigravity.ca/2026-11-14/inspect-wt_*` and `.inspect-wt/` do not exist; `git ls-remote origin` shows no `live-audit`/`deepai` branch). Its `chat_transcript_2026-11-14.md` is likewise absent (matches v2's and v4's "NOT FOUND" notes).

**To review it:** the deepAI agent must `git push` its branch (it says it is "safe to push for peer review whenever you say so") or sync the folders to this host. Once pushed, fetch and review: (1) `summary.MD` + 5 per-class summaries, (2) `deepAI_proposed_fixes_20261114_1612/README.md` (P0–P3), (3) the `fixspecs/` (8 cross-asset) and per-asset-class quick-wins, (4) `patches/0001-hyro-pick-perf-freshness-tripwire.patch` — which corroborates my hyro staleness finding (hyro_pick_performance.json 6.6d stale) and is the only peer to ship an actual code patch.

## Corrections to my own doc (adopted from peers)

Three figures I carried from the `inspect-wt` transcript are **superseded/stale** and are corrected here (also edited in `updates/…audit.md` §10):

1. **"61% spot-flicker (1,147/1,882)" → NOT reproducible.** Registry-wide flicker is **7.7%** (2,188 dropped / 28,460 closed, `pf_registry.json` generated 2026-11-12). The 1,147/1,882 pair is not on disk. Drop it.
2. **"June last-14d ≈ −1.4%" → superseded.** Live last-14d (`closed_at ≥ 2026-11-01`) is **n=751, sum −333.2%, mean −0.44%** — ~240× worse. The −1.4% is a stale June 191-trade cohort.
3. **"37 active in June" → actually May 2** (`reports/kimi_swarm_2026_05_02_v3/...`). Current surfaces disagree: 20 curated / 4,148 raw / 263 concentration / 4,310 `picks_now_live_pnl`. Never quote "37".

## New findings from peers I did NOT have (to fold into the master plan)

From **v2** (`P0_QUICK_WINS.md`, root causes with line numbers):
- **P0-1 — Forex direction bucket `KeyError: 'LONG'`** kills the ALPHA scanners: `alpha_engine/scanner.py:2942` appends to a dict that only has `BUY`/`SELL` keys → **93 failed runs / 24h**. This is the *actual* root cause of the ALPHA ENGINE failures I logged as "Run Alpha Engine".
- **P0-2 — `summary_picks.json` reports WR > 100%** in 7 classes (INDEX 1,141%, FUTURES 364%, …): `tools/sync_summary_picks_json.py:63-65` counts `wins`/`losses` over *all* rows while `resolved` counts a subset. Arithmetically impossible published payload.
- **P0-3 — Python 3.14 masquerade**: **197** workflows set `update-environment: false`, so `actions/setup-python` never activates the pinned 3.11; `pandas==2.1.4` then source-builds against system 3.14 and fails. This is the *actual* root cause of the "Install dependencies" cluster I logged.
- **P0-6 — `sym_track_*` built from the wrong population**: `_enrich_live_pnl` calls `_build_strategy_symbol_track_stats` with the *active* list filtered to closed statuses (always `[]`), not the closed ledger (`dashboard_generator.py:1830-1832` vs call site `:14551`). Explains the dead "Track" column.
- **P0-9 — security**: hardcoded Google API keys tracked in `STOCKSUNIFY/…/stock-api-keys.ts` (×2) and `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js`; `dbpasses.txt` not in `.gitignore`.

From **v2 — expanded per-asset-class remediation** (added since first read; `recommendations/{QUICK_WINS.md, per_asset_class/*, overall/{ROADMAP,DATA_CONTRACT,CI_GATES}.md}`):
- **Vacuous PASS bug**: a class with `active_count == 0` short-circuits to `thresholdPass=true` (`dashboard_generator.py:6824-6826`), so **BOND renders a green PASS with 0 picks** while `money_ready_verdict` says `INSUFFICIENT_DATA`. Fix: `active_count==0 or resolved_n<30 → INSUFFICIENT_DATA` + a `NOT_BUILT` status. (Also affects ETF/FUTURES.)
- **MUTUAL FUNDS ranker is an untracked prototype**: `alpha_engine/mutual_fund_ranker.py` + `mutual_fund_metadata.csv` exist only as `??` files in the main checkout, **absent from `origin/main`**, with a `mutut_fund_rankings.json` typo and no output ever produced. Recommendation: de-advertise + `NOT_BUILT`, do not build a live MF pick class (monthly NAV has no intraday mark).
- **FOREX PR#6 block is dead code**: the allowlist has **0 call sites**; **0/277** FOREX rows pass it. Fix: make it observable (shadow mode), don't silently assume it blocks.
- **44/44 COMMODITY rows are `=F` futures** (canonical class = FUTURES); 49/277 FOREX rows aren't spot FX; ETFs sit inside EQUITY. Fix: symbol-authoritative `canonical_asset_class` + a `FUTURES_ROLLUP`, keep the display bucket.
- **Reject date-only timestamps at ingest** (`dashboard_generator.py:8136-8154, 8351-8352`) — same root cause as the FUTURES "no date" finding, now with the resolver-side location.

From **v4** (`INDEX.md`, live Binance/Yahoo + raw DB):
- **Dashboard vs raw-DB P/L inflation**: CRYPTO recent-closed PF **1.80** vs raw-DB 90d PF **0.371** (~5×); Smart-Picks CRYPTO "PF 9.69 / WR 78.9%" is **91.7% one source** (`claude_gainer_st`) with only **3 closed rows**; EQUITY dashboard PF 0.70 vs raw PF 5.56 (filter *inverts*).
- **Alpha Engine (primary scanner) DEAD**: last 10 runs = 9 cancelled + 1 failure.
- **`at_signal_outcomes` intrabar truth 254d stale**; 4,220 picks in `TIME_EXIT` limbo (only 301/4,820 resolved = 6.2%); 22,947 ghost rows.

From **v4's ML peer review** (`childlike-airport`):
- `data/live_picks.db` SQLite: 128/129 picks **172d stale**; `audit_trail.db` **empty** (9 tables, 0 rows); `consensus_active_picks.json` **empty**; three divergent data stores (SQLite/MySQL/JSON) disagree on counts/ages/PnL; ML code is mathematically sound — the inverted-confidence issue is a *data* bug.

## Disagreement resolved (important)

v4's `INDEX.md` claims "dashboard shows **0 active picks**, `dashboard_data.json` **26 days old**, freshly-painted empty shell". **This is based on the stale repo copy** (`audit_dashboard/data/dashboard_data.json` = Oct 23), **not** the live site. The live `findtorontoevents.ca/audit/data/dashboard_data.json` I downloaded is `generated_at 2026-11-14T14:30Z` with 20 curated actives / 4,148 raw / 3,500 recent-closed. v2's `G_peer_reconciliation.md` §caution flags the same. **Do not propagate "empty dashboard"** — it describes a stale local file, not the deployed surface.

## v2 peer-review synthesis (added check 2/6)

v2 now ships `recommendations/peer_review/REVIEW_SYNTHESIS.md` + per-class reviewer memos + `inspect-wt_integration.md`. New/corrected facts:

- **FOREX date-only is 105/277 `entry_time`**, not 12 (my/v3 figure was understated).
- **COMMODITY generator uses crypto proxies** (its "commodity" signals are derived from crypto price proxies), and both COMMODITY and FUTURES are in `BLOCKED_ASSET_CLASSES` (`quality_gates.py:1724`).
- **Duplicate-ID correction:** 248 groups / 297 extra rows / 56 cross-ledger conflicts.
- **v3 shipped 3 timestamped iterations** (`T155500Z`, `T161500Z`, `T161700Z`) — the latter two add `QUICK_WINS/` + `PEER_REVIEW/`.
- **Two more peers exist:**
  - `ML childlike-airport` — **on this host** at `updates/2026-11-14-ML-AUDIT-childlike-airport/` with `proposed_fixes/{overall,crypto,stocks,bonds,mutual_funds,forex,etfs}/` (SQLite `live_picks.db` 172d-stale finding; ML code sound / data bug).
  - `hilarious-seer` — **Windows host, not accessible here** (`updates/…-hilarious-seer-*` absent, like deepAI).
- **Veto list (agreed by v2 reviewers):** v4's `proposed_fixes/**` contains destructive SQL and dangerous reversals — `DELETE` ghost rows, `UPDATE TIME_EXIT→LOST, pnl_pct=0.0`, `EXPIRED_FORCE` mass rewrite, invert ML gate, unblock FUTURES/COMMODITY without a real feed, add `MUTUAL_FUND` to canonical classes before an emitter exists, re-enable audit-dashboard `push:` trigger. **Do not apply.**
- **Unified fix contract (adopt for master plan):** quote status `LIVE/LAST_CLOSE/STALE/UNQUOTED/PLACEHOLDER`; `pnl_pct=null` when unquoted (never fabricated 0); ID dedup key + economic key `(symbol,strategy,direction,entry_time,entry_price)`; `summary_picks` single terminal population; `class_canonical` + `class_raw` + `class_mismatch`.

## Bottom line

Four independent audits agree on the negative verdict (not money-ready; data pipeline broken). v2's reconciliation recommends my `updates/…audit.md` as the **backbone** for the master review; v3 contributes the only **runnable** artifact (guardian + 11 tests); v2 contributes the **most precise root causes** (P0-1..P0-9); v4 contributes **raw-DB truth** and the cross-market table. The master plan should merge: my doc (backbone) + v2's P0 fixes (implementation) + v3's guardian (CI gate) + v4's raw-DB honesty (verification).
