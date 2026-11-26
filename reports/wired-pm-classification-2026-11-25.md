# WIRED_IN + Prediction-Market Persistence Analysis (S3, round 2)

Date: 2026-11-25
Scope: read-only code/CI/.gitignore analysis. No file edits except this report.
Convention: all file:line citations are from the working tree at analysis time.

---

## Stage A -- PM persistence map (code-only)

### A.0 The gitignore rules that matter

`.gitignore:326-333` (live-state churn policy):

```
**/data/active_picks.json          # 326
**/data/live_*.json                # 327
**/data/*_signals.json             # 328   <-- catches almost every PM signal output
# 2026-06-13 (D): must persist or the PM overlay no-ops (risk-review found it gitignored).
!prediction_market_agents/data/pm_macro_overlay_signals.json   # 328 negation precedent (333)
```

Two operational consequences (both verified):

1. A file matched by line 328 cannot be committed by `git add <path>` (silently
   fails; every `git add` in the PM workflows is `... || true`).
2. A gitignored file is **not in a fresh CI checkout**. Every production run does
   `actions/checkout`, so if the producer step for a `*_signals.json` file fails
   (all are wrapped in `|| echo non-fatal`), the dashboard loader sees *no file at
   all* -- the exact "PM overlay no-ops" failure the 2026-06-13 note warns about.

### A.1 Per-source map

