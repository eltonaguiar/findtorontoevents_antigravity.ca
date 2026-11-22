# Findings — Blocks 1–2 Synthesis (2026-11-22)

Supersedes nothing: this is the delta on top of
[`00_FINDINGS_2026-11-22.md`](00_FINDINGS_2026-11-22.md). Every number below was copied
from a JSON/MD artifact on disk (see **Provenance** at the end), not from a summary.
Where a figure in the task brief disagreed with disk, disk wins and the correction is
called out inline.

---

## What changed since `00_FINDINGS_2026-11-22.md`

**1. FOREX moved BLOCKED_DATA → READY.**
`data/forex_rate_cache` now holds **110 ordered pairs** from the ECB fix via
Frankfurter. Eleven currencies in both directions means **55 independent crosses**,
not 110 (`forex_carry_trend_20261122.json` `panel.caveat`;
`fx_meanrev_20261122.json` `panel.dedup_rule`). Coverage is **2018-12-31 .. 2026-11-20**,
**2,022 observations per pair** (min = max = 2,022 across all 110 pairs), **0 interior
gaps > 5 business days**, **0 duplicate dates** (`block1_r02_fx_gap_audit.json`, gate
PASS). Acquisition sources that failed first: **Stooq** served a JS proof-of-work
challenge, **Yahoo** returned HTTP 429, and **FRED** failed with an HTTP/2 stream error
and then a 25 s timeout.

**2. BOND readiness was a false positive; fixed.**
`tools/class_data_readiness.py` had pointed BOND at `forex_rate_cache` with a minimum
of 1 file, so 110 FX spot CSVs made BOND report READY. It now reads
`"BOND": [("rate curve", DATA / "rate_curve_cache", 1)]` (`tools/class_data_readiness.py:68`)
and correctly reports **BLOCKED_DATA** ("rate curve: have 0, need 1"). Overall
readiness is **7/12** today (CRYPTO, EQUITY, BOND, COMMODITY, FUTURES blocked; ETF,
FOREX, PENNY_STOCK, INDEX, MEME, MUTUAL_FUND, SPORTS ready). The count fell from 8/12
because one of those eight was never real.

**3. Round 21 — FX momentum: KILL.**
63-day formation / 21-day hold, quintile long-short, 110-pair panel, 93 rebalance
windows, n = **4,092** pair-rebalances. Mean net **−36.88 bp**, median **−35.93**,
95% bootstrap CI **[−44.13, −29.59]**, 2x-cost **−46.88**, net win rate **44.23%**
(gross 45.50%), halves **−43.59 / −30.31**, worst / best window **−438.80 / +242.07**,
long leg **−33.97**, short leg **−39.79**. Null (1,000 shuffles, seed 42): null mean
net **−9.93 bp** (null gross mean **+0.07 bp**), observed at the **0.0 percentile** on
both net and gross, empirical p = 1.0 in the "as bad or worse" direction. All of G1–G4
fail.

**4. Round 22 — FX short-horizon mean-reversion: KILL, but genuinely informative.**
5-day formation / 5-day hold on the **deduplicated 55-cross** universe (54 traded,
**403** windows), n = **8,866**, positions per window 22. Mean gross **+4.30 bp**, mean
net **−5.70 bp**, median **−7.41**, 95% CI **[−8.25, −3.06]**, 2x-cost **−15.70**, net
win rate **47.27%** (gross 51.04%), halves **−5.20 / −6.19**, worst / best window
**−377.55 / +287.48**, long leg **−3.74**, short leg **−7.65**. Null (1,000 shuffles):
null mean net **−10.04 bp**, p95 **−7.97**. Observed sits at the **100.0th percentile**
with empirical p = **0.001** — the reversal effect is statistically **real** (G4
passes), but gross edge is **less than half** the 10 bp round trip (G1, G2, G3 fail).

**5. The single most important sentence in this section:**
a statistically real effect that is smaller than transaction costs is not a strategy,
and Round 22 is the cleanest example this programme has produced. Reversal in FX is
detectable at p = 0.001 and still loses money at both cost levels.

**6. Peer cross-check.**
Two peer challenge files exist (three paths, one a byte-identical duplicate, md5
`1ab93461c010c6d7f366854b7d967a77`):
[`REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD`](../../REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD)
and `reports/antigravity_review_Nov192026/REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD`.
The file claims n = **1,254**, gross **+28.22%**, fees 250.80%, net **−222.58%**,
permutation p = **0.000**, with **0 live fills**. Neither path completed a trade, so
both are classified **NOT_REPLICATED / UNMEASURABLE**. The cross-check is recorded in
the deepseek challenge file's Peer table
(`REALTIMECHALLENGE_deepseek-flash_20261122T0355_EST.MD`, "Peer cross-check").

**7. Round 141 live round: NO_TRADE, scored ZERO.**
Both venues were live and agreeing (Binance **59745.16** / KuCoin **59742.90**, ≈
**3.8 bp** apart, inside the 50 bp gate) and no setup existed at **09:02:59Z /
09:08:50Z / 09:14:49Z**. It establishes **nothing** about profitability: no entry, no
exit, no TP/SL resolution, no cost drag.

