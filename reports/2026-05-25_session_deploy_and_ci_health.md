# Session Deploy + CI Health — 2026-05-25 (post 03:00 UTC)

Read-only verification run. Two tasks: (A) live `pick_funnel.html` deploy validation; (B) GitHub Actions health since session start.

---

## TASK A — Live `pick_funnel.html` deploy verification

Source: `curl -s https://findtorontoevents.ca/audit/pick_funnel.html` → HTTP 200, 56,010 bytes (captured `/tmp/pf_live.html`).

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Leaked comment text `block. -->` / `block. --&gt;` NOT visible as page text | **PASS** | `grep 'block\. -->'` and `grep 'block\. --&gt;'` both return zero matches. The replacement comment at lines ~248-251 reads "(Do not write nested HTML comment markers inside this block — they prematurely close the parent comment and leak text onto the page.) -->" and is **inside** an HTML comment so it does not render. The fix from `ee0a75525` is live. |
| 2 | CRYPTO DISPUTED banner visible | **PASS** | Line 118 `<!-- DISPUTED BANNER (added 2026-05-25 by audit-pick-flow investigation) -->`; line 120 visible text `⚠ DISPUTED — Smart Picks · CRYPTO row (n=337, WR=78.9%, PF=9.69)`. From commit `c1b977997`. |
| 3 | "Active + Closed Picks Summary" section present | **PASS** | Lines 267-329 wrapped by markers `<!-- ===== ACTIVE + CLOSED PICKS SUMMARY (added 2026-05-25) ===== -->` … `<!-- /ACTIVE + CLOSED PICKS SUMMARY -->`; `<h2>Active + Closed Picks Summary (per asset class)</h2>` at line 268. |
| 4 | 14d subset panels present (`[14d]` chip / amber `#f59e0b`) | **PASS** | CSS `.recency-2w { border-left: 4px solid #f59e0b; … }` line 69; `.chip-14d` line 71; multiple `<span class="chip-14d">[14d]</span>` headers at lines 161, 211, 224. From commit `bc1666192`. |
| 5 | 48h hero section present (`[48h]` chip / magenta `#ec4899`) | **PASS** | CSS `.recency-48h { border-left: 4px solid #ec4899; … }` line 70; `.chip-48h` line 72; `<h2>Last 48 Hours — Per Asset Class <span class="chip-48h">[48h]</span></h2>` line 140; chip also at line 288. |
| 6 | JSON sidecars reachable | **PASS** | `pick_summary_stats_2w.json` → HTTP 200, 5,116 bytes, valid JSON with keys `generated_at, window_label, window_hours, cutoff_utc, …`. `pick_summary_stats_48h.json` → HTTP 200, 70,131 bytes, same schema. |

All six checks PASS. The three pick-funnel-nightly deploys (comment-fix, DISPUTED banner, 14d/48h subsets) have landed correctly on production.

---

## TASK B — GH Actions health since 2026-05-25 03:00 UTC

Window: 200 runs returned via `gh run list --limit 200 --created '>2026-05-25T03:00:00Z'`.

**Conclusion mix:** success 182, cancelled 8, in_progress 6, failure 3, skipped 1.

**Per-workflow failing-with-no-subsequent-success: 2 workflows.**

| Time (UTC) | Workflow | Run ID | Trigger commit | Author | Root cause |
|---|---|---|---|---|---|
| 05:48:51 | Sports endpoint smoke + Playwright | 26385534240 | `040cfd246` | github-actions[bot] (Coinglass scan) | Live `/sports_*.php` endpoints returning `{"ok": false, "error": "Sports DB connection failed"}` — 5/6 smoke tests fail (today, dashboard, pick_history, clv, steam/arb). Production sports DB connectivity issue, not a code regression in the failing commit. |
| 06:37:31 | CI Tests | 26387075347 | `3ddd0990e` | **eltonaguiar** (you) | One test failed: `tests/test_tier2_hero_cards.py::test_tier2_payload_staleness_detection` — `AssertionError: Expected not stale, got is_stale=True stale_days=30.3`. The Tier-2 payload referenced by the test is 30 days old; the staleness guard correctly flips. Likely needs pipeline refresh or test-fixture date update; 5,839 other tests pass. |

**Flagged for your attention:** the `CI Tests` failure on commit `3ddd0990e` (your `audit(report): COMMODITY COT 'edge' debunked` commit). It is almost certainly NOT caused by that report — the staleness assertion is fixture-age dependent and was likely already failing on earlier runs too; this commit just inherits it. Worth confirming whether `test_tier2_hero_cards.py::test_tier2_payload_staleness_detection` has been red for a while (in which case it's a known stale-data issue, not introduced this session) or just flipped (in which case the Tier-2 generator stopped writing).

**Sports smoke failure** is an infra issue (50webs MySQL connectivity from the live PHP endpoints) — read-only constraint means I did not retry. Recommend a manual `curl https://findtorontoevents.ca/sports_today.php` later to see if the DB recovered.

**No other workflows are red.** 6 still in-progress at scan time (gha-summary-report, Backtests-and-Deploy, Forward Signal Scanner, Mirror, SUPERPOWERS bootstrap, DNA Genome Daily) — these will either succeed or appear in the next health sweep.

---

## Constraints honored

- Read-only — no `gh run rerun`, no `gh workflow run`, no commits, no DB writes.
- Did not fetch 18 MB `dashboard_data.json`; only the two small sidecars (5 KB + 70 KB).
- All HTTP requests capped at 30s via `curl --max-time 30`.
