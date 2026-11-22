# Audit Surface Consolidation — Fix Plan + Test Plan

**Date:** 2026-11-20
**Author:** copilot-cli-deepseek-flash (worktree `/tmp/consolidate` @ `ab239424b28`)
**Scope:** `findtorontoevents.ca/audit`, `/audit2`, `/audit3` + `ejaguiar1_stocks` + `ejaguiar1_backtests` + the GitHub Actions jobs that populate them.
**Status:** Plan only. No production code changed. Every number below was measured this session, not inferred.

---

## 0. Executive summary

The user's standing hypothesis — *"we couldn't find anything too strong at this time"* — is **confirmed**, but the reason is not what it looks like.

**The verdict is currently unfalsifiable, because the risk framework is one hardcoded constant per asset class.**

Measured 14-day closed picks from `ejaguiar1_stocks.at_raw_picks` (211–1115 rows/class):

| CLASS | n | WR% | avg PnL% | **modal stop-loss distance** |
|---|---|---|---|---|
| CRYPTO | 1115 | 45.7 | +0.118 | 1.0–4.5% (spread, 27 strategies) |
| FUTURES | 210 | 61.0 | +1.300 | **exactly 1.0% (n=105) or 2.0% (n=105)** |
| EQUITY | 60 | 28.3 | −1.256 | **exactly 4.5% (n=59)** |
| ETF | 56 | 1.8 | −2.983 | **exactly 3.0% (n=47)** |
| FOREX | 211 | 7.1 | −0.456 | **exactly 0.3% or 0.5%** |

Every class uses a **fixed percentage stop with no volatility normalisation**. A 3.0% stop on SPY (~0.8% daily vol) and a 3.0% stop on EEM (~1.4% daily vol) are not the same bet. A 0.3% stop on EURUSD is inside one hourly candle's noise band.

Consequence: the measured win rate is dominated by **stop geometry**, not by signal quality. Two proofs:

1. **Win rate tracks the barrier problem almost exactly.** For a driftless random walk between barriers, P(TP first) = SL_dist / (TP_dist + SL_dist). ETF has TP 4.64% / SL 2.73% → random-walk expectation **37% TP-first**. Observed on the clean resolved subset: **2 TP / 51 SL = 3.8%**. Ten times worse than a coin flip against your own stops.
2. **The same pipeline is simultaneously 61% WR (FUTURES) and 1.8% WR (ETF) in the same 14 days, all 100% from one source.** That spread is not explainable by strategy skill; it is explainable by whether the fixed stop happened to sit inside or outside the prevailing volatility regime.

**Verified NOT the cause** (checked and excluded):

- TP/SL are on the correct side of entry for 100% of 14d rows, both directions (0 bad pairs across 1,735 rows).
- `pnl_pct` sign is correct relative to `direction` and `exit_price` (0 sign inversions).
- Hold times are normal — ETF losses average 3,213 minutes (~2.2 days), not instant stop-outs, so this is not a stale-entry-price artefact.
- `at_signal_outcomes.intrabar_ambiguous = 0` on **99.3%** of genuinely-resolved rows (6,882 / 6,928). The ambiguity flag is not the problem on the real subset.

**The real blockers, ranked:**

