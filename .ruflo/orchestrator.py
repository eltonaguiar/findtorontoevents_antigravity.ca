#!/usr/bin/env python3
"""
Ruflo-style Swarm Orchestrator for findtorontoevents_antigravity.ca

Adapts ruflo agent patterns (coder, reviewer, security-architect, tester, architect)
to Hermes delegate_task with free-tier models. Runs continuous swarms for:
- Audit strategy performance analysis
- GitHub hygiene (commits, PRs, Actions)
- New strategy ideation
- Bug/security hunting

Usage:
    python3 .ruflo/orchestrator.py --swarm audit        # One-shot audit swarm
    python3 .ruflo/orchestrator.py --swarm github       # One-shot github hygiene
    python3 .ruflo/orchestrator.py --swarm strategy     # One-shot strategy ideation
    python3 .ruflo/orchestrator.py --swarm bugs          # One-shot bug hunter
    python3 .ruflo/orchestrator.py --continuous          # Run all, loop forever
    python3 .ruflo/orchestrator.py --list-agents         # List registered agents

WINDOWS BRIDGE (Codebuff → WSL):
    wsl bash -c "cd /mnt/c/findtorontoevents_antigravity.ca && python3 .ruflo/orchestrator.py --swarm audit"
"""

import argparse
import json
import os
import subprocess
import sys
import time
import shutil
import yaml
from datetime import datetime, timezone
from pathlib import Path

# Ensure stdout/stderr can handle Unicode on Windows (cp1252 → utf-8)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ──────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────

REPO_ROOT = str(Path(__file__).resolve().parent.parent)
INSIGHTS_DIR = f"{REPO_ROOT}/swarm_runs/ruflo-insights"
AGENTS_DIR = f"{REPO_ROOT}/.ruflo/agents"
API_CONSULT = f"{REPO_ROOT}/tools/swarm/api_consult.py"

# Hermes binary — full path required for non-interactive WSL shells
HERMES_BIN = os.environ.get(
    "HERMES_BIN",
    shutil.which("hermes") or "/home/zerou/.local/bin/hermes"
)

# Default timeout per agent (seconds) — free models can be slow
DEFAULT_TIMEOUT = 300  # 5 minutes

# Free-tier model pool (OpenRouter) — coordinator picks per role
# NOTE: All OpenRouter :free suffix models are broken (HTTP 404/429).
# These use paid-tier OPENROUTER_API_KEY (~$0.001/1K tokens) — all tested OK 2026-05-05.
# MASSREVIEW 2026-05-05: Updated to confirmed-working free models.
# Key sources:
#   pollinations/default      → zero-key (no auth required)
#   OPENROUTER_FREE_KEY       → hy3-preview, nemotron-3-nano, nemotron-3-super, minimax-m2.5
#   GEMINI_FREE_KEY (Google AI Studio aistudio.google.com)
FREE_MODELS = {
    "coordinator":    "pollinations/default",          # zero-key, fast
    "researcher":     "tencent/hy3-preview:free",      # via OPENROUTER_FREE_KEY
    "coder":          "nvidia/nemotron-3-nano-30b-a3b:free",  # via OPENROUTER_FREE_KEY
    "reviewer":       "nvidia/nemotron-3-super-120b-a12b:free",  # via OPENROUTER_FREE_KEY
    "lightweight":    "minimax/minimax-m2.5:free",     # via OPENROUTER_FREE_KEY
    "fallback":       "google/gemini-2.5-flash",       # via GEMINI_FREE_KEY or OPENROUTER_API_KEY
}

PAID_MODELS = {
    "cerebras": {
        "model": "gpt-oss-120b",
        "key_envs": ("CEREBRAS_API_KEY_PAID", "CEREBRAS_API_KEY_FREE", "CEREBRAS_API", "CEREBRAS_API_KEY", "CERBRAS_FREE_ITHINK"),
    },
    "deepseek": {
        "model": "deepseek-chat",
        "key_envs": ("DEEPSEEK_API", "DEEPSEEK_API_KEY"),
    },
    "xai": {
        "model": "grok-3-latest",
        "key_envs": ("X_AI_KEY", "XAI_API_KEY", "X_AI", "GROK_SUPER"),
    },
    "inception": {
        "model": "mercury-2",
        "key_envs": ("INCEPTION_AI_KEY", "INCEPTION_API_KEY"),
    },
    "openrouter": {
        "model": "openai/gpt-4o-mini",
        "key_envs": ("OPENROUTER_API_KEY", "OPENROUTER"),
    },
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "key_envs": ("GROQ_KEY", "GROQ_API_KEY"),
    },
    "huggingface": {
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "key_envs": ("HUGGINGFACE_API", "HF_TOKEN", "HUGGINGFACE_API_KEY"),
    },
    "gemini_api": {
        "model": "gemini-2.5-flash-preview-05-20",
        "key_envs": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    },
    "github_models": {
        "model": "gpt-4o-mini",
        "key_envs": ("GITHUB_TOKEN", "GH_TOKEN"),
    },
    "pollinations": {
        "model": "openai",
        "key_envs": (),  # genuinely zero-key
    },
}

LOCAL_MODELS = {
    "coordinator": "llama3.2:3b",
    "researcher": "llama3.2:3b",
    "coder": "llama3.2:3b",
    "reviewer": "llama3.2:3b",
    "security-architect": "llama3.2:3b",
    "architect": "llama3.2:3b",
    "fallback": "llama3.2:3b",
}

# ──────────────────────────────────────────────────────────────────
# MODEL CONTEXT SPECS — context limits, output limits, quality tiers
# MASSREVIEW 2026-05-05: Added to prevent garbage data from tiny-context models.
# context_chars ≈ context_tokens * 4 (average English chars per token).
# output_max: safe output limit (leaves headroom below hard cap).
# quality_score: 1-3, used to weight Phase 1 candidate selection.
# ──────────────────────────────────────────────────────────────────
MODEL_SPECS: dict[str, dict] = {
    "pollinations/default": {
        "context_tokens": 8192, "prompt_max_chars": 24000, "output_max": 2048,
        "quality_score": 1, "context_warn_chars": 18000,
        "note": "Small context — truncate workspace summaries aggressively",
    },
    "tencent/hy3-preview:free": {
        "context_tokens": 32768, "prompt_max_chars": 90000, "output_max": 6000,
        "quality_score": 2, "context_warn_chars": 72000,
        "note": "Mid-size context — OK for moderate workspace context",
    },
    "nvidia/nemotron-3-nano-30b-a3b:free": {
        "context_tokens": 8192, "prompt_max_chars": 24000, "output_max": 3000,
        "quality_score": 1, "context_warn_chars": 18000,
        "note": "Small context, nano model — keep workspace context minimal",
    },
    "nvidia/nemotron-3-super-120b-a12b:free": {
        "context_tokens": 32768, "prompt_max_chars": 90000, "output_max": 6000,
        "quality_score": 2, "context_warn_chars": 72000,
        "note": "⚠️  UNVERIFIED: context window unconfirmed — conservative 32K estimate",
    },
    "minimax/minimax-m2.5:free": {
        "context_tokens": 8192, "prompt_max_chars": 24000, "output_max": 3000,
        "quality_score": 1, "context_warn_chars": 18000,
        "note": "Small context — use concise workspace context",
    },
    "google/gemini-2.5-flash": {
        "context_tokens": 128000, "prompt_max_chars": 400000, "output_max": 15000,
        "quality_score": 3, "context_warn_chars": 320000,
        "note": "Large context — can load substantial workspace context",
    },
    "cerebras/gpt-oss-120b": {
        "context_tokens": 8192, "prompt_max_chars": 22000, "output_max": 4000,
        "quality_score": 3, "context_warn_chars": 16000,
        "note": "Moderate context — decent quality but limited window",
    },
    "deepseek/deepseek-chat": {
        "context_tokens": 64000, "prompt_max_chars": 200000, "output_max": 8000,
        "quality_score": 3, "context_warn_chars": 160000,
        "note": "Large context — good for complex synthesis tasks",
    },
    "xai/grok-3-latest": {
        "context_tokens": 131072, "prompt_max_chars": 400000, "output_max": 15000,
        "quality_score": 3, "context_warn_chars": 320000,
        "note": "Large context — can handle full workspace dumps",
    },
}


