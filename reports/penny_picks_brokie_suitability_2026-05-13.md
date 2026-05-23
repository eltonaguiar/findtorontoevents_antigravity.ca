# Penny picks vs BROKIE suitability check — 2026-05-13

## Verdict

**Penny picks are NOT suitable for BROKIE placement today.** Three independent
blockers, ranked by severity:

1. **Data is 16 days stale.** `findstocks/portfolio2/data/penny_picks_latest.json`
   was generated 2026-04-27. The generator workflow
   `.github/workflows/penny-stock-picks.yml` runs daily on its
   `cron: 0 12 * * 1-5` schedule but has **failed every run since
   2026-04-28** because the script's source endpoint
   `findstocks/portfolio2/api/penny_stocks.php` returns HTTP 404 on
   production (PHP file never merged to `main` — see Root-cause addendum
   below). The earlier `reports/penny_picks_cron_investigation_2026-05-08.md`
   tagged this as `disabled_manually` but it described workflow ID 233176023
   on the OLD findtorontoevents.ca repo; this repo (findtorontoevents_antigravity.ca)
   has the workflow live and failing. Either way, no fresh picks reach
   `penny_picks_latest.json`.

2. **Exchange-coverage mismatch.** Of the cached top-20, **10 are Canadian**
   (TSX 6, TSX-V 3, CSE 1). BROKIE runs on TradingView paper-trade through
   the `tv-paper-trade` skill which paths picks via `BINANCE:`,
   `NASDAQ:`, `NYSE:`, etc — the four-portfolio playbook
   (SCALPER/TESTER/TRUSTOURSCORE/BROKIE/zerounderscore) does not list
   TSX-V or CSE adapters. Without confirming TV symbol coverage for
   `TSX:CVVY` / `TSX-V:LCX` etc, those 10 names are paper-only on the
   Canadian side, not executable here.

3. **Rating thin.** Only 1 STRONG_BUY (LCX.V, the Canadian) and 5 BUY
   among the top-20. The other 14 are HOLD — BROKIE charter requires
   "verified alpha, highest conviction only" equivalent thresholds, and
   HOLD doesn't clear that bar.

## What the cached top-10 looks like

| Rank | Symbol | Price | Score | Rating | Exchange | RSI | mom_3m | TP | SL |
|---|---|---|---|---|---|---|---|---|---|
| 1 | LCX.V | $2.28 | 77.0 | STRONG_BUY | TSX-V | 68.4 | +228.6% | $2.96 | $1.94 |
| 2 | BTE | $4.58 | 66.0 | BUY | NYSE | 55.2 | +33.1% | $5.95 | $3.89 |
| 3 | BATL | $3.74 | 65.7 | BUY | NYSE-A | 45.3 | +350.9% | $4.86 | $3.18 |
| 4 | TRX | $1.24 | 63.3 | BUY | NYSE-A | 22.8 | +43.2% | $1.61 | $1.05 |
| 5 | VFF | $2.84 | 62.8 | BUY | NASDAQ | 54.5 | -21.9% | $3.69 | $2.41 |
| 6 | CVVY.TO | $1.35 | 62.8 | BUY | TSX | 52.7 | +42.7% | $1.75 | $1.15 |
| 7 | CRON | $2.68 | 61.4 | HOLD | NASDAQ | 56.4 | -4.7% | $3.48 | $2.28 |
| 8 | ABEV | $2.88 | 60.8 | HOLD | NYSE | 40.7 | +20.3% | $3.74 | $2.45 |
| 9 | THX.V | $1.38 | 59.4 | HOLD | TSX-V | 45.5 | -2.0% | $1.79 | $1.17 |
| 10 | ORE.TO | $2.25 | 59.2 | HOLD | TSX | 42.4 | +18.2% | $2.92 | $1.91 |

Note: prices are 16 days old. Several have likely moved out of these
ranges; specifically TRX at RSI 22.8 was deeply oversold and may have
bounced, BATL at +350.9% 3m-momentum is exactly the kind of name that
reverts hard.

## Risk fit if the pipeline were live

Assuming fresh picks + TV exchange coverage existed, BROKIE charter says:
$1K balance, 5-10% sizing, 0.75x ATR SL / 1.5x ATR TP.

For a $2-3 penny stock with ~5% daily ATR:
- 5% size of $1K = $50 per trade
- 0.75x ATR SL = ~3.75% stop = max loss ~$1.88 per trade
- 1.5x ATR TP = ~7.5% target = win ~$3.75

