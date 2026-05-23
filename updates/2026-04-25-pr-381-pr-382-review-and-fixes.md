# Review of open sports-betting PRs #381 and #382 + suggested fixes

**Date:** 2026-04-25
**Reviewer:** Claude Code (continuing the OLG/Betway/tier_breakdown work shipped as #377)
**Status:** Recommend changes before merge

> **Update 2026-04-25 06:56 UTC:** PR #381 was subsequently closed (closedAt 2026-04-25T03:20:14Z) — this review is preserved as a historical lesson. The circular-EV finding flagged here informed the close-recommendation for PR #363 in the 2026-04-25 PR triage (`updates/2026-04-25-pr-triage-15-open-prs.md`).

---

## TL;DR

| PR | State | Verdict |
|---|---|---|
| #381 — Polymarket sports integration | OPEN | **Do not merge as-is.** Python file fails `py_compile` (won't even import). Approach is conceptually wrong — produces fake EV via circular logic. Scope creep: 4 unrelated event-data files. |
| #382 — Sports betting signal sources research | OPEN | **Strip 2 unrelated `events.json` files, then OK to merge.** Research doc is genuinely useful. |
| #377 — OLG ProLine+ + Betway scrapers + inject-mode | MERGED ~30 min ago | Already deployed. Live verification at 11:15 PM EST scheduled remote-agent check. |

---

## PR #381: `sports-prediction-market-integration` — DO NOT MERGE

### Critical bugs (blocking)

#### Bug 1 — File fails to import (SyntaxError)

[`prediction_market_agents/sports_polymarket_signals.py:122`](prediction_market_agents/sports_polymarket_signals.py#L122)

```python
def _is_valid Sports_market(text: str) -> bool:   # ← space inside function name
```

Reproduce:
```bash
$ python -m py_compile prediction_market_agents/sports_polymarket_signals.py
  File ".../sports_polymarket_signals.py", line 122
    def _is_valid Sports_market(text: str) -> bool:
                  ^^^^^^^^^^^^^
SyntaxError: expected '('
```

The file cannot be imported by any other module. The `if __name__ == "__main__"` block at the bottom never runs. Every other agent that tries `from prediction_market_agents.sports_polymarket_signals import …` will crash on import.

**Fix:** rename to `_is_valid_sports_market` (matching the call site at line 270).

#### Bug 2 — Caller name mismatch

[`prediction_market_agents/sports_polymarket_signals.py:270`](prediction_market_agents/sports_polymarket_signals.py#L270)

```python
if not _is_valid_sports_market(text):   # underscored
```

Even after fixing Bug 1's space, the call site uses underscored name. Pick one and use it consistently — recommend `_is_valid_sports_market` (PEP 8 snake_case).

#### Bug 3 — `DATA_DIR` escapes the repo

[`prediction_market_agents/sports_polymarket_signals.py:38`](prediction_market_agents/sports_polymarket_signals.py#L38)

```python
DATA_DIR = Path(__file__).parent.parent.parent / "alpha_engine" / "data"
```

From `prediction_market_agents/sports_polymarket_signals.py`, `parent.parent.parent` resolves to **the drive root** (`C:\` on Windows), not the repo root. The `OUTPUT_FILE` write at line 466 will fail with `PermissionError` or write to `C:\alpha_engine\data\sports_prediction_market_signals.json` (outside the repo).

**Fix:** drop one `.parent` — should be `Path(__file__).parent.parent / "alpha_engine" / "data"`.

#### Bug 4 — Function parameter typo

```python
def generate_sports_picks(marks: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if marks is None:
        marks = fetch_sports_markets()
    ...
    for market in marks:   # uses 'market' inside loop, but param is 'marks'
```

`marks` is fine technically (used internally), but the call site `save_sports_signals(picks=...)` and the docstring all reference `markets`. Rename for consistency: `def generate_sports_picks(markets: ...)`.

### Conceptual bug (more serious than the syntax errors)

#### Bug 5 — Circular EV calculation produces fake edge

In `generate_sports_picks()`:

```python
prediction_prob = float(market.get("outcome_prices", [0.5])[0])
# ...
if prediction_prob > 0.5:
    sportsbook_odds = 1.0 + (1.0 / prediction_prob) * 0.9   # ← derived from prediction_prob
else:
    sportsbook_odds = 1.0 + (1.0 / prediction_prob) * 1.1
```

Then in `convert_market_to_sports_pick()` it computes "EV" by comparing `prediction_prob` to the implied probability of `sportsbook_odds`. Since `sportsbook_odds` was *derived from* `prediction_prob`, the "EV" is purely a function of the constant `0.9`/`1.1` haircut — **not real edge**. Every "STRONG TAKE" produced this way is noise.

**The correct architecture**, used elsewhere in this repo:

1. Polymarket scraper writes rows to `lm_sports_odds` with `bookmaker_key=polymarket` (same shape as OLG ProLine+ scraper shipped in #377: see [live-monitor/olg_prolineplus_scraper.py](live-monitor/olg_prolineplus_scraper.py)).
2. Existing [`sports_value_analyze_lib.php:106-112`](live-monitor/api/sports_value_analyze_lib.php#L106-L112) uses Pinnacle as the sharp anchor for de-vig. Add Polymarket alongside it via a `sports_value_book_is_sharp_anchor()` helper.
3. EV is then computed against the **real consensus** of all 10+ books (Pinnacle + OLG + Betway + FanDuel + DraftKings + … + Polymarket as a sharp anchor), exactly the way it is for every other book. No new tables, no new pick-generation pipeline.

This is also how the orchestrator already works for crypto (`prediction_market_agents/orchestrator.py`) — it merges PM signal *into* the existing consensus rather than running parallel.

### Scope creep — 4 unrelated files

PR #381 includes:
- `EVENT_DATA_FIXES.md`
- `EVENT_DATA_QUALITY_REPORT.md`
- `analyze_event_data.py`
- `fix_event_data.py`

These are about events ingestion (the dating-events scraper), not sports betting. They should be in their own PR with a `data-quality/` or `chore:` prefix, not bundled with the PM integration.

### SQL schema concerns (non-blocking but worth fixing)

[`live-monitor/sql/sports_prediction_market_integration.sql`](live-monitor/sql/sports_prediction_market_integration.sql)

5 new tables + 3 views = significant footprint for something that should be 0 new tables.

Specific issues:
1. **`vw_sports_high_confidence_picks` references nonexistent column** `pm.predicted_ed_pct` (typo for `prediction_edge`?) and `pm.calculation_ev_pct` (typo for `calculated_ev_pct`). View creation will fail.
2. **`vw_sports_pm_performance_summary` references undefined alias** `avg_accuracy` in `ORDER BY` (only `accuracy` is defined). MySQL will reject.
3. **`CONSTRAINT chk_prob_sum`** in the commented section is wrong — `yes_probability + no_probability` should equal 1.0 for a binary market, not be `<= 1.0`. (Currently commented out so harmless, but the comment will mislead future maintainers.)
4. **`outcome_correct TINYINT(1)`** in `lm_sports_pm_performance` lacks a `DEFAULT` — inserts will need explicit value or it'll be `NULL`, breaking `case when outcome_correct = 1` aggregations.
5. **`chk_prob_sum` mentions checking probability but uses `<=`** — for binary markets the sum should be exactly 1; for n-ary it can be ≤ 1; logic is unclear without comment.
6. **`is_high_confidence` and `is_arbitrage` are flags** that get dropped from the recommended-action computation in the cross_market table — they're set but never read.

If we proceed with the architecture I recommended (no new tables), these issues are moot — the existing `lm_sports_odds` schema handles it.

---

## PR #382: `sports-betting-signal-sources-research` — accept with one fix

The 944-line research doc at [`updates/2026-04-25-sports-betting-signal-sources-research.md`](updates/2026-04-25-sports-betting-signal-sources-research.md) is genuinely useful — concrete repo recommendations (OddsHarvester is already in our `requirements-sports-extra.txt`, kyleskom NBA-ML, georgedouzas), realistic cost estimates, sane prioritization.

**Required change before merge:** strip the 2 `events.json` files (`events.json` and `next/events.json`). They're build artifacts that shouldn't ship in a research-only PR. They're 94 deletions of legitimate data plus an addition that bumps PR size from ~944 lines to thousands of irrelevant JSON.

**Acceptable as-is:** the research doc itself.

---

## What I recommend

1. **Close PR #381** rather than fix it. The conceptual approach is wrong. Reopen as a tiny PR that just adds Polymarket as a `bookmaker_key` in the existing scraper pattern (see "Suggested replacement" below).

2. **Strip the 2 events.json files from PR #382**, then merge. The research doc is valuable.

3. **Wait for the 11:15 PM EST scheduled CI report on PR #377** before adding any more sports-betting infrastructure. We don't yet know if OLG ProLine+ + Betway are actually injecting in production. Adding more layers on top of an unverified base wastes effort.

---

## Suggested replacement for PR #381 (when ready)

If you still want Polymarket signal after the OLG/Betway path is verified:

### Single new file (~150 lines)

`live-monitor/polymarket_sports_scraper.py` — mirror of [`live-monitor/olg_prolineplus_scraper.py`](live-monitor/olg_prolineplus_scraper.py):

- Fetch `https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=200`
- Filter for sports markets via accept-keyword list (champion/finals/playoff/team names)
- Filter `volumeNum > 25000` (not 5000 — 5k markets are too thin to be sharp)
- Filter binary `outcomes` arrays only (skip multi-outcome futures for v1)
- Match Polymarket question text to existing `lm_sports_odds` events via fuzzy team-name matching
- Emit rows in `lm_sports_odds` shape with `bookmaker_key=polymarket`, `outcome_price=1.0/yes_prob`
- POST to existing `sports_odds.php?action=inject_fallback` endpoint — no schema changes

### Two-line PHP change

Add `polymarket` to the sharp-anchor list in [`sports_value_analyze_lib.php:106-112`](live-monitor/api/sports_value_analyze_lib.php#L106-L112):

```php
function sports_value_book_is_pinnacle($bookKey) {  // rename to is_sharp_anchor
    if ($bookKey === null || $bookKey === '') return false;
    $k = strtolower($bookKey);
    return (strpos($k, 'pinnacle') !== false) || (strpos($k, 'polymarket') !== false);
}
```

That's the entire integration. Polymarket then participates in de-vig the same way Pinnacle does, EV is computed against real consensus, and we add zero tables.

### One workflow step

Add to [`.github/workflows/sports-betting-refresh.yml`](.github/workflows/sports-betting-refresh.yml) after the Betway step:

```yaml
- name: Polymarket sports sharp anchor
  continue-on-error: true
  run: |
    python3 live-monitor/polymarket_sports_scraper.py --save-json --inject-api || echo "Polymarket scraper skipped"
```

Total diff: ~160 lines added, 1 line modified. PR #381 currently adds 2,639 lines for the same conceptual goal — and it doesn't work.

---

## Verification I ran for this review

```bash
# PR #381 Python file fails to import
$ python -m py_compile prediction_market_agents/sports_polymarket_signals.py
SyntaxError at line 122

# Confirmed all three flagged bugs at exact line numbers
$ grep -nE "(_is_valid Sports_market|_is_valid_sports_market|parent\.parent\.parent)" \
    prediction_market_agents/sports_polymarket_signals.py
38:DATA_DIR = Path(__file__).parent.parent.parent / "alpha_engine" / "data"
122:def _is_valid Sports_market(text: str) -> bool:
270:        if not _is_valid_sports_market(text):

# PR #382 has 2 events.json files leaking in
$ gh pr diff 382 --name-only
events.json
next/events.json
updates/2026-04-25-sports-betting-signal-sources-research.md
```
