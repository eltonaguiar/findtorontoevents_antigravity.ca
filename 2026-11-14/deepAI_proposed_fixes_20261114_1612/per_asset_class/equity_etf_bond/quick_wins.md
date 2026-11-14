# EQUITY / ETF / BOND (+ mutual funds) — Quick Wins
Scope: findtorontoevents.ca/audit non-crypto prediction surfaces. Base commit verified: `.inspect-wt` HEAD `464035ff56` (worktree base `f54efb3b4a`, confirmed via `git rev-parse`). All file:line anchors below were grep-verified to exist at this base. Live numbers cite JSON paths under `.inspect-wt/_audit_tmp/`.
Date: 2026-11-14.

**Rule of the doc:** every claim carries `file:line` or `JSON path`. Anything I could not confirm at this base is tagged `UNVERIFIED`. Each quick win ends with a `PASS/FAIL:` line.

---

## Established findings this doc builds on (not re-derived)

- BOND dead-but-displayed: `evidence_live_audit.json` `.active_raw_by_class.BOND` = n:15, all OPEN, newest_h 25.4; `.recent_closed_by_class.BOND` = n:35, newest_h 98.1; `live_money_ready.json` `.classes.BOND` n_resolved=1, policy_frozen=true.
- ETF surface contradiction: `live_pf_registry.json` `.by_asset_class[] ETF` n=15 PF 1.84055 vs `live_money_ready.json` `.classes.ETF.intrabar_truth` n=45 WR 0.0222 PF 0.0216 vs `live_dashboard_data.json` `.picks.recent_closed` ETF n=567 (WON 250 / LOST 317 → WR 44.1%).
- EQUITY registry PF 0.706803 (n=493) vs money_ready intrabar PF 0.9392 (n=250) vs 14d window PF 1.2 (n=53, `closed_stats.json` `.EQUITY."14d"`).
- Mutual funds vaporware: `alpha_engine/mutual_fund_ranker.py` does not exist (verified `ls`); zero MUTUAL rows in `live_dashboard_data.json` (regex count = 0).
- STOCKS/EQUITY label split: phantom empty `STOCK` bucket present in live payload (`live_dashboard_payload.json` `summary.non_crypto_performance.categories.STOCK` = all zeros, adjacent EQUITY closed=759).

---

## QW1 — Kill the phantom STOCK bucket; unify STOCKS/STOCK → EQUITY

**(a) Anchors (verified):**
- `audit_trail/dashboard_generator.py:6561-6563` — `_NC_ASSET_CLASSES = frozenset({"FOREX","EQUITY","STOCK","COMMODITY","FUTURES","ETF","BOND"})` (contains both EQUITY and STOCK).
- `audit_trail/dashboard_generator.py:6565` — `_NC_ALIAS_MAP` maps `"STOCKS": "STOCK"`.
- `audit_trail/dashboard_generator.py:13935` — `compute_non_crypto_performance()` `categories = ("FOREX","EQUITY","STOCK","COMMODITY","FUTURES","BOND","ETF")` — the STOCK bucket is emitted even when empty.
- Live proof: `live_dashboard_payload.json` `summary.non_crypto_performance.categories.STOCK` = `{active:0, closed:0, ..., total_pnl_pct:0.0}` while `categories.EQUITY.closed=759`.
- The sibling map used for closed-pick track-record reservation is already correct: `audit_trail/dashboard_generator.py:5444` `_NON_CRYPTO_ASSET_CLASSES = {"EQUITY","ETF","FOREX","FUTURES","COMMODITY","BOND"}` (no STOCK/STOCKS) — so a row tagged `STOCKS`/`STOCK` that reaches `_should_reserve_closed_pick_for_track_record` (line 6568-6570 path) is silently NOT reserved as non-crypto. Two parallel maps disagree.

