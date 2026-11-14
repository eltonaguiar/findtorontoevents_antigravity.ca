PASS

# Peer Review PR3 — FOREX / FUTURES / Actions-CI

**Reviewer:** Peer Reviewer PR3
**Clock:** 2026-11-14T16:30Z (Linux host; repo read-only except this archive folder)
**Reviewed plan:** `recommendations/per_asset_class/forex_futures.md`, `recommendations/patch_plan/P0_QUICK_WINS.md`, `recommendations/patch_plan/P1_STRUCTURAL.md`, `recommendations/overall/CI_GATES.md`, `sub/A_actions_health.md`, `MASTER_AUDIT.md`
**Peers:** `finpredict` v1 (16:00:04Z), `finpredict-v3` (15:55Z), `finpredict-v4` (15:55Z), plus the newer `childlike-airport` ML audit (16:04Z) that landed during this review.

---

## Verdict: PASS

**PASS — with 4 required factual corrections (none invalidates the P0 sequence).**

All five highest-risk citations in our plan reproduce exactly: the `KeyError:'LONG'` site, the audit-dashboard cron/concurrency/timeout lines, `update-environment: false` in the named workflows and its 197-file repo count, the `non_crypto_policy.py` allowlist with zero call sites, and the date-only `entry_time` write path. The recommended fixes are directionally correct and safe to sequence as written.

It is **not** an unconditional pass because four statements are wrong or materially under-scoped:

1. **"FUTURES 0 closed ever" is false as a global claim.** The dashboard `picks.recent_closed` feed has 0 FUTURES rows, but v4's own evidence file reports FUTURES intrabar `n=52, WR 42.3%, PF 1.094`, and the `childlike-airport` peer reports 234 closed FUTURES rows in the JSON closed feeds. The correct claim is "0 FUTURES rows in the dashboard closed feed", not "0 closed ever".
2. **FOREX date-only `entry_time` is 105/277 rows, not 12.** The 12 figure is date-only `timestamp`; `entry_time` is already date-only on 105 FOREX rows. P0-1 understates its own impact by ~8x.
3. **The "44 undated" FOREX rows are stamped, not undated.** They carry `YYYY-MM-DD HH:MM:SS EST` strings that both `datetime.fromisoformat` and `universal_pick_resolver._parse_timestamp` reject. Calling them "no timestamp" hides a parser bug that P0-1 does not fix.
4. **`ig_contrarian_sentiment` and `myfxbook_retail_contrarian` are not "unblocked".** Both are in `_RETIRED_STRATEGIES` (`strategy_blocklist.py:239,241`). v4 is wrong, and our P0-6 understates the blocklist gap: 4 retired strategies (not 1) account for ~95 of the 277 FOREX rows.

---

## 1. Reconciliation — v1 / v2 (ours) / v3 / v4

