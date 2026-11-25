# Handoff + Deployment Plan — Trader-Skill Edge Programme

> **SUPERSEDED FOR STATE — see `reports/HANDOFF_FINAL_2026-11-24.md`.**
> This document's four-phase plan is still correct and still the operating plan. The FINAL document
> supersedes it for current state, exact hypothesis status, and the trap list. Read FINAL first.

**Date:** 2026-11-24
**Author:** GitHub Copilot (autonomous; user unavailable during the session, instructed to proceed and make good decisions)
**Scope:** the two live workstreams — (A) verifiable trader-skill persistence on Hyperliquid, (B) the
analyst-ratings up-only programme.

---

## 0. Read this first: what is and is not proven

| claim | status | evidence |
|---|---|---|
| Ranking of Hyperliquid traders **persists** out-of-sample | **measured, exploratory** | ρ = +0.376, CI [+0.248, +0.493], p = 0.0002, n = 293 (H-260) |
| That persistence is **skill** | **NOT established** | market-beta confound is open and untested |
| Any of it is **deployable / profitable** | **NOT established** | magnitudes are non-replicable; no forward data |
| The leaderboard's `accountValue` is equity | **FALSE** | median 0.098× live; 52% of wallets hold $0 perp equity |
| The seed wallet list is real | **FALSE** | 23 of 113 fabricated; 7 not valid addresses |
| The analyst up-only floors are reachable | **YES** | 300 already met; 500 needs ~349–392 tickers; 750 needs ~523–849 |

**Nothing here should be described as an edge, a strategy, or a signal.** The honest sentence is:
*trader ordering persists; we do not yet know whether that is skill or exposure.*

---

## 1. What was completed (the todo list)

| # | todo | outcome |
|---|---|---|
| 1 | Quarantine fabricated wallet universe | **DONE** — `seed_quarantine.py` + 20 passing tests + `fabricated_seeds.json` |
| 2 | Settle objective | **DONE (assumed)** — paper-validate → small real position gated on pre-registered OOS |
| 3 | Rebuild universe from live leaderboard | **DONE** — 46,603 wallets, sha256 `5b0ace6599cf…` |
| 4 | Verify wallets | **DONE on a sample** — 60 wallets; the field itself failed (see §0) |
| 5 | Pre-register OOS hypothesis | **DONE** — H-258 (invalidated), H-259 (blocked), H-260 (exploratory) |
| 6 | Positive control that can say YES | **DONE** — ρ = 0.2743 on injected skill; gates every verdict |
| 7 | Run split-period rank-IC test | **DONE** — H-260 pilot, n = 293 |
| 8 | Test recommendation-agreement vs win rate | **DONE EARLIER** — Track C: AGREE = 0, DISAGREE = 0 (0 joinable events; 51 covered picks all June-2026 vs analyst history from 2026-08-01) |
| 9 | Attach forward clock + promotion path | **DONE** — `hl_forward_clock.py`, snapshot 1 taken, gate reports CLOSED |
| 10 | Decide what to publish vs keep private | **DONE** — see §5 |

---

## 2. Deliverables and their exact locations

**Committed**
- `antigravity_review_Nov192026@d84888e` → `42_HARVEST_UPGRADE_2026-11-24/tracker/up_only_scaling.md`

**Written, NOT yet committed** (operator decision needed — see §5)
- `copy_trader_intel/seed_quarantine.py` (+ `test_seed_quarantine.py`, `fabricated_seeds.json`)
- `copy_trader_intel/hl_skill_persistence.py` (H-258, invalidated — kept as the record of the failure)
- `copy_trader_intel/hl_persistence_v2.py` (H-260 pilot, measured denominator)
- `copy_trader_intel/hl_forward_clock.py` (+ state in `reports/hl_clock/`)
- `reports/HL_TRADER_SKILL_PERSISTENCE_2026-11-24.md`
- `reports/hypothesis_registry.json` (H-258 → DATA_INVALID, H-259 → BLOCKED, H-260 → EXPLORATORY)
- `reports/hl_leaderboard_snapshot_20261124T220111Z.json`

**COMS topics (retained)**
- `notes/copilot-up-only-scaling-recommendation-2026-11-24`
- `notes/copilot-hyperliquid-skill-warning-and-recommendations-2026-11-24`
- `notes/copilot-reply-to-ghcopilot-hyperliquid-corrections-2026-11-24`

---

## 3. Deployment plan — four phases, each with a gate

### Phase 0 — Data integrity (COMPLETE)
- `seed_quarantine.py` proves the defect and gives a filter. **20/20 tests pass.**
- Corrected counts: **23 of 113 seeds rejected; all 23 carry sequential hex; 7 are also the wrong length.**
- The two defect classes **overlap** (the short ones are also sequential) and are now reported as
  non-exclusive counts so neither hides behind the other.
- **Wiring not yet done:** `hyperliquid_scraper.py` does not call `filter_seeds()`. It is an opt-in
  sidecar with a wiring plan, per repo policy. Until wired, treat that file's seeds as unusable.

### Phase 1 — Full measured-denominator pull (READY, ~20 min)
```bash
python3 copy_trader_intel/hl_persistence_v2.py 8820
```
- Pulls `portfolio` history for the full eligible set; computes rank-IC on a **measured** equity
  denominator.
- **Gate:** positive control must PASS first (it runs automatically). If it fails, harness is BROKEN
  and no verdict is issued.
- **Expected outcome:** a tighter CI than the n=293 pilot. Still exploratory unless step 5 is repeated.

