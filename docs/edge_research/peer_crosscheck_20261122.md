# Peer cross-check + portfolio-tracking inventory — 2026-11-22

Reconnaissance only. Read-only: nothing installed, no trades, no commits.
Repo: `/home/eaguiar2015/findtorontoevents_antigravity.ca`

---

## JOB A — Peer cross-check

### A.0 Which peer files actually exist

`find . -iname 'REALTIMECHALLENGE_*.MD'` (excluding `.git/`) returns exactly three paths:

| Path | Model token | Timestamp | Note |
|---|---|---|---|
| `REALTIMECHALLENGE_deepseek-flash_20261122T0355_EST.MD` | `deepseek-flash` | 2026-11-22T08:55Z / 03:55 EST | Signed "deepseek-flash (architect)", Round 141 entry by `subq-savant-1.4` |
| `REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD` | GitHub Copilot (DeepSeek V4.1 Flash), author `githubcopilot-mercury3AI` | 2026-11-22 03:59 EST / 08:59Z | |
| `reports/antigravity_review_Nov192026/REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD` | same | same | Byte-identical copy (`diff -q` exit 0) — counted once |
| `REALTIMECHALLENGE_buffy_20261122_0358_EST.MD` | `buffy` | 2026-11-22 03:58 EST / 08:58Z | **On `origin/main` only — not in this working tree** (checkout is behind). Read via `git show origin/main:...` (read-only) |

**The four peers named in the request have no files on disk.** No `REALTIMECHALLENGE_*` file
exists from ChatGPT-6 Luna, Claude haiku-5-5, Qwen3.6 Flash, or GLM 5.3 Flash. A repo-wide
search for those model names in `*.md` files found no challenge documents. They are therefore
**UNMEASURABLE — file absent**, and no claim of theirs can be assessed. (I did not invent rows
for them.)

So the cross-check covers **three** peer documents (deepseek-flash, GitHubCopilot, buffy).

---

### A.1 ACTUAL WORK vs PROPOSED, per peer

#### Peer 1 — `deepseek-flash` (`REALTIMECHALLENGE_deepseek-flash_20261122T0355_EST.MD`)

| Category | Content |
|---|---|
| **ACTUAL WORK (executed, evidence on disk)** | Ran `tools/realtime_challenge.py --open` 3× (logs `reports/realtime_challenge/round_open_*.log`, 09:02/09:08/09:14Z) and `--resolve` once (`round_resolve_20261122T0915Z.log` → "no open positions"). Reports live quotes from Binance + KuCoin. Result: **0 positions opened** (NO_TRADE). |
| **PROPOSED (not built)** | `.github/workflows/realtime-challenge-monitor.yml` ("NOT YET BUILT"), equity-hours automation ("NOT YET BUILT"), rule amendments A1/A2/A3, and a lookback/hold comparison matrix. |
| **States it did NOT trade** | Yes, explicitly: "Completed live rounds so far: 0", "No trades placed yet", `state.json` has `open: []`, `closed: []`. |

Its own §"Prototype defect" and "What was ACTUALLY set up" are honest about the split. This is
the **only** peer whose numbers I can independently check, because its scripts and logs are in
this working tree.

#### Peer 2 — `GitHubCopilot` (`REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD`)

| Category | Content |
|---|---|
| **ACTUAL WORK (executed)** | Ran `tools/realtime_challenge.py` against live crypto bars on a Sunday: 0 live positions opened. Ran a backtest over fetched live bars (1254 trades, stored in `reports/realtime_challenge/backtest_live_bars.json`). Ran `tools/live_daytrade_sim.py` (6619-trade ledger exists at `paper_trading/live_sim/`). |
| **PROPOSED (recommendations, not done)** | RT-2..RT-6 next rounds; ccxt sandbox execution; alpaca-py equity paper arm; scheduling `live_daytrade_sim.py` (note: it *has since been* scheduled — see `live-daytrade-sim.yml`); adding `vectorbt`, `nautilus_trader`, `pybroker`, etc. |
| **Declares libraries NOT installed** | Yes: `vectorbt`, `nautilus_trader`, `lumibot`/`pybroker`, `backtesting.py`, `freqtrade`, `quantstats`, `PyPortfolioOpt`, `skfolio`, `pandas-ta`, `alpaca-py`, `python-binance` listed as "Not installed (would need adding)". |
| **States it did NOT trade** | Yes: "Zero positions opened", "Zero capital is sanctioned. No forward observation exists." |

