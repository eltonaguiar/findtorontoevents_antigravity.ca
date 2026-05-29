# ParallelSwarm — Dry-Run Evidence (2026-05-29)

Real executions proving the pipeline. No fabricated numbers — every figure below is from a command actually run this session.

## Dry Run 1 — "1 strategy per asset class", parallel across live providers

**Phase 0 (signs of life):** provider ping (`api_consult --max-tokens 5`) → **LIVE: cerebras, groq, deepseek**; dead/erroring this run: nvidia_deepseek, nous, fireworks. Gateway showed 1 cross-PC peer.

**Phase 1 (parallel implement):** 3 strategy-spec prompts dispatched concurrently —
CRYPTO→deepseek, EQUITY→cerebras, FOREX→groq — **all returned in 4 s wall-clock** (backgrounded `api_consult` + `wait`).

**Failure + failover (the valuable part):** cerebras returned **empty** on the real 700-token task (despite a LIVE 5-token ping). Per the skill's Phase-2 reassign rule, EQUITY was reassigned **→ groq**, which returned a valid spec. This is the skill's failover path working on a real failure.

**Phase 2 (validate):** all 3 specs parse as JSON with required keys —
- CRYPTO (deepseek): *Crypto Momentum Breakout with Volume Confirmation* — Close>SMA20 & >upper BB(20,2) & Vol>1.5×SMA20(Vol); trailing stop.
- EQUITY (groq, after failover): *Mean Reversion with Bollinger Bands* — long at lower BB(20,2) & RSI(14)<30.
- FOREX (groq): *Mean Reversion with Bollinger Bands* — long at lower BB(20,2), short at upper.

**Lesson captured:** liveness pings (tiny token budget) can pass while the real task returns empty — always validate the actual output, not just the ping; reassign on empty/truncated.

## Baselines for Dry Run 2 (pf_registry `by_asset_class_strategy_policy_clean_net`, n≥20)

| Class | Incumbent to beat |
|-------|-------------------|
| CRYPTO | `UNKNOWN` strategy — PF 3.23 / **WR 17%** / n=30 (fragile: few-big-winners) |
| EQUITY/ETF/FOREX/FUTURES/COMMODITY/PENNY | **none with n≥20** — no statistically-valid incumbent |

**Honest reframe:** for 7/8 classes there is no valid incumbent, so "beat the top performer" reduces to "produce the FIRST strategy that clears Tier-2 (PF≥1.5 / WR≥50% / n≥100) on a clean walk-forward backtest AND a forward test." Only CRYPTO has a (fragile) target to beat.

## Dry Run 2 — design (heavier; spec → runnable code → real backtest → compare)

1. **Phase 1b:** for each class, a live provider turns its Dry-Run-1 spec into a *harness-conformant* strategy module (the repo's `tools/backtest_*.py` / `backtest/` interface), placed at a target path.
2. **Phase 2:** syntax + interface conformance + no-lookahead audit (a backtest that peeks at future bars is the #1 way AI strategies fake edge — gate on it).
3. **Phase 4 (backtest):** run the real harness on each; compute PF/WR/MDD/n on the SAME universe + window as the incumbent. **Do not report a number that wasn't actually computed.**
4. **Beat test:** a candidate "wins" only if it clears Tier-2 AND beats the class incumbent on **both** the backtest and the forward/OOS split — with a no-lookahead + multi-symbol + dedup check (so it isn't a single-symbol or peeked artifact, per the metric-honesty-tiers rules).
5. Survivors → register in `reports/hypothesis_registry.json` (rule M-107: pre-register before claiming) and route to a swarm review.

> Status: Dry Run 1 executed and verified. Dry Run 2 requires the spec→runnable-code + backtest-harness wiring (a real engineering increment) and will produce numbers ONLY from actual harness runs — no asserted PF/WR.