| # | Producer (module) | Runtime output | Gitignored? | Tracked / state | Dashboard payload key(s) | Runner / schedule |
|---|---|---|---|---|---|---|
| 1 | `alpha_engine/polymarket_signals.py` (`OUTPUT_FILE`, :29) | `alpha_engine/data/polymarket_signals.json` | YES -- `.gitignore:328` | **absent from git** (untracked, ignored); exists locally only (mtime Nov 14) | `pm_polymarket_re_signals` (`audit_trail/dashboard_generator.py:4346-4349`), paper-only (`:4366`) | `polymarket-signals.yml` cron `2,32 * * *`; also run inside `audit-dashboard.yml:128` and `alpha-engine-live.yml:296`; GH `ubuntu-latest` (or `vars.ACTIONS_RUNNER_LABEL`) |
| 2 | `alpha_engine/kalshi_signals.py` (:31) | `alpha_engine/data/kalshi_signals.json` | YES -- `:328` | **absent from git AND absent on disk** here | `pm_kalshi_re_signals` (`dashboard_generator.py:4351-4352`), paper-only (`:4367`) | `polymarket-signals.yml:62`, `audit-dashboard.yml:129`, `alpha-engine-live.yml:309` |
| 3 | `alpha_engine/prediction_market_consensus.py` (:32-33, :605, :644) | `alpha_engine/data/prediction_market_picks.json` + merges into `alpha_engine/data/active_picks.json` | NO (neither matches any ignore rule; both already tracked) | TRACKED, committed daily (last `2026-11-24 0ff2e46`, msg "Prediction market signals ... [skip ci]") | special loader `_load_prediction_market_consensus_signals` (`dashboard_generator.py:7487`, wired at `:9634`) -> `source_system=prediction_market_consensus` (`:7478`), plus virtual `pm_high_conviction` duplicate (`:9649-9652`) | `polymarket-signals.yml:76`, `audit-dashboard.yml:130` |
| 4 | `prediction_market_agents/orchestrator.py` + sub-agents (`kalshi_signal_agent`, `polymarket_momentum_agent`, `cross_market_consensus`) | `prediction_market_agents/data/{kalshi,momentum,whale,consensus}_signals.json` | **all YES** -- `:328` | all 4 absent from git and (here) absent on disk | `pm_kalshi_signals` `pm_momentum_signals` `pm_whale_signals` (`dashboard_generator.py:4118-4127`); `consensus_signals.json` via "special collector" comment (`:4115`) | `prediction-market-agents.yml` cron `12 */2`; also `audit-dashboard.yml:133` (`python -m prediction_market_agents.orchestrator`) |
| 5 | `prediction_market_agents/polymarket_whale_tracker.py` (:101-103) | `data/whale_tracker.json`, `whale_signals.json`, `whale_alerts.json` | tracker/alerts NO; `whale_signals.json` YES (`:328`) | `whale_tracker.json` TRACKED (last 2026-11-24), `whale_alerts.json` TRACKED but stale (last commit 2026-05-23), `whale_signals.json` never persisted | `pm_whale_signals` (`:4121`) | via orchestrator on both workflows above |
| 6 | `prediction_market_agents/pm_macro_overlay.py` (:48, :397) | `prediction_market_agents/data/pm_macro_overlay_signals.json` | negated/re-included at `.gitignore:333` | TRACKED (committed with alpha-engine runs) | overlay is an input to scanner; picks mirror at `alpha_engine/data/pm_macro_overlay_picks.json` (on disk, mtime Nov 15) | `alpha-engine-live.yml` family |
| 7 | `tools/pm_macro_expansion.py` (invoked `prediction-market-agents.yml:61`) | `alpha_engine/data/pm_macro_expansion_picks.json` | NO | on disk, tracked | `pm_macro_expansion` (`dashboard_generator.py:4130-4135`) | `prediction-market-agents.yml`, cron `12 */2 * * *` |
| 8 | `copy_trader_intel/polymarket_scraper.py` (leaderboard/wallet scraper, :1622-1623) | `copy_trader_intel/data/{polymarket_picks,polymarket_trader_profiles}.json` | NO | TRACKED, committed daily (last 2026-11-24 `8d37d53`) | `polymarket_signals` (`dashboard_generator.py:4116`) -- *note: this key is the copy-trader wallet file, not #1* | `audit-dashboard.yml:127`, `polymarket-signals.yml:55` |
| 9 | `alpha_engine/prediction_market_whales.py` (:54) | `alpha_engine/data/prediction_market_whales.json` | NO | TRACKED, committed by `polymarket-signals.yml:85` | consumed as consensus input (`prediction_market_consensus.py` whale path); not a direct payload key | `polymarket-signals.yml:64` |
| 10 | `prediction_market_agents/pm_odds_history.py` + `pm_lead_lag_analyzer.py` (:45-46) | `pm_odds_history.jsonl`, `pm_leadlag_report.json` | NO | TRACKED (research outputs) | none (research only) | manual/research |
| 11 | `prediction_market_agents/polymarket_btc_updown_agent.py` (:40, :211) | `data/btc_updown_signals.json`, `btc_agent_circuit_state.json` | signals YES (`:328`); circuit state NO (but never `git add`ed) | both absent from git | none found in `JSON_PICK_SOURCES` -- **orphan** | no workflow reference |
| 12 | `prediction_market_agents/polymarket_strategy_audit.py` (:28) | `data/polymarket_strategy_audit.json` | NO | TRACKED | none (report) | manual |
| 13 | `audit_trail/pm_outcome_ingest.py` (:36) | `data/pm_market_outcomes.json` | NO (no rule matches `data/*.json` except `.sql` line 145) | **absent on disk and never committed** (no git history for it) | feeds `pm_contract_resolver` (not the payload directly) | `audit-dashboard.yml:141`, right before the resolver |
| 14 | `sports_prediction_market_bridge.py` (:40-43) | `alpha_engine/data/sports_prediction_market_signals.json` + `live-monitor/backfill/...` | YES (`:328`) | never persisted | none found in the registry -- **orphan** | `sports-betting-refresh.yml` (grep match only) |

### A.2 The race that matters (why `git add` in CI is a silent no-op)

`audit-dashboard.yml:961-968` stages an explicit list that *includes*
`alpha_engine/data/polymarket_signals.json`, `alpha_engine/data/kalshi_signals.json`
and `prediction_market_agents/data/*.json`, and `polymarket-signals.yml:80-83`
even prints `::notice::polymarket_signals.json is gitignored -- FTP-deployed only;
git add would silently no-op`. So the intent to persist exists; the `.gitignore`
negation is the missing half. CM=the pm_macro_overlay precedent is the template.

### A.3 Persistence gaps + minimal fixes (recommended `.gitignore` lines -- NOT applied)

Add as its own line (never inline-comment a pattern line, see note at `.gitignore:332`),
in the block right after `.gitignore:333`:

```
!alpha_engine/data/polymarket_signals.json
!alpha_engine/data/kalshi_signals.json
!prediction_market_agents/data/kalshi_signals.json
!prediction_market_agents/data/momentum_signals.json
!prediction_market_agents/data/whale_signals.json
!prediction_market_agents/data/consensus_signals.json
```

Per-gap rationale:

