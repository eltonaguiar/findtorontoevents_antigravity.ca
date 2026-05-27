# EAGLE Meta-Synthesis — 5-Partner Review Consolidation

**Model / Provider:** Claude Opus 4.7 (Anthropic)
**Session timestamp:** 2026-05-27 02:18 EDT (06:18 UTC — note: May uses EDT/UTC-4, the user-requested "EST" label is preserved in the filename per convention)
**Scope:** Meta-review of 5 partner-agent EAGLE responses + cross-check against canonical JSON + dashboard reconciliation + recommended unified action set

---

## The 6 partner files reviewed

| # | File | Model / Provider | Lines | Style |
|---|---|---|---|---|
| 1 | `reports/EAGLE_2026-05-27_0212_EST_Grok43_xAI_full_audit_90day_plans_gates_strategies_review.md` | Grok 4.3 (xAI) | 157 | Full audit |
| 2 | `reports/EAGLE-2026-05-27-quick-wins-claude-sonnet46-copilot.md` | Claude Sonnet 4.6 via GitHub Copilot | 275 | Quick-wins focused |
| 3 | `reports/EAGLE-2026-05-27-remaining-items-claude-sonnet46-copilot.md` | Claude Sonnet 4.6 via GitHub Copilot | 318 | Remaining-items focused |
| 4 | `updates/EAGLE_2026-05-27_0615EST_qwen-coder_alpha_engine_review.md` | qwen-coder | 299 | Alpha-engine drill-down |
| 5 | `EAGLE_2026-05-27T06-10-51_EST.md` | (no model signed) | 68 | Skeleton stub |
| 6 | (pasted by user 02:50 EDT, not file-committed) | **Mercury 2 (Inception Labs)** | ~120 (paste) | Template + tooling-focused — explicit "cannot read files locally", produces empty strategic-review TABLE for user to fill |
| 7 | (pasted by user 02:55 EDT, not file-committed) | **MiMo-V2.5 (Xiaomi LLM Core Team)** | ~600 (paste, 5 deliverables) | Full deliverable set: dedup skill + strategy review + quick wins + remaining items + DB schema. Explicit "GitHub + local 90-day plan files inaccessible — review built FROM INCIDENTS DASHBOARD ONLY" |
| 8 | (pasted by user 03:05 EDT, not file-committed) | **MiniMax Agent (researcher)** | ~500 (paste, 3 deliverables) | Quick wins + remaining items + 5-table DB schema with **audit-log tables** (incident_resolution_log + enhancement_progress_log). Explicit GitHub/local file fetch failed — built from web audit only. Adds 5-phase 12-week roadmap + prioritization matrix + Python query API examples. |

### Mercury 2 (partner #6) — what it added

Mercury 2 explicitly stated it has no file-system access ("I cannot directly read the files on your local drive"). Its contribution is:

1. **A working Python dedup script** — SHA-256 hash + shortest-path-wins; same logic as my `tools/dedup_md_files.py` (independent re-derivation = validates the approach).
2. **Empty per-class table TEMPLATE** the user can populate — columns: `Asset Class | Key Winning Picks (filtered) | Reason for Filtering | Suggested Exemption Criteria | "Sure-thing" Oscillating Trades | Top-Notch Strategy`. **This is the right shape for what the user actually asked for** ("picks that won big but were filtered", "exemption after hot streak", "trades that oscillate between 2 prices").
3. **Compact SQL schema** (single `enhancement_incident` table with `tags TEXT[]`, `related_files TEXT[]`). Different from my 3-table proposal (`roadmap_items` + `roadmap_item_history` + `roadmap_item_reviews`). Trade-off:
   - Mercury 2's design: simpler ingest, harder to audit status-history (no per-change tracking)
   - My design: heavier ingest, full audit trail + per-reviewer attribution
   - **Recommendation:** start with Mercury 2's flatter schema for v1 (faster to ship), migrate to my history+reviews schema in v2 when reviewer-attribution becomes load-bearing.

**Mercury 2 net contribution:** the column-shape of the strategic-review table is the missing piece across the prior 5 partners. None of #1–#5 explicitly named "exemption-after-hot-streak" as a separate column — they treated it as part of the gate critique. Mercury 2's framing surfaces this as a first-class question.

### MiMo-V2.5 (partner #7) — what it added

MiMo also disclosed no file-system / GitHub access — its review was built **only from the incidents dashboard JSON** (the same source all 7 partners share). What it added beyond #1–#6:

1. **Formalized conviction-override / hot-streak exemption** — the only partner to answer the user's literal question *"exemption after going on a hot streak consistently?"* with concrete thresholds:
   - ≥ 10 consecutive wins OR ≥ 70% WR rolling 20-pick window
   - Earned: reduced Sharpe gate (0.3 vs 0.5), extended max DD (25% vs 20%)
   - Forced: trailing stop tightening to 1.5× ATR (vs default 2× ATR)
   - **Hard floors that never relax even on hot streak**: leakage guards, WON/PnL sign coherence, Monte-Carlo permutation p-value
2. **Asset-class-specific gate profiles** — recognizes that one-size-fits-all gates fail on edge classes:
   - PENNY/MEME: 40% DD tolerance, 1% max position size
   - CRYPTO: higher vol tolerance + mandatory 24/7 stop monitoring
   - BONDS: relaxed Sharpe gate (structural carry advantage)
   - FOREX: relaxed n≥30 (vs n≥50) due to 24h liquidity
3. **DB schema upgrade over Mercury 2's flat design** — adds CHECK constraints + GIN indexes + a separate `roadmap_items` table linking enhancements↔incidents by ID arrays:
   - `enhancements` (status enum, asset_class array, impact CHECK, sprint VARCHAR)
   - `incidents` (severity P0/P1/P2/P3, category CHECK, FK to enhancements)
   - `roadmap_items` (quarter, theme, enhancement_ids[], incident_ids[], target_date)
   - Plus an `update_enhancement_timestamp()` trigger for auto-`updated_at` + auto-`shipped_at`
   - **Recommendation:** this is the strongest DB schema across all 7 partners. Adopt the 3-table layout with CHECK constraints as canonical v1. Migrate from Mercury 2's flat schema if any portion got prototyped earlier.
4. **10 NEW REM items not in any prior partner's list** (REM-015 through REM-024):
   - REM-015: Mean-reversion strategy template (overlaps my ENH-OSC-01 but more general)
   - REM-016: Hot-streak exemption mechanism (formalized)
   - REM-017: Asset-class-specific safety gate profiles
   - REM-018: Funding rate data feed for crypto
   - REM-019: Yield curve data feed (2s10s)
   - REM-020: Ornstein-Uhlenbeck half-life estimator
   - REM-021: Roll yield calculator for futures term structure
   - REM-022: On-chain data integration (exchange flows)
   - REM-023: Regime-exempt promotion path
   - REM-024: Worktree cleanup (already covered by my `/dedup-md-files` skill)
5. **Per-asset-class top strategies** — most detailed prescriptions across all 7 partners (universe, signal, entry, risk caps, gate, edge rationale). Worth treating as REFERENCE ARCHITECTURE, but **not derived from your specific historical data** (MiMo couldn't read the plans), so treat the parameters as starting points to backtest, not as facts.

### MiniMax Agent (partner #8) — what it added

Same access constraint (web audit only, no file/GitHub). Added on top of MiMo:

1. **5-table DB schema with audit-log tables** — adds `incident_resolution_log` + `enhancement_progress_log` to MiMo's 3-table design (incidents/enhancements/roadmap_items). The audit-log tables capture every status transition (CLAIMED/IN_PROGRESS/RESOLVED/REOPENED) with actor + notes + timestamp. **Useful upgrade for multi-AI peer-review provenance** (each partner's contribution can be a row). **Final canonical schema = MiniMax's 5-table layout**, not MiMo's 3-table.
2. **5-phase 12-week roadmap** with concrete week-by-week scheduling: Phase 1 data integrity (W1-2) → Phase 2 scoring parity (W3-4) → Phase 3 asset cleanup (W5-6) → Phase 4 strategy rebuild (W7-8) → Phase 5 advanced methods (W9-12). Concrete deadlines absent in prior partners.
3. **Effort summary matrix** — exact counts: **18 S, 26 M, 7 L, 1 XL** across the full backlog. First partner to quantify total effort.
4. **Prioritization matrix** (CRITICAL/HIGH/MEDIUM/LOW × impact × effort) — explicit decision rubric: CRITICAL = HIGH-impact + S-effort (do first); LOW = ANY-impact + L/XL-effort (defer).
5. **Python query API examples** — concrete `get_p0_incidents_by_class()`, `get_enhancement_effort_summary()`, `link_enhancement_to_roadmap()` functions. Bridges the schema to actual usage.
6. **Dedup skill design** uses content SIGNATURE (first 200 + last 200 chars, MD5) instead of full SHA-256:
   - **Pro:** ~50× faster on large files
   - **Con:** false-match risk on files with identical headers/footers but different middles (e.g., two 90-day plans that share the same intro + signature line)
   - **Recommendation:** keep my full-SHA256 `tools/dedup_md_files.py` as the canonical (correctness > speed for 117-file batches). Adopt MiniMax's signature approach only as a `--fast` flag for >10k-file scenarios.

