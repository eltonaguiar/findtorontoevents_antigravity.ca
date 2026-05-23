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
FREE_MODELS = {
    "coordinator":    "meta-llama/llama-3.3-70b-instruct:free",
    "researcher":     "google/gemini-2.0-flash-exp:free",
    "coder":          "deepseek/deepseek-chat-v3.1:free",
    "reviewer":       "meta-llama/llama-3.3-70b-instruct:free",
    "lightweight":    "meta-llama/llama-3.2-3b-instruct:free",
    "fallback":       "meta-llama/llama-3.3-70b-instruct:free",
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
        "key_envs": ("HUGGINGFACE_API", "HF_TOKEN"),
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

# Failover chain for runtime model rotation (tried in order after primary fails)
FAILOVER_MODELS = [
    "google/gemini-2.0-flash-exp:free",   # 0: researcher tier
    "deepseek/deepseek-chat:free",          # 1: coder tier
    "meta-llama/llama-3.3-70b-instruct:free",   # 2: reviewer tier
    "tencent/hy3-preview:free",             # 3: coordinator/fallback tier
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
            "Return JSON: {\"bugs\": [{\"file\", \"line\", \"severity\", \"fix\"}]}"
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
}


# ──────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ──────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sanitize_keys(text):
    """Redact API keys, tokens, and secrets from output."""
    import re
    patterns = [
        r'sk-[a-zA-Z0-9]{32,96}',
        r'csk-[a-zA-Z0-9]{40,60}',
        r'xai-[a-zA-Z0-9]{50,70}',
        r'ghp_[a-zA-Z0-9]{36,}',
        r'gho_[a-zA-Z0-9]{36,}',
        r'ghu_[a-zA-Z0-9]{36,}',
        r'ghs_[a-zA-Z0-9]{36,}',
        r'ghr_[a-zA-Z0-9]{36,}',
        r'Bearer\s+[a-zA-Z0-9\-_]{20,}',
        r'key["\s:=]+[a-zA-Z0-9\-_]{32,}',
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

    # Wait and capture
    print(f"[ORCHESTRATOR] Waiting {timeout}s for {agent_key} to complete...")
    time.sleep(timeout)

    try:
        out = subprocess.run(
            f"tmux capture-pane -t {session} -p -S -500",
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
    if not _has_any_key(cfg["key_envs"]):
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
    parser.add_argument("--swarm", choices=["audit", "github", "strategy", "bugs", "all"],
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
    parser.add_argument("--tier", choices=["free", "paid", "hybrid", "local", "auto"], default="free",
                        help="Model tier: free=Hermes free models, paid=direct API, hybrid=paid then free, local=keyless Ollama, auto=local then free")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip hermes binary verification")

    args = parser.parse_args()

    # Load YAML agents
    yaml_agents = load_yaml_agents()
    # Merge YAML-loaded agents (YAML takes priority for duplicate keys)
    for k, v in yaml_agents.items():
        if k not in AGENTS:
            # Convert YAML format to internal format
            AGENTS[k] = {
                "role": v.get("role", "unknown"),
                "model": v.get("model", FREE_MODELS["fallback"]),
                "goal": v.get("goal", f"Execute {k} agent tasks from YAML config."),
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
    elif args.continuous:
        continuous_mode(args.cycle_minutes, mode=mode, timeout=timeout, tier=tier)
    else:
        parser.print_help()
        sys.exit(1)