| Topic | v1 (`finpredict`) | v2 (ours) | v3 (`finpredict-v3`) | v4 (`finpredict-v4`) | Verdict |
|---|---|---|---|---|---|
| Overall verdict | FAIL | FAIL | FAIL | FAIL | **AGREE** |
| 365 workflows | yes | yes | — | yes | **AGREE** |
| Last-run failures | 28 | 25 last-run / 24 workflows in 24 h | — | 28 | **DISAGREE on number** — raw `A_rows.json` yields 25 failure + 11 cancelled + 38 with no last run; the 28 figure counts retried/in-progress attempts as failures. Timing artifact, not a factual break. |
| Alpha Engine | broken | 93 failed runs/24 h `KeyError:'LONG'` (47 + 46) | — | "DEAD: last 10 = 9 cancelled + 1 failure" | **AGREE that output is unusable; "dead" is imprecise** — the scanners run every 30 min and fail, they are not absent. |
| Curated active picks | 20 | **20 live** | 20 | **INDEX says 0**; its own `forex_deep_dive.md:19` says **20 total / 2 FOREX** | **v4 internally contradictory.** Live fetch and v1/v3 agree on 20. v4's 0 is a stale-local-JSON artifact, contradicted by v4 itself. |
| `dashboard_data.json` age | 1.63 h | 1.63 h | 1.63 h | `noncrypto_deep_dive.md:30` says **26 d (Oct 19)**; `forex_deep_dive.md:19` says generated **2026-11-14T14:30:07Z** | **v4 internally contradictory.** Live payload is same-day. |
| `active_raw` | 4,148 / 691 OPEN | 4,148 / 3,851 IDs / 691 OPEN | zombie scan 3,577 CRYPTO | 4,310 | **Minor count drift** (v4 backlog population). v2 count reproduced exactly. |
| FOREX frozen prices | yes | 93/118 OPEN frozen (90 null + 3 `current==entry`); 242/277 null price | yes | 2/2 curated frozen; 96.6% of stored picks null PnL | **AGREE** |
| FOREX block bypass | implied | allowlist has **0 call sites**; live gate omits it; **0/277 pass** | not addressed | **PR #6 false in practice**; `non_crypto_consensus` bypasses | **AGREE** — different mechanisms named, same conclusion. v4 adds the sizing-gate detail (`risk_policy_check.py` PR-D), verified below. |
| Consensus inputs | — | `non_crypto_consensus` retired but still emits 20 rows | — | 1 blocked + 2 "unblocked losing" strategies | **CORRECTION:** all three named strategies (`forex_rsi2_mean_reversion`, `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`) are in `_RETIRED_STRATEGIES`. v4's "unblocked" label is false. |
| FUTURES date-only | `signal_time` bare `2026-11-14`; UI blank | not reproduced on live table; `entry_time`/`signal_time` date-only, full `timestamp` present | date-only → UI blank | 0 live; only YM=F in 26-day-old file | **AGREE on the underlying defect; UI-render claim UNVERIFIED.** Our payload re-check: 3 OPEN ES=F + 6 YM=F EXPIRED date-only `timestamp`; 9/13 date-only `entry_time`. |
| FUTURES closed sample | 0 closed ever | 0 in `picks.recent_closed` | — | intrabar `n=52, PF 1.094` | **OURS OVERSTATED.** "0 closed ever" is wrong; "0 in dashboard closed feed" is correct. |
| FOREX duplicates | — | 40 dup-ID groups / 67 extra rows; 67 trade-key groups / 198 extra | — | 29 picks / 10 symbols, heavy duplication | **AGREE** (different populations) |
| SQLite `data/live_picks.db` | not covered | not covered | not covered | `childlike-airport` peer: 128/129 stale, PnL sign bug | **MISSED BY v1/v2/v3/v4.** v2 re-check: 129/129 rows >24 h stale; `pick_history` has only `REGISTERED` (136). No `asset_class` column, so the peer's "4 FOREX" split does not reproduce from this file. |
| CI Python 3.14 | install-dependency cluster | 8 workflows + 197 files `update-environment: false` | — | repeat offender list | **AGREE** |
| Audit-dashboard cancels | 0-job cancels noted | 61/168 in 7 d; median 84.5 min | cadence mismatch | Outcome Resolver / Alpha cancelled | **AGREE** |

---

## 2. Independent verification of the five high-risk claims

All commands run read-only in `/.kilo/worktrees/finpredict-v2` at ~16:30Z. "Exact lines" are `sed -n`/`grep -n` output, not inferred.

### (a) `KeyError: 'LONG'` at `alpha_engine/scanner.py:2937-2942` — **CONFIRMED**

```text
2937:    _forex_by_sym = _dd(lambda: {"BUY": [], "SELL": []})
2941:            sig_type = s.get("signal_type", "BUY")
2942:            _forex_by_sym[s["symbol"]][sig_type].append(s)
```

