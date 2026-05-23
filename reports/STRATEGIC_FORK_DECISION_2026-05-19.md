# Strategic Fork Decision — Path D — 2026-05-19

Multi-AI consensus on the post-Grok strategic fork. **Path D wins** across 4 of 6 voters (Claude / DeepSeek / xAI / Codex all picked D; Gemini picked B; Ring picked C). 2-round swarm: 4 initial parallel consults + 1 synthesis round.

## The decision

**Path D — Build the 3 literature-backed sidecars + explicit 90-day hard-freeze on the 4 dead classes with reopen criteria.**

| component | spec |
|-----------|------|
| H-033 EQUITY industry/sector cross-sectional momentum | Moskowitz-Grinblatt 1999. Long top-2 / short bottom-2 of 11 SPDR sectors by 21d return. Trend filter: SPY > 12M MA. Monthly rebal. Expected Sharpe 0.35-0.60. |
| H-034 COMMODITY term-structure roll-yield | Gorton-Rouwenhorst 2006. Long backwardation / short contango quintile across liquid commodity futures. Expected Sharpe 0.30-0.55. |
| H-035 FUTURES TSMOM diversified | Moskowitz-Ooi-Pedersen 2012. 12M sign across ~25 futures, vol-scaled. Free AQR data + yfinance fallback. Expected Sharpe 0.35-0.65. |

## Why D wins

- **Claude:** 23/40. "9 harness kills prove validation capacity is the binding constraint, not hypothesis quality. Hard-freeze 4 zombie classes to concentrate validation bandwidth on the 3 academically-replicated free-data strategies, with an explicit 90d reopen gate so the freeze is a decision, not drift."
- **DeepSeek:** 26/40 (B was 28 numerically but DeepSeek recommended D anyway). "Sidecars are your only free-data lifeline to survival; alt hypotheses require capital you don't have yet — sequence them, don't parallel them."
- **xAI:** D wins. "The only sequence that converts already-validated free-data signals into live P&L before the next kill cycle, without the focus tax of parallel infra work."
- **Codex (original):** D. "3 classic sleeves are the only credible free-data paths to actual deployable edge; new-infra detours burn a year."

## Why C and B lost

- **Ring (C / Hybrid):** "Marginal cost of sidecars 4 and 5 is nearly zero" is wrong. Validation IS the bottleneck (proven by 9 kills). Hybrid splits attention; both done badly.
- **Gemini (B / Pivot):** edge-probability score of 9/10 collapses to ≤4 the moment you impose the free-data constraint — options chains aren't free; CEF universe needs vendor data. Gemini scored an untestable strategy as high-edge — exactly the trap M-107 was designed to prevent.

## Hard-freeze rules — CRYPTO / FOREX / BOND / ETF

These classes have **NO realistic free-data edge candidate** at $10M-$100M with M-107 constraints. Freeze rules:

| class | freeze duration | reopen trigger |
|-------|-----------------|----------------|
| CRYPTO | 90 days from 2026-05-19 = 2026-08-17 | NEW hypothesis clears edge_stability_harness AND comes from a source NOT in any existing banned family. NO funding-rate, NO fear-greed-RSI, NO curve-fit ML. |
| FOREX | 90 days = 2026-08-17 | Only with a directional macro-regime signal (NOT COT-directional — banned). Rate differential + carry passes the ban; needs separate pre-registration. |
| BOND | 180 days = 2026-11-16 | Nothing plausible in free data at this AUM. Reopen only if (a) data infrastructure shifts (e.g., free TRACE micro feed) or (b) operator-funded paid bond-data feed. |
| ETF | 180 days = 2026-11-16 | Same as BOND — calendar/country-momentum decayed; creation/redemption needs intraday infra. |

## Operational rules during the freeze

1. **No new production code that scores or filters these 4 classes** beyond what already ships. Existing analytics keep running; the freeze is about strategy R&D, not display infra.
2. **The 3 new sidecars (H-033/H-034/H-035) are paper-only research** until they clear `edge_stability_harness.is_admissible()` AND 90 days of forward-tested paper. Same M-107 discipline as the 9 prior kills.
3. **Re-litigate CRYPTO data integrity:** the 500 BOND-tagged crypto rows (run 26130640164) signal an ingestion bug — fix in next session before any other CRYPTO work.

## Time-to-real-money expectation

Realistic timeline if H-033/H-034/H-035 all clear:
- Sidecars built + harness run: 1 turn (this turn).
- 90d paper forward-test: 90 days.
- Real money sizing: end-of-Q3 2026 at earliest.
- Expected sustained Sharpe per harness-cleared strategy: 0.35-0.60 (institutional but not glamorous).

**This is NOT 10x-in-a-year. This is real-money quant. Mark expectations accordingly.**

## What happens if all 3 sidecars REJECT (like the last 3 did)

Per Claude's flag: "if all 3 classic sleeves fail harness, you're in the same hole — just with cleaner paperwork." Contingency: revisit Gemini's B path (mid-cap earnings vol / CEF discount), which requires the operator to fund a paid options/CEF data feed. That's a strategic-fork escalation, not autonomous.