| Gap | Symptom today | Minimal fix | Effort |
|---|---|---|---|
| G1 `alpha_engine/data/polymarket_signals.json` (feeds `pm_polymarket_re_signals`) | absent from git; CI regenerates each run; a failed refresh step = 0 rows in payload with only a `::warning::` | line `!alpha_engine/data/polymarket_signals.json` | S |
| G2 `alpha_engine/data/kalshi_signals.json` (feeds `pm_kalshi_re_signals`) | never even regenerated locally here (file absent) -> key currently loads **nothing** on this host; non-fatal `|| echo` in 3 workflows hides it | line `!alpha_engine/data/kalshi_signals.json` | S |
| G3 `prediction_market_agents/data/{kalshi,momentum,whale,consensus}_signals.json` (feed `pm_kalshi_signals`, `pm_momentum_signals`, `pm_whale_signals`, consensus collector) | 4 payload keys whose files exist **only inside a running CI job**; no history, no FTP fallback, no local repro | 4 negation lines (above) | S |
| G4 `data/pm_market_outcomes.json` (contract settlement feed) | written each run by `pm_outcome_ingest` but **never committed** and `data/` listing in `audit-dashboard.yml:961` does not include it -> contract outcomes rebuilt from API each run; if ingest fails, all contract picks resolve to EXPIRED/`pnl_pct=None` | add `data/pm_market_outcomes.json` to the `for f in ...` list in `audit-dashboard.yml:961` (no gitignore change needed) | S |
| G5 `prediction_market_agents/data/btc_agent_circuit_state.json` + orphan `btc_updown_signals.json` | agent has no workflow at all; "Wire-up:" docstring says `if signal.edge >= 0.08 and DRY_RUN=false` execute | either wire an agent workflow + negation, or delete the dead path (owner decision) | M |
| G6 sports bridge (`sports_prediction_market_signals.json`) | output written but no payload key reads it; matches `:328` so nothing persists either | register a payload key + negation, or treat as ARCHIVE | M |

---

## Stage B -- Pricing-distortion check (how PM PnL is actually resolved)

**Two resolution paths exist, and which one a row takes is decided by a shape test, not by its source.**

1. **Binary-contract path (correct in principle).** `audit_trail/universal_pick_resolver.py:1490`
   routes a pick through `pm_contract_resolver.resolve_contract_pick` when
   `is_contract_pick()` (`audit_trail/pm_contract_resolver.py:151`) is true -- i.e.
   `asset_class  in  {PREDICTION_MARKET, EVENT_CONTRACT}` **or** the row carries a
   market id (`market_id|market_ticker|condition_id|ticker|slug`) *and* a side
   (`contract_side|outcome|side|position`, LONG/SHORT mapped to YES/NO at
   `pm_contract_resolver.py:139`). Settlement math is payout-based:
   `pnl_pct_for()` at `pm_contract_resolver.py:166` computes `(payout - entry)/entry*100`
   with `payout  in  {1.0, 0.0}` (module docstring lines 22-25); outcome comes from
   local feeds indexed by `load_market_outcomes()` (`:317`) built from
   `audit_trail/pm_outcome_ingest.py:36` (`data/pm_market_outcomes.json`, fetched from
   the settled Kalshi/Polymarket APIs at `pm_outcome_ingest.py:115,:146`).
   No outcome + past expiry -> `EXPIRED` with `pnl_pct=None` ("never invents a PnL").

2. **Spot path (where the distortion lives).** Anything failing that shape test falls
   through to the ordinary spot pipeline: `universal_pick_resolver.py:1560-1563`
   backfills a missing `entry_price` via `_snapshot_prediction_market_entry()`
   (`universal_pick_resolver.py:1027`, twin at `dashboard_generator.py:5659`), which
   sets **entry := the current spot price of the underlying at resolver time** and,
   if TP/SL are absent, *synthesizes* them from confidence via
   `_derive_prediction_market_trade_levels()` (`dashboard_generator.py:5633`:
   `tp = min(0.04, max(0.015, 0.014 + (conf-0.55)*0.04 ...))`, `sl = tp/1.67`).
   From there PnL is plain spot math: `dashboard_generator.py:1803-1805`
   (`pnl = (price-entry)/entry*100`) and `universal_pick_resolver.py:353` (`_compute_pnl`).

