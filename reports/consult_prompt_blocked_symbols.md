We are implementing a blocked-symbol universal gate in audit_trail/quality_gates.py for a trading system. The gate has three parts:

1. A kill-switch env var UNIVERSAL_BLOCKED_SYMBOLS_GATE_DISABLED that wraps the existing BLOCKED_SYMBOLS check in passes_active_gate().

2. Restricting the UEPS long-horizon bypass to data-quality blocks only (MATICUSDT, UUSDT, XMR, XMRUSDT, KATUSDT). Previously it bypassed ALL blocked symbols for UEPS source_system + POSITION timeframe picks.

3. Adding a BLOCKED_SYMBOLS filter inside alpha_engine/forward_validator.py save_active_picks() so the canonical save function strips blocked symbols before writing active_picks.json.

Context: 23 symbols are blocked (9 CRYPTO data-quality/delisted, 4 CRYPTO structural anti-edge, 10 EQUITY drain symbols). 13 instances are currently leaking into active_picks.json because at least 11 emitter files write directly without calling passes_active_gate().

Does this three-part design have any flaws? Is there a better architectural approach? Consider: race conditions, performance, maintainability, and whether we should instead centralize all active_picks.json writes through a single gate-checked function.