`defaultdict` creates the **symbol** key lazily; the inner value is a plain dict containing only `BUY`/`SELL`. Any `signal_type` of `LONG`/`SHORT` raises `KeyError`. Our citation (`P0_QUICK_WINS.md:24-32`) is exact. The 93 failed runs/24 h attribution (ALPHA 47 + FAST 46) comes from `sub/A_actions_health.md:35-36`; the current traceback line matches.

### (b) `audit-dashboard.yml` cron / concurrency / timeout — **CONFIRMED**

| Claim | Exact line found |
|---|---|
| hourly cron | `:5  - cron: '10 * * * *'` |
| concurrency group | `:41  group: dashboard-publish` |
| queue, do not cancel | `:42  cancel-in-progress: false` |
| job timeout 115 | `:55  timeout-minutes: 115` |
| resolver step 40 | `:129  timeout-minutes: 40` |
| second long step 30 | `:493  timeout-minutes: 30` |

`P0_QUICK_WINS.md:182-188` is accurate. Additional verified detail: the second `python -m audit_trail.dashboard_generator` is at `:997` and only runs in the merge-failure retry branch, so P1-4's "the same step re-runs after the commit … doubling the most expensive step" is true only on merge-conflict retries, not every run.

### (c) `update-environment: false` — **CONFIRMED**

| Workflow | Lines |
|---|---|
| `.github/workflows/signal_tracking.yml` | `:35 update-environment: false`, `:36 python-version: '3.11'` |
| `.github/workflows/alpha-engine-fast.yml` | `:35`, `:36 python-version: '3.11'` |
| `.github/workflows/forward-test-new-strategies.yml` | `:25`, `:26 python-version: '3.12'` |
| `.github/workflows/autonomous_trading.yml` | `:37`, `:38 python-version: '3.11'` |
| `.github/workflows/copy-trader-intelligence.yml` | `:30`, `:31 python-version: '3.11'` |

Repo-wide count: `grep -rl "update-environment: false" .github/workflows/ | wc -l` = **197**. `requirements.txt:2` is `pandas==2.1.4`. Our P0-3 and P1-3 are correct. Note `forward-test-new-strategies.yml` pins 3.12, not 3.11; the fix (remove `update-environment: false`, keep the pin, add an interpreter assertion) still applies.

### (d) `non_crypto_policy.py:698-741` allowlist has 0 call sites — **CONFIRMED**

```text
alpha_engine/non_crypto_policy.py:698: def evaluate_non_crypto_candidate(...)
alpha_engine/non_crypto_policy.py:724:     _FOREX_ALLOWED = frozenset({"cta_cross_asset_tsmom", "forex_carry", "forex_carry_g10"})
alpha_engine/non_crypto_policy.py:725-741: allowlist + SHORT-only enforcement
```

`grep -rn "evaluate_non_crypto_candidate" --include=*.py .` returns **only the definition**. The live gate:

```text
alpha_engine/non_crypto_policy.py:1026  def passes_non_crypto_policy(...)
alpha_engine/non_crypto_policy.py:1035-1040  passes_fx_session_gate + passes_atr_reachability_gate only
```

Callers: `multi_asset/scanner.py:705`, `multi_asset/forex_strategies.py:986`, `alpha_engine/forex_smart_picks.py:483`, `alpha_engine/commodity_signal_generator.py:211`, `alpha_engine/commodities_strategies.py:1057`. None calls the allowlist function. Payload recompute: **0/277 FOREX rows pass**. Our P0-6/P1-2 are correct.

### (e) Date-only `entry_time` in the emitter/generator — **CONFIRMED, but under-scoped**

```text
audit_trail/dashboard_generator.py:8137  _entry_ts_keys = ("entry_date", "entryDate", "entry_time", ...)
audit_trail/dashboard_generator.py:8149-8154  first non-empty value wins, no format check
audit_trail/dashboard_generator.py:8351  "signal_time": entry_ts or ts
audit_trail/dashboard_generator.py:8352  "entry_time": entry_ts
copy_trader_intel/multi_asset_copytrader_scraper.py:452  "entry_date": now.strftime("%Y-%m-%d")
copy_trader_intel/multi_asset_copytrader_scraper.py:471  "timestamp": now.isoformat()
audit_trail/universal_pick_resolver.py:747-749  formats are T-separated only; no %Y-%m-%d, no %Z
```