### Final canonical decisions across 8 partners

After 8 partner reviews, here's what becomes load-bearing:

| Decision | Canonical source | Why |
|---|---|---|
| DB schema | **MiniMax (5-table with audit logs)** | Most complete; supports multi-AI provenance |
| Dedup tool | **Claude Opus 4.7 `tools/dedup_md_files.py` (full SHA-256)** | Correctness > speed at this scale |
| Conviction-override rules | **MiMo-V2.5** | Only partner with concrete thresholds (≥10 consec / ≥70% rolling-20) |
| Per-class gate profiles | **MiMo-V2.5** | Only partner with class-specific tolerance numbers |
| 5-phase roadmap | **MiniMax** | Only partner with week-by-week deadlines |
| Effort matrix | **MiniMax (18 S / 26 M / 7 L / 1 XL)** | Only partner to quantify total backlog |
| Foundation order (PRs #9/#14/#15 → validator restart → strategy PRs) | **Claude Opus 4.7 meta** | Cross-partner consensus + canonical-JSON grounding |
| Mean-reversion template | **MiMo + Opus** | MiMo's OU half-life math + Opus's ENH-OSC-01 oscillating-pair scan |

### Caveats specific to MiMo

- Per-class strategy prescriptions are **generic best-practice**, not data-grounded. The "EUR/USD 1.05–1.12 range mean-revert" and "USD/JPY 145–155 BOJ intervention band" claims are real-world levels but not back-tested against your `trading_picks` history. Need empirical validation before sizing.
- "30% of picks fire in wrong regime" + "2,531 WON rows" + "CRYPTO 5 edges fail Bonferroni" — these claims match the incidents dashboard exactly (good — MiMo read the canonical incident JSON, not hallucinated like the unsigned partner #5).
- MiMo's "Quick Win PR list" (PR-001 through PR-008) substantially overlaps the open PRs already on GitHub (#9–#16). The hot-streak exemption (REM-016) and asset-class gate profiles (REM-017) are the genuinely new contributions worth opening fresh PRs for.

### TODO surfaced by Mercury 2 that none of #1–#5 answered

The user's original prompt asked: *"do certain trades fluctuate between 2 prices over and over and are basically a sure thing?"* — **none of the 5 prior partners answered this.** Mercury 2 named it but punted ("Spot any price-pair that repeatedly cycles between two levels — flag them as high-probability mean-reversion trades").

This is an **answerable empirical question** against `trading_picks` history. Adding to incidents/enhancements as new item:

- **ENH-OSC-01** — "Oscillating-pair scanner": query MySQL `trading_picks` for (symbol, asset_class) where `STD(entry_price) / AVG(entry_price) < 0.02` AND `n >= 20` AND `WIN_RATE > 0.65`. Surface candidates as a new dashboard tile "Range-bound sure-things". Owner: data-eng. Effort: S (~40 LOC SQL + 1 dashboard widget). **Not in any prior partner's quick-win list — original add from this meta-synthesis.**

---

## Where all 5 agree (CONSENSUS — high signal)

| Item | All 5 agree? | Action class |
|---|---|---|
| ML calibration inversion is real (confidence anti-predictive, especially CRYPTO) | ✅ 5/5 | Fix in `smart_picks_engine.py` |
| EQUITY VIX<22 hard gate is the single highest-leverage idle work (branch `feat/equity-vix-regime-gate-sidecar-2026-05-13` exists, unmerged) | ✅ 5/5 | Verify + add caller |
| ETF VIX<25 overlay unwired despite proven PF 2.05→3.22 lift | ✅ 5/5 | One-line wire in `etf_sector_emitter.py` |
| BTC UTC-hour death-zone filter (M-001) is low-LOC high-impact CRYPTO win | ✅ 4/5 (stub doesn't mention) | Add to `score_booster.py` |
| PENNY/MEME class is toxic, should be quarantined | ✅ 5/5 | Add class-wide gate (needs user approval per CLAUDE.md) |
| FOREX is net loser (PF<1); needs HARD_DISABLE until carry-backtest proven | ✅ 5/5 | M-007 env flag |
| BOND has n=11 — statistically meaningless; deprioritize 90 days | ✅ 5/5 | Hold; wire FRED_API_KEY first |
| forward_validator frozen >270h is a P0 (29M open positions backlog) | ✅ 5/5 | Restart required (DevOps action, not code-only) |
| WON-rows with negative PnL (2,531 rows, avg -41.1%) is a labeling bug | ✅ 5/5 | SQL relabel (already in open PR #15) |

→ **9 fully-converged items.** Everything else is single-partner opinion or contradicted by canonical data.

---

## Where they disagree (CROSS-VALIDATION FLAGS)

### Disagreement #1 — Per-class headline numbers

| Class | Grok (file 1) | Sonnet QW (file 2) | Sonnet RI (file 3) | qwen-coder (file 4) | Stub (file 5) | **Canonical pf_registry.json** (policy_clean_net) |
|---|---|---|---|---|---|---|
| CRYPTO | PF 1.30 | PF 1.30 | PF 1.30 | PF 1.30 | "PF 6.8 — Stable T2" 🚩 | **PF 0.96 / WR 30.95% / n=210** |
| EQUITY | PF 1.55 | PF 1.55 | PF 1.55 | PF 1.55 | PF 1.57 | **PF 0.00 / WR 0% / n=1** |
| COMMODITY | PF 2.36 | PF 2.36 | PF 2.36 | PF 2.36 | — | **absent from canonical** |
| FOREX | PF 0.87 | PF 0.87 | PF 0.87 | PF 0.87 | PF 0.27 🚩 | **PF 15.92 / WR 16.67% / n=12** |

**Verdict:**
- The "1.30 / 1.55 / 2.36 / 0.87" numbers all 4 named-model partners quote come from `by_asset_class_raw` (a deprecated view CLAUDE.md explicitly tells us not to cite). They are pre-M-067 / pre-policy-clean.
- **File 5's "CRYPTO PF 6.8 stable T2" is fabricated** — not in any view of the registry.
- **File 5's "FOREX PF 0.27" is also fabricated** — closest match is the n=53 raw view (PF 0.55), not 0.27.
- The actual canonical state (which all 5 partners missed): **CRYPTO is sub-break-even** (0.96), **EQUITY/PENNY are n=1 each** (no statistical basis), **FOREX shows a misleading PF 15.92 driven by 2 wins on n=12** (also no basis).

This is the **same hallucination pattern** I flagged in the prior PR-review tick for Kilo Code's audit. **Partner audits are quoting non-canonical numbers.** The strategic recommendations they build on top of those numbers are still mostly correct (because the VIX gate / BTC hour / calibration findings are evidence-based, not number-derived) — but the headline class-state framing is wrong everywhere.

### Disagreement #2 — Quick-win count

- Grok: 11+ items, calls 6 of them "exact code change needed"
- Sonnet QW: 8 quick-wins ("⭐ Biggest" tier + 5 wiring gaps)
- qwen-coder: 7 quick-wins as PR-1 through PR-7
- Stub: 5 generic items

After deduping by content, **the union resolves to exactly 7 unique quick-win actions** (see Unified Quick-Win Set below).

### Disagreement #3 — Sequencing

- Sonnet QW: "fix forward_validator FIRST, then everything else" — operationally correct
- Grok: "ship 6 code PRs in parallel, validator restart is a DevOps task" — correct that they're decoupled but underweights how forward_validator freeze poisons every WR claim
- qwen-coder: sequential by class, doesn't surface validator
- My take: **forward_validator + WON-relabel are blocking everything else.** Without them, no merged PR's lift can be measured. The 7 strategy PRs can be coded in parallel but their impact-tests are blocked by validator state.

---

## The unified Quick-Win set (post-meta-synthesis)

Stable across 4+ named partners, with file-paths + evidence:

| QW | Action | File(s) | Evidence | Effort | Status |
|---|---|---|---|---|---|
| **QW-1** | Merge `feat/equity-vix-regime-gate-sidecar-2026-05-13` + wire caller | `alpha_engine/equity_strategies.py` + `non_crypto_quality_gate.passes_active_gate` | Backtest PF 5.37 / WR 75% / MDD 7.3% on 30 LC | S | branch exists |
| **QW-2** | Wire VIX<25 into etf_sector_emitter | `alpha_engine/etf_sector_emitter.py` + `vix_regime_gate.is_safe_regime()` | Backtest PF 2.05→3.22 (+57%) | S | unwired, both files exist |
| **QW-3** | BTC UTC-hour filter (M-001) | `alpha_engine/score_booster.py` | Memory-backed n>1000 picks | S | unwritten, ~15 LOC |
| **QW-4** | Enable `CRYPTO_ONCHAIN_MOMENTUM_ENABLED=1` env | GHA workflow env | Module exists, just needs flag | XS | 1-line YAML |
| **QW-5** | Re-derive COMMODITY n/PF post-PR-#994 dedup audit | `audit_dashboard/data/dashboard_data.json` | `cot_paper_pilot_overemission_falsified_20260513.md` | S | audit task, no code |
| **QW-6** | Restart forward_validator + EXPIRED-stamp stale backlog | `alpha_engine/forward_validator.py` | 29.2M open positions / 270h+ frozen | M | DevOps action |
| **QW-7** | Apply WON→LOST relabel (PR #15) | `tools/mysql_dedup_fix.py` | 2,531 rows avg -41.1% PnL | M | PR #15 open, needs_changes |

QW-6 + QW-7 are foundation. QW-1..QW-5 are strategy layer. Foundation gates strategy validation.

---

## Items requiring user approval (still gated)

| QA | Action | Source partner(s) |
|---|---|---|
| QA-1 | PENNY_STOCK class-wide gate in `quality_gates.BLOCKED_ASSET_STRATEGY_PAIRS` | all 5 |
| QA-2 | 9 baby_strats overfit blocks (crypto_soc_orderflow_absorption variants + adx_pullback + choppiness_regime) | Grok, qwen-coder |
| QA-3 | M-007 FOREX_HARD_DISABLE env flag | all 5 |

Per CLAUDE.md: BLOCKED_* edits require explicit user approval.

---

## What I'm adding that the 5 partners DIDN'T cover

1. **Calibration drift across partner numbers.** None of the 5 partners caught that they're quoting the wrong view of `pf_registry.json`. My PR-review tick already established that. **Re-baseline the next round of plans on `by_asset_class_policy_clean_net`** — don't cite the raw view as the headline.
2. **The 7 open PRs (#9–#15 minus #12 closed) are the foundation layer.** The Quick-Wins partners propose are SECOND-PRIORITY behind those. No partner explicitly tied QW-1..QW-5 to the foundation-PR sequencing. My recommendation: do not draft QW-1..QW-7 PRs until #9, #14, #15 close.
3. **The 5th partner file (`EAGLE_2026-05-27T06-10-51_EST.md`) is unsigned + contains fabricated PFs.** Treat as untrustworthy. Recommend not consulting that contributor again until they can cite their data source.
4. **EDT vs EST nomenclature.** The "EST" in partner filenames is incorrect for May (DST). The site is on UTC server-side. Standard for future timeline entries: dual-stamp `<UTC> / <Toronto local (EDT or EST)>`.

---

## Incidents / Enhancements dashboard mapping

The 9 consensus items + 3 cross-validation flags slot into the existing `audit_dashboard/data/incidents_enhancements_feed.json` schema as 12 new entries. See `audit_dashboard/data/incidents_enhancements_5partner_synthesis_2026-05-27.json` for the structured payload.

Existing dashboard already has 38 entries; this adds ~12. Total after: ~50.

---

## Database-table proposal (recap)

Detailed in `reports/2026-05-27_enhancements_roadmap_db_schema.md` (prior tick). One sentence: `ejaguiar1_stocks.roadmap_items` + `roadmap_item_history` + `roadmap_item_reviews` — 3-table normalization replaces the hand-curated JSON sidecar, enables PR linkage, status-history, and AI-reviewer attribution (each partner's verdict becomes a row in `roadmap_item_reviews`).

---

## Process notes

- Source dedup performed via `/dedup-md-files` skill (built earlier this session). User-pasted 126-path Windows list → 9 canonical reports/ files. The 117 "missing" paths are correctly reported as worktree clones not present on this WSL host.
- All 5 partner EAGLE files were ingested and cross-referenced byte-for-byte (no skim-summaries) where they touched canonical data files.
- Reconciliation pass: each per-class number quoted by a partner was checked against `pf_registry.json::by_asset_class_policy_clean_net` (the canonical view per CLAUDE.md).
- No new PRs were opened in this synthesis. The 7 open PRs (#9, #10, #11, #13, #14, #15 + nightly cron #8 already merged) already cover the most-urgent foundation work.

---

## Final recommendation

**Do not draft QW-1..QW-7 PRs yet.** Order should be:

1. Author addresses the `needs_changes` review comments on PRs #9, #14, #15 (foundation)
2. PR #8's nightly fires at 19:12 UTC today → `gatekeeper_new.joblib` lands on main
3. PR #10 unblocks; merge
4. Restart forward_validator (DevOps)
5. THEN draft QW-1..QW-5 as a single 3-day strategy sprint
6. THEN seek approval for QA-1..QA-3

If anything falls off this path, the partner files are still on disk for future ticks to re-read.

---

*Signed: Claude Opus 4.7 (Anthropic) — claude-opus-4-7 — 2026-05-27T06:18:00Z / 02:18 EDT*