def _get_model_spec(model_tag: str) -> dict:
    """Get MODEL_SPECS for a model tag, with safe defaults for unknown models.

    Unknown models get conservative defaults (8K context) to prevent
    silent garbage from over-sized prompts hitting small-context models.
    """
    return MODEL_SPECS.get(model_tag, {
        "context_tokens": 8192, "prompt_max_chars": 22000, "output_max": 2000,
        "quality_score": 1, "context_warn_chars": 16000,
        "note": "Unknown model — conservative defaults applied",
    })


def _safe_truncate_prompt(prompt: str, model_tag: str) -> tuple[str, str]:
    """Truncate prompt to safe length for model context window.

    Returns (truncated_prompt, warning). warning is '' if no truncation occurred.

    Strategy:
      - If prompt <= prompt_max_chars: return as-is
      - If prompt > prompt_max_chars: truncate to prompt_max_chars
        and preserve the task directive at the end (last 500 chars)
      - Log warning for aggressive truncation (prompt > 2x prompt_max_chars)
    """
    spec = _get_model_spec(model_tag)
    max_chars = spec["prompt_max_chars"]
    warn_chars = spec["context_warn_chars"]
    warning = ""

    if len(prompt) <= max_chars:
        if len(prompt) > warn_chars:
            warning = f"prompt ({len(prompt)} chars) approaching context limit ({warn_chars}) for {model_tag}"
        return prompt, warning

    preserved_tail = prompt[-500:] if len(prompt) > 500 else prompt
    truncated = prompt[: max(max_chars - 500, 500)] + "\n\n[...truncated for context limit... ]\n\n" + preserved_tail

    if len(prompt) > max_chars * 2:
        warning = (f"⚠️  PROMPT TRUNCATED: {len(prompt)} chars → {max_chars} chars "
                   f"for {model_tag} (context={spec['context_tokens']} tokens). "
                   f"Task directive preserved in last 500 chars. "
                   f"Consider reducing workspace context for this model.")
    else:
        warning = f"prompt truncated: {len(prompt)} → {max_chars} chars for {model_tag}"

    return truncated, warning


def _validate_output_quality(output: str, model_tag: str) -> tuple[bool, str]:
    """Validate that a model output is likely high-quality given its context limits.

    Returns (is_valid, reason).
    is_valid=True means output passes quality gate.
    is_valid=False means output is likely garbage (truncated, garbled, too short).
    """
    spec = _get_model_spec(model_tag)

    if not output or not output.strip():
        return False, "empty output"

    min_useful_chars = 50
    if len(output.strip()) < min_useful_chars:
        return False, f"output too short ({len(output.strip())} chars, min {min_useful_chars}) — likely truncated or garbled"

    context_tokens = spec["context_tokens"]
    length_multiplier = 1.5 if context_tokens <= 8192 else 2.5
    if len(output) > spec["output_max"] * length_multiplier:
        return False, (f"output length ({len(output)} chars) exceeds model safe limit "
                       f"({spec['output_max']} * {length_multiplier}) for {model_tag} — may be truncated")

    stripped = output.strip()
    if stripped and stripped[-1] not in ".!?;:)":
        last_words = stripped[-100:]
        if any(indicator in last_words for indicator in ["...", "[truncat", "[omitted"]):
            return False, "output appears truncated (incomplete phrase detected)"

    words = stripped.split()
    if len(words) >= 3:
        unique_ratio = len(set(w.lower() for w in words)) / len(words)
        if unique_ratio < 0.15 and len(words) > 10:
            return False, "output appears to be repeated/garbage pattern"

    return True, "ok"

# Failover chain for runtime model rotation (tried in order after primary fails)
# NOTE: pollinations now 403 — FAILOVER uses paid-tier OPENROUTER_API_KEY.
# Working models (tested 2026-05-05): deepseek-chat <0.2s, gpt-4o-mini 0.3s, gemini-2.5-flash 0.5s
# MASSREVIEW 2026-05-05: FAILOVER_MODELS now uses confirmed-working free models.
# Priority: pollinations (zero-key) → OPENROUTER_FREE_KEY models → paid options.
FAILOVER_MODELS = [
    "pollinations/default",                            # 0: zero-key, works without any API key
    "tencent/hy3-preview:free",                       # 1: via OPENROUTER_FREE_KEY
    "nvidia/nemotron-3-nano-30b-a3b:free",           # 2: via OPENROUTER_FREE_KEY
    "google/gemini-2.5-flash",                        # 3: via GEMINI_FREE_KEY or OPENROUTER_API_KEY
    "minimax/minimax-m2.5:free",                      # 4: via OPENROUTER_FREE_KEY (last resort)
]

# Error patterns that trigger failover (checked case-insensitive against stderr)
FAILOVER_ERRORS = [
    "429",
    "rate limit",
    "exhausted",
    "timeout",
    "connect",
    "closed",
    "service temporarily unavailable",
    "provider error",
    "no endpoints available",
    "upstream error",
]


def should_failover(stderr_text, returncode):
    """Check if error suggests we should try failover model."""
    if stderr_text is None:
        stderr_text = ""
    stderr_lower = stderr_text.lower()
    for err in FAILOVER_ERRORS:
        if err.lower() in stderr_lower:
            return True
    # Non-zero exit with empty stderr usually means provider/network failure
    if returncode != 0 and not stderr_lower:
        return True
    return False


def get_failover_model(primary_model, attempt=1):
    """Get next model in failover chain. Attempt 0 = primary, 1+ = failover."""
    if attempt == 0:
        return primary_model
    # Filter out primary to avoid retrying the same model
    candidates = [m for m in FAILOVER_MODELS if m != primary_model]
    if not candidates:
        return FAILOVER_MODELS[-1]
    idx = attempt - 1  # attempt 1 → candidates[0], attempt 2 → candidates[1], etc.
    if idx >= len(candidates):
        return candidates[-1]  # Clamp to last available
    return candidates[idx]


