# 2026-10-22 — Fix "Access denied" + Profit-and-Loss Bug Status + Turnaround Plan

This document does three things: (a) fixes the broken mutual-fund / forex / stock **database (DB)**
**Application Programming Interfaces (APIs)** that returned **"Access denied"**, (b) confirms a
remaining profit-and-loss (P/L) compounding bug, and (c) lays out the plan to actually beat an
index fund. Every acronym is expanded on first use. Each section is written twice — **ELI5**
(Explain Like I'm 5: plain language) and **Technical** (for engineers).

**Acronyms used throughout (expanded):**
- **DB** = Database (a structured store of rows, like a giant spreadsheet).
- **API** = Application Programming Interface (a program that lets one piece of software ask another for data over the internet).
- **P/L** = Profit and Loss (money made or lost).
- **PHP** = "PHP: Hypertext Preprocessor," the scripting language the website's APIs are written in.
- **MySQL** = "My Structured Query Language," the specific DB software in use.
- **FTP** = File Transfer Protocol (the mechanism used to upload website files to the live server).
- **Credentials** = the username + password + host (address) that prove the API is allowed to read the DB.
- **PF** = Profit Factor (total money won ÷ total money lost; above 1.0 means net profitable).
- **WR** = Win Rate (the percentage of trades that ended with a profit).
- **MDD** = Maximum Drawdown (the largest peak-to-trough drop in value before recovering).
- **DSR** = Deflated Sharpe Ratio (a 0-to-1 score that discounts a strategy's return for how many ideas were tried, so "best of 1,000 lottery tickets" doesn't look like skill).
- **CI** = Confidence Interval (a range showing where the true result likely falls; the low end is what to trust).
- **Sharpe ratio** = return earned per unit of volatility (bumpiness); higher is smoother.
- **Index fund / buy-and-hold** = simply holding a market basket (like an S&P 500 fund) instead of trading.

---

## Part 1 — The "Access denied" bug (mutual funds, forex, stocks)

### ELI5
Every page on the site that shows fund, currency, or stock data talks to a private spreadsheet
in the cloud (the database). To open that spreadsheet, a program needs a key (username +
password). Somebody changed the lock on the spreadsheet in May 2026, but the little programs
on the website were still carrying the OLD key. So every time a visitor loaded those pages,
the cloud said "Access denied" and the page showed an error. Worse, the error message was
showing the house address and the owner's name (the DB username and the server's internet
address) to anyone who opened the error — like taping your house keys to your front door.

**The fix, simply:**
1. Give the programs the NEW key — but store it in a secret note (a `.env` file) that is never
   uploaded to the public code repository, so the key stays private.
2. Stop taping the keys to the door — change the error so it shows a friendly "Database
   connection failed" and writes the real reason only to a private server log.

### Technical
**Root cause.** The DB password for `ejaguiar1_stocks` on host `mysql.50webs.com` was rotated
on **2026-05-12** (it is now 13 characters, e.g. `st…0`). The website's PHP config files still
hardcoded the OLD password, the literal string `'stocks'` (6 characters). `mysqli` (the PHP
MySQL client) therefore failed authentication, and `db_connect.php` echoed
`$conn->connect_error` — which contains the username and the connecting host's IP address —
straight into the HTTP (HyperText Transfer Protocol) response. That is both the outage and
the information leak.

**What was changed (in the repository, main working tree):**
1. **Password source switched from hardcode to a secret `.env` file.** In
   `findforex2/api/db_config.php`, `findforex2/portfolio/api/db_config.php`, and
   `findstocks/kimis_claw/api/db_config.php`, the line `$password = 'stocks';` was replaced
   with a PHP 5.2-compatible helper `_db_env_pw()` that:
   - first tries the environment variable `MYSQL_PASSWORD` (`getenv`), then
   - reads the sibling `.env` file line-by-line (splitting on `chr(10)`, stripping `chr(13)`,
     to avoid fragile escape sequences), then
   - falls back to `'stocks'` only if neither is present.
   Line-splitting uses `chr(10)`/`chr(13)` deliberately — an earlier version used a
   single-quoted `preg_split('/\r?\n/')` which, when generated, embedded a literal newline
   inside the string and would have been a PHP parse error. The `chr()` form is immune.