| # | Blocker | Evidence |
|---|---|---|
| P0 | Hardcoded fixed-% TP/SL, no ATR/vol scaling | 59/59 EQUITY rows at exactly 4.5%; 47/47 ETF at exactly 3.0% |
| P0 | Two independent resolvers publish different answers for the same picks | `at_raw_picks` CRYPTO 45.7% WR vs `at_signal_outcomes.intrabar` 35.8% WR |
| P0 | Three surfaces read three different path sets; two files exist in two copies with divergent timestamps | `audit2_forward.json`: `audit/data/` 03:45:44 vs `audit2/` 07:35:29 — **3h 50m apart, live** |
| P1 | `/audit3` renders a fresh ledger (07:35:29) against **2-day-old** evidence (`audit3_evidence.json` 2026-11-19T05:07) | measured live |
| P1 | `intrabar_truth` excludes TIME_EXIT entirely → 24.6% of resolved trades dropped (survivorship) | verdict SQL filters `status IN ('TP_HIT','SL_HIT')` |
| P1 | 40,228 still-open positions are labelled `intrabar_status='TIME_EXIT'` with `pnl=0.0000` | any consumer not filtering `closed_at IS NOT NULL` counts them as closed break-evens |
| P1 | 6 of 11 classes have n ≤ 10, yet a "NOT_READY / INSUFFICIENT_DATA" verdict is still published | BOND n=2, CHEAP_STOCKS n=2, PENNY n=4, MUTUAL_FUND n=0, MEME n=10, ETF n=29 |
| P2 | Parity tooling exists but is **not on `origin/main`** | `git cat-file -e origin/main:tools/assert_surface_parity.py` → absent |

---

## 1. Current state (measured, live, 2026-11-20T07:5x Z)

### 1.1 Surface → data map

| Surface | URL | HTTP | Title | Primary JSON |
|---|---|---|---|---|
| audit | `/audit/` | 200 | Unified Audit Dashboard - Antigravity | `audit/data/dashboard_data.json` |
| audit2 | `/audit2/` | 200 | audit2 — candidate & methodology library | `audit2/audit2_forward.json`, `audit3_ledger.json` |
| audit3 | `/audit3/` | 200 | Audit3 — Quant Kill Tribunal | `audit3/audit3_ledger.json`, `audit3/audit3_evidence.json` |
| — | `/audit/audit3.html` | **404** | — | audit3 is NOT mounted under `/audit/` |
| — | `/audit/audit2.html` | 200 | — | second mount point for audit2 |

### 1.2 Live timestamp drift (curl, same instant)

| File | Copy A | Copy B | Drift |
|---|---|---|---|
| `audit2_forward.json` | `audit/data/` → **03:45:44** | `audit2/` → **07:35:29** | **3h 50m** |
| `audit3_ledger.json` | `audit/data/` → 07:35:29 (663,832 B) | `audit3/` → 07:35:29 (663,832 B) | in sync |
| `audit3_evidence.json` | `audit3/` → **2026-11-19T05:07:03** | — | **2 days behind its own ledger** |
| `dashboard_data.json` | `audit/data/` → 07:03:17 | — | 32m behind the ledger |

### 1.3 Publisher cadence conflict (370 workflows, 20 audit-relevant)

| Workflow | Cron | Publishes |
|---|---|---|
| `audit-hourly-update.yml` | `19 * * * *` | dashboard data |
| `audit-dashboard.yml` | hourly `:10` | `dashboard_data.json`, commits "updated data" |
| `audit3-health.yml` | `20 5,17 * * *` | `audit3_evidence.json` |
| `audit3-ledger.yml` | — | `audit3_ledger.json` |
| `audit3-denylist-watchdog.yml` | — | `audit3_ledger.json` |
| `forward-observations-ingest.yml` | — | `reports/forward_observations.json` |

**Five workflows write the same ledger family at five cadences.** Nothing coordinates them, and no parity assertion runs in CI.

### 1.4 The two-resolver disagreement

| Class | `at_raw_picks` (what pick-summary panels show) | `at_signal_outcomes.intrabar` (`verdict_basis`) |
|---|---|---|
| CRYPTO | WR 45.7%, avg +0.118% | WR 35.78%, PF 0.9167 |
| EQUITY | WR 28.3%, avg −1.256% | WR 60.31%, PF 0.975 |
| FOREX | WR 7.1%, avg −0.456% | WR 31.55%, PF 0.6402 |
| COMMODITY | WR 25.9%* | WR 40.17%, PF 1.0306 |
| ETF | WR 1.8%, avg −2.983% | WR 3.77%, PF 0.0203 |

\* from `money_ready_verdict.json` headline block. Note both blocks are published in the **same file**, and `money_ready_verdict.json` itself reports `data_source` as `closed_picks` for CRYPTO/COMMODITY but `dashboard_fallback` for EQUITY/FOREX/ETF — two different populations feeding one table.

