# Session AO — Swarm Review Request
# Date: 2026-05-17
# Session: AO (following AN — APPROVE)

## Context

Session AO: diagnostic investigation into COMMODITY and EQUITY verdict paths.
No code changes made this session. All findings are data-analysis only.
Two changes identified that would require explicit user approval before implementation.

## Session AO Findings

### 1. COMMODITY — Blocked by Two Issues

**Current:** WR=60.2% PF=2.28 verdict=WATCH (n=354 across 6 strategies)

**Issue A — `cta_cross_asset_tsmom` is a massive drag (n=71, WR=12.7%, PF=0.24)**

| Scenario | n | WR | PF | Verdict |
|----------|---|----|----|---------|
| Current (all) | 354 | 60.2% | 2.28 | WATCH |
| Without `cta_cross_asset_tsmom` | 283 | **72.1%** | **3.65** | WATCH |
| Improvement if blocked | −71 | +11.9pp | +1.37 | same verdict |

`cta_cross_asset_tsmom` is NOT in BLOCKED_ASSET_STRATEGY_PAIRS. It is blocking COMMODITY
from T1-tier performance (WR≥55%/PF≥2.0). Blocking requires user approval + mutation protocol.

**Issue B — CT=F concentration cap (CT=F = 81.6–87.1% of COT picks)**

COT strategies (cot_positioning + cftc_cot_commercial_signal) are concentrated in CT=F:
- CT=F: 230/264 COT picks (87.1%) — WR=85.7%
- ZW=F: 19 picks (7.2%) — WR=26.3%
- ZS=F: 12 picks (4.5%) — WR=0.0%
- KC=F: 3 picks (1.1%) — WR=0.0%

Even after blocking cta_cross_asset_tsmom, CT=F would be 81.6% of remaining COMMODITY picks,
exceeding MAX_SYMBOL_CONCENTRATION=0.60. Verdict returns WATCH instead of MONEY_READY.

**Interpretation:** CT=F concentration is not a risk — it IS the edge. WR=85.7% on 230 picks is
T1-grade performance. The concentration cap was designed to prevent single-name exposure when
the name is risky; here CT=F is the best-performing commodity signal.

**Path to COMMODITY MONEY_READY:**
1. Block `cta_cross_asset_tsmom` (user approval needed — needs mutation investigation)
2. Raise MAX_SYMBOL_CONCENTRATION for COMMODITY specifically, e.g. 85% (user approval needed)
Both changes are required; either alone leaves COMMODITY at WATCH.

### 2. EQUITY — stocks_rsi2_pullback Already Blocked, Thin Remaining Base

After filtering blocked strategies from closed_picks:
- Unblocked EQUITY resolved picks: n=7 (across 4 strategies)
- Top strategy: stocks_rsi2_pullback (n=37, WR=37.8%) — ALREADY BLOCKED in BLOCKED_ASSET_STRATEGY_PAIRS
- money_ready_verdict correctly falls back to dashboard n=240, WR=54.2% (from MySQL/broader source)
- EQUITY verdict WATCH is correct — PBO/SPA cannot run on 7 unblocked closed_picks

EQUITY path to MONEY_READY is via accumulation in the kimi_riseoftheclaw workflow which generates
picks into MySQL (not closed_picks.json). No immediate action needed.

### 3. CI and Test Status

| Check | Status |
|-------|--------|
| CI failures | 0 (all 20 workflows green) |
| Open PRs | 0 |
| FOOLPROOF open items | All external-blocked or monitoring |

### 4. cta_commodity_momentum_term (n=11, WR=0.0%) — Monitor Only

Too few picks for statistical conclusion (n=11 < MIN_N_CLASS=50). Continue accumulating.
Do not block yet — may improve with more data. Flag for review at n=30.

## Questions for Swarm

1. **Block `cta_cross_asset_tsmom`?**: WR=12.7% at n=71 is statistically significant (Chi-squared
   p << 0.001 for H0: WR≥50%). Strategy appears to be CTA trend-following on commodities — likely
   whipsawed in current TRENDING_DOWN regime. Should we apply the mutation protocol? Or is n=71
   sufficient evidence to go straight to block recommendation (pending user approval)?

2. **Raise COMMODITY concentration cap?**: MAX_SYMBOL_CONCENTRATION=0.60 (global). CT=F at 87.1%
   of COT picks is the structural pattern — COT analysis identifies CT=F as the highest conviction
   commodity signal. Options:
   a) Add per-class override: `CONCENTRATION_CAP_BY_CLASS = {"COMMODITY": 0.85}` (surgical)
   b) Accept WATCH and accumulate more non-CT=F commodity strategies
   c) Suppress concentration check for COMMODITY specifically (broader change)
   Which approach and threshold?

3. **COMMODITY MONEY_READY timeline**: If both changes above get user approval and are implemented,
   COMMODITY would be: WR=72.1% PF=3.65, DSR=1.0, SPA ok (p=0.0), CT=F at 81.6% (≤85% cap).
   Verdict: MONEY_READY. Is this timeline aggressive or conservative given the data?

4. **EQUITY path**: 7 unblocked closed_picks is essentially no data. The kimi workflow's MySQL picks
   (n=240, WR=54.2%) represent the real EQUITY edge. Should we pipe kimi closed picks into
   closed_picks.json? Or accept the current dashboard_fallback architecture indefinitely?

5. **Overall verdict**: Is Session AO APPROVE? No code changes were made — diagnostic only.

## Verification

- CI: 0 failures
- Analysis scripts: run inline, no persistent changes
- Commit: none this session (diagnostic only)
- Prior commits: M-080 + M-081 (Session AN, `6f9f88b1a3`)
