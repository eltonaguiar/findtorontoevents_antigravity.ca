# B11 Multi-AI Review #2 — Codebuff Proxy (2026-05-02)

**Item:** B11 — ETF source diversification  
**Reviewer:** Codebuff proxy self-review, §5 protocol  
**Date:** 2026-05-02

---

## A. Confirmed Assumptions

1. **Workflow mismatch is the actual bug.** `alpha-engine-etf.yml` ("ALPHA ENGINE - ETF Emitter") runs `tools/etf_emitter_spike.py` per its "Run ETF emitter" step (line 45). The spike script's own docstring declares it is "NOT a production emitter" and writes to a draft file not registered in JSON_PICK_SOURCES.

2. **`tools/etf_sector_emitter.py` is the intended production replacement.** It has `ETF_SECTOR_EMITTER_ENABLED` flag support, writes to the registered path `alpha_engine/data/etf_sector_picks.json`, and tests already pass (`tests/test_etf_sector_emitter.py` 7/7).

3. **`alpha_engine/strategies/etf_decay_shorts.py` has no workflow.** The module's script has a `__main__` block that writes `alpha_engine/data/etf_decay_picks.json` but NOT `leveraged_etf_decay_picks.json`. The file `leveraged_etf_decay_picks.json` is written by a different code path in the same module. Need to verify the exact output path before wiring.

---

## B. Surfaced Contradictions / Blockers

1. **`etf_decay_shorts.py` writes `etf_decay_picks.json`, not `leveraged_etf_decay_picks.json`.** Looking at the docstring: `Outputs: alpha_engine/data/etf_decay_picks.json`. But JSON_PICK_SOURCES registers `leveraged_etf_decay_picks.json`. This means either the path is wrong in JSON_PICK_SOURCES OR the script was modified to write the `_leveraged_` variant. **Must verify before wiring.**

2. **Non-crypto ETF agent (quality=0) needs separate investigation.** Not blocking this PR.

---

## C. Recommended Deltas

1. Read `alpha_engine/strategies/etf_decay_shorts.py` to find the exact output path it writes to and reconcile with JSON_PICK_SOURCES entry.
2. If output is `etf_decay_picks.json` (not leveraged variant), either: update JSON_PICK_SOURCES to use `etf_decay_picks.json`, OR update the script to write `leveraged_etf_decay_picks.json`.
3. Add a workflow step that sets `ETF_SECTOR_EMITTER_ENABLED=1` and calls `tools/etf_sector_emitter.py`.
4. Add the leveraged decay step only if the output path is confirmed correct.

---

## D. Net Verdict

**NEEDS-ONE-CHECK** — Verify `etf_decay_shorts.py` output path vs JSON_PICK_SOURCES entry before adding the leveraged step. The sector emitter fix is ready-to-ship immediately.
