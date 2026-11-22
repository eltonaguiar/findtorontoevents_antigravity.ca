
> code · openrouter/free

**CRYPTO** — blocked. 629 tested cells with negative net expectancy (-0.38%) and CI excluding zero on the wrong side. No strategy family survives this multiple-testing burden. Configuration change most likely to reveal edge: **switch benchmark from BTC-hold to cash** (removes beta drag) and **require 2x slippage + funding-rate filter** on entry.

**EQUITY** — blocked. 19 cells, CI straddles zero (+0.098% [-0.52, +0.72]). No family clears IR≥0.5 vs SPY at 2x slippage. Configuration change: **extend holding period to 20–60 days** (reduces turnover cost, captures factor persistence) and **universe restrict to mid-cap + quality factor**.

**ETF** — blocked. 12 cells, net ~0% [-0.42, +0.45]. Same issue. Configuration change: **use SPY-hedged legs (long factor / short SPY)** to isolate alpha; benchmark becomes cash, not SPY.

**FOREX** — blocked. 18 cells, CI includes zero, n=264 insufficient for IR≥0.5 vs DXY at 2x slippage. Configuration change: **restrict to G10 carry + trend (3M lookback), 1:1 risk:reward, 2-week max hold** — reduces noise, aligns with known persistent anomalies.

**COMMODITY** — blocked. H-101 look-ahead (COT T+3 lag) and M-095 cotton over-emission (14× re-emission) invalidate the 48 picks. PF 0.29 policy-clean. Configuration change: **enforce T+3 COT embargo, deduplicate signal dates, require n≥100 unique signal dates** — current data is structurally corrupted.

**BOND** — blocked. n=37 below floor, 2 cells tested. Configuration change: **universe expand to global govvies + IG credit, signal = carry + roll-down, hold 3M, benchmark = cash** — current n too small to judge.

---

**Summary**: All six classes are blocked by the measured state. The single highest-leverage configuration change across the board: **mandate 2x slippage + funding/carry costs in the cost model** — the current "net" numbers still understate true execution cost for high-turnover strategies.