### 1.4b THREE different PF numbers for the same class, all published

`audit_dashboard/data/audit3_ledger.json` (`source: /tmp/audit3/dashboard_data.json`, `source_generated_at 2026-11-20T07:03:17`) adds a **third** answer to the two in §1.4:

| Class | `money_ready_verdict.json` | `audit3_ledger.json` | `at_signal_outcomes.intrabar` |
|---|---|---|---|
| CRYPTO | PF 0.26, NOT_READY | PF 0.8283, **KILL**, n=6900 | PF 0.9167, n=3726 |
| EQUITY | PF 0.51, NOT_READY | PF 1.0761, **WEAK**, n=943 | PF 0.975, n=257 |
| ETF | PF 1.82, INSUFFICIENT (n=29) | PF 1.0003, **WEAK**, n=588 | PF 0.0203, n=53 |
| FOREX | PF 0.25, NOT_READY | PF 0.6641, **WEAK**, n=280 | PF 0.6402, n=634 |
| COMMODITY | PF 0.25, WATCH | PF 0.1182, **KILL**, n=45 | PF 1.0306, n=234 |
| FUTURES | PF 1.27, INSUFFICIENT (n=62) | PF 1.8719, INSUFFICIENT, **n=4** | PF — (not reported) |

CRYPTO is published as PF **0.26**, **0.83**, and **0.92** on one website on one day — a 3.5× spread with three different sample sizes (n=3726 / 6900 / and the 14d pick panel). **Six of six major classes have contradictory verdicts between two canonical files.**

`audit3_ledger.json` summary confirms the same emptiness from a third direction: `n_proven: 0, n_candidate: 0, n_weak: 59, n_kill: 8, n_insufficient: 301, kill_rate_pct 11.94`.

**Provenance leak:** the canonical ledger records `source: /tmp/audit3/dashboard_data.json`. A `/tmp/` path is unresolvable by any reader and will not exist on the next runner. Provenance must name a repo-relative path plus a sha256.

### 1.5 Direction asymmetry (unexplained, flagged for investigation)

| Class | LONG | SHORT |
|---|---|---|
| FUTURES | 18/61 = **29.5%** | 110/149 = **73.8%** |
| EQUITY | — | 16/16 = **100%** |
| ETF | 0/31 = **0.0%** | 1/25 = **4.0%** |

A 44-percentage-point LONG/SHORT gap on the same instrument and window is either a correct directional call (gold and equities fell over the window) or a resolution asymmetry. **Do not treat the FUTURES 73.8% SHORT or EQUITY 16/16 cells as edge until §4 row T-6 passes.** ETF losing on *both* sides is the tell that in a choppy tape a tight fixed stop is hit whichever way you bet.

---

## 2. Target architecture — one source

```
                    ┌──────────────────────────────┐
                    │  CANONICAL WRITER (single)   │
                    │  tools/publish_audit_data.py │
                    │  one lock, one commit,       │
                    │  one generated_at            │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │  audit_dashboard/data/       │  ← THE one data root
                    │    dashboard_data.json       │
                    │    audit3_ledger.json        │
                    │    audit3_evidence.json      │
                    │    audit2_forward.json       │
                    │    money_ready_verdict.json  │
                    │    pick_summary_stats_*.json │
                    │    _MANIFEST.json  ← new     │
                    └──────────────┬───────────────┘
                                   │ deploy (one job)
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
        /audit/              /audit2/              /audit3/
     (reads only)          (reads only)          (reads only)
```

Rules:
- **One writer.** Every producer emits into `audit_dashboard/data/`. Nothing writes `audit/data/` or `audit3/*.json` directly.
- **One manifest.** `_MANIFEST.json` records `{file, generated_at, sha256, row_count, producer, source_tables}` for every payload.
- **Readers assert, never fall back.** A surface that cannot find its file must show a hard error banner, not silently walk a fallback chain. (The existing 4-path fallback in `audit2.js` is what destroyed provenance.)
- **One deploy.** `tools/deploy_audit_files.py` is the only thing that uploads, and it derives its file list from `_MANIFEST.json`.

