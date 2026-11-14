# Peer Review R2 — Reviews A (finpredict-v2)

**Archive:** `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/`
**Audit clock:** 2026-11-14T16:05Z (primary payload `generated_at 2026-11-14T14:30:07Z`)
**Reviewer:** R2 peer-review subagent (read-only)
**Scope:** inventory, key claims (quoted, sourced), strengths, weaknesses/gaps, merge/recommendation for master plan.

---

## 1. Inventory

Directory entries: `INDEX.md`, `MASTER_AUDIT.md`, `PEER_CROSSREF.md`, `raw/`, `recommendations/`, `sub/`.

- **Top-level `README.md`: NOT FOUND.** `INDEX.md` (59 lines) serves as the archive index/deliverable map. A separate `recommendations/README.md` documents the remediation tree.
- `MASTER_AUDIT.md` — 438 lines, primary deliverable (exec scorecard, actions health, per-class actives, frozen data, closed picks, verdict, peer reconciliation, UNVERIFIED list). Read lines 1–60 (scorecard + actions health) + headlines cited below.
- `PEER_CROSSREF.md` — 66 lines; v1/v2/v3/v4 + `inspect-wt` transcript matrix.
- `sub/` — A_actions_health.md, A_workflow_matrix.csv, B_dashboard_freshness.md, C_crypto.md (220), D_non_crypto.md, E_statistical.md (374), F_sources.md, G_peer_reconciliation.md (135). Required files read: `C_crypto.md`, `E_statistical.md`, `G_peer_reconciliation.md`.
- `raw/` — many live JSON payloads, GitHub-API captures (`A_workflows.json`, `A_runs500.json`), Binance klines, scripts (`fetch_jobs.sh`, `fetch_full24.sh`, `wf_ids.txt`, `log_ids*.txt`). `raw/MANIFEST.md` (41 lines): full `dashboard_data.json`/`dashboard_payload.json` (48 MB) + `pf_registry.json` (30 MB) + logs (~799 MB) were **pruned** to keep the commit small; all reproducible via curl/gh commands listed. Retained small evidence files kept.
- `recommendations/` — `QUICK_WINS.md` (top 12 P0), `overall/{ROADMAP,DATA_CONTRACT,CI_GATES}.md`, `per_asset_class/*.md`, `patch_plan/{P0_QUICK_WINS,P1_STRUCTURAL,acceptance_tests}.md`, `peer_review/` (4 reviewer memos + REVIEW_SYNTHESIS.md).

## 2. Key claims (quoted, sourced)

- **Headline verdict** (`MASTER_AUDIT.md:28-32`): fleet policy-clean ledger "n=22,941, WR 42.21%, PF 0.2657, z=−23.60. 0/9 asset classes money-ready. The visible winners are explained by ~32.9 expected false positives at N=658 tests plus a correlated single-source resolver artifact plus survivorship (63% of picks never resolve)."
- **Actions health** (`MASTER_AUDIT.md:37-48`): 365 workflows (361 active); **24 failing in 24h / 88 in 7d**; 4,109 runs/24h → 214 failure/82 cancelled; 20 never run; audit-dashboard cancels ~1/3 runs and takes 80–104 min vs 30–35 documented.
- **Active picks** (`MASTER_AUDIT.md:20`): "Only 20 curated rows; 19/20 PnL = 0; raw inventory is 4,148 rows, majority zombies/unpriced." `PEER_CROSSREF.md:44` ("Curated active = 20") and `:27` (`active_raw ≈ 4,148`).
- **Closed picks** (`MASTER_AUDIT.md:22`): 42.2% WR, sum −469.5% on 3,500 rows; only 10 closes <24h old.
- **Crypto** (`sub/C_crypto.md:3` verdict FAIL; `:48`): active_raw crypto 3,577 rows, EXPIRED 3,100 (86.7%), only 75 (2.1%) ever resolved; `:51-52` pnl_pct==0.0 = 3,322/3,577 (92.9%), current_price null = 3,170 (88.6%). Zombie factory (`:150-160`): `inverse_mutations`/`inverse_luxalgo_confluence` re-emit 2,267 rows daily since 2026-05-23 (20 symbols, EXPIRED/zero-PnL/null-price). NEAR +2.74% plausible vs Binance (3.16–3.82%) (`:125-131`); price feed sound, dashboard cached rows stale (`:34`).
- **Statistical** (`sub/E_statistical.md:5`, headline FAIL): canonical closed n=22,941, WR 42.21%, PF 0.2657, z=−23.60 (`:70`); search space N=658 observed strategies, E[FP]=32.9 at α=0.05 (`:146,150`); 24 significant-WR strategies all `single_source_pct=1.00` 90–100% WR artifact cluster (`:97-114`); anti-overfit PBO invalid (T=20, unordered rows) (`:180-184`), Reality Check did not run (`arch` missing) (`:188`), DSR median 0.0033, 69/80 OVERFIT (`:169-172`); 63.2% open survivorship (`:243`); `summary_picks` WR>100% denominator bug (`:288-298`). Bottom line (`:374`): "reported profitability is a multiple-testing + survivorship + resolver-artifact composite, not a genuine edge."
- **Peer reconciliation** (`sub/G_peer_reconciliation.md:11,13`): availability verdict PASS — three independent peer subtrees exist and agree on the negative verdict; transcript `chat_transcript_2026-11-14.md` NOT FOUND on Linux (`:54`); "61% spot-flicker" and "37 active in June" unsupported (registry flicker 7.7%; 37-active is May 2) (`:68-69`); five different "active" counts coexist (20 / 4,148 / 263 / 4,310 / 0) (`:94`).

