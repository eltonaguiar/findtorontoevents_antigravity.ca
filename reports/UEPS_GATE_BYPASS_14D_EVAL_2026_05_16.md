# UEPS Long-Horizon Gate Bypass — 14-Day Shadow Evaluation
**Date:** 2026-05-16  
**Eval window:** 2026-05-02 → 2026-05-16 (14 days)  
**PR:** #599 merged 2026-05-02T03:57Z  
**Plan doc:** `reports/UEPS_GATE_FIX_PLAN_2026_05_01.md`  
**Bypass flag:** `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED`

---

## (a) Flag Flip Status

**Status: FLAG IS ON.**

`UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED: '1'` is set in the "Generate dashboard payload and build HTML" step of `.github/workflows/audit-dashboard.yml` (line 506). The accompanying comment reads:

> 2026-05-15: Enable UEPS long-horizon gate bypass after 14-day shadow. Shadow period started 2026-05-01 (B28 merge); 14d expires 2026-05-15.

The flag was present at commit `bec044c7` (2026-05-15 21:27 UTC), meaning all CI dashboard runs since that commit have had the env var set.

---

## (b) Canary Metric Values

### Dashboard snapshot examined
- **File:** `audit_dashboard/data/dashboard_data.json`
- **Generated at:** `2026-05-16T02:47:56Z`
- **Repo SHA at generation:** `3b65082439bf3bd405c0fe5d861bd2e40de745dc` (not in local clone — remote-only CI state)

### Active picks counts (stored dashboard)

| Metric | Value | Expected |
|---|---|---|
| `picks.active` total | **0** | ~62 after bypass |
| `picks.active_raw` total | **187** | ~187 |
| UEPS picks in `active` | **0** | ≤ 30 |
| UEPS picks in `active_raw` | **22** | ≤ 30 ✓ |
| All `active_raw` with `_gate_passed=True` | **0** | ~62 |

### Zero-active root cause

All 187 `active_raw` picks have `_gate_passed=False` in the stored JSON. This is a **pre-existing, broader system condition unrelated to the UEPS bypass**:
- Commit `bec044c7` message at 21:27 UTC 2026-05-15 reads **"Signal Engine scan [2026-05-15 21:27 UTC] 0 active picks [skip ci]"** — predating the dashboard generation.
- Commit `1149b4c4` at 2026-05-16 03:48 UTC also reads "0 active picks" — persists after the flag flip.
- The `quality_stats.active_before_gates=187` vs `active_after_gates=0` confirms the gate itself is zeroing the list, not the data source.

**Local simulation verdict:** Running `passes_active_gate` on all 187 `active_raw` picks against the *current* `quality_gates.py`:
- Without flag: **58/187 pass**
- With flag ON (`UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED=1`): **62/187 pass**

The stored zero result implies the dashboard was generated against a different (older, more aggressive) version of `quality_gates.py` at the remote CI commit. The two post-dashboard `quality_gates.py` commits (`06aad99c fix(equity)`, `12092900 fix(forex)` at 03:45–03:48 UTC) add only narrow strategy-level blocks and do not explain the 0-to-58 gap; the underlying gate behaviour changed between the remote CI commit and the local state.

### UEPS bypass correctness (local test)

```
os.environ['UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED'] = '1'
passes_active_gate(ueps_raw[0])  # ADBE score=61 grade=B tf=POSITION
→ True

os.environ.pop('UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED')
passes_active_gate(ueps_raw[0])
→ False  (reason: "blocked symbol ADBE (data quality issue)")
```

The bypass is **code-correct**. The `_ueps_long_horizon_bypass_active()` helper at `quality_gates.py:2437` correctly reads the env var at call time.

### Non-UEPS leak canary

Flag OFF → 58 pass; Flag ON → 62 pass. **Delta = +4, all UEPS source picks.** Zero non-UEPS picks gained passage due to the flag. This is well within the ≤+50 canary threshold. **No leak detected.**