---

## 3. Fix plan — ordered, with acceptance criteria

### P0-1 — Volatility-normalise every stop and target

**Problem.** Stops are literal constants per asset class (§0 table).

**Fix.**
- Add `alpha_engine/risk_framework.py` with `atr_stop(symbol, bars, k=2.0)` and `atr_target(atr_stop, rr=2.0)`.
- Replace hardcoded constants in every strategy emitter. Sweep for the pattern: `grep -rnE "stop_loss\s*=.*0\.[0-9]+|STOP_PCT|SL_PCT" alpha_engine/ baby_strategies/ paper_trading/`.
- Persist `atr_at_entry`, `stop_source='atr'|'fixed'`, `bars_used` on the row so the resolver can be audited later.

**Acceptance.** Over a 14-day window, no asset class has >30% of rows sharing one identical stop distance (i.e. the modal-cluster test in §4 T-1 passes). Fix is only accepted when the modal share drops below the class's own pre-fix baseline, recorded in the PR body.

**Do not** read this as "ATR will make us profitable." It won't by itself. It makes the win rate *mean* something.

---

### P0-2 — Collapse to one resolver

**Problem.** `at_raw_picks` and `at_signal_outcomes` disagree by 10+ pp WR on the same population.

**Fix.**
- Declare `at_signal_outcomes` (entry-anchored first-touch, intrabar) the **sole** outcome authority.
- Make `at_raw_picks.status / pnl_pct / exit_price` **derived columns** written by the same resolver pass, not a second calculation.
- Add a `resolver_version` column to both tables; assert both agree on `(id, status, pnl_pct)` per row.
- Keep SL-wins-ties (it is the conservative choice) but **record the tie**: add `intrabar_tie_resolved` so we can report "X% of outcomes were decided by the conservative tie-break" instead of hiding it.

**Acceptance.** A nightly assertion query returns **zero** rows where `at_raw_picks.status != at_signal_outcomes.intrabar_status`. Both surfaces render identical per-class WR/PF.

**Also required (see §1.4b):** `money_ready_verdict.json` and `audit3_ledger.json` must agree on PF for every class, or state explicitly that they measure different populations. Today CRYPTO is published three ways (0.26 / 0.83 / 0.92). Pick one authority for headline PF and label the others as diagnostics with their population stated.

---

### P0-3 — One data root, one writer, one deploy

**Fix.**
- Create `tools/publish_audit_data.py`: acquires a file lock, runs producers in dependency order, writes all payloads to `audit_dashboard/data/`, writes `_MANIFEST.json`, commits once with `[skip ci]`.
- Delete the duplicate copies at `audit/data/` and `audit3/*.json`; replace with deploy-time copies generated from the manifest.
- Retire redundant crons: keep **one** hourly publish job; convert `audit3-health.yml`, `audit3-ledger.yml`, `audit3-denylist-watchdog.yml` to *producers invoked by* the single publisher, not independent committers.
- Surface `generated_at` + `sha256` in the page footer of all three surfaces.

**Acceptance.** `curl` on all three surfaces at T+0 returns the **same** `generated_at` (within 60s) and the same ledger sha256. No two copies of any payload file exist with different timestamps.

---

### P1-4 — Commit the parity gate

`tools/assert_surface_parity.py` and `.github/workflows/surface-parity.yml` exist only as untracked files. Commit them; make the workflow required for any PR touching `audit_dashboard/`, `audit_trail/`, or `alpha_engine/money_ready_verdict.py`.

**Acceptance.** `git cat-file -e origin/main:tools/assert_surface_parity.py` succeeds; a deliberately-broken ledger makes the gate exit non-zero.

---

### P1-5 — Fix the `TIME_EXIT` misuse

**Problem.** 40,228 open positions carry `intrabar_status='TIME_EXIT'`, `intrabar_pnl_pct=0.0000`.

