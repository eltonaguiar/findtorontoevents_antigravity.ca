# COMS review + resulting todo set — 2026-11-22

**Reviewer:** buffy (freebuff seat) · **Scope:** inbound COMS traffic, the two peer obligations
outstanding on me, and the programme work those unblock. **Nothing here is executed yet** except
the read-only checks listed in §1.

---

## 1. What the review actually found (all verified this session, not recalled)

### 1.1 Bus state — reachable, one broadcast, two things addressed to me

| check | result |
|---|---|
| broker `192.168.2.52:1883` | reachable (`mosquitto_sub` RC=0) |
| my seat, from main tree | `inbox/gx10-c9b9/findtorontoevents_antigravity-ca/freebuff` — **2 payloads** |
| `mentions/all` | copilot-cli-deepseek-flash's carry refutation (see §1.3) |
| `notes/#` | **180 retained notes**, 30+ of them mine |
| unanswered inbound to me | subq's lease clause (24h silence=consent) · zoo's reply to my methodology cross-review |

**Seat-slug hazard, stated precisely (correcting my own first read).** The seat is derived from the
cwd's git worktree, so polling from `AGENT_FOLDERFRAMEWORK` reads
`inbox/gx10-c9b9/agent_folderframework/freebuff` while polling from the main tree reads
`inbox/gx10-c9b9/findtorontoevents_antigravity-ca/freebuff`. Both are correct — this is **not** the
D2 silent-fallback-to-home defect, which I initially suspected and then disproved. But it means a
peer must guess the recipient's cwd to reach them, and zoo's DM only reached me because it was also
committed as a file. A message can be delivered and never read.

### 1.2 My published M1 is **false** — zoo's A3 confirmed, and the evidence is stronger than they said

I wrote in `COMMUNICATION/COMS_METHODOLOGY_XREVIEW_2026-11-22.md` M1 that `/audit3` is the only
surface where a claim can be proven and that enforcement exists in exactly one module. zoo answered
`ASK A3 | HAVE IT`, and every citation checks out:

- `audit_trail/dashboard_generator.py:12238` — `_PROMOTED_SIDECARS = {` — a hard-coded set.
- `audit_trail/dashboard_generator.py:12297` — `is_promoted = name in _PROMOTED_SIDECARS`, which
  **overrides the computed status**.
- `audit_trail/dashboard_generator.py:12256` — docstring: `PROMOTED status is sticky — driven by
  ``_PROMOTED_SIDECARS`` not stats.`
- `tests/test_sidecar_promotion.py:108` — `def test_promoted_status_sticky_regardless_of_stats()`,
  whose own docstring is *"1 awful trade -> still PROMOTED"*.
- `alpha_engine/money_ready_verdict.py:1374` `def _verdict(...)` and `:739`
  `s["tribunal_corroborated"] = verdict in ("PROVEN_T2", "CANDIDATE")` — a second, independent
  verdict emitter that does not go through `forward_gate_block`.
- `docs/SIDECAR_STATUS.md:3` — `PROMOTED: 3`, i.e. the bypass ships populated.

The part zoo understated is `tests/test_sidecar_promotion.py:108`: the sticky bypass is not an
oversight, it is **asserted by a passing test**, so removing it fails CI. That converts "a second
path exists" into "a second path is contractually protected".

**What is and is not disproved.** M1 as a claim about *surfaces and labels* is dead. M1 as a claim
about *capital* — that `forward_gate_block` is the only thing gating real-money promotion — is
**not** disproved and remains unverified; nothing in the evidence above sizes anything.
(`docs/PROMOTION_GATE_2026-11-22.md` still says **0 of 9 classes pass, zero capital sanctioned**.)

### 1.3 Peer results that agree with mine, and one that surprises

- **carry (copilot-cli-deepseek-flash)**: gross +3.555%/yr vs T-bill 3.50% = **5 bp headroom**, and
  the halves disagree (+5.96%/yr → **+1.24%/yr**). Matches my H-228 result (carry fails at 2× cost)
  and `docs/PROMOTION_GATE` (funding carry **REFUTED**, from CANDIDATE). Three independent witnesses.
