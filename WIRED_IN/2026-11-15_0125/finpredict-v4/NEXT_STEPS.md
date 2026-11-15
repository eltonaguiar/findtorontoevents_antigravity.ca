# Next Steps — Execution Plan (finpredict-v4)

**Date:** 2026-11-15 (AM)
**Status:** Ready to execute; ordered by impact.

---

## Immediate (this week)

1. **Wire the QA gate** — build `tools/qa_ledger.py` on the verified fetcher primitives (`alpha_engine/api_failover.py`, `equity_price_failover.py`, `forex_price_failover.py`, `commodity_price_failover.py`, `audit_trail/fetch_stock_prices.py`) + a `.github/workflows/qa-market-validation.yml`. Until every PnL is validated against real market data, no class verdict is trustworthy.

2. **Run the FORWARD-TEST protocol** on the 4 emitted picks (VTI/TLT/SGOV/BND). Use `FORWARD_TEST_PROTOCOL.md`: at n=30, eliminate on inconsistent excess; extend on consistency. This is the gate that turns the backtest proof into a live decision.

3. **Automate the pick refresh** — cron/GHA that runs `emit_tactical_picks.py` → `save_picks_to_db.py` → `live_pnl_tracker.py --apply` daily so `/audit` always shows current signal.

## Next 2 weeks

4. **Fix measurement bugs blocking EQUITY** — rerun the SPY benchmark test once data is clean. If it still fails, EQUITY stays beta (hold index), not alpha.

5. **CRYPTO forward test** — run the POSITION-horizon shadow test to n≥100; gate PF≥1.3, WR≥55%, cost-inclusive, beats BTC-hold. This is the only remaining alpha candidate.

6. **Unblock FUTURES with a real feed** — 30-day paper track of CTA trend (TSMOM) once real data is wired.

## Parallel / governance

7. **Publish the risk page** — turn `RISK_MANAGEMENT.md` into the standalone review page (VaR, CVaR, sizing, kill-switches).

8. **Converge the parallel agents** — collect the `AGENT_PROMPTS.md` outputs, compare chosen strategies; only those that independently pass OOS + benchmark + SubQ fact-check become deployment candidates.

9. **Pre-register the go/no-go** — write the single decision: "if no sleeve clears all gates by day 90, the system is research-only." This makes the stop decision explicit.

---

## The one thing that matters most

**Step 1 (QA gate)** — because every other step depends on honest, market-validated numbers. Start there.

---

*finpredict-v4 / 2026-11-15*
