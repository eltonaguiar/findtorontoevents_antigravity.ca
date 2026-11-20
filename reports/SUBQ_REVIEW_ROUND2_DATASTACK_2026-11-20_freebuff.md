# Review — Subq round 2: the free data stack and the "search is the problem" thesis

**Date:** 2026-11-20 · **Reviewer:** Buffy (freebuff-deepseek-v4-flash)
**Companion:** [`SUBQ_REVIEW_2026-11-20_freebuff.md`](SUBQ_REVIEW_2026-11-20_freebuff.md) (round 1 —
residual mean reversion, id collision, cost-gate control)
**Method:** every free source Subq lists was probed from this host, and every repo-side claim was
checked against the checkout. Literature numbers are marked `UNVERIFIED`.

---

## 1. Verdict

The **data stack is accurate and mostly already ours** — 9 of 11 sources respond from this box with
no key or with a key we already hold, and two of the three we would need to sign up for are ones we
already have credentials for. The **search thesis is correct and, unusually, our own measurements
are its best evidence** rather than its citations. The **weakest part is the yfinance warning**, which
is right in substance and wrong in scope: survivorship bias afflicts *universe construction*, not
single-instrument time series, and stating it as a blanket defect would have invalidated the RSI(2)
calibration I ran yesterday for no reason. The **"what I'd do this week" ordering is wrong for us** —
alt-data ingestion is a multi-week build chasing an unproven edge, while we have a cheaper decisive
test (H-147) sitting unused.

---

## 2. Free sources, probed from this host (2026-11-20)

| Source | Probe | Result | Subq's claim |
|---|---|---|---|
| Binance REST | `GET /api/v3/ticker/price?symbol=BTCUSDT` | **200, 45 B, 403 ms** | genuinely free, no key — **correct** |
| Binance WebSocket host | TCP 443 to `stream.binance.com` | **reachable** | sub-second stream — **correct** |
| Finnhub | `GET /quote?symbol=AAPL` with **no** key | **401** | "free real-time" — true, but **not zero-setup**; signup required |
| FRED | `fredgraph.csv?id=DGS10` with **no** key | **200, 269 KB** | free — **correct**, and the CSV route needs no key at all |
| SEC EDGAR | `data.sec.gov/submissions/CIK0000320193.json` + UA | **200, 164 KB** | free, ~10 req/s — **correct** (UA required) |
| USAspending | `/api/v2/references/toptier_agencies/` | **200, 53 KB** | free — **correct** |
| CFTC COT (Socrata) | `publicreporting.cftc.gov/.../6dca-aqww.json` | **200** | free weekly — **correct** |
| CFTC COT (legacy) | `cftc.gov/dea/newcot/deafut.txt` | **200, 432 KB** | — also works, useful as a cross-check |
| Cboe VIX | `cdn.cboe.com/.../VIX_History.csv` | **200, 475 KB** | "~15-min delay" — **imprecise**: full daily history is free and immediate; the delay applies to live index quotes |
| Tiingo | no key → **403** | key present in env → usable | free tier limited |
| Alpha Vantage | `demo` key | **200, 21 KB** | works, heavily rate-limited |

**Credentials already present in this environment:** `FRED_API_KEY` set, `TIINGO_API_KEY` set;
`FINNHUB_API_KEY`, `ALPHAVANTAGE_API_KEY`, `POLYGON_API_KEY` unset.

**And the repo is already on this stack:** `tools/refresh_crypto_ohlcv.py` hits
`api.binance.com` + `api.kucoin.com`; `tools/cache/fred_carry_rates.json` exists; COT datasets are
committed (`cot_gc.json`, `cot_paper_pilot_status.json`). So the free-stack section describes work we
have already done, not a new capability.

**The correction that matters:** free data *existing* is not the constraint. This box can fetch
everything Subq lists — equity bars are stale (2026-06-18 per the plan) not unreachable. Our binding
constraint is that **no job refreshes it on a schedule with an SLA**, which is P0.1, not a sourcing
problem. A new dashboard built on the same unrefreshed tables would be stale on day one.

---

## 3. The yfinance warning — right in substance, wrong in scope

Subq: *"yfinance … has severe survivorship bias … if your universe is built from today's tickers,
every backtest is flattered."*

- **Correct:** survivorship bias genuinely afflicts cross-sectional screens. Our own
  `audit_trail/data/stock_prices.json` holds **61 symbols, zero delisted tickers** (no `.Q`/`.PK`
  entries) — any universe-wide equity backtest on it is flattered, exactly as Subq says.
- **The facts hold:** Yahoo killed the public API in 2017; yfinance calls undocumented endpoints; no
  licence, no SLA.
- **Wrong in scope:** survivorship is a property of *universe construction*, not of a single time
  series. My RSI(2) calibration used SPY and QQQ — index ETFs that exist by definition — so the
  bias does not touch it. A blanket "yfinance is not evidence" would discard a valid calibration
  while leaving the actual defect (our post-hoc 61-name universe) in place.

**House rule to adopt:** every artifact built on a yfinance-derived *universe* carries
`survivorship_flattered: true` until replaced by a point-in-time listing (delisted names from EDGAR /
exchange notices). Single-instrument series are exempt and say so.

---

## 4. The real data defect Subq's stack accidentally exposes

The one genuinely new finding in this pass is not the stack, it is **vintage**:

- Subq: *"FRED … free, with point-in-time vintages via ALFRED."*
- Repo: only `alpha_engine/cyclical_strategies.py` and `tools/crypto_rsi5070_forward_tracker.py`
  mention vintage at all. Our carry/rate features read **latest-vintage** FRED series.

Latest-vintage macro data is look-ahead: a GDP or CPI series today reflects revisions that did not
exist when the signal fired. That is the same defect class as our `wf_verdict` peeking
(+0.96% → −0.19% under point-in-time replay). It deserves a Phase-0 todo, and it is cheap: ALFRED
serves vintages over the same free FRED key we already hold.

---

## 5. The search thesis — corroborated by our own numbers, not by citations

| Subq claim | Status | Our corroboration |
|---|---|---|
| 1,285 variants, pre-registered, deflated Sharpe, honest conclusion | UNVERIFIED (literature) | — |
| Best solo public 12-year record ≈ Sharpe 0.8 | UNVERIFIED, and **absence of evidence** — do not treat as a ceiling | — |
| Synthetic zero-alpha panel: IS Sharpe 2.12 → OOS +0.18; 1.68 → +0.14 | UNVERIFIED (literature) | Our 700-strategy catalog produced 0/7 proven classes and 15 REFUTED hypotheses |
| 136,000 strategies: top 1% by predicted Sharpe = 5.70%/yr OOS vs 5.88% published average, at Sharpe 1.46 vs 2.03 | UNVERIFIED, and **the most useful number in the pass** | Same shape as our audit demoting PF while publishing net expectancy |
| A real edge is regime-dependent (gold: one negative 5-week window flips the year) | UNVERIFIED, mechanism sound | Our TAA settle: best lag-1 Sharpe 0.795 over 2007–2026, but 1.045 over 2018–2026 — window, not skill |

The single most decision-relevant sentence in the pass is the 136k result, because it says the
shrinkage lands on **Sharpe**, not on return: a searched strategy can still earn a market-like
return while carrying a much worse risk profile. That is precisely our ETF case — gross PF 1.82
looks like the one good class, while its own net expectancy is −2.26%.

Where I disagree: "the bar is Sharpe territory essentially no individual reaches" is a statement
about *verifiable public records*, and it will be used (wrongly) as a reason not to try. The defensible
version is the one our own gates already implement: **a searched edge must survive costs, out-of-sample,
and a multiplicity correction, or it is not an edge** — which says nothing about the ceiling for a
well-designed, pre-registered, single-hypothesis test.

---

## 6. "Value stocks vs mutual funds is a false binary"

Correct, and it is the same packaging illusion we keep catching: both are equity-risk-premium
exposure with different fee and turnover wrappers. Subq's diversification argument (multi-strategy
book had lower drawdown and higher Sharpe because losses coincided with gains) is the only part of
the pass I would put in front of an operator, because it is the same conclusion Phase 4 reaches from
a different direction.

---

## 7. "What I'd do this week" — right items, wrong order for us

| Subq step | My assessment |
|---|---|
| 1. Establish risk capacity before return target | **Agree, first.** A 50% loss needs 100% to recover; this is a constraint, not a strategy |
| 2. Free alt data with a known mechanism (USAspending, congressional, transaction panels, job listings) | **Defer.** Each is a multi-week ingestion build with no measured edge, and our registry has no hypothesis for any of them. Our gates would demand a pre-registration first |
| 3. Paper trade 60–90 days before funding | **Agree**, and we already have the machinery (`paper_trading/sleeves.json`, forward gates, reconciliation) |

**The step Subq is missing, and it is cheaper than all three:** H-147 — beta-hedge the picks we
already resolved and re-measure selection alpha. No new data, no ingestion, no new sleeve; reuses
`n=3,192` closed picks. It answers whether we carry information at all, which is the question every
item in §7 assumes away.

---

## 8. Recommended actions

1. **P0.1 (existing):** build the freshness job on the sources now verified here — Binance (crypto),
   FRED CSV (macro), Cboe CSV (VIX) — with `last_bar` per class and a CI failure on staleness.
   yfinance only as fallback, labelled.
2. **P0.8 (new):** move macro features to **ALFRED vintages**; latest-vintage FRED is look-ahead, the
   same defect as our PIT-replay failure.
3. **P0.9 (new):** stamp `survivorship_flattered: true` on any artifact built from a
   yfinance-derived universe until a point-in-time listing exists.
4. **Reject** Google Trends until a sanctioned access route exists (unofficial libraries break and
   have no licence).
5. **Keep H-147 first** — ahead of any alt-data or dashboard build.
6. **Do not build a second dashboard.** `/audit` already renders hourly; the useful increment is a
   freshness + MDE + selection-alpha panel on the existing page (P0.3/P0.4), not a new surface with
   its own staleness problem.

---

## 9. Reproduce

```bash
python3 /tmp/datastack_probe.py     # prints one JSON line per source
python3 -c "import json;d=json.load(open('audit_trail/data/stock_prices.json'));\
print(len(d['prices']), [s for s in d['prices'] if s.endswith(('.Q','.PK'))])"
grep -ril "alfred\|vintage" --include=*.py alpha_engine tools
```

**Stance unchanged:** no cell on `/audit` is sizeable today; cheap beta plus one pre-registered
sleeve that clears the forward gate remains the only defensible allocation. What this pass adds is a
verified, free, already-partly-wired data layer — and a vintage defect in it that we should fix
before it contaminates a macro hypothesis.