---

### A.2 NUMERIC CLAIMS + evidence cited

Each claim is a `(value, evidence in document)` pair. Verdicts are mine.

#### deepseek-flash

| # | Claim | Value | Evidence cited in doc | Verdict |
|---|---|---|---|---|
| 1 | Symbols scanned | 30 | `SYMBOLS` list in `tools/realtime_challenge.py:52` | **REPLICATED** (I read the list: exactly 30 USDT symbols) |
| 2 | Positions opened in Round 141 | 0 | `state.json` `open: []`, 3 open logs | **REPLICATED** (`state.json` confirms `open: []`, `closed: []`; log `round_resolve` says "no open positions") |
| 3 | Binance vs KuCoin spread | ≈3.8 bp (59745.16 vs 59742.90) | Tables in §"Round 141" | **UNMEASURABLE** (two live quotes at a past instant; not re-runnable now) |
| 4 | BTC nearest candidate | gap_to_break +112–119 bp, RSI 63.1–64.x | `round_open_*.log` | **REPLICATED in part**: `round_open_20261122T0902Z.log` shows BTCUSDT `RSI=64.2 gap_to_break=+112bp` |
| 5 | Backtest trade count (from GitHubCopilot, reused) | 1254 | `backtest_live_bars.json` | **REPLICATED** (file says `n_trades: 1254`) |

#### GitHubCopilot

Note the peer's own harness output is on disk (`backtest_live_bars.json`), so several claims
are checkable against a file the peer produced, but I did **not** re-run the harness.

| # | Claim | Value | Evidence cited in doc | Verdict |
|---|---|---|---|---|
| 1 | A1 Donchian trades | n=407, WR 29.7%, gross +0.38%, fees 81.40%, net −81.02% | `reports/realtime_challenge/backtest_live_bars.json` | **UNMEASURABLE** for WR/gross/fees (not in the json); json has `A1 n=407, mean_pct=-0.20021` → **n REPLICATED**, mean −20.0% per trade consistent with net −81.02%. WR/gross/fees **NOT_REPLICATED** (no stored evidence) |
| 2 | A2 RSI-dip trades | n=847, WR 33.2%, gross +27.85%, fees 169.40%, net −141.55% | same json | **n REPLICATED** (`A2 n=847, mean_pct=-0.16712`); WR/gross/fees **NOT_REPLICATED** |
| 3 | ALL arms | n=1254, WR 32.4%, gross +28.22%, fees 250.80%, net −222.58% | same json | **n + mean net REPLICATED** (`n_trades 1254`, `mean_net_pct -0.17786` = −0.178% ≈ −222.58%/1254). WR/gross/fees and the "ALL gross +28.22%" figure are **NOT_REPLICATED** (json has no gross) |
| 4 | Permutation p-value | p = 0.000 (20,000 sign-flips) | json `permutation_p: 0.0` | **REPLICATED as stored** (json says 0.0). Caveat: p is floored at 0 with 20k perms (min ≈ 5e-5); "0.000" is a rounding artifact, not exact zero |
| 5 | `live_daytrade_sim.py` cost audit | gross +$1095.96, fees $6751.82, net −$5655.86, 616% | printed verdict; ledger `paper_trading/live_sim/` | **PARTIALLY FALSE_AS_STATED**: today's `live_sim/state.json` sums to gross **+$1158.70**, fees **$6744.45**, net **−$5585.74** (6610 trades, not 6619). Numbers drifted since the doc was written; the *conclusion* (fees ≈ 6× gross) holds. The doc also says the sim "is not scheduled" — **FALSE_AS_STATED now**: `.github/workflows/live-daytrade-sim.yml` exists (cron `19,49 * * * *`) |
| 6 | S7_ORB_EQ | n=161, PF 1.18, t=+0.89, net +$61.84 | state.json | **REPLICATED** (`S7_ORB_EQ: n=161 gross=126.127 fees=64.283 net=61.843 pf=1.176 t=0.89`) |
| 7 | S1_DONCHIAN_5M | t=−12.89 | state.json | **REPLICATED** (`t=-12.89`) |
| 8 | Re-priced fee table (edge/cost at 4bp = 0.56; needs ≥12bp to clear Gate C) | values | derived arithmetic, no file | **UNMEASURABLE** (arithmetic on a gross figure I cannot reproduce; internally consistent but no stored artifact) |
| 9 | 5m rule loses with p=0.000 | p=0.000 | as #4 | **REPLICATED as stored**, same rounding caveat |