- **subq's check #5**: 13 tested, 12 killed, 1 marginal, 0 clear the 4.32% T-bill; break-even hold
  16.398 d against a ~2 d positive-funding episode. Consistent with my per-class sweep.
- **subq's fleet metric**: *"no peer ran a random-entry null… cumulative count still 0."* This is
  the one claim I can answer with work I have already done — see todo 3.

### 1.4 The D0 blocker from the 2026-11-20 handoff is **already closed**

`grep -c '^<<<<<<<\|^>>>>>>>\|^=======' COMMUNICATION/verify_coms_windows.ps1` → **0**, and
`git diff --name-only --diff-filter=U` → **empty**. No unmerged path, no conflict markers. The
handoff's BLOCKER no longer exists; `plans/coms_finalization_plan.md` corroborates (PR #9 merged,
Windows round-trip verified). One fewer item, and one fewer reason to touch that repo.

### 1.5 What is *not* fixed, and needs your decision before I touch it

`plans/coms_finalization_plan.md` still lists four client defects: `register` appends without
upserting (duplicate seats), `coms-watch` self-disables at 50 cycles, `cmd_learn` uses an unquoted
heredoc (code execution from documentation), and unvalidated topic prefixes. All live in
**`/home/eaguiar2015/AGENT_FOLDERFRAMEWORK`** — a different repo from this one. I am named
implementer in `COMMUNICATION/COMS_HANDOFF_FREEBUFF_2026-11-20.md`, but committing to another
repo, and opening a PR that needs a token that is invalid on both hosts (per the B1-B5 note), is
your call, not mine.

### 1.6 A cost measurement landed mid-review, and one of its numbers does not stand

While this review was running, a peer desk committed (uncommitted-to-git, actually) an
EQUITY/ETF/INDEX/MEME spread measurement in this same tree: `tools/equity_cost_measure.py`,
`reports/equity_cost_measurement/*.json`, plus `updates/2026-11-22-m1-equity-cost-measurement.md`
and `-m3-cost-triage.md`. This matters because subq's ask #1 was "publish your measured asset-class
cost" and my honest answer was "EQUITY/ETF/FX/BOND unmeasured" — that answer is now **out of date**,
so it changes todo A3 rather than being a footnote.

The measurement is methodologically careful: three estimators kept separate, the bar-range number
labelled an **upper bound** (12.07 bp RT equity, 6.04 bp/side used for the re-cost; Corwin–Schultz
1.50 bp), live NBBO recorded as `BLOCKED_NO_LIVE_NBBO` on an HTTP 429 rather than as zero,
commission left `COMMISSION_UNKNOWN` because no broker statement exists, and a `REFUSED` table for
classes where cost cannot decide anything. That is the right shape.

**And one number does not stand.** The peer's own triage note admits
`n_symbols_with_data: 0` in the committed JSON while the write-up quotes 12.07 bp; I read the
artifact and confirmed it (§1.6 detail in todo C5): `spread.status` is the only spread content, and
`spread_aggregate` has zero symbols with every median `null`. The cost *curve* reproduces; the
*spread* does not. So the ETF/INDEX class numbers are citable and the equity 12.07 bp is not.

---

## 2. The todo set

### A. Peer obligations — outstanding answers on me (cheap, do first)

**A1. Correct M1 in the methodology doc, and register the correction.**
Rewrite M1 from "one proof surface, one enforcement module" to the true statement: one *statistical*
gate (`forward_gate_block`) plus **three sticky label paths** (`_PROMOTED_SIDECARS`, the
`money_ready_verdict` class verdicts, and the template badges), of which one is protected by a
passing test. Cite `dashboard_generator.py:12238/12297/12256` and
`tests/test_sidecar_promotion.py:108`. Add a claim-register entry that supersedes the M1 sentence —
the register is append-only, so this is a new entry, not an edit. **Highest priority: it is a false
claim I published, and a peer has already refuted it with verified evidence.**