## 3. Strengths

- **Multi-surface evidence discipline:** every number traced to a live file, API response, or named peer artifact; UNVERIFIED markers used honestly (E §5, C §10, G §3). No invented figures.
- **Cross-peer reconciliation is the strongest asset:** `PEER_CROSSREF.md` builds an explicit agreement matrix and explains contradictions (e.g. v4 "0 active / 26d stale" = stale-snapshot artifact; live surface fresh at 1.63h).
- **Independent external verification:** C verifies dashboard PnL against Binance/Coinbase/CoinGecko and concludes the price feed is sound while pick data is broken — separates the two failure modes.
- **Actionable, implementation-ready remediation:** recommendations carry `file:line` targets, a ranked P0 set, a data-contract schema v2.0.0, CI gates G1–G13, and acceptance tests; ground rules prevent fabrication/destructive cleanup/honesty regressions.
- **Careful bias accounting** (E §6): quantifies flicker, dollar-scale, dedup, policy-exclusion, open-pick survivorship, ghost rows (22,947), and net direction; conclusion robust (even filtered fleet loses).

## 4. Weaknesses / gaps

- **Top-level README missing** — INDEX.md substitutes but is thinner on narrative than a README would be (minor).
- **Payloads pruned:** the primary 48–66 MB live payloads and pf_registry are not retained (only manifests + commands). Re-verification requires a refetch and the numbers are snapshot-bound to 14:30Z; fine for review, but the evidence is not self-contained.
- **Peer-reported figures not independently re-derived** (G §2 claim 11, `:337`): the PF 0.94 / 126-systems summary and v3's "12 tests" vs "11 tests" are passed through as peer-reported (marked UNVERIFIED).
- **Some claims rest on a single `generated_at` snapshot;** freshness and count figures (e.g. 20 curated / 4,148 raw) are point-in-time and would drift after the next hourly rebuild.
- **Intra-v4 contradiction unresolved** (G §3, `:96`): "empty live table" vs "25 top-25 picks / 4,361 open" — flagged but not settled.
- **Root causes of workflow failures remain UNVERIFIED** (step log text not fetched; `MASTER_AUDIT.md §8`).

## 5. Recommend for master plan

- **Adopt this archive as the backbone of the master review:** it is the only integration that cross-references all peers (v1/v2/v3/v4) and separates verified vs attributed claims; `MASTER_AUDIT.md` + `PEER_CROSSREF.md` + `sub/` form a coherent core.
- **Merge `E_statistical.md` as the canonical statistics section** (multiple-testing N=658, PBO/DSR/RC invalidity, survivorship, summary_picks bug) with `G_peer_reconciliation.md` for the broader peer landscape.
- **Merge `C_crypto.md` for all crypto/price-integrity remediation** (zombie quarantine, zero/null entry rejection, SL<entry<TP enforcement, dedup, no `current_price=entry` publication).
- **Carry the corrected numbers forward:** 20 curated / 4,148 raw / 263 concentration; flicker 7.7%; live 14d sum −333.2% (not −1.4%); 37-active is May 2 (Q June).
- **Publish the v4 archive and `wt-audit-prediction-system/audit_output/` on a clean branch** before citing paths (currently uncommitted) — G §4 rec 9.
- **Do NOT merge without qualification:** "37 active in June", "61% spot-flicker", "last-14d −1.4%", v4 noncrypto "dead since June" verdicts (June-snapshot-based).
