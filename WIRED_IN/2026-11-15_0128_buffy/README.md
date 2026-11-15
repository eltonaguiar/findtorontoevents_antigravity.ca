# WIRED_IN submission — `buffy` (Codebuff) · 2026-11-15 01:28 UTC

**Worktree:** `buffy` · **Branch:** `docs/wired-in-spec-2026-11-15` · **Engine:** `tools/sim_path_forward.py`
**Predecessors:** `2026-11-15_1227AM_profitability/buffy/`, `2026-11-15_1233AM_winning-strategies/buffy/`

---

## The claim under test

> "The path forward — a low-cost beta core plus a slow trend/dual-momentum overlay, occasionally a
> short-horizon swing rule — is profitable after costs, and can be shown to be so in backtests."

Two separate claims hide in that sentence, and they have **different answers**:

| Claim | Verdict | Evidence |
|---|---|---|
| *Profitable after costs* | **PASS** | Beta core compounds 10.76%/yr, DSR 0.99 over 22.08 years, net of 6 bps/side |
| *Better than the alternative you already have* (buy & hold / matched exposure) | **FAIL** | **0 of 6 active rules** beat their matched-exposure benchmark; best is −0.09%/yr |
| *Repeatable under doubling of costs* | **PASS for beta, FAIL for swing** | RSI(2) goes to −0.34%/yr at 2× costs; beta moves 0.01%/yr |

So: **profitable, yes. An edge over buy-and-hold, no.** The one genuinely valuable finding is not
alpha — it is that a 10-month SMA overlay **halves the drawdown for free** (−21.8% vs −50.8% max
drawdown, same Sharpe, return cost equal to trading costs).

---

## Contents

| File | Answers |
|---|---|
| [`specs/SPEC_ETF.md`](specs/SPEC_ETF.md) | The measured rule for ETF/index exposure (Faber 10-month SMA) — **the primary pick** |
| [`specs/SPEC_EQUITY.md`](specs/SPEC_EQUITY.md) | RSI(2) swing rule on SPY, plus an explicit statement of what was **not** measured (single-stock picks) |
| [`specs/SPEC_BOND.md`](specs/SPEC_BOND.md) | TLT as a momentum destination / duration sleeve; AGG benchmark |
| [`specs/SPEC_COMMODITY.md`](specs/SPEC_COMMODITY.md) | GLD as the third dual-momentum candidate — measured and rejected |
| [`specs/SPEC_CRYPTO.md`](specs/SPEC_CRYPTO.md) | BTC 200-day SMA trend rule — **the conditional pick** |
| [`specs/SPEC_FOREX.md`](specs/SPEC_FOREX.md) | Not measured. Measurement design + why carry is not wired in |
| [`specs/SPEC_PREDICTION.md`](specs/SPEC_PREDICTION.md) | Not measured. Binary settlement, and the fee curve that decides the class |
| [`PICK_JUSTIFICATION.md`](PICK_JUSTIFICATION.md) | What I recommend, the exact live parameters, and what would falsify it |
| [`BACKTEST_AND_RESEARCH.md`](BACKTEST_AND_RESEARCH.md) | Data, method, all results, 2× cost stress, IS/OOS, bugs fixed, literature consulted, limits |
| [`ELIMINATION_LOG.md`](ELIMINATION_LOG.md) | Each of the 8 rules and 6 classes, the gate it failed, and what eliminating it cost |
| `artifacts/` | `backtest_path_forward.json`, `backtest_path_forward_2xcost.json`, `forward_plan.json` |

---

## Headline table (baseline costs, 6 bps/side equity · 15 bps/side BTC · T-bill cash)

| Strategy | Style | CAGR | Excess vs matched benchmark | Sharpe | MaxDD | DSR | Trades |
|---|---|---:|---:|---:|---:|---:|---:|
| BH_SPY | beta core | 10.76% | −0.00% | 0.65 | −50.8% | 0.99 | 1 |
| SIXTY_FORTY | beta core | 8.11% | −3.03% | 0.65 | −28.5% | 0.99 | 1 |
| **FABER10_SPY** | trend overlay | 8.33% | **−0.09%** | **0.66** | **−21.8%** | 0.99 | 33 |
| DUALMOM_2 | trend overlay | 7.59% | −2.57% | 0.50 | −27.6% | 0.96 | 28 |
| DUALMOM_3 | trend overlay | 8.13% | −1.88% | 0.45 | −30.0% | 0.94 | 55 |
| RSI2_SPY | swing | 0.21% | −2.30% | −0.64 | −14.5% | 0.00 | 117 |
| BTC_BH | beta core | 51.04% | +48.67%† | 0.93 | −83.0% | 0.65 | 1 |
| **BTC_TREND200** | trend overlay | 58.62% | +47.69%† | 1.10 | −63.6% | 0.84 | 30 |

† Crypto's excess is measured against *SPY* at matched exposure, so it is crypto **beta**, not skill.
The honest crypto comparison is `BTC_TREND200` vs `BTC_BH`: +7.58pp CAGR and 19.4pp less drawdown —
real, but DSR 0.84 is below the 0.95 bar.

---

## Reproduce

```bash
python3 tools/sim_path_forward.py                      # baseline  -> reports/backtest_path_forward.json
python3 tools/sim_path_forward.py --cost-mult 2.0 \
        --out reports/backtest_path_forward_2xcost.json # stress
python3 tools/forward_tracker.py selftest              # 8/8 verdict-rule cases
python3 tools/forward_tracker.py status                # forward ledger verdicts
```

Data comes from the Yahoo chart API (adjusted close, dividends + splits) and is cached under
`data/cache/sim/`. Trial count is **N=8**; adding a strategy invalidates the deflated Sharpe and
must be re-run.

---

## Status

**NO-GO for real capital.** No asset class in this repo has a forward-verified edge. What this
submission establishes is narrower and defensible: *measured* evidence that low-cost beta works after
costs, that the drawdown-reduction overlay is cheap, and that four specific active rules plus one
entire asset class do **not** work — each for a stated, checkable reason.

I am not claiming alpha anywhere in this folder.