2. **Real credentials written to gitignored `.env` files** (`.gitignore` line 71–72 ignore
   `.env` and `*.env`, verified with `git check-ignore`) at:
   - `findforex2/api/.env`
   - `findforex2/portfolio/api/.env`
   - `findstocks/kimis_claw/api/.env`
   Each contains `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD` (the current 13-char value,
   pulled programmatically from `tools/db_env.get_stocks_creds()` and **never printed**),
   and `MYSQL_DATABASE`. Because `.env` is gitignored, the secret deploys to the server but
   is **never committed to the public repository**.
3. **Credential leak closed.** In `db_connect.php` for `findforex2/portfolio/api`,
   `favcreators/docs/api`, `findstocks/kimis_claw/api`, and `live-monitor/api`, the
   `echo … $conn->connect_error` was replaced with `error_log('DB connect failed: ' .
   $conn->connect_error)` (server-side log only) plus a generic
   `'Database connection failed'` JSON message. `findforex2/api/db_connect.php` was already
   generic and needed no change. Verified: **zero** `db_connect.php` files now place
   `connect_error` in client output.

**Deployment (required — these are server-side files):** upload the changed `db_config.php`,
`db_connect.php`, and the three `.env` files to the live server via the site's FTP deploy
flow (`tools/deploy_audit_files.py` or the normal host upload). PHP (the language) cannot be
lint-checked locally here (no `php` binary installed); the code was written to PHP 5.2
standards (plain `function`, `array()`, no closures, no short array syntax) and manually
byte-verified (`cat -A`) to contain no stray control characters inside string literals.

**Scope note.** The `findmutualfunds2/portfolio2/api/` directory in the repository contains
only `debug_navs.php`, `fix_dates.php`, and `test_bt.php` — the connection file
(`db_connect.php`) that `debug_navs.php` requires is **not committed** (it lives only on the
server). So the mutual-fund API's connection must be updated server-side directly, or its
`db_connect.php`/`db_config.php` must be added to the repository using the same pattern as
above. This is the one piece that cannot be fixed from the repository alone.

---

## Part 2 — The profit-and-loss (P/L) compounding bug: STILL PRESENT

### ELI5
The dashboard tries to show "how much money did all these trades make together?" The right
way is to assume you only risk a small slice of your money on each trade at a time. The
current way instead pretends you used **all** your money on every single trade, one after
another, even when many trades were open at the same time. If you had ten trades open at once,
that's impossible — you can't put 100% of your money into ten things simultaneously. So the
big number on the page is too rosy. (An earlier, related bug — cutting every trade's result off
at ±2% — **was** already fixed on 2026-06-04 to ±10%. That specific clipping is gone. But the
"pretend full money on every trade" problem underneath is **not** fixed.)

### Technical
`audit_trail/dashboard_generator.py`:
- Line ~14864 still computes the headline `total_pnl_pct_compounded_ew` by calling
  `_compound_equal_weight_capped_sequence(resolved_closed, _MAX_PNL_COMPOUND)` with
  `_MAX_PNL_COMPOUND = 10` (the 2026-06-04 change; the clamp is now ±10%, so the old ±2%
  asymmetry that trimmed +3% take-profits but left −2% stop-losses whole is gone).
- `_compound_equal_weight_capped_sequence` (line ~4965) multiplies `prod *= 1 + capped/100`
  **sequentially in timestamp order**. This implicitly assumes each trade commands 100% of
  capital. When picks **overlap in time**, the true portfolio return is far lower because
  capital is split across concurrent positions. The function's own docstring admits it:
  "fictitious sequential reinvestment of 1 unit on every trade." It is DEPRECATED and
  hard-capped at 9999%, but still wired to the headline.
- The intended replacement `_compound_rolling_window` (line ~5001) bounds the metric to the
  last 100 trades (so it stops ballooning at large N) but makes the **same** overlap-blind
  sequential-compounding assumption.
- A concurrency-aware compounding routine (dividing each trade's return by the number of
  simultaneously-open positions, or an equal-notional model capped by max concurrent
  exposure) does **not** exist in the file. **This is the fix that is still needed.** The
  same conclusion is recorded in the cross-agent spec
  `docs/superpowers/specs/2026-10-22-measurement-fix-design.md`, which lists "overlap
  compounding" and "no crypto costs" as two of Grok's bug claims that remain **verified and
  unfixed**.

