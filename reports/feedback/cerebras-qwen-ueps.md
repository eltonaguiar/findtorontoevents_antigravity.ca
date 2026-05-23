**1. RECOMMENDED OPTION**  
**B**: It isolates the long-horizon exemption to UEPS with surgical precision, preserving short-term gate integrity while unblocking UEPS under a 14-day shadow rule.

**2. WHAT TO DROP**  
**C** and **D**: C degrades score floor globally, violating Critical Constraint to not weaken existing short-term controls. D avoids the gate system entirely, creating audit fragmentation and future tech debt. **E** is passive and delays validation.

**3. SAFETY**  
Worst-case: Bypassing BLOCKED_SYMBOLS/elite_grade/score floor for UEPS leaks low-quality or manipulated signals into live portfolios, risking drawdown. Canary: `picks.active.entry_count{source_system="ueps"}` > 5 within 14d — confirms floodgate risk.

**4. UNIT TESTS**  
- Test that UEPS pick with score=45, trade_timeframe="POSITION" passes gate when flag enabled.  
- Test that non-UEPS pick (e.g. kimi_riseoftheclaw) with same score fails under same flag.  
- Test that blocked symbol (e.g. NVDA) in UEPS with flag enabled passes, but fails when disabled.

**5. ROLLBACK**  
1-line env-flag flip: `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED=false`