# Lessons from tbot.augustwheel.com — 2026-05-17

External AI-driven crypto bot reviewed at user request
(`https://tbot.augustwheel.com/trades`). It is a **cautionary case study** — a
near-perfect anti-pattern of what the money-ready gates exist to catch.

## tbot's record (verbatim from the dashboard)

| Metric | Value |
|--------|-------|
| Trades | 43 shown / 116 across tiers |
| Win rate | **26.2%** |
| Total P&L | **-$11,361.75** |
| Best trade | +$5.16 |
| Worst trade | **-$7,868.12** (FOREST/USD, bought $0.16 → stopped $0.0761, -52%) |
| Asset class | crypto micro-cap altcoins (Kraken) |
| Method | "Claude AI reasoning behind each decision" — per-pick LLM reasoning, all `BUY` |

## What killed it — and which of our gates catches each

1. **One trade = 69% of all losses.** FOREST -$7,868 of -$11,362 total. The
   stop "STOPPED" only after a -52% move — missing or far-too-wide stop on an
   illiquid micro-cap. → **MDD / tail-risk (CVaR) gate** (MONEY_READY v2 #7) +
   hard stop-loss enforcement (`feedback_halt_flag_must_be_hardcoded`,
   CRYPTO stop-loss P0). Live proof: one un-stopped altcoin wipes the account.

2. **26.2% WR with per-pick AI reasoning.** "Claude AI reasoning behind each
   decision" still produced sub-floor WR. → **`feedback_confidence_is_not_edge`**.
   Narrative/LLM reasoning ≠ statistical edge. tbot has no DSR / PBO / SPA gate
   — it trades on per-pick conviction, exactly the unfiltered firehose our
   money-ready verdict is built to reject.

3. **Asymmetric the wrong way.** Best +$5.16, worst -$7,868 — wins capped tiny,
   losses unbounded. Expectancy massively negative. → **expectancy gate**
   `E = WR·avg_win − (1−WR)·avg_loss` (MONEY_READY critique #2). The WR+PF dual
   gate also rejects this; expectancy makes the rejection unambiguous.

4. **No concentration cap.** FOREST alone = 69% of loss. → **top-symbol < 30%**
   concentration gate (current gate g + v2 #8).

5. **All-LONG micro-cap altcoins** ($0.0035–$0.16: CHIP/AZTEC/FOREST/GALA) in a
   down tape. → **`feedback_long_source_bias`** + **capacity/liquidity gate**
   (v2 #9). Illiquidity is almost certainly why the FOREST stop slipped 52%.

## Takeaway

tbot fails **every** proposed money-ready v2 gate. It is empirical validation
that `reports/MONEY_READY_METHODOLOGY.md` is targeting the right failure modes:
per-pick AI reasoning + no statistical gate + no tail-risk cap + no
concentration cap + long-only illiquid names = -$11k on 116 trades.

**No code change.** Net actions:
- Reinforces the CRYPTO stop-loss P0 — ship hard per-position stop enforcement;
  a -52% unstopped move must be structurally impossible.
- Reinforces the tail-risk (CVaR/MDD) + concentration gates in the v2 set —
  keep them in, do not water them down.
- Standing rule confirmed: never size a class on per-pick AI conviction without
  the DSR/PBO/SPA verdict + expectancy + tail-risk gates clearing first.