def _has_any_key(env_names):
    return any(os.environ.get(name) for name in env_names)


def _paid_provider_for_role(role):
    role_map = {
        "researcher": "cerebras",
        "coder": "deepseek",
        "reviewer": "inception",
        "architect": "xai",
        "security-architect": "xai",
        "coordinator": "groq",
        "lightweight": "huggingface",
    }
    return role_map.get(role, "openrouter")


def check_paid_keys():
    available = {}
    for provider, cfg in PAID_MODELS.items():
        for env_name in cfg["key_envs"]:
            if os.environ.get(env_name):
                available[provider] = {
                    "model": cfg["model"],
                    "key_env": env_name,
                }
                break
    return available


def print_key_status():
    status = check_paid_keys()
    if not status:
        print("[ORCHESTRATOR] No paid API keys detected.")
        return
    print(json.dumps(status, indent=2))


# Agent definitions (also loadable from .ruflo/agents/*.yaml)
AGENTS = {
    "audit_researcher": {
        "role": "researcher",
        "model": FREE_MODELS["researcher"],
        "goal": (
            "Analyze the findtorontoevents.ca /audit dashboard data. "
            "Read audit_trail/data/universal_resolved_picks.json, battleground/data/*, "
            "and MySQL picks tables (via mysql_client.py or direct SQL). "
            "Identify: (1) strategies with forward_wr < 0.55, (2) stale strategies (no picks in 7+ days), "
            "(3) non-crypto elite score starvation, (4) anti-predictive weight leakage, "
            "(5) retired strategies still emitting. Return ONLY JSON: {\"findings\": [...], \"top_actions\": [...]}"
        ),
    },
    "audit_quant": {
        "role": "coder",
        "model": FREE_MODELS["coder"],
        "goal": (
            "Quantitative audit: check updates/universal_resolved_picks.json for WR by asset class. "
            "Look for regime gate deployment status, transaction cost modeling, inverse trade backtests. "
            "Check if forward resolution tracker is still broken (all forward_wr=0.5). "
            "Return JSON with numeric evidence and recommended code fixes."
        ),
    },
    "github_hygiene": {
        "role": "reviewer",
        "model": FREE_MODELS["reviewer"],
        "goal": (
            "GitHub hygiene check: use gh CLI to list open PRs, recent commits, failed Actions runs. "
            "Check for: (1) PRs older than 7 days, (2) failing workflows, (3) commits without tests, "
            "(4) workflow files in worktrees vs main .github/workflows mismatch. "
            "Return JSON: {\"prs\": [...], \"failed_actions\": [...], \"recommendations\": [...]}"
        ),
    },
    "bug_hunter": {
        "role": "security-architect",
        "model": FREE_MODELS["coordinator"],
        "goal": (
            "Hunt bugs in the codebase. Search for: (1) Python scripts with hardcoded paths, "
            "(2) SQL injection risks in mysql_client.py, (3) race conditions in cron scripts, "
            "(4) stale reference to antigravity_ca instead of antigravity.ca, "
            "(5) strategies with elite_score > 90 but forward_wr = 0.5 (ghost elite), "
            "(6) unclosed DB connections, (7) missing error handling. "
            "Return JSON: {\"bugs\": [{\"file\": \"<path>\", \"line\": \"<num>\", \"severity\": \"<HIGH|MEDIUM|LOW>\", \"fix\": \"<description>\"}]}"
        ),
    },
    "strategist": {
        "role": "architect",
        "model": FREE_MODELS["coordinator"],
        "goal": (
            "Strategy ideation: read updates/strong_strategy_per_asset_class_*.md, "
            "battleground/data/chatgpt_combined_signals.json, and any what-if or near-pick docs. "
            "Propose 3 new trading strategies with: name, asset class, expected edge, "
            "implementation sketch, risk controls. Return JSON array."
        ),
    },
    "brainstorm_reviewer": {
        "role": "reviewer",
        "model": PAID_MODELS.get("cerebras", {}).get("model", "deepseek-chat"),
        "goal": (
            "You are the synthesizer in a brainstorm-then-review swarm. "
            "You will receive outputs from multiple brainstorm models. "
            "Critically review all candidates, identify consensus and disagreements, "
            "rank by quality, and produce a final synthesis with citations. "
            "Return ONLY JSON: {\"synthesis\": \"...\", \"ranking\": [...], \"agreements\": [...], \"disagreements\": [...]}"
        ),
    },
}


# ──────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ──────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sanitize_keys(text):
    """Redact API keys, tokens, and secrets from output.

    FIX 2026-05-05: expanded from 10 to 22 patterns to cover modern key
    formats (Anthropic sk-ant-*, Gemini AIza*, GitHub fine-grained tokens,
    JWT eyJ..., MongoDB conn strings, PEM private keys, etc.).
    """
    import re
    patterns = [
        # OpenAI keys
        r'sk-[a-zA-Z0-9_-]{32,96}',
        r'sk-proj-[a-zA-Z0-9_-]{32,100}',
        # Anthropic keys (sk-ant-*, sk-ant-api03-*)
        r'sk-ant-[a-zA-Z0-9_-]{32,64}',
        r'sk-ant-api03-[a-zA-Z0-9_-]{32,100}',
        # Cerebras / xAI proprietary formats
        r'csk-[a-zA-Z0-9]{40,60}',
        r'xai-[a-zA-Z0-9]{50,70}',
        # Gemini / Google AI Studio keys
        r'AIza[0-9A-Za-z_-]{35,42}',
        r'(?i)GOOGLE_?API_?KEY["\'\s:=]+[a-zA-Z0-9_-]{35,42}',
        # Modern GitHub tokens (fine-grained PATs, classic tokens)
        r'github_pat_[a-zA-Z0-9_]{22,82}',
        r'ghp_[a-zA-Z0-9]{36,48}',
        r'ghs_[a-zA-Z0-9]{36,48}',
        r'gho_[a-zA-Z0-9]{36,48}',
        r'ghu_[a-zA-Z0-9]{36,48}',
        r'ghr_[a-zA-Z0-9]{36,48}',
        # JWT tokens (eyJ...eyJ...signature)
        r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
        # MongoDB connection strings (mongodb://user:pass@host)
        r'mongodb(\+srv)?://[^\s"\']+:[^\s@/"\']+@[^\s"\']+',
        # Bearer tokens
        r'Bearer\s+[a-zA-Z0-9\-_\.]{20,80}',
        # Generic API key patterns
        r'(?i)"api_key"\s*:\s*"[^"]{20,}"',
        r'(?i)api[_-]?key["\s:=]+[a-zA-Z0-9_-]{32,}',
        # Private keys (PEM format)
        r'-----BEGIN [A-Z ]+PRIVATE KEY-----',
        r'-----BEGIN OPENSSH PRIVATE KEY-----',
        # OpenAI/Azure endpoint keys (azure-specific)
        r'[a-f0-9]{32}\.azurewebsites\.net',
        r'[a-f0-9]{32}\.cognitiveservices\.azure\.com',
    ]
    for p in patterns:
        text = re.sub(p, '[REDACTED]', text, flags=re.IGNORECASE)
    return text


