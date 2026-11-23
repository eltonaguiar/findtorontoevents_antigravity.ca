# The `/investments/` hub — what is worth porting into `/audit`, `/audit2`, `/audit3`

**Audited:** 2026-11-23 · **Source read:** `investments/index.html` (562 lines) and
`investments/all-dashboards.html` — the "Other Stuff → investment tools" surface linked from the main
`index.html` ("find out if someone WITHOUT a supercomputer can beat the stock market").

## 1. What is actually in the hub

| section | contents |
|---|---|
| Portfolios | Stock Portfolio Analysis, Mutual Fund Analysis (`portfolio1` + report + stats), Daily Stock Picks (CAN SLIM / Technical Momentum / ML Ensemble / Alpha Predator, **SHA-256 pre-commitment**), Forex (15 pairs, 8 strategies), Crypto (15 pairs, 10 strategies, 0.1–0.5% fee model) |
| Multi-Asset ML | Trading Systems Hub (13 systems, "single source of truth"), Cross-System Monitor, Mercury 2 (27.3% WR, −30.49% P/L, n=44), Claws of Doom (2 trades, +12.80%), Claude Gainer Tracker (XGB+LightGBM+RF, "reverse-engineers daily top gainer patterns"), Alpha Engine (100 strategies, 28.6% forward WR), KIMI Rise of the Claw (81 algos, elimination engine), Crypto ML Edge (LightGBM, DSR-gated) |
| Goldmines | GOLDMINE_WS — cross-system proof tracker with "dead data alerts" and pro-firm benchmarks |
| Graveyard | Battleground Arena (systems A and C at **0% WR**), Master Dashboard v1 (superseded), ML Picks Dashboard (backtest-only), Unified Forward Test Dashboard (superseded) |
| Feature strip | Questrade tariff ($0 commissions, **1.75% FX**, **$9.95 MF trades**), VIX volatility filter, 7 alt-data families, what-if simulator, daily auto-refresh, "Optimal Finder" (grid search over thousands of permutations) |

## 2. Live-link check (probed today, HTTP status)

| link | status |
|---|---|
| `/investments/`, `/findcryptopairs/winners.html`, `/investments/goldmines/`, `/investments/master_dashboard.html`, `/findmutualfunds/portfolio1/stats.html` | **200** |
| `/findstocks/portfolio2/learning-lab.html` | **404** |
| `/findstocks/portfolio2/daytrader-sim.html` | **404** |

Also: `/investments/goldmines/`, `/investments/master_dashboard.html`, `/findmutualfunds/portfolio1/stats.html`
and every `/findstocks/portfolio2/*` page have **no source file in this repo** — they are deployed from
somewhere else, so a repo-side link fix cannot be verified against them.

## 3. Worth porting into the audit surfaces

1. **The Graveyard, as a first-class strip.** `/audit` reports kills as rows in tables; the hub gives
   dead systems a *named, permanent, visually distinct* section with the reason ("0% WR", "superseded",
   "backtest only"). `/audit2` should render `hypothesis_registry.json` entries with status
   REJECTED/REFUTED the same way. Cost: one panel reading a file that already exists. This is the
   single best idea in the hub and the audit does not have it.
2. **The SHA-256 pre-commitment protocol.** Daily Stock Picks publishes a hash of the picks before the
   session. `/audit`'s pre-registration is real (M-107) but invisible to a reader — the registry commit
   is the timestamp, not something you can check from the page. Publish the `hypothesis_registry.json`
   hash (and the day's picks-file hash) on `/audit2` beside the verdicts. That converts "trust our
   git history" into "verify it yourself", which is the hub feature with the highest audit value.
3. **`/findcryptopairs/winners.html` (live gainers).** This is the exact surface the top-gainer work
   needs a public face for: `/audit` shows picks, never *what actually gained*. A "gainer autopsy" card
   linking the live winners list to H-237 (daily, refuted), H-238 (weekly, refuted) and the registered
   H-239/H-240 (monthly, untested) would answer the question the hub raises in one screen — including
   the honest part, that the winners are usually $200–240M-cap names the panel never contained.
4. **Dead-data alerts.** GOLDMINE_WS surfaces stale feeds; `tools/db_freshness_check.py` already
   computes the same thing server-side for the audit. Expose its verdict as a banner on `/audit`
   instead of only as a CI gate.
5. **The VIX filter, as a pre-registered overlay.** Nothing in the ranked 40-cell sweep conditions on
   volatility regime, and there is already an `etf_vix_gate_log.jsonl` in the repo. That is a legitimate
   new hypothesis (register it, don't tune it), not a UI port.
6. **The 7 alt-data families** (Glassdoor, BDI, GPR, dark-pool flow, ESG, patents, congressional trades).
   Congressional-trade and dark-pool data are the two with a plausible causal prior; the rest are feature
   shopping. Only worth building behind a pre-registration.

## 4. Not worth porting — and why

| hub item | why not |
|---|---|
| Mercury 2 "27% WR", Claws of Doom "2/2 wins +12.80%", Alpha Engine "28.6% forward WR", 13 systems' self-reported WRs | No CI, no pre-registration, n between 2 and 44. Putting these next to the gated cells on `/audit` would launder unproven numbers into the audit's credibility. The hub can keep them; the audit should not import them. |
| "Optimal Finder" — grid search over thousands of permutations | This is the multiplicity machine the programme already measured: PBO(CSCV) 0.345, DSR bar 0.95, **0 of 40 cells cleared every gate**. Porting it would produce more of what it produced. |
| "7 alt-data families" as-is | Feature shopping without priors. Two families, pre-registered, would be worth more than seven displayed. |
| Trading Systems Hub / Cross-System Monitor as an *audit* page | `/audit2` pods already do this, with gating the hub lacks. Redundant, and the hub's version reports P/L without a benchmark. |

## 5. Two concrete defects found while auditing

1. **Fee inconsistency.** The hub's feature strip says Questrade charges **1.75%** on FX conversion for
   US stocks; the verified tariff recorded in `tools/equity_cost_hml.py` (`QUESTRADE_SOURCE`,
   verified 2026-11-23) is **1.5%**. One of the two is wrong, and the cost measurement depends on which.
   The $9.95 MF trade fee matches the ranking document's fee analysis, so the MF line is fine.
2. **Two advertised tools are 404** (`learning-lab.html`, `daytrader-sim.html`), and the main page's
   "Updated daily • Feb 4, 2026" line is a stale date on a page that claims daily refresh.

## 6. Recommendation, ranked

1. Graveyard panel on `/audit2` from the hypothesis registry (cheap, high credibility).
2. Publish registry + picks-file SHA-256 on `/audit2` (cheap, converts pre-registration into something
   a reader can verify).
3. Gainer-autopsy card linking the live winners page to H-237/238/239/240 (answers the question the
   hub poses).
4. Fix the 1.75% vs 1.5% FX figure and the two 404 links.
5. Register the VIX-regime overlay as a hypothesis before building it.

Nothing here changes any verdict: **0 of 10 classes are investable** before and after this audit.
