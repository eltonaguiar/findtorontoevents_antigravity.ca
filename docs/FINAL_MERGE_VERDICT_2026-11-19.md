# FINAL MERGE VERDICT — 2026-11-20T00:05Z

**Author:** kilo (deepseek-flash via Kilo extension, Linux) · **Seat:** `gx10-c9b9/vanilla-handsaw/kilo`
**Question:** what should be pushed to `main`, in what order, and how do we test it?

---

## 1. Where my work is

**Everything of mine is already on `findtorontoevents_antigravity.ca` main.** My worktree is clean;
nothing is uncommitted; nothing is only local.

| Layer | Location |
|---|---|
| Code + tests + workflows | `main` — 19 commits from `6abfa22364e` to `5a26f9ac52b` (see `docs/REVIEW_INDEX_KILO_2026-11-19.md`) |
| Verify commands | same doc, §3 |
| Human-readable review package | `antigravity_review_Nov192026` @ `d7a41f63f681`, folder `artifacts/2026-11-19T2308Z_linux-kilo-ext_deepseek-flash/` (17 files + MANIFEST) |
| Snapshot of the broken-main incident | `docs/WORK_PRESERVATION_AND_MERGE_POLICY_2026-11-19.md` §1.3 |
| Ingest fix (new, stacked) | branch `fix/ingest-classify-restore` @ `7fcf665bf73`, tag `archive/2026-11-19/ingest-classify-restore` |

## 2. Peer review status — 4 of 8 reviewed

| Peer | Artifacts seen | Verdict |
|---|---|---|
| **OpenCode (Windows)** | P0 alert, debate votes, cross-check, 5 archive tags, merge/backup decision | **Trustworthy.** Tags verified. One merge claim was wrong (`fix/audit2-3-p0-p1` is 552 behind) and has been corrected |
| **FreeBuff** | TAA 576-cell CSV, sector spec `H-20260612-equity_sector_rotation_vix`, $2k critique, per-class report | **Good work, unfinished.** T16 + sector repro still in progress; one stale claim (`selection_alpha.available=false`) needs correcting |
| **Kilo (Linux CLI)** | PR #965, TODO sweep T4–T21, cherry-pick branch **now pushed** `feat/kilo-todo-sweep-clean @07b020459e1` | **Good, finally verifiable.** 8 files, no conflicts. 16 pre-existing failures on main they correctly did not hide |
| **GitHub Copilot** | PR #962/#964 merged, TAA lag repro, cost floor, cross-check (found my DSR bug) | **Best process contribution.** Its sim has 3 open findings from Hermes (F1–F3) it should answer |
| **Hermes (Windows)** | ACK + review tally; F1–F3 against Copilot | **Contributes reviews, no code artifacts** |
| **Google Swarm** | none | **Not accounted for** |
| **OpenCode console-linux** | none | **Not accounted for** |
| **KILO Desktop (Windows)** | none | **Not accounted for** |

## 3. What to push — in this order

### 3.1 FIRST: PR #972 `hotfix/audit3-merge-repair` (open)
Fixes the partially-merged port: `require_alpha` TypeError in `main()`, duplicated N1
persistence block, missing `ALPHA_PASSTHROUGH_KEYS`, cost-stress tier reconciliation. Without
it the 6-hourly ledger **fails at runtime**. Rebase first (11 commits behind), then merge.

### 3.2 SECOND: `fix/ingest-classify-restore` @ `7fcf665bf73` (mine, stacked on #972)
One file: restores `forward_observations_ingest.py` from `1238e16` — `classify()` regains the
`timeframe` parameter (H-144 position pods) and the strategy-keyed pod matching (H-BABY breakout),
plus `unmatched_top`. **With #972 + this, 93/93 audit3 tests pass.** Merge #972 first, then this.

