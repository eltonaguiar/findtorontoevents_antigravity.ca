# 03 — Answers to the 2026-11-14 Final Plan

**Date:** 2026-11-15 · **Author:** Buffy
**Source under review:** `final_v4/flaxen-hair_2026-11-14T2304/` + the summary text supplied

Verdict first: **the Nov-14 plan's headline conclusion is correct and I am not contradicting it — no
class is proven profitable, and no capital should be deployed.** But four of its supporting numbers are
wrong or stale against the live ledger, one of its claims is now resolved, and its §1–5 framework has a
structural gap that will make it fail again if left unaddressed.

---

## 1. Where I confirm the plan

| Claim | Verdict | Basis |
|---|---|---|
| **No asset class is currently proven profitable** | ✅ **Confirmed** | My independent measurement: verified PF 1.02–1.16 for the three measurable classes, all below the money-ready bar |
| 0/23 hypotheses survived OOS + effective-N + capital + execution gates | ✅ Confirmed | Consistent with IC ≈ 0 (Pearson 0.039, Spearman 0.105) |
| All 9 classes `sizing_allowed: false` | ✅ Confirmed | Correct call |
| Do not deploy capital yet | ✅ **Endorsed** | See §5 |
| Mutual funds are not a prediction class | ✅ Confirmed | Structural — once-daily NAV |
| Promotion gates default OFF / cost gate fail-open | ✅ Confirmed, and worse than stated | See §2.4 |

The plan's decision is right. Everything below sharpens it, not reverses it.

---

## 2. Where the numbers need correction

### 2.1 "ETF: Zero live picks" — **wrong**

The live payload contains **575 closed ETF rows, 566 of them with verified marks** (2% contamination —
the cleanest class in the system), plus 19 in `asset_class_health` at WR 68.4%, PF 1.788.

The confusion comes from a real event: on 2026-05-31 the ETF class had 159 OPEN and 134 `TIME_EXIT`-at-
zero rows, so a naive `status IN ('WON','LOST')` query returned almost nothing. **The picks existed;
the resolver never marked them.** "Zero live picks" is a measurement artefact being reported as a
coverage fact.

### 2.2 "COMMODITY / FUTURES PF ~1.78, WR ~47%, n~750" — **not reproducible**

Measured today: COMMODITY has 23 closed rows, **7 verified**, PF 0.60. FUTURES has 10 closed rows,
**0 verified**, 100% forged.

The 1.78 figure traces to `multi_asset_cot` at PF 21.33 on n=144, which the 2026-05-13 plan already
flagged as a CT=F single-symbol artefact, with 230/354 rows being COT duplicates. **Quoting 1.78 as a
class PF is quoting a concentration artefact.** This is the single most misleading number in the
inherited corpus.

### 2.3 "CRYPTO recent PF ~0.74, WR ~33%" — **cohort mismatch, not a contradiction**

I measure PF 1.02 / WR 40% on **2,114 verified marks**. The 0.74/33% figures come from policy-clean
subsets with different denominators (`asset_class_health` itself reports n=22,077, PF 0.258). Three
different CRYPTO PFs are in circulation: **0.258 / 0.74 / 1.02**. None is authoritative until the
cohort definition is pinned. That ambiguity *is* the finding.

### 2.4 The measurement problem is larger than "PnL = 0%" rows

The plan treats PnL=0% as a data-quality item. Measured: **3,350 of 6,968 closed rows (48.1%)** are
forged flats — `exit_price == entry_price`, stamped `TIME_EXIT`. That is not a rounding issue; it is
**half the ledger**. Any class-level statistic computed over the full ledger is measuring the resolver.

### 2.5 "ETF win rate 2.22% → 68.42% spread" — explained

Both are real and neither is edge: 2.22% is the naive `WON/(WON+LOST)` view on resolver-zero rows;
68.42% is the `asset_class_health` view on a different cohort. Verified-mark WR is **44%**. The spread
is a cohort-definition artefact, which is why L1 must publish the cohort definition with every number.

### 2.6 DSR threshold "≥0.95 at N≥38" — **under-powered**

With **361 registered strategies**, the multiple-testing denominator is 361, not 38. A DSR computed at
N=38 understates the correction by ~10×. At 361 trials, roughly **18 strategies are expected to look
significant at α=0.05 by chance alone**. The threshold must be computed at the true trial count.

---

## 3. "SubQ status: NOT_RUN" — resolved

