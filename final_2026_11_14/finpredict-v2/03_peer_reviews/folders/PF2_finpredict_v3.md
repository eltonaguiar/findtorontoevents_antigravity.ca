# PF2 — Peer Folder Review: `finpredict-v3` (all five dated sets)

**Verdict: PASS (conditional merge-readiness).**

The committed v3 deliverables are runnable, reproducible, and support the shared negative verdict. Conditions before treating the archive as final: (a) revert the two uncommitted edits v3 made inside **our** archive (`2026-11-14/finpredict-v2_20261114-1602/recommendations/{QUICK_WINS.md,patch_plan/P0_QUICK_WINS.md}`); (b) do not commit the duplicate `tools/*`, `tests/*`, `updates/*` files at the repo root; (c) fix the internal citation drift listed in §8; (d) wire the hygiene tool only as a **post-generation** gate with an explicit payload path and a minimum-row guard (see §5).

- **Reviewer:** PF2 (read-only; no repo source modified)
- **Clock:** 2026-11-14T17:55Z; commands re-run at ~17:59–18:02Z
- **Scope:** every file in the five dated sets under `.kilo/worktrees/finpredict-v3/2026-11-14/finpredict-v3/`
- **Compared against:** our archive `2026-11-14/finpredict-v2_20261114-1602/` (`MASTER_AUDIT.md`, `PEER_CROSSREF.md`, `recommendations/**`)

---

## 0. Repository state (important context)

- v3's worktree is on branch `archive/2026-11-14-finpredict-v3`, and **`HEAD == origin/main == 7e8c7ac82da`**. All five dated sets and the ML/gatekeeper commits (`d8c8dd25581`, `3ac931822d8`, `7e8c7ac82da`) are **already on `origin/main`**. This is not a pending merge; it is a live archive plus uncommitted working-tree deltas.
- Uncommitted in v3's worktree:
  - **`M 2026-11-14/finpredict-v2_20261114-1602/recommendations/QUICK_WINS.md`** and **`M .../patch_plan/P0_QUICK_WINS.md`** — v3 edited **our** archive. Not on main, but it is a cross-archive modification and a hygiene violation. Revert or move into v3's own dated folder.
  - Untracked repo-root duplicates: `tools/pi_data_hygiene.py`, `tools/pi_fundamental_ranker.py`, `tools/pi_horizon_validation.py`, `tests/test_pi_data_hygiene.py`, `tests/test_pi_fundamental_ranker.py`, `updates/2026-11-14-prediction-data-hygiene.md`, plus `playwright.live.config.ts`, `tests/audit_live_js_errors_spec.ts`. These duplicate the archive copies. Do not commit as repo source without a decision.
- `.pyc` files under the sets are build artifacts (`__pycache__`, 6 files, 17:52:22–23Z) and are excluded from the review.

---

## 1. Per-set inventory

### Set A — `2026-11-14T155500Z` (hygiene audit + tool + tests)

| Path (relative to set) | mtime (UTC) | Bytes | Description |
|---|---|---:|---|
| `README.md` | 2026-11-14T16:07:58Z | 9,399 | Archive header, 7 verified findings, verdict, peer reconciliation, sibling reconciliation |
| `tools/pi_data_hygiene.py` | 16:07:58Z | 11,428 | Read-only hygiene guardian (5 tagged checks + recency + zombie scan + flat-cohort detector); exit 1 on findings |
| `tests/test_pi_data_hygiene.py` | 16:07:58Z | 4,798 | 14 pytest cases (13 unit + 1 live-payload smoke) |
| `updates/2026-11-14-prediction-data-hygiene.md` | 16:07:58Z | 8,347 | Defect evidence, per-class remediation plan with target code |
| `tools/__pycache__/pi_data_hygiene.cpython-312.pyc` | 17:52:22Z | 17,751 | Build artifact |
| `tests/__pycache__/test_pi_data_hygiene.cpython-312-pytest-9.0.3.pyc` | 17:52:22Z | 16,107 | Build artifact |

### Set B — `2026-11-14T161500Z` (QUICK_WINS)

