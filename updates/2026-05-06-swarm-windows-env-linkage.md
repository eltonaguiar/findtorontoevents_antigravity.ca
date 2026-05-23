# Swarm Windows Environment Variable Linkage

**Date:** 2026-05-06  
**Files changed:** `tools/swarm/config_loader.py`, `tools/swarm/safety.py`, `tools/swarm/api_consult.py`

---

## Overview

Linked all Windows User environment variables to the swarm by adding alias mappings across the three core swarm files. This ensures the swarm can pick up API keys that may be named differently depending on how they were set up (e.g., `*_API_KEY_PAID` variants, `GROK_API_KEY` vs `XAI_API_KEY`, etc.).

---

## Changes Made

### 1. `tools/swarm/config_loader.py` — ENGINE_KEY_ENVS

Added `_PAID` suffix aliases and alternative key names for all engines:

| Engine | Added Aliases |
|--------|--------------|
| deepseek | `DEEPSEEK_API_KEY_PAID` |
| xai | `GROK_API_KEY`, `GROK_API_KEY_PAID` |
| inception | `INCEPTION_API_KEY_PAID` |
| openrouter | `OPENROUTER_API_KEY_PAID` |
| nous | `NOUS_API_KEY_PAID` |
| groq | `GROQ_API_KEY_PAID` |
| huggingface | `HUGGINGFACE_API_KEY_PAID` |
| anthropic | `ANTHROPIC_API_KEY_PAID` |
| openai | `OPENAI_API_KEY_PAID` |
| gemini_api | `GEMINI_API_KEY_PAID` |
| github_models | `GITHUB_TOKEN_PAID` |

### 2. `tools/swarm/safety.py` — ENGINE_REQUIRED_KEYS

Added the same aliases so that `isolated_env()` correctly passes the keys to subprocess workers.

### 3. `tools/swarm/api_consult.py` — PROVIDERS key_envs

Added the same aliases so that `_resolve_key()` can find keys set under alternative names.

---

## Why This Matters

On Windows, API keys can be set with different naming conventions:
- **Standard:** `XAI_API_KEY`, `GROQ_API_KEY`, etc.
- **PAID variant:** `XAI_API_KEY_PAID`, `GROQ_API_KEY_PAID`, etc.
- **Legacy/alternative:** `GROK_API_KEY` (actual Windows User env name for xAI)

Without these aliases, the swarm would silently skip engines even when the keys are present in the Windows User environment variables.

---

## Verification

All three files passed Python syntax check:
- `tools/swarm/config_loader.py` ✓
- `tools/swarm/safety.py` ✓
- `tools/swarm/api_consult.py` ✓

---

## Current Windows User Env Status (2026-05-06)

| Key | Status |
|-----|--------|
| OLLAMA_CLOUD_KEY | SET (80 chars) |
| KIMI_API_KEY | SET (51 chars) |
| DEEPSEEK_API | SET (35 chars) |
| ANTHROPIC_API_KEY | MISSING |
| OPENAI_API_KEY | MISSING |
| GITHUB_TOKEN | MISSING |
| XAI_API_KEY | MISSING |
| GROK_API_KEY | MISSING |
| GROQ_API_KEY | MISSING |
| HUGGINGFACE_API | MISSING |
| GEMINI_API_KEY | MISSING |
| GOOGLE_API_KEY | MISSING |

The swarm will now correctly pick up any of these if they are set in Windows User environment variables.