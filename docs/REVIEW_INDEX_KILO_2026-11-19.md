# Review index — kilo (deepseek-flash via Kilo extension), 2026-11-19

**Purpose:** everything I landed, how to verify it, and which files I own so parallel agents do
not overwrite each other. All commits are on `origin/main`. My worktree is clean.

## 1. My commits (newest first)

| SHA | What |
|---|---|
| `5a26f9ac52b` | work-preservation + merge policy; read-only worktree backup script |
| `8aee6f084fd` | volume_ratio migration + dry-run backfiller (sidecar default) |
| `ff884c4cb37` | per-hypothesis growth watchdog + pod grace |
| `1238e16d086` | four falsifier tests (provenance, negative edge, zero alpha, DSR) |
| `032d88897d1` | re-enable gitleaks PR + daily secret scan (P0) |
| `79b5de2be3f` | sleeve thesis: 9-month lag-1d numbers + exact-ETF set test |
| `33e41deca65` | CANDIDATE falls back to global DSR when local uncomputable (peer bug) |
| `7f27703e893` | per-entry COMS review with verdicts/actions |
| `eb6bf02cf75` | allocation adopted 90/0/10 |
| `d6a56290b42` | design debate opener (16 elements, 6 criteria, assignments) |
| `77be7fb34ff` | next-phase plan (measurement integrity first) |
| `f4d6192db69` | real-money readiness + 5-test peer framework |
| `4ec5fd7089f` | etf-rotation aligned to validated TAA spec |
| `57c1c0d11d2` | ETF rotation + random control sleeves + daily marks + PDT correction |
| `6448b582fe0` | core-beta sleeve live (SPY 721.90, $1,400) |
| `260df7f980f` | DSR trial counts on every bucket |
| `1189ff4150d` | provenance triple on every rendered number |
| `1a36da257e2` | unmatched-strategy diagnostics in the forward ingest |
| `6abfa22364e` | G9 alpha at strategy scope, global DSR floor, family gates, forward ingest |

## 2. Files I own — do not edit concurrently without a COMS claim

```
alpha_engine/audit3_tribunal.py
alpha_engine/audit3_selection_alpha.py
alpha_engine/forward_observations_ingest.py
tools/forward_growth_watchdog.py
tools/backfill_volume_ratio.py
tools/backup_worktrees.sh
tools/sleeve_daily_summary.py
paper_trading/sleeves.py  paper_trading/sleeves.json  paper_trading/data/*
tests/test_audit3_tribunal.py  tests/test_audit3_falsifiers.py
tests/test_forward_observations_ingest.py  tests/test_forward_growth_watchdog.py
tests/test_paper_sleeves.py  tests/test_sleeve_daily_summary.py  tests/test_volume_ratio.py
.github/workflows/forward-observations-ingest.yml
.github/workflows/sleeve-daily.yml
.github/workflows/secret-scan.yml
docs/AUDIT_SURFACES_FULL_REVIEW_2026-11-19.md
docs/WHAT_WORKS_PER_ASSET_CLASS_2026-11-19.md
docs/ALLOCATION_2000_AND_LIVE_SIM_PLAN_2026-11-19.md
docs/NEXT_PHASE_PLAN_2026-11-19.md
docs/DESIGN_DEBATE_2026-11-19.md
docs/COMS_REVIEW_FEEDBACK_2026-11-19.md
docs/REAL_MONEY_READINESS_AND_PEER_FRAMEWORK_2026-11-19.md
docs/WORK_PRESERVATION_AND_MERGE_POLICY_2026-11-19.md
docs/VOLUME_CONTEXT_MIGRATION_APPROACH_2026-11-19.md
```

If you need a change in one of these, post the file + intent on COMS first. I will do the same
for yours.

## 3. How to verify my work (each is one command)

```bash
# full focused suite (157 tests)
python3 -m pytest tests/test_audit3_tribunal.py tests/test_audit3_expectancy_gates.py \
  tests/test_audit3_edge_hunt.py tests/test_audit3_selection_alpha.py \
  tests/test_forward_observations_ingest.py tests/test_audit3_cost_basis.py \
  tests/test_paper_sleeves.py tests/test_sleeve_daily_summary.py \
  tests/test_forward_growth_watchdog.py tests/test_audit3_falsifiers.py \
  tests/test_volume_ratio.py -q

# provenance + DSR trials on the live ledger
python3 - <<'PY'
import json,urllib.request
d=json.load(urllib.request.urlopen("https://findtorontoevents.ca/audit3/audit3_ledger.json"))
p=d["provenance"]; c=d["cells"][0]
print(p["id"], p["population"], "cell trials:", c.get("dsr_n_trials"),
      "bucket id ok:", c.get("provenance_id")==p["id"])
PY

# watchdog (should be green today; pods WARN inside grace)
python3 tools/forward_growth_watchdog.py --n-admissible 430 \
  --manifest reports/audit3_confirmatory.json

# volume backfill (dry run only; --apply is NOT authorised)
python3 tools/backfill_volume_ratio.py --limit 200 --json
```

## 4. What I did **not** touch

- The restored WIP in `.kilo/worktrees/vanilla-handsaw` (21 files) belongs to another agent. I
  only recovered it from a stash ref after its directory was deleted; I have not committed or
  pushed it.
- `feat/audit3-p0-p1-correctness` / PR #965: I did not merge, rebase, or force-push it.
- Any Windows-only code, COMS client code, or the prediction-market modules.

## 5. Open items (mine)

| Item | State |
|---|---|
| B3b per-hypothesis watchdog | landed |
| B5 falsifiers | landed |
| B6 volume migration | tooling ready; `--apply` awaits approval |
| B7 beta-matched hold arm | queued |
| C3 graduation runbook | queued |
| P0 security | branch still exposed; owner must rotate + delete |

## 6. Known blockers I cannot fix alone

1. **B1**: the equity/ETF emitters do not write intrabar outcomes for the breakout strategies, so
   `POD-EQUITY-BREAKOUT` cannot accrue; the watchdog will turn the ingest job red on 2026-11-26.
2. **P0 security**: branch `feat/audit-review-organization-2026-11-19` still contains the
   credential at its tip; only the owner can rotate and delete.
3. **Volume schema**: needs an operator decision between sidecar (my recommendation) and ALTER.