| Path | mtime | Bytes | Description |
|---|---|---:|---|
| `QUICK_WINS/00_INDEX.md` | 16:15:50Z | 2,732 | Class verdicts + systemic top-3 |
| `QUICK_WINS/overall/GLOBAL_QUICK_WINS.md` | 16:15:50Z | 5,227 | 7 systemic fixes with Impact/Effort/Risk and verified targets |
| `QUICK_WINS/asset_classes/CRYPTO.md` | 16:15:50Z | 4,490 | QW-C1…C5: zero-entry, zombie quarantine, re-quote, dedup, status/PnL contradictions |
| `QUICK_WINS/asset_classes/FUTURES.md` | 16:15:50Z | 2,548 | QW-F1…F3: gate placeholders, date-only serialization, exclude unproven class |
| `QUICK_WINS/asset_classes/BOND.md` | 16:15:50Z | 3,173 | QW-B1…B4: backfill prices, min-n, age-gate, verify FRED/yfinance wiring |
| `QUICK_WINS/asset_classes/EQUITY.md` | 16:15:50Z | 2,949 | n+CI disclosure, last-close labeling |
| `QUICK_WINS/asset_classes/ETF.md` | 16:15:50Z | 2,571 | Parked-state label, re-quote hook, thin sample |
| `QUICK_WINS/asset_classes/FOREX.md` | 16:15:50Z | 3,220 | Purge 11 phantoms, dedupe batch `closed_at` |
| `QUICK_WINS/asset_classes/COMMODITY.md` | 16:15:50Z | 2,851 | Unproven badge, forward-validator routing |
| `QUICK_WINS/asset_classes/MUTUAL_FUNDS.md` | 16:15:50Z | 3,237 | Planned/not-built; ranker + page absent; `funds.html` exists (verify) |

### Set C — `2026-11-14T161700Z` (PEER_REVIEW, round 1)

| Path | mtime | Bytes | Description |
|---|---|---:|---|
| `PEER_REVIEW/00_INDEX.md` | 16:18:09Z | 2,056 | Class review summary + cross-peer flags |
| `PEER_REVIEW/overall/PEER_REVIEW_OVERALL.md` | 16:18:09Z | 4,800 | Peer inventory, verdict consensus, agreements, contradictions, best-of |
| `PEER_REVIEW/asset_classes/CRYPTO.md` | 16:18:09Z | 6,450 | Peer review for CRYPTO |
| `PEER_REVIEW/asset_classes/FUTURES.md` | 16:18:09Z | 4,622 | Peer review for FUTURES |
| `PEER_REVIEW/asset_classes/BOND.md` | 16:18:09Z | 4,869 | Peer review for BOND |
| `PEER_REVIEW/asset_classes/EQUITY.md` | 16:18:09Z | 3,952 | Peer review for EQUITY |
| `PEER_REVIEW/asset_classes/ETF.md` | 16:18:09Z | 3,173 | Peer review for ETF |
| `PEER_REVIEW/asset_classes/FOREX.md` | 16:18:09Z | 3,669 | Peer review for FOREX |
| `PEER_REVIEW/asset_classes/COMMODITY.md` | 16:18:09Z | 3,137 | Peer review for COMMODITY |
| `PEER_REVIEW/asset_classes/MUTUAL_FUNDS.md` | 16:18:09Z | 3,601 | Peer review for MUTUAL_FUNDS |

### Set D — `2026-11-14T174500Z` (ML_VALIDATION + tool + tests)

| Path | mtime | Bytes | Description |
|---|---|---:|---|
| `ML_VALIDATION/README.md` | 17:49:32Z | 7,840 | ML audit (Part 1–3), proof methodology (Part 4), harness results (Part 5), remediation, R2 reconciliation |
| `ML_VALIDATION/tools/pi_horizon_validation.py` | 17:49:31Z | 7,328 | Walk-forward + CI + PF + stability proof harness over recorded closed trades |
| `ML_VALIDATION/tools/pi_fundamental_ranker.py` | 17:49:32Z | 11,295 | Leakage-free chronological walk-forward ranker scaffold (synthetic mock default) |
| `ML_VALIDATION/tools/test_pi_fundamental_ranker.py` | 17:49:32Z | 3,293 | 4 tests: no-future-leakage, null CI, planted signal, window sizes |
| `ML_VALIDATION/results/horizon_validation_n60.txt` | 17:47:56Z | 922 | n≥60 run: 6 groups, 0 pass |
| `ML_VALIDATION/results/horizon_validation_n30.txt` | 17:47:56Z | 2,763 | n≥30 run: 26 groups, 0 pass |
| `ML_VALIDATION/tools/__pycache__/pi_horizon_validation.cpython-312.pyc` | 17:52:23Z | 12,299 | Build artifact |
| `ML_VALIDATION/tools/__pycache__/pi_fundamental_ranker.cpython-312.pyc` | 17:52:23Z | 16,967 | Build artifact |

### Set E — `2026-11-14T175100Z` (PEER_REVIEW_R2)