def load_yaml_agents():
    """Load additional agent definitions from .ruflo/agents/*.yaml files."""
    agents_dir = Path(AGENTS_DIR)
    if not agents_dir.is_dir():
        return {}
    loaded = {}
    for yf in sorted(agents_dir.glob("*.yaml")):
        try:
            with open(yf, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                print(f"[ORCHESTRATOR] skip {yf.name}: root is not a dict (got {type(data).__name__})", file=sys.stderr)
                continue
            if "role" not in data or "goal" not in data:
                # Warn but still load — merge loop fills in defaults from inline AGENTS.
                # Only skip if key already exists in AGENTS (inline is sufficient).
                key_missing = data.get("type", yf.stem)
                if key_missing not in AGENTS:
                    print(f"[ORCHESTRATOR] skip {yf.name}: missing 'role'/'goal' and no inline fallback for '{key_missing}'", file=sys.stderr)
                    continue
                print(f"[ORCHESTRATOR] warn {yf.name}: missing 'role'/'goal'; will use inline default", file=sys.stderr)
            key = data.get("type", yf.stem)
            loaded[key] = data
        except Exception as e:
            print(f"[ORCHESTRATOR] Warning: failed to load {yf}: {e}", file=sys.stderr)
    return loaded


# ──────────────────────────────────────────────────────────────────
# HERMES INVOCATION
# ──────────────────────────────────────────────────────────────────

def verify_hermes():
    """Check that hermes binary is callable."""
    try:
        result = subprocess.run(
            [HERMES_BIN, "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            print(f"[ORCHESTRATOR] Hermes: {version}")
            return True
    except Exception as e:
        print(f"[ORCHESTRATOR] ERROR: Hermes not accessible at {HERMES_BIN}: {e}", file=sys.stderr)
        return False
    print(f"[ORCHESTRATOR] ERROR: Hermes returned non-zero exit code", file=sys.stderr)
    return False


def run_hermes_direct(agent_key, timeout=DEFAULT_TIMEOUT, max_failover_attempts=3):
    """
    Run a hermes agent query directly (non-interactive, no tmux).
    Uses: hermes chat -q "prompt" -Q --source tool --yolo

    Supports runtime model failover: on rate limits or provider errors,
    rotates through FAILOVER_MODELS chain with exponential backoff.
    """
    agent = AGENTS.get(agent_key)
    if not agent:
        print(f"[ORCHESTRATOR] Unknown agent: {agent_key}", file=sys.stderr)
        return None

    primary_model = agent['model']

    for attempt in range(max_failover_attempts):
        current_model = get_failover_model(primary_model, attempt)
        model_label = f"primary ({primary_model})" if attempt == 0 else f"failover-{attempt} ({current_model})"

        print(f"[ORCHESTRATOR] Running {agent_key} (attempt {attempt+1}/{max_failover_attempts}, {model_label}, timeout={timeout}s)...")

        # Build the prompt with current model
        prompt_parts = [
            f"You are a {agent['role']} agent in a ruflo-inspired swarm.",
            f"Workspace: {REPO_ROOT}",
            f"Only use paths under {REPO_ROOT}. Do NOT use /mnt/c/Windows/System32.",
            f"Use model: {current_model}",
            "Output JSON ONLY. No markdown wrappers, no explanations, no ```json.",
            "Sanitize any API keys in your output (replace with [REDACTED]).",
            "",
            f"TASK: {agent['goal']}",
        ]
        prompt = "\n".join(prompt_parts)

        cmd = [
            HERMES_BIN, "chat",
            "-q", prompt,
            "-Q",              # quiet mode: no banner, spinner, tool previews
            "--source", "tool", # mark as tool/integration session
            "--yolo",           # auto-approve dangerous commands (trusted context)
            "--ignore-user-config",  # use built-in defaults for isolation
            "--model", current_model,  # 2026-05-05 fix: was prompt-text only,
                                        # never reached the CLI. Caused all agents
                                        # to use Hermes' configured default model
                                        # regardless of YAML, producing
                                        # 'HTTP 404: No endpoints found for .'
                                        # when default was empty/broken. Evidence:
                                        # swarm_runs/ruflo-insights/bugs_bug_hunter_*
                                        # and github_github_hygiene_* (3 runs all
                                        # 404'd with empty model in URL).
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=REPO_ROOT,
            )
            output = result.stdout.strip()
            stderr = result.stderr.strip()

            # Check if recoverable error + more attempts remain → failover
            if should_failover(stderr, result.returncode) and attempt < max_failover_attempts - 1:
                trigger = stderr[:200] if stderr else f'returncode={result.returncode}'
                print(f"[ORCHESTRATOR] Failover triggered: {trigger}", file=sys.stderr)
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                continue

            if result.returncode != 0:
                print(f"[ORCHESTRATOR] {agent_key} exited with code {result.returncode}", file=sys.stderr)
                if stderr:
                    print(f"[ORCHESTRATOR] stderr: {stderr[:500]}", file=sys.stderr)

            # Success or non-recoverable error — return whatever we got
            return sanitize_keys(output) if output else None

        except subprocess.TimeoutExpired:
            print(f"[ORCHESTRATOR] {agent_key} timed out after {timeout}s", file=sys.stderr)
            if attempt < max_failover_attempts - 1:
                print(f"[ORCHESTRATOR] Retrying with failover model...", file=sys.stderr)
                time.sleep(2 ** attempt)
                continue
            return None
        except Exception as e:
            print(f"[ORCHESTRATOR] {agent_key} error: {e}", file=sys.stderr)
            if attempt < max_failover_attempts - 1:
                time.sleep(2 ** attempt)
                continue

    print(f"[ORCHESTRATOR] {agent_key}: All {max_failover_attempts} failover attempts exhausted.", file=sys.stderr)
    return None


def run_hermes_tmux(agent_key, timeout=DEFAULT_TIMEOUT):
    """
    Fallback: Run hermes agent via tmux session (for cases where direct mode fails).
    """
    agent = AGENTS.get(agent_key)
    if not agent:
        print(f"[ORCHESTRATOR] Unknown agent: {agent_key}", file=sys.stderr)
        return None

    prompt = (
        f"You are a {agent['role']} agent in a ruflo-inspired swarm.\n"
        f"Workspace: {REPO_ROOT}\n"
        f"Only use paths under {REPO_ROOT}. Do NOT use /mnt/c/Windows/System32.\n"
        f"Use model: {agent['model']}\n"
        f"Output JSON ONLY. No markdown wrappers, no explanations, no ```json.\n"
        f"Sanitize any API keys in your output (replace with [REDACTED]).\n\n"
        f"TASK: {agent['goal']}"
    )

    ts = now_iso().replace(":", "-")
    session = f"ruflo_{agent_key}_{ts}"
    safe_prompt = prompt.replace("'", "'\"'\"'")

    # Build tmux command with hermes chat -q
    # 2026-05-05 fix: pass --model so the agent's YAML-configured model is honored.
    # See run_hermes_direct() for the full bug context.
    cmd = (
        f"{HERMES_BIN} chat -q '{safe_prompt}' -Q --source tool --yolo "
        f"--ignore-user-config --model '{agent['model']}'"
    )
    tmux_cmd = (
        f"tmux new-session -d -s {session} -x 120 -y 40 "
        f"'{cmd}'"
    )

    print(f"[ORCHESTRATOR] Spawning {agent_key} via tmux session {session}...")
    try:
        subprocess.run(tmux_cmd, shell=True, check=True, timeout=15)
    except Exception as e:
        print(f"[ORCHESTRATOR] Error creating tmux for {agent_key}: {e}", file=sys.stderr)
        return None

    # Wait and capture — polling loop instead of a flat sleep so we can
    # return early if the session exits before the full timeout.
    print(f"[ORCHESTRATOR] Waiting up to {timeout}s for {agent_key} to complete...")
    poll_interval = 5  # seconds between checks
    elapsed = 0
    while elapsed < timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval
        # Check if the tmux session still exists.
        alive = subprocess.run(
            f"tmux has-session -t {session} 2>/dev/null",
            shell=True, timeout=5
        )
        if alive.returncode != 0:
            print(f"[ORCHESTRATOR] {agent_key} finished after ~{elapsed}s")
            break

    try:
        out = subprocess.run(
            f"tmux capture-pane -t {session} -p -S 0",
            shell=True, capture_output=True, text=True, timeout=15
        )
        text = sanitize_keys(out.stdout)
    except Exception as e:
        print(f"[ORCHESTRATOR] Error capturing tmux {session}: {e}", file=sys.stderr)
        text = None
    finally:
        subprocess.run(f"tmux kill-session -t {session} 2>/dev/null", shell=True, timeout=5)

    return text


def run_paid_api(agent_key, timeout=DEFAULT_TIMEOUT):
    """Run one agent via direct provider APIs through api_consult.py."""
    agent = AGENTS.get(agent_key)
    if not agent:
        print(f"[ORCHESTRATOR] Unknown agent: {agent_key}", file=sys.stderr)
        return None
    if not os.path.exists(API_CONSULT):
        print(f"[ORCHESTRATOR] Missing API consultant: {API_CONSULT}", file=sys.stderr)
        return None

    provider = _paid_provider_for_role(agent.get("role", "fallback"))
    cfg = PAID_MODELS.get(provider)
    if not cfg:
        return None
    if cfg["key_envs"] and not _has_any_key(cfg["key_envs"]):
        print(f"[ORCHESTRATOR] No key available for paid provider {provider}", file=sys.stderr)
        return None

    prompt = (
        f"You are a {agent['role']} agent in a ruflo-inspired swarm.\n"
        f"Workspace: {REPO_ROOT}\n"
        f"Only use paths under {REPO_ROOT}.\n"
        "Output JSON ONLY. No markdown wrappers, no explanations, no ```json.\n"
        "Sanitize any API keys in your output (replace with [REDACTED]).\n\n"
        f"TASK: {agent['goal']}"
    )

    cmd = [
        sys.executable,
        API_CONSULT,
        "--provider", provider,
        "--model", cfg["model"],
        "-",
    ]
    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=REPO_ROOT,
        )
    except Exception as e:
        print(f"[ORCHESTRATOR] paid tier error for {agent_key}: {e}", file=sys.stderr)
        return None

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        print(f"[ORCHESTRATOR] paid tier failed for {agent_key}: {stderr[:350]}", file=sys.stderr)
        return None
    output = (result.stdout or "").strip()
    return sanitize_keys(output) if output else None


def run_local_no_key(agent_key, timeout=DEFAULT_TIMEOUT):
    """Run one agent using local Ollama only (no API keys)."""
    agent = AGENTS.get(agent_key)
    if not agent:
        print(f"[ORCHESTRATOR] Unknown agent: {agent_key}", file=sys.stderr)
        return None
    if shutil.which("ollama") is None:
        print("[ORCHESTRATOR] local tier requested but `ollama` is not installed", file=sys.stderr)
        return None
    if not os.path.exists(API_CONSULT):
        print(f"[ORCHESTRATOR] Missing API consultant: {API_CONSULT}", file=sys.stderr)
        return None

    role = agent.get("role", "fallback")
    local_model = LOCAL_MODELS.get(role, LOCAL_MODELS["fallback"])
    prompt = (
        f"You are a {agent['role']} agent in a ruflo-inspired swarm.\n"
        f"Workspace: {REPO_ROOT}\n"
        f"Only use paths under {REPO_ROOT}.\n"
        "Output JSON ONLY. No markdown wrappers, no explanations, no ```json.\n"
        "Sanitize any API keys in your output (replace with [REDACTED]).\n\n"
        f"TASK: {agent['goal']}"
    )
    cmd = [
        sys.executable,
        API_CONSULT,
        "--provider", "ollama_local",
        "--model", local_model,
        "-",
    ]
    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=REPO_ROOT,
        )
    except Exception as e:
        print(f"[ORCHESTRATOR] local tier error for {agent_key}: {e}", file=sys.stderr)
        return None

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        print(f"[ORCHESTRATOR] local tier failed for {agent_key}: {stderr[:350]}", file=sys.stderr)
        return None
    output = (result.stdout or "").strip()
    return sanitize_keys(output) if output else None


def run_agent(agent_key, mode="direct", timeout=None, tier="free"):
    """Run a single agent and return its output."""
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    tier = (tier or "free").lower()
    if tier == "local":
        return run_local_no_key(agent_key, timeout=timeout)
    if tier == "paid":
        return run_paid_api(agent_key, timeout=timeout)
    if tier == "hybrid":
        paid = run_paid_api(agent_key, timeout=timeout)
        if paid:
            return paid
    if tier == "auto":
        local = run_local_no_key(agent_key, timeout=timeout)
        if local:
            return local

    if mode == "direct":
        result = run_hermes_direct(agent_key, timeout=timeout)
        if result is None and shutil.which("tmux"):
            print(f"[ORCHESTRATOR] Direct mode failed, falling back to tmux...")
            result = run_hermes_tmux(agent_key, timeout=timeout)
        return result
    else:
        return run_hermes_tmux(agent_key, timeout=timeout)


# ──────────────────────────────────────────────────────────────────
# INSIGHT STORAGE
# ──────────────────────────────────────────────────────────────────

def save_insight(swarm_name, agent_key, output):
    """Save agent output to a timestamped JSON file."""
    os.makedirs(INSIGHTS_DIR, exist_ok=True)
    ts = now_iso().replace(":", "-")
    fname = f"{INSIGHTS_DIR}/{swarm_name}_{agent_key}_{ts}.json"
    payload = {
        "swarm": swarm_name,
        "agent": agent_key,
        "timestamp": now_iso(),
        "output_format": "hermes_raw",
        "output": output,
    }
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[ORCHESTRATOR] ✓ Saved insight → {fname}")
    return fname


def compile_insights():
    """Compile all insights into a single COMPILED_latest.json."""
    if not os.path.isdir(INSIGHTS_DIR):
        print("[ORCHESTRATOR] No insights directory yet.")
        return None
    files = sorted(
        [f for f in os.listdir(INSIGHTS_DIR) if f.endswith(".json") and f != "COMPILED_latest.json"]
    )
    compiled = []
    for f in files[-50:]:  # last 50
        path = os.path.join(INSIGHTS_DIR, f)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                compiled.append({"file": f, **data})
        except Exception:
            pass

    summary_path = f"{INSIGHTS_DIR}/COMPILED_latest.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(compiled, f, indent=2)
    print(f"[ORCHESTRATOR] ✓ Compiled {len(compiled)} insights → {summary_path}")
    return summary_path


# ──────────────────────────────────────────────────────────────────
# SWARM ORCHESTRATION
# ──────────────────────────────────────────────────────────────────

def run_swarm_audit(mode="direct", timeout=None, tier="free"):
    """Run the audit swarm: researcher + quant in parallel."""
    print("\n" + "=" * 60)
    print("  SWARM: AUDIT PERFORMANCE")
    print("=" * 60)

    agents_list = ["audit_researcher", "audit_quant"]

    # Parallel execution for free tier (tmux) or paid tier (threaded api_consult)
    use_parallel = (mode == "direct" and shutil.which("tmux")) or tier in ("paid", "hybrid")
    if use_parallel:
        import threading
        results = {}
        results_lock = threading.Lock()

        def _run_agent_wrapped(key):
            output = run_agent(key, mode=mode, timeout=timeout, tier=tier)
            with results_lock:
                results[key] = output

        threads = []
        for key in agents_list:
            t = threading.Thread(target=_run_agent_wrapped, args=(key,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
    else:
        # Sequential direct mode
        results = {}
        for key in agents_list:
            results[key] = run_agent(key, mode=mode, timeout=timeout, tier=tier)

    for key in agents_list:
        output = results.get(key)
        if output:
            save_insight("audit", key, output)
        else:
            print(f"[ORCHESTRATOR] ✗ {key} produced no output", file=sys.stderr)


def run_swarm_github(mode="direct", timeout=None, tier="free"):
    """Run the GitHub hygiene swarm."""
    print("\n" + "=" * 60)
    print("  SWARM: GITHUB HYGIENE")
    print("=" * 60)

    output = run_agent("github_hygiene", mode=mode, timeout=timeout, tier=tier)
    if output:
        save_insight("github", "github_hygiene", output)
    else:
        print("[ORCHESTRATOR] ✗ github_hygiene produced no output", file=sys.stderr)


def run_swarm_strategy(mode="direct", timeout=None, tier="free"):
    """Run the strategy ideation swarm."""
    print("\n" + "=" * 60)
    print("  SWARM: STRATEGY IDEATION")
    print("=" * 60)

    output = run_agent("strategist", mode=mode, timeout=timeout, tier=tier)
    if output:
        save_insight("strategy", "strategist", output)
    else:
        print("[ORCHESTRATOR] ✗ strategist produced no output", file=sys.stderr)


def run_swarm_bugs(mode="direct", timeout=None, tier="free"):
    """Run the bug hunter swarm."""
    print("\n" + "=" * 60)
    print("  SWARM: BUG HUNTER")
    print("=" * 60)

    output = run_agent("bug_hunter", mode=mode, timeout=timeout, tier=tier)
    if output:
        save_insight("bugs", "bug_hunter", output)
    else:
        print("[ORCHESTRATOR] ✗ bug_hunter produced no output", file=sys.stderr)


def run_swarm_brainstorm_review(mode="direct", timeout=None, tier="free", task=None):
    """Run the brainstorm-then-review swarm.

    Two-phase workflow:
      Phase 1 (brainstorm)  — 6 fast/cheap models in parallel, each generates
                              a raw candidate answer independently.
                              Zero-key: uses pollinations + deepseek + hy3 (free tier).
      Phase 2 (review)      — 1 strong reviewer (cerebras/deepseek/xai) synthesizes
                              the 6 candidates into a final ranked answer with
                              citations to support each claim.

    Args:
        task: Optional task description. If None, uses a sensible default that
              references the repo context so brainstormers have something to work with.

    This is the first-class brainstorm_review mode: distinct from single-agent
    audit/strategy/bugs which use 1-2 agents. Brainstorm_review is inherently
    multi-model and multi-phase.
    """
    if task is None:
        task = (
            "Analyze the findtorontoevents.ca codebase and trading system. "
            "Focus on: (1) top 3 highest-priority bugs or code quality issues, "
            "(2) strategies with the most room for improvement, "
            "(3) any silent failures, data quality issues, or anti-patterns. "
            "Use the workspace at C:/findtorontoevents_antigravity.ca as context. "
            "Return specific file paths, line numbers, and actionable recommendations."
        )
    print("\n" + "=" * 60)
    print("  SWARM: BRAINSTORM → REVIEW (multi-model synthesis)")
    print("=" * 60)

    # NOTE: All OpenRouter :free models broken (HTTP 404/429) — pollinations also 403.
    # Use paid-tier OPENROUTER_API_KEY. Working models (tested 2026-05-05):
    # gpt-4o-mini (0.3s), gpt-4o (0.5s), gemini-2.5-flash (0.5s), deepseek-chat (0.1s)
    # MASSREVIEW 2026-05-05: replaced all broken/discontinued free models with confirmed-working ones.
    # Pollinations works with ZERO auth. The 4 OpenRouter-free models require OPENROUTER_FREE_KEY.
    brainstorm_models = [
        "pollinations/default",                      # ✅ zero-key, confirmed working
        "tencent/hy3-preview:free",                 # ✅ via OPENROUTER_FREE_KEY
        "nvidia/nemotron-3-nano-30b-a3b:free",     # ✅ via OPENROUTER_FREE_KEY
        "nvidia/nemotron-3-super-120b-a12b:free",  # ✅ via OPENROUTER_FREE_KEY
        "minimax/minimax-m2.5:free",                # ✅ via OPENROUTER_FREE_KEY
        # Reserve slot for Gemini or OpenCode if user configures those keys
        "google/gemini-2.5-flash",                  # ✅ requires GEMINI_FREE_KEY or OPENROUTER_API_KEY
    ]
    # Deduplicate if some models aren't available on current tier
    brainstorm_models = list(dict.fromkeys(brainstorm_models))

    # Phase 1: parallel brainstorm via ThreadPoolExecutor (~6x speedup)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    timeout_val = timeout or 120

    # Build prompt once (model tag injected per-call at print-time)
    prompt_head = (
        f"You are a brainstormer in a multi-model synthesis swarm.\n"
        f"Workspace: {REPO_ROOT}\n"
        f"Produce a concise, factual answer to the task below.\n"
        f"Include specific file paths, line numbers, or data points where relevant.\n"
        f"Do not hedge — state your answer directly.\n"
        f"If you lack information, say so explicitly.\n"
        f"\n"
        f"TASK: {task}"
    )

    brainstorm_outputs = []
    def _fetch_model(model_tag):
        # Run via api_consult directly (bypasses Hermes)
        result = _run_brainstorm_model(model_tag, prompt_head, timeout=timeout_val)
        return model_tag, result

    print(f"[ORCHESTRATOR] Phase 1 — launching {len(brainstorm_models)} parallel calls...")
    with ThreadPoolExecutor(max_workers=len(brainstorm_models)) as pool:
        futures = {pool.submit(_fetch_model, m): m for m in brainstorm_models}
        for future in as_completed(futures):
            model_tag, result = future.result()
            if result:
                brainstorm_outputs.append({"model": model_tag, "output": result})
                print(f"[ORCHESTRATOR]   ✓ {model_tag}: {len(result)} chars")
            else:
                print(f"[ORCHESTRATOR]   ✗ {model_tag}: failed (skipped)")

    if not brainstorm_outputs:
        print("[ORCHESTRATOR] ✗ brainstorm phase produced no outputs — cannot proceed", file=sys.stderr)
        return

    print(f"[ORCHESTRATOR] Phase 1 complete: {len(brainstorm_outputs)}/{len(brainstorm_models)} models responded")

    # Phase 2: review synthesis
    print("\n[ORCHESTRATOR] Phase 2 — Review synthesis")
    synthesis_prompt = (
        f"You are the reviewer/synthesizer in a brainstorm-then-review swarm.\n"
        f"{len(brainstorm_outputs)} brainstormers produced candidate answers below.\n"
        "Your job: critically review all candidates, identify consensus and disagreements,\n"
        "rank the answers by quality and confidence, and produce a final synthesis.\n"
        "For each claim, cite which brainstorm model supported it.\n"
        "If candidates contradict, note which is more credible and why.\n\n"
        "BRAINSTORM RESULTS:\n"
        + "\n\n".join(
            f"--- {c['model']} ---\n{c['output']}" for c in brainstorm_outputs
        )
    )

    # Phase 2: call reviewer directly via api_consult so we can pass synthesis_prompt
    reviewer_provider = PAID_MODELS.get("cerebras", {}).get("model", "deepseek-chat")
    # Use cerebras if available, else deepseek, else fall back to hermes via run_agent
    reviewer_call = None
    for provider_key in ["cerebras", "deepseek", "xai", "inception"]:
        if provider_key in PAID_MODELS and check_paid_keys().get(provider_key):
            reviewer_call = provider_key
            break

    if reviewer_call:
        try:
            import sys as _sys
            _sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "swarm"))
            from api_consult import call_openai_compat
            model_name = PAID_MODELS[reviewer_call].get("model", "deepseek-chat")
            reviewer_model_tag = f"{reviewer_call}/{model_name}"

            # Apply context safety to synthesis prompt too
            safe_synthesis, warn2 = _safe_truncate_prompt(synthesis_prompt, reviewer_model_tag)
            if warn2:
                print(f"[ORCHESTRATOR]   ⚠  reviewer ({reviewer_call}): {warn2}")

            reviewer_spec = _get_model_spec(reviewer_model_tag)
            synthesis_sampling = {"max_tokens": reviewer_spec["output_max"]}

            content, _meta = call_openai_compat(
                reviewer_call, safe_synthesis, model_name, sampling=synthesis_sampling,
            )
            if content:
                is_valid, reason = _validate_output_quality(content, reviewer_model_tag)
                output = content if is_valid else None
                if not is_valid:
                    print(f"[ORCHESTRATOR]   ⚠  reviewer quality gate: {reason} — using raw brainstorm", file=sys.stderr)
            else:
                output = None
        except Exception as e:
            print(f"[ORCHESTRATOR] reviewer API failed ({e}), falling back to run_agent", file=sys.stderr)
            output = None
    else:
        output = None

    if output:
        save_insight("brainstorm_review", "synthesis", output)
        print(f"[ORCHESTRATOR] ✓ synthesis complete: {len(output)} chars")
    else:
        # Fallback: save raw brainstorm outputs as insight
        combined = "\n\n".join(
            f"=== {c['model']} ===\n{c['output']}" for c in brainstorm_outputs
        )
        save_insight("brainstorm_review", "raw_brainstorm", combined)
        print("[ORCHESTRATOR] ⚠ reviewer failed — saved raw brainstorm only", file=sys.stderr)


def _run_brainstorm_model(model_tag: str, prompt: str, timeout: int = 120) -> str | None:
    """Run a single brainstorm model via api_consult (no Hermes needed).

    Applies context safety: prompt truncation + output quality validation.
    """
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "swarm"))
        from api_consult import call_openai_compat
    except ImportError:
        return None

    # Parse provider:model from OpenRouter-style tag
    parts = model_tag.split("/")
    if len(parts) >= 2:
        provider_raw = parts[0].lower()
        # Map known providers; anything else (nvidia, tencent, minimax, etc.)
        # goes through openrouter which routes to the correct backend.
        if provider_raw in ("deepseek", "xai", "inception", "cerebras", "groq",
                             "openrouter", "huggingface", "gemini", "github_models",
                             "pollinations", "nous", "ollama_cloud", "ollama_local"):
            provider = provider_raw
        else:
            # Unknown provider — route through openrouter as the gateway
            provider = "openrouter"
        model_name = parts[1]
        # For openrouter, the model_name stays as-is (e.g. nvidia/nemotron-3-nano-30b-a3b:free)
        # — openrouter's API accepts the full <vendor>/<model>:free format directly.
    else:
        return None

    # Apply context safety: truncate prompt if it exceeds model's context budget
    safe_prompt, warn = _safe_truncate_prompt(prompt, model_tag)
    if warn:
        print(f"[ORCHESTRATOR]   ⚠  {model_tag}: {warn}")

    spec = _get_model_spec(model_tag)
    max_output = spec["output_max"]
    # Pass max_tokens via sampling dict (call_openai_compat signature:
    # (provider, prompt, model_override, sampling=None))
    sampling = {"max_tokens": max_output}

    try:
        content, _meta = call_openai_compat(
            provider, safe_prompt, model_name, sampling=sampling,
        )
        if not content:
            return None

        # Validate output quality before returning
        is_valid, reason = _validate_output_quality(content, model_tag)
        if not is_valid:
            print(f"[ORCHESTRATOR]   ✗ {model_tag}: quality gate failed ({reason})")
            return None

        return content
    except Exception as e:
        print(f"[ORCHESTRATOR]   ✗ {model_tag}: API error ({e})")
        return None


