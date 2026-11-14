# Peer Review — parallel audits of 2026-11-14 (reviewed from primary files, not summaries)
**Reviewer:** scratch-hippodraco · **Scope:** childlike-airport, flaxen-hair, hilarious-seer worktrees + main repo (`E:\findtorontoevents_antigravity.ca` = `/home/eaguiar2015/findtorontoevents_antigravity.ca` on this Linux host). All peers branched from the same base commit `1d9354ab9e2` as this worktree.

**Round-2 addendum (~18:00Z):** full second pass over every folder modified today — see `scratch-hippodraco.MD` Appendix A for the merged delta. Headlines: finpredict-v3 **implemented** the gatekeeper leakage flip (`d8c8dd25581`, reported on origin/main — verify + coordinator sign-off); finpredict-v1 shipped 3 P0 truth fixes; finpredict-v4's fresh evidence (ghost cohorts 22,947) adopted but its May-snapshot PF claims and destructive `proposed_fixes` SQL **red-lined**; childlike `live_picks.db` verified TRUE with corrected counts (129/129, 173d); finpredict-v3's R2 review rates this archive "most implementation-ready" (opinion, carried as such); hilarious stubs rewritten mid-review, still WEAK (opinion); spice-hyena does not exist in this workspace.

## Main-repo recently modified files (today, checked directly)
| When | File | Relevance |
|---|---|---|
| 16:07 | `updates/2026-11-14-ML-AUDIT-childlike-airport.md` | Peer audit #1 (reviewed below) — note: landed in **main repo root**, not its worktree |
| 16:01–16:07 | `bestiejob/jobs.json`, `bestiejob/README.md` | Unrelated job-board automation |
| 16:15–16:45 | `.github/gh_monitor_state.json`, `___HELL_HEALTH_OPENCODE.MD` | Infra monitors |
| 16:04–16:05 | `reports/peer_inbox_hourly.log`, `logs/vllm_8000.log` | Ops noise |
Conclusion: the only audit-relevant change in main today is childlike-airport's report. Our worktree's only change is `scratch-hippodraco.MD` + this folder (both untracked, nothing pushed).

## Agreement matrix (independent corroboration)
| Finding | scratch (us) | childlike | flaxen | hilarious |
|---|---|---|---|---|
| `pnl_pct` unit mix (100×) | ✅ MySQL recompute | — (SQLite only) | ✅ JSON recompute (`vix_reversal::SI=F`) | ✅ (claimed) |
| Stale/zombie picks | ✅ 90,588 OPEN, resolver frozen 08:xxZ | ✅ `live_picks.db` 172d | ✅ 2026-03/04 files | ✅ zombies |
| Mutual funds absent | ✅ code+DB | ✅ | ✅ | ✅ |
| `ml_score == confidence` | noted (§5.4) | — | ✅ measured | — |
| Non-unique pick IDs | — | — | ✅ (`…::2026-03-11` ×4-5) | — |
| Regime coverage ~0 | ✅ 21/16,126 | — | — | ✅ |
| Fresh artifacts mislabelled stale (walkforward etc.) | ✅ 212d | partial | partial | ✅ 157h hyro |
Verdict: the unit bug, staleness and fund gap are **three-way corroborated**. flaxen's ID-duplication and ml_score-coupling findings are genuine additions we adopted (QW-ALL also-section).

## Per-peer review

### childlike-airport — SOLID-WITH-CORRECTIONS (`updates/2026-11-14-ML-AUDIT-childlike-airport.md`, also at main-repo `updates/`)
**Strengths:** real SQLite forensics we could not replicate here (`data/live_picks.db` / `data/audit_trail.db` **do not exist in scratch-hippodraco** — peer-worktree-only evidence, treat as unverified locally): 128/129 picks 172d stale, 8 PnL sign contradictions (NEARUSDT +12.9% stored negative), `pick_history` 136 rows all REGISTERED (no lifecycle), `audit_trail.db` 9 tables × 0 rows. Sound read of `ml_ranker_fixed.py` and gatekeeper leakage docs. Its 8 fixes are safe (refresh, backfill via `asset_class.py`, lifecycle events).
**Corrections:** (1) "No dbpasses.txt exists" is misleading — it corrected itself in flaxen's version: the file is at `~/dbpasses.txt`; ours verified 70 labelled keys via env indirection only. (2) `alpha_engine/asset_class.py` as "canonical single source" contradicts the second classifier in `config.py:1020-1134` (§4.3) — unification is a fix, not a fact. (3) Gatekeeper "sound" understates that leakage-drop is **opt-in off** and folds are unsorted (§7). (4) Its universe is SQLite/JSON only — it missed the 90k MySQL zombie ledger and the percent/fraction mix in `at_signal_outcomes`.

