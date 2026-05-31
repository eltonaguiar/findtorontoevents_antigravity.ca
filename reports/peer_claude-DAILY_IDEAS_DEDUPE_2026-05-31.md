# DAILY_IDEAS.MD Dedupe + Status Sweep — 2026-05-31

Companion to wkab9g07u testing-protocol dedupe. Scope: every file matching `DAILY_IDEAS*`, `*daily_idea*`, `*ideas_daily*`, plus narrow roadmap/idea-log glob (excluded worktree noise from `.qwen/`, `.kilo/`, `node_modules/`, `venv/`, `build/`).

## 1. Candidate inventory

| Bucket | Count |
|---|---|
| Total raw matches (broad pattern incl. ROADMAP/BACKLOG) | 1964 |
| Narrowed to `DAILY_IDEAS*` / `*daily_idea*` / `*ideas_daily*` | **706** |
| Living in `.claude/worktrees/` (ORPHAN_COPY by policy) | **682** |
| Repo-tree (non-worktree) | **24** |
| Repo-tree, root-level idea logs (per-AI variants) | 16 |
| Repo-tree, `reports/` synthesis/digest artifacts | 7 |
| Repo-tree, `tools/swarm/prompts/` | 1 |

## 2. Byte-level dedupe (md5)

### 2a. Root-level idea logs — all 16 are content-distinct

```
f4ec0b3f29b2ecd0899cbea03e9a0472  DAILY_IDEAS.MD                              <-- CANONICAL
b7c19c69b15a81282a2f56cc4bba7041  DAILY_IDEAS_KIMICLI_2026_05_16.MD
6adf6b1be641e1175bc37b5b04da5748  DAILY_IDEAS_GROK_2026_05_16.MD
af40fd085c8366d78218e30001ff16f1  daily_idea_cursor.MD
a36df7e521ce8672d157af48f83cb7e3  daily_ideas_ghcopilot_auto.MD
8767e86014dc44de653ca8d18c102046  daily_idea_antigravity.MD
9430ee50853c452f4f037705bfd89d97  DAILY_IDEAS_OLLAMA.MD
f7c698bf17b3e0e902ba9caa0659578c  daily_ideas_KimiCode.MD
906a0659f591452270c580977cbc5952  DAILY_IDEAS_PROMPTS.MD
85b15d216b3f0e293d07f958d9a20e6d  DAILY_IDEAS_OPENMONOAGENT.MD
ebcf009d30a2652bab0ff8cefe57f1ca  DAILY_IDEAS_LLMARENA_May162026.MD
88840b16dd3dcdf3640271ffadd50aba  DAILY_IDEAS_XIAOMIMIMO_May172026.MD
ad83d835a19062a002f0a8d88414ff8f  DAILY_IDEAS_CURSORCLI_2026_05_16.MD
57fa6b162bac1ad3257cf09de1bcfd8b  daily_ideas_nvidia.MD
b1ca2163f057e87144bf1e8cebad678b  DAILY_IDEAS_HUGGINGFACE.MD
16d0e422de21d2cd92f0c6b60d1cf076  daily_ideas_Kilocode_laguna.MD
```

No byte-dupes among root-level files (0 hash collisions).

### 2b. Worktree copies of `DAILY_IDEAS.MD`

682 worktree copies collapse to 2 distinct content hashes (`de9fad5b…`, `fc710c2b…`), both older than canonical. All ORPHAN_COPY.

**Byte-dupe groups across full corpus: ~690 redundant worktree copies (main file + per-AI variants mirrored ~43x).**

## 3. CANONICAL

```
./DAILY_IDEAS.MD
size: 260,448 bytes
mtime: 2026-05-31 22:44:39 UTC   <-- modified today
lines: 3,742
## headings: 56  (chronological, newest-at-bottom)
```

Last formal heading: `2026-05-29 — 200-day MA trend strategy tracking`. After that, an unheaded `2025-05-31` block (typo — should be `2026-05-31`) appended today containing the operator's hedge-fund-grade verification prompt.

## 4. Status keyword counts (canonical body)

| Keyword | Count |
|---|---|
| IMPLEMENTED / DONE / SHIPPED | 31 |
| TESTED / VERIFIED | 21 |
| REJECTED / REFUTED / KILLED | 22 |
| OPEN / TODO / PENDING | **62** |

