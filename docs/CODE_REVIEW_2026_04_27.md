# 48-Hour Code Review — 2026-04-27

**Window:** 2026-04-25 → 2026-04-27
**Branch under review:** `origin/main`
**Reviewer:** multi-agent (3 parallel `superpowers:code-reviewer` passes — audit dashboard / sports betting / events) + synthesis
**PRs in scope:** 21 human-authored PRs out of ~3,600 commits (auto-bot commits filtered)

The three product surfaces named by the user — `findtorontoevents.ca/audit`, `findtorontoevents.ca` (events), and `findtorontoevents.ca/live-monitor/sports-betting.html` — were each reviewed independently. This document synthesizes findings across them.

---

## TL;DR

| Area | Critical | High | Medium | Verdict |
|---|---|---|---|---|
| Audit dashboard (financial prediction) | 3 | 6 | 6 | Surgical fixes shippable; one big perf risk |
| Sports betting (predictions + auto-place) | 9 | 7 | 6 | **Money-math + secrets exposure — ship code fixes today, rotate creds today** |
| Public events site | 0 | 0 | 3 | Genuinely low risk |
| **Total** | **12** | **13** | **15** | |

A companion PR ships the 6 surgical critical fixes (3 audit + 3 sports). The remaining 4 sports criticals (`C4`, `C5`, `C6`, `C8`) are operations-level (credential rotation, FTPS switch, auth-key replacement) and require user decisions before code can be touched.

This review explicitly **excludes** PRs #444, #445, #446, which were opened earlier today as part of the asset-class-active-picks investigation (already reviewed inline at the time of opening).

---

## Critical findings — code fixes shippable today

### 🔴 [audit-C1] SQL injection in `feature_edge_analyzer.py`
**PR:** #348 `feat(audit): ML score + feature persistence + symbol-strategy edge tracking`
**Files:** `audit_trail/feature_edge_analyzer.py:124-128`, `:175-178`, `:187-194`

Raw SQL is built via f-string with `col`, `asset_class`, and `direction` directly interpolated:
```python
conditions.append(f"rp.asset_class = '{asset_class}'")
conditions.append(f"rp.direction = '{direction}'")
sql = f"""SELECT ... WHERE rp.{col} ... {where}"""
cur.execute(sql)
```

Today every caller passes hardcoded constants (`"ALL"`, names from `NUMERIC_FEATURES`/`CATEGORICAL_FEATURES`). But `run_full_analysis()` accepts arbitrary `asset_classes` and `directions` lists from a CLI argparse path (`__main__`) and from `dashboard_generator.py:13738`. A future caller passing user-controlled input gives full DB write/leak access against the audit trail.

**Fix:** parameter-bind `asset_class`/`direction`; whitelist `col` against `NUMERIC_FEATURES`+`CATEGORICAL_FEATURES` keys before interpolation. Defense-in-depth — today's exposure is theoretical, the f-string pattern is permanent risk.

### 🔴 [audit-C2] `update_pick_outcome` mislabels break-evens as LOSS
**PR:** #348
**Files:** `audit_trail/pick_feature_store.py:403`, `audit_trail/symbol_strategy_tracker.py:78`

```python
status = "WIN" if pnl_pct > 0 else "LOSS"   # pick_feature_store.py
is_win = 1 if pnl > 0 else 0                 # symbol_strategy_tracker.py
```

Any `pnl_pct == 0.0` (true break-even, or round-trip-fee-only flat) becomes LOSS. This contradicts `forward_validator.py` and `outcome_resolver.py` which carry FLAT/EVEN as a third state. Once `update_pick_outcome` is wired into the resolver (per the PR body), every dead-flat trade silently inflates LOSS counts in the per-symbol WR table — exactly the deliverable PR #348 advertises. Same family as the [Cycle10 unit-mismatch bug](feedback_cycle10_unit_mismatch_bug.md) we already learned from.

**Fix:** classify as `EVEN` when `pnl_pct == 0` in both call sites; mirror the trinary on the WIN/LOSS counters in `symbol_strategy_tracker.update_from_closed_pick`.

### 🔴 [audit-C3] Hot-path persistence loop runs ~3,600 single-row commits per cycle
**PR:** #348
**Files:** `audit_trail/dashboard_generator.py:13713-13722`, `audit_trail/pick_feature_store.py:357`

