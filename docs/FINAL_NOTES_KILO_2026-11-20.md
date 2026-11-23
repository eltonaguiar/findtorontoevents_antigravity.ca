# FINAL NOTES — kilo (deepseek-flash via Kilo extension, Linux)

**Written:** 2026-11-20T02:20Z · **Seat:** `inbox/gx10-c9b9/vanilla-handsaw/kilo`
**Source repo:** `eltonaguiar/findtorontoevents_antigravity.ca` @ `main` (`515591f5d45` at write time)
**Review package:** `eltonaguiar/antigravity_review_Nov192026`, folder
`artifacts/2026-11-19T2308Z_linux-kilo-ext_deepseek-flash/`

---

## 1. Bottom line

The measurement layer is now auditable and the forward clock has started. **Nothing is
money-ready**: 0 proven cells, 0 candidates, selection alpha −0.268 %/trade, and the two pods that
just started accruing hold 13 rows between them. This push was repair and measurement, not signal.

## 2. Live state at handoff

| Field | Value |
|---|---|
| `audit3_ledger.json` generated | **2026-11-20T01:57:23Z** |
| `provenance.id` | **b5363b282409b564** |
| population / scored | canonical / **8,769** rows (362 cells) |
| PROVEN / CANDIDATE / WEAK / KILL / INSUFFICIENT | **0 / 0 / 59 / 8 / 295** |
| selection alpha | **−0.2681 %/trade** |
| forward ledger | 430 live rows; **443 admissible** (13 new: faber_taa 12, etf_dual_momentum 1) |
| pods with forward rows | 2 (first time) |

## 3. What I changed (all on main)

### Measurement integrity
- `6abfa22364e` — G9 selection alpha at **strategy** scope, global DSR floor (658), source-family gating
- `1189ff4150d` — provenance triple (population, cost model, win definition) + `provenance_id` on every bucket
- `260df7f980f` — `dsr_n_trials` published on every bucket
- `33e41deca65` — CANDIDATE DSR falls back to the global value when local is uncomputable (peer-found bug)
- `1238e16d086` — four falsifier tests (provenance changes with denominator; −1 %/trade cannot promote; zero alpha cannot prove; DSR undefined at 1 trial)
- `94466c02b7b` — forward benchmark window extended past the exit (time-expiry rows were getting permanently NULL benchmarks)

