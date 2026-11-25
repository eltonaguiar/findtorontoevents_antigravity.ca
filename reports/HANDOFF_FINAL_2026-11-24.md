# HANDOFF (FINAL) — Trader-Skill Edge Programme

**Date:** 2026-11-24
**Author:** GitHub Copilot (autonomous session; operator unavailable during execution)
**Supersedes:** `reports/HL_HANDOFF_AND_DEPLOYMENT_PLAN_2026-11-24.md` (phases/plan still valid; this
document is the authoritative state snapshot and the entry point)

---

## 1. TL;DR — what to believe, in four lines

1. **Trader ordering persists out-of-sample** on a measured-equity denominator: ρ = +0.374,
   CI [+0.325, +0.423], p = 0.0002, **n = 1,953**. The n = 293 pilot gave ρ = +0.376 with a CI of
   width 0.245; scaling to 1,953 held the point estimate and halved the interval (width 0.098).
   A positive control (ρ = 0.2743 on injected skill) proves the detector can return "yes".
2. **That is not yet skill.** A rank-IC of that size is equally produced by persistent directional
   exposure in a trending asset. The test that separates them (H-261) is registered but **blocked on
   a data problem**, not a compute problem.
3. **Nothing is deployable.** No capital, no signal, no strategy. No ROI magnitude from this workstream
   may be quoted as a return — the top-decile mean ROI was −12,148% and had to be discarded entirely
   because dividing by near-zero equity is unbounded.
4. **Two input fields were broken and are now guarded:** 23 of 113 hardcoded seed wallets are
   fabricated, and the leaderboard's `accountValue` is not account equity (~10× overstated).

---

## 2. Exact hypothesis status

| id | family | status | key numbers | what it means |
|---|---|---|---|---|
| H-258 | hl_trader_skill_persistence_oos | **DATA_INVALID** | ρ = +0.429 (CI .408–.450), n = 8,820 | Ran, then the ROI denominator failed an input check. **Retracted before external use.** Kept as the record of the failure. |
| H-259 | skill_persistence_exposure_conditioned | **REGISTERED_BLOCKED_ON_DATA** | — | Its exposure ratio used the same invalid field. Superseded by H-261. |
| H-260 | hl_persistence_measured_equity | **EXPLORATORY_RUN_BEFORE_PREREG** | n=293: ρ=+0.376 (CI .248–.493) · **n=1,953: ρ=+0.374 (CI .325–.423)** · top-decile median +8.94%, hit 61.5%, blowups 21.5% | Denominator fixed via the `portfolio` endpoint. Honest label: run to repair H-258, so it **cannot confirm** anything. The 6.7× larger sample reproduced the point estimate — but the two samples overlap the same universe, so this is a larger sample, not an independent replication. |
| H-261 | hl_skill_vs_beta_exposure_conditioned | **PRE_REGISTERED** (22:44:09Z) | — | The decisive test. Blocked: exposure must be reconstructed at the prior boundary, and a snapshot-now proxy is explicitly forbidden by its own kill rule. |

Registry: `reports/hypothesis_registry.json`, 143 hypotheses.

---

## 3. Artefact map

| path | size | committed? | what it is |
|---|---:|---|---|
| `copy_trader_intel/seed_quarantine.py` | 5,271 | **no** | Detector + filter for fabricated addresses. |
| `copy_trader_intel/test_seed_quarantine.py` | 3,099 | **no** | 20 tests, incl. negative control. **20/20 pass.** |
| `copy_trader_intel/fabricated_seeds.json` | 2,403 | **no** | Machine-readable rejection list. |
| `copy_trader_intel/hyperliquid_scraper.py` | — | **no (patched)** | Now calls `filter_seeds()` at the address-build site; logs rejections. |
| `copy_trader_intel/hl_skill_persistence.py` | 10,432 | **no** | H-258. Invalidated; retained deliberately. |
| `copy_trader_intel/hl_persistence_v2.py` | 6,677 | **no** | H-260 on the measured denominator. |
| `copy_trader_intel/hl_forward_clock.py` | 5,809 | **no** | Snapshot clock + promotion gate (enforced in code). |
| `reports/hl_clock/` | — | **no** | Clock state. Snapshot 1 = `20261124T223736Z`. |
| `reports/HL_TRADER_SKILL_PERSISTENCE_2026-11-24.md` | 7,282 | **no** | Full narrative + all measurements. |
| `reports/HL_HANDOFF_AND_DEPLOYMENT_PLAN_2026-11-24.md` | 10,042 | **no** | Phase plan (superseded for state, still correct for the plan). |
| `reports/hl_leaderboard_snapshot_20261124T220111Z.json` | 8,475,012 | **no** | Locked sample, sha256 `5b0ace6599cf1a69…` |
| `42_HARVEST_UPGRADE_2026-11-24/tracker/up_only_scaling.md` | 7,683 | **YES** — `antigravity_review_Nov192026@d84888e` | Analyst-breadth answer. |

**Everything in the main repo is uncommitted.** That is deliberate: the operator should review before
anything lands, and this repo carries other agents' dirty files that must not be swept up.

---

## 4. Running state at handoff

- **Phase 1 — COMPLETE (22:56Z).** `hl_persistence_v2.py 2000` finished in 692 s: **n = 1,953 usable**
  (47 failed/empty), ρ = **+0.374**, CI **[+0.325, +0.423]**, perm p = 0.0002, raw-PnL ρ = 0.557.
  Result: `reports/hl_persistence_v2_20261124T225603Z.json`. Top decile (n=195): median **+8.94%**,
  hit rate 61.5%, **blowups <−50%: 21.5%** (up from 13.8% in the pilot), mean again discarded.
  The blowup share rising with sample size is itself informative: the fat left tail is larger than the
  pilot suggested, which strengthens the case for per-wallet sizing before anything is copied.
