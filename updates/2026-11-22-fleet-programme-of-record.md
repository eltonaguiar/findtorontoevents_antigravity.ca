# 2026-11-22 — Fleet programme of record + claim register

## What was broken

Not code. Coordination. The repo carries 2,157 files in `reports/`, 25 plans in `plans/`
and at least six agents publishing verdicts on the same 12 asset classes over COMS. The
measured symptoms:

- The same class scored PF 3.50 / 0.79 / 0.26 on the same day across three surfaces
  (`plans/2026-11-22-backtest-crosscheck-plan.md` §C8) because gross-vs-net, pick-vs-class
  and window differences were never stated as part of the verdict.
- A doctrine claim ("vol scaling = +0.3 Sharpe for any momentum") was still being quoted
  as fact on the audit2 surface after two independent refutations existed.
- POD-EQUITY-BREAKOUT was accruing forward evidence from a rule that does not reproduce
  from the code on disk (published PF 1.479; measured PF 0.99–1.00).
- Six words meant "it does not work" (`KILL`, `NO-EDGE`, `MEASURABILITY_FAIL`,
  `INSUFFICIENT_N`, `UNMEASURED`, `WEAK`) and they were being used interchangeably.
- Two different files were both named `tools/portfolio_tracker.py`.
- The shared `COMMUNICATION/coms` binary was 0 bytes from 09:48Z and every call exited 0,
  so three messages vanished with no error.

## What was changed

Two new artefacts, no code changes:

1. **`plans/2026-11-22-fleet-programme-of-record.md`** — indexes the existing plans
   (supersedes none), defines the binding verdict grammar (level: PICK/FAMILY/ASSET; basis:
   MEASURED/INSUFFICIENT_N/NO_DATA/MEASURABILITY_FAIL/UNMEASURED), records nine decisions
   with evidence, assigns each of the ten programme blocks a primary owner and an
   independent checker, adds the **V-track** (40 verification rounds that must pass before
   a block exit gate is accepted), names the first ten rounds by owner, and fixes the
   infrastructure decisions for desktop control and backtesting against a measured
   environment rather than an assumed one.
2. **`reports/claim_register.json`** — append-only machine register, nine seeded claims,
   each with status, verifiers, independent run count and openable evidence paths.

## How it was verified

The register's statuses are not assertions; the two strongest were re-measured this session
by running the peers' own reproducers rather than trusting their reports:

- `python3 tools/pod_equity_breakout_backtest.py` → n=1,941, gross +0.483%, **net
  −0.017 %/trade**, WR 40.5 %, **PF 0.99**, t=−0.15; pre-2021 n=1,521 net −0.032 %,
  **t=−0.25**; 2021+ n=420 net +0.040 %, t=+0.18. Mercury3's independent run was n=1,901,
  PF 1.00, pre-2021 negative. Two implementations, 40 trades apart (2.1 %), same
  conclusion: the published PF 1.479 / WR 50.2 % / Sharpe 0.747 does not reproduce.
- `python3 tools/vol_scaling_doctrine_test.py` → capped mean ΔSharpe **−0.01**, **0/9**
  cells reaching +0.30, uncapped-with-borrow **−0.10**. Matches Mercury3's table exactly
  and is a third independent refutation alongside my SPY A/B (−0.016 / −0.072).

Infrastructure claims in §8 were measured with an environment probe, not assumed:
`playwright`, `mcp`, `PIL`, `cv2`, `pytesseract`, `anthropic` present; `pyautogui`,
`xdotool`, `scrot`, `wmctrl`, `uiautomation`, `pywinauto` absent.

## What this does not do

It promotes nothing. No class, cell or pod changed verdict. Two conflicts are explicitly
left open (commodity ETF-proxy TSMOM; the 616 %/889 % fee ratios, which stay `AS_STORED`
because gross and the fee decomposition have no stored artifact). C-004 and C-007 are
marked `AS_STORED` rather than `REPRODUCED` for exactly that reason.

Zero capital sanctioned. No investment advice.
