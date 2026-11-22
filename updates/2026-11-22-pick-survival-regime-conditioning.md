# Pick survival + regime conditioning (2026-11-22)

Reproducer: `python3 tools/pick_survival_regime.py --boot 1500`
Artifacts: `reports/survival_regime/survival_regime.json`
Closes todos **36, 37**.

---

## Two defects in my own first pass — both over-stated evidence

**1. Regime conditioned on the CLOSE date.** My first version joined each pick to
the BTC regime on the day it *closed*. That is look-ahead: a pick's P&L and the
"BTC above its 50-day SMA" flag are both functions of the same price path, so
wins sort mechanically into the UP bucket. It produced the programme's
best-looking number to date — `CRYPTO|UP +15.72bp, PF 1.12, CI-LB 1.03, survives
BH` — which was an artefact of conditioning on the outcome. The resolved ledger
carries no `opened_at`, so **regime at entry is UNMEASURED for those 10,968 rows**.

**2. "Picks beat BTC by +395bp/trade at t=9.33".** Arithmetically correct,
economically meaningless. H-119 is a balanced long/short book (226 long / 204
short) and BTC fell 3.66% per holding window over this sample. A market-neutral
book beats a falling long-only index by construction. The correct hurdle for a
zero-beta book is **cash**, and the correct test is regression alpha.

Both are now fixed in the tool, and both are retained in the output as
deliberately-labelled invalid variants so the size of the bias is visible.

---

## 36 — Survival

Scope: **H-119 only.** `reports/forward_observations.jsonl` is the only artifact
carrying `opened_at`, and it is single-hypothesis. n=430.
Durations are **right-censored** — picks still open are absent, so all of this is
conditional on having closed and under-states the tail.

| | |
|---|---|
| median duration | **24.1 h** |
| p25 / p75 / p95 | 11.2 / 85.2 / 1258.8 h |
| closed within 24 h | 49.8% |
| closed within 48 h | 67.7% |
| closed within 7 d | 77.9% |
| closed within 30 d | 88.6% |

| duration bucket | n | mean bp | WR% | PF | t |
|---|---:|---:|---:|---:|---:|
| <6h | 58 | **−68.59** | 24.14 | 0.49 | −2.54 |
| 6–24h | 156 | +31.40 | 43.59 | 1.33 | 1.57 |
| 1–3d | 103 | +42.20 | 47.57 | 1.44 | 1.72 |
| 3–7d | 18 | −86.49 | 33.33 | 0.54 | −1.04 |
| 7–30d | 46 | **+131.85** | 52.17 | 2.05 | 1.53 |
| >30d | 49 | +59.22 | 44.90 | 1.59 | 1.29 |

Nothing is significant. The only clean signal is that the **<6h bucket is
actively bad (−68.59bp, t=−2.54)**: very fast exits are stop-outs. Duration is
not monotone in return, so "just hold longer" is not a usable rule.

**Provenance: 430/430 rows have `created_at > closed_at` — 100% backfilled.**
This is the single most important line in the section. Every H-119 row was
written *after* the outcome was known. It is a backtest, regardless of the
filename. Combined with the earlier `tools/h119_ledger_audit.py` result
(cluster-bootstrap net PF CI-LB 0.775–0.850), H-119 cannot gate anything.

Cost actually charged: median fee 0.00bp, median slippage **16.00bp/side**.

---

## 37 — Regime

### Variant A (regime at CLOSE) — INVALID, look-ahead
Retained only to size the bias. Reported `EQUITY|UP +57.23bp q=0.0277` and
`CRYPTO|UP +15.72bp q=0.0277`. **Both are artefacts.** Do not cite.

### Variant B (regime at ENTRY) — the honest measurement
H-119, n=430, regime read at the entry date with no look-ahead.

| regime | n | net bp | WR% | PF | t |
|---|---:|---:|---:|---:|---:|
| BTC UP | 274 | +23.60 | 41.61 | 1.22 | 1.21 |
| BTC DOWN | 156 | +39.80 | 44.23 | 1.37 | 1.67 |
| vol LOW | 209 | +51.45 | 47.37 | 1.53 | 2.67 |
| vol MID | 159 | +21.53 | 38.99 | 1.20 | 0.77 |
| vol TOP | 62 | −24.17 | 35.48 | 0.83 | −0.60 |

Neither trend regime is significant, and the pick does **better** in DOWN than
UP — the opposite of the invalid variant. The one borderline cell is LOW-vol
(t=2.67), which is a single cell out of five and not BH-surviving after
correction. **Regime conditioning does not rescue H-119.**

### Variant C (the decisive test) — beta-adjusted alpha, then cost

| | |
|---|---|
| n paired windows | 430 |
| beta vs BTC | **−0.0217** (balanced book, as designed) |
| alpha | **+21.52 bp/trade** |
| alpha t-stat | **+1.29 — NOT significant** |
| mean BTC over window | −366.01 bp |

Side decomposition (hurdle = 0, the correct one for a neutral book):

| side | n | pick bp | t vs 0 |
|---|---:|---:|---:|
| LONG | 226 | **−8.77** | −0.37 |
| SHORT | 204 | **+71.86** | **+4.01** |

All of whatever is there lives on the short side, in a sample where BTC fell 20%.

Cost truth:

| | |
|---|---|
| gross mean/trade | +29.48 bp |
| round-trip cost (2 × 16bp measured) | 32.0 bp |
| **NET/trade** | **−2.52 bp** |
| mean hold | 205 h |
| annualised gross | +12.61%/yr |
| **annualised net** | **−1.08%/yr** vs T-bill 3.5%/yr |

---

## What this changes

1. **H-119 is net-negative (−2.52bp/trade, −1.08%/yr) and its "forward" ledger is
   100% backfilled.** It moves from CANDIDATE to **REFUTED** as a deployable edge.
2. **The programme's best-looking result was a look-ahead artefact.** Variant A
   survives BH and clears PF CI-LB 1.0 — and is wrong. That is the clearest
   demonstration yet that surviving a statistical filter does not make a number
   real; only the *measurement design* does.
3. **"Beats the benchmark" is not a verdict.** Benchmark choice decides the
   answer. A balanced L/S book must be tested against cash and against regression
   alpha, never against a directional index.
4. Fast exits (<6h) are stop-outs, not skill. If the system is to be changed at
   all, the exit logic is where the evidence points — but as a *loss reducer*, not
   an edge.

## Promotion-gate additions

| item | label | basis |
|---|---|---|
| H-119 (directional) | **REFUTED** | net −2.52bp/trade, −1.08%/yr; 430/430 backfilled |
| H-119 long leg | **REFUTED** | −8.77bp, t=−0.37 |
| H-119 short leg | **NOT ESTABLISHED** | +71.86bp t=4.01 but single-sample, in a falling market, and the book overall loses after cost |
| regime conditioning | **REFUTED as a rescue** | no entry-regime cell significant after BH |