**Paragraph answer -- is WR/PF for PM rows trustworthy?** *Partially, and only for the
contract rows.* The contract path is honest (outcome-based payout, EXPIRED-with-None
rather than fake zeros) but it is only as good as its feed: `data/pm_market_outcomes.json`
is never persisted (Gap G4), so a failed ingest step turns settled contracts into
`EXPIRED/pnl_pct=None` -- those drop out of WR without being wrong, which *biases*
win-rate upward if losses are also resolving as EXPIRED. The spot-derived side is not
a contract PnL at all: entry is snapshotted late (first resolver run that sees a live
price), TP/SL are synthesized from a confidence scalar rather than from the contract,
and the resulting `pnl_pct` is a move in the underlying asset, not the payoff of the
contract a reader would infer from a "prediction-market" row. On top of that, the one
PM system with a long closed ledger -- `prediction_market_consensus` (PF 24.5 / WR 90% /
n=89) -- is **already formally retired as a resolver artifact** in
`audit_trail/quality_gates.py:2045-2051` (23 DOGEUSDT rows tagged `SL_HIT_RESOLVED`
with *positive* PnL, one XRPUSDT row `SL_HIT` worth **+80.37%**), and
`copy_trader_intel` was re-blocked as a real loser (quality_gates note, same file,
a few lines below). Meanwhile PM sources are *exempt* from the sanity gate
(`_pick_sanity_gate_exempt`, `quality_gates.py:3857-3865`), so sign/exit contradictions
are not being caught at ingest either. **Verdict: contract-row WR/EXPIRED counts are
directionally usable with the G4 caveat; spot-derived PM PnL and any PF quoted for
`prediction_market_consensus`/`copy_trader_intel` are not trustworthy for money-ready
decisions -- treat them as display-only (which is why they are already in
`_PAPER_ONLY_SYSTEMS`, `dashboard_generator.py:4363-4372`).**

---
## Stage C -- WIRED_IN classification (25 dirs + 1 manifest)

### C.0 Method

* Runtime-consumer test: `git grep` for `WIRED_IN/` across `audit_trail/ audit_dashboard/
  alpha_engine/ tools/ tests/ .github/ copy_trader_intel/ prediction_market_agents/`
  -> only two hits: `audit_trail/dashboard_generator.py:4328` (comment naming the
  `2026-11-15T0150Z_childlike-airport` spec) and `tools/build_theory_tracker_sidecar.py:8`
  (which actually reads `reports/h0XX_*.json`, not WIRED_IN files).
* Consumer test: `wired_in_childlike` is referenced at
  `dashboard_generator.py:4330-4332` (JSON_PICK_SOURCES), `:4369` (`_PAPER_ONLY_SYSTEMS`),
  `audit_trail/universal_pick_resolver.py:320` (SYSTEM_SOURCES) and locked by
  `tests/test_wired_in_childlike_wireup.py`.
* Row-level check: `WIRED_IN/2026-11-15T0150Z_childlike-airport/picks/active_picks.json`
  = 3 rows (XLV, LLY, SHY) and `audit_dashboard/data/wired_in_childlike_active_picks.json`
  = the same 3 rows -> the wire is live (SNAPSHOT-level drift only).
* Existing internal index: `WIRED_IN/archive/2026-11/MANIFEST.md` (2026-11-16). I verified
  and **partially disagree** with it -- see C.2.

### C.1 Table

