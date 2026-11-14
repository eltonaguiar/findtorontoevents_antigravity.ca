# Final Plan — 24h review, QA gate, fund sleeve, risk page

**Date:** 2026-11-14 · **Window reviewed:** 2026-11-13 ~22:00 → 2026-11-14 23:40 UTC (remote + local + live payload)
**Status:** plan + working QA artefact + risk page. Every number below was produced today by the command that appears beside it. Nothing here is estimated.

---

## 0. What actually changed in 24h

`git log origin/main --since="24 hours ago" | wc -l` → **2,055 commits**. Almost none are work: all but ten end in `[skip ci]` (signal scans, PnL refreshes, payload rebuilds by bots). The real change set is ten PRs:

| PR | Content |
|----|---------|
| #767 | multi-testing audit of /audit |
| #768 | remediation plan + v1–v4 edge search (0/40 trials pass) |
| #769 | `final_2026_11_14/` package, peer claims adjudicated by re-execution |
| #770 | `final_v2/` per-class profitability |
| #771 | **code**: `stop_fill.py`, gap-aware resolver fill, per-class cost gate, COT test |
| #773 | **code**: kimi records the stop it exited against; B4 settled; EQUITY fails its SPY gate |
| #774 | removed a foreign doc #773 carried |
| #775 | CI: pandas `"ME"` alias; B13 counts corrected; peer review |
| #776 | docs: scratch-hippodraco bundles |
| #777 | CI: last `ME` alias; cost fallback moved to caller |

CI on tip `d92b08b5e84`: **`test (3.11)` success, `test (3.12)` success — 6,577 passed, 0 failed.**

**Local state:** HEAD was **65 commits behind** `origin/main`; 10 dirty paths, of which the only financial two (`audit_trail/dashboard_generator.py`, `combined_book/fetch.py`) are **already superseded by #777**. `audit_dashboard/data/dashboard_data.json` is gitignored (`.gitignore:218`) and locally dated **2026-10-19T19:40Z — 26 days stale**. The live payload is `2026-11-14T22:34Z`. **Any audit run against the local checkout audits a 26-day-old artefact.**

### 0.1 A hazard hit during this session
A background process ran `git pull origin main --rebase` at 23:24 and **discarded this document and the validator** (they were uncommitted; the auto-stash held 4 unrelated files). Cause is structural, not a mistake in the work: the tree receives ~1 commit/minute from bots, so rebases fire constantly and uncommitted work is collateral. Mitigation now in place: the artefacts are committed locally (not pushed), and copied to `/tmp/deliverable_backup/`. See `AGENTS.md` → silent-file-revert.

---

## 1. The live ledger, measured

| Surface | Rows | Note |
|---|---|---|
| `picks.active` | **14** | what a user sees |
| `picks.active_raw` | **4,159** | what the system tracks |
| `picks.recent_closed` | **3,500** | the WR/PF denominator |
| `picks.smart_picks` | **0** | empty |

**PnL = 0.0%:**

| Surface | Zeros | Share | Verdict after checking real prices |
|---|---|---|---|
| `active` | 10 | 71.4% | **7 JUST_OPENED + 3 FLAT_VERIFIED — legitimate** |
| `active_raw` | 3,904 | 93.9% | 45/60 sampled are **UNPRICED** (no price at all) |
| `recent_closed` | 49 | 1.4% | **37 FABRICATED_FLAT**, 11 UNVERIFIABLE, 1 FLAT_VERIFIED |

This distinction matters and I want it stated plainly: **the 10 zeros a visitor sees are not fake.** All are `age_hours ≤ 2.0` with `entry_price == current_price` to the cent (ETHUSDT 1757.22, BTCUSDT 63817.98, ES=F 7583.0, AMZN 266.66). A position opened 30 minutes ago has not moved yet.

**The 49 closed zeros are a different thing.** Each has `exit_price == entry_price` and a `TIME_EXIT`/`UNKNOWN` reason, and the exit price is *not the market close on its own exit date*:

| Symbol | Stated exit | Real close 2026-11-14 | Error |
|---|---|---|---|
| V | 383.90 | 425.76 | **−9.83%** |
| GOOGL | 342.00 | 295.77 | **+15.63%** |
| LLY | 1,189.41 | 1,443.50 | **−17.60%** |
| GE | 354.39 | 331.81 | +6.81% |
| JNJ | 270.00 | 285.75 | −5.51% |
| AMZN | 260.28 | 266.66 | −2.39% |

Nine large caps closed in the same second, none marked to market. These rows enter the denominator as non-wins at 0.0% and flatten the league table.

**Other integrity facts:** `active_raw` has 3,637 blank `current_price` (87.4%), 987 blank `entry_time` (23.7%), 754 blank `exit_reason`. `recent_closed` has **1,745 blank `entry_time` (49.9%)** — half the closed ledger cannot be window-checked. Exit reasons: SL_HIT 1,433 · TP_HIT 868 · FORCE_CLOSED 619 · TIME_EXIT 554 · UNKNOWN 22 · EXPIRED 4. `total_picks` is **null on all 9 class metrics**, so no PF/WR on the page has a published n. `readiness.by_class` contains 9 classes and **no MUTUAL_FUND**.

---

## 2. Defects, ranked by damage

| # | Defect | Measured |
|---|---|---|
| D1 | Fabricated flat closes (`exit_price := entry_price`, stamped `TIME_EXIT`) | **37** rows, error up to 17.6% |
| D2 | Unpriced open positions shown as flat | **87.4%** of `active_raw` |
| D3 | No published n on any class metric | `total_picks: null` × 9 |
| D4 | `smart_picks` empty | 0 rows live |
| D5 | Half the closed ledger unvalidatable | 1,745/3,500 blank `entry_time` |
| D6 | Local payload 26 days stale + gitignored | 2026-10-19 vs 2026-11-14 |
| D7 | Fund tooling stranded upstream | `tools/fund_durability.py` etc. absent from main; PRs **#759/#760 open since 2026-10-23** |
| D8 | Displayed ≠ tracked | 14 vs 4,159 |

---

## 3. Workstreams (dependency-ordered)

**W1 — Truth layer.** Every pick terminates (`TP_HIT`/`SL_HIT`/`TIME_EXIT`/`EXPIRED`) with a real `exit_price` and `closed_at`. `TIME_EXIT` may not write `exit_price == entry_price` unless the exit-date close confirms it; otherwise `UNPRICED_CLOSE`, excluded from WR/PF and reported separately. Backfill or tag `entry_time`. Publish `n_raw`/`n_effective` beside every PF/WR.
*Acceptance:* `resolved + expired + unpriced + open == emissions`; zero fabricated flats; zero class metrics without n.

**W2 — QA gate** (built today, §4).
*Acceptance:* validator runs in CI against the live URL, exits non-zero on D1/D2, goes green only after W1.

**W3 — Promotion gate.** `admit_strategy()` returns `False` unless `n_effective ≥ 200`, DSR ≥ 0.95 with correlation-adjusted trials, PBO ≤ 0.10, BH-FDR q < 0.05 across the tested family, OOS PF ≥ 1.25 after per-class costs. Delete the `MONEY_READY_*_GATE = "0"` defaults (`money_ready_verdict.py:180,195`) — a gate that defaults off is not a gate.
*Acceptance:* synthetic null rejected ≥95%; nothing promoted with n < 200. An empty `smart_picks` is an acceptable, honest state.

**W4 — Fund/ETF sleeve** (§5). Monthly clock allocation with measured base rates — explicitly not a prediction edge.

**W5 — Risk page** (§6). Built today.

**W6 — Ops.** Five workflows; normalise direction tokens to fix `scanner.py:2942 KeyError: 'LONG'`; archive never-run workflows.

---