---

### A.3 Import test — the 8 requested modules (installed nothing)

`python3` import of each, on this machine:

| Module | Result | Version |
|---|---|---|
| `vectorbt` | **ABSENT** (`ModuleNotFoundError`) | — |
| `backtrader` | **ABSENT** | — |
| `ccxt` | **PRESENT** | 4.5.56 |
| `yfinance` | **PRESENT** | 1.3.0 |
| `alpaca` (`alpaca-py`) | **ABSENT** | — |
| `pywinauto` | **ABSENT** | — |
| `crewai` | **ABSENT** | — |
| `arch` (bonus, claimed by peer) | **PRESENT** | 9.0.0 |
| `statsmodels` (bonus) | **PRESENT** | 0.14.6 |

**Genuinely present: `ccxt`, `yfinance` (plus `arch`, `statsmodels`, `pandas`, `numpy`, `scipy`).**
Absent: `vectorbt`, `backtrader`, `alpaca-py`, `pywinauto`, `crewai`.

Peer claims about these:
- GitHubCopilot's "Installed and usable now" table (ccxt 4.5.56, arch 9.0.0, statsmodels 0.14.6,
  yfinance 1.3.0, pandas/numpy/scipy) → **TRUE**, every version matches.
- GitHubCopilot's "Not installed" list (vectorbt, alpaca-py, …) → **TRUE**.
- No peer claims `pywinauto`/`crewai` are installed. Nothing to contradict; both remain absent.

---

### A.4 Self-hosted-runner claim

No peer document proposes a GHA "live monitor" on a self-hosted runner. Grepping both peer
files for `self-hosted` returns only an unrelated mention of `paper_trading/backtest_runner.py`.
On disk, only two workflows optionally accept a self-hosted runner
(`alpha-engine-live.yml:46`, `audit-dashboard.yml:62`, both via `${{ inputs.runner || 'ubuntu-latest' }}`);
**nothing is configured to require one**, and every paper/time-based workflow inspected
(`live-daytrade-sim.yml`, `crypto-intraday-sim.yml`, `outcome-resolver.yml`) uses `ubuntu-latest` /
`vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest'`. A 24/7 self-hosted machine is not part of the
current design.

---

### A.5 Free-data-source claims vs. observed session evidence

Observed this session (given): **Stooq** returned a JS proof-of-work challenge, **Yahoo**
returned HTTP 429 on both mirrors, **Frankfurter/ECB** worked.

Peer claims touching these sources:

| Peer | Claim | Contradicted? |
|---|---|---|
| GitHubCopilot §4.2 | `yfinance 1.3.0` → "Equity/ETF/futures daily bars (already used throughout this project)" | **PARTIALLY CONTRADICTED**: the library imports, but Yahoo just returned HTTP 429 on both mirrors. Claiming it *works* for equity daily bars is not supported right now. |
| deepseek-flash §Instrument selection | equity path "`yfinance` → AlphaVantage → exchangerate-api failover" | **PARTIALLY CONTRADICTED**: yfinance leg is 429-blocked; the failover legs are the reason it might still work, but no evidence they do. |
| Neither peer claims Stooq or FRED. | — | n/a |

Neither peer rests its core result on Yahoo/Stooq, so no central claim collapses; but any
future equity arm that assumes yfinance alone will fail. Frankfurter/ECB is the one known-good
free source and is already used as an FX fallback in `alpha_engine/active_picks_sync.py:268`.

---

### A.6 One thing to adopt / one thing unsupportable, per peer