| # | dir | class | evidence | wiring effort |
|---|-----|-------|----------|---------------|
| 1 | `2026-11-15T0150Z_childlike-airport` | **WIRED** | `dashboard_generator.py:4330` + `universal_pick_resolver.py:320` + `tests/test_wired_in_childlike_wireup.py`; 3 shadow rows = live payload file | -- (S for refresh) |
| 2 | `2026-11-15T0230Z_childlike-airport` | ARCHIVE | 1 md (root-cause/QA bugfix doc); no producer, no consumer -- supersedes nothing, superseded by `0653Z` follow-ups | S |
| 3 | `2026-11-15T0653Z_childlike-airport` | ARCHIVE | explicitly "Template. Do not fill" (`STRATEGY_SHORTLIST.md`); prompt/HEAD_START pack, no runtime reader | S |
| 4 | `2026-11-15T0700Z_childlike-airport` | ARCHIVE | "Merged master prompt ... This folder does not claim a strategy is profitable" (`README.md`) | S |
| 5 | `2026-11-15T0703Z_childlike-airport` | RESEARCH-ONLY | negative-result diagnosis (0/10 proof gates), no picks | S |
| 6 | `2026-11-15T0709Z_childlike-airport` | RESEARCH-ONLY | DB-relevance + failure-signature notes; no picks (credentials correctly not stored) | S |
| 7 | `2026-11-15T065338Z_hilarious-seer` | RESEARCH-ONLY (ARCHIVE-candidate) | audit prompt templates + `taa_backtest_result.json`; verdicts marked BLOCKED/Unwired by its own table | S |
| 8 | `2026-11-15T0700Z_finpredict-summary` | RESEARCH-ONLY (ARCHIVE-candidate) | "0/23 hypotheses survived clean OOS" -- taxonomy, no picks; folded into `final_v001` | S |
| 9 | `2026-11-15T0130Z_scratch-hippodraco` | ARCHIVE (CANDIDATE-adjacent) | `picks/pick_justification.md`: EQUITY top-8 / ETF top-4 **"PAPER CANDIDATE ... candidates for forward-test tracking only"**, CRYPTO/FOREX/etc BLOCKED; no machine-readable picks file | M (needs an emitter) |
| 10 | `2026-11-15T0657Z_scratch-hippodraco` | ARCHIVE | same worktree as #9, later stamp, "Complete research audit -- no profitable asset class found"; `research/forward_tracker.py` meta only | S |
| 11 | `2026-11-15_0125` (finpredict-v4) | ARCHIVE | superseded by `final_v001/2026-11-15T0740Z_finpredict-v4` (same author, later digest) | S |
| 12 | `2026-11-15_012638_UTC_copilot-financial-review-20261115` | RESEARCH-ONLY | self-declares: "No algorithm in this package is newly wired into production" | S |
| 13 | `2026-11-15_0128_buffy` | **CANDIDATE** | `FORWARD_TEST.md` section 1 puts 4 named rules on the clock (`FABER10_SPY`, `BTC_TREND200`, `vwap-reversion-scout`, `rs-breakout-scout`) + `state/forward_test/plan.json` exists; **none of them emit to `JSON_PICK_SOURCES`** (only forward_validator/monitor data files mention them) | **M** (add emitters -> JSON_PICK_SOURCES entries) |
| 14 | `2026-11-15_0135` (inspect-wt) | **CANDIDATE** | README: "two deployable candidates under pre-registered forward gates" -- MF/ETF monthly 12-1 momentum sleeve (166-mo backtest) + variant-C selector (n=237, PF 1.26, p<0.0013) | **M/L** (new emitters + hypothesis registration) |
| 15 | `2026-11-15_0654_UTC_quant_prompt_kit` | ARCHIVE | 4 prompt/template files only | S |
| 16 | `2026-11-15_0700_scratch-hippodraco` | RESEARCH-ONLY (ARCHIVE-candidate) | consolidated audit: "Zero asset classes proven profitable"; also states `skyrocket_detector` NOT wired -- **stale**: it *is* wired today (`JSON_PICK_SOURCES.append(("skyrocket_detector", ...))` at `dashboard_generator.py:4199`) | S |
| 17 | `2026-11-15_0708` (HERMES_WIN_inspect-wt) | RESEARCH-ONLY (ARCHIVE-candidate) | repo-archaeology pack: proof protocol, plans, tracker CSV; manifest row already ARCHIVE-CANDIDATE; only self-referencing `run.py` hit in git grep | S |
| 18 | `2026-11-15_0711_buffy` | RESEARCH-ONLY (ARCHIVE-candidate) | master prompt + experiments (`repo_mine.py`, `build_tracker.py`) -- sidecar tool reads their `reports/h0XX_*.json`, not the WIRED_IN dir | S |
| 19 | `2026-11-15_0725_inspect-wt` | RESEARCH-ONLY (ARCHIVE-candidate) | repo archaeology (44.8k files), failure taxonomy, PROOF_PROTOCOL; no picks | S |
| 20 | `2026-11-15_AM_profitability_plan` | ARCHIVE | per-class spec docs; duplicates the identically-dated repo-root plan dir (`2026-11-15_AM_profitability-plan/`) | S |
| 21 | `archive/` | ARCHIVE | self-describing: `2026-11/MANIFEST.md` index of the other dirs | -- |
| 22 | `final_v001` | **CANDIDATE (roadmap)** / ARCHIVE (docs) | 6 consolidated decision docs; `2026-11-15T0750Z_childlike-airport/README.md` is the actionable one: extends `wired_in_trend_momo_4d` (ETF), enhances `wired_in_short_duration_ballast` (BOND), names per-class priorities -- **but no new code or pick file shipped with it** | **L** (multi-phase) |
| 23 | `flaxen-hair_2026-11-15T0125` | ARCHIVE | audit/elimination md pack; superseded by `final_v001/2026-11-15T0741_flaxen-hair` | S |
| 24 | `flaxen-hair_2026-11-15T0234_flaxen-hair` | ARCHIVE | 9-section plan pack (asset-class plans, holding-period analysis); superseded by `final_v001/2026-11-15T0741_flaxen-hair` | S |
| 25 | `2026-11-15T0724_flaxen-hair` | ARCHIVE | 1 file (`PRE_PROMPT.md`) -- a prompt stub | S |

