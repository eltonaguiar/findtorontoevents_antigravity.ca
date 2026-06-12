# PLAN_INSIGHTS_CLAUDE_June122026_250pm.MD

**Agent:** Claude (Fable 5) · **Date:** 2026-06-12 ~2:50 PM EDT · **Scope:** the /thingstocheck_June2026 investigation + this session's full work ledger.
**Method:** every number below is direct-SQL or code-verified by me; peer/subagent claims were independently re-verified before inclusion (validation log in §6). Companion peer docs: `PLAN_INSIGHTS_CURSOR_June122026_638PM.MD` (+PR #562), `PLAN_INSIGHTS_NEMOTRON_JUNE122026_224PM.MD`, `BUFFY_MASTER_HANDOFF_JUNE122026.MD`.

---

## §1 THE ANSWER: is there a hidden edge buried in /audit's filters/tabs/buttons?

**No hidden *proven* edge exists in any filter combination — and we can now say that with evidence, not vibes.** The full surface inventory (8 surfaces traced to their data sources) shows every "edge-looking" preset is built on strategy-level aggregates, legacy trust stamps, or dashboard-composite scores — none on the honest intrabar ledger at symbol×direction granularity. The honest baseline is **0/9 classes Tier-2** (intrabar `at_signal_outcomes`, entry-anchored first-touch, SL-wins-ties).

What DOES exist (small, real, unproven-at-n):
| Candidate | Honest stats | Status |
|---|---|---|
| `luxalgo_confluence × CRYPTO × SHORT` | WR 71.1% / PF 2.21 / n=38 | PROBATION — **blocked by 0 emitter picks** (Cursor P0-1) |
| **CRYPTO SHORT as a side** | WR 55.8% / PF 1.36 / n=104 (dedup 57.8%/1.41, time-split 1.03/1.74) | forward-confirm candidate; the LONG side (30.1%, Σ−508.6%, n=1051) is the book's biggest leak → INCIDENT#23, P0C block in flight |
| `crypto_rsi5070_us` (entry condition) | 47.2%/1.535 n=108, last-30 retention holds | pre-registered gate at n≥150 ~Jun-25 |
| `forex_rsi2_mean_reversion` | 60%/2.15 n=20 | small-n watch (DNR for promotion at this n) |
| `forex_trend_aligned` (F1) | 68.8%/5.33 n=16 | accruing |
| `equity_gap_fade` (BUFFY backtest) | 66.7%/1.364 n=36 | fails monkey-P95 (1.380); near-miss, route via registry |

**Why months produced nothing:** (1) the scoreboard lied until June (inflated WR 23-24%); (2) losses are entry-selection losses — and the single biggest selection error is **being 100% LONG in CRYPTO + mega-cap tech with no short side and no regime filter**; (3) the real wins are PF 1.3-1.5-class and need disciplined accumulation (forward lanes + CI-lower-bound gates), not heroics.

---

## §2 VERIFIED ANSWERS to each operator question

- **gpt4_1 "55.6% WR" — TRUE as computed, NOT proven.** 20W/16L on 36 resolved; the leaderboard *correctly* excludes 75 MISPRICED_ENTRY rows. But its own CI is **[39.6%, 70.5%]** (spans coin-flip), n=36, and only **4 of 127 picks are API_GENERATED** (63 SYNTHETIC_SEED_ENRICHED + 24 COVERAGE_FALLBACK) — so it isn't even mostly the model's own picks. Do not size on it.
- **kimi_direct — same shape:** 29W/18L (61.7%) on 47 resolved + 47 MISPRICED_ENTRY excluded. The "single-snapshot resolver bias" was already mitigated by the re-resolution + MISPRICED_ENTRY quarantine; **recommendation: keep the data (don't nuke), it's correctly flagged** — what's missing is per-row intrabar replay for the OPEN cohort, not a restart.
- **ai-tournament "NOT MONEY-READY" labels — CORRECT and should stay.** They reflect the honesty banner (the 73-91% WRs were single-snapshot artifacts) + tiny resolved n per model. The page is working as designed.
- **picks-now 21.1% forward WR — three stacked causes (ranked):** ① *resolution artifact:* TP=2×SL geometry makes **33.3% the break-even WR**, and a touch-only denominator (the TIME_EXIT bug: `resolve_picks_now.py:99` assumes 24 bars/day so equities NEVER time-exit; 167/202 stuck OPEN forever) censors exactly where slow winners live — the panel benchmarks red-below-50% against the wrong null; ② *staleness:* the JSON froze 06-09 because the workflow called an unsupported `--apply` flag, crashing hourly under a `|| non-fatal` guard — **fixed this session (`7e9a4cade4`)**; ③ *genuine selection failure:* a 100%-LONG mega-cap-tech basket (643/643 STRONG_BUY) bought repeatedly into the June 9-11 selloff — losses hand-verified to the cent. Remaining fixes are freebuff handoffs (bars/day horizon, unique-symbol accounting, breakeven-aware display, short side/regime).
- **portfolio_history.html — STALE since 2026-05-25, RESURRECT (~half-day).** The 30-min cron is green but (a) state JSON is gitignored and never fetched → all 36 portfolios re-bootstrap from $10k every run, (b) FTP uploads only the HTML, never the JSONs. The "ton of losing portfolios" (~−89% compounded EW) is frozen pre-fix data compounded by the re-bootstrap bug — diagnose AFTER resurrection, not before.
- **ai_leaderboard.html only claude-opus-4.7 — resolver symbol-mapping gap.** 43 engines in the book, but `outcome_resolver_swarm._resolve_yf_ticker` only handles prefixed symbols; 302/309 open picks use bare symbols → silently skipped nightly. **Recommendation: one-shot retro-resolve (~15-line fix) of the frozen 340-pick archive, then merge the board into ai-tournament.html as a static section and retire the page** (the swarm book is decommissioned as of today).
- **pick_funnel.html — core JSONs fresh + honest; two defects:** the nav-surface matrix sidecar is 10 days stale (its builder soft-fails, masked) and the DISPUTED-row highlight regex misses concentration-flagged cells (the stale 76.9%-CRYPTO cell renders unstruck vs intrabar truth 32.4%).
- **research_index.html — healthy weekly cadence, honest (0 GO verdicts), but SHELF-WARE:** nothing in the pick path consumes it. Needs the P3-winner → hypothesis-registry bridge (Wire-Up Rule).
- **"FWD WR% shows strategy WR instead of strategy-symbol-direction" — root cause found:** the FWD WR column is strategy-wide *by design* (documented), but the Track stats that should carry the granularity are **DIRECTION-BLIND** — keyed on (strategy|source)+symbol only (`dashboard_generator.py:5495`). With LONG 30% vs SHORT 56%, that's materially misleading → **INCIDENT#136** filed with the key-shape fix.
- **Active/recently-closed picks: mostly losing.** 48h closed: CRYPTO 38.6% WR PF 0.88, FOREX 27.1%/0.54, FUTURES 33.3%/0.89; 14d EQUITY 47.0%/1.36 is the least bad. Consistent with 0/9.
- **Reverse-split/limit artifacts:** none found in the verified slices (prices hand-checked to the cent vs independent data; `reverse_split_affected` column exists and is used; MISPRICED_ENTRY quarantine catches the tournament's bad entries).

---

## §3 ACHIEVEMENTS (this session, all verified on main)

1. **Hourly honest-measurement chain fully unblocked** — root-caused + fixed + verified 3 consecutive green runs: P0A resolver died in `backup_rows()` (no backups creds on runner) `983413526f`; recency panels frozen 7d (tracked-but-unstaged → stash-reverted) `d2f56ae23f`; untracked archive merge-block `f2afe5773c`.
2. **kimi pollution purged:** NULL-timestamp dedup-bypass writer fixed `7dfc7ff0f6` + **141,344 rows purged** (backed up; verified 0 intrabar rows touched). Table 182,809→43,083 real rows.
3. **ACT-engine built + smoke-tested:** `tools/pf_ci_lower.py` (cluster bootstrap PF CI-lower-bound + n_eff) and `tools/replay_harness.py` (preflight→dedup→proven replay→costs→CI→R1→R2→monkey-P95→stress→verdict) — correctly ruled a random CRYPTO cohort NOT_ADMISSIBLE. `c0280e4b8d`/`c226b3b167`.
4. **Weekly loop cycle #1 executed** (hash-locked scorecard `8f84c2bff9`); registry rescue (36 local-only pre-registrations one push from loss) + H-111 pre-registered `41fbfa4d45`.
5. **Swarm paper picks decommissioned** per operator (`062ad473b5`): panel+payload+pipeline removed, book archived `_OLD`; insights extracted (LONG/SHORT asymmetry independently replicated; consensus tiers added NO edge; `losing_cell` negative-tag worked).
6. **Incidents/enhancements filed:** #21 #22 #23 #134 #135 #136, ENH#164 #165, FINDING#17 #18 — all SQL-verified before filing.
7. **picks-now track-record freeze fixed** `7e9a4cade4`; `/thingstocheck_June2026` skill+command committed to GitHub (secret-scanned: clean).
8. **CRYPTO-LONG block coordination:** validated the action, broadcast the REQUIRED forward-lane exemption to all peers via the gateway, stood down to avoid a two-agent collision on config.py/quality_gates.py.

## §4 TASKS REMAINING (priority order)

- **P0:** verify the peer's P0C LONG-block lands WITH the forward_test_only/shadow exemption · fix luxalgo SHORT emission =0 (Cursor P0-1) · P0B `is_emission_allowed()` central gate (closes #135's three blocklist scope-gaps incl. `regime_filter.py:474` default-allow).
- **P1:** retro-resolve the swarm book + merge ai_leaderboard into ai-tournament · resurrect portfolio_history (2 workflow additions) · direction-aware track keys (#136) · nav-surface matrix builder un-mask · freebuff handoff for picks-now resolver horizon/accounting/display.
- **Checkpoints (pre-registered, do-not-retune):** pead gate Jun-14 (judge payoff asymmetry, not WR) · FOREX n=95→100 verdict (~days) · rsi5070 n≥150 ~Jun-25 · handoff-LONG OOS Jul-9.
- **Hygiene:** 71.5% emission dup-rate (the promotion blocker) · #132 walk-forward refresh (blocks H2 scoring) · #14 UNKNOWN classifier · tracker file spam (ENH#165).

## §5 DEEP-DIVE AREAS

1. **Masked-failure audit of ALL workflows** — SIX instances found in one day (P0A creds, recency stash-revert, archive merge-block, picks-now `--apply`, nav-surface builder, portfolio-history state amnesia). Same shape every time: green check, frozen data, `|| non-fatal`. Deep-dive = a freshness-assertion harness (`generated_at < 2h` per critical JSON) wired into the weekly scorecard H1.
2. **CRYPTO SHORT structural question** — is the SHORT edge selection or falling-market beta? Needs regime-stratified replay (the harness now exists) before the Jun-25 gate.
3. **Tournament OPEN-cohort intrabar replay** — 798 OPEN tournament picks have entry/tp/sl; replaying them via the harness would 3-5× every model's resolved n and settle gpt4_1/kimi_direct properly.
4. **Growth-stock-screener concepts (starboi-63)** for picks-now: its relative-strength rank + liquidity/trend template + stage-2 filter are exactly the regime/selection layer picks-now lacks; implement as a pre-registered EQUITY entry-condition family, NOT another standalone screener.
5. **Research→production bridge** — research_index P3 winners into hypothesis_registry automatically.

## §6 PEER-CLAIM VALIDATION LOG (this session)

| Claim | Source | Verdict |
|---|---|---|
| CRYPTO LONG 30.1% Σ−503% / SHORT 55.8% | BUFFY | **CONFIRMED to the decimal** (−508.6 current) |
| gpt4_1/kimi "ZERO trades in honest ledger → pipeline failure" | nemotron | **HALF-RIGHT:** zero in at_signal_outcomes is by-design keyspace separation; tournament_picks has its own resolved+flagged cohort. "Pipeline failure" framing REFUTED |
| `forex_rsi2_mean_reversion` "blocked at 7.1%/0.09" | nemotron | **UNVERIFIED** — no provenance in their session; conflicts with intrabar 60%/2.15 n=20. Do not act on it |
| luxalgo refuted 42.4%/1.144 | nemotron | **SOURCED** (28d forward pilot n=953) — but direction-blind; the SHORT slice is the live probation candidate |
| FWD WR% "confirmed bug" | my Explore agent | **OVERCLAIMED** — by-design column; the real bug is direction-blind Track keys (#136) |
| picks-now `--apply` crash, TIME_EXIT 24-bars/day bug, prices-to-the-cent | my agent 3 | **CONFIRMED verbatim** (reproduced the argparse exit 2 live) |
| portfolio state amnesia + HTML-only FTP | my agent 2 | **CONFIRMED** (2 STOR lines, both HTML; state gitignored) |

**Bottom line for the operator:** the measurement layer is now trustworthy and self-sustaining; the book's biggest single fix (CRYPTO LONG block) is validated and in flight with guardrails; the honest path to "high certainty of a tiny profit" is the forward-lane CI-lower-bound discipline on the 4-5 small candidates above — n arrives in weeks (rsi5070 Jun-25, FOREX days, pead Jun-14), not months, now that the hourly chain works.