The dashboard cycle hot-path loops over `active + recent_closed + smart_picks` (~3,600 rows) calling `store_pick_features(...)` which executes `cur.execute()` followed by `conn.commit()` *per row*. Per-row commit on SQLite fsync-syncs every iteration. Combined with `run_full_analysis()` which performs ~112 separate aggregate queries on top, plus optional `rebuild_from_closed_picks` rescanning the entire 24k-row `raw_picks` table, this pushes the audit-dashboard.yml workflow toward the timeout that PR #436 just widened.

**Fix:** move `conn.commit()` outside the per-row loop (single transaction); set env-default `AUDIT_RUN_FEATURE_EDGE_ANALYSIS=0` for the next cycle until the cadence is established.

### 🔴 [sports-C2] Situational adjustments are always 0 — feature is marketed but inert
**PR:** #400
**File:** `alpha_engine/sports_edge_finder.py:181-193`

```python
if "basketball" in sport:
    adj = self.situational.adjust_nba_prob(true_prob)   # no rest, no b2b
elif "icehockey" in sport:
    adj = self.situational.adjust_nhl_prob(true_prob)   # no b2b, no goalie
elif "baseball" in sport:
    adj = self.situational.adjust_mlb_prob(true_prob)   # no divisional, no total
elif "americanfootball" in sport:
    adj = self.situational.adjust_nfl_prob(true_prob)   # no spread, no wind
```

Every call uses default kwargs, which means each `adjust_*_prob` returns 0. PR #400's body advertises +6.5% NBA-rest, +3% NFL key-numbers, etc. as the value-add. This is the [Confidence ≠ Edge](feedback_confidence_is_not_edge.md) anti-pattern: marketing a signal whose math always evaluates to no-op.

**Fix:** gate the situational call behind an `os.environ.get("SPORTS_SITUATIONAL_ADJUSTMENT") == "1"` flag with a clear log line, until the upstream feed (rest days from a schedule table, divisional flag from team mapping, weather from a wx API) is wired. Default off.

### 🔴 [sports-C3] Devig fallback is single-outcome only — EV ≈ 0 by construction
**PR:** #400
**File:** `alpha_engine/sports_edge_finder.py:175-178`

```python
# Fallback: use devigged consensus from all quotes for this outcome
invs = [1.0 / float(q["outcome_price"]) for q in quotes]
true_prob = sum(invs) / len(invs) if invs else 0.5
```

This is the mean of `1/odds` for *one outcome*, never normalized against the other outcomes of the event. The result equals the bookmaker's vig-loaded implied probability. When `ev = (true_prob * (price - 1)) - (1 - true_prob)` is computed downstream, the result trends to `-vig%`, so the "+EV" branch never legitimately fires from this path; any positive EV that does emerge is dispersion noise, not edge. The reference PHP implementation (`sports_value_truep_consensus_jensen` at `live-monitor/api/sports_value_analyze_lib.php:120-154`) does this correctly — Python regressed.

**Fix:** pre-compute Jensen-normalized devig once per event by summing `mean(1/price)` across all outcomes, then derive each `true_prob = oc_invs[ok] / inv_sum`.

### 🔴 [sports-C9] Arbitrage scanner doesn't enforce different-books-per-leg, no staleness filter
**PR:** #400
**File:** `alpha_engine/sports_arbitrage_scanner.py:94-122`

Comment says "different books" but the code happily picks the same book for every leg. Combined with `lm_sports_odds` accumulating rows over time (the read query filters by `commence_time` and price range only, not `last_seen`), arbs can be assembled from prices that no longer exist. Anyone acting on these alerts loses money.

**Fix:** enforce distinct `bookmaker_key` across legs (skip event if all legs share one book); bump `min_profit_pct` default 0.5 → 1.5 to absorb slippage; add a runtime warning when the data feed lacks an `updated_at`/`last_seen` predicate.

---

## Critical findings — operations-level (NOT in code PR; require user action)

These are critical but cannot be fixed by a code patch alone — they require credential rotation, deploy-pipeline changes, or auth-system work. Listed here as **action items for the user**.

### ⚠️ [sports-C4] Plaintext production DB password in repo
- `live-monitor/api/db_config.php:8-10, 26-27` — `'eltonsportsbets'`, `'stocks'` written directly.
- `alpha_engine/sports_edge_finder.py:31` and `alpha_engine/sports_arbitrage_scanner.py:39` repeat the same password as a Python `os.environ.get(..., DEFAULT)` fallback.
- **Action:** rotate both passwords today. Move credentials to a non-tracked include outside webroot. Remove Python defaults — refuse to start if env var is missing.

