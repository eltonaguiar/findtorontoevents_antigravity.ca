@echo off
REM agentmemory startup script — updated 2026-05-16
REM Fixed: switched from local (OOM-prone xenova ~90MB model) to OpenRouter embeddings
REM Root cause of BM25-only mode: PowerShell Start-Process doesn't inherit $env: vars; must set via CMD set
set EMBEDDING_PROVIDER=openrouter
REM set OPENROUTER_API_KEY from Windows env — do NOT hardcode here (push protection)
REM Run: setx OPENROUTER_API_KEY "sk-or-..." in an admin CMD once, then restart
set OPENROUTER_EMBEDDING_MODEL=openai/text-embedding-3-small
set AGENTMEMORY_DROP_STALE_INDEX=true
set AGENTMEMORY_VERBOSE=1
cd /d C:\findtorontoevents_antigravity.ca
npx -y @agentmemory/agentmemory@0.9.17 > agentmemory.log 2>&1
