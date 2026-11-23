# Consolidated audit / audit2 / audit3 plan + test plan

**Author:** Kilo, worktree `vanilla-handsaw`, 2026-11-20T07:5xZ.
**Scope:** consolidate what the three public surfaces (`/audit`, `/audit2`, `/audit3`) actually
say, name one source of truth, and give a ranked fix list where every item has a test plan.
**Rule:** every number below was read from a live artifact or the code on `origin/main` at the
time of writing. Where something is unverified it is labelled unverified.

---

## 1. Measured current state (2026-11-20T07:35Z)

| Surface | HTTP | Data source | Notes |
|---|---|---|---|
| `/audit/` | 301 → `index.html` 200 | `dashboard_data.json` + sidecars | publishing dashboard |
| `/audit2/` | 301 → `index.html` 200 | `audit3_ledger.json`, `audit2_forward.json`, `audit2_pods.json` | candidate/methodology library |
| `/audit3/` | 301 → `index.html` 200 | `audit3_ledger.json`, `status.json` | kill tribunal + forward gate |

Canonical ledger, both copies fetched live and byte-identical (663,832 bytes, same
`generated_at`):

```
/audit3/audit3_ledger.json     http=200  generated_at 2026-11-20T07:35:29.619043+00:00
/audit/data/audit3_ledger.json http=200  generated_at 2026-11-20T07:35:29.619043+00:00
```

Ledger book (live):

```
coverage.denominator.mode            canonical
canonical_kept_rows                  8,795
scored_rows / valid_closed_picks     8,795 / 8,795   (scored_share_of_valid_pct 100.0)
total_closed_picks                   16,406   (scored_share_of_total_pct 53.61)
verdicts                             PROVEN 0 · CANDIDATE 0 · WEAK 59 · KILL 8
kill classes                         CRYPTO, FOREX, COMMODITY
window                               2026-02-17 … 2026-11-20T06:30:44Z
```

Public status contract (`/audit3/status.json`, age 0.01h, `stale false`):

```
coverage {mode canonical, scored 8795, total 16406, valid 8795}
verdicts {proven 0, candidate 0, weak 59, kill 8}
forward  {rows 444, enforced true, eligible_pods 0}
```

Forward clock (`/audit2/audit2_forward.json`, same `generated_at`):

| hypothesis | n_forward | net PF CI-LB | IR | benchmark coverage | eligible |
|---|---|---|---|---|---|
| H-119 (crypto momentum) | 430 | 0.9213 | 0.0429 | 0.798 | no |
| H-2026-11-19-03 (POD-FABER-TAA) | 12 | 0.0 | −0.5831 | 0.75 | no |
| H-2026-11-19-06 (POD-ETF-DUAL-MOMENTUM) | 1 | — | — | 1.0 | no |

`audit2_pods.json`: 11 pods; `POD-EQUITY-BREAKOUT` is `pre_registered` with 0 rows because its
four strategies (`donchian-stock-breakout`, `rs-breakout-scout`, `vol-contraction-scout`,
`adx-trend-scout`) never emit — confirmed by `updates/2026-11-20-kilo-final-session-notes.md` B1.

Code facts checked on `origin/main`:

- `alpha_engine/audit3_tribunal.py` contains **no drawdown code at all** (0 hits for
  `drawdown`/`max_drawdown`) → the F1 "arithmetic-sum drawdown" fix is **still open**.
- `MATERIALITY_COST_FRACTION = 0.5` exists (cost-scaled materiality floor) → F2 is partly
  present; the "cost-floor base" wording in the handoff is not a distinct shipped constant.
- `tools/assert_surface_parity.py` **does not exist** (only `tools/assert_tribunal_runs.py`) →
  the /audit vs /audit3 parity RED finding has a docs fix but **no hard CI test**.
- `audit3_verdict_history.json` is written by `audit3-ledger.yml` (`--history-write`) and the
  deploy pipeline — a second publisher remains (open item 2 from the handoff).
- `audit2.js` `LEDGER_PATHS` is pinned canonical-first and self-discloses `LEDGER_SERVED_FROM`
  → the unpinned-ledger finding is fixed in code.