### flaxen-hair — SOLID, most complete peer (`quick_wins/` 8 class files + 2 scripts; audit at `updates/2026-11-14-flaxen-hair.md`)
**Strengths:** the only peer to ship per-class proposals for **all** requested classes with effort/severity, verification SQL, and runnable helpers; the SI=F 100× example is the cleanest public proof of the unit bug; coinglass expiry detail (`config.py:69` MAX_HOLD 48h, monitor only in `cmd_portfolio`) verified present in our tree; bond migration check (`tools/migrations/20260530_add_bond_asset_class.sql` exists) adopted as QW-BOND-4.
**Corrections / unsafe variants (do not apply as written):**
0. **`shared/normalize_pnl_units.py:60-62` — partially unsafe (independent peer-review refinement, verified):** the script does anchor to the recomputed ratio at `:54`, so it does not corrupt genuine small percents the way a pure magnitude check would — but when `|existing|>1.0` it trusts `existing/100` over the recompute, so a genuine +150% crypto ratio (1.5) becomes 1.5% and any garbage percent is preserved ÷100 instead of replaced. Correct rule: unconditionally write the recomputed ratio whenever entry/exit exist. It also picks **ratio** as canonical while flaxen's own forex file picks **percent** (`FX-1/QW-1`) and its crypto file says "percent-only writes" — three canonical units in one pack; implementing all three re-creates P0-1. Adopt percent-at-write (QW-ALL-2). Separately, the `normalize_pnl_pct()` helper in `CRYPTO_QUICK_WINS.md:87` (`abs(v)<=1.0 → v*100`, verified present) **is** a pure magnitude heuristic and would corrupt a genuine 0.08% into 8% — do not ship that one at all.
1. `shared/normalize_pnl_units.py` picks **ratio** as the canonical unit and treats `|stored|>1` as percent — the opposite convention from the live dashboard/MySQL (percent), and still magnitude-based: a genuine +150% crypto trade (ratio 1.5) would be "converted" to 1.5%. Its saving grace is recomputing from entry/exit first; the safe rule (adopted in QW-ALL-2) is: recompute-or-NULL, never guess by magnitude.
2. Crypto snippet writes `pnl_pct=0, pnl_dollar=0` on stale expiry — fabricates flat trades. Adopted version writes **NULL** tombstones (QW-ALL-4).
3. Bond snippet closes the stale ZN=F pick with `realized_pnl_pct: 0.0` — same fabrication in miniature; use NULL.
4. `mysql -p` CLI suggestion in BO-5 would put credentials in shell history/process list — use `tools/db_env.py` instead (their intent is right, the vehicle is not).
**Missed:** MySQL headline ledger entirely (their "no trustworthy live PnL" is true of JSON files; the live dashboard payload does exist and reconciles arithmetically — the failure is underneath, in MySQL).

### hilarious-seer — WEAK on per-class depth (`audit_quickwins/…/*/quickwins.md` = 5–6-line stubs; summary at `updates/2026-11-14-hilarious-seer-audit-summary.md`)
**Strengths:** correct headline (FAIL, zombie/freshness/regime priorities), plus one unique contribution: the **model-roster/402 hygiene** (dead providers cerebras/fireworks/together) corroborating project memory (`zai_free_tier`, cerebras corrections). Its crypto stub cites real files (`prune_active_picks.py`, `smart_picks_performance.py:189` — verified existing).
**Corrections:** per-class "quickwins" are pointers, not proposals (no effort/verification/risk); claims "2 files edited / verified edits" for equity/bonds/forex inside a read-only-style audit — unverifiable from the stubs and, if true, violates the only-push-your-own-changes hygiene unless documented; `bonds_pnl_validator.py` is described as created ("new") with no file present in the listed tree; the summary mixes a session-outage narrative (Kilo 402 balance) into audit evidence. Adopt: roster hygiene + prune/regime pointers. Do not rely on its per-class claims without re-verification.

## Independent peer-review pass (second reviewer, 2026-11-14)
A second reviewer independently re-checked the three peers against `scratch-hippodraco.MD` and confirmed this file's ratings (flaxen SOLID-WITH-CORRECTIONS, childlike SOLID-WITH-CORRECTIONS, hilarious WEAK/stubs), with additions adopted here:
- **`data/live_picks.db` exists in the MAIN repo** (472K, dated Jun 3; verified `ls`) but not in any audit worktree — so childlike's key finding is a real main-repo catch our live-MySQL audit missed, marked *valid-but-unmerged*: re-verify in main before acting. Its WUSDT sign example also mixes units, corroborating P0-1 in a second store. Other misses we accept: local `audit_trail.db` 9×0-row tables, `meta_strategy.db` empty tables, SPY/QQQ tagged EQUITY in `multi_asset_picks.json`.
- **hilarious-seer phrasing corrected:** its roster/402 material is *off-scope ops drift* (already covered by the `freellm_free_tier_opt_in_design` project decision), not an asset-class contribution; "adopt" above should read "note only, not corroborating evidence." Its per-class stubs remain non-citable.
- Rejected as stated: flaxen ETF dedupe snippet (`... or list(best.values())` logic bug) and any direct SQL `UPDATE` without dry-run/backup (crypto QW-5) — require the QW-ALL-4 pattern (dry-run counts, tombstone status, NULL PnL).

## What we adopted / rejected (traceability)
| Peer item | Disposition |
|---|---|
| PnL normaliser (flaxen script) | Adopt concept, **reject** ratio-convention + magnitude rule → QW-ALL-2 recompute-or-NULL, percent |
| Stale-expiry snippets (flaxen) | Adopt, change `pnl=0` → `pnl=NULL` → QW-ALL-4, QW-CRYPTO-1 |
| Coinglass 48h expiry gap (flaxen CR-1) | Adopt → CRYPTO peer addendum |
| Bond migration verify (flaxen BO-5) | Adopt, db_env not CLI → QW-BOND-4 |
| Pick-ID uniqueness (flaxen OW-3) | Adopt → QW-ALL also |
| ml_score decoupling (flaxen OW-4) | Adopt → QW-ALL also |
| live_picks.db lifecycle (childlike #5) | Adopt as direction; evidence is peer-worktree-only → re-verify before acting |
| Roster 402 hygiene (hilarious) | Adopt → note in OVERALL also; consistent with saved memory |
| "Bonds yield×duration validator" (hilarious) | **Reject as stated** — no such file/verification; bonds here are ETF proxies (QW-BOND-2) |