| Peer | Adopt | Wrong / unsupportable |
|---|---|---|
| deepseek-flash | **Amendments A1 + A2** (record signal frequency and a "closest non-signal candidate" row every round) — turns a zero round into evidence about scarcity, cheap and honest | The claim that BTC/KuCoin agreed to 3.8 bp and the exact RSI/gap digits are unreproducible from a past instant; treat as anecdote, not measurement |
| GitHubCopilot | **Cost-survival framing** (`edge/cost ≥ 3`, gate on net bps not win rate) and the discovery that `live_daytrade_sim.py` was orphaned (now fixed by `live-daytrade-sim.yml`) | The **gross +28.22% / fees 250.80%** decomposition: only n=1254 and mean net are stored in `backtest_live_bars.json`; gross/fees/WR have no artifact and the live-sim dollar figures have since drifted (−$5585.74 today vs −$5655.86 in doc) |
| buffy | **The cost-floor arithmetic** (§8: TP +0.60% needs a 0.84% move at 24bp round-trip, so the rule needs >64% accuracy to break even) and the discipline of publishing a losing round with its ledger — the only peer that has actually opened *and closed* a live paper round trip (verified in `data/realtime_challenge/sprint1.json`: 3 closed rows, `pnl_usd` −9.83/−9.44/−10.89 = −$30.16, matching the doc) | The "LIVE, positions open, first fills taken" header: `buffy.json` has `closed: []` and both positions are past their 09:58Z deadline with no re-run of `cycle` in this checkout; also `pnl_pct: null` in the sprint ledger, so the per-trade % returns in §8 are computed from prices, not stored |

---

## JOB B — Portfolio-tracking inventory

All mtimes are from `ls -la`; "last commit" from `git log -1 --format=%cs`.

### B.1 Inventory table