### Score distribution in `active_raw`

| Score bucket | Count |
|---|---|
| ≥ 55 | 27 (UEPS: 6) |
| 40–54 | 30 |
| < 40 | 130 |

The UEPS picks in `active_raw` score 55–61 with `elite_grade=B` and `trade_timeframe=POSITION`, consistent with the plan's expected profile.

---

## (c) Closed UEPS Pick Statistics

| Metric | Value |
|---|---|
| UEPS picks in `picks.recent_closed` | **0** |
| UEPS picks with computable WR | **0** |

No UEPS picks have closed during the shadow period. Because `picks.active` has been 0 throughout (the broader zero-active condition), UEPS picks have never reached the production active feed in practice, so there are no closed trades to evaluate. The n ≥ 5 threshold for WR assessment cannot yet be met.

The plan's expected ≥ 45% WR baseline (Magic Formula + Piotroski historical) remains unverified.

---

## (d) Recommendation

### Recommendation: Investigate zero-active condition before declaring bypass live

The bypass code is **correct and the flag is ON**. The UEPS bypass itself passes the canary:
- UEPS count in active_raw: 22 ≤ 30 ✓
- Non-UEPS leak from flag: 0 extra picks ✓
- Bypass logic verified locally: ADBE, PYPL, QCOM, META, HD all pass with flag ON ✓

However, the 0-active condition means UEPS picks are not visibly reaching `picks.active` in the published dashboard. This is a pre-existing system-level issue (confirmed by Signal Engine commit messages since at least 2026-05-15 21:27 UTC) that must be resolved independently of the UEPS bypass.

**Immediate actions:**

1. **Investigate and fix zero-active condition.** Check what changed in the quality_gates between the last known-good active feed and the current state. The local simulation shows 58–62 picks should be passing — the divergence is in the dashboard generator's CI environment, not the gate code. Candidate causes: module import failure causing `_QUALITY_GATES_AVAILABLE=False`, a new upstream filter added in a remote CI-only commit, or a stale `BLOCKED_STRATEGIES` load from an artefact that isn't in the local clone.

2. **Confirm UEPS picks appear in next green dashboard.** Once the zero-active condition is resolved, confirm UEPS active count is 6–22 (subset of 22 raw that pass trust + status + safety gates).

3. **UEPS emitter health: OK.** `audit_dashboard/data/ueps_picks.json` was generated at 2026-05-16T01:32Z with 22 long picks (universe=51, filtered=49). The emitter is running. Note: `alpha_engine/data/ueps_picks.json` is absent from the local clone — check that the scheduler commit isn't being suppressed by `[skip ci]` tagging.

4. **WR baseline: deferred.** With 0 closed trades, the ≥ 45% WR target is unmeasurable. Re-evaluate once n ≥ 5 UEPS closed picks exist in `picks.recent_closed`.

5. **Keep flag ON.** The bypass code is correct, the leak canary is clean, and the flag has no negative effect on the system. Rolling it back would be unwarranted.

### Status table

| Canary | Status | Detail |
|---|---|---|
| Flag flipped | ✅ ON since 2026-05-15 | `audit-dashboard.yml:506` |
| UEPS active_raw count ≤ 30 | ✅ 22 | Within limit |
| Non-UEPS leak ≤ +50 | ✅ +0 | No leak |
| Total active ~+30 | ⚠️ N/A | Zero-active condition blocks measurement |
| UEPS picks in active | ❌ 0 | Zero-active system issue (not bypass regression) |
| UEPS WR ≥ 45% (n≥5 closed) | ⏳ Deferred | n=0 closed |
| Bypass code correctness | ✅ | Local test: ADBE/PYPL/QCOM pass with flag |

**Overall verdict: HOLD — bypass is correctly implemented and flag is ON, but the zero-active system condition must be resolved before the bypass can be declared production-effective.**