**(b) Minimal change** (in `quick_wins.patch`, hunk 1): remove `"STOCK"` from `_NC_ASSET_CLASSES`; change `"STOCKS": "STOCK"` → `"STOCKS": "EQUITY"` and add `"STOCK": "EQUITY"`; after the `classify_asset` fallback in `nc_asset_category_for_pick` (line ~6695) pass `val` through the same alias map; drop `"STOCK"` from the `categories` tuple at 13935 and make the two `stats[cat]` increments defensive (`stats.setdefault(cat, _blank_bucket())` at lines ~13948/13952 so an un-mapped category can never KeyError-crash the build).

**(c) Expected effect:** payload stops emitting the zero `STOCK` bucket; any future row tagged `STOCK`/`STOCKS` lands in EQUITY stats on all three paths (nc-category stats, per-asset quality summary `_normalize_per_asset_class` at :6587-6595 which already maps to EQUITY, and `_NON_CRYPTO_ASSET_CLASSES` track-record reservation). Label split fully collapses to one canonical name.

**(d) Risk:** low. Zero live rows carry `STOCK`/`STOCKS` as asset_class (payload scan: `"STOCK"` appears exactly once — the phantom bucket key). Template `template.html:6265-6270` STOCK-merge special-case becomes inert but harmless. Must update the test that pins the old behavior: `tests/test_orphan_emitter_wire.py:119` asserts `out["asset_class"] == "EQUITY"` for an ETF-tagged row (see QW2 — same patch fixes both).

**PASS/FAIL: PASS** (anchors verified at base; no live row regressions possible).

---

## QW2 — orphan_emitter_etf stamps missing asset_class as EQUITY, not ETF

