# Stock APIs deployed from Windows source · ledger normalization audited · cost measurement verified

**Date:** 2026-11-23
**Owner:** `copilot-cli-deepseek-flash`
**Closes:** todo #19
**Also covers:** completion of the H-248 ledger normalization and independent verification of the equity cost measurement

---

## TL;DR

| Item | Before | After |
|---|---|---|
| `stock_intel.php` | HTTP **404** | **`{"ok":true,"company_name":"Apple Inc",…}`** with live technicals |
| `penny_stocks.php` | HTTP **404** | **`{"ok":true,"total":1529,…}`** live screener data |
| `findstocks/portfolio2/api/` | **did not exist** on live or in repo | created + connector deployed |
| Monitored systems serving real JSON | 4 of 7 | **6 of 7** |
| `alpha_engine` ledger normalization | 1,874 rows dropped, cause assumed | **audited: irrecoverable, not a normalizer bug** |
| Round-trip cost | 0.9756 bp (unverified recompute) | **verified by independent recompute — 0.9756 bp** |

---

## 1. Todo #19 — the two missing APIs

### Where the source was

Recovered over SSH from the Windows host:

```
C:/Users/zerou/Downloads/findtorontoevents.ca (3)/findtorontoevents.ca/findstocks/portfolio2/api/
    stock_intel.php    19,488 B   sha256 676f675392a7…
    penny_stocks.php   11,707 B   sha256 c688cf3bcfd6…
```

Both pass the PHP 5.2 gate unchanged (no short arrays, no `__DIR__`, no closures).

### The real reason for the 404s

The endpoints did not 404 because a file was missing from a directory that existed.
**The `api/` directory itself did not exist** — in the repo, `findstocks/portfolio2/`
contained only `data/penny_picks_latest.json`, and on the live host the path returned
404 because nothing had ever been uploaded there.

That also explains an older mystery: `kimi_goldmine_api.php` required
`findstocks/portfolio2/api/db_connect.php` and could never have worked. (That file was
already repointed to `findforex2` in the previous commit; this creates the directory
its proper connector belongs in.)

### What was created

| File | Purpose |
|---|---|
| `findstocks/portfolio2/api/db_config.php` | host/user/db for `ejaguiar1_stocks`; password resolved from the FTP-deployed `.env` via `_fs_cred()` — **no hardcoded secret**, because the hardcoded one in five other configs is stale |
| `findstocks/portfolio2/api/db_connect.php` | mirrors the deployed, working `findforex2/api/db_connect.php`; sets `$conn`, emits JSON and exits on failure |
| `findstocks/portfolio2/api/stock_intel.php` | from Windows, unmodified |
| `findstocks/portfolio2/api/penny_stocks.php` | from Windows, unmodified |

### Deployment gotcha worth recording

`curl -T` returned `curl: (9) Server denied you to change to the given directory`
because FTP cannot create directories implicitly. The remote directory had to be made
first:

```bash
curl -K - -Q "MKD /findtorontoevents.ca/findstocks/portfolio2/api" 'ftp://ftps2.50webs.com/'
```

Then all four uploads succeeded (`rc=0`).

### Verified live

```
GET /findstocks/portfolio2/api/db_connect.php
    -> 0 bytes  (the failure path prints JSON, so EMPTY = CONNECTED)

GET /findstocks/portfolio2/api/stock_intel.php?action=full&ticker=AAPL
    {"ok":true,"ticker":"AAPL","company_name":"Apple Inc",
     "stock_info":{"sector":"Technology",...},
     "technicals":{"current_price":349.21,"data_points":252,
                   "sma_20":347.7355,"sma_50":329.9982,"sma_200":286.9691,
                   "golden_cross":true,...}}

GET /findstocks/portfolio2/api/penny_stocks.php?region=us&max_price=5
    {"ok":true,"region":"us","total":1529,"count":50,
     "stocks":[{"symbol":"NXAT","price":0.548,"change_pct":144.97,...}]}
```

System status after deploy — **6 of 7** now serve real JSON:

```
Crypto Winner Scanner    OK json
Meme Coin Scanner        DB FAIL      <- todo 18, separate MySQL account
Sports Betting Picks     OK json
Stock Intelligence       OK json      <- was 404 MISSING
Penny Stocks             OK json      <- was 404 MISSING
Forex Insights           OK json
Mutual Funds             OK json
```

