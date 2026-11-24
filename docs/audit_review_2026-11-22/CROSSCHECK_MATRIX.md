# Cross-check matrix — /audit vs /audit2 vs /audit3 vs the database, per asset class

Measured 2026-11-22. Companion to `METRIC_DEFINITIONS.md` (the definitions) and
`tools/reconcile_class_metrics.py` (the measurement). Outputs:
`reports/class_metric_reconciliation_20261122.{json,md}`.

Rule of this document: **every PF is quoted with its surface, its n, and its cost basis.**
A PF without those three is not a number, it is a rumour.

---

## 1 The matrix

`/audit2` is a forward-pod surface and publishes no class-level PF, so its column is forward-row count.
`DB` is the live `trading_picks` table under the scrutiny-engine filter, gross then net at the ledger's cost.

| class | /audit PF (n) | /audit intrabar PF (n) | /audit3 net PF (n) | /audit3 alpha | DB gross PF (n) | DB net PF (n) | /audit2 fwd rows |
|---|---|---|---|---|---|---|---|
| CRYPTO | 0.2621 (22,287) | 0.9169 (3,731) | 0.7886 (6,926) | **−0.5549** KILL | 1.051 (11,006) | 0.996 (11,006) | 447 (H-119 only) |
| EQUITY | 1.08 (121) | 0.9796 (258) | 1.0499 (956) | −0.045 WEAK | 1.016 (1,210) | 0.959 (1,210) | **0** |
| COMMODITY | 0.3259 (35) | 1.0277 (235) | 0.1505 (50) | **−3.5699** KILL | 0.635 (1,498) | 0.532 (1,498) | 0 |
| ETF | **1.8752 (32)** | **0.0187 (56)** | 0.9947 (590) | −0.1036 WEAK | 0.940 (74) | 0.889 (74) | 0 |
| FOREX | 0.1751 (468) | 0.6351 (641) | 0.8496 (264) | −0.069 WEAK | 1.5335 (8,014) | 1.081 (8,014) | 0 |
| BOND | null (2), WR 1.0 | 0.3915 (26), WR 7.69% | 0.806 (37) | −0.0512 WEAK | 0.658 (75) | 0.564 (75) | 0 |
| FUTURES | 1.2706 (17) | 0.8929 (63) | 1.8719 (**4**) | +1.3353 INSUFFICIENT_N | 0.956 (66) | 0.841 (66) | 0 |
| MEME | 0.0234 (10) | UNMEASURED | not in ledger | not in ledger | 0.960 / 0.837 (79+23) | 0.843 | 0 |
| PENNY_STOCK | 0.1779 (4) | UNMEASURED | not in ledger | not in ledger | UNMEASURED | UNMEASURED | 0 |
| MUTUAL_FUND | 0.0 (0) | UNMEASURED | not in ledger | not in ledger | UNMEASURED | UNMEASURED | 0 |
| INDEX | not in /audit | not in /audit | not in ledger | not in ledger | 0.392 (25) | UNMEASURED | 0 |
| SPORTS | not in /audit | not in /audit | not in ledger | not in ledger | not in DB | not in DB | 0 |

Sources: `/audit` from `_raw/audit_data_money_ready_verdict.json`; `/audit3` from
`_raw/audit3_audit3_ledger.json` `classes[]`; DB from `tools/reconcile_class_metrics.py --db`
against `mysql.50webs.com/ejaguiar1_stocks` (52,608 closed rows).

---

## 2 What the matrix says, class by class

### CRYPTO — the only class where all four sources have a material sample
The only real measured population. WR 39–47% everywhere, i.e. it loses more often than it wins.
`/audit` daily PF 0.2621 and intrabar PF 0.9169 differ by 3.5x; the page publishes the lower one
but sizes on the higher one. The DB says gross 1.051 and net 0.996, the ledger says 0.789.
All of them are below the promotion bar, and selection alpha −0.5549 with `beta_dominant: true`
means even the positive gross number is market beta, not skill. **No surface claims an edge here.**

