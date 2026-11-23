# Investment Hub vs /audit — what's worth building on, what to retire

**Date:** 2026-11-23 · **Scope:** the "Other Stuff → Investment Hub" submenu on the main page
(`TORONTOEVENTS_ANTIGRAVITY/index.html`, lines ~999-1055 and ~5991-6073) and the pages it points to.

**Verdict in one line:** the hub contains one page that makes *deployment* claims, no measurement
apparatus anywhere in it, four dead links, three empty catalogue sections — and one genuinely valuable
idea (strategy-family attribution) that `/audit` is currently missing.

> ### ⚠️ CORRECTION (2026-11-23, later same day)
> The "four dead links" framing below is **wrong about production and misleading**. All four paths are
> **live and served correctly** (HTTP 200). They are missing from the *repository*, not from the site.
> Worse, the goldmines system they point to is **live in HTML but dead in data**: its API returns
> `{"ok":false,"error":"Database connection failed"}` and its sister API fails with
> `unexpected T_FUNCTION` because the host runs **PHP 5.2.17**.
>
> See `reports/INVESTMENT_HUB_GOLDMINES_EXISTENCE_2026-11-23.md` for the full existence matrix and root
> cause. The fix-list item "Remove, or ship the files" was the **wrong action** — nothing should be
> removed; the files exist and need fixing. Everything else in this document stands.

---

## 1. What the hub actually is

The submenu points at `/investments/` and four siblings. Only **two files exist in the repo**:

| Path | Size | Status |
|---|---|---|
| `investments/index.html` | 35 KB | OK — "Investment Tools", 25+ outbound links |
| `investments/all-dashboards.html` | 76 KB | OK — 12-section catalogue of dashboards |

**Four links are dead in-repo** — ~~because `investments/goldmines/` does not exist at all~~ — see
CORRECTION above: they are **live on production**, merely unversioned.

| Link | In repo? |
|---|---|
| `/investments/goldmines/antigravity/` | **MISSING** |
| `/investments/goldmines/kimi/kimi-goldmine-client.html` | **MISSING** |
| `/investments/goldmines/windsurf/` | **MISSING** |
| `/investments/master_dashboard.html` | **MISSING** |

They may exist on the FTP host, but nothing in the repo can produce them — so a fresh clone deploys
four 404s.

## 2. Three of the twelve catalogue sections are empty or mislabeled

From `investments/all-dashboards.html`:

| Section | Links found | Problem |
|---|---|---|
| 🗄️ SQLite Databases | **0** | Promises a database catalogue, contains nothing |
| 📁 Key Backtest & Live Data Files (JSON/CSV) | **0** | Promises a data-file catalogue, contains nothing |
| 🧠 Trained ML Model Files | 3 | The 3 "links" are just nav footer links (`/`, `/investments/`, `/updates/`) — **no models listed** |
| 💀 Meme Coin & Penny Stock | 2 | Both links are the **same** URL, `/STOCKS/algorithm-competition.html` |

An "All Dashboards & Data" page whose data and model sections are empty is the most misleading thing on
the hub, because its title promises exactly the inventory that is missing.

## 3. The page that matters: `live-monitor/research/live-vs-research.html`

This is the only hub page that makes forward-looking **capital** claims, and it is the reason this
assessment exists.

**It is entirely static.** Measured: `fetch(` = 0, `.json` = 0, `.csv` = 0. No data binding at all —
the numbers are typed into the HTML. Its only date token is the word "Generated".

### Its claims, verbatim

> **"The 5 Forward-Test Validated Strategies (Deploy These)"** — "Only these 5 strategies survived the
> Nov 2025 – Feb 2026 forward test, including the crypto crash."

| # | Strategy | Class | Score | Priority |
|---|---|---|---|---|
| 1 | Funding Rate Arbitrage | Crypto | 88/100 (A) | P0 |
| 2 | Pairs Trading | Multi-asset | 79/100 (B+) | P0 |
| 3 | Betting Against Beta (BAB) | Stocks | 77/100 (**A-**) | P0 |
| 4 | Quality Minus Junk (QMJ) | Stocks | 75/100 (B+) | P1 |
| 5 | Flash Crash Reversal | Crypto | 71/100 (B) | P1 |