### 3.3 THIRD: Kilo's `feat/kilo-todo-sweep-clean` @ `07b020459e1`
Now pushed. 8 files, no conflicts: `audit2_pods.json`, `value_screener_picks.json`,
`updates/2026-11-19-audit3-todo-sweep.md`, `audit3.html` "not evaluated" rendering,
`dashboard_generator.py` pnl note, TACTICAL_ROTATION claim retraction, H-142/H-143 pods.
Open as a PR, run the suite on the rebase, merge.

### 3.4 Docs-only, safe: #903, #894, #872, #968 (buffy findings), #969 (backup tool)
Review for accuracy, then merge. They cannot revert code.

### 3.5 NOT to push
- **PR #965 wholesale** — 1,555 commits behind, contains none of the landed gates; merging reverts
  the measurement work. (Its unique files are already cherry-picked into 3.3.)
- **`fix/audit2-3-p0-p1` as a merge** — 552 behind main; cherry-pick its tests/dashboard hunks only.
- **`feat/audit-review-organization-2026-11-19`** — contains the exposed credential. Rotate, delete,
  purge. Never merge.

## 4. How to test (copy-paste)

```bash
# 1. Focused audit3 suite — must be 93 passed after #972 + ingest restore
python3 -m pytest tests/test_audit3_tribunal.py tests/test_audit3_expectancy_gates.py \
  tests/test_audit3_edge_hunt.py tests/test_audit3_selection_alpha.py \
  tests/test_forward_observations_ingest.py tests/test_audit3_cost_basis.py -q

# 2. Crash smoke test — the exact call that failed on main tonight
python3 -c "import sys;sys.path.insert(0,'.');from alpha_engine.audit3_tribunal import build_report; \
print(build_report([{'id':'x','asset_class':'CRYPTO','strategy':'s','direction':'LONG', \
'symbol':'BTCUSDT','source_system':'a','status':'WON','pnl_pct':1.0, \
'closed_at':'2026-11-01T00:00:00+00:00'}]*30,'x.json',None)['cells'][0]['required_n'])"
# expect: a positive integer, no NameError/TypeError

# 3. CLI parses (the argparse regression)
python3 -m alpha_engine.audit3_tribunal --help >/dev/null && echo CLI_OK

# 4. Ledger builds end-to-end (needs DB creds)
python3 -m alpha_engine.audit3_tribunal --picks <payload.json> --out /tmp/ledger.json \
  --alpha /tmp/alpha.json && echo LEDGER_OK

# 5. Live provenance still healthy
curl -s https://findtorontoevents.ca/audit3/audit3_ledger.json | python3 -c \
 "import json,sys;d=json.load(sys.stdin);p=d['provenance'];c=d['cells'][0];\
print(p['id'],p['population'],c.get('dsr_n_trials'),c.get('provenance_id')==p['id'])"

# 6. Secrets gate is on: every PR runs gitleaks
```

## 5. What is still red or blocked (be honest)

| Item | State |
|---|---|
| `materiality_floor_pct` / churn wiring tests | still failing on main; needs the G9+N three-way reconciliation by **one owner** |
| **B1 emitter** | the EQUITY/ETF breakout strategies are absent from `at_signal_outcomes`; pod has 0 forward rows; the watchdog turns the ingest job **red on 2026-11-26** |
| P0 credential | branch still on origin; rotation + deletion are operator actions |
| Volume schema | sidecar tooling ready; `--apply` needs approval |
| FreeBuff T16 / sector repro | in progress |
| Google Swarm, OpenCode console, KILO Desktop | no seat, no artifacts |

## 6. Final position

Push **#972**, then **`fix/ingest-classify-restore`**, then **Kilo's 8-file cherry-pick**, then the
docs PRs. That gets main from *unrunnable* to **93/93 audit3 tests green** without reverting anyone's
work. Hold everything else until the G9+N reconciliation is done by a single owner with the same
test bar.

**None of this makes money yet.** Zero proven cells, zero candidates, selection alpha −0.27%/trade,
and no forward rows for the only pre-registered pod. The correct push tonight is *repair and
measurement*, not a signal.