## 4. QA plan — PnL = 0% against real market data

Implemented in `tools/pnl_zero_validator.py` (runs today, exits 1 on the live payload).

### 4.1 The primary test is exit-price vs its own exit-date close
The first version compared the exit price to **entry**, which conflates "held a long time, so the market moved" with "the price was never looked up". A subagent review flagged it, and it was right. The implemented test:

- **Closed row:** `exit_price` vs the market close **on the exit date**. If the difference exceeds slippage (**0.25%**), the row is `FABRICATED_FLAT`. This does not need `entry_time` at all, so it works on the 49.9% of rows that lack one.
- **Open row:** `current_price` vs the live price since entry. No `current_price` ⇒ `UNPRICED`, never "flat".
- **Open row, `entry_price == mark`, age ≤ 2h:** `JUST_OPENED`.

The entry→exit window is still reported (`real_move_pct`) as *context*, never as the verdict.

### 4.2 Tolerances (floor for suspicion, not a pass mark)
| Class | tol | Why |
|---|---|---|
| EQUITY / ETF / BOND | 0.50% | ~1 intraday sigma for a large cap |
| CRYPTO | 1.00% | 24/7, materially higher daily vol |
| FOREX | 0.10% | majors rarely move 0.5%/day |
| FUTURES / COMMODITY | 0.75% | session gaps + contract rolls |

Known modes, stated rather than hidden:
- **False negative:** a fabricated exit within 0.25% of the close — indistinguishable from honest slippage, and *accepted as correct*. The alternative (zero tolerance) would flag every legitimate fill.
- **False positive:** a genuinely flat instrument on a low-vol day can sit just inside the slippage band. Bounded by design; the count is reported, not hidden.
- **Misses entirely:** rows whose history is shorter than the lookback window (`UNPRICEABLE`), and classes with no free source.

### 4.3 Blank-field policy
| Surface | Field | Rule |
|---|---|---|
| displayed (`active`) | `entry_price`, `current_price`, `take_profit`, `stop_loss`, `entry_time` | **hard fail** |
| open (`active_raw`) | `current_price` | allowed, tagged `UNPRICED`, excluded from aggregates |
| closed ≤ 7 days | `exit_price`, `closed_at`, `exit_reason` | **hard fail** |
| closed, any age | `entry_time` | warn + tag; excluded from validation rate |

### 4.4 Invariants
`resolved + expired + unpriced + open == emissions` · `|implied_return − stated_pnl| ≤ 1.0pp` · `censored_pct` published beside every WR, > 20% ⇒ headline `INCOMPLETE`.

### 4.5 Measured result today
```
recent_closed:  FABRICATED_FLAT 37 · UNVERIFIABLE_NO_ENTRY 11 · FLAT_VERIFIED 1
active:         JUST_OPENED 7 · FLAT_VERIFIED 3
active_raw:     UNPRICED 45 · FLAT_VERIFIED 11 · UNPRICEABLE 3 · JUST_OPENED 1  (60 sampled)
VERDICT: FAIL   (exit 1)
```

---

## 5. Mutual funds and ETFs — what "solid picks" can honestly mean

### 5.1 Funds cannot be a pick class (structural)
NAV is struck once daily **after** the close; orders fill at the **next** NAV; TP/SL can only execute at that next NAV; many funds impose 30-day frequent-trading limits. The resolver's intrabar TP/SL model is meaningless here, and the ledger has **no MUTUAL_FUND class** (9 classes, none). A fund "pick" is an **allocation on a monthly clock** and must be labelled that way — never as an active pick.

**Definition (so the two are not confused):** a *pick* is a directional entry with a price, a stop, a target and an intrabar exit test. An *allocation* is a target weight rebalanced on a fixed schedule with no stop and no target. Funds can only ever be the second.