### Phase 2 — Close the beta confound (the decisive test)
- Bucket wallets by **net exposure** (`sum(signed positionValue) / equity`) from `clearinghouseState`,
  then compute rank-IC **within** each bucket.
- **Prediction if the effect is skill:** persistence survives in the *low*-exposure bucket.
- **Prediction if the effect is beta:** ρ is flat across exposure buckets.
- **Gate:** must be pre-registered as a new hypothesis (H-261) **before** running.
- **Blocker found today:** most large accounts are flat or are spot/vault accounts at any instant, so
  a single spot-check is a weak exposure proxy. Use exposure sampled at the **prior boundary**, not now.

### Phase 3 — Forward clock (RUNNING, ≥7 days)
```bash
python3 copy_trader_intel/hl_forward_clock.py            # take a snapshot (skips if <1h)
python3 copy_trader_intel/hl_forward_clock.py --status   # report / promotion gate
```
- Snapshot 1 taken `20261124T223736Z` (46,603 wallets, sha256 `5b0ace6599cf…`).
- **Promotion gate: CLOSED — 7.00 more days required.** The script enforces this itself, so the rule
  cannot be forgotten the way the old programme's forward-observation requirement was.
- **Gate:** ≥2 snapshots ≥7 days apart AND the later one reproduces ρ > 0 with a CI excluding zero.

### Phase 4 — Capital (GATED, do not enter yet)
Only after Phases 2 and 3 both pass:
1. **Paper** copy-trade 20–30 wallets from the validated bucket for ≥4 weeks, with per-wallet position
   sizing and a hard drawdown stop — the 7–14% blowup rate measured today is the reason sizing matters
   more than selection.
2. **Small real** position only after paper reproduces positive expectancy net of fees.
3. Never size on the median/trimmed-mean ROI figures alone: ROI on near-zero equity is unbounded, which
   is why the top-decile **mean** had to be discarded (−12,148%).

---

## 4. Analyst-ratings track (second live workstream)

**Recommendation: continue.** Documented at `42_HARVEST_UPGRADE_2026-11-24/tracker/up_only_scaling.md` (committed).

- Floors: **300 already met** (BofA 439 clean events at 306 tickers). **500** needs ~349 (linear) to
  ~392 (sublinear). **750** needs ~523 to ~849.
- **Depth lever is exhausted** (14.93 years already collected; ~8.4 more years needed by waiting).
- **Next action:** one collector run to ~520 tickers (~3 min at 0.25 s/symbol). This clears 500 under
  every assumption and 750 under linear scaling.
- **Gate:** publish the MDE (1.39% at sd = 12%, ~1.5% after the 1.13 design effect) with any null.

---

## 5. Publish vs keep private — operator decisions

| item | recommendation | why |
|---|---|---|
| Fabricated-seed finding | **PUBLISH** (already on COMS) | Other agents are citing that file as a reference implementation. |
| `accountValue` ≠ equity | **PUBLISH** (already on COMS) | Anyone ranking by that field is ranking by a 10×-wrong number. |
| H-260 persistence ρ = 0.376 | **PUBLISH AS EXPLORATORY**, never as "skill found" | It has a working positive control and an honest label; suppressing it would be worse. |
| Any ROI/return magnitude | **DO NOT PUBLISH as a return** | Non-replicable; the mean is arithmetically meaningless. |
| Fabricated wallet *addresses* themselves | **safe to publish** | They are invalid/nonexistent accounts; no privacy issue. |
| Trader wallet addresses in the snapshot | **keep private for now** | Public on-chain, but republishing a ranked list invites being read as a recommendation. |

---

## 6. Named-file register (what to read, in order)

1. `reports/HL_TRADER_SKILL_PERSISTENCE_2026-11-24.md` — the full narrative and all measurements.
2. `reports/hypothesis_registry.json` → H-258 / H-259 / H-260 — pre-registrations and honest states.
3. `copy_trader_intel/seed_quarantine.py` — the quarantine, executable.
4. `copy_trader_intel/hl_persistence_v2.py` — the corrected test.
5. `copy_trader_intel/hl_forward_clock.py` — the clock and promotion gate.
6. `42_HARVEST_UPGRADE_2026-11-24/tracker/up_only_scaling.md` — the analyst-breadth answer.

---

## 7. Risk register

| risk | severity | mitigation |
|---|---|---|
| ρ = 0.376 is market beta, not skill | **high** | Phase 2 exposure-conditioned test; do not deploy before it |
| Copying high-ROI wallets copies leverage | **high** | 7–14% blowup rate measured; size per wallet, hard stops |
| `accountValue` still used somewhere downstream | medium | grep for `accountValue` before any ROI computation |
| `hyperliquid_scraper.py` seeds still in use by peers | medium | COMS warning posted; filter exists but is not wired |
| Forward clock never accumulates a second snapshot | medium | script enforces the gate; needs a scheduled run (cron/GHA) |
| Phase-1 run returns a tighter CI that still cannot separate beta | medium | that is a legitimate NULL, and must be reported as bounded, not as failure |

---

## 8. What I would do next, in one line each

1. Wire `filter_seeds()` into `hyperliquid_scraper.py` (log the rejected count).
2. Schedule `hl_forward_clock.py` daily so the 7-day gate can actually open.
3. Pre-register H-261 (exposure-conditioned) **before** running Phase 2.
4. Run Phase 1 (full 8,820 pull) to tighten the CI.
5. Run the analyst collector to ~520 tickers.
6. Commit the uncommitted artefacts in §2 once the operator has reviewed them.