**(a) Anchors (verified):**
- `audit_trail/dashboard_generator.py:8562` — `_ORPHAN_EMITTER_ASSET_CLASS = {"orphan_emitter_bond":"BOND", "orphan_emitter_etf":"EQUITY",  # ETFs roll up to EQUITY in the dashboard`, ...}`.
- `audit_trail/dashboard_generator.py:4062-4063` — `ORPHAN_EMITTER_SOURCES` entry `("orphan_emitter_etf","non_crypto_agent/data/etf_picks.json", None, "EQUITY")`.
- Consumed at `:8582` `inferred_ac = _ORPHAN_EMITTER_ASSET_CLASS.get(source_system)` inside `_normalize_orphan_emitter_pick`, applied at `:8607` `if inferred_ac and not raw.get("asset_class"): raw["asset_class"] = inferred_ac`.
- The emitter really does omit asset_class: `.github/workflows/etf-agent.yml:85-96` builds `picks` from 4 strategy fns + `compute_elite_score(p)` — no `asset_class` field anywhere (grep = 0 hits in emit path; contrast bond-agent.yml:292 which stamps `p["asset_class"] = "BOND"`).
- Test pinning the wrong value: `tests/test_orphan_emitter_wire.py:113-119` `test_normalizer_fills_asset_class_for_etf_and_futures` asserts `== "EQUITY"`.

**(b) Minimal change** (patch hunk 2): `:8562` and `:4063` `"EQUITY"` → `"ETF"`; update the test to assert `"ETF"`. Rows that self-tag keep their own tag (idempotent by design, `:8605-8607`).

**(c) Expected effect:** every future orphan-emitter ETF pick missing asset_class is classified ETF → counted in the ETF nc-card, ETF money_ready cohort and ETF policy-clean ingest instead of diluting EQUITY (EQUITY registry n=493 currently carries cross-label noise while ETF policy-clean sits at n=15).

**(d) Risk:** low. No live rows currently from `orphan_emitter_etf` (payload scan: `orphan_emitter_etf` appears 0 times in active_raw sources; EQUITY active_raw sources are stocks_competition/ueps/penny_screener/kimi/stocksunify2/...). Only fires when the etf-agent emits.

**PASS/FAIL: PASS** (behavior change limited to previously-empty source).

---

## QW3 — BOND/ETF nc-card staleness + FROZEN badge (BOND shows PF/WR from a 98h-old closed cohort with no marker)

**(a) Anchors (verified):**
- `audit_dashboard/template.html:6232-6237` — nc-card `categories` array includes `{key:'BOND'...}`.
- `audit_dashboard/template.html:6321` — `if (serverActiveCount === 0 && serverClosedCount === 0) continue;` — BOND renders (closed=35) with WR 34.3% / PF from `audit_trail/dashboard_generator.py:13935-13975` stats, with **no staleness signal** even though `.recent_closed_by_class.BOND.newest_h = 98.1` (evidence_live_audit.json).
- Server stats builder has no age field today: `audit_trail/dashboard_generator.py:13952-13960` (closed loop tracks only counts/pnl).
- FROZEN already exists on the headline banner but not on the cards: `template.html:997` `frozenBadge` driven by `money_ready_verdict.json` `classes[cls].policy_frozen` (live: `.classes.BOND.policy_frozen = true`); the freeze itself is `audit_trail/quality_gates.py:1726` `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}` with the 2026-06-03 BOND freeze comment at :1730-1732.

**(b) Minimal change** (patch hunks 3a/3b): in `compute_non_crypto_performance` closed loop, track `bucket["newest_closed_age_hours"] = min(existing, pick age)` from `pick.get("age_hours")` (fallback: now − `closed_at`); in template nc-card render (~6323, right after `hasAnyData = true`), if `serverCat.newest_closed_age_hours > 72` render a grey badge `⏸ newest closed ${Xh} ago` before WR/PF, and additionally render `🍦 FROZEN` when `moneyReadyClasses[cat.key]?.policy_frozen === true` (reuse the already-fetched `mv` object from `template.html:976` — hoist to a module var in the same hunk).

**(c) Expected effect:** BOND card reads "⏸ newest closed 98.1h ago · 🍦 FROZEN" instead of silently presenting PF/WR from a stale, operator-frozen cohort. ETF card shows staleness only if it ever goes >72h (today newest closed 25.8h — no badge).

**(d) Risk:** low, template + additive server field only; if `mv` fetch fails the badge simply doesn't render (existing `.catch` at :1023 leaves spans intact).

**PASS/FAIL: PASS.**

---

## QW4 — Headline banner: disclose intrabar-vs-daily divergence on ETF/EQUITY lines

**(a) Anchors (verified):**
- `audit_dashboard/template.html:976-1025` — JS auto-update rewrites each `[data-mg-class]` span with live `money_ready_verdict.json` stats (PF/WR/n at `:1012-1014`). For ETF the live line currently renders "INSUFFICIENT DATA (PF 0.02, WR 2.2%, n=45)" — the poisoned intrabar subset — with no hint that the same JSON's daily cohort says PF 1.84 n=15.
- The JSON already carries the discriminator: `live_money_ready.json` `.classes.ETF.intrabar_daily_divergence = {daily_pf:1.8358, honest_pf:0.0216, pf_inflation_x:84.99, flag:true}` (writer is post-base code — `UNVERIFIED at f54efb3b4a`; the JSON fields are the verified artifact). EQUITY flag also true (pf_inflation_x 1.38).

**(b) Minimal change** (patch hunk 3c): inside the money_ready span renderer (~line 1010), if `c.intrabar_daily_divergence && c.intrabar_daily_divergence.flag === true` append badge `⚠ DAILY/INTRABAR DIVERGENT (daily PF X vs honest Y)` with a tooltip citing `pf_inflation_x`.

**(c) Expected effect:** nobody can quote "ETF PF 0.02" from /audit without seeing the contradiction; EQUITY similarly flagged (1.38×).

**(d) Risk:** minimal, template-only; badge is additive, static forensic snapshot already preserved in `<details>` (`:1016-1018`).

**PASS/FAIL: PASS.**

---

## QW5 — Pause BOND emission while the class is operator-frozen (bond-agent crons into a -60 wall daily)

**(a) Anchors (verified):**
- `.github/workflows/bond-agent.yml:8-11` — `schedule: cron: '32 14 * * 1-5'` (weekday 14:32 UTC), stamps `p["asset_class"] = "BOND"` at :292.
- The freeze that makes those emissions inert: `audit_trail/quality_gates.py:1726` `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}` + `:4107-4109` score −60 per BOND pick; freeze rationale at :1730-1732 (BOND 2026-06-03 freeze, live PF 0.37; bypass = paper-only 60d HYG/LQD).
- Net effect live: BOND rows appear only in `active_raw` (n=15, all ~25h old — evidence_live_audit.json), never in `picks.active` (0 BOND rows there); `live_money_ready.json` `.classes.BOND.n_resolved = 1`, policy_frozen true. The daily agent run is pure zombie inventory.
- The alternate daily scanner is already disabled: `.github/workflows/alpha-engine-bond.yml.disabled:17` (cron commented out / file disabled) — precedent exists for parking a BOND workflow.

**(b) Minimal change** (patch hunk 4): comment the `cron:` line in `bond-agent.yml` with a `# FROZEN 2026-06-03 — re-enable when BOND leaves quality_gates.BLOCKED_ASSET_CLASSES (see paper-only bypass gate in proposed_fix.md §B)` note. Keep `workflow_dispatch` so it can be run manually.

