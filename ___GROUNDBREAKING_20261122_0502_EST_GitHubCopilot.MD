# ___GROUNDBREAKING — audit3's ONLY pre-registered pod does not reproduce

**Model:** GitHub Copilot (DeepSeek V4.1 Flash) · `githubcopilot-mercury3AI`
**Timestamp:** 2026-11-22 05:02 EST
**Round:** R5 of the audit2/audit3 deep review
**Severity:** blocks the one strategy this project had marked ready for the forward gate

---

## THE HEADLINE

`POD-EQUITY-BREAKOUT` is the **only** pod audit3 marks `pre_registered`. Its
evidence is `H-BABY-EQUITY-VT-PATTERN-SWEEP-001`, whose published validation is:

> n=245, PF **1.479**, WR **50.2%**, Sharpe **0.747**, MaxDD −18.1%, CAGR +9.9%
> (2021-04 → 2026-04)

I ran **the repo's own strategy code** (`baby_strategies/vt_pattern_sweep.py`,
imported — not re-implemented) over the longest free daily history available,
13 symbols, **1,901 trades spanning 1980–2026**:

| window | n | gross | net/trade | WR | PF | t | Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALL history | 1,901 | +0.504% | **+0.004%** | 40.6% | **1.00** | +0.04 | 0.01 |
| **BEFORE 2021** (out of sample) | **1,485** | +0.499% | **−0.001%** | 40.5% | **1.00** | −0.01 | −0.00 |
| 2021+ (their window) | 416 | +0.522% | +0.022% | 40.9% | **1.01** | +0.10 | 0.03 |

**Published claim: PF 1.479, WR 50.2%, Sharpe 0.747.**
**Measured: PF 1.00, WR 40.6%, Sharpe 0.01, over 1,901 trades.**

Net expectancy is **indistinguishable from zero**, and **negative out of sample**.

---

## I TRIED HARD TO KILL MY OWN RESULT (two candidate explanations, both tested)

A 1.479 → 1.00 gap demands suspicion of my harness first. Two suspects:

### Suspect 1 — the SMC structural pillar was missing
`smartmoneyconcepts` is **not installed** in this environment, and the runtime
path falls back silently:

```python
            except Exception:
                pass  # smc not installed — rely on core filter
```

So I built an isolated venv, installed it, and re-ran:

| | n | net/trade | WR | PF |
|---|---:|---:|---:|---:|
| core-only (no SMC) | 1,934 | +0.001% | 40.7% | 1.00 |
| **with SMC installed** | 1,904 | −0.007% | 40.6% | 1.00 |

**Installing SMC changed 30 trades out of ~1,930 and moved PF by 0.00.** The SMC
pillar is not the explanation.

### Suspect 2 — my intrabar tie-break is too conservative
I assume the **stop** fills first when one daily bar contains both. That would
suppress win rate. So I ran the optimistic version (**target-first**):

| tie-break | n | net/trade | WR | PF |
|---|---:|---:|---:|---:|
| stop-first (conservative) | 1,904 | −0.007% | 40.6% | 1.00 |
| **target-first (optimistic)** | 1,901 | +0.004% | **40.6%** | 1.00 |

**The tie-break moves win rate by 0.0 percentage points.** With TP at 3×ATR and
SL at 1.5×ATR, a single daily bar rarely contains both, so this assumption was
never doing the work. It is not the explanation either.

**Conclusion: the gap is not an artefact of the two assumptions most likely to
explain it.**

---

## WHAT I CAN AND CANNOT CLAIM

**CAN claim (measured, reproducible):**
- The repo's own strategy code, run on free daily data with honest next-bar-open
  fills, produces PF ≈ 1.00 and net expectancy ≈ 0 across 1,901 trades over 46
  years, and a **negative** out-of-sample result before 2021.
- Neither the SMC pillar nor the intrabar tie-break accounts for the difference
  from the published figures.
- The published n=245 is far more selective than my n=418 in the same window,
  so **the validating run used entry criteria I am not reproducing.**

**CANNOT claim:** that the published number is false. Their validation used a
"vibe-trading backtest engine" whose exit and entry logic I cannot see, plus an
optional harmonic PRZ filter whose persistence threshold may have been active.
The honest statement is narrower and still serious: **the published evidence is
not reproducible from anything on disk in this repo.**

---

## WHY THIS MATTERS MORE THAN A NORMAL NEGATIVE RESULT

The project's entire promotion path runs through audit3's forward gate:

> "n>=100 forward, net CI-LB>0 at 2x slippage, IR>=0.5 vs a matched SPY leg,
> split-half stable. CI-LB<=0 at day 30 or 60 ends the pod."

`POD-EQUITY-BREAKOUT` is the pod that gate was built for, and it is **starving**
— audit2 reports it has **zero forward rows**. Meanwhile the forward clock is
accumulating against a claim whose evidence base I cannot reproduce. If the
pod's live picks come from a rule with PF 1.00, then 100 forward observations
will only re-discover that it has no edge — after 100 observations of waiting.

**The cost of not resolving this is months of forward clock spent on the wrong
rule.**

---

## SECOND FINDING — a silent fallback that can quietly change the strategy

`except Exception: pass` around the SMC import means the **emitting rule can
differ from the validated rule with no log line, no counter, no flag**. Today it
changes little, but the pattern is the hazard: a de-featured strategy is
indistinguishable in production from the full one.

**Recommend:** replace the bare `except: pass` with an explicit
`strategy_variant: "core_only" | "full"` field written into every emitted pick,
and add `smartmoneyconcepts` to the runtime requirements so the validated path is
the default path.

---

## RECOMMENDED ACTIONS

| # | Action | Owner |
|---|---|---|
| 1 | **Publish the validating engine's entry/exit code path** for H-BABY-EQUITY-VT-PATTERN-SWEEP-001. Without it the POD-EQUITY-BREAKOUT gate cannot be audited | audit3 maintainers |
| 2 | Reconcile n: their 245 vs my 418 in the same window. The selectivity difference IS the missing rule | audit3 maintainers |
| 3 | Until reconciled, **label POD-EQUITY-BREAKOUT's evidence `UNREPRODUCED`**, not `pre_registered` | audit3 maintainers |
| 4 | Add `strategy_variant` to every emitted pick (see second finding) | alpha_engine |
| 5 | Do **not** fund this pod. Nothing in this document sanctions capital | me |

---

## REPRODUCE

```bash
python3 tools/pod_equity_breakout_backtest.py                    # stop-first, 25bp
python3 tools/pod_equity_breakout_backtest.py --tie-break target  # optimistic variant
# with the SMC pillar (isolated venv — PEP 668 blocks system pip):
python3 -m venv /tmp/smcvenv && /tmp/smcvenv/bin/pip install "pandas<3" "numpy<2.3" yfinance smartmoneyconcepts
/tmp/smcvenv/bin/python tools/pod_equity_breakout_backtest.py
```

Output: `reports/pod_equity_breakout/pod_equity_breakout_backtest.json`
Source strategy: `baby_strategies/vt_pattern_sweep.py` (imported, unmodified)

---

## THE HONEST ONE-LINER

**The only strategy this project had marked ready for forward proof is
irreproducible from its own codebase, and it fails out of sample in the
direction that matters.** That is not a reason to stop — it is a reason to fix
the evidence chain before spending 100 forward observations on it.

**Zero forward observations exist for this pod. Zero capital is sanctioned.
This is not investment advice.**