Payload counts (recomputed from `raw/dashboard_data.json`):

| Class | date-only `timestamp` | date-only `entry_time` |
|---|---:|---:|
| FOREX | 12 | **105** |
| FUTURES | 6 | 9 |

The emitter writes a full ISO `timestamp` on the same row, so the fix in P0-1 is safe. The 44 "no parseable timestamp" rows are `... EST` strings, not blank; the resolver's format list also cannot parse them.

---

## 3. Additional claim checks (not requested, but material)

| Claim | Result |
|---|---|
| `picks.active` = 20; 19 `pnl_pct==0`; 7 exact `current==entry`; 19 within 1e-4 | **Confirmed** |
| `picks.active_raw` = 4,148 / 3,851 IDs; EXPIRED 3,377 / OPEN 691 / SL_HIT 55 / TP_HIT 25 | **Confirmed** |
| `active_raw` null price 3,584; `pnl_pct==0` 3,832; exact `current==entry` 202 | **Confirmed** |
| `recent_closed` = 3,500; FUTURES = 0; exit mix SL 1,451 / TP 884 / FORCE 622 / TIME 516 / UNKNOWN 22 / EXPIRED 5 | **Confirmed** |
| `summary_picks` FOREX 147.0% (8,536 W / 8,968 L vs resolved 5,806); FUTURES 363.9% (222/357 vs 61); INDEX 1,141.2% | **Confirmed** |
| `db_health` ghost rows 22,947; open 90,523 / total 143,156 | **Confirmed** |
| FOREX 277 rows / 118 OPEN / 158 EXPIRED / 1 SL; 273 `pnl==0`; 242 null price; 40 dup-ID groups / 67 extra; 67 trade-key groups / 198 extra | **Confirmed** |
| FOREX 44 currency-ETF rows (FXA 13, CEW 10, UUP 9, FXC 5, FXY 4, FXE 2, FXB 1) + 5 EURUSDT = 49/277 | **Confirmed** |
| FOREX top strategies: MeanReversionBB 74, Quality Compounders 36, `ig_contrarian_sentiment` 30, `forex_rsi2_mean_reversion` 24, MomentumEMA 21, `non_crypto_consensus` 20 | **Confirmed** |
| 233 FOREX rows parse; 114 are >30 d; oldest 267.3 d | **Confirmed** — the "158 rows >30 d" correction in `forex_futures.md:33` is right |
| FUTURES 13 rows: 3 OPEN ES=F (same ID, entry 7583.0, Saturday 13:06Z), 10 EXPIRED (YM 6, NG 1, GC 1, CL 1, ZN 1) | **Confirmed** |
| `_RETIRED_STRATEGIES` includes MomentumEMA, `forex_rsi2_mean_reversion`, `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`, `futures_momentum`, `cta_cross_asset_tsmom`, `non_crypto_consensus` | **Confirmed** (`strategy_blocklist.py:104` list; entries ~125,144,229-241; `_BLOCKED_STRATEGIES` at :439) |
| `risk_policy_check.py` PR-D is a sizing gate, not an emission block | **Confirmed** (`:22-28`, `is_forex_sizing_allowed` `:31-60`) |
| `multi-asset-scanner.yml` runs `*/30 * * * *` every day with no session guard | **Confirmed** (`:10`, `:36-38`) |
| `futures-agent.yml` "correctly weekday-gated" | **PARTLY WRONG** — it has `0 14 * * 1-5`, `0 22 * * 1-5`, **and `0 22 * * 0` (Sunday)** at `:7-10`. The Sunday run is before the Sunday 23:00 UTC reopen (EST), so the point survives but the wording is wrong. |
| v4's `evidence_intrabar_truth.json` FUTURES `n=52, PF 1.094` | **Confirmed** (file read) |
| `data/live_picks.db`: 129 rows, all >24 h stale, `pick_history` only `REGISTERED` (136) | **Confirmed**; peer's "128/129" and "4 FOREX with null price" are **not reproducible** from this snapshot (no `asset_class` column; all 129 have non-null `current_price`). |