### C.2 Disagreement with the internal manifest

`WIRED_IN/archive/2026-11/MANIFEST.md` marks `0230Z` / `0653Z` / `0700Z` childlike variants
"LIVE-REFERENCED (variants)". **Verified false in the narrow sense**: no generator, resolver,
panel, workflow or test references those directories (only `dashboard_generator.py:4328`
points at `0150Z`). They are prompt/status snapshots kept "until childlike emitter
consolidation" -- harmless to keep (S), but they are not runtime inputs.

### C.3 Recommended wire-vs-archive summary

* **Wire (do not archive):** `0150Z_childlike-airport` only -- it is the live one (3 rows).
* **Wire next (best ROI, in order):** `2026-11-15_0128_buffy` (4 pre-registered rules already
  on the forward clock -- the monitoring exists, only transport to `JSON_PICK_SOURCES` is
  missing) -> `2026-11-15_0135` (two pre-registered candidates, one needs a new emitter +
  `reports/hypothesis_registry.json` entry) -> `final_v001/...0750Z_childlike-airport`
  roadmap (L, phase-gated).
* **Archive -- 11 dirs, all effort S** (after the standing checklist in
  `archive/2026-11/MANIFEST.md` "Later-pass checklist"): #2 `0230Z`, #3 `0653Z`, #4 `0700Z`,
  #7 `065338Z_hilarious-seer`, #10 `0657Z_scratch`, #11 `_0125`, #15 `_0654_UTC_quant_prompt_kit`,
  #20 `_AM_profitability_plan`, #23 `flaxen_hair_0125`, #24 `flaxen_hair_0234`, #25 `0724_flaxen-hair`
  -- prompts/templates/duplicates/summaries. (#9 `0130Z_scratch` stays put until #14/#4 decide
  whether its paper-candidate rules are revived; `archive/`, RESEARCH-ONLY packs
  `0703`/`0709`/`012638`/`0700_scratch`/`0708`/`0711`/`0725`, and `final_v001` stay in place
  because active docs still cite them.)
* **Nothing to delete** -- every recommendation is a move under `WIRED_IN/archive/2026-11/`,
  never a delete (manifest Rule section), and each move needs `git grep <dir>` first.

---
## Stage D -- Ranked action plan (top 5)

Owner-decision column: **Y** = needs an explicit owner call (changes repo policy, displayed
stats, or what surfaces as a pick); **N** = mechanically additive, safe to do on review.

