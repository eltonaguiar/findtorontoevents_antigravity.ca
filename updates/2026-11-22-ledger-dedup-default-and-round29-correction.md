# Dedup is now default — and a round-29 figure I overstated (2026-11-22)

Reproducer: `python3 tools/ledger_mine.py --boot 1500` (dedup is now the DEFAULT;
`--no-dedup` keeps the old behaviour for comparison)

---

## What changed

`tools/mega_mutation_falsification.py` found 16/105 duplicate rows inside
`mega_mutation` — including the **same position emitted twice on the same day**
(AVAXUSDT SHORT @9.409 and JUPUSDT LONG @0.1698, both 2026-04-30). That
prompted the obvious question: **how much of the whole ledger is like this?**

`tools/ledger_mine.py` now de-duplicates **by default**, on the key
`(source_system, symbol, side, exact entry price)`. Within one emitter an
identical key is one position recorded twice — a strategy cannot fill twice at
the same price to the cent and have those be two trades. The key includes the
source, so it can never merge two different emitters' picks.

## A round-29 number I overstated

Round 29's leakage audit (L4) reported:

> **3,916 rows (35.70%) are redundant symbol-day re-emissions across 1,048 clusters**

**That was wrong as a measure of duplication.** L4 counts rows sharing a
symbol **and a closed day**, which conflates two completely different things:

| what L4 actually measured | what it is |
|---|---|
| two **different** sources trading BTCUSDT on the same day | legitimate agreement between independent emitters, not duplication |
| one source recording the **same fill** twice | genuine duplication |

Strict duplication on the correct key is **375 rows (3.42%)**, not 3,916 (35.70%).

The lesson is worth recording because the inflated number was the more alarming
one and I did not question it: **a clustering statistic is not a duplication
statistic unless the key proves it.** L4's text is corrected here; the tool still
reports the symbol-day clustering, now with the correct label.

## The verdicts did not move

| class | round 29 (raw) | now (dedup) | verdict |
|---|---:|---:|---|
| CRYPTO | −18.17 bp, PF 0.885 | **−16.04 bp, PF 0.90 (LB 0.84)** | FAIL (unchanged) |
| EQUITY | +18.60 bp, PF 1.088 | **+19.29 bp, PF 1.09 (LB 0.89)** | pf>1, CI includes 1 (unchanged) |
| ETF | −0.32 bp | **−0.22 bp** | FAIL (unchanged) |
| FOREX | −15.13 bp | **−15.45 bp** | FAIL (unchanged) |
| COMMODITY | −346.51 bp | **−369.80 bp** | FAIL (unchanged) |
| BOND | −18.22 bp | **−18.22 bp** | FAIL (unchanged) |
| FUTURES | +57.09 bp, n=12 | **+57.09 bp, n=12** | INSUFF-N (unchanged) |
| **ALL** | −15.24 bp, PF 0.904, t=−3.91 | **−13.40 bp, PF 0.91, t=−3.38** | **FAIL (unchanged)** |

**Zero of seven verdicts changed.** The ledger still loses money at
t = −3.38 on 10,593 de-duplicated picks. Removing the duplicates makes the result
12% *less* negative, which is the right direction for the ledger and changes
nothing about the conclusion.

Notably `mega_mutation`'s duplication rate (15%) was roughly **4× the ledger
average** (3.42%). A source with an unusual number of duplicate rows is a source
whose statistics need the most scrutiny, which is exactly the order the
falsification battery applied them in.

## Why default rather than a flag

A duplicated row is not an independent observation. Leaving the default at
"count everything" means every future reader inherits an inflated `n` unless they
remember to pass a flag. The correct default is the one that cannot over-count;
`--no-dedup` remains available for anyone who needs to reproduce the old numbers.

## Scorecard impact

`reports/weekly_scorecard/` now reflects the deduplicated ledger:
live ledger net expectancy **−13.40 bp, n=10,593, PF 0.91, t=−3.38** — still
REFUTED, and still the single strongest piece of evidence in the programme.
