# Focus Decision (final_v3) — which asset classes + which mutual-fund subset

Based on the SubQ comparison (`subq/B_ASSET_CLASS_RANKING.md`, `subq/C_MUTUAL_FUND_SUBSET.md`) and the full audit.

## Decision: focus on 2 classes beyond mutual funds

**1. EQUITY (primary)** — the only class with a positive long-run expected return harvestable *cheaply today*:
- **Why:** equity beta + cross-sectional factors (momentum/value/quality/low-vol, net Sharpe 0.4–0.8) are the most robustly documented premia; near-zero maintenance; $1 minimum; high capacity; point-in-time backtesting is possible now (fix = add dividends to the price-only Nasdaq panel).
- **What to build:** a **diversified factor portfolio** (not single-name scouts), monthly rebalance, dividend-adjusted, benchmark-matched. Measure excess-of-benchmark, not absolute Sharpe.
- **Risk:** live EQUITY is PF 0.70 (z −3.03) — so factors MUST be benchmark-matched or it's just beta; the repo's prior failures were index mean-reversion (H7) and sector rotation, not the untested single-stock cross-section.

**2. CRYPTO (secondary)** — the only class with clean keyless data and the strongest session evidence:
- **Why:** Binance spot/funding is the only reliable keyless feed; it holds the only DSR-1.0 mechanism (funding carry H21–23) and the statistically-validated trend premium (Sharpe ~0.5–2.1 regime-dependent).
- **What to build:** a **vol-targeted trend sleeve** (50d+200d blend, 20% vol target) + a **funding-carry sleeve**, both measured **excess-of-benchmark on a bear-inclusive window**.
- **Risk:** economically marginal — carry returns 3.7–4.8% vs 4.5% cash; trend benchmark-relative-alpha is unproven (H1 0.60 vs B&H 0.56). Treat as a diversifier/drawdown-control sleeve, not a headline edge.

**Runner-up to revisit:** FUTURES (highest ceiling — CTA trend is the canonical managed-futures strategy) but **data-blocked** (no continuous-contract feed); revisit only after a real feed exists.

## Mutual-fund subset: least money in, lowest fees, least capital

**Best default: `VTI`** — Vanguard Total Stock Market ETF: **0.03% expense ratio, $0 minimum, fractional shares from ~$1.** Least money, least maintenance (buy-and-hold one fund), broker-portable. (`FZROX` 0.00%/$0 only wins if locked to Fidelity.)

**3-fund core (~70/15/15, rebalance annually):**
- `VTI` (US equity beta) 0.03%
- `BND` (total bond ballast) 0.03%
- `SGOV` or `VGSH` (short-Treasury cash floor) 0.04–0.09%

**Why ETFs over open-end funds:** intraday liquidity, fractional shares (no $3,000 Admiral minimum like VTSAX/VFIAX), 3 bp cost. Expected return is **~7–9% nominal equity beta + ~4–5% current T-bill carry** — explicitly **not a trading edge**, it is the market baseline that every repo "edge" failed to beat net of costs and selection bias.

**Repo fit:** demote `tactical_fund_rotation` to a benchmark reference; add a `BENCHMARK_SLEEVE` config in `portfolio_defs.py` + a monthly `benchmark_snapshot.py` that writes NAV rows and plots the sleeve vs SPY and the live closed-feed PnL — a **control arm**, never a pick emitter.

## The honest framing that governs all of it

- Mutual funds (index) + equity beta + crypto trend + funding carry are **risk premia / beta**, not contest-winning alpha. They are "high chance to be profitable" in the **long-run, low-maintenance, low-capital** sense — exactly what the user is asking for.
- The repo's 683-strategy zoo is overfit noise on broken data (0/166 money-ready). The profitable path is **one clean, benchmark-relative-validated sleeve per class**, plus the passive index baseline as the control.
