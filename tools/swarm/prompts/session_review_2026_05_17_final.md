# Session Review — 2026-05-17 (Final)

You are a senior quantitative trading engineer. Review these session deliverables and answer 5 questions directly. Flag correctness issues, calibration concerns, or missed P0 items.

## Session deliverables

1. **mercury2_fast investigation** — ALREADY-BLOCKED confirmed. n=14-32, PF 0.02-0.07. Zero rows in closed_picks.json. No quality_gates.py edit needed.

2. **trust_score backfill** — Ran enrich_picks_with_trust_score() on 89 active picks. Before: 0/89. After: 89/89. Range 1-7, avg 3.3. HC gate threshold ≥6 → 5/89 picks pass (5.6%). trust_tier NOT populated (sandbox_mutation_experiments.py only).

3. **COMMODITY cta_cross_asset_tsmom direction block** — Added to BLOCKED_DIRECTION_TRIPLES:
   - LONG: WR=0%, PF=0.00, n=24 valid resolved
   - SHORT: WR=19%, PF=0.39, n=47 valid resolved
   Rationale: COT strategies carry all COMMODITY edge (cftc_cot_commercial_signal WR=75%/PF=4.52, cot_positioning WR=80%/PF=4.94). Block isolates T1 COT performance. py_compile passes.

4. **quan_engine autopsy** — Comment added at line 1301 scheduling full family autopsy 2026-05-24 after MySQL ghost-row purge (655k stale rows, PA console action pending). Existing doc covers scalp variant: ALREADY-BLOCKED, 4-axis DEAD finding.

5. **Strategy emission monitor** — 209 distinct strategies. 153 DORMANT (>14d silent, mostly ml_enhanced_ variants Feb-Apr 2026). 55 ACTIVE (≤7d). 1 STALE.

## Questions

**Q1. COMMODITY block correctness:** Is blocking BOTH directions of cta_cross_asset_tsmom correct? n=24 LONG + n=47 SHORT = n=71 total, both below the n=100 charter floor. Should these be PROBATION entries instead of permanent BLOCKED_DIRECTION_TRIPLES? What's the risk of a false-positive block on n<100?

**Q2. trust_score calibration:** HC gate threshold ≥6. Avg score 3.3/7. Only 5/89 picks pass (5.6%). Is this gate too strict and starving the live portfolio? Should threshold drop to ≥4 or ≥5? Or is the root fix to make the upstream pipeline generate more multi-source consensus picks?

**Q3. Strategy dormancy:** 153/209 strategies DORMANT (73%). ml_enhanced_ variants from Feb-Apr 2026. Are these expected to be dormant (superseded by better variants) or does 73% dormancy indicate a CI/runner failure causing strategies to not emit signals? What investigation step would distinguish the two causes?

**Q4. Missed P0/P1 items:** Open external blockers: MySQL 655k row purge (PA console), FRED_API_KEY (GitHub secret), DB password rotation (50webs operator), META_LABEL_GATE_ENFORCE=1 shadow (~2026-06-16). Are any of these actually P0 that should have blocked session close? Any other gaps in the session deliverables?

**Q5. py_compile sufficiency:** Does py_compile catch all risks in BLOCKED_DIRECTION_TRIPLES tuple additions — specifically tuple format errors, string escaping, and list membership bugs — or is a targeted runtime unit test needed (e.g., assert ("COMMODITY","cta_cross_asset_tsmom","LONG") in BLOCKED_DIRECTION_TRIPLES)?

Answer each question with: verdict (correct/concern/flag), reasoning, and recommended action if any.
