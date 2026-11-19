# Response to the arena.ai audit3 review (2026-11-19)

Review under assessment: `AUDIT3_FEEDBACK_2026-11-19.md` (124 lines, on main).
Everything below was re-derived from `audit_dashboard/data/audit3_ledger.json` and the
04:04Z dashboard payload, not taken on trust.

**Overall:** the strongest outside review of audit3 so far. Its statistics are sharper
than most of our own writing, its numbers check out almost exactly, and its two biggest
points (§2.1 win-rate gate, §2.10 not wired to emission) are correct and consequential.
It has one factual error (§2.6), one mislabelled pairing (§2.2), and it grades two
already-known `/audit` defects as new. Fixed here: §2.1, §2.4, §2.6 (partly), §2.8,
§2.9 (partly), §5.1. Deferred with reasons: §2.3, §2.7, §2.10, §5.8.

---

## Grade per item

| § | Claim | Verdict |
|---|---|---|
| 2.1 | WR>50% gate is mis-specified; expectancy is the edge test | **AGREE — fixed** (worse than stated) |
| 2.2 | 3 positive-CI segments double-count the A⊂B overlap | **AGREE, pairing wrong — fixed** |
| 2.3 | BH pools confirmatory + discovery cells | **AGREE — deferred** |
| 2.4 | Trial accounting inconsistent (45 vs 59 vs 99/28) | **AGREE — all three numbers exact; DSR fixed** |
| 2.5 | luxalgo SHORT fails multiplicity + concentration, not edge | **AGREE — every number exact** |
| 2.6 | Hard-coded slippage constants are optimistic | **DISAGREE — measured data says conservative; 2× stress added anyway** |
| 2.7 | Split-half is too weak a stability test | **AGREE — deferred** |
| 2.8 | Ledger leaks a /tmp path; needs input hash | **AGREE — fixed** |
| 2.9 | Ledger is recent-biased; crypto longs killed spuriously | **AGREE — partly fixed, plus a new finding** |
| 2.10 | Tribunal is not wired to block emission | **AGREE — the most important item; not done** |
| 4.2 | Kill-switch shows WR lift +6.10pp but PF lift −0.0224 | **AGREE — and the PF series is degenerate** |
| 5.1 | Schema spec leaks host + credential path on a public repo | **AGREE — fixed (redacted)** |
| 5.8 | Missing `forward_observations` table blocks PROVEN from live data | **AGREE — deferred, high value** |

---

## §2.1 — Correct, and worse than the review says

The review says the WR gate cannot certify a premia cell. True, and broader than that:
`q_value` was computed from the **WR binomial** p-value (`binom_sf(wins, n)`). So a
35%-WR / 2.5-payoff cell with a strongly positive expectancy CI failed not just the
PROVEN floor but the CANDIDATE multiplicity check too — `q → ~1.0` whenever WR < 50%.
The gate system could not express "this loses often and makes money", which is what
trend and carry premia are.

**Fixed:** `p_value` is now the one-sided bootstrap **P(net mean ≤ 0)**; `p_wr` is
reported as a descriptor and never gates. `p_harm` for the kill path is likewise the
bootstrap `frac_positive` rather than a WR flip. PROVEN_T2 now requires
`n ≥ 100`, net-CI lower bound **≥ 0.05%/trade** (new materiality floor — 5bp is inside
the error of the cost model, so promoting a 1bp edge would be theatre), stable halves,
symbol share ≤ 60%, source share ≤ 90% (aggregates only), BH q ≤ 0.10, DSR ≥ 0.95.
A single-emitter cell can still be PROVEN, but it now carries
`single_source: true` and the reason "proven on the ledger, not sizing-eligible until
replicated independently" — a flag, not a block, because gating on it would resurrect
the "nothing can ever graduate" problem from the other side.

Effect on the live ledger: low-WR/high-payoff cells become promotable; nothing currently
PROVEN changed; `luxalgo_confluence SHORT` now reaches CANDIDATE (see §2.5).

## §2.2 — Right conclusion, wrong pairing

Measured, the three "positive-CI segments" are:

| Segment | n | net/trade | net 95% CI |
|---|---|---|---|
| `grade A` CRYPTO | 33 | +1.472% | [+0.483, +2.450] |
| `score>=60` CRYPTO | 33 | +1.472% | [+0.483, +2.450] |
| `elite_grade B` CRYPTO | 72 | +1.407% | [+0.618, +2.188] |

`grade A` and `score>=60` are **the same 33 rows to four decimals**, not merely
overlapping — 65 segment cells across at most two distinct cohorts. The review's
`A ⊂ B` framing understates it.

**Fixed:** reconstructed segment proxies are now capped at CANDIDATE
(`reconstructed section proxy: CANDIDATE is the ceiling`). **Not fixed:** the nominal
CIs on those rows are still unadjusted for the 65-cell screen. The honest read is that
n=33 with two duplicate labels is not evidence of anything yet.

## §2.3 — Agree, deferred

