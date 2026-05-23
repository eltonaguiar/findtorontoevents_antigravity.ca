# Leap Crypto — Fresh Picks 2026-05-13 (T-48h to contest close)

**Account:** The Leap Crypto, flat, $100,278 cash
**Window:** ~48h to May 15, 2026 close
**Universe:** BTC/ETH/SOL/DOGE/XRP USDC.P (Coinbase perps only)
**Live read:** TV `quote_get` confirms BTC $79,149.9 (chart locked to BTCUSDC.P; ETH/SOL/DOGE/XRP echoed same payload — known TV-MCP stale-symbol echo). Using user last-seen for the rest.

## Verdict: TWO PICKS — 1 anchor SHORT continuation + 1 satellite mean-revert LONG

This is NOT a pass setup but it is NOT a portfolio either. Prior bearish thesis (BTC topping $79-84k) banked +$278; tape now sits at the lower end of that zone with the bounce-or-break decision pending. 48h is too short to fade structure but long enough for one more leg if BTC loses $78.5k. I add ONE small counter-trend satellite so a sharp short-squeeze rip doesn't zero the round.

**Edge stability check:** `edge_stability_CRYPTO.json` 7d window WR 41.9%, PF 1.17 (n=831) — degrading vs 90d PF 1.27. CRYPTO is in DECAYING_EDGE per index file. This caps conviction; do not pyramid the anchor beyond entry.

**Lesson absorbed from leap_top5 research:** winners pyramid one directional trend with leverage; we won't pyramid on decaying edge, but we DO concentrate the anchor (10%) instead of 5×2%.

---

## Pick 1 — ANCHOR: BTCUSDC.P SHORT (continuation)

| Field | Value |
|---|---|
| Symbol | BTCUSDC.P (Coinbase) |
| Side | SHORT |
| Entry | $79,150 market, or limit-add at $79,400 (retest of broken micro-range) |
| Stop | $79,950 (above prior swing + round number) |
| TP1 | $77,800 (50% off) |
| TP2 | $76,800 (close remainder) |
| R | $800/BTC; reward to TP2 = $2,350 → **R:R 2.94** |
| Size | **10% of equity = $10,000 notional** at 5x leverage (margin ~$2,000) → 0.126 BTC |
| Expected $ outcome | win ≈ +$370 at TP2 / loss ≈ –$126 at stop (per 0.126 BTC sizing on cash, not levered margin) |

**Thesis (one line):** BTC failed to reclaim $81.2k after losing $84k; lower-high lower-low 4H structure intact; clean break of $78.5k opens $76.8k support shelf within 48h. Aligned with prior winning leap thesis that already paid.

---

## Pick 2 — SATELLITE: XRPUSDC.P LONG (mean-revert, hedge to BTC short)

| Field | Value |
|---|---|
| Symbol | XRPUSDC.P (Coinbase) |
| Side | LONG |
| Entry | $1.45 market (or wait for $1.43 limit) |
| Stop | $1.40 (below 7d support) |
| TP1 | $1.53 (Sat 1.6R) |
| TP2 | $1.58 (2.6R) |
| Size | **3% of equity = $3,000 notional** at 3x leverage → ~2,070 XRP |
| Expected $ outcome | win ≈ +$185 at TP2 / loss ≈ –$103 at stop |

**Thesis (one line):** XRP has decoupled from BTC selloffs intermittently this cycle (regime corr CRYPTO↔EQUITY +0.20, intra-crypto BTC↔XRP loosening); supplies a non-correlated tail if BTC squeezes higher on macro pop while alts grind sideways. Acts as partial hedge to anchor SHORT — direction split 1L/1S.

---

## Why no third pick

- ETH SHORT would just double BTC SHORT exposure (corr ~0.85) → violates anti-3xSHORT rule.
- SOL same direction tax + smaller % move historically in 48h.
- DOGE-L would duplicate theswarm DOGE-L (PCG-5 Gate 2 conflict).
- Adding a 4th pick is the breadth-not-depth mistake that capped prior round at +0.28%.

## Direction split

1 SHORT (anchor 10%) + 1 LONG (satellite 3%) = NET short ~$7,000 notional but not 3/3 SHORT. Compliant.

## Auto-exit conditions (all positions, hard rules)

- **Profit-lock (PCG-5 Gate 4):** if combined realized + unrealized hits **+3% account = +$3,008**, close everything and stand down to May 15.
- **BTC reclaim $80,200:** stop on the SHORT was $79,950 but a clean 4H close above $80.2k = thesis dead → close XRP-L too (alts would have already ripped).
- **Time-stop:** **2026-05-15 12:00 UTC** (12h before contest close) flatten everything regardless of PnL. Don't let auto-close print a worse exit.
- **Macro tape break:** if SPY gaps >–1.5% pre-market May 14, close BTC SHORT into the open (correlation spike could over-extend the move, but contest-close risk > extra alpha).

## Expected round outcome

- Base case (both hit TP2): +$555 ≈ +0.55%
- Anchor TP, satellite stop: +$370 – $103 = +$267
- Anchor stop, satellite TP: –$126 + $185 = +$59
- Both stop: –$229 (account –0.23%, well inside risk budget)

Beats prior +0.28% in base case; floor is survivable. Concentrated but not reckless on decaying-edge regime.
