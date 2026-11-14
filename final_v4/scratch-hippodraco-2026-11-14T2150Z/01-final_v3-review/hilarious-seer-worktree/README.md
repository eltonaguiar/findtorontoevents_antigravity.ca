# final_v3 — common themes, fix plan, and the focus decision

**Date:** 2026-11-14 · **Scope:** every financial-prediction artifact modified today (committed to
`main` or sitting uncommitted in the local tree), plus the three fixes built in this pass.

This folder is a *decision* document, not another audit. The audits are done — `final_v2/` contains six
of them, and they do not disagree about the important thing: the system is not money-ready. What was
missing was (a) a common-theme synthesis across those six, (b) a plan that distinguishes fixes from
wishes, and (c) a defensible answer to "which asset class do we actually chase".

---

## The three answers

### 1. The common themes are five bugs, and four of them are about measurement

| # | Theme | Status |
|---|---|---|
| B1 | A refuted strategy is still advertised as **VALIDATED** in a live package | FAIL |
| B2 | Same asset class, three counts, ETF win rate **2.22% vs 68.42%** | FAIL |
| B3 | Crypto stop fills: 1.54× planned risk, **98.8% of the class loss**, 94% from one system | **fixed today** |
| B4 | 40–56% of non-crypto "SL_HIT" rows **never touched the stop** | OPEN — investigated, unexplained |
| B5 | Exit taxonomy lives in `exit_reason`, not `resolution_method` (null on all 3,500) | FAIL |
| B8 | 170 ledgers, **4 pass at 95% vs 8.5 expected by chance** | FAIL |

Full detail, including B6/B7/B9–B14 and the evidence for each: `00_common_themes/BUGS.md`.
Questions the data cannot yet answer: `00_common_themes/DEEP_INVESTIGATION.md`.

### 2. Focus: two classes, one of them conditional

**EQUITY** is the only class clearing its own cost structure (3.23× round-trip cost, mean +0.323%,
+238.3pp) and should get the first real benchmark test — against SPY, not zero.

**CRYPTO** is the only class with a diagnosed, fixable defect hiding a possible edge (fix → PF 0.768 →
≈1.00). It gets the second slot, conditional on the fill fix producing forward evidence.

Everything else is blocked by arithmetic: ETF at 267% cost/PnL, COMMODITY at 422%, FOREX a −16.2pp
breakeven gap, BOND n=35. **Mutual funds do not count** — they are the equity risk premium, not a
prediction edge, and cannot be measured intraday. See `03_focus/DECISION.md` and
`03_focus/MUTUAL_FUNDS_SUBSET.md`.

### 3. SubQ does not exist — recorded, not substituted

Not on PATH, no repo reference (only SQL `subquery` strings), and the Gravity Index catalog has no such
service. I ran the coverage/comparison function with three instruments instead and documented what SubQ
*would* add. `02_subq/COVERAGE_AND_COMPARISON.md`.

---

## What shipped (code, not just prose)

| Change | File | Verified by |
|---|---|---|
| Stop-fill model + provenance fields | `audit_trail/stop_fill.py` | 20 unit tests; `05_evidence/stop_fill_audit.txt` |
| Gap-aware fill in the resolver | `audit_trail/universal_pick_resolver.py` | flag `RESOLVER_GAP_AWARE_FILL`; compiles clean |
| Per-class 3× cost gate | `tools/per_class_cost_gate.py` | 18 unit tests; index built from 3,500 rows |
| Gate wired into HC filter | `tools/hc_gates_python.py` | default ON, fails open; `PER_CLASS_COST_GATE_ENABLED=0` reverts |
| `after_cost_net_per_trade` populated | `audit_trail/dashboard_generator.py` | class fallback when strategy index misses |
| Intrabar replay harness | `tools/stop_fill_replay.py` | 30 crypto + 25 equity + 25 ETF real replays |
| COT contrarian test | `tools/cot_contrarian_backtest.py` | **gate failed 4/4** — reported as failure |

52 tests pass. Documented in `updates/2026-11-14-stop-fill-cost-gate-cot.md` (AGENTS.md rule: no
undocumented fixes).

---

## The two numbers that matter

1. **Cost gate, retroactive:** keeping only classes that clear 3× cost turns **−617.5pp into +238.3pp**
   and removes **78.9%** of emissions. In-sample; it shows the gate removes losing classes, not that
   the survivor has alpha.
2. **Stop fills, real 1h replay** (`kimi_riseoftheclaw`, n=30): recorded **−177.90pp** → gap-aware
   **−46.19pp** (planned risk would be −42.00pp). 28 of 30 stops were genuinely touched; **14.3% gapped
   through**. This is what "PF ≈ 1.00, breakeven not profit" looks like in money.

---

## Structure

```
final_v3/
├── README.md                                  ← you are here
├── 00_common_themes/
│   ├── BUGS.md                                B1–B14, each with evidence
│   └── DEEP_INVESTIGATION.md                  D1–D8, what data is missing and what would settle it
├── 01_plan/
│   ├── GENERAL_FIXES.md                       G1–G24 across measurement, gates, exits, ML, hygiene
│   ├── GITHUB_ACTIONS_FIXES.md                A1–A12, measured over 360 workflows
│   ├── ASSET_CLASS_FIXES.md                   per-class defect → fix → re-emit gate
│   └── BACKTEST_SIMULATIONS.md                every fix simulated, incl. what was NOT simulated
├── 02_subq/COVERAGE_AND_COMPARISON.md          availability + the substitute protocol
├── 03_focus/
│   ├── DECISION.md                            the 90-day focus, with kill conditions
│   └── MUTUAL_FUNDS_SUBSET.md                 low-capital / low-fee subset, and the trap in the premise
└── 05_evidence/                               console output + JSON for every number above
```

---

## Reproduce

```bash
# stop-fill provenance across the ledger
python3 -m audit_trail.stop_fill --payload <dashboard_payload.json>

# the 3x cost gate (writes config/per_class_cost_gate.json)
python3 tools/per_class_cost_gate.py --build --input <dashboard_payload.json>
python3 tools/per_class_cost_gate.py --report

# real intrabar replay of stopped picks
python3 tools/stop_fill_replay.py --payload <payload> --class CRYPTO --source kimi_riseoftheclaw --limit 30
python3 tools/stop_fill_replay.py --payload <payload> --class EQUITY --limit 25

# the COT test that failed its own gate
python3 tools/cot_contrarian_backtest.py --json reports/cot_contrarian_2026-11-14.json

# tests
python3 -m pytest tests/test_stop_fill.py tests/test_per_class_cost_gate.py \
                  tests/test_cot_contrarian_backtest.py -q
```

---

## Limits of this package

- **One dataset.** Six peer packages review the same 3,500-row ledger; agreement between them is not
  independent confirmation (B14). Where I add information it is from a genuinely separate source: real
  Binance/yfinance candles and the CFTC COT table.
- **Replays are samples** (n=25–30 per class), not censuses. They justify investigation; they do not
  rewrite history.
- **No forward data exists** for any fix shipped today. "Unmeasurable" is the honest status of post-fix
  profitability, and it is not the same claim as "unprofitable".
- **B4 is unexplained.** The leading hypothesis (mislabelled exits) is consistent with the replay but
  not proven; a trailing-stop explanation remains possible for the touched subset.
- **SubQ could not be used.** No service by that name was found; see the SubQ document for what it would
  have added and how to plug it in.
