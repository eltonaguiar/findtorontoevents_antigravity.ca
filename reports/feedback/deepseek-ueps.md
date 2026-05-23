1. **RECOMMENDED OPTION: B** – It directly addresses all three rejection causes (score floor, BLOCKED_SYMBOLS, elite_grade D) for UEPS only, without degrading short-term strategies, and uses the required env-flag pattern.

2. **DROP: A, C, D, E**  
   - **A** bypasses only the score floor, leaving 33% of UEPS still blocked by BLOCKED_SYMBOLS/elite_grade.  
   - **C** lowers the floor globally for POSITION, risking short-term strategies that also use that timeframe.  
   - **D** is a UI hack that hides the problem; the gate still blocks live picks.  
   - **E** defers indefinitely – chicken-and-egg persists.

3. **WORST-CASE**: A bug in `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED` accidentally bypasses the gate for *all* sources, letting low-quality short-term picks through.  
   **CANARY**: Monitor `picks.active` count daily; if it jumps >30 in a week (UEPS only adds ~30), rollback. Also track `forward_wr` for any non-UEPS pick that appears in `active` – if non-zero, flag immediately.

4. **UNIT TESTS** (3):  
   - `test_ueps_long_horizon_bypass_skips_score_floor` – UEPS POSITION pick with score=19 passes.  
   - `test_ueps_long_horizon_bypass_skips_blocked_symbols` – UEPS NVDA pick passes.  
   - `test_ueps_long_horizon_bypass_does_not_affect_short_term` – non-UEPS POSITION pick with score=19 still fails.

5. **ROLLBACK**: Flip env flag `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED` to `false` (default-OFF) – no PR revert needed.