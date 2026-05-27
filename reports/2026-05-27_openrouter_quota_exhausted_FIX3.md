---
title: "FIX 3: mercury + ring_261T silently no-op — OpenRouter key quota exhausted"
date: 2026-05-27
status: root cause identified, 3 options to fix
---

# FIX 3 — `OPENROUTER_API_KEY` 403 quota error

## Direct evidence (from ai-tournament-pipeline run 26479021538)

For **every** mercury and ring_261T persona × asset combination in the most-recent run:

```
[prompt] mercury/liquidity_grazer/CRYPTO (inception/mercury-2)...
[API] inception/mercury-2 error 403: {"error":{"message":"Key limit exceeded (total limit). Manage it using https://openrouter.ai/workspaces/default/keys/10c5b7deaea019a148c44134375b1a69c6a548550610246742eafe672b6ab1be","code":403}}
[fail] mercury/liquidity_grazer/CRYPTO: API call failed
```

The `OPENROUTER_API_KEY` GitHub secret is set, but the underlying OpenRouter account/key has **exhausted its credit limit**. Every attempt returns 403.

## Three options to restore mercury + ring_261T

### Option A — Top up the existing OpenRouter account (fastest)
1. Visit https://openrouter.ai/workspaces/default/keys/10c5b7deaea019a148c44134375b1a69c6a548550610246742eafe672b6ab1be
2. Either add credit OR generate a new key with credit
3. `gh secret set OPENROUTER_API_KEY` with the new value
4. Re-trigger `ai-tournament-pipeline.yml` workflow_dispatch

### Option B — Switch mercury to direct Inception API
`INCEPTION_API_KEY` is already in the repo secrets (set 2026-05-23). My PR #6 exposes it to the runner. Edit `config/model_persona_mapping.json` for `mercury`:

```diff
-  "api_key_env": "OPENROUTER_API_KEY",
-  "model_name": "inception/mercury-2",
-  "endpoint": "https://openrouter.ai/api/v1/chat/completions",
+  "api_key_env": "INCEPTION_API_KEY",
+  "model_name": "mercury-2",
+  "endpoint": "https://api.inceptionlabs.ai/v1/chat/completions",
```
(Verify the Inception endpoint path — that's a best-guess; may need confirmation from Inception's docs.)

### Option C — Skip mercury + ring_261T temporarily, lean on other providers
- Comment out `mercury` and `ring_261T` from `config/model_persona_mapping.json`
- Add 1-2 replacement models via providers you already have keys for (NVIDIA, GROQ, Cerebras, Together, Z.AI, etc.)
- Faster than waiting on OpenRouter to refill if budget-constrained

## Recommendation

**Option A** if you want the 1T-parameter Ring back (it's the most-distinct family in the tournament). **Option B** if you want a stable architecture not dependent on OpenRouter credits. **Option C** if you want max model diversity from your existing key pool.

A typical OpenRouter credit refill is $5-10, restoring weeks of daily tournament submissions for the 2 models. Probably the cheapest "fix" of the three.

## Impact when fixed

With mercury + ring_261T submitting again:
- Active model count after PR #6 + secret-sets: 7 → **9**
- Model diversity: 2 new families (Inception, InclusionAI) — currently the tournament's most-correlated 3 active models share Western open-weights roots
- ring_261T at 1T parameters provides extended-thinking depth that the smaller models can't match

## Filing
This is documentation for the user — no code change is needed in this PR (PR #6 already exposes INCEPTION_API_KEY which Option B would use). If you choose Option B, I can open a follow-up PR with the config edit. If Option A, it's pure key management on your side.