### Forward clock
- `1a36da257e2` — `unmatched_top` diagnostics (made 3,321 orphan rows visible)
- `ff884c4cb37` — per-hypothesis watchdog + 7-day pod grace (pre_registered pods fail after grace)
- `8aee6f084fd` — `volume_ratio_at_entry` migration + **dry-run** backfiller (55–59 % fillable)
- `d5fd72b7575` (#979) — **pod emission audit CI gate**: 15 of 23 manifest strategies exist in no table

### Paper sleeves ($2k plan)
- `6448b582fe0` — `core-beta` (SPY, $1,400) live
- `57c1c0d11d2` — `etf-rotation` + random control + daily marks workflow
- `4ec5fd7089f` / `79b5de2be3f` — aligned to the validated 14-ETF, top-5, 189-day spec; lag-1d thesis corrected
- `622cc11174c` — `etf-hold`, the beta-matched control buffy required
- `docs/GRADUATION_RUNBOOK.md` — every gate before real money

### Security
- `032d88897d1` — re-enabled the repo's gitleaks gate (PR + daily) after the P0 credential branch

### Documents (all on main under `docs/`)
`AUDIT_SURFACES_FULL_REVIEW_2026-11-19.md` · `WHAT_WORKS_PER_ASSET_CLASS_2026-11-19.md` ·
`ALLOCATION_2000_AND_LIVE_SIM_PLAN_2026-11-19.md` · `REAL_MONEY_READINESS_AND_PEER_FRAMEWORK_2026-11-19.md` ·
`NEXT_PHASE_PLAN_2026-11-19.md` · `DESIGN_DEBATE_2026-11-19.md` (v1 consensus table) ·
`COMS_REVIEW_FEEDBACK_2026-11-19.md` · `WORK_PRESERVATION_AND_MERGE_POLICY_2026-11-19.md` ·
`VOLUME_CONTEXT_MIGRATION_APPROACH_2026-11-19.md` · `REVIEW_INDEX_KILO_2026-11-19.md` ·
`COLLABORATION_PROTOCOL_2026-11-19.md` · `WORK_ROLLCALL_2026-11-19.md` ·
`FINAL_MERGE_VERDICT_2026-11-19.md` · `B1_POD_STRATEGY_NAMES_FINDING_2026-11-20.md` ·
`POD_EMISSION_AUDIT_2026-11-20.md` · `GRADUATION_RUNBOOK.md` · `FINAL_NOTES_KILO_2026-11-20.md`

## 4. Corrections I made to my own claims

Recorded because a review that never corrects itself is not a review:

1. **"audit3 scores a payload slice (21.43 %)"** — the live ledger moved to canonical (58.84 %). The
   denominator changing between runs became the finding.
2. **PDT $25k repeal** — I flagged it as unverified; it is real (FINRA Notice 26-10, effective
   2026-06-04). My flag was withdrawn and my allocation doc patched.
3. **TAA 0.88 Sharpe** — the headline was unlagged; honest lag-1d is Sharpe 0.81/0.82 with CAGR
   *trailing* SPY. TAA is drawdown control, not excess return.
4. **"5/13 benchmark-unmeasured is correct missing-bar behaviour"** — wrong; the bars existed. The
   fetch window ended at the exit, so time-expiry rows got permanent NULLs. Fixed.
5. **"selection_alpha.available=false ⇒ G8 unreachable" (buffy's claim, which I initially repeated
   as plausible)** — false on the live ledger: available=true, n=3,185, alpha −0.268. Corrected.

## 5. Peer review status — 4 of 8 reviewed

| Peer | What I verified | Verdict |
|---|---|---|
| OpenCode (Windows) | P0 alert, 5 archive tags, protocol, debate votes, cross-check | Trustworthy; one merge claim corrected (`fix/audit2-3-p0-p1` is 552 behind) |
| FreeBuff | TAA 576-cell CSV, sector spec, $2k critique, per-class report | Good, unfinished (T16 ETA outstanding); one stale claim corrected |
| Kilo (Linux CLI) | PR #977 (4 new files, +192/−0, valid JSON, no secrets) | Approve after rebase; merged |
| GitHub Copilot | PR #962/#964, TAA lag repro, found my DSR fallback bug | Best process contribution; Hermes' F1–F3 still open |
| Hermes (Windows) | ACK, review tally, live_simulator on main | Accounted |
| Google Swarm / OpenCode console / KILO Desktop | none | **Not accounted for** |

## 6. Open blockers, with owners

| Blocker | Owner | State |
|---|---|---|
| 15 phantom manifest strategies | manifest owner | My CI gate flags them; TWO pods can accrue today (`etf_faber_tactical`, `etf_dual_momentum`) |
| 3,321 unmatched cohort rows | research/registration owner | ensemble 289, forex_rsi2 175, macd_rsi 150, volume_spike 142 … |
| P0 credential branch | operator | rotate the DB password, delete + purge `feat/audit-review-organization-2026-11-19` |
| Volume schema `--apply` | operator | sidecar (recommended) or ALTER; tooling ready, dry-run only |
| `materiality_floor_pct` / churn wiring | quant-validation owner | main still has 3 red tests |
| Main worktree dangling merge (`MERGE_HEAD 04e4862`) | owner of that worktree | snapshot at `/tmp/kilo_backups/mainrepo-merge/` |

## 7. Verify everything (copy-paste)

```bash
# 1. audit3 focused suite (expect 93+ passed on current main)
python3 -m pytest tests/test_audit3_tribunal.py tests/test_audit3_expectancy_gates.py \
  tests/test_audit3_edge_hunt.py tests/test_audit3_selection_alpha.py \
  tests/test_forward_observations_ingest.py tests/test_audit3_cost_basis.py -q

# 2. crash smoke test
python3 -c "import sys;sys.path.insert(0,'.');from alpha_engine.audit3_tribunal import build_report;\
print(build_report([{'id':'x','asset_class':'CRYPTO','strategy':'s','direction':'LONG','symbol':'BTCUSDT',\
'source_system':'a','status':'WON','pnl_pct':1.0,'closed_at':'2026-11-01T00:00:00+00:00'}]*30,'x.json',None)['cells'][0]['required_n'])"

# 3. CLI parses
python3 -m alpha_engine.audit3_tribunal --help >/dev/null && echo CLI_OK

# 4. phantom pods
python3 tools/pod_emission_audit.py --strict --out /tmp/pea.json; echo "rc=$?"

# 5. live provenance
curl -s https://findtorontoevents.ca/audit3/audit3_ledger.json | python3 -c \
 "import json,sys;d=json.load(sys.stdin);p=d['provenance'];c=d['cells'][0];\
print(p['id'],p['population'],c.get('dsr_n_trials'),c.get('provenance_id')==p['id'])"
```

## 8. What I would do next, in order

1. **Amend the manifest** to the real emitters and flip `pod emission audit` to `--strict`
   (2 pods can accrue immediately).
2. **Reconcile main's 3 red tests** (materiality/churn) — one owner, one worktree.
3. **Rotate the exposed credential** and delete the branch.
4. **Let the forward clocks run.** n≥200, net CI>0 at 2× cost, DSR≥0.95, beats *both* control arms:
   only then does the $2k allocation change from 90/0/10.
5. Only after that: the three pre-registered experiments (vol-target A/B, RVOL≥1.5 overlay,
   5 TP/SL configs — never 96).

*Not investment advice. No strategy, threshold value, or honest-verdict policy was relaxed; every
change made it harder to call something profitable.*

---

## 9. Addendum — 2026-11-20T04:00Z

**Main state:** `origin/main` passes **100 audit3/ingest/pod tests** (PR #983 cleared the last reds).

**Checks that came back clean or resolved:**
- **Coverage denominator — RESOLVED** (PR #984): live ledger reports `scored_rows` 8,769 =
  `valid_closed_picks` 8,769, `scored_share_of_valid_pct` **100.0**, status **ok** (was null),
  share_of_total 53.56 % of 16,372.
- **Retracted-claim sweep of the live pages — CLEAN.** `/audit`, `/audit2`, `/audit3` were grepped
  for the retracted TAA figures ("0.88", "MaxDD −19%"). `/audit` returned 5 matches, all unrelated:
  a `+0.88 %` row in a returns table and CSS colour thresholds. `/audit2` and `/audit3` returned 0.
  No page still cites the retracted claim.

**Changes after the original notes:**
- **TAA retraction applied to my own sleeve** (`a68aaad1a8c`): PR #986 retracted "Sharpe 0.88 /
  MaxDD −19 %" — 0/576 cells meet both bars at lag ≥ 1. The `etf-rotation` thesis now carries the
  honest lag-1d numbers (Sharpe 0.82 vs SPY 0.69, MaxDD −20.9 % vs −52.9 %, CAGR 8.94 % vs 10.79 %)
  and states it survives only as **drawdown control**. A test pins that no retracted number is
  presented as evidence.
- **Asset-class guard** (`1ffa3e393ea`): the pod emission audit now flags a strategy that emits only
  in asset classes its pod does not declare — the trap that three "breakout" names (CRYPTO/FUTURES/
  COMMODITY) would have sprung on the equity pod.
- **Equity signal core** (`1e2a93c2d18`): `tools/equity_breakout_candidates.py`, daily Donchian 20/10,
  2R target, **dry run only**, 5 tests. Live result: **0 candidates of 14 ETFs** — every one is
  2.6–11.2 % below its 20-day high (SPY −6.93 %, QQQ −10.25 %, GLD −11.18 %). A wired equity sleeve
  would be in cash today.
- **PR #987**: audit2 now shows the ledger's forward-gate reason per hypothesis.

**Live ledger at this addendum:** `03:56:27Z`, provenance `e9d53b2e6d0b0259`, 0 PROVEN / 0
CANDIDATE, alpha −0.2681; forward rows faber_taa 12, etf_dual_momentum 1, H-119 430.

**Unchanged conclusion:** repair and measurement, not signal. Nothing is money-ready.

### 9.1 Correction — FX (2026-11-23)

My earlier note that `fx_prices` ends 2026-02-09 and left 211 forex picks unmeasurable was wrong:
`stock_ohlcv` carries `AUDJPY=X` through 2026-11-23, and `trading_picks` holds **64,082** `=X` rows
with **46,249** open (`exit_price IS NULL`). FX is blocked by the **resolver** (entries never closed),
not by missing prices. Corollary: the FX/carry path can be unblocked with a resolver fix, which is
cheaper than procuring data.
### 9.2 Addendum — EQUITY drift and a second class table (2026-11-23)

audit3 now reports EQUITY **+0.106%/trade, PF 1.050, n=956, CI [−0.480, +0.693]** — down from +0.184 at
n=939 on 11-19. A peer's 505-row COD-cost table shows EQUITY −0.148% at n=8. Different populations,
same decision: **no class is investable; EQUITY is least-bad, not proven.** Do not fund on the point
estimate, and any EQUITY work must carry the CI and the drift.
### 9.3 Addendum — AUDJPY is UNRECONCILED, not a lead (2026-11-23)

I had called FOREX/AUDJPY LONG "the only cell whose net CI is entirely above zero" (n≈33, CI [0.242, 0.942]).
Three populations now disagree:

| Population | n | mean | median | notes |
|---|---:|---:|---:|---|
| `at_signal_outcomes`, all closed AUDJPY=X | **282** | **−0.37%** | −0.50% | wins 104/282; range −85.9% … +68.1%; trimmed mean −0.31% |
| audit3 symbol bucket | ~34 | +0.576% | – | DSR 0.815 |
| riseoftheclaw `signal_tracking` | 24 | −2.45% | −5.21% | 2 wins/24; one +142% dominates |

The **broadest** sample is negative. The positive bucket is a selected subset, so AUDJPY is
**unreconciled and not actionable** until the three populations are joined on pick id. This supersedes my
"only positive CI cell" statement; the correct reading is that bucket-level positivity can be selection.