The Nov-14 plan records SubQ as `NOT_RUN` and treats peer SubQ documents as unverified synthesis. That
was correct at the time — and it happened because **earlier agents interpreted "SubQ" as "subagent
query"** and searched the filesystem for a binary. A real SubQ API key exists in `dbpasses.txt`.

I ran it: **3 arms × 8 questions = 24 decisions, all HTTP 200**, artefacts in `07_subq/`.
Full analysis in `07_subq/FACTCHECK.md`. Headline: it independently returns `NONE_PROVEN` (P=0.80 bare,
0.87 with evidence) and `fix_measurement` as the top priority (P=0.99 with evidence).

---

## 4. Where the plan's framework is structurally incomplete

The plan's five steps are directionally right: fix measurement, separate beta from alpha, strict
protocol, risk overlay, prioritisation. Three gaps will cause a repeat failure:

**Gap 1 — enforcement point.** The plan says "enforce the existing promotion gates." But the repo's
own blocklist is enforced in `build_pf_registry.py` (**display layer**) while banned strategies kept
writing 370 picks/week to the DB (`ml_crypto_predictor` LONG: 206 in 7 days; `alpha_engine_fast`: 163).
**Gates at the read layer filter what you see; only write-layer gates change what you trade.**

**Gap 2 — no truth gate before the protocol.** The plan goes measurement → protocol → benchmark. Missing
is a hard precondition: *no statistic may be computed over unmarked rows at all.* The validator
(`tools/pnl_zero_validator.py`) and measurability report (`tools/asset_class_measurability.py`) now exist
and should block CI.

**Gap 3 — "build mutual fund infrastructure from scratch" is the wrong spend.** The plan's week 2–4 item
is to build NAV cache + ranker + metadata for mutual funds. But funds cannot host intrabar stops, fill at
next unknown NAV, and are subject to 30-day frequent-trading limits. **Building a pick pipeline for them
is building something that cannot be executed.** Funds belong on the allocation side (monthly clock, cost
filter), which needs no new infrastructure.

---

## 5. Corrections to the go/no-go thresholds

| Threshold in plan | Issue | Proposed |
|---|---|---|
| PF ≥ 1.5 | Reasonable, but must be **after** per-class costs | PF ≥ 1.5 net |
| Sharpe ≥ 1.0 | Per-trade Sharpe is 0.005–0.061; must annualise with stated trades/yr | Annualised, method disclosed |
| DSR ≥ 0.95 at N≥38 | Under-powered for 361 trials | DSR ≥ 0.95 at **N = true trial count** |
| WR ≥ 50% | Should be EXPIRED-inclusive (plan doesn't say) | WR ≥ 52% incl. EXPIRED as non-win |
| n ≥ 100 closed picks | Too low once effective-N is applied | n ≥ 100 **verified**, OOS ≥ 2 halves |
| Kelly > 0 after shrinkage | Correct; currently **−0.0538** → size zero | Keep; publish the negative |
| Max DD < 15% | Fine for a sleeve, not for the ledger (measured −100% compounded) | Sleeve-level, compounded |
| "Mutual funds in ledger = 0" | Correct, but shouldn't be a goal | Not a gate |

---

## 6. What I would change in the plan's sequencing

| Plan order | Proposed order | Why |
|---|---|---|
| 1. PnL validation | 1. **L0 truth: resolver mark-to-market + backfill 3,350 rows** | Validator without the fix only reports the same failure forever |
| 2. MF/ETF infra | 2. **Move blocklist to emitter** | Stops new contamination while backfill runs |
| 3. EQUITY benchmark | 3. **EQUITY vs SPY (unchanged — right call)** | Agreed |
| 4. CRYPTO post-fill | 4. **CRYPTO after fill fix, POSITION horizon** | Agreed; expect ≈breakeven, not profit |
| 5. Review | 5. **ETF 200-DMA trend (new slot)** | Cleanest data, documented method, currently absent from 361 strategies |
| — | 6. **Retire MEME/PENNY, label DORMANT** | Stops phantom classes occupying dashboards |

---

## 7. One-sentence answer to the plan

**The plan is right to say no class is proven and no capital should move; its numbers need three
corrections (ETF has 566 verified marks, COMMODITY/FUTURES are unmeasurable not 1.78 PF, CRYPTO has
three conflicting PFs), its SubQ gap is now closed with a real run, and its one wrong spend is building
mutual-fund pick infrastructure for an asset class that cannot be picked.**
