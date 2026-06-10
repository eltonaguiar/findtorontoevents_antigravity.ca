# Code Review — 48h Web Pages + Resolver Accuracy (2026-06-10)

Operator goal: world-class prediction system. Two known failure modes to guard: (1) reverse-stock-split
artifacts, (2) **pick performance resolved by a layered INACCURATE method** (close-walk / non-intrabar →
inflated WR). Reviewed all web-facing pages + resolver code changed on `main` in the last 48h
(2 parallel review agents + direct verification of the production resolver lines).

## A. Resolver accuracy — the core concern (VINDICATED + LOCATED)
The 3 standalone re-resolution tools (the 48h work) are **ACCURATE**: true intrabar first-touch,
SL-wins-same-bar-ties (conservative), `ambiguous` flag, fixed-horizon-from-ENTRY (no look-ahead), and
a bad-geometry guard in `reresolve_intrabar_signal_outcomes.py`. ✓

The accuracy gaps are in the **PRODUCTION live resolver `audit_trail/universal_pick_resolver.py`**
(wired into audit-dashboard.yml + dashboard_generator + 10 callers — it feeds /audit):

- **Bug 1A (HIGH) — stale/look-ahead intrabar window.** The OHLC pre-fetch (`:1041-1043`) pulls only
  the *most-recent* bars (`yfinance period="5d"`, `binance limit=48`), NOT bars anchored to each pick's
  entry. Bars carry no timestamp (Binance `k[0]` open_time is discarded, `:542-548`). So for any pick
  older than the window, `_check_tp_sl_intrabar` (`:558-595`, which is itself correct) replays the WRONG
  recent bars → look-ahead / confidently-wrong "intrabar" resolution. **STATUS: documented, NOT yet
  fixed — it's a multi-function refactor of the hot production resolver that must be TESTED, not rushed
  (this repo has had outages from rushed resolver changes).**
  *Fix spec (tested follow-up):* (1) add `"timestamp": int(k[0])` to Binance bars + the index ts to
  yfinance bars; (2) fetch entry-anchored windows (klines `startTime`/yf `start=` from pick.timestamp
  forward) OR fetch wider + filter; (3) in `_check_tp_sl_intrabar` skip bars with `ts < pick entry` and
  return None if none remain (→ tagged close_approx). Mirror the proven `tools/reresolve_intrabar.py`
  entry-anchored pattern, or route production resolution through that tool.
- **Bug 1B (MEDIUM) — close-only fallback. FIXED (this review).** When intrabar bars are missing,
  the resolver fell back to `check_tp_sl(pick, current_price)` (`:761-785`) — a single-snapshot price
  check that tests TP before SL (the classic inflation pattern), silently labeled like a real outcome.
  **Fix applied:** tagged these `resolution_method="close_approx"` (vs `"intrabar"`) on the resolved
  dict so downstream WR/PF can exclude/flag them. Additive, zero behavior change. (`:1255-1284`)
- **Bug 1C (LOW) — production path lacks the `ambiguous` flag + bad-geometry guard** the standalone
  tools have. Port them with the Bug 1A fix.

## B. Reverse splits — WIRED (no active artifacts)
`universal_pick_resolver` applies `should_adjust_for_split` (`:1159-1198`) BEFORE the TP/SL replay,
scaling entry/tp/sl by the cumulative factor, date-guarded to splits AFTER pick submission — correct.
Registry `reverse_split_symbols.py` (7 symbols). `stock_ohlcv` scanned split-clean (120d). Gap (benign):
the equity-touching standalone tools (`resolve_picks_now`, `reresolve_intrabar_signal_outcomes`) don't
re-apply split adjustment, relying on `stock_ohlcv` being pre-adjusted at ingest. Orphan dead code:
`outcome_resolver.py:720 get_split_adjustment` (0 callers).

## C. Web pages (48h) — mostly honest; 2 fixed
| Page | Finding | Action |
|---|---|---|
| model.html | unclosed `<div id=resolver-artifact-banner>` (whole page nested in banner) + over-confident green "✅ intrabar now live" banner contradicting the site's own OPEN intrabar P0s | **FIXED**: closed the div; banner re-framed amber/honest, names the Bug 1A gap + points to intrabar_truth_by_class.json |
| claudes_test.html | h1/subtitle said "26 portfolios" but title/filter/data = 29 (stale breakdown summing to 26) | **FIXED**: 26→29, dropped the stale breakdown |
| edge_validation_roadmap.html | headlines "NO CURRENT EDGE / ALL CLASSES FAIL TIER-2" | CLEAN (exemplary honesty) |
| incidents.html, trading_blueprint.html, ab_panel.html, findcryptopairs/now.html, reports/{daily,weekly,gha}.html | honest/deflationary numbers, no broken fetches, no unlabeled artifacts | CLEAN |
No broken/404 data fetches found anywhere; no "S-tier 100% WR"-style artifacts shown as edge.

## Fixes shipped this review
- `model.html`: closed unclosed banner div + replaced false-confidence resolver banner with honest amber framing.
- `claudes_test.html`: portfolio count 26→29.
- `universal_pick_resolver.py`: Bug 1B `resolution_method` tagging (intrabar vs close_approx).

## Deferred (HIGH — needs a TESTED change, not a rushed hot-resolver edit)
- **Bug 1A** entry-anchored intrabar fetch in `universal_pick_resolver.py` (spec above). Highest-value
  remaining accuracy fix; recommend adopting `reresolve_intrabar.py`'s entry-anchored pattern with a
  test harness before it lands in the live hourly resolver.
