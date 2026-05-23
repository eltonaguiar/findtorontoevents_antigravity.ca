# Doc-PR Merge State Audit — 2026-05-03 UTC

**Audit window:** 24 h since last review pass (2026-05-02 → 2026-05-03)  
**Audit basis:** GitHub API via MCP + `git log --since='5 days ago' -- updates/ reports/ docs/`  
**Definition:** doc-PR = open PR whose changed files are *predominantly* under `updates/`, `reports/`, `docs/`, or top-level `*.md` files; excludes PRs primarily changing Python / JS / HTML even when they also touch docs.

---

## 1. Summary Table

| Metric | Count |
|--------|------:|
| Total open PRs (all types) | 9 |
| Doc-PRs (by file-path rule) | **1** |
| Stalled doc-PRs | **0** |
| Mergeable-and-green doc-PRs | **1** |
| Non-doc PRs (excluded from scope) | 8 |

> **Finding:** Of 9 open PRs, only **#724** passes the doc-PR test. All 8 others are primarily Python / config / JSON / HTML code changes; several also touch `updates/` or `reports/` files, but those are supporting artefacts rather than the primary payload. See §4 for the classification rationale per PR.

---

## 2. Per-PR Table (doc-PRs only)

| # | Title | Author | Age (d) | Last activity | CI | Review | Draft | mergeState | Stalled? | Stall reason | Recommended action |
|---|-------|--------|--------:|--------------|-----|--------|-------|------------|----------|--------------|-----------------|
| [724](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/724) | investigation(forex+crypto): deep-dives + FOREX rescue plan + 5 new strategies | eltonaguiar | 0 | 2026-05-03T03:49Z (≈14 h ago) | ✅ scan PASSED (03:52Z) | COMMENTED (Codex bot, non-blocking) | No | unknown* | **NO** | — | **MERGE-NOW** |

\* `mergeable_state=unknown` is GitHub's "not yet computed" state for a brand-new PR; the scan CI check passed cleanly so there is no known conflict or failure.

### PR #724 detail

- **Branch:** `investigation/forex-crypto-deep-dives-2026-05-03` → `main`
- **Commits:** 3 — all doc additions, no code changes
- **Files changed:** 6 — all `.md` / `.MD`
  - `FOREX_COMMODITIES_BONDS.MD` (top-level, 651 lines) — FOREX/COMMODITY/BOND recovery plan
  - `reports/deep_dive_FOREX_2026_05_03.md` — FOREX per-source autopsy
  - `reports/deep_dive_CRYPTO_quan_unknown_drag_2026_05_03.md` — CRYPTO drag source correction
  - `reports/FOREX_RESCUE_CONSOLIDATED_2026_05_03.md` — authoritative rescue plan (supersedes deep-dive)
  - `reports/forex_corrupt_filter_analysis_2026_05_03.md` — independently verified corruption-filter root cause
  - `reports/forex_new_strategies_2026_05_03.md` — 5 new FOREX strategy proposals
- **Key self-imposed hold:** "Peer ack on corruption-filter code fix before code PR" — this applies to a *downstream* code PR, not this docs PR. The docs PR itself has no outstanding blockers.
- **Stall flags checked:**
  - (a) updatedAt > 5 days: **NO** (0.6 d)
  - (b) mergeStateStatus DIRTY: **NO** (unknown, not DIRTY)
  - (c) CHANGES_REQUESTED ≥ 3 d stale: **NO** (no CHANGES_REQUESTED)
  - (d) CI FAILURE > 24 h: **NO** (scan PASSED)
  - (e) Draft with no update ≥ 7 d: **NO** (not draft)

---

## 3. Top 3 Unblock Recommendations

### R1 — Merge #724 without waiting for corruption-filter code PR

**Rationale:** All content is read-only investigation docs with CI green and no blocking review. The PR's own checklist separates the docs merge from the downstream code PR ("peer ack required before *code* PR ships"). Leaving docs unmerged delays the audit-trail reference for peers working on the follow-up fix. Action: assign a peer reviewer, verify no rebase needed (base SHA `72ac79ff` may have drifted on fast-moving `main`), then merge.

### R2 — Watch for base-SHA drift on #724

**Rationale:** `main` is extremely active — 50+ commits happened in the time the local checkout was in detached HEAD. The PR base was `72ac79ffc6` at creation. By the time a reviewer approves, the branch may need a rebase to stay compatible with any changes to `FOREX_COMMODITIES_BONDS.MD` or the referenced `dashboard_generator.py` lines. A quick `git log --oneline main..investigation/forex-crypto-deep-dives-2026-05-03` before merging will confirm.

### R3 — Establish a lighter doc-PR merge lane

**Rationale:** The sole doc-PR this cycle (#724) was opened and could already be merged the same day — the 0-stall rate is healthy but brittle. On a day with more doc-PRs, the queue could quickly stall without a designated reviewer lane. Recommend labelling doc-PRs with `type: documentation` and routing to a fast-merge policy (1 approving review → merge, no 24 h wait).

---

## 4. Classification Notes for Non-Doc PRs (excluded)

The following 8 PRs were evaluated and excluded because their *primary payload* is code, not docs. Some touch doc files as supporting artefacts.

| # | Title | Primary files | Why excluded |
|---|-------|--------------|-------------|
| 723 | feat(B18): shadow-mode auto-promotion | `audit_trail/*.py`, `tools/*.py`, `tests/*.py` | Code-first; `updates/` and `reports/` are supporting artefacts |
| 676 | data(events): quality follow-up | `events.json`, `next/events.json` | Data files (JSON), not documentation |
| 661 | Infrastructure v2.0 | `alpha_engine/*.py` (4 files + `__init__.py`) | Predominantly Python; `INFRASTRUCTURE_README.md` is inside `alpha_engine/` not top-level `docs/` |
| 660 | P0 Emergency Gate Fixes | `config/hf_quality_gates.json`, `config/per_asset_thresholds.json` | Config JSON is primary; `EMERGENCY_GATE_FIXES.md` is one of three files |
| 644 | docs(audit): per-asset quality gate plan | `audit_trail/quality_gates.py`, `dashboard_generator.py`, `quality_monitor.py`, `check_asset_quality_gate.py`, `template.html`, `.github/workflows/audit-dashboard.yml` | 6 code/config files vs 3 doc files; code is the primary change |
| 615 | fix: resolve 5 scanner blockers | `alpha_engine/production_scanner.py`, `inverse_edge_system.py`, `circuit_breaker.json`, `cta_strategy_replicator.py` | Primarily bug-fix Python; `updates/` doc is one of five files |
| 608 | test(tradingagents): B26 smoke test | `tests/test_tradingagents_smoke.py` | Primary deliverable is a test file; `reports/feedback/` docs are supporting |
| 597 | P0 fixes + USDCHF investigation | `alpha_engine/isolated_signal_integrator.py`, `alpha_engine/pick_revalidator.py`, `tests/*.py` | Code-first (P0 fix + new module); `updates/` doc is supporting |

---

## 5. Recent Doc Activity on main (git log --since='5 days ago')

```
2026-05-03  424dd210  Claude Gainer ML scan 2026-05-03 17:35 UTC [skip ci]
2026-05-03  cb3d4ee8  MOMENTUM CATCHER [2026-05-03 17:23 UTC] — 10 picks [skip ci]
```

No direct-to-main doc commits found under `updates/`, `reports/`, or `docs/` in the last 5 days. All doc activity this cycle has landed exclusively via PRs (as expected for a multi-agent repo).

---

*Generated by Claude Code audit agent. Read-only pass — no audited PRs were commented on, closed, or merged.*
