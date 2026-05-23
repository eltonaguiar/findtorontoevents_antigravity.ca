# Doc Reorg Safety Audit — 2026-05-08

Hermes (other-PC) proposed moving 200+ `.md` docs into `docs/` hierarchy. Audit checks: which moves are SAFE, which would BREAK live infrastructure (events page / favcreators / audit / hyrotrader).

## ⚠️ Files that CANNOT move without code changes

| ref | file → would break | fix required first |
|---|---|---|
| `tools/_insert_audit_review_index.py:23` | hardcoded GitHub URL → `docs/AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md` | Update the URL string before moving file |
| `audit_trail/dashboard_generator.py:9854` + `:10035` | `research_ref="updates/long_term_value_project_2026-04-27/research/13_goldmine_audit.md"` embedded in dashboard payload | Update generator before moving |
| `CLAUDE.md` (project root) | Project instruction file — Claude Code reads from root only | **DO NOT MOVE** |
| `AGENTS.md`, `CODEBUFF.md` (project root) | Peer-agent instruction files; convention-based root location | DO NOT MOVE |
| `README.md` (project root) | GitHub default | DO NOT MOVE |
| `AUDIT_BLUEPRINT.md` (project root) | freebuff audit infra references via `tools/db_review/specs/` symlink + cross-doc references | Keep at root |

## ✅ Safe to reorganize (NEW dir, additive only)

These categories are reference-by-glob or one-off — moving is non-breaking:

| category | current location | safe target | safety rationale |
|---|---|---|---|
| Daily audit reports | `updates/2026-*-daily-*.md` | `docs/audit/daily/2026-*.md` | `updates/index.html` is hand-built nav; no auto-scan generator |
| Deep-dive analyses | `updates/*-deep-dive*.md` | `docs/audit/deep-dives/` | same |
| Swarm session logs | `updates/*-swarm*.md`, `updates/VERBATIM_*.md` | `docs/audit/swarms/` | same |
| Asset-class deep dives | `updates/2026-05-05-buffy-asset-class-*.md` | `docs/audit/asset-classes/` | same |
| Sports-betting docs | `updates/*-sports-*.md` | `docs/sports-betting/` | live `live-monitor/sports-betting.html` doesn't link to them; refs only inside other .md |
| Memecoin docs | `updates/memecoin*.md` | `docs/memecoins/` | same |
| Strategies docs | `100_ALGORITHMS_MASTER_CATALOG.md`, `25_Quantitative_Trading_Algorithms.md` | `docs/strategies/` | check for grep-refs first |

## ✅ Safer middle ground — ADDITIVE-ONLY

Hermes' `docs/` proposal has a backward-compat clause: **keep `updates/`** alongside new `docs/`. Recommend this exact pattern:

1. Create `docs/INDEX.md` — single catalog/TOC pointing to existing scattered locations. **Zero file moves.**
2. Create `docs/audit/`, `docs/audit/hyrotrader/`, `docs/sports-betting/`, `docs/events/`, `docs/memecoins/`, `docs/strategies/`, `docs/agents/`, `docs/tools/`, `docs/projects/` — empty stubs each containing a 1-pager pointing to canonical files in their CURRENT location.
3. Move ONLY safely-isolated docs (no incoming refs) on a slow rolling basis, one PR at a time, with grep-verify pre-flight.

## Pre-flight checklist before ANY move

```bash
# 1. grep for hard refs in all production paths
F=updates/2026-04-15-audit-getVerifiedTier-index-corruption.md
grep -rln "$F" tools/ audit_trail/ audit_dashboard/ alpha_engine/ .github/

# 2. grep in HTML for href to it
grep -rln "$F" *.html updates/*.html audit_dashboard/*.html

# 3. check generator outputs (last 7d)
grep -rln "$F" reports/ swarm_runs/ tmp/ 2>/dev/null

# 4. if all 3 are 0 → safe to move
git mv $F docs/audit/$(basename $F)

# 5. update updates/index.html nav if listed
# 6. commit with bold "doc-reorg" scope
```

## Live HTML dependencies (touch with care)

Pages that go live on findtorontoevents.ca:
- `TORONTOEVENTS_ANTIGRAVITY/index.html` (4,845-line homepage; per CLAUDE.md NEVER replace)
- `live-monitor/sports-betting.html`
- `audit_dashboard/index.html` (auto-generated from `template.html`)
- `audit_dashboard/template.html` (edit THIS, not index.html)
- `audit_dashboard/hyrotrader/index.html`
- `updates/index.html` (hand-built nav; if you move an `updates/*.md` you may need to update the link target inside this file)
- `hub/index.html`
- `live-monitor/research/live-vs-research.html`

None of these reference `.md` files at runtime — they're all static HTML or generated from JSON. **Doc reorg won't break the pages themselves.** But code that REGENERATES them (e.g. `dashboard_generator.py`) does have hardcoded `.md` refs in research_ref fields, so doc moves can break dashboard payload integrity.

## Recommendation

**Adopt Hermes' plan with these constraints**:
1. Keep all root `.md` files (CLAUDE.md, AGENTS.md, README.md, AUDIT_BLUEPRINT.md) at root.
2. Keep `updates/` directory intact (backward compat).
3. Build `docs/` as additive new structure, not migration target.
4. For each candidate move, run the 4-step pre-flight before `git mv`.
5. Update `dashboard_generator.py:10035` BEFORE moving `updates/long_term_value_project_2026-04-27/research/13_goldmine_audit.md` (or just leave that one).
6. Update `tools/_insert_audit_review_index.py:23` BEFORE moving `docs/AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md`.

## Estimated risk per category

| category | risk | move? |
|---|---|---|
| `updates/2026-*.md` (200+ files, mostly orphaned reports) | LOW | YES — slowly, with pre-flight per file |
| Root `.md` files (~10) | HIGH | NO — leave at root |
| `docs/*.md` (~30) | MEDIUM | NO — already in docs/, just reorganize internally |
| `tools/*.md` (~5) | LOW | YES — move to `docs/tools/` |
| `live-monitor/*.md` | MEDIUM | check refs first |
| `audit_dashboard/*.md` | MEDIUM | leave; closely tied to generator |

## Outstanding

- Build `docs/INDEX.md` first as zero-risk metadata layer
- Spawn a single-pass agent to grep-validate all 200+ candidate moves before any `git mv`
- Don't merge Hermes' aggressive bulk-move PR; convert to incremental per-file PRs

## Related
- `database/` reorg (this session) — same additive pattern, succeeded
- `reports/` flat dir — should consider moving recent ones to `docs/audit/2026-05-*/`
