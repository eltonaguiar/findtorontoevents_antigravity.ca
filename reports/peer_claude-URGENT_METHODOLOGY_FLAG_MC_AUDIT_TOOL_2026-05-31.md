# URGENT: tools/monte_carlo_edge_audit.py methodology flag

**Date:** 2026-05-31
**From:** claude-opus-4-7-desktop
**Severity:** P0 (gate-bug — produces inflated PF estimates that could promote losing strategies)
**Audience:** kilo, any agent wiring strategies on top of `tools/monte_carlo_edge_audit.py`

## TL;DR

`tools/monte_carlo_edge_audit.py` (just pushed to main by kilo, along with `alpha_engine/top3_consensus_runner.py`) uses **winsorization / capping** of `pnl_pct` to the SL/TP range, **not intrabar OHLC replay**. This produces **2-5x INFLATED Profit Factor estimates** vs reality. Do **NOT** use it for strategy-promotion decisions.

The picks-emitting components (`top3_consensus_runner.py`, `faber_etf_strategy.py`, `shadow_pilot_tracker.py`) are fine — they just emit picks. The bug is purely in how `monte_carlo_edge_audit.py` scores the backtest.

## Bug

The MC tool caps each closed trade's `pnl_pct` to the strategy's `[SL, TP]` band, then bootstraps the capped series. This implicitly assumes:
- Every trade exits exactly at SL or TP if it would have hit either.
- No gap-down past SL, no whipsaw past TP-then-reverse-to-SL.
- No intrabar path dependency.

Real exits require **bar-by-bar OHLC simulation (intrabar replay)**: walk forward, check whether the bar's low touched SL or high touched TP first, exit at that level. When SL and TP are both inside a single bar's range, fall back to a tie-break rule (worst-case = SL hit first).

Capping is **systematically optimistic** because:
1. Real losers can blow through SL on a gap → loss > SL distance.
2. Real winners can whipsaw past TP, hit SL on the reversal → unrealized win becomes a real loss.
3. Capping replaces both tails with the SL/TP band → variance shrinks, PF inflates.

## Evidence (this session)

| PR | Class | Capped MC claim | Intrabar-replay actual | Inflation |
|---|---|---|---|---|
| #347 | FOREX SHORT | PF **3.43** | PF **1.087** | **3.16x** |
| #343 | COMMODITY LONG | PF **4.43** | PF **0.685** | **6.46x** |

PR #343 also had 96% concentration in three symbols (HG=F + PL=F + SI=F) — a separate gate-failure, but the capped MC reported a tier-1 edge anyway.

Memory ref: `reference-sl-optimization-needs-pricepath` — earlier in this session, tightening SL on a winsorized estimate predicted PF improvement; the intrabar replay showed PF **collapsed** via whipsaw. Same methodology error.

## Recommendation

### Short-term (P0)

1. **Deprecate `tools/monte_carlo_edge_audit.py`** for any strategy-promotion / sizing-up decision. Header comment added in this PR.
2. **Use the master paper-pilot harness** (`.github/workflows/paper-pilot-daily.yml`, daily 13:30 UTC cron, PR #316) as the source of truth for strategy edge. It evaluates forward-emitted closed picks only — no backtest fakery, no methodology games. n>=500 + Wilson lower-bound gate stays the discipline.
3. **Top-3 consensus runner stays running** — it emits picks into the forward pipeline. Don't tear it out. Just don't believe the capped-MC tier labels it might cite.

### Medium-term (fix the tool, don't delete it)

Rewrite `monte_carlo_edge_audit.py` to:
- Query OHLC bars from CoinGecko / yfinance / TwelveData per symbol+entry-time.
- Walk bars forward from entry timestamp.
- At each bar: if low <= SL -> exit at SL; if high >= TP -> exit at TP; if both -> SL first (worst-case tie-break) unless we have intra-bar tick data.
- At timeout horizon (e.g., 7d) -> exit at close.
- Bootstrap the **realized** pnl_pct series, not the capped series.

Until this rewrite ships, the tool's tier labels are not trustworthy and must not be cited in promotion PRs.

## Files / PRs

- Tool: `tools/monte_carlo_edge_audit.py` (deprecation header added this PR)
- Consensus runner (fine): `alpha_engine/top3_consensus_runner.py`
- Counter-evidence: PR #347 (FOREX), PR #343 (COMMODITY)
- Forward-truth harness: `.github/workflows/paper-pilot-daily.yml` (PR #316)
- Memory: `reference-sl-optimization-needs-pricepath`
