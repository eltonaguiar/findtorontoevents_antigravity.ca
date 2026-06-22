# crypto_short_volhigh — first ROBUST candidate of the winner-hunt (2026-06-22)

**Setup:** SHORT a CRYPTO pair when the entry-bar realized-volatility regime is HIGH (feature F4=HIGH,
computed from the pre-entry 1h-bar return dispersion in `stamp_entry_conditions.features`). Honest
intrabar first-touch ledger (SL-wins-ties, per symbol-direction-day dedup, net 16bp).

**Found by:** `tools/mine_entry_condition_cells.py` after the 2026-06-22 methodology swarm (#650)
added (a) the F4 volatility axis and (b) a symbol-bootstrap netPF CI-LB gate. It is the FIRST cell
(of 30 tested) to pass the full robustness gate.

## Why it's different from the refuted candidates
The plain `CRYPTO|SHORT|RSI50-70` was a regime artifact (won only in BTC-down months, lost 0/7 in the
up-month). Conditioning on HIGH VOLATILITY instead of RSI **disentangles the regime confound**:
high-vol = overextended moves that mean-revert, independent of BTC direction. The result wins in
both regimes.

## Falsification battery (class=CRYPTO, n=54, Feb–Jun 2026) — ALL PASS
| test | result | bar | pass |
|------|--------|-----|------|
| net_PF | 1.856 (WR 63%) | >=1.2 | ✓ |
| symbol-bootstrap netPF CI-LB(5%) | **1.41** | >=1.0 | ✓ (fairer fat-tail test) |
| ex-top-3 netPF (diagnostic) | 1.43 | — | ✓ survives concentration |
| time-split IS / OOS | 1.78 / 1.94, **both WR 63%** | both >1 | ✓✓ stable |
| regime (per BTC month) | Mar +U **83% WR**, May +D 72%, Jun +D 58% | wins up & down | ✓ |
| P&L concentration top-3 | 47% (RENDER 20/JUP 14/WIF 13), 19 symbols | <60% | ✓ |
| session | US 2.96 / ASIA 3.44 / EU 0.60 | not single-session | ✓ (EU weak) |

## Honest caveats (binding before any sizing)
- **n=54 < 80 forward gate.** Not promotable yet; needs forward accrual to n>=80, ideally 150.
- **EU session weak** (netPF 0.60, WR 53%) — the edge is US/ASIA-concentrated by session.
- **~4 months of data**; the high-vol regime itself is partly a 2026 feature. Walk-forward across
  more regimes still owed (deepseek's blind-spot note).
- **It's a SHORT** — real-money execution needs perps/margin/borrow; model funding + borrow cost.
- Cells overlap in the miner; treat the FDR/bootstrap as a screen, confirm on a fresh forward window.

## Status & next steps
- FORWARD-REGISTERED as `crypto_short_volhigh` in `stamp_entry_conditions.py` (tracker toward n>=80).
- Swarm-verify the vol-conditional mean-reversion thesis (TICK-15) before any paper-pilot.
- The always-on `robust-edge-miner` cron (#649) will keep re-confirming it as n grows; if it stays
  robust through n>=80 with CI-LB holding, it's a genuine paper-pilot candidate.
- This is the best honest lead found — **more robust than rsi5070-LONG** (which fails the bootstrap).