**(c) Expected effect:** active_raw stops accumulating ~5 dead BOND rows/day (bond_scanner 6 + alpha_engine 5 + orphan_emitter_bond 4 currently); DB ingest, resolver load and the raw-pool "Show All Picks" view all shrink. Zero impact on picks.active (already 0 BOND).

**(d) Risk:** low & reversible (un-comment one line). Only risk is forgetting to re-enable — mitigated by the BOND restart-or-retire gates in proposed_fix.md §B which require the freeze lift first.

**PASS/FAIL: PASS** (emissions are provably filtered before any active surface).

---

## QW6 — funds.html: red-flag the data-age indicator when the feed is stale

**(a) Anchors (verified):** `audit_dashboard/funds.html:1353-1358` — computes `age` from `D.generated_at` and writes `data-age` text but never warns; `:213` renders `<span id="data-age">`. funds.html is FTP-deployed by 4+ workflows (`.github/workflows/audit-dashboard.yml:1045`, `deploy-competition-to-site.yml:101`, `deploy-riseoftheclaw.yml:469/521`) so a frozen feed can sit on the site with a benign "Xh ago" reading.

**(b) Minimal change** (patch hunk 5): at `:1358`, if `mins > 120` set the span color to `var(--red)` and text `⚠ Xh ago (stale)`.

**(c) Expected effect:** stale "Strategy Funds" surface is self-evidently stale; matches the honesty pattern already used in the main template (recency STALE badge at `template.html:1001-1002`).

**(d) Risk:** trivial. **PASS/FAIL: PASS.**

---

## QW7 — FWD WR / FWD N liveness check for EQUITY rows (verification result: fields are live strategy-level aggregates; no defect)

**(a) Anchors (verified):**
- Writer: `audit_trail/dashboard_generator.py:15813-15815` — every pick gets `strat_fwd_wr/strat_fwd_pf/strat_fwd_trades` from the leaderboard row each build; sparse-row ML-group fallback at :15805-15811; universal-forward sync fallback at :16095-16103.
- At-issue freeze already exists: `:333-338` stamps `at_issue_strat_fwd_wr` so later rebases can't rewrite history.
- Live check (`live_dashboard_data.json` `.picks.recent_closed` EQUITY): all 738 rows carry non-null `forward_wr`/`forward_trades`/`strat_fwd_wr`; mean fwd WR 44.7%, median fwd_n 83; even a 47.7h-old pick shows fwd_n=115 — proving these are **strategy-level** aggregates, as documented for users at `audit_dashboard/template.html:1652` ("FWD WR = pick.strat_fwd_wr ... N = strat_fwd_trades") and gated at `:3513/:3525-3528`.