Risk math is tolerable, but with thin volume on TSX-V names and live
slippage, real fills can drift 2-5 % from entry. NYSE-listed names
(BTE, ABEV, CRON, VFF) are the only safe candidates.

## Root-cause addendum — why the pipeline stopped (verified 2026-05-13)

Earlier cron audit (`reports/penny_picks_cron_investigation_2026-05-08.md`)
reported workflow ID 233176023 as `disabled_manually` 2026-02-21. That
report audited the OLD `eltonaguiar/findtorontoevents.ca` repo where the
workflow was genuinely disabled. On THIS repo
(`eltonaguiar/findtorontoevents_antigravity.ca`) the workflow file was
ported in active state via commit `edcc1be903b` (also 2026-02-21) and
has been running ever since on its `cron: 0 12 * * 1-5` schedule —
`gh run list -w "Penny Stock Daily Picks"` shows every run since
2026-04-27 has FAILED:

```
[penny_picks] WARNING: Failed to fetch us offset=0: Expecting value: line 1 column 1 (char 0)
[penny_picks] WARNING: Failed to fetch ca offset=0: Expecting value: line 1 column 1 (char 0)
[penny_picks] INFO: Universe: 0 candidates after filtering
[penny_picks] ERROR: No candidates found. Exiting.
```

`scripts/penny_stock_picks.py:107-121` calls `{API_BASE}/penny_stocks.php`
where `API_BASE` defaults to `https://findtorontoevents.ca/findstocks/
portfolio2/api`. Probing that URL from this host returns HTTP 404 with
the 50webs 'Object not found!' page — JSON parse fails because the body
is HTML.

The PHP file itself **does not exist on `main`**. It was added in commit
`fa7ecda8e4d` ('Add CoinGecko dual-source meme scanner ...') on stale
branches `GROK_FINAL_2026`, `OPUS46`, and `STOCKS_KIMIS_CLAW`, but the
entire `findstocks/portfolio2/api/` directory was never merged into
`main`. Companion `tools/deploy_penny_stocks.py` is in the same boat —
exists on those branches, not on `main`.

So the workflow has been writing to `penny_picks_latest.json` from a
phantom universe. The last successful 2026-04-27 run likely hit an
endpoint that WAS live on 50webs from a manual FTP deploy of one of
those stale branches' PHP files, but the file has since been overwritten
or rotated.

## Recommended next steps (revised after root-cause)

1. **Resurrect the PHP endpoint.** Either:
   - **Option A (faster):** `git checkout OPUS46 -- findstocks/portfolio2/api/penny_stocks.php tools/deploy_penny_stocks.py`,
     review the cherry-pick on a branch, FTP-deploy the PHP to
     `findtorontoevents.ca/findstocks/portfolio2/api/penny_stocks.php`,
     then commit the resurrected files to `main`. **Note:** the FTP
     step cannot be automated via GitHub Actions on 50webs (per
     `CLAUDE.md` 'Critical File Rules': '50webs has no shell — files
     don't reach production until somebody FTP-uploads them'). Requires
     running `tools/deploy_penny_stocks.py` with `FTP_SERVER` / `FTP_USER`
     / `FTP_PASS` set, or a manual FTP session.
   - **Option B (cleaner):** rewrite `scripts/penny_stock_picks.py:107-156`
     to source the universe directly from yfinance (e.g. `yf.download`
     over a US/CA penny universe seeded from a static symbol list at
     `data/penny_universe_seed.json`). No PHP dependency, no 50webs
     round-trip, no GitHub Actions IP at risk of being WAF-blocked.
2. **Once Option A or B lands and a fresh `penny_picks_latest.json`
   commits successfully**, filter to NYSE / NASDAQ / rating>=BUY and
   swarm-vet before placing on BROKIE.
3. **Document the stale branches as a recovery source.** Three stale
   branches carry artifacts that may be needed later (`GROK_FINAL_2026`,
   `OPUS46`, `STOCKS_KIMIS_CLAW`) — they should not be deleted without
   a manifest of what each carries vs `main`.

## Refs

- Stale picks: `findstocks/portfolio2/data/penny_picks_latest.json` (mtime 2026-04-27)
- Generator workflow (disabled): `.github/workflows/penny-stock-picks.yml`
- Cron investigation: `reports/penny_picks_cron_investigation_2026-05-08.md`
- BROKIE charter: `.claude/skills/tv-paper-trade/SKILL.md` (Portfolio Definitions table)
