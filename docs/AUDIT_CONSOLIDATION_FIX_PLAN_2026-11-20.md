# Audit consolidation, fix & test plan — /audit · /audit2 · /audit3 (2026-11-20)

**Author:** deepseek-deepseek-flash-ef6c (Hermes seat, Windows `desktop-081g9oh`, worktree `findtorontoevents_antigravity-ca`)
**Status:** plan for review (docs-only). Nothing here is investment advice; nothing is money-ready.
**Scope:** consolidate the useful theory + live numbers from `/audit`, `/audit2`, `/audit3` into **one source of truth**, list the fixes that make the three pages agree, and give a test plan that fails closed. Reconciled against the work other seats already landed (#985/#994/#995/#996/#997/#998/#999 — single-publisher ledger, audit2 pin, alpha-gate repair).

---

## 0. TL;DR

- The three surfaces are **not** one system. `/audit2` and `/audit3` both render the canonical `audit3_ledger.json`; **`/audit` renders a separate legacy stack** (`dashboard_data.json` + `money_ready_verdict.json` + a dead `strategy_tribunal_latest.json`) and **never reads `audit3_ledger.json`**. That is the consolidation defect.
- The single most important number on all three pages is **negative selection alpha: −0.267 %/pick, 95 % CI [−0.511, −0.025], n = 3,152** — the pick layer *subtracts* value versus direction-adjusted buy-and-hold. It agrees with "0 proven / 0 candidate" across 368 cells.
- The money verdict is stable and matches the user's read: **no strong edge in stocks, crypto, forex, bonds, ETFs, commodities, futures, mutual funds at this time.** The only survivor after honest lag/cost is **ETF tactical allocation as drawdown control, not alpha** (and forward n = 0).
- Data quality is **red**: 22,947 ghost rows (MEMECOIN/meta_strategy) and 94,934 open picks vs 21 active in `trading_picks`. Any ledger that queries `trading_picks` without the quarantine can be contaminated.
- The consolidation is ~70 % done (canonical ledger is now single-published and byte-identical at `/audit3/` and `/audit/data/`). The remaining work is: make `/audit` read the canonical ledger/cohort, kill the dead legacy tribunal panel, unify the doctrine block, and unify the pod manifest.

---

## 1. Verified live state (2026-11-20 ~07:35–07:50 UTC)

### 1.1 Canonical ledger — `audit3_ledger.json`
`generated_at 2026-11-20T07:35:29Z`, `source_generated_at 07:03:17Z`

| Field | Value |
|---|---|
| rows scored | 8,795 |
| cells total / tested | 368 / 67 |
| PROVEN / CANDIDATE / WEAK / KILL / INSUFF | 0 / 0 / 59 / 8 / 301 |
| confirmatory / discovery cells | 8 / 360 |

Class verdicts (from the same ledger):

| Class | Verdict | n | PF | WR |
|---|---|---|---|---|
| CRYPTO | KILL | 6,900 | 0.8283 | 40.09 % |
| EQUITY | WEAK | 943 | 1.0761 | 45.07 % |
| ETF | WEAK | 588 | 1.0003 | 43.03 % |
| FOREX | WEAK | 280 | 0.6641 | 36.43 % |
| COMMODITY | KILL | 45 | 0.1182 | 15.56 % |
| BOND | WEAK | 35 | 0.6538 | 40.00 % |
| FUTURES | INSUFFICIENT_N | 4 | 1.8719 | 50.00 % |

**Selection alpha (M1b):** `n=3,152`, `pick_net −0.2434 %`, `hold_net +0.024 %`, **`alpha −0.2674 %`, CI [−0.5114, −0.0249]`**, `alpha_per_day −2.51 %`, `alpha_annualized −916.6 %`, `alpha_pct_min_hold −0.1131 %`, `min_hold_participation 51.68 %`.

**Coverage / denominator:** canonical kept rows 8,795 of 16,406 closed; excluded `invalid_row 7,405`, `mirror_duplicate 95`, `non_performance_exit 43`, `resolver_breakeven_fallback 68`. The ledger scores the *published canonical view*; `/audit` counts the same rows.

**Forward gate:** enforced. `reports/forward_observations.jsonl` n = 444; **POD-EQUITY-BREAKOUT `n_forward = 0`** ("nothing can promote").

### 1.2 Single-publisher check (already fixed by peers)
`/audit3/audit3_ledger.json` and `/audit/data/audit3_ledger.json` are **byte-identical** (663,832 B each) → the single-publisher change (#994/#998/#999 lineage) is live and working. `/audit2/audit3_ledger.json` is 404, but `audit2.js` `LEDGER_PATHS[0] = ../audit3/audit3_ledger.json` (canonical first) and discloses any fallback copy. **Ledger duplication is resolved; page-level duplication is not.**

### 1.3 `/audit` legacy stack (the divergence)
- `/audit` is a 1.43 MB page (`Unified Audit Dashboard v99.0`). **Zero references to `audit3_ledger.json`.**
- It fetches `data/dashboard_data.json`, `./data/money_ready_verdict.json`, and `./data/strategy_tribunal_latest.json`.
- `/audit/data/strategy_tribunal_latest.json` → **HTTP 404**. `audit_dashboard/template.html:1021` still fetches it; `strategy-tribunal.yml` (weekly, Friday 14:00 UTC) tries to commit it and its own comment admits it never reached main.
- `/audit/data/money_ready_verdict.json` (a *different cohort*) disagrees with the canonical ledger:

| Class | money_ready PF (n_resolved) | audit3 PF (n) | Ratio |
|---|---|---|---|
| CRYPTO | 0.2613 (3,726) | 0.8283 (6,900) | 3.2× |
| EQUITY | 0.5107 (257) | 1.0761 (943) | 2.1× |
| FOREX | 0.2497 (634) | 0.6641 (280) | 2.7× |
| ETF | 1.8227 (53) | 1.0003 (588) | 0.55× |
| COMMODITY | 0.2544 (234) | 0.1182 (45) | 0.46× |

Same class, two profit factors, no shared label on the page → readers cannot reconcile. This is **the** honesty gap.

### 1.4 Data quality — `db_health.json` (06:48Z), tier **red**
- `ghost_rows`: **22,947** across 10 cohorts — all `MEMECOIN / meta_strategy` (DOGE/WIF/PEPE/FLOKI/BONK/SHIB/ORDI), `distinct_entries` 1–4.
- `open_bloat`: `trading_picks` **open 94,934**, active 21, total 147,967, `info_schema_estimate 46,135`; `bt_backtest_trades` open 29,247,197 / total 32,441,049; `last_terminal_write 2026-11-20 04:43`, 2 h since last close.

### 1.5 Money-readiness banner — `audit_surface_truth.json` (04:55Z)
`money_ready_classes: []`, `money_ready_count: 0`, headline "0/9 asset classes money-ready on policy-clean closed picks."

---

## 2. Findings (each with the artifact to falsify it)

**F1 — Two parallel stacks, one canonical.** `/audit2` + `/audit3` read `audit3_ledger.json`; `/audit` reads `dashboard_data.json` + `money_ready_verdict.json` (+ dead `strategy_tribunal_latest.json`). `/audit` has 0 hits for `audit3_ledger`. *Evidence:* live `/tmp/audit.html` (1,437,652 B) grep; `/tmp/l3.json`; `audit_dashboard/template.html:1021,1152`.

**F2 — Denominator divergence shown without labels.** CRYPTO PF 0.26 vs 0.83, EQUITY 0.51 vs 1.08 (§1.3). Both are "true under their own cohort"; presenting them without a cohort label is the defect. *Fix:* one canonical cohort + explicit `cohort_id`/`denominator` on any second view.

**F3 — Dead legacy tribunal.** `strategy_tribunal_latest.json` 404s; template still fetches it; weekly job still tries to publish it. *Fix:* delete the panel or repoint it at `audit3_ledger.json::kill_tribunal`.

**F4 — Pod registry has two sources.** `audit2.js` hardcodes a 6-pod `PODS` fallback while also fetching `audit2_pods.json` (live manifest, 11 pods). A stale fallback can render when the fetch fails. *Fix:* manifest only, or mark the hardcoded list explicitly `STALE SNAPSHOT 2026-11-19`.

**F5 — Negative selection alpha.** −0.267 %/pick, CI excludes 0 (§1.1). This is the honest answer to "did we find edge": the pick layer is a drag. *Fix:* surface it on `/audit` overview, not just `/audit3`.

**F6 — Data-quality red.** 22,947 ghost rows + 94,934 open picks (§1.4). *Fix:* quarantine is correct; the numbers must appear on `/audit` and gate any ledger ingest that reads `trading_picks`.

**F7 — Publisher/cadence sprawl.** 58 audit/pick/forward workflows. The ledger is single-published now, but other sidecars (`money_ready_verdict.json`, `dashboard_data.json`, `audit2_pods.json`) still have multiple potential writers and cadence races. *Fix:* extend the `_PUBLISHED_ELSEWHERE` pattern to every canonical sidecar; one writer per artifact.

**F8 — Money outcome (confirms the user's read).** 0 PROVEN / 0 CANDIDATE across 368 cells; every class WEAK/KILL/INSUFFICIENT. The only surviving result is **ETF tactical allocation as drawdown control** (MaxDD −50.8 % → −31.6 %, ~38 % cut, for ~0.54 %/yr CAGR give-up), and that is **risk control, not alpha**, with forward n = 0. Everything else (crypto directional, forex, commodity, futures day-trading, mutual funds) is KILL/insufficient.

---

## 3. Target architecture — "one source, three views"

```
                     ┌─────────────────────────────────────────────┐
                     │  audit_dashboard/data/audit3_ledger.json     │  ← SINGLE SOURCE OF TRUTH
                     │  (alpha_engine/audit3_tribunal.py)           │     published only by
                     │  summary · classes · cells · symbols ·       │     audit3-ledger.yml
                     │  selection_alpha · forward_gate · doctrine   │
                     └───────────────┬─────────────────────────────┘
                                     │ read-only (no re-derive)
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
  /audit (INDEX)              /audit2 (WHAT TO TEST)       /audit3 (WHAT'S KILLED)
  money-readiness tile        candidate & observe pods      kill tribunal, cells,
  data-quality tile           forward clock, measures       symbols, families
  links to audit2/audit3      doctrine (shared)             doctrine (shared)
```

Rules:
1. **One numbers source:** `audit3_ledger.json`. `/audit2` and `/audit3` are pure renderers (already true). `/audit` must stop computing its own verdicts and read the same ledger for the overview tiles.
2. **One cohort, labelled:** `money_ready_verdict` must derive from the canonical view (`coverage.denominator.mode = canonical`). If a second cohort is kept, it carries `cohort_id` + `denominator` and the page renders both with labels — never two unlabelled PFs for one class.
3. **One doctrine block:** the ledger already embeds `doctrine` + `conventions` + `not_money_ready_disclaimer`. Move audit2's `MEASURES`/`TRAPS`/doctrine prose into `audit_dashboard/data/audit_doctrine.json` and render it from **both** `/audit2` and `/audit3` (one copy, two consumers).
4. **One pod manifest:** `audit2_pods.json` (projection of `reports/audit3_confirmatory.json`) is the only pod source; the JS hardcoded fallback is removed or explicitly labelled stale.
5. **One state snapshot:** generate a small `AUDIT_STATE.md` (counts, parity, freshness, forward n) each ledger run so a reader (or agent) does not have to parse 100+ JSON sidecars to answer "what is true right now".
6. **One writer per artifact:** extend `_PUBLISHED_ELSEWHERE` so `money_ready_verdict.json`, `dashboard_data.json`, `audit2_pods.json`, `audit_surface_truth.json` each have exactly one publisher.

---

## 4. Fix list (prioritized)

### P0 — correctness / honesty (do first)
| # | Fix | Where | Acceptance |
|---|---|---|---|
| P0-1 | `/audit` reads canonical ledger for overview tiles; stop showing a second unlabelled PF | `audit_dashboard/template.html` (add fetch of `../audit3/audit3_ledger.json`; render `summary` + `classes` + `selection_alpha`) | One PF per class on `/audit`; source line names `audit3_ledger.json` |
| P0-2 | Reconcile `money_ready_verdict` to the canonical cohort **or** label it | generator of `money_ready_verdict.json` + `template.html:1152` | CRYPTO PF identical (to 2dp) to ledger, or visibly "cohort=policy-clean, not canonical" |
| P0-3 | Kill the dead legacy tribunal panel | `audit_dashboard/template.html:1021`; `tools/strategy_kill_tribunal.py`; `.github/workflows/strategy-tribunal.yml` | `/audit` has no fetch of `strategy_tribunal_latest.json`; no 404 in console |
| P0-4 | Surface selection alpha + data-quality on `/audit` overview | `template.html` + `db_health.json` render | `/audit` shows α −0.267 %/pick and ghost/open counts |
| P0-5 | Remove/label the hardcoded audit2 pod fallback | `audit2.js` `PODS` (line ~6) | Page renders `audit2_pods.json`; fallback marked `STALE` or absent |

### P1 — consolidation / consistency
| # | Fix | Where |
|---|---|---|
| P1-1 | Extract doctrine/measures/traps into `audit_doctrine.json` consumed by audit2 + audit3 | `audit2.js`, `audit3` template, new `audit_dashboard/data/audit_doctrine.json` |
| P1-2 | One writer per sidecar (extend `_PUBLISHED_ELSEWHERE`) | `.github/workflows/audit-dashboard.yml` `deploy_findtorontoevents()` |
| P1-3 | Emit `AUDIT_STATE.md` each ledger run | `alpha_engine/audit3_tribunal.py` or a small tool |
| P1-4 | Forward-benchmark: pad ingest past exit, backfill 87 null legs, schedule ingest | ingest query (`BENCHMARK_LOOKAHEAD_MS`), `forward-benchmark-ledger.yml` |
| P1-5 | Stamp `at_issue_*` for 100 % of rows (E13); `fx_backfill.py` (E11) | resolver; `tools/fx_backfill.py` |

### P2 — quality of life
| # | Fix |
|---|---|
| P2-1 | Retire unused legacy JSONs (hundreds of dated sidecars) behind one `INDEX` |
| P2-2 | Workflow-concurrency audit: collapse 58 pick/forward workflows into documented groups |
| P2-3 | Add `/audit` "in simple terms" note to every tile (user prefers ELI5) |

---

## 5. Test plan

### 5.1 Unit (fast, no network)
```bash
python -m pytest tests/test_audit3_tribunal.py tests/test_audit3_selection_alpha.py \
                 tests/test_strategy_freeze_gate.py -q
# expect 49 passed (34 + 11 + 4)
```
Add:
- `tests/test_canonical_cohort_parity.py` — assert `money_ready_verdict` PF == ledger PF (2dp) **or** that it carries `cohort_id`/`denominator` and a label. Fails closed if two unlabelled PFs exist for a class.
- `tests/test_audit_no_dead_sidecars.py` — assert no template `fetch()` targets a sidecar absent from `tools/deploy_audit_files.py` UPLOADS (catches `strategy_tribunal_latest.json`).
- `tests/test_audit2_no_hardcoded_pods.py` — assert `audit2.js` does not ship an unlabelled `PODS` fallback, or that it contains `STALE SNAPSHOT`.

### 5.2 Contract / schema
```bash
python -m pytest tests/test_audit_dashboard_payload.py tests/test_dashboard_payload_contract.py \
                 tests/test_money_ready_verdict_strict_json.py tests/test_audit_metric_invariants.py -q
```
- Ledger schema `audit.canonical.v1` present; `summary`, `classes`, `selection_alpha`, `forward_gate`, `doctrine` all present.
- `selection_alpha.overall.alpha_ci` excludes 0 (or the page says "no edge").

### 5.3 Live parity (post-deploy)
```bash
# byte parity: canonical ledger served from two paths
curl -s https://findtorontoevents.ca/audit3/audit3_ledger.json | sha256sum
curl -s https://findtorontoevents.ca/audit/data/audit3_ledger.json | sha256sum   # must equal
# dead-panel scan: every fetch target returns 200
for u in strategy_tribunal_latest.json hypothesis_registry.json money_ready_verdict.json db_health.json; do
  curl -s -o /dev/null -w "%{http_code} $u\n" "https://findtorontoevents.ca/audit/data/$u"
done
# HTTP 200 on all three surfaces
for p in audit audit2 audit3; do curl -s -o /dev/null -w "%{http_code} /$p/\n" "https://findtorontoevents.ca/$p/"; done
```

### 5.4 End-to-end (Playwright / existing specs)
```bash
npx playwright test tests/audit-pages.spec.ts tests/audit_post_deploy_validation.spec.ts \
                     tests/audit_live_js_errors_spec.ts
```
Assertations:
- No console errors on `/audit`, `/audit2`, `/audit3`.
- `/audit` overview shows one PF per class and names its source.
- `/audit2` renders `audit2_pods.json` and shows the served ledger path.
- `/audit3` renders 0 proven / 0 candidate / 59 weak / 8 kill for the current ledger.

### 5.5 CI gates (block merge on fail)
- `tribunal-runtime-gate.yml` (already live, PR #999) — fail if `audit3_tribunal.py` crashes on the live payload.
- New `audit-parity-gate.yml` — runs §5.1–5.3 on PRs touching `audit_dashboard/`, `alpha_engine/audit3_*`, `.github/workflows/audit*`.
- `strategy_freeze_gate.py` must stay exit-1 while P0 items are open.

### 5.6 Data-quality gate
```bash
python - <<'PY'
import json,urllib.request
d=json.load(urllib.request.urlopen("https://findtorontoevents.ca/audit/data/db_health.json"))
assert d["checks"]["ghost_rows"]["data"]["tier"] in ("green","yellow"), "ghost rows still red"
assert d["checks"]["open_bloat"]["data"]["open_bloat"]["fail"] is False, "open bloat still red"
print("db quality OK")
PY
```

---

## 6. Money-worthiness — the honest verdict (matches the user's read)

- **No strong edge found** in stocks, crypto, forex, bonds, ETFs, commodities, futures, or mutual funds. 0 PROVEN / 0 CANDIDATE across 368 cells.
- **Selection alpha is negative** (−0.267 %/pick, CI excludes 0): the pick layer underperforms holding. This is the number to lead with.
- **Only survivor:** ETF tactical allocation **as drawdown control** (MaxDD roughly halved for ~0.54 %/yr CAGR give-up), corrected after honest 1-day lag (the original "Sharpe 0.88" claim was retracted). That is **risk control, not alpha**, and forward n = 0.
- **Crypto** is the right *paper* sandbox (24/7, best data), directional picks are KILL. **Forex/commodity/futures day-trading** fail every gate. **Mutual funds** have n = 0. **$0 real capital** until a pod clears the forward gate (n ≥ 100, net PF CI-LB > 1.0, 100 % intrabar honest, ≥ 90 % benchmark coverage).
- Databases: GoDaddy MySQL (`mysql.50webs.com`), databases `ejaguiar1_{stocks,backtests,sportsbet,events,news,deals,backups,memecoin,favcreators,tvmoviestrailers}`; credentials belong in `Desktop/dbpasses.txt` and must **never** be committed or put on COMS. The audit stack reads `ejaguiar1_stocks` (`at_*`, `bt_*`, `trading_picks`).

---

## 7. Open decisions (owner)
1. Keep a second (policy-clean) cohort for `money_ready_verdict`, or collapse everything to the canonical cohort? (Recommend collapse; if kept, label it.)
2. Delete the legacy tribunal panel outright, or repoint it at `audit3_ledger.json::kill_tribunal`? (Recommend delete; canonical already has a kill tab.)
3. Promote `audit_doctrine.json` as the single doctrine file (audit2 + audit3), or keep prose in each page? (Recommend the file.)
4. Retire the weekly `strategy-tribunal.yml` now that audit3-ledger is canonical? (Recommend yes.)

---

## 8. References
- Canonical generator: `alpha_engine/audit3_tribunal.py`; ledger `audit_dashboard/data/audit3_ledger.json`.
- Legacy: `tools/strategy_kill_tribunal.py`; `.github/workflows/strategy-tribunal.yml`; `audit_dashboard/template.html:1021`.
- Deploy: `tools/deploy_audit_files.py`; `.github/workflows/audit-dashboard.yml` (`10 */3`); `.github/workflows/audit3-ledger.yml`.
- Prior context: `COMS_AUDIT2_3_HANDOFF_2026-11-19.md`, `reports/money_maker_per_asset_class_2026-11-19.md`, `updates/2026-11-20-single-publisher-audit3-ledger.md`, `AUDIT_BLUEPRINT.md`.
- Peers landed: #985, #994, #995, #996, #997, #998, #999.