- `alpha_engine/forward_observations_ingest.py` wires strategy-keyed conditions for
  `etf_faber_tactical` (H-2026-11-19-03), `etf_dual_momentum` (H-2026-11-19-06),
  `contango_roll_yield` (H-2026-11-19-05) → the wire-emitting-pods finding is fixed.

---

## 2. Single source of truth — target architecture

The three surfaces should not be three populations. Target:

1. **One ledger:** `audit3_ledger.json` is the only scored population. Publish the *same bytes*
   to `/audit3/`, `/audit2/`, `/audit/data/`; never let a copy diverge.
2. **One status contract:** `audit3/status.json` is the only freshness/verdict summary; every
   surface reads it (or renders from the same ledger), never recomputes a conflicting number.
3. **One forward clock:** `forward_clock.json` + `audit2_forward.json` are views of
   `reports/forward_observations.jsonl`, one gate implementation (`alpha_engine/forward_validator.py`).
4. **One hypothesis registry:** `reports/hypothesis_registry.json` (108 hypotheses) is the only
   place a pod/strategy gets pre-registered. No pod without a registry id.
5. **One parity assertion in CI:** a script that fails the build if the copies differ, if the
   ledger is stale, or if `/audit2` renders a different population than `/audit3`.

Today: items 1 and 3 are close, item 2 exists, item 4 exists, **item 5 is missing**.

---

## 3. Consolidated findings / theories (the useful stuff)

### 3.1 What the data says about money (the honest stance)

- **Selection alpha is negative.** −0.2674%/trade, 95% CI [−0.5114, −0.0249], n=3,152
  (verified in `updates/2026-11-20-coverage-denominator-reconciliation.md` context and the
  G9 gate). Our picks currently subtract value vs direction-adjusted buy-and-hold.
- **0 PROVEN / 0 CANDIDATE** out of 359 cells (277 scored strategies). 59 WEAK, 8 KILL.
- **CRYPTO = KILL** (n≈6,740, PF 0.84), **COMMODITY = KILL**, **FOREX = KILL**; EQUITY/ETF/BOND
  WEAK; FUTURES insufficient-n.
- **ETF tactical rotation claim RETRACTED** (`reports/money_maker_per_asset_class_2026-11-19.md`
  §0): "Sharpe 0.88 vs SPY 0.74" reproduces only at same-close. Honest 1-day lag: Sharpe 0.82 vs
  0.69, **CAGR 8.94% vs SPY 10.79%**; 0/576 pre-registered cells clear Sharpe ≥0.88 and MaxDD
  ≥−19%. What survives is **drawdown control** (−50.78% → −31.61%, a 38% cut for ~0.54%/yr CAGR)
  = risk control, not alpha.
- **Uncorroborated /audit sleeves** (`Multi-Timeframe Trend Alignment` 87% WR PF 11.8, etc.):
  post-hoc survivor display from MySQL `at_pick_outcomes`, not scored by the tribunal. Now
  badged "UNVERIFIED (not in audit3)" via `audit3_verdict`/`tribunal_corroborated`.
- **Base rates:** Brazil futures day traders 97% lose; Taiwan −23.9bp/day net; published
  anomalies decay 26–58% post-publication.

**Verdict:** no strong money-worthy asset class found yet. Real money = low-cost index beta only.
Short-term trading = paper only, until a pod clears the forward gate (n≥100, net PF CI-LB > 1.0,
100% intrabar honesty, ≥90% benchmark coverage). This matches the user's own reading: nothing
strong in any asset class so far.

### 3.2 Surviving theories worth forward-testing (from /audit2 doctrine + external research)

| Edge | Class | Status | Why it is still alive |
|---|---|---|---|
| Trend / dual-momentum rotation (Faber 10-mo SMA) | ETF | risk-control only | 20y in-repo evidence; drawdown cut survives honest lag |
| Time-series momentum 1–4wk | CRYPTO | paper | 3 pre-registered slots ticking (H-2026-11-19-01/-02/-07) |
| Breakout continuation | EQUITY/ETF | WEAK cluster | best WEAK cluster; needs real emitters (B1) |
| Low-turnover 12-1 momentum | EQUITY | plausible | survives costs per external research |
| Maker-side only | Prediction markets | structural | Kalshi maker 1.75% vs taker ~7%; any live expression must be maker-only |
| Funding carry | CRYPTO | not worth building | compressed to ~2.7–6%/yr pre-fee ≈ $0–80/yr on $2k |

