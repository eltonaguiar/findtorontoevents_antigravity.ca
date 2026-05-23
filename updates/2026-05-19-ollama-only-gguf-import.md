# Ollama-only local GGUF import (no LM Studio)

**Date:** 2026-05-19  
**Goal:** Run local money-ready consults with **Ollama only** on Windows 0.24.

## Problem

- `F:\Models\Ollama_GGUFs\*.gguf` are symlinks into `%USERPROFILE%\.ollama\models\blobs\`.
- `ollama create` with `FROM F:/.../library-*.gguf` returned **invalid model name** when the symlink target was missing or when only the symlink path was used.
- LM Studio was not installed; pipeline should not depend on it.

## Fix

1. **`tools/ollama_import_gguf.py`**
   - Resolves symlink → real blob path.
   - Builds Modelfile from `ollama show <template> --modelfile` (qwen/llama/mistral/deepseek heuristics).
   - `ollama create <tag> -f Modelfile` with absolute `FROM` (forward slashes).

2. **`tools/local_gguf_ollama_consult.py`** — rewritten for Ollama-only consult + optional `--import-missing`.

3. **`tools/local_gguf_consult.py`** — marked deprecated (LM Studio).

## Verify

```powershell
python tools/ollama_import_gguf.py --scan
python tools/ollama_import_gguf.py --import-all
# 6/17 ok on 2026-05-19 (remaining 11 = missing blobs → need ollama pull)
ollama list
```

Created tags include: `library-deepseek-r1-14b:latest`, `library-llama3.1-latest:latest`, `library-mistral-nemo-latest:latest`, `library-qwen2.5-coder-7b:latest`, etc.

## Next

- `ollama pull` for models with broken symlinks (gemma3, mixtral, 32b variants), then re-run `--import-all`.
- `python tools/local_gguf_ollama_consult.py --all-installed` for benchmark sweep.
