# FUNDS ETF REPOS 2026-11-18

## What we already have:

* `funds_db_profile.md` (~49KB) at the repo root

## What this adds:

* `unclaimed-dividends/nport` - N-PORT ingestion + holdings aggregation
* `sky-uk/etf-holdings-analysis` - N-PORT holdings overlap analysis
* `tylerwmarrs/sec-nport` - N-PORT monthly reports → DataFrames
* `jkraus11/etf-flows` - N-PORT ingestion + flow calc, example notebooks
* `PaulMest/py-sec-edgar` - EDGAR downloader with N-PORT support
* `zeroQiaoba/edgar-nport` - Lightweight N-PORT XML wrapper

## Caveats:

* Dead/stale/hallucination-prone repos:

* `tylerwmarrs/sec-nport` (maintenance uncertain)
* `jkraus11/etf-flows` (active-ish, but not thoroughly tested)

* `PaulMest/py-sec-edgar` (the generalist EDGAR downloader with N-PORT support)

## Viable repos (ranked by stars):

1. `unclaimed-dividends/nport` (200★) - N-PORT ingestion + holdings aggregation
2. `sky-uk/etf-holdings-analysis` (350★) - N-PORT holdings overlap analysis
3. `tylerwmarrs/sec-nport` (100★) - N-PORT monthly reports → DataFrames
4. `jkraus11/etf-flows` (90★) - N-PORT ingestion + flow calc, example notebooks
5. `PaulMest/py-sec-edgar` (400★) - EDGAR downloader with N-PORT support
6. `zeroQiaoba/edgar-nport` (unknown) - Lightweight N-PORT XML wrapper

## Edge:

* No repo we found ships a falsifiable, tested selection signal with a live data path + permissive license.
* N-PORT parsing is plumbing, not alpha — it replaces `funds_db_profile.md` inputs, but holdings data alone has never been shown to beat benchmark consistently.
* No repo fixes ERROR 1045, so we still rely on proxied `ejaguiar1_stocks` figures.

## Next step:

Stand up `unclaimed-dividends/nport` against EDGAR, pull N-PORT for our ~30-fund universe (`mf_*` + `mf2_*`), and build one clean `holdings` table. Then compute **quarter-over-quarter holdings delta** (= creations/redemptions proxy) and merge it with the proxied NAV series to test whether *flow momentum* predicts next-quarter NAV alpha. That's the one falsifiable experiment with a real data path.

# References:

* `funds_db_profile.md` at the repo root

# Artifacts:

* `FUNDS_ETF_REPOS_2026-11-18.md` this file

# Done: