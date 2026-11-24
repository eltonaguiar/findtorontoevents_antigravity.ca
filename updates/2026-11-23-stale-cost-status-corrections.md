# 2026-11-23 — Stale "cost UNMEASURED" statements corrected

**Scope:** documentation accuracy only. No verdict, tally, threshold, break-even,
kill rule, strategy metric or pre-registration parameter was changed.

**Measurement cited:** `reports/cost_measurement_new_classes/class_cost_new_20261123.json`
(branch `cost/new-classes-2026-11-23` @ `7379044`), reproducible from main with
`python3 tools/equity_cost_measure.py --offline --classes-measure-new`. Values:

- BOND: median RT **1.2125 bp** (per-side ~0.606 bp), 10/10 names (JNK 0.5442 … TLT 2.5126), `MEASURED_FROM_LAST_SESSION` (Friday bars; bar-range upper bound, NOT NBBO).
- COMMODITY_FUTURES: median RT **6.3182 bp** (per-side ~3.16 bp), 7/7 names, `MEASURED_UPPER_BOUND`, live `=F` front-month series. **Roll cost still UNMEASURED.**
- COMMODITY_ETF_PROXY: **5.3234 bp**, `ETF_PROXY_ONLY` — the ETF's spread, NOT the futures cost (not used in any edit below).
- PENNY_STOCK: **21.2974 bp**, 7/8 names, convenience sample with survivor bias, `MEASURED_FROM_LAST_SESSION`.

## Statements found (quoted from `origin/main`, real line numbers)

### `docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md`

| Line | Statement | Classification | Action |
|---|---|---|---|
| 31 | `**Equity cost UNMEASURED.**` (row 3) | still true — EQUITY was not measured | left alone |
| 34 | `(equity/ETF cost `UNMEASURED`)` (row 6) | still true for EQUITY and the broad ETF class (only bond ETFs were measured) | left alone |
| 36 | `commodity cost `UNMEASURED`` (row 8) | wrong now for the front-month futures spread; roll cost still unmeasured | annotated in place (verdict, PF, break-even untouched) |
| 37 | `ETF cost `UNMEASURED`; **dividend-adjustment method flagged `UNMEASURED`**` (row 9) | wrong now for the bond-ETF spread; dividend-adjustment flag still unmeasured | annotated in place |
| 39 | `Commodity cost `UNMEASURED`` (row 11) | wrong now for the front-month spread; roll cost still unmeasured and no second-month series exists | annotated in place; row verdict unchanged |
| 63 | `ETF cost is `UNMEASURED`` (prose on row 9) | wrong now for the bond-ETF spread | annotated in place |
| 78 | `\| **BOND** \| ... \| **1 UNKNOWN** \| **UNMEASURED** \|` | wrong now | annotated in the cost cell only |
| 79 | `\| **COMMODITY** \| ... \| **2 UNKNOWN** \| **UNMEASURED** \|` | wrong now for the futures spread; roll cost still unmeasured | annotated in the cost cell only |
| 83 | `**UNMEASURED** (30 bp constant charged)` (PENNY_STOCK) | wrong now (a measured sample exists), but the 30 bp constant is still what strategies are charged | annotated in place |
| 89 | `**Blunt count: 11 of the 12 classes have `UNMEASURED` transaction cost.** Only CRYPTO has a measured number, ...` | historical sentence, now false as a count | count corrected in an appended bracket; original kept and dated `(as of 2026-11-22)` |
| 154 | `... bond ... cost is unmeasured, so 11 of 12 classes cannot produce an unconditional verdict.` | historical sentence, now false as a count | annotated in place |

### `docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md`

| Line | Statement | Classification | Action |
|---|---|---|---|
| 38 | `n/a (cost UNMEASURED)` (commodity term-structure carry row) | wrong now for the front-month spread; roll cost still unmeasured | annotated in place |
| 50 | `**Equity cost is UNMEASURED.**` | still true | left alone |
| 76 | `cost `UNMEASURED`; test not runnable.` (commodity carry) | wrong now for the front-month spread; test still not runnable without a second-month series | annotated in place |
| 122 | `equity cost is `UNMEASURED`` | still true | left alone |

