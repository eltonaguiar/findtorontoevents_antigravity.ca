# Pre-merge research & proofs-of-concept (2026-11-19, final run)

**Author:** Kilo (worktree `universal-pisces`, branch `review-financial-prediction-strategies`)
**Purpose:** de-risk the upcoming worktree merge + deploy with measured evidence.

---

## 1. Merge readiness — CLEAN

Both peer forward branches are already merged into `origin/main`
(`git merge-base --is-ancestor … origin/main` = YES for
`feat/forward-observations-contract` and `feat/forward-gate-and-ingest`). My
branch is based on the older `f9e6c82`; the real integration is
`HEAD + origin/main`.

Evidence:
- `git merge-tree --write-tree --name-only HEAD origin/main` → **exit 0, no conflicts**.
- The merged `alpha_engine/audit3_tribunal.py` compiles (1,434 lines) and the
  merged `reports/hypothesis_registry.json` parses with **104 hypotheses**.
- File overlap is confined to 3 files, and every hunk is **disjoint**:

| File | Mine | Peer | Conflict |
|---|---|---|---|
| `alpha_engine/audit3_tribunal.py` | evaluate_cell 2× gate, required_n, _pod_for, alpha post-pass | `_promote()` forward gate, `forward_gate_block`, `--forward-ledger` | **none** (closest hunks ~21 lines apart) |
| `alpha_engine/audit3_selection_alpha.py` | FX `bare =` mapping | `_conn()` credential fix | **none** |
| `reports/hypothesis_registry.json` | +5 hypotheses at EOF | 1-line H-119 result edit | **none** |

**Recommended order:** merge `origin/main` into this branch (or rebase the 10
commits onto it), then run the combined suites:
`test_audit3_*` + `test_forward_observations*` + `test_stop_fill_overshoot`.

**Semantic notes (not conflicts):**
- Forward gating becomes **default-on** after the merge (peer's `main()` passes
  `forward=forward_gate_block(...)`); the committed `reports/forward_observations.jsonl`
  (430 H-119 rows) is the default ledger. Decide whether CI should pass
  `--forward-ledger` explicitly / assert its fingerprint.
- My 5 pods are `observe`, and the peer's forward gate skips anything
  `!= "pre_registered"` — consistent; they will not appear under `forward_gate.pods`
  until promoted.
- My alpha post-pass iterates `cells`, including symbol/segment proxies the peer
  now forward-gates; both only downgrade, so ordering is safe.

## 2. Forward-observation FK compatibility — COMPATIBLE

The peer's `alpha_engine/forward_observations.py` validates `hypothesis_id` by
recursively collecting every `"id"` in the registry
(`hypothesis_ids()` L111–138; FK check L174–178) and **ignores status**. A
direct test confirmed `H-2026-11-19-01..05` resolve with no errors (and a typo
is correctly rejected as a dangling FK). **No fix required.**
Caveat: promotion requires `intrabar_first_touch is True` on every row
(L201–202, L399); my observe pods are close-only, so any adapter that emits for
them must supply an intrabar first-touch resolver.

## 3. Stop-fill overshoot — PoC reproduces the peer finding

`alpha_engine/stop_fill_overshoot.py` run on the live 3,500-row slice, stopped
cohort only:

| Slice | n | planned risk | realized loss | overshoot |
|---|---|---|---|---|
| CRYPTO | 1,113 | 1.878% | 2.939% | **+1.061pp** |
| overall | 2,020 | 2.650% | 2.901% | +0.250pp |

The quant-audit figure was 1.919% → 2.990% = +1.071pp (different window), so the
measurement reproduces. This PoC also found and fixed a real bug: the module
originally counted **every** row, so winners drove the overall mean negative.
It now filters to stopped trades by `status`/`exit_reason` (`stopped_only=True`).

## 4. Canonical full-book — the slice flatters the system

Scoring the canonical resolved view (8,735 rows, 53.5%) instead of the 3,500
export slice (21.4%):

- 0 PROVEN, **0 CANDIDATE** (was 1), 11 KILL cells, **3 KILL classes**.
- `luxalgo_confluence SHORT` CANDIDATE → **WEAK** (n=1,924, −0.089%/trade).
- FOREX WEAK → **KILL**.

A workflow guard now fails the run if the payload declares the canonical view but
the sidecar was not fetched, so the 21.4% slice can no longer be published
silently.

## 5. audit2 deploy — exact change applied

`/audit2` was a 404 and `audit_dashboard/v2/index.html` is orphaned (in no
deploy list). The audit3-ledger FTP step now also uploads
`audit_dashboard/audit2.html → /audit2/index.html` and
`audit_dashboard/audit2.js → /audit2/audit2.js`; the page reads
`../audit3/audit3_ledger.json`, so no data upload is needed. YAML validates.

---

## Commit log on this branch (10 commits)

```
3574c4adc ci(audit3): deploy /audit2 alongside /audit3
6eb02dbb5 fix(stop-fill): count only stopped trades
4c7c55e4c ci(audit3): fail loudly when canonical view declared but unfetched
05bb08d15 feat(audit2): candidate & methodology library page
36455c9d4 docs(audit3): canonical full-book verification
88e5fda85 docs(audit3): live rebuild verification (2x gate + power)
ccaa2685e feat(audit3): selection-alpha gate
1ed98e59a feat(audit3): per-cell required_n + MDE
4e8ada007 feat(audit3): observe pods + FX mapping + stop-fill module
408918cad feat(audit3): 2x-cost stress required gate
```

*Not investment advice.*