### 3.3 Consolidated open findings (ranked)

| # | Finding | State | Fix owner |
|---|---|---|---|
| F1 | arithmetic-sum drawdown (no drawdown code in tribunal) | **open** | alpha_engine |
| F2 | cost-floor base wording | partly present (0.5×cost materiality) | alpha_engine |
| P0-1 | /audit vs /audit3 parity: docs fixed, no hard test | **open** | CI |
| P0-2 | `audit3_verdict_history.json` second publisher | **open** | deploy/audit3-ledger |
| P1-4 | 15/23 manifest strategies emit nothing | **open** | pod manifest |
| P1-5 | H-119 benchmark coverage 0.798 < 0.90 | **open** (needs DB creds + price joins) | data |
| P1-6 | B1 POD-EQUITY-BREAKOUT phantom (0 rows) | **open** | registry |
| P2-7 | FX backfill 15 pairs × 203d | **open** (needs DB creds) | data |
| P2-8 | sleeve gate replay `rankable=false` | PR #983/#985 in flight | buffy |
| P2-9 | parity assertion doesn't check /audit2 | **open** | CI |
| P2-10 | FMP key rotation removed from template | **blocked on human** | operator |

---

## 4. Database + GHA dependency map

Credentials live in `/home/eaguiar2015/dbpasses.txt` (**never read or expose contents** —
per project constraint). Schema inventory: `docs/FINANCE_DB_SCHEMA_SPEC.md`.

| DB | Tables | Role in the audit surfaces |
|---|---|---|
| `ejaguiar1_stocks` | 409 | canonical pick ledger: `trading_picks` (~147k rows, `strategy`/`symbol`/`status`/`pnl_pct`), `at_raw_picks` (~113k), `at_pick_outcomes` |
| `ejaguiar1_backtests` | 10 | `bt_backtest_runs` + trade-level results (B1 emitter check, NZDUSD=X mislabel) |
| `ejaguiar1_memecoin` | 58 | crypto scans/signals/paper trades |
| `ejaguiar1_sportsbet` | 49 | sports bankroll/bets (not scored by audit3) |
| `ejaguiar1_backups` | 414 | point-in-time archive |

GHA pipelines that populate the surfaces (schedules read from `origin/main`):

| Workflow | Schedule | Feeds |
|---|---|---|
| `audit3-ledger.yml` | `23 */6 * * *` | `audit3_ledger.json`, verdict history, persistence |
| `forward-observations-ingest.yml` | `41 */6 * * *` | `reports/forward_observations.jsonl` → forward clock |
| `audit-dashboard.yml` | `10 */3 * * *` | `dashboard_data.json` + `/audit` pages |
| `audit-hourly-update.yml` | `19 * * * *` | `/audit` refresh |
| `audit3-health.yml` | `20 5,17 * * *` | ledger freshness alarm (12h warn / 24h fail) |
| `audit3-denylist-watchdog.yml` | daily | denylist staleness (3-day fail) |
| `alpha-engine-live.yml` | hourly-ish | denylist hits + live picks into `trading_picks` |
| `crypto-intraday-sim.yml` | 30-min | crypto paper pilot → forward observations |

**Consolidation point:** the ledger's `coverage` block is computed from the publishing
dashboard's canonical view (`audit.canonical.v1`, sha256 `03d6e350cec3…`). Any fix that changes
the canonical slice must update that sidecar, not just the ledger.

---

## 5. Ranked fixes with test plans

Every test below is runnable locally without DB creds unless marked.