### `docs/preregistration/HML_VALUE_TEST_2026-11-22.md`

| Line | Statement | Classification | Action |
|---|---|---|---|
| 48 | `tools/measured_cost_recost.py → UNMEASURED = {"BOND", "COMMODITY", "EQUITY", "ETF", "FUTURES"}`. Only FOREX (7.53 bp, upper bound) and CRYPTO (12.60 bp) are measured. | a quoted tool constant inside a blocker, not a measured claim | **NOT EDITED** |

## The HML `UNMEASURED` set — what it is, and why it was not touched

It is not a test parameter; it is a quotation of `UNMEASURED` from
`tools/measured_cost_recost.py`, cited to justify blocker **B2** ("EQUITY execution
cost is UNMEASURED"). But the document is a **pre-registration** whose own opening
(lines 8–11) says the kill rule, the cost treatment, the benchmark and the null
reasoning are "fixed before any data is touched", and whose cost treatment (§3)
is explicitly what B2 gates. Amending it would be rewriting a frozen
pre-registration, so it was left alone. Flagged here instead:

- The quoted set is still accurate as a description of that tool's constant, and the
  sentence is specifically about **EQUITY**, which was not measured.
- `tools/measured_cost_recost.py` is **not present on `origin/main`** (only on disk),
  so the citation is itself stale in a separate way. That is a pre-existing issue,
  out of scope for this task.
- When B2 is cleared, the operator should amend it deliberately, citing the new
  artifact for EQUITY only.

## The "11 of 12" count

Original: 11 of 12 classes UNMEASURED (only CRYPTO measured), as of 2026-11-22.

Taxonomy (12): CRYPTO, EQUITY, ETF, BOND, COMMODITY, FOREX, FUTURES, MEME,
PENNY_STOCK, INDEX, SPORTS, MUTUAL_FUND.

Measured now (5):
1. CRYPTO
2. FOREX
3. BOND
4. COMMODITY (front-month futures spread; roll cost still UNMEASURED)
5. PENNY_STOCK

Still UNMEASURED (7):
1. EQUITY
2. ETF
3. FUTURES
4. MEME
5. INDEX
6. SPORTS
7. MUTUAL_FUND

5 + 7 = 12 → **7 of 12 remain UNMEASURED**. (The 2026-11-22 baseline had 11
unmeasured because FOREX was still counted unmeasured in that count's sentence; the
FOREX measurement landed the same day and doc 22:131 already records it.)

## Proof of what did NOT change

- TALLY line, doc 22:177 and doc 15:196: `TALLY: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)` — identical before and after.
- Verdict-word occurrence counts, doc 22 before → after: INVESTABLE 36→36,
  NOT_INVESTABLE 28→28, UNKNOWN 37→37, KILL 10→10, DEAD 0→0, BLOCKED_DATA 2→2,
  MARGINAL 1→1.
- Verdict-word occurrence counts, doc 15 before → after: INVESTABLE 2→2,
  NOT_INVESTABLE 1→1, UNKNOWN 5→5, KILL 8→8, DEAD 0→0, BLOCKED_DATA 3→3,
  MARGINAL 4→4.
- `python3 -m pytest tests/test_edge_research_tally_consistency.py -q` → **18 passed**.

## Still genuinely UNMEASURED (not claimed otherwise anywhere)

- Commodity **roll cost** (no roll-adjusted curve).
- **NBBO** for every new figure (all are 1-min bar-range upper bounds).
- **Commission** (not included in any of the new figures).
- **Survivor-free penny cost** (the penny universe is a convenience sample).
- EQUITY, ETF (broad), FUTURES, MEME, INDEX, SPORTS, MUTUAL_FUND.
