# findtorontoevents.ca/audit — UI / Edge / Freshness Audit
**Date:** 2026-05-25 03:30 UTC  ·  **Author:** Claude Opus 4.7  ·  **Source:** live DB + live `dashboard_data.json` HEAD fetch + template.html / hc_filter.js source review

## TL;DR

| Surface | Verdict | Severity |
|---|---|---|
| **HIGH CONVICTION overlay** (CRYPTO 60.3% / EQUITY 68.1% cited) | **Unreproducible** — the cited closed-book stats can't be recomputed from the live `trading_picks` table because `trust_score` is NULL on 38,884 of 38,889 closed picks (99.99%) | P0 |
| **Smart Picks "Signal Time EST 1.4h ago"** | **Misleading display** — every row shows the same age because it's the dashboard-JSON age, not the per-pick signal age. `signal_time` field is absent from `smart_picks_feed`; UI falls back to `age_hours` (= file-build age) | P1 |
| **Swarm Picks section** | **Effectively abandoned** — data file last regenerated 2026-05-24 04:34 UTC, newest pick inside is dated **2026-05-12** (13 days old). Workflow `swarm-pick-review.yml` runs daily but no longer produces new picks | P1 |
| **US Equity Picks (UEPS) tab** | **No live edge** — page itself says "Building track record — n=0/100"; sample picks shown are demo / sample | P2 |
| **Smart Picks button vs Smart Picks tab** | Two different things; the button is a filter on Active Picks, the tab is a curated feed. Not a bug, but easily confused | P3 |

---

## 1. HIGH CONVICTION overlay (the "🔥 HIGH CONVICTION FILTERS APPLIED" panel)

Live DB query just now (`mysql.50webs.com / ejaguiar1_stocks`, table `trading_picks`):

```
Score / trust population on CLOSED picks (n=38,889 total):
  closed_with_elite_score    27,859    (71.6%)
  closed_with_trust_score         5    (0.013%)
  closed_score_ge_55          4,216
  closed_trust_ge_4               0    ← the HC gate requires this
```

Active picks:
```
Category       n_active   pass HC (s>=55,t>=4)
crypto         4,897      1     ← yes, ONE pick
forex          1,387      0
commodity      1,302      0
(null)           951      0
equity           534      0
```

→ The HC overlay as currently configured is effectively a kill switch — only one active pick passes today.

**The cited closed-book stats:**
- `CRYPTO: WR 60.3% on N=562 (+9.7pp lift)` — **unreproducible**. The 562 closed-with-trust-and-score-gates doesn't exist; there are 5 closed picks total with a non-NULL trust_score.
- `EQUITY: WR 68.1% on N=72 (+29.0pp lift)` — same problem.
- `FOREX: WR 55.0% n=309` — current DB shows 1,666 closed FOREX picks at WR 43.9% (the bigger n makes the older "55%" look like a small-window cherry-pick). 5 rows have `pnl_pct < -100%` including one at **−106,700%** — unit-clamp commit #876 missed them. Drags FOREX avg to −8% and makes PF round to 0.00.
- `COMMODITY: WR 5% / PF 0.12 (n=20 post-dedup)` — current full-baseline is 674 closed picks at WR 40.5% / PF 0.97. The "n=20 post-dedup" was a specific filtered slice; that exact slice now returns 0 matches.

**Fix paths (pick one):**
1. Backfill `trust_score` on the 38,884 closed picks that don't have it (preferred — would let the HC overlay actually work on historical data).
2. Move HC gate from `pick.trust_score` to a field that IS populated (e.g., `elite_score` or strategy-level derived TRUST tier from a JOIN).
3. Mark the HC overlay UNVERIFIABLE on the UI until #1 lands, and remove the cited WR claims until they can be recomputed live.

## 2. Smart Picks "Signal Time EST" freshness

**Live HTTP HEAD** on `https://findtorontoevents.ca/audit/data/dashboard_data.json`:
- `Last-Modified: Mon, 25 May 2026 02:03:55 GMT` (just under 1.5h before my check)
- `generated_at: 2026-05-25T01:55:35.704580+00:00`
- Size: 22.8 MB

**Field presence** (counted in first 2 MB of the live JSON):
- `"signal_time"` occurrences: **0**
- `"age_hours"` occurrences: **362**
- `"created_at"` occurrences: 0