---

## 4. Contradictions and corrections to our own plan

| # | Our statement | Evidence | Correction |
|---|---|---|---|
| C1 | `MASTER_AUDIT.md:101` — FUTURES "**0 closed ever**"; `forex_futures.md` P1-5 repeats the premise | `recent_closed` FUTURES = 0 is true, but v4 intrabar n=52 and childlike-airport 234 closed | Say "**0 FUTURES rows in `picks.recent_closed`**"; FUTURES has resolved samples elsewhere. P1-5's goal is "get FUTURES into the primary feed", not "create the first closed sample". |
| C2 | `forex_futures.md` P0-1 — "fixes 9/13 FUTURES `entry_time` and **at least 12** FOREX date-only rows" | 105/277 FOREX rows already have date-only `entry_time` | Expected impact is **105 FOREX + 9 FUTURES**, ~8x larger. |
| C3 | `forex_futures.md:30,33` — "**44 have no timestamp**" / "no parseable timestamp" | 44 rows are `YYYY-MM-DD HH:MM:SS EST`; they are stamped but unparseable by both parsers | Say "**44 EST-suffixed timestamps that neither parser accepts**"; add `%Z`/`dateutil` to the resolver fix. |
| C4 | `forex_futures.md:48,218` — only `non_crypto_consensus` is called out as retired | `ig_contrarian_sentiment` (30), `MomentumEMA` (21), `forex_rsi2_mean_reversion` (24) are also in `_RETIRED_STRATEGIES` | The blocklist gap is **~95/277 rows across 4 retired strategies**, not 20/277 across 1. Strengthens P0-6/P1-2. |
| C5 | P0-4 — `futures-agent.yml` "correctly weekday-gated (`0 14 * * 1-5`)" | `:7-10` also has `0 22 * * 0` | Say "mostly weekday-gated, but includes a Sunday 22:00 UTC run before the EST reopen". |
| C6 | P1-4 — the post-commit generator re-run "doubles the most expensive step" | `audit-dashboard.yml:997` is inside the merge-failure retry branch | True only on merge-conflict retries; not a normal per-run double. |
| C7 | Do-not-do #1 — "do not flip `FOREX_HARD_DISABLE` first" | v4 recommends "kill or paper-trade only" and "enforce PR #6" | **Sequencing difference, not a factual conflict.** Our shadow → warn → block-new-emissions path is safer; add an explicit operator decision gate before enforcement. |
| C8 | `forex_futures.md:147` — the 3 ES=F rows are "one ID emitted 3×" | Confirmed: all three share `multi_asset_futures_connors_rsi2::ES=F::2026-11-14_1306` | No correction; note that 2 of the 3 have `current_price=None` and one has `current==entry`, so the "100% frozen" label is accurate but for two different reasons. |

Peer contradictions worth recording:

- **v4 INDEX vs v4 deep dives:** "0 active picks / 26-day stale dashboard" (INDEX, `noncrypto_deep_dive.md:30`) is contradicted by `forex_deep_dive.md:19` ("20 total active picks… generated 2026-11-14T14:30:07Z") and by v1/v2/v3. Treat v4's headline as a stale-local-file artifact.
- **v4 "Alpha dead":** the namespace is unhealthy (`KeyError`), but 48 Dynamic + 48 FAST runs occurred in 24 h. "Dead" should read "failing on every attempt".
- **v4 "unblocked losing strategies":** false; all three consensus inputs are retired (see C4).
- **v1/v4 "28 last-run failures" vs v2 "25":** snapshot/retry artifact. Raw `A_rows.json` = 25 failure + 11 cancelled + 38 with no last run.
- **childlike-airport vs v2 active counts:** 129 SQLite rows / 273 deduped JSON active / 4,148 `active_raw` / 20 curated are four different populations. Do not compare them; label the population in every fix.

