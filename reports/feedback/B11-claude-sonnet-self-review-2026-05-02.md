# B11 Multi-AI Review #1 — Claude Sonnet 4.6 (2026-05-02)

**Item:** B11 — ETF source diversification  
**Reviewer:** Claude Sonnet 4.6 (self-review, §5 protocol)  
**Date:** 2026-05-02

---

## A. Confirmed Assumptions

1. **File paths are correct.** The three ETF sources registered in JSON_PICK_SOURCES are:
   - `('leveraged_etf_decay', 'alpha_engine/data/leveraged_etf_decay_picks.json', None)` — confirmed at `audit_trail/dashboard_generator.py:3844`
   - `('etf_sector_rotation', 'alpha_engine/data/etf_sector_picks.json', None)` — confirmed at `audit_trail/dashboard_generator.py:3848`
   - `('orphan_emitter_etf', 'non_crypto_agent/data/etf_picks.json', None)` — confirmed at `audit_trail/dashboard_generator.py:3895`

2. **Root cause is confirmed.** `alpha-engine-etf.yml` runs `tools/etf_emitter_spike.py` which:
   - Writes to `alpha_engine/data/active_picks_etf_draft.json` (NOT in JSON_PICK_SOURCES)
   - Is explicitly marked `is_draft: True`, `ingested_by_dashboard: False`
   - The registered `etf_sector_picks.json` is populated by `tools/etf_sector_emitter.py` which is NEVER called by any workflow

3. **`leveraged_etf_decay` staleness confirmed.** 4 picks from 2026-04-04 (28 days ago). They fail `passes_active_gate` with `age=661.7h > NON_CRYPTO_MAX_AGE_HOURS=240h`. No workflow calls `alpha_engine/strategies/etf_decay_shorts.py`.

4. **The emitter code is already production-ready.** `tools/etf_sector_emitter.py` has proper error handling, graceful fallback to empty picks on yfinance failure, opt-in flag support, and is already registered in JSON_PICK_SOURCES.

5. **Wire-Up Rule compliance.** `etf_sector_rotation` IS already wired into JSON_PICK_SOURCES. The issue is purely operational (workflow calling wrong script). No Wire-Up Rule change needed.

---

## B. Surfaced Contradictions / Blockers

1. **B11 doc says "add ≥1 alternative ETF source".** The actual problem is NOT a missing source — it's that existing registered sources produce 0 picks because the wrong script runs. The fix is a workflow update, not a new emitter.

2. **`non_crypto_agent/data/etf_picks.json` root cause unresolved.** The non_crypto agent runs daily but quality=0 picks. Root cause is within the `non_crypto_agent` pipeline. Out of scope for this PR (separate investigation needed).

3. **yfinance availability in GitHub Actions is assumed.** The workflow installs yfinance and it has network access. Local sandbox blocks yfinance. Production should work.

---

## C. Recommended Deltas

1. Change the workflow to call `tools/etf_sector_emitter.py` (with `ETF_SECTOR_EMITTER_ENABLED=1`) to populate `etf_sector_picks.json`.
2. Add a step to call `alpha_engine/strategies/etf_decay_shorts.py` to regenerate `leveraged_etf_decay_picks.json`.
3. Extend the git commit step to commit both `etf_sector_picks.json` and `leveraged_etf_decay_picks.json`.
4. Keep the spike script step for backward compatibility (it writes `active_picks_etf.json` which other tooling may read).
5. Add a test verifying the workflow calls both production emitters.

---

## D. Net Verdict

**READY-TO-SHIP** — Small workflow-only fix. Low risk. Existing tests pass. Production behavior: if yfinance works in GH Actions, ETF picks will flow to /audit for the first time. If yfinance fails, emitters gracefully return 0 picks (no worse than today).
