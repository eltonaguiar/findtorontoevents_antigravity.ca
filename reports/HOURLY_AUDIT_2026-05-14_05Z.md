# Hourly Audit — 2026-05-14 05Z

**UTC time:** 2026-05-14T05:13Z  
**Session:** Claude Sonnet 4.6 autonomous hourly check (1 of N)  
**Priority goal:** #1 — Phenomenal performance across all asset classes on /audit  
**Context refs:** Issue #685 (resolver rescope DONE), #686 (per-asset live attribution), #693 (EQUITY monitor — closed as completed 2026-05-13)

---

## 1. DASHBOARD REFRESH STATUS

- **Pull result:** `git pull --rebase origin main` — already up to date (main HEAD: c25c4021)
- **dashboard_data.json generated_at:** `2026-05-09T06:00:16Z` — **5 days stale**
- **Staleness note:** Hourly [skip ci] auto-push scans (gainer/conviction/live-picks) are landing on a detached HEAD, not advancing main. The dashboard_data.json on main is therefore from 2026-05-09. Recent 24h window is empty (0 picks) because all closed picks predate May 13.
- **recent_closed n:** 3,500 picks; date range spans to ~2026-05-09

---

## 2. PER-ASSET PF/WR — WINDOWED ANALYSIS

All window metrics computed from `picks.recent_closed` with `closed_at` as the trade-close timestamp, evaluated relative to 2026-05-14T05:13Z.

### 2a. asset_class_health (verdict-grade, authoritative post-resolver-v2)