### 5.2 What is genuinely deliverable — measured, not asserted
Fee criteria verifiable from a prospectus: expense ratio ≤ 0.20% (ideally ≤ 0.10%), 0% load, no 12b-1, minimum ≤ $1,000, AUM ≥ $1B, turnover ≤ 20%/yr, R² ≥ 0.99. A fund's **ETF share class is the same portfolio at a lower fee tier**, which is why the ETF row is the right place to measure the exposure.

| Instrument | History | CAGR | Vol | Sharpe | Max DD | P(+) 1y | P(+) 5y | P(+) 10y |
|---|---|---|---|---|---|---|---|---|
| SPY (S&P 500) | 407 mo | 8.71% | 14.74% | 0.64 | **−52.2%** | 78.5% | 76.1% | **90.2%** |
| QQQ (Nasdaq-100) | 333 mo | 9.58% | 23.21% | 0.51 | **−81.1%** | 79.4% | 86.8% | 89.7% |
| XLF (Financials) | 336 mo | 4.04% | — | 0.30 | −79.9% | 63.3% | — | — |
| VOO | **195 mo** | 12.10% | 14.03% | 0.89 | −24.8% | 85.8% | 100% | — |
| AGG (bonds) | 279 mo | −0.29%* | 4.42% | −0.04 | −22.8% | 53.9% | 58.4% | 62.9% |

\* AGG's near-zero CAGR is a **data artefact, not a return**: Yahoo monthly closes are price-only and exclude distributions, and bond funds pay most of their return as income. **VOO's "100% of 5-year windows positive" is survivorship** — its history starts 2010 and contains no bear market; the page flags it `SHORT·EXCL 2008`. SPY, with 2008 in the sample, is the honest number: **worst 10-year window −40.2%**.

**Fee drag:** same portfolio, same 8.71% CAGR over 20 years — 0.03% vs 0.60% expense ratio costs **~10% of terminal value**. The fee is the only certain input in the table.

### 5.3 The ETF class in this ledger is not evidence yet
Live payload says ETF PF **1.825**, WR 73.3% — with `total_picks: null`. Until n is published (W1) and the cell clears W3, that is a small-sample artefact. **I am not counting ETF as a proven edge today.**

---

## 6. Risk management — applied, and on its own page

`tools/risk_page_builder.py` → `reports/risk_metrics_live.json` + **`audit_dashboard/risk_management.html`** (10,351 bytes, self-contained). Methods: VaR/CVaR, Sortino, PSR, max DD (compounded), Ulcer, fractional Kelly, payoff ratio, Monte-Carlo risk of ruin, HHI concentration, fee drag, rolling-window base rates.

**Measured on the live ledger (n = 3,500 closed):**

| Metric | Value | Reading |
|---|---|---|
| Win rate | 41.6% | below break-even for the payoff ratio |
| Profit factor | **0.907** | gross wins < gross losses |
| Mean / median per trade | −0.154% / −0.873% | median worse than mean: wins are rarer but larger |
| CVaR 95% / 99% | −7.96% / −11.48% | expected loss in the worst 5% / 1% of trades |
| Skew | +0.573 | fat right tail — consistent with lottery-like payoffs |
| Max drawdown (compounded) | **−100%** (terminal −99.98%) | a negative-mean series compounds to zero |
| Kelly fraction | **−0.0538** | **bet size is zero** — arithmetic, not opinion |
| MC risk of ruin | **44.4%** over 200 trades | book halves with near-coin-flip odds |
| HHI by class | 0.385 | concentrated |
| Top emitter | kimi_riseoftheclaw 1,687 rows (**48.2%**) | one emitter is half the ledger |
| Censored | **87.4%** | headline status `INCOMPLETE` |

The page renders `INSUFFICIENT` rather than a number when n is inadequate, prints caveats inline, and carries a "what this page does not claim" block.

---

## 7. Probability of success and risk