**Fix.** Use a dedicated `'OPEN'` status (or NULL) for unresolved rows. Backfill historical rows where `closed_at IS NULL`.

**Acceptance.** `SELECT COUNT(*) FROM at_signal_outcomes WHERE intrabar_status='TIME_EXIT' AND closed_at IS NULL` → **0**.

---

### P1-6 — Stop dropping TIME_EXIT from `intrabar_truth`

`alpha_engine/money_ready_verdict.py:1569-1575` filters `intrabar_status IN ('TP_HIT','SL_HIT')`, discarding 24.6% of resolved trades. Publish `wr_decided` (TP vs SL only) **and** `wr_all` (including TIME_EXIT at its actual PnL). Report both; never present only the decided subset.

**Acceptance.** `money_ready_verdict.json` carries `intrabar_truth.wr_decided` **and** `intrabar_truth.wr_all` for every class with n>0.

---

### P1-7 — Suppress verdicts below the sample floor

Six of eleven classes have n ≤ 10. Publish `"verdict": "NO_EVIDENCE"` (not `NOT_READY`) whenever `n_resolved < 30`, and render those cells visibly greyed with "n too small to judge".

**Acceptance.** No class with n<30 carries a `NOT_READY` or `WATCH` label anywhere on any surface.

---

### P2-8 — Resolve the LONG/SHORT asymmetry before believing it

Run §4 T-6. Until it passes, **suppress the per-direction WR split from all dashboards**, because a 73.8% vs 29.5% split will be read as edge.

---

## 4. Test plan

### T-1 — Stop-geometry guard (new, `tests/test_risk_framework.py`)

```python
def test_no_hardcoded_class_stop_constant(db):
    """No asset class may have >30% of rows at one identical stop distance."""
    for cls, share, dist in modal_stop_share(db, days=14):
        assert share < 0.30, f"{cls}: {share:.0%} of rows share SL={dist}%"

def test_stop_scales_with_volatility(db):
    """SPY and EEM stops must differ; equal stops prove no vol normalisation."""
    assert stop_pct("SPY") != stop_pct("EEM")
```

### T-2 — Resolver agreement (new, `tests/test_resolver_parity.py`)

```python
def test_raw_picks_matches_signal_outcomes(db):
    """Zero drift allowed between the two published outcome tables."""
    drift = db.rows("""
        SELECT COUNT(*) FROM at_raw_picks r
        JOIN at_signal_outcomes s ON r.id = s.id
        WHERE r.status <> s.intrabar_status""")
    assert drift == 0
```

### T-3 — Known-bad-row regression fixture

Commit one real ETF row (`XLK`, LONG, entry 196.79, TP 206.68, SL 190.86, exit 190.86, −3.02%) plus one synthetic row with TP/SL swapped. Assert:

- the real row resolves `SL_HIT`;
- the swapped row is **rejected** as bad geometry, not silently resolved. (Today `at_raw_picks` was 0% bad-pair, but `at_signal_outcomes` docstring mentions "bad-geometry-excluded" — the exclusion needs a test proving it fires.)

### T-4 — Surface parity (extend `tools/assert_surface_parity.py`)

```python
def test_all_surfaces_report_same_generated_at():
    stamps = {s: manifest[s]["generated_at"] for s in ("audit","audit2","audit3")}
    assert max(stamps.values()) - min(stamps.values()) < timedelta(seconds=60)

def test_no_duplicate_payload_with_divergent_timestamp():
    """The audit/data vs audit2/ audit2_forward.json 3h50m split must be impossible."""
    for name in PAYLOADS:
        copies = glob(f"**/{name}", recursive=True)
        assert len({sha256(p) for p in copies}) == 1, f"{name}: divergent copies"
```

### T-5 — Playwright disclosure test (new, `tests/audit_provenance.spec.ts`)

For each of `/audit/`, `/audit2/`, `/audit3/`:

- footer shows a parseable `generated_at`;
- footer shows the sha256 of the ledger actually rendered;
- the rendered sha256 equals the manifest value;
- a fetch-blocked ledger produces a **visible error banner**, not an empty table.