| Class | PF | WR | Notes |
|---|---|---|---|
| CRYPTO | 1.41 | 48.4% | Up from 1.25 (pre-PR-#694 HYPEUSDT block) |
| EQUITY | 1.57 | 53.7% | T2 candidate; goldmine_6x kill (#692) reflected |
| COMMODITY | 3.97 | 67.2% | Strong; n still below 100 charter floor |
| ETF | 1.44 | 59.2% | Approaching T2; n→100 goal |
| BOND | 0.66 | 54.5% | Sub-floor n=11; monitor only |
| FOREX | 0.27 | 41.7% | Genuinely sub-floor; mutation protocol active |
| FUTURES | N/A | 0.0% | No active data |

### 2b. 24h window

| Class | n | WR | PF |
|---|---|---|---|
| (all) | 0 | — | — |

**Note:** Zero picks in 24h window. Dashboard data is 5 days stale; no picks closed between May 9 and today reach the recent_closed array on main. Baseline comparison (CRYPTO 24h PF 3.54) deferred.

### 2c. 7d window (May 7 – 14)

| Class | n | WR | PF | Baseline 7d | Delta |
|---|---|---|---|---|---|
| CRYPTO | 388 | 47.4% | 2.16 | 1.33 | **+0.83 ✅** |
| EQUITY | 11 | 54.5% | 2.93 | 0.87 | **+2.06 ✅** |
| COMMODITY | 6 | 100.0% | inf | — | n too small |
| ETF | 4 | 100.0% | inf | — | n too small |
| FOREX | 30 | 13.3% | 0.22 | 0.14 | +0.08 (still catastrophic) |

### 2d. 30d window (Apr 14 – May 14)

| Class | n | WR | PF | Baseline 30d | Delta |
|---|---|---|---|---|---|
| CRYPTO | 1,498 | 49.2% | 1.65 | 1.33 | **+0.32 ✅** |
| EQUITY | 107 | 62.6% | 2.87 | 1.41–2.18 | **above range ✅** |
| COMMODITY | 39 | 76.9% | 6.07 | — | Excellent; n<100 |
| ETF | 44 | 81.8% | 6.12 | — | Excellent; n<100 |
| FOREX | 370 | 13.5% | 0.25 | 0.97 (pre-#687) | -0.72 vs pre-fix (30d still contaminated by pre-#687 losses) |

### 2e. Key delta interpretations

- **EQUITY dramatic recovery:** 7d PF 0.87 → 2.93. Directly attributable to PR #692 (goldmine_6x_consensus kill). Issue #693 monitor goal satisfied — closed 2026-05-13 as completed. ✅
- **CRYPTO improvement:** 7d PF 1.33 → 2.16 and 30d 1.33 → 1.65. Post-PR-#683 (cftc_cot kill) + PR-#694 (quan_engine HYPEUSDT block) both contributing. Do not destabilize (per issue #686).
- **FOREX marginal improvement:** 7d PF 0.14 → 0.22, WR 10.7% → 13.3%. PR #687 (JPY-cross BUY rule fix) may be helping at the margin, but FOREX remains catastrophically sub-floor. Mutation protocol per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` remains active.
- **FOREX 30d degraded vs pre-fix baseline (0.97):** The 30d window still includes the large pre-#687 loss corpus; this is expected and not a regression signal.

---

## 3. PR TRIAGE

### Open PRs at session start
Only PR #1012 was open when this session began.

| PR | Title | Action |
|---|---|---|
| #1012 | fix(live-picks): remove inner datetime import causing UnboundLocalError | **Already merged** by eltonaguiar at 05:10Z — CI green (scan: success) |

**PRs merged by this session:** none (author self-merged #1012 before review was possible).

### HOLD set (#660, #658, #681, #661)
Not present in open PR list — all closed/rejected upstream. No action required.

### Author-rebased set (#669, #676, #608, #665, #644, #597, #615, #655)
Not present in open PR list — all merged or closed upstream. No action required.

---

## 4. MUTATION ANALYSIS — NEW FINDINGS

Run: `python3 tools/mutation_analysis.py --json` at 2026-05-14T05:12Z.

### 4a. Direction-flip kill candidates (meets n>=20 + WR<35% criteria)

| Strategy | Direction | WR | n | Status |
|---|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 14.7% | 163 | **P1 — needs 3+ AI consensus before kill** |
| `myfxbook_retail_contrarian` | LONG | 10.2% | 118 | **P1 — needs 3+ AI consensus before kill** |
| `quan_engine_swing` | LONG | 26.0% | 104 | **P2 — below 35% WR floor, direction mutation recommended** |

Pattern: all three match the direction-flip axis from `MUTATION_THREE_AXIS_PROTOCOL.md`. Recommended mutations:
- Block LONG direction only (not full strategy kill) via `BLOCKED_STRATEGY_SYMBOL_PAIRS` or direction-gate logic
- Do NOT auto-kill: requires 3+ AI consensus per CLAUDE.md constraints
- Post evidence to issue #686 for cross-AI review

Contrast (SHORT performance of same strategies, confirming direction flip is real):
- `ig_contrarian_sentiment` SHORT: 60.9% WR / n=46 — **keep**
- `myfxbook_retail_contrarian` SHORT: 46.2% WR / n=13 — keep (n small, monitor)
- `quan_engine_swing` SHORT: 60.0% WR / n=5 — keep (n very small)

### 4b. Symbol-block candidates (meets n>=20 + WR<35% criteria)

| Strategy | Symbol | WR | n | Status |
|---|---|---|---|---|
| `rapid_fire` | UUSDT | 0.0% | 34 | **P1 — symbol block candidate; add to BLOCKED_STRATEGY_SYMBOL_PAIRS** |
| `rapid_fire` | TAOUSDT | 5.6% | 18 | P3 — n<20, monitor at next cycle |
| `rapid_fire` | ESPUSDT | 0.0% | 5 | P3 — n too small |
| `multi_asset_copytrader` | SI=F, AMD, ZW=F | 0% | <10 each | P3 — n too small for kill |

`rapid_fire UUSDT` (n=34, WR 0%) meets all three kill criteria: (a) pattern matches existing symbol kills, (b) n>=20, (c) WR<35%. However, this is a symbol-within-strategy block, not a strategy kill — requires a dedicated PR against `audit_trail/quality_gates.py` BLOCKED_STRATEGY_SYMBOL_PAIRS. **Needs operator go-ahead before implementing.**

### 4c. No new strategy-level kills meeting full PF<0.5 + n>=20 criteria
The mutation tool does not output aggregate PF per strategy; direction/symbol breakdowns above are the actionable signals. Full strategy PF verification would require a separate closed-picks export.

---

## 5. ISSUE #685 COMPLIANCE

- Resolver rescope work: **DONE** (PR #684). No resolver code changes this session.
- Any PR claiming "widen re-resolve scope": auto REQUEST_CHANGES (none seen this cycle).
- Plan v2.1 fabricated stats (PF 5.81, ml_score 0.90, WINNER_FILTER): **REFUTED** — auto REQUEST_CHANGES on any citing PR (none seen this cycle).

---

## 6. SUMMARY TABLE

| Item | Result |
|---|---|
| Dashboard data freshness | **STALE** — 2026-05-09T06:00Z (5 days); 24h window empty |
| PRs merged this session | 0 (PR #1012 self-merged by author before this cycle) |
| New strategy kill findings | 4 (3 direction-flip + 1 symbol-block candidate) |
| EQUITY recovery confirmed | ✅ 7d PF 0.87 → 2.93 post-PR-#692 |
| CRYPTO improving | ✅ 7d PF 1.33 → 2.16 post-PR-#683/694 |
| FOREX status | ⛔ 7d PF 0.22, WR 13.3% — mutation protocol active |
| Issue #693 status | ✅ Closed 2026-05-13 (EQUITY monitor complete) |

---

## 7. RECOMMENDED NEXT ACTIONS

1. **Fix dashboard_data.json staleness** — investigate why hourly [skip ci] scans land on detached HEAD instead of advancing main; without this fix, the 24h window metric will remain dark.
2. **rapid_fire UUSDT symbol block** — n=34, WR=0%: operator approval needed, then PR against `audit_trail/quality_gates.py`.
3. **ig_contrarian_sentiment + myfxbook_retail_contrarian LONG blocks** — post evidence comment to issue #686, await 3+ AI consensus.
4. **quan_engine_swing LONG direction** — mutation analysis in sandbox (n=104, WR=26%); if SHORT-only confirms edge, block LONG.
5. **COMMODITY/ETF n→100** — both strong (PF 6+) but below charter floor; no kills needed, just volume growth.