| Path | mtime | Bytes | Description |
|---|---|---:|---|
| `PEER_REVIEW_R2/00_INDEX.md` | 17:54:48Z | 1,291 | R2 index + summary |
| `PEER_REVIEW_R2/overall/PEER_REVIEW_R2_OVERALL.md` | 17:54:44Z | 3,583 | Consolidated 6-peer consensus + master-plan adjustments |
| `PEER_REVIEW_R2/overall/PEER_REVIEW_V1_MASTERPLAN.md` | 17:53:59Z | 6,599 | Review of v1 master-plan inputs |
| `PEER_REVIEW_R2/overall/PEER_REVIEW_V2.md` | 17:54:03Z | 7,892 | Review of our archive (v2) — names it the reconciliation backbone |
| `PEER_REVIEW_R2/overall/PEER_REVIEW_V4.md` | 17:54:18Z | 8,183 | Review of v4 archive |
| `PEER_REVIEW_R2/overall/PEER_REVIEW_ML_AUDIT.md` | 17:54:18Z | 8,029 | Review of childlike-airport ML-audit fixes |
| `PEER_REVIEW_R2/overall/PEER_REVIEW_SCRATCH.md` | 17:54:16Z | 6,734 | Review of scratch-hippodraco quick-wins |
| `PEER_REVIEW_R2/overall/PEER_REVIEW_SEER.md` | 17:54:23Z | 5,206 | Review of hilarious-seer stubs |

**Totals:** 36 authored files + 6 `.pyc` artifacts; no README at the archive root of sets B–E (each has an index instead).

---

## 2. Tool/test results (exact, re-run read-only)

| Command | Result |
|---|---|
| `cd 2026-11-14T155500Z && python3 -m pytest tests/test_pi_data_hygiene.py -q` | **14 passed in 0.17s** |
| `cd 2026-11-14T174500Z && python3 -m pytest ML_VALIDATION/tools/test_pi_fundamental_ranker.py -q` | **4 passed in 0.29s** |
| `cd <v3 worktree> && python3 -m pytest tests/test_gatekeeper_leakage_default.py -q` (claim in ML README) | **4 passed in 0.09s** |
| `python3 2026-11-14T155500Z/tools/pi_data_hygiene.py --json /tmp/kilo/dashboard_data_latest.json --asof 2026-11-14T15:50:00+00:00 --show` | **exit 1**; TOTAL FINDINGS **16** = STALE_CRYPTO_PRICE 2, FROZEN_CLOSED_PHANTOM 11, DATE_ONLY_SEED 3, NULL_PRICE 0, PLACEHOLDER_ENTRY 0; flat cohort 0 |
| `python3 ML_VALIDATION/tools/pi_horizon_validation.py --json /tmp/kilo/dashboard_data_latest.json --min-trades 60` | resolved 3,489; phantoms excluded 11; groups tested 6; **passed 0** |
| same, `--min-trades 30` | groups tested 26; **passed 0** |

Live payload used: `/tmp/kilo/dashboard_data_latest.json` (25,099,200 bytes, mtime 2026-11-14T15:51Z, `generated_at 2026-11-14T14:30:07Z`). All v3 result files reproduce exactly.

Zombie scan reproduced exactly: CRYPTO n=3,577 / 3,085 >7d / 3,170 null; EQUITY 182/46/110; FOREX 277/114/242; COMMODITY 44/16/32; FUTURES 13/10/8; BOND 15/0/9; ETF 38/8/11; SPORTS 2/0/2.

---

## 3. Unique findings vs our archive — ADOPT / MERGE / REJECT / ALREADY_COVERED

Targets are paths in **our** archive unless noted.