It also asserts, in bold:

> **"None of the 5 forward-test validated strategies are currently deployed in live trading. Meanwhile,
> strategies that FAILED forward testing (momentum, breakout, Ichimoku) are generating 80%+ of our
> signals. This is the #1 reason for poor performance."**

### Four problems with that, all checkable

1. **The scores are unattributed ordinals.** No `n`, no confidence interval, no significance test, no
   cost basis. Grep of the page for `sample size | p-value | confidence | significan | wilson |
   bootstrap` returns **zero matches** — the only statistic word present is "Sharpe" (6×). "88/100 (A)"
   is not a measurement.
2. **The letter grades are non-monotonic.** 79/100 → **B+** but 77/100 → **A-**. A lower score receives
   a better grade, so the grade scale cannot be a function of the score.
3. **"+475% expectancy improvement"** is a relative change with no base. 475% of what, from what
   denominator, over what n?
4. **"Quality Minus Junk (QMJ)" is contradicted by measurement taken today.** My HML value test —
   the same quality/value factor family — returned **KILL**: gross +0.11%/yr, **net +0.02%/yr** against
   a **4.32%** hurdle, SE 6.65% (`reports/hml_result.json`). A QMJ-style factor scoring "B+ / 75" on a
   page titled "Deploy These" is the exact failure mode `/audit` exists to prevent.

**Why it's not buildable-upon as-is:** a "Proven / Deploy These" page with no statistical apparatus,
that cannot update, contradicts the estate's standing finding of **0 proven edges**. Building on it
would import its errors. It should be **retired or rebuilt from `/audit` data**, not extended.

## 4. The claim /audit CAN test — and the result

The 80% claim is testable against `audit_dashboard/data/dashboard_data.json` → `systems` (133 systems,
43 with resolved picks, **8,757 resolved signals**):

| Name matches | Systems | Resolved | Share | WR | PF |
|---|---|---|---|---|---|
| `momentum` \| `breakout` | 2 | 53 | **0.6%** | 5.7% | 0.163 |
| `ichimoku` | **0** | 0 | **0.0%** | — | — |
| everything else | 41 | 8,704 | 99.4% | 40.6% | 0.869 |

**Measured: 0.6%, not 80%+.** And "Ichimoku" matches **zero** systems by name.

### But the honest reading is narrower than "the hub is wrong"

System names are **source/scanner** names (`aggregated_picks`, `claude_gainer_st`, …), not strategy
families. So there are two possibilities, and I can't distinguish them from the current ledger:

- **Reading A:** the claim is simply false — momentum/breakout/Ichimoku are a negligible share.
- **Reading B:** the claim is about *internal* strategy families that never surface as a system name.
  If so, the attribution is **invisible in the ledger**, which means nobody can verify or refute the
  hub's central diagnosis — including the hub.

**Either way the conclusion is the same:** the ledger cannot answer "which strategy family produced the
losing signals," and that is the single most valuable thing to fix.

Partial confirmation that family data *can* exist: `alpha_engine/data/active_picks.json` records carry a
`strategy` field with 11 distinct values (`regime_crash`, `cta_commodity_momentum_term`,
`futures_bb_mean_reversion`, …). So attribution exists at **pick** level but is **lost at the
resolved-history/summary** level — exactly where the question is asked.

## 5. What is worth building on, ranked

### #1 — Strategy-family attribution in the ledger → `/audit` (HIGHEST VALUE)

The hub asks the right question. `/audit` has the data but not the field. Concretely:

- Carry `strategy` / a coarse `strategy_family` through `universal_pick_resolver.py` into the aggregated
  `systems` payload, so resolved history is groupable by family.
- Only then can the 80% claim (and its inverse — "are the 5 'validated' strategies actually sourceable?")
  be answered with an n attached.