| # | Action (what + exact change) | Why it is ranked here | Effort | Owner decision? |
|---|---|---|---|---|
| 1 | **Re-include the PM signal files** -- add these 6 own-line entries to `.gitignore` right after line 333 (comments on their own lines, `.gitignore:332`): `!alpha_engine/data/polymarket_signals.json`, `!alpha_engine/data/kalshi_signals.json`, `!prediction_market_agents/data/kalshi_signals.json`, `!prediction_market_agents/data/momentum_signals.json`, `!prediction_market_agents/data/whale_signals.json`, `!prediction_market_agents/data/consensus_signals.json`; then `git add` each once so they enter history | Today 4 dashboard keys (`pm_polymarket_re_signals`, `pm_kalshi_re_signals`, `pm_kalshi_signals`, `pm_momentum_signals`, `pm_whale_signals`) depend solely on a `|| echo non-fatal` producer step inside a fresh checkout. One failed producer = rows silently vanish from `/audit` (the exact 2026-06-13 pm_macro_overlay failure mode, `.gitignore:331`). `alpha_engine/data/kalshi_signals.json` is *currently* absent on disk too | S | **Y** (repo-churn policy: these were ignored to stop commit churn; the counter-argument is that they are the fallback the `git add` lists already assume) |
| 2 | **Persist contract settlements** -- add `data/pm_market_outcomes.json` to the `for f in ...` list in `.github/workflows/audit-dashboard.yml` step "Commit updated data" (~line 961). No `.gitignore` change needed (verified: no rule matches `data/*.json` except `.sql`) | The whole point of the 2026-11-16 contract-resolver fix leaks: outcomes are rebuilt from the Kalshi/Polygon APIs every run, so a transient ingest failure rewrites settled contracts as `EXPIRED/pnl_pct=None` (WR bias) and there is no persisted evidence trail | S | **N** (pure additive persistence, no display/behavior change) |
| 3 | **Make PM WR/PF readable again** -- three small, independent changes: (a) surface the already-computed `pm_pick_kind` (set at `universal_pick_resolver.py:1506`) as a dashboard split so contract rows and `spot_derived` rows never share a WR/PF cell; (b) drop PM sources from `_pick_sanity_gate_exempt` (`audit_trail/quality_gates.py:3857-3865`) so `SL_HIT_RESOLVED`-with-positive-PnL contradictions are rejected at ingest; (c) keep `prediction_market_consensus` retired (`quality_gates.py:2045-2051`) rather than "fixing" its PF 24.5 | Stage B: contract PnL is sound, spot-derived PnL is a proxy that never matches a contract payoff; the two are currently mixed, and PM rows are exempt from the sanity gate that would catch sign contradictions | M | **Y** (changes headline stats people read) |
| 4 | **Wire buffy's pre-registered rules** (`WIRED_IN/2026-11-15_0128_buffy`): add emitters for `FABER10_SPY`, `BTC_TREND200`, `vwap-reversion-scout`, `rs-breakout-scout` (already on the forward clock via `state/forward_test/plan.json` + `tools/forward_tracker.py`) and register 1-2 `JSON_PICK_SOURCES` entries, shadow/paper-only first (`_PAPER_ONLY_SYSTEMS` pattern like `wired_in_childlike`) | Highest-leverage supply win: these are pre-registered, forward-tracked, still-unemitted rules. The sibling S4 analysis shows clean-trade supply (~20 active of ~4100/pick supply, ~99k OPEN rows) is the binding bottleneck, so a WIRED_IN candidate that is *already* on the forward clock beats mining another plan | M | **Y** (it promotes research to visible pick source) |
| 5 | **WIRED_IN archive pass** -- execute the standing checklist in `WIRED_IN/archive/2026-11/MANIFEST.md`: `git grep` each dir, move the 11 S-effort dirs listed in C.3 under `WIRED_IN/archive/2026-11/<dir>/`, update the manifest table, run `tests/test_wired_in_childlike_wireup.py` + one audit cycle. Corrects the manifest's stale "LIVE-REFERENCED (variants)" claim for `0230Z`/`0653Z`/`0700Z` | 25 dirs with 1 runtime consumer is pure navigation cost for the next agent; the manifest itself already declared this the "safe first step" -- the index exists, only the move is deferred | S + 1 audit cycle | **Y** (file moves in a shared tree) |

**Explicit non-actions (deliberately not ranked):** do not delete any WIRED_IN dir; do not
promote PM rows out of `_PAPER_ONLY_SYSTEMS` (Stage B says their PnL is not money-grade);
do not wire `polymarket_btc_updown_agent` / `sports_prediction_market_bridge` (orphans, Gap
G5/G6) -- decide deprecation vs wiring only after #1-#3 land.

### Verification notes for this report (evidence trail)

* gitignore verdicts come from `git check-ignore -v` + `git ls-files` per path (Stage A table).
* Workflow/cron/runner facts from `.github/workflows/{polymarket-signals,prediction-market-agents,alpha-engine-live,audit-dashboard,kalshi-snapshot}.yml`.
* Runtime-consumer test for WIRED_IN = `git grep -l "WIRED_IN/"` over the 9 code roots; hits were `audit_trail/dashboard_generator.py:4328` and `tools/build_theory_tracker_sidecar.py:8`.
* WIRED row-count check: 3 rows (XLV/LLY/SHY) in both the WIRED_IN pick snapshot and `audit_dashboard/data/wired_in_childlike_active_picks.json`.