This is the regression test for the 2026-11-19 incident (two copies, 2h30m apart, neither page disclosing which it rendered).

### T-6 — Direction-symmetry control

Re-resolve a sample of FUTURES SHORT and EQUITY SHORT picks with the direction barriers mirrored, and assert the outcome distribution does not change. If it does, the resolver has a directional asymmetry and **all** LONG/SHORT splits are invalid.

### T-7 — Sample-floor test

```python
def test_small_n_never_gets_a_verdict():
    for cls, v in verdict.items():
        if v["n_resolved"] < 30:
            assert v["verdict"] == "NO_EVIDENCE"
```

### T-8 — CI wiring

- `python3 -m py_compile` on every touched module.
- `node --check audit_dashboard/audit2.js`.
- `pytest tests/test_risk_framework.py tests/test_resolver_parity.py -q`.
- `python3 tools/assert_surface_parity.py` must exit 0.
- Playwright `audit_provenance.spec.ts` on the 3 surfaces.
- All five as required checks on PRs touching audit paths.

---

## 5. What we can and cannot claim today

**Can claim (measured):**
- 0 of 11 asset classes pass a money-ready gate (`summary.money_ready == []`).
- Bootstrap CI lower **and** upper are negative for CRYPTO, EQUITY, FOREX, COMMODITY — statistically significant loss, not sampling noise.
- Stops are hardcoded per class, verified by modal clustering (59/59, 47/47).
- Three surfaces, five publishers, one duplicate file 3h50m out of sync.

**Cannot claim:**
- That any strategy has no edge. With a fixed 3% stop on a 1%-vol ETF against a 4.64% target, the measurement cannot see edge even if it exists.
- That FUTURES 61% WR / PF 2.75 is real edge. n=210, 100% single source, and 73.8% of the profit comes from SHORT in one 14-day window.
- Any per-class verdict for BOND (n=2), CHEAP_STOCKS (n=2), PENNY (n=4), MUTUAL_FUND (n=0), MEME (n=10).

**Honest headline for the dashboards:** *"Measurement is not yet trustworthy; no class can be declared money-ready or not-ready until P0-1, P0-2 and P0-3 land."*

---

## 6. Sequencing

| Wave | Items | Gate to proceed |
|---|---|---|
| 1 | P1-5, P1-6, P1-7, T-7 (labelling only, no strategy change) | verdict file publishes `NO_EVIDENCE` correctly |
| 2 | P0-3, P1-4, T-4, T-5 (one source + parity in CI) | all three surfaces same `generated_at` |
| 3 | P0-2, T-2, T-6 (one resolver) | zero drift between outcome tables |
| 4 | P0-1, T-1 (ATR risk framework) | modal stop share <30% per class |
| 5 | **Re-measure.** Nothing before this point is a verdict. | new 30-day clean window |

Waves 1–2 are safe, mechanical, and reversible. Waves 3–4 change what the numbers say. **Do not start wave 5 conclusions on wave 1 data.**

---

## 7. Reproducer

```bash
# connect
mysql -h mysql.50webs.com -u ejaguiar1_stocks -p ejaguiar1_stocks

# modal stop clustering (the P0-1 proof)
SELECT asset_class, ROUND(ABS(entry_price-stop_loss)/entry_price*100,1) d, COUNT(*) n
FROM at_raw_picks
WHERE closed_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 14 DAY) AND entry_price>0
GROUP BY 1,2 ORDER BY 1, n DESC;

# resolver disagreement (the P0-2 proof)
SELECT asset_class, intrabar_status, COUNT(*) FROM at_signal_outcomes GROUP BY 1,2;

# open rows mislabelled as closed (the P1-5 proof)
SELECT SUM(closed_at IS NULL) FROM at_signal_outcomes WHERE intrabar_horizon_bars=0;
```

Live drift: `curl -s https://findtorontoevents.ca/audit/data/audit2_forward.json | jq -r .generated_at`
vs `curl -s https://findtorontoevents.ca/audit2/audit2_forward.json | jq -r .generated_at`