### ⚠️ [sports-C5] Cleartext FTP scheme in `tools/deploy_sports_files.sh`
- Line 96, 130: `curl --user "$FTP_USER:$FTP_PASS" "ftp://ftps2.50webs.com/..."` — host name says `ftps2` but URL scheme is `ftp://`. Control channel sends credentials in cleartext.
- **Action:** verify 50webs supports `ftps://` with `--ssl-reqd --ftp-ssl-control`. If yes, switch the URL scheme. If no, switch to SFTP/SCP.

### ⚠️ [sports-C6] Deploy creds read from unprotected `C:\windows_env_backup_2026-04-14.md`
- `tools/deploy_sports_files.sh:38-42` greps FTP_USER/FTP_PASS out of a Windows-rooted markdown file.
- **Action:** move to `~/.config/torontoevents/ftp.env` (or Windows DPAPI vault). Refuse to start if creds aren't found in env or the protected location.

### ⚠️ [sports-C8] Single static API key `livetrader2026` gates all write endpoints
- Hardcoded in `sports_picks.php:13`, `sports_bets.php:14`, `sports_odds.php`. Leaks via PR descriptions, Cerebras consult logs (`reports/consult_cerebras_*`), and CI workflow YAML.
- Gates: `analyze`, `daily_picks`, `settle_picks`, `auto_place`, `void_pending`, `inject_fallback`. Any reader can corrupt WR/ROI display, place arbitrary stakes, or inject fake odds.
- **Action:** replace with per-action HMAC or long random env-sourced key. Rotate. Switch write actions to POST + IP allow-list.

### ⚠️ [sports-C7] LIKE-wildcard passability via `sport=%` parameter
- `sports_picks.php:589`, `sports_bets.php:445`, `sports_value_analyze_lib.php:217` — `$sport` is escaped against direct injection but not against `%`/`_` wildcard chars used in LIKE predicates.
- Combined with C8's universal write-key, a single GET like `?action=auto_place&sport=%&key=livetrader2026` could over-match and mass-place bets.
- **Action:** validate `$_GET['sport']` against a fixed allow-list (the `_sportsAvailable` array already exists in the file); also `addcslashes($s, '%_')` before escape on LIKE predicates.

---

## High findings (track in followup PR)

| ID | Area | File | Issue |
|---|---|---|---|
| audit-H1 | finance | `tools/data/feed_risk_metrics_2026_04_20.json:265-280` | Cached artifact ships literal `NaN` tokens; browsers reject. Regenerate via `python tools/feed_risk_metrics.py` (which has `_json_default`). Same class as PR #441. |
| audit-H2 | finance | `tools/feed_risk_metrics.py:264-280` | DSR/PSR computed off **gross** PnL despite "net drives gate" decision in PR body. Reader assumes net-aligned. |
| audit-H3 | finance | `tools/hf_stats.py:455-461` | `_variance_ratio(early, late)` evaluated twice in OR-chain; report uses rounded value but alert uses raw — boundary cases produce inconsistent dashboards. |
| audit-H4 | finance | `tools/hf_stats.py:178-180` | Sortino denominator is `len(pnls_capped)` not `len(downside)`. Inflates Sortino ~1.5× at WR=43%. |
| audit-H5 | finance | `tools/hf_stats.py:154` | Unconditional `±50%` PnL clip distorts CVaR for crypto/equity tail. Detect series type or log cap-hit count. |
| audit-H6 | finance | `audit_trail/feature_edge_analyzer.py:248-249` | Skipped-cols allowlist contains the same names being tested for existence — pre-migration DBs silently get empty results. |
| sports-H1 | money | `live-monitor/api/sports_picks.php:172, 300` | `'win_probability' => 100/best_odds` is implied-with-vig, not a win prob; UI labels it as the latter. |
| sports-H2 | safety | `live-monitor/sports-betting.html` (lines 1568, 1578, 1612, 1621, 1641, 1660, 2455-2458, 2343) | Team / book / outcome names from external scrapers concatenated into `innerHTML`. `escHtml()` exists but isn't called on the main pick grid. Mass-rewrite needed. |
| sports-H3 | UX | `live-monitor/sports-betting.html:2832` | Wilson CI on WR doesn't gate the ROI headline; 0-WL cells render misleading `+164%` numbers on n=3 samples. |
| sports-H4 | safety | `live-monitor/api/sports_odds.php:217-220` | `inject_fallback` accepts arbitrary odds with no bookmaker allow-list. Combined with C8, fake +EV pipeline. |
| sports-H5 | money | `live-monitor/api/sports_bets.php:510-544` | `auto_place` gates on stored `true_prob` without external sanity check; can be poisoned via H4. |
| sports-H6 | money | `live-monitor/api/sports_bets.php` aggregator | `cell.wins/losses` not asserted to reconcile against `bets` total — Wilson CI on inconsistent counts. |
| sports-H7 | safety | `live-monitor/api/sports_value_analyze_lib.php:216-227` | Per-sport workflow expires future bets *before* refilling — non-transactional. Mid-run crash → empty dashboard. |