---

## 5. Peer recommendations we missed, and ours that conflict

### Missed from peers (add or explicitly scope out)

1. **SQLite `data/live_picks.db` is a third data layer** (childlike-airport, 16:04Z). 129 rows, all >24 h stale, `pick_history` only `REGISTERED`. Our plan audits MySQL + JSON only. Either add a "retire or reconcile the SQLite store" item or declare it out of scope with an owner. This is the clearest gap.
2. **`forex` vs `FOREX` case-duplication** (childlike-airport): 120 lowercase `forex` closed rows alongside 1,097 `FOREX`. Our P0-3/P1-1 covers currency ETFs and `EURUSDT`, not case normalization. Add a normalization assertion.
3. **11 frozen closed FOREX phantoms** (v3, also v1): EURUSD/USDCHF/USDJPY/AUDUSD/GBPUSD/NZDUSD/SOFI, March 2026, `exit UNKNOWN`, `exit_price == entry_price`. Our plan has a FUTURES resolver item (P1-5) but no FOREX phantom sweep. Add to P1-3/P1-5.
4. **`tools/pi_data_hygiene.py` already exists** in the v3 worktree (`tools/pi_data_hygiene.py`, `tests/test_pi_data_hygiene.py`, 14 passing per its verification). It is **not on main**. Port it and wire it into our G2/G6 gates instead of writing new detectors from scratch.
5. **`risk_policy_check.py` PR-D** (v4): verified sizing-only gate. Add it to the P1-2 rationale so the "sizing blocked but emission allowed" distinction is explicit and testable.
6. **Filter `_gate_passed=false` rows from the active panel** (v3, v4): the 2 curated FOREX rows are `_gate_passed=false`, `_below_gate=true`. Our P1-6 adds `PLACEHOLDER`, but does not explicitly say gated rows leave the active panel. Make that explicit.
7. **`asset_class.py` is the canonical classifier** (childlike-airport). Our P1-1 agrees, but note the contradiction: `alpha_engine/asset_class.py` lacks the currency ETFs (`:37-53`) and already calls `EURUSDT` crypto (`:222-224`). The canonical module is not yet canonical for these two sets; P1-1 must add them, not merely defer to it.

### Ours that conflict (see also C1-C7)

- "0 closed ever" vs the n=52 intrabar ledger. Fix the wording; keep the goal.
- "at least 12 FOREX date-only rows" vs 105 actual. Fix the scope.
- "44 undated" vs 44 EST-stamped/unparseable. Fix the diagnosis.
- "futures-agent weekday-gated" vs its Sunday cron.
- P1-4's double-generator claim is conditional, not universal.
- Our do-not-flip-hard-disable sequence differs from v4's immediate enforcement. Keep ours; document the operator gate.

---

## 6. Recent-file scan since 2026-11-14T15:30Z

Method: `find . \( -path ./.git -o -path ./node_modules -o -path ./.kilo/worktrees \) -prune -o -type f -newermt '2026-11-14 15:30:00 UTC' -print`. Note: a first scan without `UTC` produced false positives because the host `TZ` is unset; the UTC-qualified scan is authoritative. Result: **43 files**.