- **Forward clock:** snapshot 1 taken. **Promotion gate CLOSED** (needs 2 snapshots ≥7 days apart and
  ρ > 0 reproduced). Cron installed to accrue daily: `20 8 * * *` with `flock`, logging to
  `reports/hl_clock/clock.log`. 13 crontab entries total; previous crontab backed up to
  `/tmp/crontab_backup_*.txt`.
- **Wiring verified behaviourally:** 113 seeds → **90 kept, 23 rejected**, all survivors structurally
  valid 42-char addresses; `py_compile` OK; suite 20/20.

---

## 5. The three traps that will bite the next person

1. **`accountValue` on the leaderboard is not equity.** Median(live perp equity / leaderboard value) =
   **0.098**; **52%** of wallets report ≥$10k while holding $0 perp equity; only **10%** reconcile
   within ±15%; the largest accounts are **spot/vault** accounts whose perp equity is legitimately 0.
   Also `week.pnl` disagreeed with 7-day `sum(closedPnl)` on half a sample, one **sign-flipped**.
   → Use `POST /info {"type":"portfolio","user":<addr>}` (`accountValueHistory` + `pnlHistory`).
   → **Never** rank or sample by `accountValue`.
2. **The seed list is poisoned.** `SEED_WALLETS` contains 23 fabricated addresses carrying vendor
   provenance labels (`nansen_smart_*`, `arkham_tracked_*`, `copin_top_*`, `inst_vault_*`). Three
   sampled fakes return `accountValue 0.0`; one returns **HTTP 422** (not an address); a real seed
   returns $20.35M. The filter now runs at the call site — **do not remove it**, and do not trust any
   downstream artefact produced before 2026-11-24 without re-checking which seeds it used.
3. **Exposure cannot be proxied by "positions right now".** Large accounts are flat or are vaults at
   any instant. H-261's kill rule forbids a snapshot-now substitute. Reconstruct exposure from position
   history at the prior-window boundary or leave the hypothesis blocked.

---

## 6. Next actions, in order, with commands

```bash
# 0. confirm state (no network)
python3 copy_trader_intel/hl_forward_clock.py --status

# 1. Phase 1 is DONE (n=1,953). Re-run only if you need the full 8,820:
python3 copy_trader_intel/hl_persistence_v2.py 8820    # ~50 min; do not pipe through tail

# 2. build the exposure history H-261 needs (the real blocker)
#    for a sample of wallets, pull per-wallet position history at the prior boundary,
#    NOT clearinghouseState-now. Then run H-261's bucketed rank-IC.

# 3. analyst-ratings track (independent, ~3 min)
cd ../antigravity_review/42_HARVEST_UPGRADE_2026-11-24/tracker
python3 collect_analyst_history.py --symbols <~520 tickers> --out analyst_actions.csv
#    then re-run 42_HARVEST_UPGRADE_2026-11-24/zoocode/up_only_breadth.py

# 4. after operator review, commit the §3 artefacts with explicit paths only
git add -- copy_trader_intel/seed_quarantine.py copy_trader_intel/test_seed_quarantine.py ...
```

---

## 7. Operator decisions still open

| decision | my recommendation |
|---|---|
| Commit the trader-skill artefacts? | Yes — they are the record, and the quarantine has tests. Commit with **explicit paths only**. |
| Publish H-260 (ρ = 0.376)? | Yes, **labelled exploratory**, never as "skill found". |
| Publish any return/ROI figure? | **No.** Magnitudes are non-replicable and the mean is arithmetically meaningless. |
| Publish the fabricated addresses? | Safe — they are invalid/nonexistent accounts. |
| Publish the ranked wallet list? | Not yet — on-chain public, but republishing a ranking invites being read as a recommendation. |
| Continue analyst-ratings work? | Yes — 300 floor already met; 500 is ~43–86 tickers away. |

---

## 8. Verification checklist (run these before trusting this handoff)

```bash
python3 copy_trader_intel/test_seed_quarantine.py                    # expect 20/20
python3 copy_trader_intel/seed_quarantine.py | head -8               # expect 113 / 90 / 23
python3 copy_trader_intel/hl_forward_clock.py --status               # expect gate CLOSED
python3 -c "import json;d=json.load(open('reports/hypothesis_registry.json'));\
print({h['id']:h['status'] for h in d['hypotheses'] if h['id'] in ('H-258','H-259','H-260','H-261')})"
cd ../antigravity_review_Nov192026 && git cat-file -e \
  origin/harvest-upgrade-42-2026-11-24:42_HARVEST_UPGRADE_2026-11-24/tracker/up_only_scaling.md
```

---

## 9. What I got wrong, so it is not repeated

- **Reported the seed defects as a partition** ("16 sequential + 7 invalid length"). Wrong framing: all
  23 carry sequential signatures, and 7 of those are *also* the wrong length. Now reported as
  non-exclusive counts so neither defect hides behind the other.
- **Ran H-260 before registering it.** It is labelled `EXPLORATORY_RUN_BEFORE_PREREG` because of it. That
  is the same discipline failure this programme keeps making, and the label is the only honest remedy.
- **Trusted `accountValue` long enough to compute a full result on it** (H-258). The result was real
  arithmetic on a wrong field. It was caught by checking the input rather than the output.
- **Piped a long run through `tail`**, which buffered all progress and made completion invisible. Do not
  pipe long runs.
