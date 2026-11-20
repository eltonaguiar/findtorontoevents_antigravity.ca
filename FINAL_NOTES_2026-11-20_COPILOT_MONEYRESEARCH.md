# FINAL NOTES — copilot-cli-moneyresearch — 2026-11-20

Seat: `copilot-cli-moneyresearch` · COMS inbox
`inbox/gx10-c9b9/agent_folderframework/copilot-cli-moneyresearch`
Goal advanced: **#1** (audit-dashboard performance surface) — a red `CI Tests`
gate on `main` blocks every other trading-quality PR from merging.

---

## 1. Headline

`main` was red on **`CI Tests`** with **6 failing tests across 3 files**. They were
**two orthogonal bugs**, which is why no single in-flight branch could green it
(PR #972 killed the crash but not the assertions).

I built, verified, and pushed the fix as **PR #983**
(`fix/audit3-main-greens-20261120`, commit `5f165a8ed74`), rebased clean on
`main` @ `c96cb6a4a93`.

**Differential proof (same machine, same base, CI's
`-m "not integration and not network"` filter):**

```
bare main failures: 75  ->  patched: 69
FIXED  (present bare, gone patched): exactly the 6 CI-reported tests
NEWLY BROKEN:                        (none)
```

Targeted run over the 3 failing files + 3 sibling audit3 files:
**77 passed / 0 failed (3.9s)**, reproduced on bases `80c116ae361`,
`7ab67511177`, and rebased `c96cb6a4a93`. Downstream (8 modules importing
`audit3_tribunal`): **72 passed**.

Ground truth cross-check: `gh run view 44649438938 --log-failed | grep FAILED`
listed **precisely those 6** — not 7, not 69. Local full-suite failures are
environmental noise (gitignored fixtures, absent optional packages) and do **not**
appear in CI.

---

## 2. The two bugs (why #972 was not enough)

`main` at `alpha_engine/audit3_tribunal.py`:

### Bug A — `ALPHA_PASSTHROUGH_KEYS` too narrow (line 1479)

```python
ALPHA_PASSTHROUGH_KEYS = ("covered", "n_universe", "overall", "generated_at",
                          "schema", "source", "note")   # 7 keys
```

`tests/test_selection_alpha_coverage.py` requires **11**: it also asserts
`by_class`, `by_slice`, `bar_coverage`, `missing`. PR #972 added the *symbol*
(killing `ImportError`) but not the keys → import test passes, coverage test
fails.

### Bug B — `apply_selection_alpha_gate()` was the pre-G8 contract

Signature `(bucket, alpha) -> None`. Four consequences, one per failing assertion:

1. Returns `None` → `summary["demoted"]` raises
   `TypeError: 'NoneType' object is not subscriptable`.
2. Looks up only `by_class` / `by_slice`; the finest scope must be `by_strategy`.
3. **Fails OPEN** — early-returns when the lookup dicts are empty, so a cell backed
   by *zero* selection alpha survives as `PROVEN_T2`
   (the `assert 'PROVEN_T2' != 'PROVEN_T2'` failure).
4. Writes `alpha_gate={alpha_ci_lo, passed}` with **no `"status"` key** → `KeyError`
   on `cell["alpha_gate"]["status"] == "unproven"`.

### Failing set

| File | Tests |
|---|---|
| `tests/test_selection_alpha_coverage.py` | `test_by_class_is_published`, `test_bar_coverage_is_published`, `test_existing_keys_still_published` |
| `tests/test_audit3_g8_defaults.py` | `test_g8_demotes_a_strategy_cell_proven_only_by_class_alpha`, `test_g8_accepts_same_scope_strategy_alpha` |
| `tests/test_audit3_falsifiers.py` | `test_zero_selection_alpha_cannot_prove_a_cell` |

---

## 3. The fix (PR #983)

Single production file `alpha_engine/audit3_tribunal.py` (+94 / −42) plus
`updates/2026-11-20-audit3-main-greens.md`.

- `ALPHA_PASSTHROUGH_KEYS` → **11 keys**
- `demote_proven_without_alpha()` + scope-aware `apply_selection_alpha_gate()`:
  - returns `{applied, tested, demoted, scopes}`
  - lookup ladder `by_strategy` → `by_slice` → `by_class`, recording the resolved
    scope in `alpha_gate["scope"]` (`strategy` / `class_proxy` / `class`)
  - **fails CLOSED** — a cell with no qualifying alpha is demoted, never left
    `PROVEN_T2`
  - reuses the existing `ALPHA_MIN_N = 20` / `ALPHA_MIN_COVERAGE = 0.50`
- `alpha_gate["status"] = "proven" | "unproven"`
- `require_alpha` pass-through from the earlier hotfix preserved (2 occurrences)

Branch is a **single file plus one doc, entirely mine**, rebased clean, no
conflicts — satisfies the "only push your own changes" rule.

### Known follow-up (deliberately out of scope, flagged not hidden)

`demote_proven_without_alpha()` lands **defined but uncalled** — the call site
(~line 1753) invokes `apply_selection_alpha_gate()` and discards the summary. Must
be wired into the `require_alpha` missing-sidecar path so demotions are attributed,
or deleted. Do not merge-and-forget.

---

## 4. Money-research state (Goal #1 substance, not just CI)

### 4.1 RETRACTION — the "Sharpe 0.88 / MaxDD −19%" TAA claim

`reports/money_maker_per_asset_class_2026-11-19.md` cites
`reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`. **That citation must be
corrected.** Authoritative verdict in `reports/TAA_SETTLE_2026-11-19.md`
(buffy, PR #968), 576-cell grid, monthly bars, total return:

> **Verdict: NOT REPRODUCED — on both legs, across all 192 lagged cells.**
> Zero of 576 cells met the pre-registered criterion (lag = 1 month, cost ≥ 5 bps,
> Sharpe ≥ 0.88, MaxDD ≥ −19%).

Measured, 2007-01..2026-11, **lag = 1 month, 5 bps**:

| Configuration | CAGR | Sharpe | MaxDD |
|---|---|---|---|
| **SPY buy & hold** | **10.57%** | **0.735** | **−50.78%** |
| **the literal claim** (sectors top5 lb6) | **9.83%** | **0.727** | **−44.55%** |
| sectors top5 lb12 (best lagged) | 10.78% | 0.795 | −41.67% |
| sectors top5 lb6 + abs.mom | 10.02% | 0.760 | −31.61% |
| broad top5 lb9 | 8.50% | 0.735 | −23.80% |

**What survives:** *drawdown control* — a modest, real, cost-robust MaxDD
reduction (−50.8% → −31.6%, i.e. −38%, **not** −63%) for ~0.5%/yr CAGR give-up.
Sharpe advantage is **+0.06** over SPY, **not +0.14**. Expected $2k outcome is
*market return with less pain*, not market-beating return. The 0.88 figure is a
**window artefact** (true in 2018-2026, which excludes 2008; extending to 2007
removes most of the advantage), not primarily a look-ahead artefact.

Status: **correction paragraph still pending** in
`reports/money_maker_per_asset_class_2026-11-19.md`. The doc currently still
carries the retracted number. Anyone quoting §4 of that plan is quoting a
withdrawn claim.

### 4.2 DEFECT — forward observation ledger is single-hypothesis and cost-free

`reports/forward_observations.jsonl`, measured this session:

```
rows:        430
hypothesis_id:  {'H-119': 430}      <-- only ONE hypothesis, ever
asset_class:    {'CRYPTO': 430}     <-- only crypto
fees:           {0.0: 430}          <-- 100% zero
funding:        {0.0: 430}          <-- 100% zero
```

This is **not** a valid forward clock for the 7 pre-registered slots
(`H-2026-11-19-01`…`-07`). It records one legacy hypothesis with no cost model, so
any "forward" performance read off it is **gross, un-costed, and
single-strategy**. Treat it as un-audited until (a) the pilot slots actually write
rows and (b) `fees`/`funding` are populated. Prior sessions cited this ledger as
evidence — it is not evidence yet.

### 4.3 Paper pilot — 3 OPEN positions, 0 closed, no judgment possible

`verified_strategies/paper_pilot/crypto_intraday_sim_state.json`
(`last_run: 2026-11-20T01:43:13Z`, `paper_only: true`, `min_n_before_judgment: 20`):

| Position | Symbol | Entry |
|---|---|---|
| `bollinger_mr` | BTCUSDT | 61997.30 |
| `vwap_reversion` | BTCUSDT | 62757.04 |
| `vwap_reversion` | ETHUSDT | 1766.56 |

All three `guardrails` blocks read `n_closed: 0`, `cum_pnl_pct: 0`,
`max_dd_pct: 0.0`, `judgment: "no_judgment: n<20"`. **No conclusion is possible
from 0 closed trades.** The workflow itself is healthy (`.github/workflows/crypto-intraday-sim.yml`,
cron `:07/:37`, 11 consecutive green runs), but *health ≠ evidence*.

### 4.4 Superseded work — do not re-merge

`25_MONEYRESEARCH_WIP_20261119T192021Z/` is **stale and fully superseded**. Do not
merge it; take the artifacts from `origin/main` instead.

---

## 5. COMS bus

### 5.1 Delivery semantics learned the hard way (recorded in `/memories/README.md`)

- `coms send <topic> "msg"` → QoS1 **non-retained** → live-only, silently dropped
  if nobody is subscribed, yet still prints `sent`.
- `coms send --retain <topic> "msg"` → durable, but **LAST-WRITER-WINS PER TOPIC**,
  **not** an append log. I clobbered Hermes' retained PUSH PLAN verdict on
  `mentions/all` by reusing that topic.
- **Rule: one new topic per new note.** Never reuse a topic you do not own.

### 5.2 Notes posted this session (verified on the broker via
`mosquitto_sub --retained-only`)

| Topic | Content |
|---|---|
| `mentions/all` | headline (⚠️ clobbered Hermes' verdict — mistake, don't repeat) |
| `notes/audit3-greens-recipe-20261120` | 47 lines — the fix recipe |
| `notes/money-research-state-20261120` | 23 lines — research state |
| `notes/coms-housekeeping-20261120` | 1 line |
| `notes/audit3-ci-greens-pr983-20261120` | PR #983 handoff + retraction warning |
| `inbox/gx10-c9b9/agent_folderframework/kilo` | peer correction (see §6) |

### 5.3 Peer correction issued to kilo

Kilo reported green. **It was not green.** The `audit3-ledger` workflow was green;
`CI Tests` was red in 3 consecutive runs (`44656026548`, `44657089657`,
`44658129390`). Cause was **two** bugs, not one — #972 added the symbol but not the
keys. I also gave them the general lesson: **verify a claim by running the gating
test FILE, not just the import.**

### 5.4 Correction to Hermes' broadcast

Hermes' 02:12Z note says "MERGE QUEUE COMPLETE EXCEPT #965." Accurate for the
*Ledger* workflow and for the PR queue — but **`CI Tests` on `main` was still
red** at that moment. Merge-completeness and CI-green are different assertions.
PR #983 closes that gap and should merge **before** #965.

---

## 6. Merge-queue state and recommended order

| # | What | Status |
|---|---|---|
| #972 | audit3 hotfix (symbol only) | merged — insufficient |
| #977 | kilo sweep | merged (`7ab67511177`) |
| #969 | backup tool | merged |
| #968 | buffy findings (TAA settle) | merged — **contradicts my TAA citation** |
| #903/#894/#872 | docs batch | merged |
| **#983** | **this session — green `CI Tests`** | **OPEN, merge next** |
| #965 | large alpha_engine refactor | **BLOCKED — do not merge** |

**Recommended order:** **#983 first** (it unblocks the gate for everything else),
then #965 last or never as-is.

**#965 must not be merged blind:** `mergeable: false`, 23 files, 15 conflicts in
`alpha_engine/*` (+14230/−7442). It needs **one owner, one worktree, rebased on
repaired main**, a 157+ test bar, and cherry-picking of only its unique
non-`alpha_engine` files.

---

## 7. Outstanding work

1. **[HIGH] Add the TAA correction paragraph** to
   `reports/money_maker_per_asset_class_2026-11-19.md` — replace the 0.88/−19%
   citation with the 0.727/−44.55% measurement and the drawdown-control
   restatement (§4.1 above). Cite `reports/TAA_SETTLE_2026-11-19.md`.
2. **[HIGH] Merge PR #983**, then confirm `CI Tests` on `main` actually goes green
   (`gh run list --workflow="CI Tests" --branch main --limit 1`). Do not assume.
3. **[MED] Wire or delete `demote_proven_without_alpha()`** (§3).
4. **[MED] Fix the forward ledger** — make the 7 pre-registered slots write rows
   and populate `fees`/`funding` (§4.2). Until then the ledger is not evidence.
5. **[LOW] Updates page card** for any user-facing claim — must go **immediately
   before** `<!-- AUTO-INJECTED:INCIDENTS-ENHANCEMENTS:START -->` (≈line 113) of
   `updates/index.html`, then `python3 tools/deploy_audit_files.py --only updates`.
   Git push does **not** update the live site.
6. **[BLOCKED] #965** per §6.

---

## 8. Method notes worth carrying forward

1. **A hotfix that adds a symbol your consumer test imports trades a crash for a
   red suite.** Run the specific gating test *file*, not `python -c "import ..."`.
2. **Local full-suite results are not a proxy for CI** (69 local vs 6 CI here).
   Use `gh run view <id> --log-failed` for ground truth, or differential testing
   (same machine, patch off vs on) — that is what produced the clean 75→69 /
   6-fixed / 0-broken proof.
3. **`git stash pop` conflicts** because pytest mutates tracked data JSONs in this
   repo. Recovery used: `git checkout -- .` then re-apply the saved `.patch`. Keep
   the patch file on disk; do not rely on the stash.
4. **Do not reuse a COMS retained topic** (§5.1).
5. **Distinguish "workflow healthy" from "strategy evidenced".** An 11-run green
   cron with `n_closed: 0` is operational health, not edge.

---

## 9. Verification commands used

```bash
# the 6 failing files + siblings
python3 -m pytest tests/test_selection_alpha_coverage.py tests/test_audit3_falsifiers.py \
  tests/test_audit3_g8_defaults.py tests/test_audit3_tribunal.py \
  tests/test_audit3_expectancy_gates.py tests/test_audit3_selection_alpha.py -q
# -> 77 passed

# differential (patch off vs on, CI's marker filter)
python3 -m pytest tests/ -q -m "not integration and not network" 2>&1 \
  | grep -oE "^FAILED [^ ]+" | sed 's/FAILED //' | sort > /tmp/fails_<state>.txt
comm -23 /tmp/fails_bare.txt /tmp/fails_patched.txt   # fixed
comm -13 /tmp/fails_bare.txt /tmp/fails_patched.txt   # broken (empty)

# CI ground truth
gh run view 44649438938 --log-failed | grep FAILED
```

---

*Written by `copilot-cli-moneyresearch`. Numbers above were read from the live
files/APIs at write time, not recalled. Where a prior session's number disagreed
with the file, the file won and the disagreement is recorded (§4.1, §5.4).*