**(b) Change:** none required. Optional polish (defer): add "(strategy-level)" to the FWD WR column header. Not filed as a fix.

**(c/d):** n/a. **PASS/FAIL: PASS (verified liveness, no change shipped).**

---

## QW8 — Static BOND banner text ("at_raw_picks: 78 rows") staleness (verification result: already handled by the live auto-updater; no defect)

**(a) Anchors (verified):** `audit_dashboard/template.html:908` static span says "BOND — ACCUMULATING (at_raw_picks: 78 rows, up from 2)" (live raw count is 15); but `template.html:976-1025` replaces the span content every page load from `money_ready_verdict.json` (BOND included in the class list at :981) and preserves the dated static text inside a `<details> "Forensic snapshot"` block (`:1016-1018`). The correct FROZEN badge path exists (`:994-997`).

**(b) Change:** none. **PASS/FAIL: PASS (no change shipped).**

---

## ETF window puzzle: why money_ready n=45 / WR 2.2% vs recent_closed n=567 / WR 44.1% (root-cause note feeding the proposed fix)

Three disjoint ingest universes for one label:
1. `live_dashboard_data.json` `.picks.recent_closed` ETF n=567 — 557/567 from `source_system=kimi_riseoftheclaw` (scanner at `KIMI_RISEOFTHECLAW/live_scanner.py:468-476` STOCKS_ETF universe; no asset_class field of its own — classified by symbol at `audit_trail/dashboard_generator.py:3494-3503`).
2. `live_pf_registry.json` ETF n=15 — `top_source: file:mysql:at_pick_outcomes`, i.e. the resolver/registry closed-picks ingest (`audit_trail/universal_pick_resolver.py:849-876` writes `at_pick_outcomes`).
3. `live_money_ready.json` `.classes.ETF` n_resolved=45 — `top_source: etf_scanner` share 1.0 (`data_source: dashboard_fallback`), i.e. only `alpha_engine/etf_scanner.py:276`-tagged rows made the intrabar cohort. The n=45 sits right at the 14d-window scale (`closed_stats.json .ETF."14d".n = 43`).

So money_ready's ETF "honest truth" is gated on a 45-row etf_scanner-only subset, and that subset's WR collapsed to 2.2% while the same class resolves 39.5% WR on daily closes over the same period. The mechanism (verified in resolver code at this base, applied to whichever writer inherits it):

- `audit_trail/universal_pick_resolver.py:1003-1049` — intrabar OHLC cache prefetches only symbols found in the **current active feeds**; yfinance window is `period="5d", interval="1h"` (:485).
- `:558-596` `_check_tp_sl_intrabar` replays the bar list **from the oldest bar** and never filters bars to the pick's entry timestamp — bars don't even carry timestamps (yfinance path `:502-510` keeps only open/high/low/close/volume; Binance path `:537-548` **discards `k[0]` open_time**).
- `:1231-1252` — the resolver clamps every pick's TP into 2-4% and SL into 1-2.5% before replay. For a LONG ETF pick entered intraday, the 5-day pre-entry bar window almost always contains a low ≤ (entry × 0.975-0.99): the pick resolves `SL_HIT` off **pre-entry** wicks. 2 survivors out of 45 = 2.2% WR. Equity picks escape partially because their native SL (~5-8%, cf. `etf-agent.yml:103-107` "stock TP/SL (8%/5%)") is wider than the ETF-scale SLs.

Full fix → `proposed_fix.md` (entry-time-anchored intrabar replay). `UNVERIFIED at base`: the writer of `at_signal_outcomes.intrabar_*` columns (no match for `intrabar_truth`/`sizing_source` anywhere in this tree) — the code mechanism above is verified at f54efb3b4a; the production writer is on a newer origin/main.

## Mutual funds — honest-options spec

Moved to `proposed_fix.md` §C as requested (remove-from-UI vs implement-ranker decision with the Vanguard universe anchor `multi_asset/portfolio_defs.py:674-699`).