## 5. Today's appended block (2026-05-31) maps to peer reports

| Peer report (today) | Maps to operator-prompt section | Status |
|---|---|---|
| daily-idea-1-statistical-edge-validation-framework | "how many trades for valid edge" | OPEN |
| daily-idea-2-hidden-edge-detection (in git-staged elsewhere) | "verified-alpha / pick_funnel permutations" | OPEN — file missing locally |
| daily-idea-3-ai-leaderboard-hedge-fund-stats | "quant stats vs B&H" | OPEN |
| daily-idea-4-tournament-portfolio-automation-broken | "Model Portfolios automation seems broken" | OPEN P0 |
| daily-idea-5-200d-ma-strategy-tracking | "SMA/EMA/HMA-200 variants" | OPEN |
| daily-idea-6-golden-persona-finder | "golden persona search" | OPEN |
| daily-idea-7-destructive-op-backup-policy | "backup to ejaguiar1_backtests" | OPEN policy |
| daily-idea-8-audit-text-needs-timestamp-automation | "/audit text date/time stamp" | OPEN UI |

## 6. Cross-reference vs today's 60-PR wave — 8 status changes proposed

| OPEN canonical idea | Today's PR/commit | Proposed status |
|---|---|---|
| Resolver intrabar / outcome mislabels | PR #208 + tournament resolver fix (per MEMORY) | OPEN → PARTIALLY-IMPLEMENTED |
| Confidence inversion gate for CRYPTO | PR #227 (`CONFIDENCE_INVERT_CRYPTO` off, commit 575475235) | OPEN → REJECTED |
| Tighter-SL for 2 CRYPTO strategies | commit 34ec109ec (price-path refute) | OPEN → REJECTED |
| R:R fix path for 2 CRYPTO winners + genome OOS | commit ca87f357b | OPEN → TESTED |
| Mercury 2 gap analysis | commit f703e9541 | OPEN → TESTED |
| FOREX whitelist P0 + PR-overlap coord | commit 40af55671 (peer inbox) | OPEN → TESTED |
| DATA INTEGRITY banner = db_health quick CHECK BUGS | PR #207 | OPEN → IMPLEMENTED |
| Model Portfolios automation broken | (none today) | OPEN → OPEN/P0 escalate |

**Net status-change proposals: 8.**

## 7. New ideas to add — 6 entries proposed

1. **ETF verdict-aggregation fallthrough (PR #351)** — class-floor not enforced before T-class.
2. **FUTURES outcome_resolver parity (PR #356)**.
3. **Anti-fabrication: 2-agent quote-confirm before code-diff PRs** — per `docs/AGENT_DIFF_FABRICATION_PATTERN_2026-05-31.md` (9% trustworthy rate measured).
4. **Concentration HHI>0.30 gate before DSR/SPA** — per CLAUDE.md (2 false-T1 PASSes on 2026-05-17).
5. **Persist DISPUTED banner + 14d/48h panels on pick_funnel.html** (commit c1b977997).
6. **Drain peer inbox before any FOREX-touching PR** — per peer DMs 2026-05-31.

**Net new-ideas proposed: 6.**

## 8. Worktree cleanup recommendation

682 worktree copies are stale and confuse multi-agent grep. Add soft-deny on `.claude/worktrees/**/DAILY_IDEAS*` or force pre-flight `git pull --rebase` on worktree spawn. Non-destructive.

## 9. Hand-off to wkab9g07u consolidate

Canonical path written to `/tmp/canonical_daily_ideas.txt`:
```
./DAILY_IDEAS.MD
```

Consolidate phase should:
1. Fix EOF block typo `2025-05-31` → `2026-05-31` + add proper `## 2026-05-31 — …` heading.
2. Apply the 8 status changes from §6.
3. Append the 6 new entries from §7.
4. Per-AI variants (`DAILY_IDEAS_KIMICLI`, `daily_idea_cursor`, etc.) intentionally DIVERGENT — leave them as per-agent scratchpads.

---

**Summary:** `DAILY_IDEAS:total_candidates=706:byte_dupes=~690:canonical_path=./DAILY_IDEAS.MD:open_ideas=62:status_changes_proposed=8:new_ideas_proposed=6`