**A2. Reply to zoo, in their §6 one-line format.** Q1 AGREE (with their stale-payload evidence),
Q5 AGREE, Q6 AGREE (badge, not hide — their PROMOTED-at-n=0 and BOND-WR-100%-at-n=2 findings are
the same class of error), Q2/Q4 UNCLEAR with my own reasoning, Q3 DONT KNOW (honest — I have not
measured de-overlap for a monthly book), A3 **VERIFIED-AND-WORSE** (the test lock), A1 NEED (no
delisted key — same gap as my items 16/19/20), A2 NEED nothing (I do not hold those six run JSONs),
A4 **granted scope**: `tools/registry_metric_audit.py` + `tools/fleet_consult.py --check-claims`,
with the specific ask that they run the checker against *my* claims too.

**A3. Answer subq's two narrow asks — and correct my own stale cost claim.**

(a) **Cost. My "non-crypto is unmeasured" statement is now out of date as of this session**, so the
reply must carry the newer numbers, not mine. A peer desk has measured them in this tree
(uncommitted at time of review, `tools/equity_cost_measure.py`):

| class | measured RT cost (upper bound unless noted) | caveat |
|---|---|---|
| EQUITY | **12.07 bp** RT (median 1-min bar range, 13 names) = 6.04 bp/side; Corwin–Schultz **1.50 bp** RT | NBBO `BLOCKED_NO_LIVE_NBBO` (HTTP 429, Sunday); `COMMISSION_UNKNOWN` |
| ETF | **6.71 bp** RT median, 3.36 bp/side | vs the 50 bp flat constant in the ledger = ~7.5× too high |
| INDEX | **8.03 bp** RT | alias of ETF; no separate cost model |
| MEME | **not measurable** | 1 of 2 names tick-truncated (SHIB: 53 distinct highs / 7,135 bars); quoting it would fabricate |
| PENNY_STOCK | **BLOCKED** | no penny instrument in cache |
| FX | 7.533 bp RT upper bound (peer); mean-reversion break-even 4.3038 bp | weekday-overlap run scheduled, not run |
| CRYPTO | 45.524 bp per pair RT @1× (mine, H-228); ~20.0–52.0 bp depending on venue | — |
| COMMODITY / BOND | **cost cannot matter** | break-even **0 bp/side**: both lose with free trading |

The honest line is "equity RT cost is **at most ~12 bp, plausibly 1.5–3 bp**, with NBBO and
commission still UNKNOWN" — not a false-precision constant. Every non-crypto verdict that cited an
*assumed* 5/10/25 bp should be re-labelled as conditional on this band.

(b) **Random-entry nulls: publish every percentile, and answer the fleet metric precisely.**
Mine: FX momentum 0.0, FX carry 98.2, 12-1 momentum 1.6, crypto intraday 0.0, equity breakout
(Donchian/D7) 69.8, commodity V1/V2/V3 30.2 / 33.1 / 25.2, bond B1 2.0, H-232 random-top-3 92.4.
**And a survivor-side percentile now exists from the peer desk**: the equity pod at measured
6.04 bp sits at the **10.2nd percentile** of random entries → `NOT_INVESTABLE`. So subq's "count
is still 0" was true when written and is **no longer true**, and the honest correction is that it
was a *reporting* gap, not an absence of the test — cheaper cost did not save that survivor either.
The part of subq's framing that stands: a null percentile beside a survivor is the only form that
counts, and I personally still have none because I have no survivor.

**A4. Tell subq D0 is closed** (0 markers, no unmerged paths) so the handoff item stops being
tracked as a blocker.

### B. COMS client work — blocked on your approval (different repo)

**B1.** Fix the four `coms_finalization_plan.md` defects (`register` upsert, watch exhaustion,
`cmd_learn` heredoc quoting, topic-prefix validation), one commit each, tests that fail before and
pass after, verified on Linux **and** over SSH on `win081g9oh`. Needs: your go-ahead to commit to
`AGENT_FOLDERFRAMEWORK`, and a working push path (the B1-B5 note reports `gh` token invalid on both
hosts, so a PR could not be opened last time).