| Group | Files | Relevance |
|---|---|---|
| v4 archive (12) | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/{actions_health_report,forex_deep_dive,noncrypto_deep_dive,dashboard_data_report,dashboard_metrics_sources,market_crossref_report,INDEX}.md` + 4 `evidence_*.json` | Peer artifacts under review |
| New ML audit (8) | `updates/2026-11-14-ML-AUDIT-childlike-airport.md` + `proposed_fixes/{overall,crypto,stocks,bonds,mutual_funds,forex,etfs}/FIX_PROPOSED.md` | **New peer, not in v1-v4 cross-ref**; source of the SQLite/case-normalization findings |
| CI/monitor state (4) | `.github/gh_monitor_state.json`, `.kilo/agent-manager.json`, `tools/ai_menu.sh`, `___HELL_HEALTH_OPENCODE.MD` | No prediction-source change; `tools/ai_menu.sh` is operator tooling |
| bestiejob (8) | `bestiejob/{FRESH_JOBS.md,jobs.json,README.md,README.BAK_*}` + 3 `public/**/jobs.json` | Unrelated job-board pipeline |
| Logs (2) | `logs/vllm_8000.log`, `reports/peer_inbox_hourly.log` | Runtime logs |
| Our archive | `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/**` | Excluded by rule; this review is the only new file from PR3 |

Commits since 15:30Z (non-`[skip ci]`): 20+, dominated by `audit(finpredict)` / `archive:` commits from v1/v3/v4 and two merges. Automated `[skip ci]` data commits continue (audit payload, crypto portfolios, scans). **No `alpha_engine/`, `audit_trail/`, `copy_trader_intel/`, or `.github/workflows/` source change landed in the window**, so the code citations above remain valid as of the review clock.

---

## 7. Ranked must-fix list

Ranked by (failure impact × confidence) ÷ blast radius.

| Rank | Fix | Why first | Exact anchor | Effort |
|---:|---|---|---|---|
| **1** | Guard the FOREX direction bucket (`LONG→BUY`, `SHORT→SELL`, else `OTHER`) | Removes the dominant 93 failed runs/24 h and restores both Alpha scanners | `alpha_engine/scanner.py:2937-2942` | S |
| **2** | Make the FOREX block observable, then enforce on new emissions | 0/277 pass the advertised allowlist; **~95/277 rows come from 4 already-retired strategies**; consensus threshold is 1 | `non_crypto_policy.py:698-741,1026-1040`; `non_crypto_consensus.py:143-147`; `strategy_blocklist.py:104,229-241` | S→M |
| **3** | Quote provenance + ISO entry-time enforcement | 93/118 OPEN FOREX frozen; 242/277 null price; **105 FOREX + 9 FUTURES date-only `entry_time`**; resolver cannot parse date-only or `EST` | `dashboard_generator.py:8137-8154,8351-8352`; emitter `:452,471`; resolver `:747-749` | S |
| **4** | CI: remove `update-environment: false` in the 8 failing workflows; move audit-dashboard cron to 2 h | 197 files affected; 61/168 cancels/7 d; 84.5 min median vs hourly cron | `.github/workflows/{signal_tracking,alpha-engine-fast,forward-test-new-strategies,autonomous_trading,copy-trader-intelligence}.yml`; `audit-dashboard.yml:5,41,42,55,129,493` | S |
| **5** | FUTURES weekend guard + exact-ID dedup | 3 copies of one ES=F ID emitted Saturday; no session check | `multi-asset-scanner.yml:10,36-38`; emitter `:798-854,2700-2705` | M |
| **6** | Correct the FUTURES closed-ledger premise and wire the feed | "0 closed ever" is false; the dashboard feed is the gap | `universal_pick_resolver.py:743-755,1294-1304`; `dashboard_generator.py:4128` | L |
| **7** | FOREX phantom sweep + `EST` timestamp parsing | 11 frozen closed phantoms; 44 unparseable timestamps; date-only hold math | `universal_pick_resolver.py:743-755`; v3 `FROZEN_CLOSED_PHANTOM` | S/M |
| **8** | Reconcile or retire the SQLite layer; normalize `forex`→`FOREX` | 129 stale SQLite rows; 120 case-duplicated closed rows; 3-way divergence | `data/live_picks.db`; `alpha_engine/asset_class.py` | M |
| **9** | Suppress/harden impossible `summary_picks` WR | FOREX 147.0% and FUTURES 363.9% are arithmetically impossible | `tools/sync_summary_picks_json.py:63-65,161` | S |
| **10** | Reuse v3's hygiene detector; fix G8's static assertion | Avoids duplicate tooling; G8 must assert cron ≥ p95 and `cancel-in-progress: false` | `tools/pi_data_hygiene.py` (v3 worktree); `CI_GATES.md` G8 | S |

**Do first:** #1 and #4 are independent and same-day. #2 must be shadow-only on day 1. #3 lands after #2's shadow count so `UNQUOTED` can be joined to `would_block` without changing enforcement.

---

## 8. UNVERIFIED

- **Root causes of the retrying runs** (Sports smoke, CI Tests, Market Beating, robust-edge-miner, ALPHA Live) — still mid-retry at capture; unchanged from v2's `sub/A_actions_health.md:190-195`.
- **Production value of `FOREX_HARD_DISABLE`.** Repo default computes `False`; the 277 emitted rows imply it was off, but the deployed env var was not observable.
- **What writes the 44 `... EST` timestamps.** The parser gap is proven; the emitter was not traced.
- **Whether the 11 frozen closed FOREX phantoms are genuinely unresolved or a resolver bug** — v1/v3 agree on the symptom; no exit ledger was reconstructed.
- **CME holiday behavior** of the proposed `_futures_session_open` — weekends only unless a calendar is added.
- **v4's "0 picks / 26-day stale" source file.** The contradiction is proven; the exact stale local JSON was not identified.
- **The 234 closed FUTURES figure** (childlike-airport) — peer-reported; `data/closed_picks.db` is absent, so it was not independently reproduced.
- **v4's 28 vs v2's 25 last-run failures** — retry timing; no single stable number.
- **Browser rendering of date-only rows** (blank vs `Nov 14, 8:06 AM`) — payload semantics verified, UI not rendered.
- **`data/live_picks.db` FOREX=4 / missing `asset_class`** (childlike-airport) — not reproducible: the table has no `asset_class` column and all 129 rows have non-null `current_price`. Different snapshot or inferred from another feed.

---

## 9. Evidence commands (read-only, reproducible)

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict-v2

# (a) KeyError
sed -n '2930,2950p' alpha_engine/scanner.py

# (b) workflow scheduler
grep -n "cron:\|group:\|cancel-in-progress\|timeout-minutes" .github/workflows/audit-dashboard.yml

# (c) python pin
grep -n "update-environment\|python-version" .github/workflows/signal_tracking.yml
grep -rl "update-environment: false" .github/workflows/ | wc -l   # 197

# (d) dead allowlist
sed -n '690,745p' alpha_engine/non_crypto_policy.py
grep -rn "evaluate_non_crypto_candidate" --include=*.py .

# (e) date-only
sed -n '8130,8160p' audit_trail/dashboard_generator.py
sed -n '8345,8356p' audit_trail/dashboard_generator.py
sed -n '445,475p' copy_trader_intel/multi_asset_copytrader_scraper.py
sed -n '735,760p' audit_trail/universal_pick_resolver.py

# payload recounts
python3 - <<'PY'
import json,collections
d=json.load(open('2026-11-14/finpredict-v2_20261114-1602/raw/dashboard_data.json'))
ar=d['picks']['active_raw']
fx=[r for r in ar if (r.get('asset_class') or '').upper()=='FOREX']
fu=[r for r in ar if (r.get('asset_class') or '').upper()=='FUTURES']
print(len(ar),len({r['id'] for r in ar}))
print(collections.Counter(r['status'] for r in fx))
print(collections.Counter(r['status'] for r in fu))
PY
```

**Bottom line:** the plan's diagnosis is sound and its five riskiest citations are exact. Fix the four scope/wording errors (C1-C4) before publishing, add the SQLite/case-normalization/phantom-sweep items, and keep the shadow-before-enforce sequence.
