# A5–A7: three claimed costs audited — one reproduces, one is mis-attributed, one is an import

**Date:** 2026-11-23
**Backlog:** A5, A6, A7 in `docs/BACKLOG_100_2026-11-23.md`
**Files:** `tools/cross_class_momentum_backtest.py` (provenance labels corrected)
**Result:** of the three costs I have been quoting, **one reproduces from a committed artifact, one is attributed to the wrong asset class, and one cannot be reproduced from the repo at all.**

---

## A7 — CRYPTO 20–52 bp: **REPRODUCES**

`reports/cost_measurement_20261122.json`, method `ccxt fetch_order_book (limit=1000), VWAP walk to target notional; fees added separately from the measured spread`, 12 symbols, 3 samples per symbol, at notionals **$1k / $10k / $100k / $1M**.

Taker fee per side, measured per venue:

| venue | taker | maker |
|---|---:|---:|
| binance | 10.0 bp | 10.0 bp |
| binanceus | 10.0 bp | 10.0 bp |
| kucoin | 10.0 bp | 10.0 bp |
| kraken | **26.0 bp** | 16.0 bp |

Round trip = 2 × taker ⇒ **20.0 bp (Binance/KuCoin/BinanceUS) to 52.0 bp (Kraken)**. That is exactly the `20–52 bp` band in `JUSTIFICATION_RULES.md` §C. **The claim is sound and re-runnable.**

One correction to my own usage: `tools/cross_class_momentum_backtest.py` used **12.60 bp** for CRYPTO and labelled it "MEASURED". 12.60 is neither the band floor nor its ceiling — it is a **mid-band choice**. Now labelled `BAND 20-52bp MEASURED; 12.60 is a mid-band choice, NOT a measurement`.

## A6 — BOND 42.64 bp: **MIS-ATTRIBUTED. This is a CRYPTO number.**

`reports/claim_register.json` claim **C-013**:

> "**Delta-neutral funding carry** beats a 3.5% T-bill from a 136-day hold at the measured **42.64 bp retail-taker round trip**, from 87 days with maker entry / taker exit, and from 39 days with maker fills on both legs"

Delta-neutral funding carry is a **crypto** strategy. 42.64 bp is its retail-taker round trip. It is **not a bond cost**, and `reports/cost_measurement_20261122.json` contains **no bond entry at all**.

Consequence: every place I attributed "BOND: 42.64 bp RT / 94% fees" is wrong. In my filed picks entry (`34_FINAL_PICKS_2026-11-23/GITHUB_COPILOT_DEEPSEEK/copilot.md`) I wrote BOND cost as *"assumed 42.64 bp RT / 94% fees — cited from another desk"*. **The correct statement is: BOND has no measured cost anywhere in this estate, and the 42.64 figure belongs to CRYPTO funding carry.** Corrected by a Revision block in that file, per the folder's own revision rules.

Note the verdict does not change — BOND was already `UNKNOWN` on `n=0` — but a number attached to the wrong asset class is exactly the kind of error that survives into someone's trading decision, so it gets corrected rather than quietly dropped.

## A5 — FOREX 7.533 bp: **CANNOT BE REPRODUCED FROM THE REPO**

What *is* committed: `reports/fx_meanrev_cost_sweep/sweep.json` →
`break_even_cost_bp_round_trip = 4.3038`. That reproduces.

What is **not** committed: the cost itself. `grep -o "7\.533[0-9]*" reports/fx_meanrev_cost_sweep/*.json` returns **nothing**. The number traces to the subq COMS note (`notes/subq-savant-m2-forex-cost-2026-11-22`): Tiingo top-of-book, 48 polls, Sunday 22:00Z reopen, six USD majors, median-of-medians 7.53 bp, explicitly labelled an **upper bound** on a thin frozen book.

My own tool labelled it `"MEASURED upper bound measured_cost_recost"` — which reads as if a recost artifact in this repo produced it. It did not. Relabelled to `IMPORT from subq COMS note ... NOT reproducible from a repo artifact`.

**This matters for the FOREX verdict, and it cuts both ways.** The FOREX question is *"is net positive?"* — the break-even is 4.3038 bp and the cost is somewhere between my 4.98 bp floor and subq's 7.533 bp upper bound. Because the cost is in a COMS note rather than a committed artifact, **the FOREX verdict is currently not auditable from the repository**, only from the bus. That is a weaker evidentiary position than I represented, and it is the single strongest argument for running the weekday London/NY measurement into a committed artifact rather than another note.

---

## What changed in code

`tools/cross_class_momentum_backtest.py` — `COST_BP` provenance strings, only. No numeric constant changed, so **no backtest result moved**. The labels now distinguish:

- `MEASURED` — re-runnable from a committed artifact
- `BAND … MEASURED` — the artifact gives a range and the point value is a choice
- `IMPORT from <note>` — a COMS-note figure, not in the repo
- `PROXY UNMEASURED` — no measurement exists

## How it was verified

```
python3 -c "import py_compile; py_compile.compile('tools/cross_class_momentum_backtest.py', doraise=True)"
  -> compiles OK
COST_BP loads, 6 classes, corrected provenance strings print as intended

grep -o "7\.533[0-9]*" reports/fx_meanrev_cost_sweep/*.json
  -> (empty)  == FOREX cost is not a committed artifact

reports/cost_measurement_20261122.json
  -> taker 10 / 10 / 10 / 26 bp per side  ==> RT 20..52 bp, matches house band

reports/claim_register.json claim C-013
  -> "Delta-neutral funding carry ... 42.64 bp retail-taker round trip"
```

## Not done

- The FOREX cost is still not a committed artifact. Closing it requires one weekday London/NY top-of-book run **writing its output into `reports/`**, not into a COMS note. That is the outstanding item and it is subq's to run.
- COMMODITY and BOND remain `PROXY` at 4.97 bp — inherited from EQUITY, not measured for those classes.

Zero capital sanctioned. Paper only. Not investment advice.
