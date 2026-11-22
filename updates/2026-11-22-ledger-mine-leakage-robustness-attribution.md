# Ledger mine: leakage audit, per-class robustness, source attribution (2026-11-22)

Reproducer: `python3 tools/ledger_mine.py --boot 2000`
Artifacts: `reports/ledger_mine/ledger_mine.json`, `reports/ledger_mine/ledger_mine.md`
Evidence class: **OBSERVED** (live resolved picks, net of the ledger's own class-cost model)
Capital: none. Not investment advice.

Closes todos **31, 33, 34, 35**.

---

## What was broken

Two defects in my *own first run* of the tool, both caught before anything was published:

1. **Timestamp parser dropped 67% of the ledger.** It accepted only
   `%Y-%m-%d %H:%M:%S %Z`, silently rejecting the 6,513 rows using the
   ISO-with-microseconds form `2026-11-22T10:57:17.123456+00:00` that dominates
   the file. First-pass "results" were computed on the 3,632 legacy-format rows
   — a selection on the data-generating process. Now 10,968/10,968 parse, 0 rejected.

2. **Benjamini-Hochberg q-values attached to the wrong sources.** The first
   version computed q in iteration order and then mapped them onto rows *after*
   sorting by net. It printed `genetic_programmer` (p=0.2932) as
   "POSITIVE-SURVIVES-BH at q=0.0040" while `ml_strategy_reviver_inverse`
   (p=0.0000) got q=1.0000. The q-map is now built before any sort, with a length
   assertion.

Both were over-stating evidence. Both are why the rejection count is now printed
next to the kept count: a silent 67% loss cannot hide again.

---

## 31 — Leakage audit

| signal | measurement |
|---|---|
| rows kept | 10,968 / 10,968 |
| WON on gross | 4,780 (43.58%) |
| WON on net | 4,732 (**43.14%**) |
| gross-win but net-loss | 48 (1.00% of gross wins) |
| redundant symbol-day re-emissions | **3,916 (35.70%)** |
| extreme P&L (\|net\|>50%) | 2 rows, both `mercury2_fast` BTCUSDT |
| zero-cost rows | 0 |
| coverage | 2026-02-17 .. 2026-11-22, 276 days |
| provenance (created_at > closed_at) | **UNMEASURED** — artifact ships no `created_at` |

Concentration: `luxalgo_filters` 36.7% of rows; CRYPTO 83.0% of rows (HHI 0.699).

**CORRECTION (2026-11-22, same day).** The line here originally read
"**The load-bearing leakage finding is the 35.7% redundancy**" and described
1,048 symbol-day clusters as re-emissions of one signal.

That was **wrong as a measure of duplication.** Symbol-day clustering conflates
two different things: two *different* sources trading the same symbol on the same
day (legitimate agreement between independent emitters) and one source recording
the *same fill* twice (genuine duplication). Strict duplication on the correct key
`(source, symbol, side, exact entry)` is **375 rows = 3.42%**, not 3,916 = 35.70%.

Cluster-bootstrapping is still the right choice for exactly the reason above —
symbol-day clustering does break iid assumptions even when the rows are not
duplicates. But the 35.7% figure overstated the duplication. Verdicts are
unaffected: all seven are unchanged under strict dedup
(see `updates/2026-11-22-ledger-dedup-default-and-round29-correction.md`).

`breakout_b_ml` is a **phantom source**: 44 rows, **zero** wins, every row exactly
−0.1097%, all status FLAT, exits `expired_72h`. It is a flat fee charged 44 times,
not a strategy outcome. Any PF computed over it is meaningless.

---

## 33 — Per-class, cluster-robust (cluster = symbol|closed-day, 2,000 resamples)

| class | n | clusters | gross bp | net bp | WR% | PF | PF CI-LB | t | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| CRYPTO | 9,099 | 4,319 | −8.20 | **−18.17** | 43.02 | 0.89 | 0.83 | −4.34 | FAIL |
| EQUITY | 936 | 769 | +23.60 | **+18.60** | 46.47 | 1.09 | 0.88 | 1.00 | pf>1, CI includes 1 |
| ETF | 590 | 477 | +4.68 | −0.32 | 42.88 | 1.00 | 0.80 | −0.03 | FAIL |
| FOREX | 252 | 209 | −13.13 | −15.13 | 40.48 | 0.67 | 0.42 | −2.36 | FAIL |
| COMMODITY | 44 | 19 | −331.51 | **−346.51** | 15.91 | 0.12 | 0.03 | −4.32 | FAIL |
| BOND | 35 | 30 | −13.22 | −18.22 | 40.00 | 0.66 | 0.27 | −1.12 | FAIL |
| FUTURES | 12 | 11 | +72.09 | +57.09 | 58.33 | 1.56 | 0.34 | 0.62 | INSUFF-N |
| **ALL** | **10,968** | **5,830** | −6.13 | **−15.24** | 43.14 | **0.90** | **0.85** | **−3.91** | FAIL |

**The live system loses 15.24bp per resolved pick, and the loss is
statistically unambiguous (t = −3.91).** Zero of seven classes clears a
cluster-robust PF of 1.0. EQUITY is the only class with a positive point
estimate and its CI lower bound is 0.88 — it is not established, it is
undetermined.

Independent replication: subq-savant reported "10,968 resolved picks, mean
−0.1524% per trade, win rate 43.14%" from separate code. This tool reproduces
−15.24bp and 43.14% exactly. Two independent implementations, same answer.

---

## 34 — Source attribution (n_trials = 20 sources with n≥30)

Positive raw: **9/20**. Positive after Benjamini-Hochberg: **3/20**.
Expected positive-by-chance at α=0.05: **1.0**.

Ledger total: **−167,151 bp-rows**. Largest absolute contributors:
`kimi_riseoftheclaw` −55,828 (33.4%), `luxalgo_filters` −46,607 (27.9%),
`aggregated_picks` −39,437 (23.6%), `ml_bg_system_f` −24,537 (14.7%).

### Falsification pass on the three BH survivors

I do not accept a BH survivor on the q-value alone. Each was re-tested for
time-concentration, split-half stability, direction balance, and best-day removal.

| source | n | days | net | split-half | drop best day | verdict |
|---|---:|---:|---:|---|---|---|
| `ml_strategy_reviver_inverse` | 85 | **8** | +145.5 | +198.7 → **+31.2** | +145.5 → +75.6 | **does not hold** |
| `mega_mutation` | 105 | 67 | +135.0 | +83.6 → **+196.0** | +135.0 → **+123.8** | **holds** |
| `dna_winner_picks` | 141 | 18 | +67.6 | +161.6 → **−132.9** | +67.6 → +26.8 | **does not hold** |

- `ml_strategy_reviver_inverse`: only **8 distinct days**, 84% edge decay across
  the split, half the edge from one day. 85 rows over 8 days is one episode.
- `dna_winner_picks`: **sign flip** across the split (+161.6 → −132.9), 61% of
  days negative. Dead.
- `mega_mutation`: only survivor. 67 days, direction-balanced 55L/50S, split-half
  improves, best-day removal costs only 8%. Still n=105 in AVAX/JUP/WIF/DOT —
  memecoin-adjacent, and 23% of its P&L is in the top 5% of wins.

**Honest score: 1 of 67 emitters shows a survivable positive expectancy, and it is
n=105 on 67 days.** That is a CANDIDATE, not an edge. It needs the forward clock.

---

## 35 — The disputed 78.9% CRYPTO claim: NOT REPRODUCED

| measure | value |
|---|---|
| CRYPTO rows | 9,099 |
| WR on net | **43.02%** |
| WR on gross | 43.48% |
| mean net | **−18.17 bp** |
| PF net | 0.89 |

No source with n≥20 reaches 78.9%. The highest is
`ml_strategy_reviver_inverse` at 69.41% on n=85 — and that source just failed the
falsification pass above. The 14-day panel independently shows CRYPTO at
**46.57% WR** (`pick_summary_stats_14d.json`), not 78.9%.

**The 78.9% figure is not a measurement of the live CRYPTO ledger. It should be
treated as an artifact of a narrower filter that is not documented in the
payload.** Consistent with the pre-existing page flag at commit `c1b977997`.

---

## What changed in the programme's beliefs

1. **The live ledger is a proven loser at −15.24bp/pick (t=−3.91), not a
   "disputed" performer.** This is now the strongest single piece of evidence in
   the programme and it points the same way as every cost-side measurement.
2. **35.7% of the ledger is redundant re-emissions.** Every historical
   ledger-based statistic that did not cluster-correct was inflated.
3. **One candidate survives: `mega_mutation`.** It does not clear the promotion
   gate (no forward clock, n=105) and it stays in SHADOW.
4. **`breakout_b_ml` must be quarantined** — 44 phantom flat-fee rows.
5. **Provenance remains UNMEASURED for this artifact.** `h119_ledger_audit.py`
   can run the test on the H-119 ledger because that one carries `created_at`;
   this one does not, so backfilled and pre-registered rows are indistinguishable
   here.

## Promotion-gate state after this block

| class | label | basis |
|---|---|---|
| CRYPTO | **REFUTED** | −18.17bp, PF 0.89, CI-LB 0.83, n=9,099 |
| COMMODITY | **REFUTED** | −346.51bp, PF 0.12, n=44 |
| FOREX | **REFUTED** | −15.13bp, PF 0.67, n=252 |
| BOND | **REFUTED** | −18.22bp, PF 0.66, n=35 |
| ETF | **REFUTED** (tactical) | ledger −0.32bp; tactical engine 0.81 vs 60/40 0.86 |
| EQUITY | **NOT ESTABLISHED** | +18.60bp but CI-LB 0.88 |
| FUTURES | **UNMEASURED** | n=12 |
| `mega_mutation` | **CANDIDATE** | +135bp, n=105, 67d, survives falsification |
