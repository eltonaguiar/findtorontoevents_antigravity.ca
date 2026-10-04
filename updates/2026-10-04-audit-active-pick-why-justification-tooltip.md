# 2026-10-04 — Active Picks: per-pick "WHY" justification tooltip

## What was wrong

`findtorontoevents.ca/audit` Active Picks showed a row for each live pick, but there
was **no single, evidence-grounded answer to "why was this pick chosen?"**. The
information existed but was scattered across a dozen column tooltips (Score, Trust,
FWD WR, Track, EDGE, AGV, Strategy…) and the composite audit string that answers the
question — `_buildPickReason()` — was only used for **CSV exports**, never rendered in
the UI.

Concretely, on 2026-10-04 the live book had 2 published active picks
(`SB=F` COMMODITY, `ZN=F` FUTURES, both `non_crypto_consensus`). A user hovering the
row could see individual metrics but nothing that said, in one place: what the signal
was, what statistically backs it, what the structural/fundamental basis is, and — very
importantly — whether the evidence is actually strong or just a hypothesis.

The two live picks are a good example: both carry
`forward_status: "NO_DATA: no closed picks found for this system/strategy"`, so they
have **no live forward track record at all**, yet nothing in the table made that
limitation prominent.

## What changed

`audit_dashboard/template.html` (only file with logic changes):

1. **New `_pickEvidenceTier(p)`** — derives an evidence tier from fields already on the
   pick (no new data collection):

   | Tier | Trigger |
   |------|---------|
   | `PROVEN EDGE` (green) | GOLDEN verified edge, **or** live forward WR ≥ 55% with n ≥ 10, **or** walk-forward OOS WR ≥ 55% with `wf_p_value < 0.05` |
   | `SUPPORTED` (blue) | VERIFIED verified edge, **or** forward WR ≥ 45% with n ≥ 5, **or** trust ≥ 7 |
   | `THIN EVIDENCE` (amber) | some forward / walk-forward / trust signal, but small or not significant |
   | `UNPROVEN` (red) | no forward and no walk-forward evidence |

   **Contradiction guard:** if the *same* strategy×symbol combo has a losing record
   (`combo_stats.n ≥ 5` and `combo_stats.wr < 45`), the tier is capped at
   `THIN EVIDENCE` regardless of a strong forward sample, and a red **Conflict** line is
   added. This prevents a "PROVEN EDGE" badge from sitting next to "this exact pair
   loses 65% of the time" — which is what the existing columns were doing.

2. **New `_buildPickJustification(p)`** — builds a single rich tooltip with:
   - **Why now:** the raw entry reason (signal).
   - **Direction:** `_buildDirectionReason()` (RSI / MA / regime context).
   - **Statistical evidence:** forward WR + n, forward-validated flag, walk-forward OOS
     WR with its p-value and a *significant / not significant* label, WF composite +
     verdict, verified-edge tier with WR/PF/n, trust score with its breakdown, ML score,
     Reward:Risk, Antigravity safety, symbol×direction intrabar WR.
   - **Fundamental / structural basis:** strategy description, system description,
     concept family, confluence / agreeing systems (`Unknown` descriptions suppressed).
   - **Gate notes:** any `blocked/kill/gate` penalties on the pick.
   - **Honesty footer** (colour-coded by tier): states plainly whether the edge is
     corroborated, supported-but-thin, or a fresh/unproven hypothesis.

3. **Always-visible `ℹ WHY` badge** added to the **Symbol cell** (not a new column, so
   it shows regardless of a user's saved column preferences). Hovering opens the
   justification tooltip. The badge is colour-coded by tier.

4. Regenerated `audit_dashboard/audit_frontend_manifest.json` (line numbers shifted by
   the insertion — this is a generated artifact tracked on `main`).

New test: `tests/test_active_pick_why_justification.js` (18 cases), wired into
`.github/workflows/ci-tests.yml` next to the existing `test_card_metrics.js` node guard.

## How it was verified

**Unit (`node tests/test_active_pick_why_justification.js`) — 18 passed, 0 failed.**
The test extracts the *real* functions out of `template.html` and runs them:
- real `SB=F` payload pick → `THIN EVIDENCE` (correct: no forward sample, WF p=0.452);
- forward n≥10/WR≥55 → `PROVEN EDGE`;
- significant WF (p<0.05, OOS≥55) → `PROVEN EDGE`;
- GOLDEN / VERIFIED verified edge → `PROVEN EDGE` / `SUPPORTED`;
- losing combo (WR 35.1, n=97) caps a strong forward sample to `THIN EVIDENCE` +
  `Conflict:` line; healthy combo does not;
- `UNPROVEN` when there is no evidence at all;
- tooltip contains Why now / Direction / Statistical evidence / Fundamental basis /
  honesty footer / tier label;
- `reason` containing `<img src=x onerror=…>` is HTML-escaped (no XSS).

**Interface (Playwright, real Chromium, real live data).** Served the edited
`template.html` as the page with the live `dashboard_data.json` beside it and rendered it:
- 102 `ℹ WHY` badges rendered (active + closed tables);
- tier tally across the live book: `THIN EVIDENCE 88`, `SUPPORTED 10`, `PROVEN EDGE 4`;
- **every** tooltip contains the Statistical + Fundamental sections;
- both visible active picks (`SB=F`, `ZN=F`) render the full tooltip on hover;
- example output for `SB=F`:
  > Why now: [Consensus 2v0] Strategies: futures_bb_mean_reversion, cot_positioning.
  > Original: COT positioning SHORT: Weekly RSI=82 overbought. Sugar.
  > Statistical evidence — Forward sample: none yet (NO_DATA) · Walk-forward OOS WR
  > 64.3% · p=0.452 (not significant) · Trust 4.2/10 · R:R 1.33x · AGV 70/100 …
  > Only weak or unvalidated evidence backs this setup … Treat as a hypothesis, not a
  > proven edge.
- **0 page errors.**

**Regression suite:** `node tests/test_card_metrics.js` (14 passed),
`node tests/test_b6_concept_filter.js` (pass), and
`pytest tests/test_audit_summary_render.py tests/test_tier2_hero_cards.py
tests/test_tier2_hero_cards_xss.py tests/test_strategy_alias_parity.py
tests/test_walkforward_payload_restored.py tests/test_ueps_dashboard_integration.py`
→ **61 passed, 1 skipped**.

JS syntax: all 22 `<script>` blocks in `template.html` compile clean.

## Notes / limitations

- The tier is a *summary of existing payload fields*, not new evidence. If a pick has no
  forward/walk-forward fields, the tooltip correctly says so rather than inventing a case.
- The badge renders in the Symbol cell for both the Active and Closed tables (shared row
  renderer) — deliberate, so closed picks can be retro-audited the same way.
- Deploy: `audit_dashboard/template.html` is applied to `index.html` by
  `audit_trail/dashboard_generator.py::build_html` on the next `audit-dashboard` run
  (hourly cron at `:10`, or `workflow_dispatch`). No generator changes are needed.