| # | v3 item (set) | Class | Target | Condition / reason |
|---|---|---|---|---|
| 1 | `pi_data_hygiene.py` + 14 tests (A) | **MERGE** | `recommendations/overall/CI_GATES.md` (new G14), `recommendations/patch_plan/acceptance_tests.md` | We have no runnable hygiene gate; G2 covers quote honesty only. Wire post-generation, explicit `--json`, min-row guard. |
| 2 | `FROZEN_CLOSED_PHANTOM` check (A) | **MERGE** | `recommendations/overall/CI_GATES.md` G14 + `tests/test_quote_contract.py` (planned) | We have the 11-phantom finding and a fix item, but no detector. Use 11 as regression baseline. |
| 3 | `DATE_ONLY_SEED` check (A) | **MERGE** | `recommendations/overall/CI_GATES.md` G14; fix already in `recommendations/QUICK_WINS.md` #6 | Detector is valid as a **field-shape** check. It does **not** prove the UI "no date" symptom (all 3 flagged rows also carry a full `timestamp`; our MASTER_AUDIT §6 already says not reproduced). |
| 4 | `NULL_PRICE` / `PLACEHOLDER_ENTRY` (A) | **REJECT as wired; MERGE after extension** | `recommendations/overall/CI_GATES.md` G14 | Only scans `picks.active` (20 rows) → reports 0, while `active_raw` has **85** `entry<=0` rows and **3,584** null prices. The tool cannot see the garbage it cites (e.g. `XRPUSDT SHORT entry=0.0` from `prediction_market_consensus`, verified in raw). |
| 5 | `ACTIVE_RAW` zombie scan (A) | **MERGE** | `recommendations/overall/CI_GATES.md` G14 (informational, with thresholds) | Exact per-class counts are ALREADY_COVERED by `sub/C_crypto.md` / `sub/D_non_crypto.md`; the repeatable scan is the unique value. Today it is **print-only** and does not affect the exit code. |
| 6 | `FABRICATED_FLAT_PNL_COHORT` detector (A) | **REJECT as wired; ADOPT only if relocated** | `recommendations/patch_plan/acceptance_tests.md` (full closed DB / `pf_registry`) | 0 hits on `recent_closed`. The known 286-trade flat-3% cohort lives in the larger closed DB, so the check gives false assurance. Keep the known cohort as a data fixture, not the gate. |
| 7 | TRUE RECENCY per-class table (A) | **ALREADY_COVERED** | `sub/B_dashboard_freshness.md`, `MASTER_AUDIT.md` §2/§6 | Signal-age vs price-freshness distinction already our position. |
| 8 | GLOBAL #1 — gate hygiene in audit-dashboard CI (B) | **MERGE (conditional)** | `recommendations/overall/CI_GATES.md` G14 | Do **not** run pre-generation as written. Run after `dashboard_generator` with explicit path + assert `len(active)>0 and len(recent_closed)>0`; start report-only/allowlist because today it fails with 16 findings. |
| 9 | GLOBAL #2/#7 — payload lag / banner relabel (B) | **ALREADY_COVERED** | `sub/B_dashboard_freshness.md`, `recommendations/overall/DATA_CONTRACT.md` | Same fix direction. |
| 10 | GLOBAL #3 — stop pinning crypto price (B) | **ALREADY_COVERED** | `recommendations/per_asset_class/crypto_commodity.md` P0-1/P0-2, `QUICK_WINS.md` #5 | — |
| 11 | GLOBAL #4 — dual-cohort headline (B) | **ALREADY_COVERED** | `recommendations/overall/CI_GATES.md` G1, `DATA_CONTRACT.md` | — |
| 12 | GLOBAL #5 — preserve auto-expired rows (B) | **ALREADY_COVERED** | `QUICK_WINS.md` #9, veto list | Quarantine, not delete. |
| 13 | GLOBAL #6 — disable never-run workflows / rerun stale (B) | **MERGE (minor)** | `recommendations/overall/CI_GATES.md` G7/G8; `sub/A_actions_health.md` | Disable-only is safe; keep our veto on deletion. Do not mass-rerun stale failures without root-cause triage. |
| 14 | CRYPTO QW-C1…C5 (B) | **ALREADY_COVERED** | `recommendations/per_asset_class/crypto_commodity.md`, `QUICK_WINS.md` #9/#11 | One useful detail to merge: `prediction_market_consensus` emits **both** a valid row (`XRPUSDT entry=0.9955`) and a zero-entry duplicate at the same 13:54:51Z timestamp — duplicate emission, not just field omission. |
| 15 | BOND QW-B1…B4 (B) | **ALREADY_COVERED** | `recommendations/per_asset_class/bond_mutual_funds.md` | — |
| 16 | FUTURES QW-F1…F3 (B) | **ALREADY_COVERED** | `recommendations/per_asset_class/forex_futures.md` P0-1, retire-vs-restart gate | — |
| 17 | MUTUAL_FUNDS QW (B) | **ALREADY_COVERED + MERGE nuance** | `recommendations/per_asset_class/bond_mutual_funds.md` | Unique nuance: `audit_dashboard/funds.html` exists (206,841 B); `alpha_engine/mutual_fund_ranker.py` and `audit_dashboard/mutual-funds.html` absent (verified). Decide whether `funds.html` is the intended page. |
| 18 | PEER_REVIEW round 1 (C) | **ALREADY_COVERED** | `PEER_CROSSREF.md` | Same agreement matrix; no new numbers. |
| 19 | `pi_horizon_validation.py` (D) | **ADOPT** | `recommendations/patch_plan/acceptance_tests.md` (rigor gate), `recommendations/overall/CI_GATES.md` | We have no walk-forward “proof” harness. Adopt as the standing gate for any future “solid” claim. |
| 20 | `pi_fundamental_ranker.py` + 4 tests (D) | **ADOPT as scaffold only** | `recommendations/per_asset_class/equity_etf.md` | Correct-by-construction and honest, but default data is a **synthetic mock**; no real fundamentals are wired. Do not present its “NO EDGE” as a market result. |
| 21 | ML code-error table (D) | **MERGE** | `sub/E_statistical.md` (new ML subsection) or `MASTER_AUDIT.md` §3 | Unique evidence not in our archive: `sports_ml.py:47` random split, `per_class_trainer.py:227-236` OOF threshold search, synthetic `ensemble_stacker`, stale `crypto_ml_edge`/`ml_crypto_predictor`. |
| 22 | Gatekeeper leakage default flipped ON (D) | **ADOPT (already live)** | Verify in `sub/E_statistical.md`; no merge action | Committed `d8c8dd25581`, already on `origin/main`; 4 tests pass. Treat as a live behavior change, not an archive item; monitor the emitter. |
| 23 | R2: v4 `pick_summary_stats.json` 173d stale (E) | **MERGE** | `sub/F_sources.md`, `MASTER_AUDIT.md` §3 | Our archive says 79–245d sidecars but does not call out this specific v4 evidence file. |
| 24 | R2: v4 FOREX PF conflict 2.02 / 0.108 / 0.66 (E) | **MERGE** | `sub/G_peer_reconciliation.md`, `MASTER_AUDIT.md` §7 | Reconcile/label the three populations before any master plan cites a FOREX PF. |
| 25 | R2: ML-audit `asset_class` schema no-op + destructive SQL + MF stub scanner veto (E) | **MERGE** | `QUICK_WINS.md` veto list; `recommendations/peer_review/` note | Add: per-class SQL targets a top-level `asset_class` that `etfs`/`overall` say does not exist → would no-op; veto blanket UPDATE / row-move / `INSERT OR REPLACE`; veto stub-scanner `--merge`. |
| 26 | R2: v1 registry-ID duplication + 4 open decision conflicts (E) | **MERGE** | `recommendations/overall/ROADMAP.md` (decision gate) | Close quote enum, dedup key, FUTURES/COMMODITY end-state, FOREX hard-disable default before P1. |
| 27 | R2: scratch QW-ALL-1..9 checklist (E) | **ALREADY_COVERED** | `recommendations/patch_plan/P0_QUICK_WINS.md` | Same code roots; cross-reference, don’t duplicate. |
| 28 | R2: seer stubs are corroboration only (E) | **ALREADY_COVERED** | `PEER_CROSSREF.md` | We already do not rely on seer per-class claims. |

