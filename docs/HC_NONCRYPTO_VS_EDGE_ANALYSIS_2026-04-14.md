# High Conviction vs “edge” on non-crypto — validation & gap analysis (2026-04-14)

This document validates peer findings (Claude) against the **in-repo** dashboard snapshot and explains why **strict** High Conviction can show **no non-crypto** rows even when the UI documents **statistical edge** for some asset classes.

## 1. Two different meanings of “edge”

| Concept | What it measures | Where it shows |
|--------|-------------------|----------------|
| **HC explainer / manifest** | *Population-level* metrics (e.g. “EQUITY: PF 2.62 on n=119”) for picks that satisfied a **research filter** historically | `hcEdgeManifest()` in `audit_dashboard/template.html` |
| **Strict HC button** | Each **active** row must pass **shared gates 1–9** *and* **`passesValidatedEdgePerClass`** | `filterHcStrict` = `filterHighConvictionOrdered` → then per-class edge |

A cohort can show **PF > 1** in aggregate while **every current active row** fails **Gate 5** (strategy forward WR &lt; 45%), **Gate 4** (`strat_fwd_trades` &lt; 5), **Gate 2** (score &lt; 50 and trust &lt; 8), or **Gate 1** (score &lt; 40). The HC preset is **row-level**, not “this class is good on average.”

## 2. What strict HC does to non-crypto classes

`passesValidatedEdgePerClass` (browser + same logic in analysis scripts):

- **CRYPTO / EQUITY:** `score ≥ 50` and `trust ≥ 3` (after passing base HC gates).
- **FOREX:** `strat_fwd_wr ≥ 50%` (and all base gates).
- **COMMODITY, BOND, ETF, FUTURES:** **rejected** — manifest marks them weak / nodata / dead; strict HC does not admit them regardless of scanner output.

So **VT ETF-tagged** strategies (`asset_class: etf` from `antigravity_strategies.py`) **cannot** appear under strict HC until the manifest and this gate are deliberately changed.

## 3. Validated against `audit_dashboard/data/dashboard_data.json` (local snapshot)

Snapshot stats (run `python tools/_hc_noncrypto_diagnostic.py` to reproduce):

| Metric | Value |
|--------|--------|
| Active picks | **97** |
| By class | **CRYPTO 40**, **EQUITY 49**, **FOREX 2**, **SPORTS 6** |
| Non-crypto (excl. SPORTS) | **51** |

**Non-crypto primary gate failures (first failing check, non-crypto only):**

| Failure code | Count | Meaning |
|--------------|-------|---------|
| `Gate1_score_lt_40` | 44 | Score &lt; 40 |
| `Gate2_compound_score_trust` | 6 | Score &lt; 50 **and** trust &lt; 8 |
| `Gate5_fwd_wr_lt_45pct` | 1 | Forward WR &lt; 45% |

**Equity examples (abbreviated):**

- **goldmine_stocks:** Many rows `score=45`, `trust=4`, `strat_fwd_trades=0` → fail **Gate2** *before* forward gates in this snapshot. (After loader/PR fixes that populate `strat_fwd_*`, the **first** failure for many rows becomes **Gate 4** or **Gate 5**, not “hidden zero trades.”)
- **super_signals (SPY/QQQ):** `score=30`, `n=131`, `strat_fwd_wr ~35%` → fails **Gate 1** and **Gate 5**.
- **regime_terminal:** `score=30`, `n=20`, `strat_fwd_wr=40%` → fails **Gate 1** and **Gate 5**.

This aligns with Claude’s summary: **even with forward n**, **regime_terminal (~40%)** and **super_signals (~35%)** stay **below the 45% Gate 5 floor**. Goldmine’s **true** forward WR must be **≥ 45%** *on the strategy key used for the pick* to clear Gate 5 once Gate 4 is satisfied — a **~21%** leaderboard WR implies **no** HC pass on forward merit.

## 4. Crypto strict HC count (ordering / correlation)

Using the Python mirror of **`filterHighConvictionOrdered`** (batch **Gate 9** correlation semantics):

