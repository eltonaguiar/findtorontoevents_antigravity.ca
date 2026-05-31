# TESTING_PROTOCOL.MD — Live Refresh + §7 Supersession Audit (2026-05-31)

**Author:** peer_claude (Opus 4.7, delegated from qwen's stalled queue, kilo-relay back-up)
**Branch:** `peer-claude/testing-protocol-live-refresh-2026-05-31`
**Scope:** patch the canonical `TESTING_PROTOCOL.MD` with live per-class numbers
from `money_ready_verdict.json` + `pf_registry.json`, replace stale 2026-04 §2.5
empirical claims, and add a supersession NOTE atop §7 pointing at the canonical
investigation / mutation / n-floor docs.

## Inputs (canonical per CLAUDE.md)

| File | generated_at | What |
|------|--------------|------|
| `audit_dashboard/data/money_ready_verdict.json` | 2026-05-31T22:41:12Z | per-class verdict (WR, PF, MDD, n_resolved, concentration) |
| `audit_dashboard/data/pf_registry.json` | 2026-05-31T22:41:13Z | `by_asset_class_policy_clean_net` (slippage-adjusted) |
| `reports/peer_claude-REFRESH_TESTING_PROTOCOL_NUMBERS_2026-05-31.md` (PR #396) | 2026-05-31 | reverification of the 9 §2.5 empirical claims against n=6,619 closed picks |

## Task 1 — Live per-class table (before / after)

### Before (in TESTING_PROTOCOL.MD as of HEAD)
- The header banner referenced only "Audited 2026-04-04" + a generic CRYPTO/EQUITY/FOREX
  paragraph in the doc body; no per-class WR/PF/MDD/concentration table was present at
  the top of the file. Per-class numbers had to be inferred from §13 sub-sections
  (stale 2026-04) and §15 audit notes.

### After (this PR)
A 10-row table now sits in the header banner block, pulled verbatim from the two
canonical JSONs:

| Class | n_resolved | WR | PF | MDD | Top-source share | Verdict |
|-------|------------|----|----|-----|------------------|---------|
| CRYPTO | 347 | 39.2% | 0.879 | 100.0% | `file:battleground` 25.4% | **NOT_READY** |
| EQUITY | 43 | 30.2% | 0.156 | 98.2% | `regime_terminal` 41.9% | INSUFFICIENT_DATA |
| FOREX | 29 | 27.6% | 0.035 | 82.3% | `multi_asset_scanner` 37.9% | INSUFFICIENT_DATA |
| FUTURES | 12 | 16.7% | 0.536 | 16.6% | `multi_asset_scanner` 91.7% (single-source) | INSUFFICIENT_DATA |
| UNKNOWN | 8 | 50.0% | 0.514 | 16.8% | `file:alpha_engine` 87.5% (single-source) | INSUFFICIENT_DATA |
| COMMODITY | 7 | 57.1% | 3.870 | 4.6% | `file:alpha_engine` 57.1% | INSUFFICIENT_DATA |
| ETF | 4 | 50.0% | 0.476 | 6.2% | `file:alpha_engine` 50.0% | INSUFFICIENT_DATA |
| PENNY_STOCK | 1 | 0.0% | 0.000 | 1.5% | `multi_asset_scanner` 100% | INSUFFICIENT_DATA |
| BOND | 0 | n/a | n/a | n/a | n/a | INSUFFICIENT_DATA (no closed) |
| PREDICTION_MARKETS | absent | n/a | n/a | n/a | n/a | not in canonical view |

**Summary deltas vs the figures cited in CLAUDE.md MAJOR GOAL #1 banner:**
- CRYPTO `n=728 / WR 43% / PF 1.14` (CLAUDE.md, source `money_ready_verdict.json 2026-05-24`) →
  today `n=347 / WR 39.2% / PF 0.879` (verdict + pf_registry 2026-05-31).
  Population shrank ~52%, WR down 3.8pp, PF down 0.26. Degraded.
- EQUITY `n=33 / WR 33% / PF 0.90` (CLAUDE.md 2026-05-24) → today `n=43 / WR 30.2% / PF 0.156`.
  PF collapse from 0.90 → 0.156. Degraded.
- COMMODITY `n=28 / WR 11% / PF 0.31` (CLAUDE.md) → today `n=7 / WR 57.1% / PF 3.87`.
  Population shrank 75% (CT=F kill?), small-n flip to apparent T2-shaped numbers; not
  actionable (n=7).
- FOREX `n=53 / WR 40% / PF 0.55` (CLAUDE.md) → today `n=29 / WR 27.6% / PF 0.035`.
  Degraded sharply.
- BOND `n=8` (CLAUDE.md) → today `n=0`. All 8 bond rows aged out of cohort or were
  policy-excluded.
- ETF `n=2 / PF 11.99` (CLAUDE.md) → today `n=4 / PF 0.476`. Tiny-n; flipped.

**Operator action item:** CLAUDE.md MAJOR GOAL #1 banner now also stale relative to
this refresh. Recommend a follow-up to either (a) update CLAUDE.md banner to point at
"see TESTING_PROTOCOL.MD header table for current per-class numbers" or (b) explicitly
date-stamp the CLAUDE.md banner as `as-of 2026-05-24` so future readers know to verify.

## Task 2 — §7 diff against canonical superseding docs

### §7 as it stood (TESTING_PROTOCOL.MD lines 501-520)
- **Trigger:** WR < 35% on ≥ 10 resolved trades OR PnL < -15% OR 5+ consecutive losses
  OR DNA "super loser" flag → status = `REHAB_CANDIDATE`.
- **Action:** pause original config only (not whole family).
- **Stages 1-6:** cross-symbol → cross-asset → inverse → mutation grid → regime → crossover.
- **Stage 7:** Graveyard (last resort).
- **Existing code reference:** `alpha_engine/strategy_killer.py::KILL_CRITERIA`.

### Discrepancies found

| # | §7 rule | Canonical doc / artifact that supersedes | Discrepancy class |
|---|---------|------------------------------------------|-------------------|
| 1 | "WR<35% on ≥10 trades" as the kill threshold | PR #404 §0.2 n-floor decoder: this is the **auto-rehab screening n-floor (10)** only; the actual kill / graduation surface uses n≥500 | Rule covered by newer canonical doc — §7 wording implied it gates a kill, which contradicts §0.1 hard gates. **Now annotated** in this PR's §7 NOTE block. |
| 2 | "Pause original config" without prior investigation | `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` requires an investigation ladder BEFORE any block expansion | §7 rule that's no longer followed in isolation — must be paired with the investigation doc. **Now annotated.** |
| 3 | Stages 1-6 (cross-symbol / cross-asset / inverse / mutation / regime / crossover) presented without the three-axis autopsy as input | `docs/MUTATION_THREE_AXIS_PROTOCOL.md` mandates the symbol × direction × timeframe slice via `python tools/mutation_analysis.py --json` **before** mutation grid (Stage 4) | §7 rule covered by newer canonical doc — the three-axis run is now the input to Stages 4 and 5. **Now annotated.** |
| 4 | Inverse evidence cites `winner_pattern_precursor 0% LONG → 81.2% inverse` | Live DB has zero rows for `winner_pattern_precursor` 2026-05-31 (PR #396 report claim #1) — strategy renamed or culled | §7 rule that's no longer applicable (the cited example is dead). **Now annotated as historical.** |
| 5 | SHORT bias is implicitly favored in the rehab inverse stage (cf. §2.5 SHORT +5 bonus) | §2.5 reverification (PR #396): SHORT 30d WR = 20.7% n=111 vs LONG 37.6% n=226 — SHORT actively bleeding post PR #277 EQUITY un-kill | §7 rule that contradicts new live evidence — inverse-to-SHORT may now destroy value. **Now annotated as direction-edge stale.** |
| 6 | `BLACKLISTED_STRATEGIES` size implicit (April list) | `alpha_engine/config.py::BLACKLISTED_STRATEGIES` lists 19 entries today (was ~4 in April); `stocks_rsi2_pullback` UN-KILLED 2026-05-31 tick 33 | New canonical state — §7 didn't track. **Now snapshotted in the NOTE block.** |
| 7 | "Existing code: `alpha_engine/strategy_killer.py::KILL_CRITERIA` → repurpose as `REHAB_CRITERIA`" | Not verified in this pass — kept as-is; flagged for follow-up | Possible stale code reference — needs a separate verification pass. |

### Supersession notes added (in §7 of TESTING_PROTOCOL.MD)
1. Pointer to `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` as mandatory pre-block workflow.
2. Pointer to `docs/MUTATION_THREE_AXIS_PROTOCOL.md` + `tools/mutation_analysis.py --json`
   as mandatory three-axis autopsy input.
3. Pointer to PR #404 §0.2 n-floor decoder (six surfaces: auto-rehab=10, screening=30-100,
   SPA=20, scarcity=25, walk-forward=200, paper-pilot graduation=500, money-ready=50).
4. Snapshot of the live `BLACKLISTED_STRATEGIES` + `BLACKLISTED_EXCHANGES` (19+1 entries) plus
   the `stocks_rsi2_pullback` UN-KILL note.
5. Annotation that the inverse-direction evidence is historical and SHORT has reversed —
   verify before sizing.

## Task 3 — Patch summary

**File modified:** `TESTING_PROTOCOL.MD` (root canonical only; worktree copies untouched).

**Edits:**
1. Header banner: adds "Last refreshed: 2026-05-31 from money_ready_verdict.json" note
   + the 10-row per-class live verdict table.
2. §2.5 table: adds two columns — **2026-05-31 Verdict (n=6,619)** and updated **Action**.
   9 claims reverified: 1 HOLDS (Trust 6-7 stronger than April), 5 DRIFTED, 3 DEAD.
   Two gates flagged as wrong-signed: Overconfidence Penalty (Conf≥0.90 is now the sweet
   spot, not toxic) and SHORT Base Bonus (SHORT has reversed). Conf 0.75-0.79 bonus is
   dead (−43.1pp). Adds reverification cadence (next due 2026-08-31 or n>10,000).
3. §7 NOTE block (5 bullets): supersession pointers + historical-evidence annotation +
   live blacklist snapshot.

**Worktree copies NOT touched** (per instruction):
- `.qwen/worktrees/*/TESTING_PROTOCOL.MD` — left alone.
- `.claude/worktrees/*/TESTING_PROTOCOL.MD` — left alone (if any).

**Verification:** `wc -l TESTING_PROTOCOL.MD` before/after = 1670 → ~1750 lines.
No section headings deleted; only additions and the §2.5 table replacement.

## Counts (for the orchestrator return value)
- `classes_refreshed` = 10 (CRYPTO, EQUITY, FOREX, FUTURES, UNKNOWN, COMMODITY, ETF, PENNY_STOCK, BOND, PREDICTION_MARKETS noted absent)
- `stale_figures_replaced` = 9 (the §2.5 empirical claims) + 1 header date stamp + 1 BOND n-cite + 4 CLAUDE.md cross-ref deltas (CRYPTO/EQUITY/COMMODITY/FOREX) = 15 figure-level updates
- `section7_discrepancies` = 6 (rules 1-6 above; rule 7 deferred)