---

## Medium findings (informational)

Captured in the per-area review reports at:
- `%TEMP%\review_audit.md` (M1–M6)
- `%TEMP%\review_sports.md` (M1–M6)
- `%TEMP%\review_events.md` (M1–M3 + N1–N10)

Highlights:
- PR #427's TP percentile change (p75→p60) shipped without shadow-mode rollout — no a-priori rollback signal.
- PR #426's Wilson CI is **mathematically correct** but the headline number on small-n cells should be CI-low rather than ROI.
- PR #443's `statusBadge` fix doesn't HTML-escape `s` — defensive XSS hardening opportunity (today the `status` enum is server-controlled, so risk is theoretical).
- PR #394 net-added 0 events to main (the cron pipeline had already ingested them); the "+15" claim in the PR body is misleading.
- PR #428 smoke test validates the JSON payload but doesn't assert UI safety properties (no `target=_blank`/`noopener` check, no event-card render check).

---

## Confirmed clean

- **PR #436** (FTP-deploy `if: always()` + unshallow guards) — correct pairing for freshness-over-consistency trade-off.
- **PR #443** (statusBadge `undefined` leak fix + unshallow guards) — guard pattern is the GitHub-recommended idiom; only the defensive XSS is missing.
- **PR #427** (TP p75→p60 + ML-1 silent error logging) — `except Exception as _score_err: logger.warning(...)` is the right surface change. Tests pin the new constant + the operative path.
- **PR #429** (sports `AWAITING GRADE` pill + CI auto-comment with last-known-good revert) — solid operational hardening. The 3-hour heuristic for `is_finished` is a reasonable stopgap.
- **PR #426** Wilson CI formula is correct (`z=1.959964`, continuity-corrected, properly clamped). Honesty issues are about presentation, not math.
- **PR #425/#423** `tools/deploy_sports_files.sh` — covers the right files; the security issues are credential-handling, not deploy logic.

---

## Followup workstreams (suggested ordering)

1. **Today:** rotate every secret called out in C4/C5/C6/C8 (in parallel with the code-fixes PR landing).
2. **This week:** open a sports-XSS PR for H2 (escHtml across all innerHTML sites in `sports-betting.html`).
3. **This week:** open audit-H1 PR (regenerate `feed_risk_metrics_2026_04_20.json` and add a CI sanity check that `json.loads()` accepts it without `allow_nan=True`).
4. **Next sprint:** audit-H2/H4/H5 (gross-vs-net PSR/DSR; Sortino denominator; unconditional clip in `compute_hf_metrics`).
5. **Next sprint:** sports-H4 (`inject_fallback` bookmaker allow-list + per-IP rate limit) and H7 (transaction-wrap the per-sport expire-then-refill).
6. **Sometime:** `kimi_riseoftheclaw` numbers in `docs/AUDIT_DASHBOARD_ASSET_CLASS_TWEAKS_2026_04_27.md` — the recent_closed slice (56.5% WR / +296% PnL on n=283) is not representative; the full ledger at `KIMI_RISEOFTHECLAW/data/closed_picks.json` is 994 picks at 28% WR / -558% PnL, which validates the registry's UNTRUSTED tag on the merits. (Per Copilot agent investigation, 2026-04-27.)

---

## Reviewer setup

```
Audit subagent     →  /tmp/review_audit.md   (3 Crit / 6 High / 6 Med + Notes)
Sports subagent    →  /tmp/review_sports.md  (9 Crit / 7 High / 6 Med + Notes)
Events subagent    →  /tmp/review_events.md  (0 Crit / 0 High / 3 Med + N1-N10)
```

Each agent worked from `gh pr view <num> --json files,title,body` plus `gh pr diff <num>`, plus reads of the current file state on `origin/main`. No agent ran the dashboard generator locally (per CLAUDE.md). Findings cross-checked against `MEMORY.md` for prior-incident pattern matching.