---

## 4. `pi_data_hygiene.py` — is it usable as a CI gate?

**Yes, usable — with four mandatory changes.** It is deterministic, offline, fast (<1 s), and exits non-zero on findings. But as written it is **not safe to wire as a hard pre-publish gate**.

| Check | Scope actually scanned | Live result | Gate-safe? | Gap |
|---|---|---|---|---|
| `STALE_CRYPTO_PRICE` | `picks.active` only | 2 (XRP, BTC) | Yes | Exact-equality (`<=1e-6`) flags a genuinely flat quote too; no quote timestamp. Acceptable as a definition. |
| `FROZEN_CLOSED_PHANTOM` | `picks.recent_closed` only | 11 | Yes | Does not scan the larger closed DB; fine for the 11 known rows. |
| `DATE_ONLY_SEED` | `picks.active` | 3 (XRP, BTC, ES=F) | Yes, as field-shape | All 3 also carry a full `timestamp`; the UI “no date” symptom is not proven by this check. |
| `NULL_PRICE` | `picks.active` only | 0 | **Under-scoped** | Raw feed has **3,584** null `current_price`. |
| `PLACEHOLDER_ENTRY` | `picks.active` only | 0 | **Under-scoped** | Raw feed has **85** `entry<=0` rows, including `XRPUSDT SHORT 0.0` from `prediction_market_consensus` (13:54:51Z). The check cannot see its own headline evidence. |
| `ACTIVE_RAW` zombie scan | `picks.active_raw` | CRYPTO 3,577/3,085/3,170 etc. | **Informational only** | Printed but not counted in `total`/exit code. It does not gate. |
| `FABRICATED_FLAT_PNL_COHORT` | `picks.recent_closed` | 0 | **No-op on this payload** | The known 286-trade cohort is not in `recent_closed`; relocate to the full closed DB. |
| TRUE RECENCY table | `picks.active` | per class | Informational | Useful, not a gate. |

**Specific CI hazards (verified):**

1. **Vacuous pass.** With no `--json`, the tool tries `/tmp/kilo/dashboard_data_latest.json`, then `audit_dashboard/data/dashboard_data.json`, then `alpha_engine/data/active_picks.json`. The second file is **generated at build time and absent in a fresh checkout** (`audit_trail/dashboard_generator.py:18594` writes it), while the third exists and does **not** have the `picks.active`/`recent_closed` schema. I ran the tool against an empty `{"picks":{}}` payload: `TOTAL FINDINGS: 0`, exit 0. A pre-generation gate can therefore pass without scanning anything.
2. **Pre-generation timing is wrong.** `GLOBAL_QUICK_WINS.md` #1 says run it “BEFORE dashboard regen”. That is exactly when the payload is stale or absent. Run it **after** `dashboard_generator` and pass the path explicitly.
3. **Hard-fail blocks every deploy today.** The live payload has 16 findings; failing the job on any finding stops publication until the data is fixed. Start with report-only/annotations, or a committed baseline allowlist that fails only on **new** findings.
4. **No schema/min-row guard.** Add an assertion that `len(active) > 0` and `len(recent_closed) > 0` (and optionally a known `generated_at` freshness bound) before trusting a zero exit.