| Component | Entry point (file:line) | Real prices? (source / key) | TP/SL resolution | Ledger format | Ledger last modified | GHA-runnable? | Verdict |
|---|---|---|---|---|---|---|---|
| **`paper_trading/live_sim/`** (driven by `tools/live_daytrade_sim.py`) | `python3 tools/live_daytrade_sim.py` (`tools/live_daytrade_sim.py:308` `main()`); scheduled `.github/workflows/live-daytrade-sim.yml` | **Yes** — yfinance OHLCV (`tools/live_daytrade_sim.py:71`), cached to CSVs; no key | **Yes** — `tools/live_daytrade_sim.py:227-234`: `if s>0 and l[j] <= pos["stop"]: exit_px, reason = pos["stop"], "SL"` … `elif … h[j] >= pos["tgt"]: exit_px, reason = pos["tgt"], "TP"`; stop-first on ties | `paper_trading/live_sim/trades.jsonl` (9528 lines) → `id, strategy, symbol, side, entry, exit, entry_ts, exit_ts, units, bars, gross, fees, pnl, ret_pct_book, reason`; summary `state.json` | `trades.jsonl`/`state.json` **Nov 22 09:30** (untracked `??`, regenerated each run) | **Yes** (ubuntu-latest, cron :19,:49) | **LIVE** |
| **`audit_trail/universal_pick_resolver.py`** | `python3 audit_trail/universal_pick_resolver.py` (`:1320` `main()`, `:1847` entry); used by `audit-dashboard.yml`, `resolver-step5-6-backfill.yml`, `quant-auditor-fast-pr.yml` | **Yes** — Binance spot mirrors + Bybit + CoinGecko + CryptoCompare (`:402-473`), yfinance for non-crypto (`:522`); keys optional (env) | **Yes** — `_check_tp_sl_intrabar()` `:722`, `tp = pick.get("take_profit"…)` `:734`, `sl = …` `:735`, `sl_hit = bool(sl and low <= sl)` `:778`, `tp_hit = bool(tp and high >= tp)` `:779`, gap-fill + pessimistic tie handling `:780-804` | Reads `*_active_picks.json` across ~30 systems (`:140-174`); writes resolved rows into the dashboard payload / system closed picks | code Nov 19 23:58; `audit_trail/data/stock_prices.json` Nov 20 02:03; `dashboard_payload.json` Oct 23 | **Yes** (already in GHA) | **LIVE** |
| **`audit_trail/fetch_stock_prices.py`** | `python3 audit_trail/fetch_stock_prices.py` (`:59` `main()`) | **Yes** — yfinance (`:13`), FMP fallback needs `FMP_API_KEY` (`:31`, key from env only) | No (prices only) | `audit_trail/data/stock_prices.json` → `{prices:{SYM:px}, updated_at, count}` | `stock_prices.json` **Nov 20 02:03** | **Yes** (no desktop) | **WORKS_BUT_UNUSED** as a standalone (it is a price helper for the resolver) |
| **`alpha_engine/active_picks_sync.py`** | `python3 alpha_engine/active_picks_sync.py` (`:500` `main()`); invoked with `ACTIVE_PICKS_SYNC_APPLY=1` by `outcome-resolver.yml` (cron `47 */1 * * *`) and `audit-dashboard.yml`, `resolver-step7-apply.yml` | **Yes** — `alpha_engine.api_failover.fetch_price` (`:298`), yfinance (`:323`), FMP fallback via `fetch_stock_prices` (`:370`), Frankfurter for FX (`:268`); DB needs MySQL password (secret), FMP key env | **Yes** — `compute_verdict()` `:131`: `tp = …("take_profit")` `:143`, `sl = …("stop_loss")` `:144`, `if tp and live_price >= tp: tp_hit = True` `:159-160`, `elif sl and live_price <= sl: sl_hit = True` `:161-162` (inverted for SHORT `:164-167`), time-exit `:185` | `alpha_engine/data/closed_picks.json` via `append_to_closed_picks_json()` (`:444-495`) → `id, symbol, direction, asset_class, strategy, entry_price, exit_price, pnl_pct, status, exit_reason, closed_at, resolved_at, trust_score, elite_score, confidence`; also updates MySQL `at_raw_picks` | code Nov 19 23:58 | **Yes** (already in GHA) | **LIVE** |
| **`portfolio_tracker/`** | `python -m portfolio_tracker.tracker` (`:322` `main()`); `tracker.py` | **No** — it only *reads* closed picks from 8 systems and computes metrics; fetches no prices | No (consumes already-closed picks) | `portfolio_tracker/data/portfolio_metrics.json` (and `symbol_report_*.json`, `system_allocations.json`) | data files **Nov 19 23:58**, last commit 2026-11-19 | **Yes** (pure python, no desktop) | **WORKS_BUT_UNUSED** (analytics layer, no price/TP-SL of its own; ledger stale) |
| **`verified_strategies/paper_pilot/`** | per-strategy scripts, e.g. `python3 verified_strategies/paper_pilot/crypto_intraday_sim.py --one-shot` (`crypto_intraday_sim.py:1-38`); summary `pilot_forward_summary.py`; crypto sim scheduled by `crypto-intraday-sim.yml` | **Yes** for the crypto sim (real 4h bars via `tools.crypto_bars`); others vary (ETF/equity via yfinance) | **Partial** — rows carry `take_profit`/`stop_loss`, but the crypto sim log shows `stop_loss: null` and `take_profit: null` on some OPEN rows; resolution is deferred to `tools/pilot_forward_bridge.py` | `*_paper_log.jsonl` → `date, event(OPEN/CLOSE/SIGNAL), slot, strategy, hypothesis_id, asset_class, symbol, direction, entry_price, entry_ts, take_profit, stop_loss, reason` + per-strategy `*_state.json` | logs **Nov 19-20** (faber 02:02, rest 23:58); crypto sim log has **0 CLOSE rows** | **Yes** (crypto sim already scheduled :07,:37) | **WORKS_BUT_UNUSED** (harness sound, but zero closed trades and logs stale since Nov 20) |
| **`live_monitor/position_monitor.py`** | `python live_monitor/position_monitor.py` (`position_monitor.py:1-10`) | **Yes** — Binance ticker (`.us` + global + `api4` mirror) `:29-31`; no key | Monitors distance to hardcoded TP/SL/liq; does NOT close: positions hardcoded `:53-107` (AVAX, LINK, NEAR, ADA, BNB, BTC, 20× leverage) | `live_monitor/data/position_state.json` → per-position `current_price, pnl_pct, liq_price, dist_to_tp, dist_to_sl, dist_to_liq, alert_level` | `position_state.json` **Nov 19 23:58**; last_updated field **2026-03-27** | **Yes** (no desktop, but Discord webhook optional) | **VESTIGIAL** (hardcoded real-money BTCC positions from March, stale 8 months, references no workflow) |
| **`paper_trading/data/closed_picks.json`** | produced by `paper_trading` systems (`python -m paper_trading` → `scanner.main()`, `paper_trading/__main__.py:2`) | **Yes** via `multi_source.py` (Binance→CryptoCompare→CoinGecko; keys optional env `CRYPTOCOMPARE_API_KEY`/`COINGECKO_API_KEY`) | Recorded outcomes only (`status: TP_HIT/SL_HIT`) | JSON list → the 23 fields you listed | **Nov 19 23:58**; all `exit_date` are **2026-03-05/06** | **Yes** | **VESTIGIAL** (34 picks, all closed in March, never updated) |