- **Base HC passes:** **4** picks on this snapshot (not 6).
- Evaluating **`passesHighConvictionPick` per row in isolation** (no sequential `corrPairs` registry) can yield **more** rows — the **UI strict path uses ordered filtering**, so the **live table can show fewer** rows than an isolated row-by-row count.

So **“3–6 strict HC picks, crypto-only”** is a reasonable **range**: snapshot timing, correlation dedup, and strict edge (`score ≥ 50` for crypto) compress the list.

## 5. CI / PR deployment timeline (peer table)

Claude’s workflow table (**runs 24402517939, 24405683811, 24408354405**, PRs **#200, #206, #207, #208**) was **not re-verified here** (would require `gh run list` / fresh artifact pull). Treat it as **operational context**.

**Local repo observation:** this `dashboard_data.json` still shows **goldmine `strat_fwd_trades=0`** on sample equity rows → consistent with a snapshot **before** goldmine forward-tracking fully appears in the embedded payload, or before the next generator run.

## 6. Why you remember “edge” on non-crypto but see no HC rows

1. **Explainer edge** = validated on **historical cohorts** with filters that **do not** match every live row’s `strategy` / `strat_fwd_wr` / score.
2. **Strict HC** = **per-row** gates + **hard** 45% forward WR for non-forex, **50%** for forex validated-edge, plus **ETF/commodity/futures/bond** **excluded** entirely.
3. **Score pipeline:** Several equity rows sit at **30** or **45** with **trust 4** — they never reach **50** or fail the **compound** rule, so they drop before or with forward stats.
4. **Inverse / contrarian paths** (e.g. PR **#208**): if **`wired_in_scanner: false`** until validation completes, they **do not** add picks yet — correct expectation for **days–weeks** after enable.

## 7. What is actually needed for non-crypto **strict** HC

**Without changing policy:**

| Class | Requirement |
|-------|----------------|
| **EQUITY** | At least one active source with rows meeting: gates 1–9, `score≥50`, `trust≥3`, `strat_fwd_trades≥5`, `strat_fwd_wr≥45%`, and **independent-group** rules unless stamped tier bypass applies. Realistic near-term: **new or repaired strategy** with forward stats above floors, or **inverse** hypothesis validated and emitting rows that clear the same gates. |
| **FOREX** | Same as above, plus validated-edge **`strat_fwd_wr ≥ 50%`** (stricter than Gate 5’s 45%). |
| **ETF / others** | **Policy change:** extend `passesValidatedEdgePerClass` + manifest or introduce a **separate preset** (e.g. “HC (research)” without ETF exclusion). |

**Policy / product levers (explicit trade-offs):**

- Lower **`forwardWRMinPct`** or **forex** edge threshold for a **dedicated** preset — document dilution risk.
- **Stamped tier** path already bypasses **Gate 8** only; **Gate 5** still applies for tier B — won’t save **40%** WR strategies.
- **Separate UI mode:** “High conviction (gates only)” vs “High conviction + validated edge” so non-crypto **population edge** is visible without pretending each row passes strict WR.

## 8. Repeatable commands

```powershell
# Row-level non-crypto failure breakdown + strict HC by class
python tools/_hc_noncrypto_diagnostic.py

# Base HC + failure reasons (older script; per-row HC, no ordered corr)
python scratch_investigate_hc.py
```

## 9. Conclusion

- Claude’s **direction** is **correct**: with current gates and validated-edge rules, **strict HC stays crypto-heavy**; **equity** sources in the snapshot **fail score and/or forward WR**, and **goldmine** exposing real forward stats **does not unlock HC** if true WR is **~21%** and the floor is **45%**.
- The feeling that there is “edge” elsewhere is **consistent** with the **manifest** (class-level stats) but **inconsistent** with **per-row strict HC** until at least one **live** source satisfies **all** layers.
- **Next verification** after deploy: re-run `tools/_hc_noncrypto_diagnostic.py` on fresh `dashboard_data.json`, confirm goldmine `strat_fwd_*` populated, leaderboard WR ~peer quote, and **SPORTS** stripped from active per PR **#206**.