**Recommended wiring (post-generation):**

```yaml
- name: Gate G14 — data hygiene (report, then baseline)
  run: |
    python tools/pi_data_hygiene.py \
      --json audit_dashboard/data/dashboard_data.json \
      --asof "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" --show
```

…plus an in-repo wrapper that (a) asserts the two arrays are non-empty, (b) diffs against a committed baseline (today: 2/11/3), and (c) fails only on new tags. Extend `NULL_PRICE`/`PLACEHOLDER_ENTRY` to `active_raw` if the goal is to catch zero-entry garbage.

---

## 5. `ML_VALIDATION` — runnable, and does it support the verdict?

**Runnable: yes. Supports the verdict: yes, within a survivor-biased sample.**

- `pi_horizon_validation.py` reproduces exactly: 3,489 resolved trades, 11 phantoms excluded, **0/6** groups pass at n≥60, **0/26** at n≥30. Gates are CI lower bound > 0.50, PF > 1.05, win-majority in ≥66% of windows. The n30 table shows CRYPTO `luxalgo_confluence` n=1,290 WR 42.9% CI_lo 40.3% (reliably anti-skill) and no group clearing the CI.
- The harness uses **only `picks.recent_closed`**, which our audit showed is the 49% survivorship-filtered sample. The README says this explicitly; it is an **upper bound**, not a full-ledger proof. Do not upgrade the wording to “no strategy is profitable” without that qualifier.
- `pi_fundamental_ranker.py`: 4 tests pass; the no-signal mock yields CI [0.439, 0.520] and “NO EDGE DETECTED”, while the planted-signal mock is detected — i.e. the harness is not broken. **But the default is synthetic mock data**; no real fundamentals were run. The correct claim is “scaffold works; no real fundamental signal was tested.”
- The leakage remediation is real and already on main: `_drop_leakage_enabled()` returns `True` by default (opt-out via `ML_GATE_DROP_LEAKAGE=0|false`), `_LEAKAGE_FEATURE_INDICES = (5,6,19,30)`, and `tests/test_gatekeeper_leakage_default.py` passes 4/4 (`d8c8dd25581`). This is a **production behavior change already live**; verify the emitter/canary rather than re-merging.
- ML code-error spot checks that held: `scripts/sports_ml.py:47` `train_test_split(..., test_size=0.2)` with no `shuffle=False`; `ml_gatekeeper/ab_router.py:28-34` leakage-feature list and `:143-158` `(0.5,0.5)` placeholder; `per_class_trainer.py:227-236` OOF threshold search; `scripts/ensemble_stacker.py:286-297` synthetic `np.random.randn` data; `claude_gainer_ml/models/training_meta.json` positive rate 13.04% train vs 1.52% test.
- Caveats: the ML README class table has internal n/WR mismatches (COMMODITY “n=0 … 40.2%”, FUTURES “n=0 … (n=52)”, ETF n=8 vs 44/45 later). Treat the table as a summary, not a citable per-class dataset.

---

## 6. PEER_REVIEW_R2 — conclusions and corrections to **our** archive

**R2 conclusions (correctly attributed):** adopt our v2 archive as the reconciliation backbone; adopt scratch QW-ALL-1..9 as the implementation checklist; merge v1’s master-plan after fixing registry-ID duplication and closing 4 decision conflicts; red-line the ML-audit destructive SQL and mutual-fund stub scanner; refresh v4’s 173-day-stale evidence and resolve its three FOREX PF figures; keep the no-“solid” prohibition until the horizon harness passes.

**Corrections R2 makes to our archive:** **none numeric.** It endorses our headline set and repeats them (n=22,941, WR 42.21%, PF 0.2657, z=−23.60; 20 curated / 4,148 raw; 63.2% open survivorship; 0/9 money-ready). It adds only caveats:

- Top-level `README.md` absent (`INDEX.md` substitutes) — true; by design.
- Primary 48–66 MB payloads and `pf_registry` pruned — true; documented in `raw/MANIFEST.md` (41 lines).
- Peer-reported figures not independently re-derived — true and already marked.
- Point-in-time counts will drift — true.
- Intra-v4 “0 active vs 20 active” contradiction unresolved — true; we documented it as v4-internal.
- Workflow failure root causes remain `UNVERIFIED` — true; already in `MASTER_AUDIT.md` §8.

**Two inaccuracies in R2 about our archive (citation drift):**

1. `PEER_REVIEW_V2.md:43` says our archive passes through “v3’s ‘12 tests’ vs ‘11 tests’”. Our `PEER_CROSSREF.md:12` says **14 tests**; there is no 12/11 text in our archive. R2 misquotes us.
2. `PEER_REVIEW_R2_OVERALL.md` / `PEER_REVIEW_V2.md` call ours “the only integration that cross-references all peers”. v1’s master-plan inputs also review v2/v3/v4 folders. “Strongest” is defensible; “only” is not.