### B.2 Notes on what is genuinely functional vs vestigial

- **Genuinely functional & moving data now:** `paper_trading/live_sim/` (LIVE, ticks every 30 min),
  `audit_trail/universal_pick_resolver.py`, `alpha_engine/active_picks_sync.py` (both in GHA).
- **Sound code, stale ledger:** `portfolio_tracker/` (analytics only), `verified_strategies/paper_pilot/`
  (no closed trades yet).
- **Vestigial:** `live_monitor/` (hardcoded March positions, no workflow), `paper_trading/data/closed_picks.json`
  (March-only), empty `paper_trading/data/paper.db` (0 bytes, Jun 3).

### B.3 Closest existing component + what is missing

**Closest: `tools/live_daytake_sim.py` → `paper_trading/live_sim/` (scheduled by
`.github/workflows/live-daytrade-sim.yml`).** It is the only component here that already
(a) fetches real prices, (b) pre-registers entries, (c) resolves TP/SL pessimistically, and
(d) writes a real ledger on a schedule every 30 minutes.

**What is missing to make it a proper daily mark-to-market paper portfolio with TP/SL:**

1. **Open-position mark-to-market.** It records only CLOSED trades (`trades.jsonl` rows all have
   `exit`/`exit_ts`). There is no "open positions marked at the current price" view — the thing
   a portfolio tracker needs. The closest is `state.json`, which only holds closed summary stats.
2. **Real portfolio bookkeeping.** `BOOK = 1000.0`, `RISK_PCT = 0.01` (`tools/live_daytrade_sim.py:50-51`)
   is a fixed notional per trade; there is no equity curve, cash balance, or position-size compounding
   that tracks a portfolio over time (that lives only as `max_dd_usd` per strategy).
3. **A daily cadence and a persisted, committed ledger.** It runs intraday on yfinance but
   `paper_trading/live_sim/` is **untracked** (`git status: ?? paper_trading/live_sim/`) and
   regenerated each run; there is no dated snapshot per day to compare.
4. **A portfolio-level TP/SL view across systems.** It tracks 7 of its own strategies; it does not
   ingest the ~30 systems' active picks that `universal_pick_resolver.py` already knows about.

**Alternative if you want TP/SL against a real multi-system portfolio instead of one simulator:**
`audit_trail/universal_pick_resolver.py` (`_check_tp_sl_intrabar`, `:722`) already resolves TP/SL
intrabar across all systems' active picks with real prices and is GHA-scheduled. What it lacks is
an *open-position mark-to-market snapshot* and a simple equity-curve ledger per portfolio type
(it feeds a dashboard payload, not a portfolio P&L series).

So: **for "one working paper portfolio that marks to market daily and records TP/SL", start from
`tools/live_daytrade_sim.py` + `paper_trading/live_sim/`; add an open-positions mark-to-market
pass, an equity/cash model, and a daily committed snapshot.** If you instead want it across all
real signal sources, extend `audit_trail/universal_pick_resolver.py` with an open-position
mark-to-market ledger.

---

## Summary

- **Peer files on disk:** 3 unique (deepseek-flash, GitHubCopilot, buffy); the 4 named peers have no file → UNMEASURABLE.
- **Installed of the 8 tested:** ccxt, yfinance. Absent: vectorbt, backtrader, alpaca-py, pywinauto, crewai.
- **Disk-contradicted peer claims:** GitHubCopilot's "live_daytrade_sim.py is not scheduled" (now scheduled), and its live-sim dollar figures (drifted); yfinance "works for equity daily bars" (Yahoo 429 this session).
- **Portfolio tracking:** LIVE = `live_sim`, `universal_pick_resolver`, `active_picks_sync`; WORKS_BUT_UNUSED = `portfolio_tracker`, `paper_pilot`; VESTIGIAL = `live_monitor`, `closed_picks.json`.
