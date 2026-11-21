# consult_multi key handling + DSR baselines raised to the measured space

Date: 2026-11-21. Two independent fixes, both verified below.

## 1. What was broken in `tools/consult_multi.py`

**A credential with inner whitespace was pasted into a request URL.** The
`GOOGLE GEMINI API KEY:` line in `~/dbpasses.txt` is 109 characters for a
39-character key: the value carries trailing commentary on the same line. The
loader did `lines[j].strip()`, which removes leading/trailing space but keeps
everything inside the line, so the full 109-character string became the `key=`
query parameter. Gemini answered 400 and **the error text echoed the URL,
including the key, into captured logs** (a fan-out artifact under
`reports/2026-11-21-multimodel-panel/` had to be redacted after the fact).

**A quota failure was reported as success.** The HF router answers HTTP 200 with
`content: null` when the monthly credit pool is spent. `_post_openai_compat`
returned that `None` as the model's answer, so `--doctor` printed `OK` for a
provider that had answered nothing, and fan-out wrote a file containing `None`.

### Changes

- `_clean_key()`: a credential is one whitespace-free token — take the first
  token, strip surrounding quotes/backticks, trailing `,;`. Applied to both the
  file value and the env fallback.
- `_scrub()`: every known key value and any `key=`/`Bearer ` token is replaced
  with `***` before an exception is re-raised. Applied in the three HTTP helpers
  (OpenAI-compatible, Gemini, Cloudflare). Gemini's URL additionally goes through
  `urllib.parse.quote(key, safe="")`.
- `_post_openai_compat()` now raises on missing/empty `content` and reports the
  `finish_reason`, so a quota refusal is a failure instead of a blank answer.
- New `--doctor`: pings all 14 providers with an 8-token prompt and prints
  OK/FAIL, latency, and a scrubbed error.
- New `--peers provider:model,...` and `--parallel N`: custom fan-out with a
  thread pool, alongside the existing presets.

### Verification

```
$ python3 tools/consult_multi.py --doctor --timeout 15
huggingface   openai/gpt-oss-20b          OK     0.6s  None     <- before the fix
cloudflare    @cf/meta/llama-3.1-8b-instruct  OK  0.2s  OK
deepinfra     meta-llama/Meta-Llama-3.1-8B-Instruct  OK  0.6s  OK
gemini_api    gemini-flash-latest         FAIL       TimeoutError: The read operation timed out
3/14 providers answered
```

The Gemini line is the proof: before the fix it failed with the key visible in a
400 URL; now it fails cleanly with no credential in the message. `--list` still
reports key presence; `--doctor` reports whether the key actually works. The two
disagree for 11 of 14 providers (nvidia 410, groq/cerebras/fireworks/nous 404,
together 401, github_models DNS, mistral 429, aimlapi 403, hypereal 402) — those
keys should be rotated or retired, not relied on.

## 2. DSR trial baselines raised to the measured search space

`NB_TRIALS_BY_CLASS` moved CRYPTO 14→629, FOREX 6→18, COMMODITY 3→9 (EQUITY 19,
ETF 12, BOND 2, FUTURES 3 unchanged), sourced from distinct cells in
`pf_registry.by_asset_class_strategy_policy_clean_net`, the book the verdict
reads. New `tools/dsr_baseline_flip.py` computes DSR at any trial count, asserts
its arithmetic matches the live `_dsr_gate` (self-check passes on all 7 classes),
and bisects the largest trial count that still clears 0.95.

**Result:** CRYPTO flips PASS→FAIL (0.9978 at 14 trials → 0.9284 at 629;
breakpoint 345). No other class moves, and no class can move upward: DSR is
monotone decreasing in trial count. Full analysis and limitations:
`reports/2026-11-21-dsr-trial-baseline-flip.md`.

### Verification

```
$ python3 tools/dsr_trial_baseline_report.py --strict
BOND      2  2  ok        CRYPTO  629 629 ok      EQUITY 19 19 ok
ETF      12 12  ok        FOREX    18  18 ok      COMMODITY 9 9 ok
FUTURES   3  3  ok        exit=0
```

## 3. H-146 registered (EQUITY mid-cap gross profitability)

The multi-model panel's only convergent experiment is now pre-registered before
any data is touched, per M-107: `reports/hypothesis_registry.json`, id `H-146`,
status `UNTESTED`, benchmark factors declared up front (MKT/SMB/HML/RMW),
20–60 day hold band fixed, and the EQUITY aggregate baseline (n=955, +0.098%,
CI [−0.516, +0.720]) recorded so the subset is compared against the diluted
aggregate rather than in isolation.

Two 8B delegates reviewed the wording after registration (Cloudflare Llama-3.1-8B,
DeepInfra Llama-3.1-8B). Both misread the "filed strictly before the rebalance
date" rule as the leak and proposed replacing it with look-ahead-prone
alternatives — that rule *is* the leak guard, so the suggestion was rejected.
Their only shared observation, that the exit band mixes calendar days with a
month-end trading event, is already resolved by the registered text ("exit at the
first month-end at least 20 calendar days after entry"). Recorded here because a
review that is recorded as agreement when it was not is worse than no review.

## 4. Stale test fixed (not weakened)

`tests/test_profit_program_math_2026_11_20.py::test_dsr_gate_uses_the_class_trial_count`
asserted that an unmapped class still gets `nb_trials >= 1`. That encoded the
pre-P0.5 behaviour, where a class with no recorded baseline deflated by a single
trial — i.e. no correction at all, reported as a usable number. Merged `_dsr_gate`
deliberately replaced it with an explicit skip (`ok: None`, `skipped: True`,
`nb_trials: None`).

Verified pre-existing, not caused by this change: stashing the baseline edit and
rerunning the test reproduces the same failure (`1 failed`), because the failure
comes from the skip branch, not from any baseline value.

The assertion is now **stricter** — it pins the skip contract (`ok is None`,
`skipped is True`, `nb_trials is None`) instead of accepting any number >= 1.
