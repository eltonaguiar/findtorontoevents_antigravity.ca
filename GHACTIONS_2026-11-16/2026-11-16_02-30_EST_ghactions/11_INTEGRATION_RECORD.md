# 11 — Integration Record (batch PRs, QA evidence, open threads)

**STAMP: 2026-11-16_02-30_EST (07:30 UTC)** · closes the "finish all todos" round ·
companions: `IMPLEMENTATION_PLAN.md` (protocol), `SUMMARY.md` (fleet map), `05`–`10`.

## 1. Batch ledger — 5 PRs (all QA Layer-1 verified before landing)

| PR | Scope | QA evidence (coordinator, personally re-run) | Run-based validation |
|---|---|---|---|
| #836 | P0 scheduled-paths (yf window+retry, pead push-retry+loud, alpha-live sync retry) | YAML×3, anchor asserts | tonight 22:11 pead + 22:49 yf (the failing scheduled paths) |
| #837 | summary_picks WR counts (TP_HIT/SL_HIT) | py_compile + SQL-count sanity | next audit cycle: per-class WRs non-zero |
| #838 | OPEN-bloat gate + pnl_pct NULL + resolved-unknown (6+2 files) | 31/31 new + 476/2-pre-existing + 2 wiring sites compiled | next cycle: `db_health.json` gains `open_bloat{open,active,fail}`, tier honest (expect red at 91,855/21) |
| #839 | no-op gating + guardian v1.1 + `queue:max` ticks + permissions ×20 + pins + deploy hygiene (35 files) | 29/29 + dry-run exit 0 + **`on:`-drift NONE ×32** + 356 YAMLs | **08:37 guardian = live v1.1 proof** (timeout_kill rows, CANCEL BUCKETS, `derived_from`) |
| #840 | PM momentum root-cause (Gamma lexicographic sort) + alias gate + alert attribution + REDUCE enforcement + Hyro contract + un-ghost (14 files) | 29/29 + 477/3-pre-existing + attribution clean | next cycle: momentum rows/status loud, `kimi_riseoftheclaw` replaces `unknown`, label gated |

Pre-existing test failures (forex-gate env state, 2–3 depending on subset) verified identical
with every batch stashed — not ours, flagged to owner.

## 2. Cross-fleet state at close (§0.5 reconciliation)

- **Fleet B (auditpage)**: #835 truth-layer merged; ghost-prose = fixed (their E:\ copy of the
  cross-PC patch is redundant). The "three-way ghost contradiction" P0 = display side DONE;
  the data-layer cleanup (actual cohort disposal) remains the owner's quarantine-not-delete policy call.
- **Cross-PC fleet (E:\ machine)**: `DATA_QUALITY_REMEDIATION_2026-11-16.md` still stranded on
  that box — recommend they commit it to `GHACTIONS_2026-11-16/` here (3rd stranding-class item tonight).
- **ghactions-v3**: see §3.
- **Stash note**: S2 preserved foreign WIP it found in `/tmp/kilo/drop2` → `/tmp/kilo/drop2-preserve-20261116-0709/` + `stash@{0}` in that worktree. S3's equivalent content landed via #839 — after #839 merges, the preserved copy + stash entry are safe to drop (recorded here so nobody pops it blindly).

## 3. v3's 2 hardening commits (P1-7)

_(recorded at close: see the live check in the session — if still unmerged, they are
`60141976a83` regime-terminal push harden + `e6f3932991d` ueps/audit-impact step harden;
fallback = cherry-pick into a follow-up PR, per plan.)_

## 4. WIRED_IN archive plan (CF5, docs-level)

- `WIRED_IN/2026-11-15_0708*/`, `2026-11-15_0711_buffy/`, `2026-11-15T0150Z_childlike-airport/`,
  `2026-11-15_0725_inspect-wt/` = research artifacts. Plan: move under `WIRED_IN/archive/2026-11/`
  with a `MANIFEST.md` (per-folder: purpose, outputs consumed by /audit (childlike cards ✓),
  verdicts). Deferred owner-side: nothing depends on their paths at runtime except
  `wired_in_childlike_active_picks.json` (regenerate by copying, not by re-running experiments).
- KPI labels (CF5): the /audit KPI tiles need `n`/cohort labels (e.g. "Verified Realized WR 51.3%
  (269 trades)") — template display-only change; queued as display work alongside the
  theory-panel polish.

## 5. Open items after this round (all documented, nothing lost)

1. Owner decisions: sports five · AsterDEX gate · AI Tournament · QA secrets #786 · PM promotion
   gates · alpha-fast interval (ρ>1) · `exit_price=entry_price` flat-exit fabrication ·
  historical `pnl_pct` DB migration (`--backfill-pnl-null --execute`, per-table, dry-run first).
2. Design follow-ups: PREDICTION class/binary resolver · KIMI emission stamps real `algorithm`
   (51 rows attributed downstream only) · guardian R-rule baseline re-derivation continues at 08:37.
3. Watchers: 07:36 PR-run monitor · 08:00 cron · 08:37 guardian debut · tonight's #836 proofs ·
   next-cycle proofs for #837/#838/#840.

## 6. Model/credit handling (fleet-wide lesson adopted)

Context-limit victims pin to the LONG_CONTEXT pool (`particle-1:free` / `longcat-2.5:free` /
`Mercury-3` ~1M) — part of the babysitting ladder (1,608-model catalog) alongside
`Auto Efficient` → `agnes-2.5-pro` → `Glyph Cluster` → `Auto Free`/`glm-4.7-flash`.