def continuous_mode(cycle_minutes=30, mode="direct", timeout=None, tier="free"):
    """Run all swarms in a continuous loop."""
    print(f"[ORCHESTRATOR] Continuous mode: {cycle_minutes}min cycles. Ctrl+C to stop.")
    cycle = 0
    while True:
        cycle += 1
        print(f"\n{'=' * 60}")
        print(f"  CYCLE {cycle} — {now_iso()}")
        print(f"{'=' * 60}")

        run_swarm_audit(mode=mode, timeout=timeout, tier=tier)
        run_swarm_github(mode=mode, timeout=timeout, tier=tier)
        run_swarm_strategy(mode=mode, timeout=timeout, tier=tier)
        run_swarm_bugs(mode=mode, timeout=timeout, tier=tier)
        compile_insights()

        print(f"[ORCHESTRATOR] ✓ Cycle {cycle} complete. Sleeping {cycle_minutes}min...")
        try:
            time.sleep(cycle_minutes * 60)
        except KeyboardInterrupt:
            print("\n[ORCHESTRATOR] Interrupted. Compiling final insights...")
            compile_insights()
            break


def list_agents():
    """List all registered agents from built-in (which includes YAML-merged)."""
    # AGENTS already has built-in + YAML-merged (done before calling this)
    # Separate into built-in-only and YAML-merged for display
    BUILT_IN_KEYS = {"audit_researcher", "audit_quant", "github_hygiene", "bug_hunter", "strategist"}
    
    builtin = {k: v for k, v in AGENTS.items() if k in BUILT_IN_KEYS}
    merged = {k: v for k, v in AGENTS.items() if k not in BUILT_IN_KEYS}
    
    print(f"\n{'=' * 60}")
    print(f"  REGISTERED AGENTS ({len(AGENTS)} total)")
    print(f"{'=' * 60}")
    print(f"\n  Built-in ({len(builtin)}):")
    for key, agent in builtin.items():
        print(f"    • {key:25s}  role={agent['role']:20s}  model={agent['model']}")
    if merged:
        print(f"\n  YAML-loaded ({len(merged)}):")
        for key, agent in merged.items():
            print(f"    • {key:25s}  role={agent['role']:20s}  model={agent['model']}")
    print()


# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ruflo-style swarm orchestrator for Hermes Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 .ruflo/orchestrator.py --swarm audit
  python3 .ruflo/orchestrator.py --swarm audit --mode tmux
  python3 .ruflo/orchestrator.py --continuous
  python3 .ruflo/orchestrator.py --continuous --cycle-minutes 60
  python3 .ruflo/orchestrator.py --list-agents

Windows bridge (run from Codebuff / PowerShell):
  wsl bash -c "cd /mnt/c/findtorontoevents_antigravity.ca && python3 .ruflo/orchestrator.py --swarm audit"
"""
    )
    parser.add_argument("--swarm", choices=["audit", "github", "strategy", "bugs", "brainstorm_review", "all"],
                        help="Run one swarm (or 'all' for one-shot all 4)")
    parser.add_argument("--continuous", action="store_true",
                        help="Run all swarms continuously")
    parser.add_argument("--cycle-minutes", type=int, default=30,
                        help="Cycle interval in minutes (default: 30)")
    parser.add_argument("--mode", choices=["direct", "tmux"], default="direct",
                        help="Execution mode: direct (hermes chat -q) or tmux (default: direct)")
    parser.add_argument("--timeout", type=int, default=None,
                        help=f"Timeout per agent in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--list-agents", action="store_true",
                        help="List all registered agents")
    parser.add_argument("--check-keys", action="store_true",
                        help="Show which paid API keys are available")
    parser.add_argument("--tier", choices=["free", "paid", "hybrid", "local", "auto"], default="hybrid",
                        help="Model tier: free=Hermes free models, paid=direct API, hybrid=paid then free (default), local=keyless Ollama, auto=local then free")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip hermes binary verification")
    parser.add_argument("--task", type=str, default=None,
                        help="Task description for brainstorm_review swarm (required for that mode)")

    args = parser.parse_args()

    # Load YAML agents.
    #
    # ROOT CAUSE FIX 2026-05-05: previous logic was `if k not in AGENTS`, which
    # silently DROPPED every YAML agent whose `type:` matched an inline key
    # (all 5 of them — bug_hunter, audit_researcher, audit_quant,
    # github_hygiene, strategist). This contradicted the inline comment
    # ("YAML takes priority") and meant the richer YAML goal text — which
    # contains the explicit anti-hallucination contract ("If you cannot
    # inspect the file path, return unable_to_verify instead of inventing
    # findings") and the `evidence` field requirement — never reached the
    # model. That silent drop produced the 71% false-positive rate observed
    # on the bug_hunter run (5 of 7 reported bugs were hallucinated
    # paths/lines).
    #
    # Fix: YAML overrides inline (per-field merge so a YAML file that omits
    # `model` still inherits the inline default).
    yaml_agents = load_yaml_agents()
    # Shallow copy of AGENTS as base for merge — prevents mutation of the
    # module-level AGENTS dict during successive YAML agent reloads.
    _base = dict(AGENTS)
    for k, v in yaml_agents.items():
        existing = _base.get(k, {})
        AGENTS[k] = {
            "role": v.get("role", existing.get("role", "unknown")),
            "model": v.get("model", existing.get("model", FREE_MODELS["fallback"])),
            "goal": v.get("goal", existing.get("goal",
                          f"Execute {k} agent tasks from YAML config.")),
        }

    if args.check_keys:
        print_key_status()
        sys.exit(0)

    if args.list_agents:
        list_agents()
        sys.exit(0)

    # Verify hermes is callable only when we may execute hermes.
    hermes_needed = args.tier in ("free", "hybrid", "auto")
    if not args.no_verify and hermes_needed:
        if not verify_hermes():
            print("[ORCHESTRATOR] Cannot proceed without Hermes. Use --no-verify or choose --tier paid/local.", file=sys.stderr)
            sys.exit(1)

    mode = args.mode
    timeout = args.timeout
    tier = args.tier

    if args.swarm == "audit":
        run_swarm_audit(mode=mode, timeout=timeout, tier=tier)
        compile_insights()
    elif args.swarm == "github":
        run_swarm_github(mode=mode, timeout=timeout, tier=tier)
        compile_insights()
    elif args.swarm == "strategy":
        run_swarm_strategy(mode=mode, timeout=timeout, tier=tier)
        compile_insights()
    elif args.swarm == "bugs":
        run_swarm_bugs(mode=mode, timeout=timeout, tier=tier)
        compile_insights()
    elif args.swarm == "all":
        run_swarm_audit(mode=mode, timeout=timeout, tier=tier)
        run_swarm_github(mode=mode, timeout=timeout, tier=tier)
        run_swarm_strategy(mode=mode, timeout=timeout, tier=tier)
        run_swarm_bugs(mode=mode, timeout=timeout, tier=tier)
        compile_insights()
    elif args.swarm == "brainstorm_review":
        if args.task is None:
            print("[ORCHESTRATOR] Warning: no --task specified, using default. Pass --task \"...\" for best results.")
        run_swarm_brainstorm_review(mode=mode, timeout=timeout, tier=tier, task=args.task)
        compile_insights()
    elif args.continuous:
        continuous_mode(args.cycle_minutes, mode=mode, timeout=timeout, tier=tier)
    else:
        parser.print_help()
        sys.exit(1)