**Corrections v3 should take from our archive (R2 does not flag these):**

- v3 CRYPTO doc says “218 duplicate ids; 55 ids appear in both `active_raw` and `recent_closed`”. Our corrected figures are **248 duplicate-ID groups / 297 extra rows / 56 cross-ledger** (`MASTER_AUDIT.md` §10.1). v3’s numbers are the pre-review draft.
- v3 `PEER_REVIEW/00_INDEX.md` says FUTURES “0 closed ever”. Our correction: **0 rows in `picks.recent_closed`; full history n=13 policy-clean, intrabar n=52**. v3’s own README also says ES=F has “0 closed history”, not class-wide zero.
- v3 `PEER_REVIEW/00_INDEX.md` says COMMODITY “DEAD (June zombies)”; v3’s README says COMMODITY has signals **today at 14:22Z**. Internal conflict; our position is alive-but-unproven and gate-blocked, not dead.
- v3 uses CRYPTO **z=−7.1** in the round-1 README/index but its own R2/V1 review quotes **z=−22.69** (and EQUITY −3.03 vs our −3.03). The −22.69 figure is the policy-clean fleet population (n=21,988); −7.1 is not reconciled anywhere in v3.
- v3 test-count drift: README header says **14 tests / 14 passed**; the same README’s reproducibility line says **11 passed**; the updates doc says **11** twice and **14** once. Actual: **14**.

---

## 7. Citation spot-check (v3 claim → verified)

| v3 claim | Verification | Result |
|---|---|---|
| 14 hygiene tests pass | `pytest` 14 passed in 0.17s | ✅ |
| Live run: 2 stale, 11 phantoms, 3 date-only; exit 1 | Re-ran; TOTAL 16, exit 1 | ✅ |
| CRYPTO raw 3,577 / 3,085 >7d / 3,170 null | Re-ran zombie scan | ✅ exact |
| BOND 9/15 null; FUTURES 10/13 old | Re-ran | ✅ exact |
| `FABRICATED_FLAT_PNL_COHORT` did not fire | Re-ran; 0 | ✅ |
| `audit_dashboard/data/dashboard_data.json` is the payload path | Generated at `dashboard_generator.py:18594`; absent pre-build | ⚠️ valid post-build only |
| Fallback candidate is safe | `alpha_engine/data/active_picks.json` exists; empty-schema run exits 0 | ❌ vacuous-pass hazard |
| `XRPUSDT SHORT entry=0.0` from `prediction_market_consensus` 13:54 | Found in `active_raw` (`pm_consensus_XRPUSDT_202611141354`) | ✅ |
| 85 zero-entry / 3,584 null raw rows | Re-counted | ✅ |
| `train_model.py:685-711` tail-slice leak | Actual `ohlcv_1h[-24:]` at **line 673** | ⚠️ ~12-line drift |
| `crypto_ml_edge` net Sharpe ~16 / DSR 1.0 | `BTCUSDT_1h_edge_meta.json`: `net_sharpe 40.49`, `dsr_probability 1.0` | ⚠️ magnitude/file-specific, not “~16” |
| `training_meta` 13% vs 1.5% positive rate | 0.1304 vs 0.01516 | ✅ |
| `sports_ml.py:47` no `shuffle=False` | Verified | ✅ |
| `ab_router.py:28-38` leak list; `:143-158` placeholder | Verified | ✅ |
| `ensemble_stacker` synthetic | `np.random.randn` generator at :286-297 | ✅ |
| `per_class_trainer.py:227-236` OOF threshold | Verified | ✅ |
| Leakage mask default ON + 4 tests | `_drop_leakage_enabled()` returns True; 4 passed; commit `d8c8dd25581` on `origin/main` | ✅ |
| `funds.html` exists; ranker/mutual-funds.html absent | `audit_dashboard/funds.html` 206,841 B; other two absent | ✅ |
| v3 “218 dup / 55 cross” | Our corrected 248 groups / 297 rows / 56 cross | ❌ stale |
| v3 CRYPTO z=−7.1 | R2/V1 and ours use −22.69 (policy-clean) | ❌ unreconciled |
| v3 FUTURES “0 closed ever” | 0 in `recent_closed`; n=13/52 full history | ❌ imprecise |
| v3 COMMODITY “DEAD (June)” | v3 README says COMMODITY signals today 14:22Z | ❌ internal conflict |

---

## 8. Destructive fixes / veto list

**VETO (do not implement):**