**B2.** Document canonical seat addresses per agent/worktree. Until A/B1, describe the
cwd-derived-seat rule in one place so peers stop missing each other. This is documentation, not
code, and does not need the other repo.

### C. Programme continuation — the open work this unblocks

**C1. Sharpen the N_eff band.** Current result is N_eff ≈ 25 with a band of 20–30 against a DSR
boundary of 27–28, i.e. the verdict is inside the noise. More bootstrap draws and a finer subset
grid would either move the band clear of 27 or establish that it cannot be resolved at this sample
size — both are publishable; "25 ± 5" alone is not.

**C2. Schedule `pod_forward.py`.** No cron or workflow runs it, so the 15/20 forward days will not
advance on their own. A daily job is the difference between a clock and a monument.

**C3. Build the point-in-time universe of ≥22 names.** This is the single root under the pod's
self-imposed PASS bar and programme items 16 and 19. It is also the only thing that turns the
0.0 pp survivorship gap from a zero lower bound into a measurement.

**C4.** Re-check the remaining blocked items (**6** realised fill prices, **12**/**14** paid
futures/options series, **19** per-symbol ADV, **20** fund NAV source) against any new peer
intelligence — A1 of my own cross-review asked the fleet for exactly these data sources, and the
first replies are now in.

**C5. SETTLED (twice) — the artifact is good; my first correction was reading a stale file.**

> **Re-check result, later in the same session: the repair HAD landed at 23:09:46Z.** Re-reading the
> same path gives `n_symbols_with_data = 13`, `range_upper_bound_rt_bp_median = 12.074926303113397`,
> `measured_cost_per_side_used_bp = 6.0374631515566985`, `provenance_self_check = PASS`, per-name
> values inline, `generated_utc = 2026-11-22T23:08:17Z`. Sorting the 13 per-name values, the 7th is
> `QQQ = 12.074926303113397` — the median to the last digit. **The 12.07 bp is backed and citable.**
> The paragraph below stands as the record of what the pre-repair file said and why the panic was
> reasonable, but the "do not cite" instruction is **withdrawn**: the failure was a stale read on my
> side, and the lesson is to record the mtime whenever an artifact is about to be called empty.

**Original note (pre-repair file, now superseded): the equity-cost headline has no artifact behind it.**
The peer flagged their own discrepancy; I checked the file and **they were right**. Read back from
`reports/equity_cost_measurement/equity_cost_20261122.json`:

```
spread            = {"status": ...}            # no samples at all
spread_aggregate  = {"universe": "POD_UNIVERSE", "n_symbols_with_data": 0,
                     "range_upper_bound_rt_bp_median": null,
                     "corwin_schultz_rt_bp_median": null,
                     "measured_cost_per_side_used_bp": null}
proof_bar         = populated ('measured', '5bp', '25bp')
```

So the **12.07 bp EQUITY figure is prose-only**: zero symbols, every median null. The `cost_curve`
and `proof_bar` blocks *are* populated, so the **cost curve reproduces** — the **spread measurement**
does not. Consequence for A3: cite `class_cost_20261122.json` (which does hold per-class universes)
for ETF **6.71** / INDEX **8.03** bp RT, and label the equity **12.07 bp as UNBACKED — do not
cite** until the tool is re-run to completion and the aggregate is non-null. This is precisely the
R1/R5 defect class `tools/registry_metric_audit.py` was built to catch, landing on a peer's number
one paragraph after that peer flagged it themselves — which is the registry-audit idea working.

---

## 3. Ordering, and why

A1 first because a peer has verified that one of my published claims is false — every hour it stays
published, it misleads anyone reading the methodology. A2/A3/A4 next because they are cheap, they
close obligations to two desks, and A3's content is already measured. Then C1/C2 (my own open
scientific work), then C3 (the expensive root), then B, which is the only group needing your
permission.

Nothing in this list changes a verdict. H-201 remains `NOT_PROVEN`; no class passes the promotion
gate; zero capital is sanctioned.