Splitting a `confirmatory` namespace from `discovery` is the right design: a
pre-registered pod deserves a smaller family (or fixed α) than 40+ exploratory cells.
It needs a namespace field in `reports/hypothesis_registry.json` and a rule the
promotion path reads, so it is a separate change, not a gate tweak.

## §2.4 — Every number exact

Verified: `summary.n_cells_tested = 45`, `provenance.n_cells_scored_with_dsr = 59`,
cells with n ≥ 10 = 60, registry = **99 entries across 28 distinct raw status
spellings** (the review's count is precisely right).

**Fixed:** DSR is now only computed and published for cells inside the tested family
(n ≥ 20), so `n_cells_dsr_scored == n_cells_tested` is an enforced invariant, and a
`registry_note` states that one N feeds BH, Bonferroni and DSR.
**Not fixed:** the 28 status spellings. That is the evidence registry's enum, and
canonicalising it there is the correct place.

## §2.5 — Every number checks out

`luxalgo_confluence` SHORT: n=476, WR 54.41% (Wilson [49.92, 58.83]), PF 1.5572,
net +0.668%/trade, bootstrap CI [+0.352, +0.964], q 0.338, DSR 0.9766,
`top_source_share` 0.9769. The LONG side of the same strategy is n=754, WR 36.21%,
PF 0.7966, net −0.330%, **KILL**. A strategy that is KILL long and positive short is
short beta far more plausibly than it is an edge.

Under the v2 gates this cell is now **CANDIDATE** (forward paper, no sizing) — which is
the correct verdict: it has edge vs zero, it fails multiplicity at the strict
promotion bar, and at 97.7% single-source it cannot become PROVEN until a second source
exists. The BTC-regression and the SL-wins-ties first-touch check the review asks for
are still open and still necessary.

## §2.6 — Disagree, with measured numbers

The review calls the constants "optimistic". Our own `slippage_validation` block
measures realised slippage against them:

| Class | constant used | measured | ratio |
|---|---|---|---|
| CRYPTO | 0.15% | **0.0997%** | 1.50× conservative |
| EQUITY | 0.10% | **0.0500%** | 2.00× conservative |
| FOREX | 0.05% | 0.0200% | 2.50× conservative |
| ETF | 0.08% | 0.0500% | 1.60× conservative |
| COMMODITY | 0.12% | 0.1500% | 0.80× optimistic |

So the constants are conservative everywhere except COMMODITY, and audit3's kills are
not the product of an optimistic cost model. The review's *measurement* concern still
lands for small-cap EQUITY (n-weighted averages hide tail names), and a stress column
is cheap, so:

**Added:** `net_ci_pct_2x` + `stress_2x_ok` — the same net CI at **2× the class
constant** — on every cell and every class, surfaced as a `2× cost` column (holds /
breaks). Report-only; it never changes a verdict.

## §2.7 — Agree, deferred

Two halves is the weakest stability test worth running. Rolling 4–8 week cohort means
with a monotonicity check is the right upgrade; it needs a per-cell time series the
ledger does not currently keep.

## §2.8 — Fixed

`provenance` now carries `generator_version` (`audit3.v2`), `input_sha256` (SHA-256 of
the input payload), and `git_sha` (`GITHUB_SHA` or `git rev-parse`). The `/tmp` source
path stays because it is genuinely where CI writes the file, but it is no longer the
only thing identifying the input.

## §2.9 — Agree in part, plus a finding the review missed

The ledger judges 3,500 of 16,330 closed picks (21.4%) — this is now stated on the page
by the coverage panel added earlier today. The crypto-LONG kill claim needs care:
`BTC-USD LONG` (n=25, −1.80%), `ETH-USD` (24, −1.99%), `SOL-USD` (23, −3.20%),
`BCH-USD` (20, −3.92%), `BNBUSDT` (20, −1.44%) are KILL, but `ETHUSDT LONG` (n=109,
−0.35%) and `SOLUSDT LONG` (n=61, −0.28%) are only WEAK, and `BTCUSDT SHORT` (+0.09%),
`ETHUSDT SHORT` (+0.56%), `SOLUSDT SHORT` (+1.05%) are positive-WEAK.

The same underlying instrument is split across `-USD` and `USDT` symbol spellings into
separate cells with different verdicts, and the `-USD` cells carry n≈20–25, barely above
the floor. **That is a symbol-identity defect, not evidence about crypto longs.** It
belongs with the known FOREX key mismatch (`AUDCAD` vs `AUDJPY=X`) as one canonicalisation
problem. Not fixed here; recorded as the next data-integrity item.

## §2.10 — Agree; it is the most important sentence in the review

"A tribunal that reports kills while the emitter never reads it is theatre." Correct.
`KILL` cells do not currently degrade any emission privilege, which makes the whole
surface advisory. Wiring tribunal output into the scanner's denylist — plus an explicit
PROVEN_T2 → small-size-with-forward-review path, so the machine can graduate something —
is a scanner change, deliberately not smuggled into a gate PR. Next.

## §4.2 — Agree, and the lift metric is worse than misleading

`kill_switch.impact` reports `wr_lift_pp: 6.1`, `pf_lift: −0.0224`,
`verdict: "POSITIVE"` — with `baseline_pf: 0.0316` and `post_pf: 0.0092`. A profit
factor of 0.03 is not a profit factor; it means the denominator is accumulating dollars
where the numerator accumulates percent. So the "PF lift" is computed on a broken
series and the card's `POSITIVE` label rests on WR alone. Either fix the PF units or
drop the lift line.

## §5.1 — Agree; redacted now

The spec named `mysql.50webs.com:3306` and the credential-resolution path
(`tools/db_env.py` + `~/dbpasses.txt`) in a **public** repo, in a document the review
itself was asked to paste into a web AI. No passwords were exposed, but host + user
mapping + resolver path is a roadmap. Host and credential paths are now `<DB_HOST>` /
non-documented placeholders, with a redaction note. This was my merge; it should not
have gone out that way.

## §5.8 — Agree, this is the missing piece

`forward_observations(...)` with a promotion rule ("PROVEN_T2 requires n ≥ 100 forward
rows with net CI-LB > 0") is exactly what stops audit3 from being a museum. The
`FWD` fields exist piecemeal; a first-class forward table with `benchmark_leg_ret` and
`resolver_version` is the change that makes "winning" measurable.

---

## What changed in code

| Item | Change |
|---|---|
| §2.1 | expectancy p-value primary; WR descriptor (`p_wr`); materiality floor 0.05%/trade; `single_source` flag on PROMINENT single-emitter cells |
| §2.2 | segment proxies capped at CANDIDATE |
| §2.4 | DSR restricted to tested family; invariant + `registry_note` |
| §2.6 | `net_ci_pct_2x` / `stress_2x_ok` + `2× cost` column |
| §2.8 | `generator_version`, `input_sha256`, `git_sha` |
| §5.1 | spec redacted |

## What this does **not** change

No pick, signal, size or emission path. No threshold in the kill rule (still net CI
< 0 **and** BH harm q ≤ 0.10). The tribunal still cannot size anything: PROVEN_T2 is a
statement about the realized ledger, and the page keeps saying so.

---

## v3.1 review check (2026-11-19, after #901 / #902)

The reviewer could not push from their sandbox, so `AUDIT3_FEEDBACK_2026-11-19.md`
on main is still v1. Part 4 of v3.1 was checked line by line against `main`:

| v3.1 claim | State on main | Verdict |
|---|---|---|
| `reports/audit3_confirmatory.json` has `"pods": []` — "the promotion path is built and unused" | 3 pods: `POD-EQUITY-BREAKOUT` pre_registered, `POD-LUXALGO-SHORT` post_hoc, `POD-CRYPTO-ENSEMBLE-GRADE` declined | **stale** (#901) |
| tribunal→emitter wiring "in flight, expect it to land" | wired at ingest and at write, plus a class gate and a CI health assertion | **done** (#898/#900/#901) |
| expectancy gate fixed; `p_wr` demoted to descriptor | confirmed in code | **confirmed** |
| spec redaction done, ~4 DB names remain | 0 host / 0 credential-path hits; DB names left on purpose (they are not credentials and the inventory is the document) | **confirmed** |
| tier2 panel, "Renaissance" labels, PF-lift card still open | retired / stripped / removed | **done** |
| one smart-picks definition | still open (feed says 0 scored, snapshot says 95 at 68.4%) | **done** — one `smart_picks` object in the payload; the 0-vs-95 gap is live-vs-history, labelled `history.comparable_to_live_feed=false` rather than presented as a contradiction |
| ETF needs the canonical view before any conclusion | view + declared denominator shipped | **addressed** |
| H-119 two vintages | still open | **done** — fallback is now a labelled dated snapshot, the card names its vintage, and `gate_eta ~2026-06-25` is retired at source (n≥150 was already met at n=431; only `net_ci_lb_gt_1.15` fails) |
| kill lists share exactly one name | still open | **done** — kept separate on purpose (name-only policy vs direction-aware expectancy; `luxalgo_confluence` is KILL LONG and CANDIDATE SHORT), with `tools/kill_list_reconcile.py` publishing the union and provenance |
| `forward_observations` ledger | still open | **shipped and filled** — contract + clock + promotion rule (`alpha_engine/forward_observations.py`), read-only ingestion (`forward_observations_ingest.py`), **430 real forward rows for H-119** that reproduce the tracker's net PF within 0.4% (1.1147 vs 1.1191), and PROVEN_T2 now gated on them in audit3 |

`docs/FINANCE_DB_SCHEMA_SPEC.md` note: the remaining `ejaguiar1_*` mentions were left
in place. The review flags them "only if this repo is ever made public"; removing the
DB names would strip the inventory of the one thing that makes it navigable, and they
are not credentials. If that judgement should change, it is a one-line sed.

Net: all 10 v3.1 P0 rows are now closed at the contract level. What remains is not a
missing table but a missing **writer**: the forward ledger has 0 rows because no
ingestion adapter fills it, so `PROVEN_T2` is defined and unreachable at the same
time — which is the honest state until forward evidence actually exists. Its closing recommendation
("the fastest high-value action is registering Pod 1") was already done before the
review landed.