- This is the one item that converts a hub claim into an `/audit` measurement rather than an opinion.

### #2 — `live-monitor/goldmine-alerts.html` → dashboard-freshness gate

Unlike the static page, this one is genuinely live: **10 live hooks**, and it `HEAD`-checks each
dashboard URL while reading `alpha_engine/data/active_picks.json`, `KIMI_RISEOFTHECLAW/data/
live_signals_now.json`, and `scan_runs.json` from raw.githubusercontent.

- The repo already has a *server-side* freshness guardian (`tools/db_freshness_check.py` +
  `db-freshness-guardian.yml`). This page is the **front-end analogue** and there is no equivalent for
  "is the dashboard itself stale / 404 / not updating".
- Worth porting as either a `/audit` panel or a CI job that fails when a published dashboard stops
  advancing. It would also have caught the four dead hub links above automatically.

### #3 — `live-monitor/research/` and `findcryptopairs/audit-trail.html` → compare, don't duplicate

`findcryptopairs/audit-trail.html` (13 live hooks) is a per-pick audit trail for crypto;
`live-monitor/research/index.html` (50 KB) is its research index. `/audit/pick_funnel.html` already
covers much of this. **Action: diff the two, keep the better one, and retire the duplicate** — do not
build a third.

### #4 — Reuse the *layout*, replace the *numbers*

"The Brutal Reality: Backtest vs Live — Side-by-Side" and the TIER S / TIER F framing are good
information architecture for exactly the question `/audit` exists to answer. Reuse the page structure;
populate it from `backtest_vs_forward` and `fwd_vs_bt_divergence` in the dashboard payload, with n and
CIs attached. Never re-hand-type the figures.

### #5 — Treat the 5 strategies as pre-registrable hypotheses, not deployed facts

Funding Rate Arbitrage, Pairs Trading, BAB, QMJ and Flash Crash Reversal are all specific enough to
pre-register in `reports/hypothesis_registry.json` (M-107) with a test statistic and a decision rule —
which is the opposite of "Deploy These" before any test. Note the repo already has
`alpha_engine/funding_rate_arb.py` wired into the audit pipeline, so #1 above is partly built.

## 6. Fix list (cheap, do first)

| Item | Action |
|---|---|
| 4 dead `/investments/goldmines/…` + `master_dashboard.html` links | **CORRECTED:** they are LIVE. Version-control them and fix the broken PHP, do not remove |
| SQLite Databases / Backtest JSON / ML Models sections (0 links) | Populate or delete — an empty "All Data" section is worse than none |
| Meme/Penny section links the same URL twice | Fix |
| Non-monotonic TIER grading (79=B+, 77=A-) | Drop letter grades; use measured PF/WR with n |
| "Proven" / "Deploy These" on `live-vs-research.html` | Reconcile with 0-proven-edges, or retire the page |

---

## 7. Provenance

| Number | Source |
|---|---|
| Hub submenu + links | `TORONTOEVENTS_ANTIGRAVITY/index.html` lines ~999-1055, ~5991-6073 |
| Catalogue sections & link counts | `investments/all-dashboards.html`, parsed by `<h2>` |
| Dead links | `investments/goldmines/` absent; `find` over repo |
| Static-page proof | `grep -c 'fetch(\|.json\|.csv'` on `live-monitor/research/live-vs-research.html` = 0 |
| 5-strategy claims & scores | extracted verbatim from that page |
| 8,757 resolved / 0.6% share | `audit_dashboard/data/dashboard_data.json` → `systems` (gen. 2026-11-22T04:00:19Z) |
| QMJ KILL, net +0.02% vs 4.32% | `reports/hml_result.json` |
| `strategy` field, 11 values | `alpha_engine/data/active_picks.json` (n=29 active) |

**Caveat stated plainly:** the 0.6% figure refutes the hub claim *as expressed through system names*.
It does not prove momentum/breakout are rarely used internally, because family attribution is not
carried into resolved history — that gap is finding #5.1, not a conclusion.

Zero capital sanctioned. Paper only. Not investment advice.