### P0-1 — Hard parity + freshness assertion in CI
**What:** add `tools/assert_surface_parity.py` that (a) requires the two live ledger copies to be
byte-identical, (b) requires `status.json.stale == false`, (c) fails if `audit2.js` renders a
population different from `/audit3`.
**Test plan:**
```bash
python3 tools/assert_surface_parity.py --ledger /tmp/a.json --ledger /tmp/b.json --status /tmp/s.json
pytest tests/test_audit3_cli_smoke.py tests/test_audit3_ledger_e2e.py -q
```
**Expected:** exit 0 when copies match and status is fresh; non-zero with a named path on drift.

### P0-2 — Single publisher for `audit3_verdict_history.json`
**What:** make `audit3-ledger.yml` the only writer; the deploy pipeline consumes, never writes.
**Test plan:** `git grep -n "audit3_verdict_history" .github/ tools/` → exactly one `--history-write`
site; `pytest tests/test_audit3_ledger_e2e.py -q`.

### P0-3 — F1 arithmetic-sum drawdown + F2 cost floor
**What:** add a compounded-drawdown series to the tribunal output and document the cost floor
(`MATERIALITY_COST_FRACTION = 0.5`) as the base for the materiality gate.
**Test plan:** new unit tests in `tests/test_audit3_tribunal.py`:
```bash
pytest tests/test_audit3_tribunal.py -q   # currently 34 passed
```
**Expected:** drawdown test uses a known equity curve (e.g. +50%, −50% → compounded −25%, not 0%).

### P1-4 — Phantom strategies
**What:** for each of the 23 manifest strategies, require `strategy EXISTS in trading_picks` or
retire/rename. Amend the pre-registration to real emitters.
**Test plan:**
```bash
python3 tools/pod_emission_audit.py --strict
pytest tests/test_pod_emission_audit.py -q
```
**Expected:** 0 phantom under `--strict` after the manifest is amended (today 15/23).

### P1-5 — H-119 benchmark coverage 0.798 → ≥0.90
**What:** price joins for ~87 rows (needs DB creds). No code change required per status snapshot.
**Test plan:** `python3 -m alpha_engine.audit3_forward_gate` (or the forward summary) →
`gate.benchmark_coverage >= 0.90`; `pytest tests/test_forward_observations*.py -q`.

### P1-6 — B1 POD-EQUITY-BREAKOUT
**What:** amend the pre-registration to real emitters (`donchian_breakout_scalp` 81,
`proven_donchian_adx_trend` 55, `adx_momentum` 95) or retire the pod.
**Test plan:** registry contains the amended ids; `audit2_forward.json` shows n>0 for the pod
after the next ingest (`41 */6`).

### P2-7 — FX backfill
**What:** `python3 tools/fx_backfill.py --apply` (15 pairs × 203d) enables FX selection alpha.
**Test plan:** `python3 tools/fx_backfill.py --dry-run` (already verified) then `--apply`;
selection-alpha gate reports a non-empty FX scope.

### P2-9 — Extend parity assertion to `/audit2`
**What:** `assert_surface_parity.py` also checks `audit2.js`'s `LEDGER_SERVED_FROM` disclosure.
**Test plan:** render `/audit2` with the fallback copy made stale → page must disclose
"Served from fallback copy".

### P2-10 — FMP key rotation
**Blocked on human.** No code.

---

## 6. What I did NOT verify (honest gaps)

- I did not run the DB-backed steps (`fx_backfill --apply`, H-119 price joins) because they need
  credentials from `dbpasses.txt`, which I must not read.
- I did not re-run the full `audit3_tribunal` on a fresh `dashboard_data.json` in this session;
  the ledger numbers above are the live published artifact.
- F2's exact intended meaning ("cost-floor base") is ambiguous in the handoff; I recorded what
  exists in code rather than guessing.

---

## 7. Suggested next actions

1. Land P0-1 (parity assertion) — cheapest, closes a real CI gap.
2. Land P0-3 F1 drawdown test — the tribunal currently has no drawdown metric at all.
3. Amend the pod manifest (P1-4) so `--strict` can be enforced.
4. Operator: rotate the FMP key (P2-10).
5. Data: run the two cred-blocked backfills (P1-5, P2-7) in a credentialed runner.

*Not investment advice. Nothing here is a promotion; 0 PROVEN / 0 CANDIDATE.*