1. **Hard-fail hygiene gate pre-generation** or on the `active_picks.json` fallback — vacuous pass or blocked deploys (see §4).
2. **`DELETE` 22,947 ghost rows** (v4 QW-2) — destroys audit trail; quarantine/tag.
3. **`UPDATE TIME_EXIT → LOST, pnl_pct=0.0`** (v4 MF-4) — fabricates outcomes.
4. **ML-audit blanket `UPDATE` of PnL/timestamp** for all 101 crypto rows; **row-move active→closed**; **`INSERT OR REPLACE`** keyed by `(id,system)` — destructive, and the per-class SQL targets a non-existent top-level `asset_class` (would no-op).
5. **Mutual-fund stub scanner `--merge`** — emits placeholder/empty signals into `active_picks.json`.
6. **`EXPIRED_FORCE` mass rewrite** of historical statuses.
7. **Invert the ML confidence gate** as stated — it is a data/label artifact, not a signal.
8. **Unblock FUTURES/COMMODITY** without a real feed/session guard.
9. **Add `MUTUAL_FUND` to canonical classes** before a real emitter/NAV feed exists.
10. **Commit v3’s edits to our archive** (`QUICK_WINS.md`, `P0_QUICK_WINS.md`) — revert or relocate; do not push cross-archive changes.
11. **Commit the duplicate root `tools/`/`tests/`/`updates/` files** — the canonical copies live in the dated sets; root duplicates confuse ownership.

**Not destructive, but flag:** the gatekeeper leakage default was flipped **ON** in production (`d8c8dd25581`). It is the right direction and is tested, but it changes the live emitter’s feature set; verify via canary/monitoring rather than treating it as a doc-only change.

---

## 9. UNVERIFIED

- `goldmine_stocks` n=270 / WR 50% / PF 0.42 / −4.6; `stocks_competition` PF 1.33 on n=217 — quoted from ML README, not re-derived.
- “361 families + 285 baby + mutation ⇒ ~260 lucky PF>1.5 survivors” — carried from v1; not re-computed here.
- `claude_gainer_ml` test precision/recall/F1 = 0.0 at threshold 0.75 — only the positive-rate split was verified.
- `ml_crypto_predictor` disabled “36.8% WR, −32% PnL” — not checked.
- v4’s dashboard CRYPTO PF 1.801 vs raw 0.371 and Smart Picks PF 9.69 — R2-reported, not independently re-derived here.
- The 286-trade flat-3% cohort — our archive adopted it from v1/v3; the detector itself does not surface it from `recent_closed`.
- `inverse_*` daily re-emission since 2026-05-23 — corroborated by our `sub/C_crypto.md`; not re-derived in this review.
- Workflow failure root causes (step logs), real-money-vs-paper, Kalshi performance — remain `UNVERIFIED` as in our archive.
- The horizon harness result is an **upper bound** on the survivor-filtered `recent_closed` ledger; it is not a full-ledger proof.

---

## 10. Top 5 merge items (ranked)

1. **G14 hygiene gate** — merge `tools/pi_data_hygiene.py` + 14 tests into `recommendations/overall/CI_GATES.md` as a **post-generation** gate with explicit `--json`, non-empty-array assertion, and baseline diff; extend `NULL_PRICE`/`PLACEHOLDER_ENTRY` to `active_raw`. Keep the 2/11/3 counts as the baseline.
2. **Phantom + date-only detectors** — fold `FROZEN_CLOSED_PHANTOM` (11 baseline) and `DATE_ONLY_SEED` (3, field-shape only) into G14/`tests/test_quote_contract.py`; do not claim the UI “no date” symptom from the field check.
3. **Horizon harness as the rigor gate** — adopt `pi_horizon_validation.py` in `acceptance_tests.md`; no “solid/proven” claim until n≥60/≥30 CI+PF+stability gates pass. Reproduced 0/6 and 0/26.
4. **ML code-error + leakage section** — merge the ML error table (random split, OOF threshold overfit, synthetic stacker, stale models) into `sub/E_statistical.md`/`MASTER_AUDIT.md` §3; record that the gatekeeper leakage default flip is already live on `origin/main` (`d8c8dd25581`) and verify via canary.
5. **R2 veto/decision-gate additions** — add to `QUICK_WINS.md` veto list and `ROADMAP.md`: ML-audit schema no-op + destructive SQL + MF stub scanner; v1 registry-ID dedup + 4 decision conflicts; v4’s 173-day-stale `pick_summary_stats.json` and the 3-way FOREX PF conflict.

**Cleanup before closing:** revert v3’s uncommitted edits to our two recommendation files; remove/relocate the duplicate root `tools/`/`tests/`/`updates/` files; fix v3’s internal test-count, z-score, FUTURES-closed, and COMMODITY-dead drift.

---

*PF2 review. Read-only; no repo source modified. All commands and counts above were executed against the archived files and `/tmp/kilo/dashboard_data_latest.json` at 2026-11-14T17:59–18:02Z.*