### EQUITY — the only class with net PF > 1 on a material sample, and the least powered
`/audit3` PF 1.0499 at n 956, but `required_n` is **22,569** (4% of what is needed). `/audit` shows
1.08 at n 121 and intrabar 0.9796. The DB says 0.959 net. So three of four surfaces are at or below
1.0 and the one above 1.0 is underpowered by 24x, with alpha −0.045 (negative). Any "EQUITY is our
best class" claim is a claim about the least-supported number on the page. **Zero forward rows**,
so it cannot be promoted regardless.

### ETF — the worst inversion on any surface
`/audit` daily PF **1.8752** vs intrabar PF **0.0187**: an inflation factor of **100.28x** and 58.9pp
of WR that does not survive honest first-touch resolution. `/audit3` 0.9947 and DB 0.889 net agree
with the intrabar number, not the daily one. **The daily ETF PF is an artifact and should never be
quoted.** This is the single clearest example of why intrabar resolution is mandatory.

### FOREX — largest population, worst ledger, best DB
8,014 rows in the DB with gross PF 1.5335 → net 1.081, yet `/audit3` says 0.8496 on only 264 rows
and `/audit` says 0.1751. The DB is 30x the ledger's sample for this class. Either the ledger's
canonical cohort is a badly unrepresentative 264-row slice of 8,014, or the DB rows include
something the canonical filter rejects. **This is the strongest single case for cohort forensics.**

### BOND — the 92-point intrabar inflation
`/audit` daily says WR 100% on n 2; intrabar says WR 7.69% on n 26. A 92.3pp gap. n 2 is not a
measurement, so the daily column is noise, but the *published* number is the noise.

### FUTURES — a verdict built on 4 rows
`/audit3` PF 1.8719 and alpha +1.3353 (the only positive alpha anywhere) on **n 4**. The DB has 66
rows at 0.841 net. The one positive alpha in the system is a 4-row artifact. It is correctly
labelled INSUFFICIENT_N, but the alpha +1.3353 will be quoted out of context by someone.

### COMMODITY — the KILL is over-determined but n-blind
`/audit3` 0.1505 on 50 rows, alpha −3.5699, KILL. DB 0.635 gross → 0.532 net on 1,498 rows.
The `H-101` COT look-ahead contamination applies here (`_reviews/05_COMMODITY.review.md`).
Every surface is below 1.0 except `/audit` intrabar 1.0277 (n 235, and −8.6pp WR inflation).
The kill is safe; the exact magnitude is not.

### MEME / PENNY_STOCK / MUTUAL_FUND / INDEX / SPORTS
Not measurable. MEME and PENNY are charged 30bp (10x EQUITY) and have tens of rows;
INDEX is an alias with 25 DB rows and no ledger bucket; SPORTS has no rows in `trading_picks` at all.
These are `UNMEASURED` and must stay that way until n is real.

---

## 3 Ranked list of what actually needs fixing

1. **The `invalid_row` exclusion bucket** (11,782 rows, larger than the 8,827 scored). Until it is explained, every class verdict is conditional on an undocumented filter. Highest leverage.
2. **Selection-alpha coverage.** Alpha is the gate, yet it is measured on 24.2% of CRYPTO, 50% of FOREX. Either alpha must cover the class or the verdict must say it is a subset verdict.
3. **Two cost constants for one class** (`/audit` 15bp vs `/audit3` 9.96bp CRYPTO). Unify or label every PF with which one it used.
4. **The daily-vs-intrabar inversion** (ETF 100.28x, BOND 92.3pp). Publish only the intrabar number, or publish both with the inflation factor adjacent.
5. **`mega_mutation` staleness.** It is the one cell that survives cost (net PF 3.33 on n 339) but its window ended 2026-06-11 and it is 82% single-source. It needs fresh rows, not a louder verdict.
6. **Zero forward rows for every class except CRYPTO.** No non-CRYPTO class can ever clear the forward gate until an emitter writes rows for it.

---

## Provenance

- model: none (curator-written from frozen evidence and one live read-only DB query)
- inputs: `_raw/` payloads (sha256 in `_MANIFEST.json`), `reports/class_metric_reconciliation_20261122.json`
- DB: read-only SELECTs against `ejaguiar1_stocks` on 2026-11-22; no writes
- snapshot: `/audit3/audit3_ledger.json` `88606e1e…` generated 2026-11-22T06:35:41Z