`penny_stocks.php` uses **no database at all** (it proxies the Yahoo Finance screener),
so it is unaffected by the credential problem — only `stock_intel.php` needed the DB.

## 2. Ledger normalization — audited, and complete

The concern was that `alpha_engine` contributed only 327 of 2,204 rows to H-248 because
1,874 lack a `timestamp`. If a fallback field existed, the sample would grow a lot.

`tools/pumpwatch_consensus.py` now emits a `normalization_audit` block measuring this
instead of assuming it:

| Ledger | rows | entry-time usable | `timestamp` | `entry_date` | note |
|---|---|---|---|---|---|
| `alpha_engine` | 2,204 | **327** | 327 | 290 | `entry_date` is a **strict subset**; 1,877 rows have neither |
| `claws_ml_battleground` | 562 | **562** | — (uses `timestamp_est`) | 0 | 100% covered |
| `mercury2` | 469 | **466** | 469 | 0 | 3 rows lack `pnl_pct` |

**The alpha gap is irreducible from this file.** Two things pin that:

1. `entry_date` adds **zero** rows — every row with an `entry_date` also has a `timestamp`
   (only-timestamp = 37, only-entry_date = 0).
2. The one field with 94.9% coverage, `closed_at`, is the **exit** time. Clustering two
   systems on when they *exited* would manufacture consensus out of unrelated entries,
   so it is deliberately excluded. The tool documents this inline.

Normalization is therefore maximal, and the H-248 result is unchanged by the audit
(`REFUTED`; difference −0.7614%, CI [−1.7405, +0.2761]). Reporting the audit alongside
the result is the point: the limitation is now **measured** rather than asserted.

## 3. Cost measurement — verified, not trusted

`reports/equity_cost_hml.json` was recomputed two independent ways.

**a) Components recompose exactly**

```
spread 0.7696 + commission 0.0 + ECN 0.0 + SEC 0.206 + FX 0.0 = 0.975600 bp
stated total_bp                                              = 0.975600 bp   MATCH
```

**b) Recompute from the 191 per-symbol rows** (not from the stored aggregate)

```
cs usable symbols            65        (stored: 65)
median cs_bp (usable)        0.769640  (stored: 0.7696)
median roll_bp (valid)       4.768644  (stored: 4.7686)
independent total = 0.7696 + 0.206 = 0.9756 bp
stored total_bp                   = 0.9756 bp        agree within 0.01bp
```

### Final measured round-trip cost: **0.9756 bp**

Against the repo's constants:

| Constant | Value | Ratio to measurement |
|---|---|---|
| `alpha_engine/cost_model.py` | 5.0 bp | **5.13×** too high |
| `pod_equity_breakout_backtest` | 25.0 bp | **25.63×** too high |
| Roll estimator (what HML used) | 4.7686 bp | 4.89× too high |

This confirms what `updates/2026-11-23-equity-cost-model-sensitivity.md` concluded: the
constants overstate cost by 5–25×, **but** the HML verdict does not depend on it — at the
measured cost HML still nets only +0.092%/yr against a 4.32% hurdle (assessment:
`ROBUSTLY-KILLED`). The cost correction changes the *sign* of marginal strategies, not
their verdict.

Caveat unchanged: 0.9756 bp is an optimistic **floor** (patient execution, $20k/name =
0.008% of ADV, liquid names). Corwin-Schultz and Roll disagree 6× on the same bars, so
cost is a range and the safe planning number remains the higher end.

## 4. Reproduce

```bash
# cost verification
python3 -c "import json;d=json.load(open('reports/equity_cost_hml.json'));print(d['cost_round_trip_bp'])"

# ledger normalization audit + H-248
python3 tools/pumpwatch_consensus.py --cost-bps 25

# PHP 5.2 gate over everything touched
python3 tools/validate_php52.py findstocks/portfolio2 investments/goldmines \
    findcryptopairs findmutualfunds2 findforex2
```

---

Infrastructure and descriptive statistics only. No picks, no signals, zero capital, and
nothing here is investment advice.