---

## Part 3 — Turnaround Plan: how to actually beat an index fund

### ELI5 (the honest summary)
Right now none of the ~59 automated strategies beats simply holding a market index. Crypto
loses about half a percent per trade before fees; stocks and ETFs (Exchange-Traded Funds —
baskets you can buy like a stock) make a tiny bit, but on too few trades to tell skill from
luck. The small drawdowns aren't because the systems are safe — they're because they trade
tiny amounts. The winning move is to stop trying to be clever with minute-by-minute trades
and instead run a slow, boring, well-known portfolio (the "core") plus a small set of
promising experiments (the "satellite") that only get real money after they prove themselves
on paper first.

**The plan in one breath:**
1. **Core (~75%)** — a monthly, diversified ETF rotation based on momentum (buy what's been
   going up over ~6 months, drop what's falling). This mirrors what already exists
   (tactical-rotation sleeve, Sharpe 0.88 vs SPY 0.74) and what the mutual-fund ranker and
   fund-holdings tool point to.
2. **Satellite (~25%)** — the only two candidates with real structure (the CRYPTO SHORT at
   1-hour RSI 30–50, and the stock `rs-breakout-scout`), kept on **paper money** until each
   accumulates 100+ forward trades.
3. **Machine** — one shared rules file (`gates.yaml`), a trial ledger that logs every idea
   tried (so the lucky-guess discount DSR can work), and honest costs + position sizing
   everywhere.

### Technical — measured results and status
**Core backtest** (`tools/core_satellite_backtest.py`, monthly data from 2010, next-month
entry to avoid look-ahead, 10 basis-point round-trip cost on turnover, compounded):
- **Dual-momentum rotation (top 3 of SPY/QQQ/IWM/EFA/EEM/TLT/GLD/DBC, negative-momentum → AGG):**
  CAGR (Compound Annual Growth Rate) 10.40%, Sharpe 0.90, MDD −19.2%, Calmar 0.54,
  beta to SPY 0.54, alpha +2.62%/yr. **Does NOT beat SPY buy-and-hold on return** (SPY:
  CAGR 14.43%, Sharpe 1.02) — it is *calmer* (lower drawdown, lower beta), not richer.
  This independently reproduces Grok's finding (their candidate mix: 6.3%/yr vs SPY 8.6%/yr,
  but calmer). At 2× cost the rotation's CAGR falls to 9.60%.
- **Known bug in this run:** the SPY 200-day trend-filter row returned a nonsensical value
  (infinite CAGR, worst month +7258%) — a data/edge-case bug in `run_spy_trend` to be fixed
  before that row is trusted. The dual-momentum and buy-and-hold rows are sound.

**Cross-agent status (unchanged, honest):** 0 of 9 asset classes are MONEY-READY. The 59-strategy
audit yields 3 CANDIDATE and 56 FAIL. The best real result (rs-breakout-scout, PF 1.28 on an
8.8-year re-backtest) trails SPY. Mutual-fund / futures / options classes are empty. Data-quality
fixes (batch-close timestamps, 0.00% flat exits, Deflated-Sharpe-greater-than-1, look-ahead
rows) are landing in pull request #756 and follow-ups.

**Deliverables produced this session:**
- `tools/core_satellite_backtest.py` — the honest core-vs-SPY backtest.
- `alpha_engine/fund_holdings_deriver.py` + `audit_dashboard/data/fund_holdings_consensus.json`
  — derives institutionally-owned large-cap stocks from top holdings of the top-rated funds.
- `tools/critic_daily_equity_metrics.py` + the ten-point checklist on the Buffy audit page.
- The DB "Access denied" + credential-leak fix (Part 1).
- Pull request #756 — the Deflated-Sharpe and resolver quick-fixes (do not merge yet).

---

## What "do better" honestly means
For a public-facing product, the defensible claim is a disciplined, low-cost, transparent
ETF-rotation core (which can reasonably match or modestly beat a passive index on a
risk-adjusted basis and demonstrably controls drawdown) — **not** a high-frequency
alpha machine. The satellites are small optionality that only graduate on sealed-forward
proof. Everything on the current `/audit` page that looks better than this was inflated by
the bugs above; those fixes are landing.

*Not financial advice. All figures are research measurements, net of assumed trading costs,
using next-bar / next-month entry.*
