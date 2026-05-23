# Leap Crypto fresh-picks review — 2026-05-13

**Subject:** 2 positions just placed in The Leap Crypto paper ($100,278.60 balance, T-48h to contest close 2026-05-15).
**Mode:** review only — no position changes.

## TL;DR

Keep both positions. **Do NOT add a 3rd.** Optional: halve BTC-S qty to 0.063 if you want to express discomfort with the forced 10x leverage; otherwise the 0.45% combined max-loss is well inside risk budget and the trade is internally consistent with the closeout thesis that just paid +$278.60.

## 1. Is the BTC-S still valid?

**Yes, but the thesis is now older and noisier than at original swarm-spec time.**

- Entry 79,551.5 is **above** the original swarm-target $79,150, so the short was sold into a stronger bounce — that's actually a *better* short fill (R:R lifted to 6.9 from spec 2.94 per placement log line 22).
- Invalidation logic intact: 4H close above $80,200 = thesis dead. SL at $79,950 is tight (~50bps); a single 4H squeeze wick can take it out without proving anything. Acceptable given 48h time-stop.
- `alpha_engine/data/regime_report.json` is **NOT a usable read** — it's running on 2026-03-23 candles ($70,115 BTC) and only the `regime_last_checked` field updates. Treat the "CHOPPY / RSI 56.5 / FLAT" output as stale and ignore it for this decision. Flag for Goal-#1 maintenance backlog.
- `reports/edge_10_btc_utc_backtest_20260513T020000Z.md` falsified the "22 UTC = 61.2% WR" memory claim (actual 42.9% n=14) — entry time is not a meaningful filter here.
- `edge_stability_CRYPTO.json` 7d window PF 1.17 (decaying) per the original swarm doc — caps conviction, but does not invalidate a single anchor SHORT that already has a built-in 4H invalidation. **Verdict: valid.**

## 2. Is XRP-L positioning sound?

**Marginal — it is the weakest position but a defensible hedge.**

- The role (alt-beta long, BTC-S hedge) is sound: DOGE played the same role last round and printed +$20.16 (small but positive — `leap_closeout` line 33).
- $0.0302 risk leg vs $0.1498 reward leg = 4.96 R:R; the satellite costs only $103 if it stops.
- Better alternative in the 5-symbol Leap universe? **No clearly better choice given the constraint that the LONG must be alt-beta with BTC-decoupling.** SOL is more BTC-correlated, ETH would duplicate BTC-S inversely (anti-hedge), DOGE just closed positive (avoid repeat-trade overfit). XRP at 1.4302 sits near 7d support — a structurally cleaner long than a fresh DOGE-L.
- Caveat: XRP has been range-bound; TP 1.58 (~10.5% above entry) in 48h requires a clear breakout day. Base-case is partial fill / chop, not full TP.

## 3. Add a 3rd position?

**No.** Three reasons:

1. The original swarm doc (`leap_fresh_picks_2026-05-13.md` line 53-58) explicitly rejected a third pick — adding ETH-S duplicates BTC-S correlation (~0.85), SOL adds direction tax, DOGE-L is overfit.
2. Top-5 Leap research (`leap_top5_traders_research_2026-05-13.md`) showed concentration > breadth: +0.28% on 47 strategies underperformed contest winners running 2-3 conviction picks at high leverage.
3. With 48h left, a third opening trade has insufficient time to mature past entry slippage + spread. The 98.7% margin buffer is *not* unused capital — it's contest-end risk buffer.

## 4. Sizing — should we halve BTC-S?

The forced 10x doubled spec notional ($10k vs $6.5k), but:

- Max combined loss is still $451 (0.45% of account), well inside swarm risk budget.
- Halving to 0.063 BTC cuts max-loss to ~$251 BUT also cuts max-win on the anchor from +$2,751 to +$1,375. On a +0.28% baseline round, you need the right-tail.
- The contest's reward function is right-tail-skewed (per top-5 research line 38) — winners don't downsize before close.

**Recommendation: leave 0.126 BTC.** The 10x is a forced constraint, not a sizing error.

## Risk register (open)

- BTC squeeze through $79,950 SL on macro pop (CPI / FOMC speak) is the single largest tail.
- Coinbase perp funding rate not checked — if funding flipped deeply negative, a short-squeeze is structurally more likely.
- Time-stop 2026-05-15 12:00 UTC is the right hard line; don't get cute and extend it.