| Claim | Confidence | Basis |
|---|---|---|
| Mutual funds can be a live pick class | **<10%** | structural: once-daily NAV, next-NAV fills |
| Low-fee index core positive over 10y+ | **~85–90%** | SPY: 90.2% of 287 ten-year windows positive, worst −40.2% |
| This system has a defensible prediction edge today | **<10%** | PF 0.907, Kelly −0.054, 0/8 emitters significant, 0/40 trials pass |
| ETF PF 1.825 is real | **Low** | n unpublished |
| Fixing D1/D2 changes reported WR | **High** | 37 fabricated flats sit in the denominator now |

**Risks of the plan itself:** W1/W2 are mechanical, low risk. W3 will likely empty the dashboard of promoted picks — correct, but it will look like a regression to anyone watching counts. W4/W5 are additive and cannot damage the ledger.

---

## 8. Subagent review — what was dispatched, and what it changed

**Cloud CLIs — all four failed, no output:**
`claude` → "Credit balance is too low" · `codex` → `failed to load models cache: unknown variant 'max'` · `gemini` → `IneligibleTierError` · `grok` → `MaxFilesWatch` crash on a worktree path.

**Local fleet — initially timed out, cause found:** `deepseek-r1:32b` was pinned on **100% GPU with `UNTIL 22 hours from now`**, starving every request. After unloading, models answered in seconds: `llama3.2:3b` 5s, `qwen2.5:14b` 23s, `qwen2.5:7b` 22s. Transcripts: `reports/subagent_review/`.

**Adopted (genuine catches):**
1. **`qwen2.5:14b` — the conflation critique.** Comparing exit to entry produces false negatives whenever entry is old. Replaced with exit-vs-own-day-close (§4.1). This changed the finding set: 38 → **37 fabricated**, and the detail now names the actual discrepancy instead of an inferred move.
2. **`qwen2.5:7b` — pick vs allocation was undefined.** Added the explicit definition in §5.1.

**Rejected, with reasons:**
- `qwen2.5:7b`: "`total_picks` null is overstated… does not specify which metrics" — it is a measured fact about all 9 rows, not a claim.
- `qwen2.5:14b`: NO-GO because "a comprehensive backtesting framework" is missing — W3 plus the pre-existing pre-registration harness is that framework; the gap is enforcement, not existence.
- `llama3.2:3b`: called the 87.4% figure an artefact of the 49 closed rows; the two sections are independent counts. (Its "no plan for handling reclassified rows" point is fair and is W1.)

**Honest limitation:** cloud models that can read the repo were unavailable, so the subagents reviewed a written evidence packet, not the files themselves. The peer-file cross-check is mine, not theirs.

---

## 9. Proposed edits

| File | Change | Risk |
|---|---|---|
| `tools/pnl_zero_validator.py` | **done** — the §4 gate | low (additive) |
| `tools/risk_page_builder.py` + `audit_dashboard/risk_management.html` | **done** — §6 page | low (additive) |
| `audit_trail/universal_pick_resolver.py` | refuse `exit_price == entry_price` on `TIME_EXIT` without market confirmation → `UNPRICED_CLOSE` | medium |
| `audit_trail/dashboard_generator.py` | tag `UNPRICED`; exclude from PnL aggregates; publish `n_raw`/`n_effective` | medium |
| `.github/workflows/` | run validator hourly + on PRs touching resolver/generator | low |
| `money_ready_verdict.py:180,195` | delete the `"0"` defaults | high impact, low code risk |
| fund PRs #759/#760 | rebase or re-open from a clean branch (3 weeks stale) | medium |

---

## 10. Limits

- Whether the 3,378 historical expired rows were net winners — not recoverable without `exit_price`.
- True n behind any class PF (`total_picks: null`).
- Whether #759/#760 still apply cleanly (`mergeable=UNKNOWN`) — needs a rebase attempt, not a guess.
- 11 of 49 closed zeros remain `UNVERIFIABLE_NO_ENTRY` — reported as such, not assumed either way.
- Fund history is price-only (no distributions): equity CAGR understated by roughly the dividend yield; bond figures understate badly.