---

## Honest programme state after ~5 rounds of 200

Verdict per class from `reports/per_class_edge_verdicts_20261122.json` (11 published
rows) plus SPORTS, which has no row in that file and is listed as READY by the
readiness checker with no edge verdict.

| Class | Current verdict | Blocking reason |
|---|---|---|
| ETF | **KILL** | net edge −9.24 bps, cost survival −1217%, 0/62 windows admissible |
| BOND | **KILL** | 327 strong windows split 140+/187−; needs 3 same-sign |
| CRYPTO | **KILL** | gross +9.85 bps but net −20.15 bps, cost survival −205%, 26+/25− |
| FUTURES | **KILL** | net −9.00 bps, cost survival −895%, 96 strong windows 40+/56− |
| FOREX | **KILL** | R22 net −5.70 bps, CI-LB −8.25, gross +4.30 < 10 bp cost; R21 net −36.88 bps, CI-LB −44.13, 0.0 pct of null |
| MEME | **KILL** | skew −2.356, worst −75% vs best +52.57%, median 0.0 |
| EQUITY | **WEAK** | mean net +1.49 bps but CI-LB −2.58 (< 0), 2x-cost mean −13.51 bps |
| INDEX | **INSUFFICIENT_N** | denominator leak confirmed: 88 rows on 5 symbols, only 25 filed INDEX |
| COMMODITY | **NO_ROWS** | `data/cftc_cot` empty |
| MUTUAL_FUND | **NO_ROWS** | structurally unmeasurable on daily NAV |
| PENNY_STOCK | **NO_ROWS** | only a 59-symbol seed universe, no closed rows |
| SPORTS | **no verdict** | READY by data check; no edge row published |

- **Zero classes are investable. Zero reached CANDIDATE.**
- Of 200 planned rounds, roughly 5 have been executed. The remaining ~195 are mostly blocked by data acquisition, not by lack of ideas.
- The binding constraint is data: point-in-time earnings consensus, futures/commodity price series and CFTC COT history are all still missing, which keeps EQUITY PEAD, COMMODITY and FUTURES untestable.
- What would actually change the answer next: acquiring (i) a futures continuous series, (ii) CFTC COT history, (iii) point-in-time earnings consensus, (iv) a yield curve for BOND/carry. The FX carry leg in particular was **never tested** — both FX rounds tested momentum and reversal, not carry, because carry needs rate differentials and no yield curve exists on disk (`forex_carry_trend_20261122.json` `carry_note`).

---

## Methodological lessons worth keeping

- **Readiness checkers need class-specific paths.** BOND was reported READY because it was pointed at FX CSVs with a minimum of 1 file. A shared data directory is not shared evidence.
- **Dedup vs full-universe sign check (G6) caught a double-counting artefact before it was reported as edge.** With 110 ordered pairs, EURUSD and USDEUR are exact inverses, so the same move is counted twice. R22 pre-registered the 55-cross dedup as primary and recorded G6 (`dedup_full_same_sign = true`) rather than discovering the inflation after the fact. R21 used all 110 as instructed and its caveat says what that does to exposure.
- **The null distribution turns "positive but small" into "precisely how far below cost".** R22's gross +4.30 bp sounds like a lead; against a null mean of −10.04 bp it is a real effect that is still −5.70 bp net. R21's observed −36.88 bp sitting at the 0.0 percentile is worse than random, which no confidence interval alone would have said as clearly.
- **An anti-fishing clause keeps a kill a kill.** R22 reported the pre-registered 5d/5d result unchanged instead of scanning lookbacks for one that passes. A parameter search over the same data would have produced a positive-looking number and no information.

---

## Provenance

| Number / claim | Artifact |
|---|---|
| R21 panel (110 pairs, 2,022 dates, 2018-12-31..2026-11-20), stats, null, gates, KILL | `reports/forex_carry_trend_20261122.json` |
| Carry never tested; no yield curve on disk | `reports/forex_carry_trend_20261122.json` → `carry_note` |
| R22 dedup 55-cross universe, 54 traded, 403 windows, n=8,866, stats, null, G6, KILL | `reports/fx_meanrev_20261122.json` |
| 110 pairs audited, 2,022 observations/pair, 0 interior gaps > 5bd, 0 duplicate dates, gate PASS | `reports/block1_r02_fx_gap_audit.json` |
| Per-class verdicts and blocking gates | `reports/per_class_edge_verdicts_20261122.json` |
| 7/12 readiness; BOND points at `rate_curve_cache` | `tools/class_data_readiness.py:68` + its 2026-11-22 output |
| Prior baseline (FOREX BLOCKED_DATA, readiness 8 classes) | `docs/edge_research/00_FINDINGS_2026-11-22.md` |
| Peer claims n=1,254, gross +28.22%, net −222.58%, p=0.000, 0 live fills | `REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD` |
| Duplicate verified byte-identical (md5 match) | `reports/antigravity_review_Nov192026/REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD` |
| Round 141 NO_TRADE, Binance 59745.16 / KuCoin 59742.90, three poll timestamps | `REALTIMECHALLENGE_deepseek-flash_20261122T0355_EST.MD` |