**Template logic** [audit_dashboard/template.html#L12583-L12589](audit_dashboard/template.html):
```javascript
if (p.signal_time || p.timestamp || p.generated_at) {
  signalTime = ...formatted...
} else {
  signalTime = (p.age_hours || 0).toFixed(1) + 'h ago';   ← FALLBACK
}
```

→ **Because `signal_time` is missing on every Smart Picks pick, every row falls through to `age_hours` — which is computed at file-build time.** So `"1.4h ago"` means the *file* is 1.4h old, NOT that the *pick* fired 1.4h ago. A pick that's been open for 5 days will still display "1.4h ago" because the dashboard JSON was rebuilt 1.4h ago.

**Fix:** populate `signal_time` (= `created_at` from `trading_picks`) into the `smart_picks_feed` payload in `audit_trail/dashboard_generator.py`. One-line addition where the smart_picks_feed is built.

## 3. Swarm Picks section

**Data source:** `audit_dashboard/data/swarm_picks.json` (60 KB, 38 picks)
**Last file modification:** 2026-05-24 04:34 UTC (~23 hours ago)
**Newest pick inside file:** `created_at = 2026-05-12T16:02:00−05:00` (**13 days old**)
**Oldest pick:** 2026-05-11T22:00:00−05:00

**Workflow:** `.github/workflows/swarm-pick-review.yml` — `cron: "0 3 * * *"` (daily at 03:00 UTC). It runs but emits no new picks (only resolves/refreshes the existing 38).

**Comparison to ai-tournament:** different system entirely.
- **Swarm Picks** = multi-model TradingView paper-trade captures (38 historical picks frozen May 11-12), graded by consensus tier (unanimous / strong / moderate / single / control). One-time backfill; nightly job only resolves existing picks, doesn't add new ones.
- **AI Tournament** (`/audit/ai-tournament.html`) = live forward-test of 10+ models submitting daily picks via `tools/ai_tournament/generate_picks_fleet.py`. Active, growing — 1,490 picks today, +20 today from Grok HEAVY submission.

→ Swarm Picks is **abandoned** in the sense that no new picks have entered for 13 days. The nightly workflow exists but appears to no longer generate fresh swarm consensus. Recommend either (a) revive the multi_model_pick_gen.py pipeline so new picks flow in, or (b) deprecate the Swarm Picks tab on /audit and redirect to ai-tournament.html.

## 4. US Equity Picks (UEPS) tab

The tab title literally says "Building track record (n=0/100)". The screenshot picks (ADBE, PYPL, QCOM with F-Score 7-8, Altman Z scores) are demo/sample data from `HEDGE_FUND_GAP_ANALYSIS_2026-05-24.md` — they are not in `trading_picks`. **No edge can be claimed** until real picks flow through. The composite (Magic Formula × Piotroski × Acquirer's Multiple × SafetyGate) is documented but doesn't have a live writer yet.

## 5. "Smart Picks button" vs "Smart Picks tab" — UX confusion

[audit_dashboard/template.html#L1306](audit_dashboard/template.html) is the **button** `🧠 SMART PICKS` — it filters the Active Picks table by intersecting against the live `smart_picks_feed`. Its own tooltip already admits: "Closed-pick analysis shows the underlying confluence/score fields are missing from most historical records, so the Smart Picks filter cannot be verified as an edge on closed data. Use it as a live signal overlay, not as a standalone edge filter."

[audit_dashboard/template.html#L1358](audit_dashboard/template.html) is the **tab** `🧠 Smart Picks` — opens the curated panel that reads `smart_picks_feed` directly with its own asset-class filter buttons (All / Crypto / Equity / Forex / Commodity / Futures / ETF).

Both consume the same JSON; the difference is overlay-vs-direct-view. The button's own tooltip is the most honest line on the page: **Smart Picks is a live signal overlay, not a verified-edge filter.**

## 6. Cross-cutting baseline stats (where the real edge actually is — or isn't)

```
BASELINE 90d / ALL closed (from trading_picks, no gates applied):
  class        n      wr%     PF    avg_pnl%
  commodity   674    40.5    0.97    -0.00
  crypto    4,494    44.7    0.97    -0.04
  equity       30    60.0    0.76    -0.39    ← n too small
  etf          14    28.6    0.20    -1.26    ← n too small + losing
  forex     1,666    43.9    0.00   -69.74    ← outlier-distorted
  futures      18    11.1    0.16    -0.05    ← critical
  meme         66    31.8    0.41    -1.85
```

**Reality check vs the page's headline tiles:**
- CRYPTO headline "PF 1.25 / WR 44.6% / n=8067" → recent live closed-book is **PF 0.97 / WR 44.7% / n=4,494**. Headline is using a longer-history aggregate; the recent panel is honest.
- The "SUPREME EDGE 2026-05-12" callout for COMMODITY `cot_positioning` (n=104, WR 86.5%, Sharpe +1.377) returns 0 matching rows from `WHERE strategy LIKE 'cot%'` today — the strategy may have been renamed or the cot rows are in a different table. **Worth verifying before quoting this on the page.**

## 7. "If you bought Smart Picks at entry, would you be profitable?" — partial answer

I cannot fully simulate this in one turn because the full `smart_picks_feed` payload (entry + current_price per pick) lives at the bottom of the 22.8 MB dashboard JSON and would need a large fetch + per-symbol price re-marking. **What I can say from what I sampled:**
- `age_hours` shows 362 picks in the feed
- They lack `signal_time` so we can't trust "1.4h ago" — most are likely older
- Aggregate CRYPTO baseline 90d closed = WR 44.7% / PF 0.97 → on equal-weight basis you would be **break-even to slightly losing** before fees if you treated every Smart Pick as a closed-out trade

To do this properly: fetch the full `smart_picks_feed`, re-mark every OPEN pick with `current_price` from yfinance, compute unrealised + realised P&L, weight by position size. Estimated 30-45 min of agent time. **Recommend spawning a follow-up subagent if you want a hard number.**

---

## Action items (ranked)

| # | Pri | Action | Cost |
|---|---|---|---|
| 1 | **P0** | Backfill `trust_score` on closed picks OR rewrite HC gate to use a populated field. Page is currently citing stats that can't be reproduced. | M |
| 2 | **P0** | Re-clamp 5 FOREX rows with `pnl_pct < -100%`. One-line `UPDATE trading_picks SET pnl_pct = -100 WHERE pnl_pct < -100`. | S |
| 3 | **P1** | Add `signal_time` field to `smart_picks_feed` payload in `dashboard_generator.py` so "Signal Time" stops being misleading | S |
| 4 | **P1** | Decide on Swarm Picks tab: revive the pick-gen pipeline OR redirect to ai-tournament.html. 13 days stale right now. | M |
| 5 | **P2** | Verify the `cot_positioning` SUPREME EDGE callout — current DB query returns 0 rows; strategy may have been renamed or table changed | S |
| 6 | **P2** | Run the per-pick P&L simulation on Smart Picks (separate subagent, ~45 min) | M |
| 7 | **P3** | Surface "n_active that pass HC" and "data freshness age" as live readouts at the top of every tab. Right now staleness is invisible. | M |

---

## 8. Independent cross-validation (Ring-2.6-1T via opencode, 03:50 UTC)

Ring ran the same audit independently and corroborated every P0/P1 finding above. **Net-new findings from Ring's pass that I missed:**

1. **`data/smart_picks.json` itself is 25 days stale** (last regenerated 2026-04-30T02:56). I saw the dashboard JSON age (1.5h) and the dashboard-side `signal_time` missing-field issue — Ring caught that the *upstream file* the dashboard reads from is much older. So picks may be re-cycled with stale entry prices.
2. **`signal_outcomes` table is 82 days stale** (last resolved 2026-03-04) — worse than the `trading_picks` 2-day staleness I caught. The outcome-resolver pipeline is essentially dead for forward-validation.
3. **Top-N Rank Backtest tool is broken** — connect failure ("Access denied"). The hindsight-replay validator is non-functional, so we can't ground-truth any "X% WR if you took the top-N at time T" claim.
4. **DSR "perfect" CRYPTO ML edges on n=25-34** (INJ 1d WR 100%, FET 1d WR 100%) — Ring flags these as **suspiciously perfect**. DSR ≥ 0.9995 on n=25 means almost zero loss variance, which can be a small-window artifact, not real edge. The COT n=104 result is the one that survives serious scrutiny.

**Ring's verdict on profitability** ("if you bought Smart Picks at entry"): slightly positive due to heavy filtering, but edge is concentrated in narrow buckets (cot_positioning commodity, ML-enhanced crypto LONGs with conf 0.80-0.85, copy traders on micro-samples). The "82% WR / PF 13" headline cells are post-hoc segment searches, not actionable forward signals.

**Bottom line (both audits agree):** the system has narrow real edge but should NOT be treated as a production trading system in current state. The most honest line on the page is the Smart Picks button's own tooltip: *"the underlying confluence/score fields are missing from most historical records, so the Smart Picks filter cannot be verified as an edge on closed data. Use it as a live signal overlay, not as a standalone edge filter."*

**Combined P0 list (mine + Ring's):**
1. Backfill `trust_score` on closed picks (HC overlay claims unreproducible)
2. Re-clamp 5 FOREX rows with `pnl_pct < -100%`
3. Regenerate `smart_picks.json` (25 days stale)
4. Investigate signal_outcomes resolver — 82 days stale = dead pipeline
5. Fix Top-N Rank Backtest DB connection
6. Add `signal_time` to smart_picks_feed payload (UI shows misleading file-age)
7. Decide on Swarm Picks tab (13 days stale; revive or deprecate)
8. Mark the DSR=0.9999 CRYPTO ML claims on the page as "small-sample, awaiting n≥100 confirmation"
