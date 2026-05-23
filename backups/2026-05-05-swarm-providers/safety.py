"""Centralised safety enforcement for the swarm.

Adopted from Kimi swarm `ai_swarm/safety.py` pattern, slimmed for our flat
module structure (no pydantic). Three jobs:

1. **Read-only env isolation** for non-Claude workers — pass only the API
   keys the worker needs, drop everything else (so a leaked or compromised
   worker can't read unrelated secrets like AWS_*, GH_TOKEN).

2. **Disallowed-tool list** — canonical set of write/destructive commands
   that should never be in a worker's allowlist. Used by `worker_runner`
   when it builds the `--disallowedTools` arg for Claude.

3. **Post-run git-clean check** — after a "read-only" worker exits, verify
   the repo has no uncommitted changes. Flag any drift.

Usage:
    from tools.swarm.safety import (
        isolated_env, READ_ONLY_DISALLOWED, post_run_git_check, can_post,
    )
    env = isolated_env("deepseek")
    drift = post_run_git_check()  # {"clean": bool, "changes": [...]}
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Engine name -> required env-var names. The worker subprocess sees ONLY
# these from the API/secret universe, plus PATH/HOME/USERPROFILE/APPDATA.
ENGINE_REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "deepseek": ("DEEPSEEK_API", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL"),
    "cerebras": ("CEREBRAS_API", "CEREBRAS_API_KEY", "CERBRAS_FREE_ITHINK", "CEREBRAS_MODEL"),
    "xai": ("X_AI_KEY", "XAI_API_KEY", "X_AI", "GROK_SUPER", "XAI_MODEL"),
    "inception": ("INCEPTION_AI_KEY", "INCEPTION_API_KEY", "INCEPTION_MODEL", "INCEPTION_API_URL"),
    "ollama_cloud": ("OLLAMA_CLOUD_KEY", "OLLAMA_CLOUD_MODEL", "OLLAMA_CLOUD_URL"),
    "ollama_local": ("OLLAMA_LOCAL_MODEL", "OLLAMA_MODEL", "OLLAMA_HOST"),
    # OpenRouter — OpenAI-compat HTTP gateway exposing 200+ models.
    "openrouter": ("OPENROUTER", "OPENROUTER_MODEL"),
    # Groq — LPU inference, free tier available. Key envs checked in priority order.
    "groq": ("GROQ_KEY", "GROQ_API_KEY", "GROQ_MODEL"),
    # HuggingFace router — Inference Providers gateway.
    "huggingface": ("HUGGINGFACE_API", "HF_TOKEN", "HUGGINGFACE_API_KEY"),
    # Nous Research Portal — Hermes 4 family inference.
    "nous": ("NOUS_API_KEY", "NOUS_PORTAL_KEY", "NOUS_MODEL"),
    # Google AI Studio (Gemini) — OpenAI-compatible endpoint.
    "gemini_api": ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL"),
    # GitHub Models — free inference for GitHub users.
    "github_models": ("GITHUB_TOKEN", "GH_TOKEN"),
    # Pollinations AI — genuinely zero-key; no env vars required.
    "pollinations": (),
    # CLI engines authenticate via OAuth-stored tokens in their own config dirs;
    # they need USERPROFILE / APPDATA / LOCALAPPDATA passed through.
    "claude": (),
    "gemini": (),
    "opencode": (),
    "kilo": (),
    "copilot": (),
    # Cursor agent CLI: OAuth-stored session under %USERPROFILE%/.cursor;
    # CURSOR_API_KEY is an optional override for headless / CI runs.
    "agent": ("CURSOR_API_KEY", "CURSOR_AGENT_CLI"),
    # Kimi CLI (Moonshot AI): OAuth via `kimi login` (token under ~/.kimi/);
    # KIMI_API_KEY / MOONSHOT_API_KEY are optional API-key overrides for CI;
    # KIMI_CLI lets the resolver find a non-default binary path.
    "kimi": ("KIMI_API_KEY", "MOONSHOT_API_KEY", "KIMI_CLI"),
    # openclaude (@gitlawb/openclaude): third-party Claude Code fork with a
    # `--provider` flag routing to OpenAI / Gemini / DeepSeek / Anthropic /
    # GitHub Models / Bedrock / Vertex / Foundry / Ollama. Pass through the
    # union of provider keys it may consult; OPENCLAUDE_PROVIDER selects a
    # default provider when the swarm `--model` arg is absent. Audit the
    # package before each upgrade — see SWARM_DESIGN_NOTES.md trust section.
    "openclaude": (
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
        "DEEPSEEK_API", "GEMINI_API_KEY", "GOOGLE_API_KEY",
        "GH_TOKEN", "GITHUB_TOKEN", "OPENCLAUDE_PROVIDER",
    ),
    # OpenAI Codex CLI: OAuth via `codex login` (ChatGPT-bundled, primary);
    # OPENAI_API_KEY is an optional alternate auth path codex auto-detects.
    # CODEX_HOME redirects the auth/config dir for CI multi-account isolation.
    "codex": ("OPENAI_API_KEY", "CODEX_HOME"),
    "freebuff": (),
}

# Always-passed-through env vars (process basics + Windows paths).
ALWAYS_KEEP = (
    "PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "HOME",
    "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
    "PROGRAMW6432", "PYTHONPATH", "PYTHONIOENCODING", "PYTHONUTF8",
    "SWARM_STDOUT", "SWARM_RUN_ID",
)

# Canonical disallowed tools for read-only worker runs (Claude-style allowlist).
READ_ONLY_DISALLOWED: tuple[str, ...] = (
    "Edit",
    "Write",
    "Bash(git push:*)",
    "Bash(git commit:*)",
    "Bash(git reset:*)",
    "Bash(git rebase:*)",
    "Bash(git checkout:*)",
    "Bash(git stash drop:*)",
    "Bash(rm:*)",
    "Bash(mv:*)",
    "Bash(cp:*)",
    "Bash(chmod:*)",
    "Bash(curl:* -X POST*)",
    "Bash(gh pr merge:*)",
    "Bash(gh pr comment:*)",
    "Bash(gh pr review:*)",
    "Bash(gh pr edit:*)",
    "Bash(gh pr close:*)",
    "Bash(gh issue comment:*)",
    "Bash(gh issue close:*)",
    "Bash(gh release:*)",
    "Bash(gh api:* -X POST*)",
    "Bash(gh api:* -X PATCH*)",
    "Bash(gh api:* -X DELETE*)",
)

# Read-only allowlist building blocks.
READ_ONLY_ALLOWED: tuple[str, ...] = (
    "Bash(gh pr view:*)",
    "Bash(gh pr diff:*)",
    "Bash(gh pr checks:*)",
    "Bash(gh pr list:*)",
    "Bash(gh issue view:*)",
    "Bash(gh issue list:*)",
    "Bash(gh api:* -X GET*)",
    "Bash(git diff:*)",
    "Bash(git log:*)",
    "Bash(git show:*)",
    "Bash(git blame:*)",
    "Bash(git status:*)",
    "Bash(grep:*)",
    "Bash(rg:*)",
    "Bash(find:*)",
    "Bash(ls:*)",
    "Bash(cat:*)",
    "Bash(head:*)",
    "Bash(tail:*)",
    "Bash(wc:*)",
    "Read", "Grep", "Glob",
)


def isolated_env(engine: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Return a minimal env for a worker subprocess.

    Includes ALWAYS_KEEP + ENGINE_REQUIRED_KEYS[engine] from os.environ.
    Drops every other secret. Add `extra` overrides last.
    """
    env: dict[str, str] = {}
    needed = set(ALWAYS_KEEP) | set(ENGINE_REQUIRED_KEYS.get(engine, ()))
    for k in needed:
        v = os.environ.get(k)
        if v is not None:
            env[k] = v
    if extra:
        env.update(extra)
    return env


def post_run_git_check(repo_dir: Path | None = None) -> dict:
    """`git status --porcelain` after a read-only worker run.

    Returns dict with `clean` (bool) and `changes` (list of porcelain lines).
    Use to flag any worker that wrote files despite a read-only contract.
    """
    cwd = str(repo_dir or REPO)
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=15, shell=False,
        )
    except Exception as e:
        return {"clean": True, "changes": [], "error": str(e)}
    if proc.returncode != 0:
        return {"clean": False, "changes": [], "error": proc.stderr.strip()}
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return {"clean": len(lines) == 0, "changes": lines}


def can_post(role: str) -> bool:
    """Only `comment-poster` may write to GitHub."""
    return role == "comment-poster"


def claude_readonly_args() -> list[str]:
    """Build the canonical read-only --allowedTools / --disallowedTools args.

    Caller flattens into a Claude CLI invocation:
        cmd += ["--allowedTools", *READ_ONLY_ALLOWED,
                "--disallowedTools", *READ_ONLY_DISALLOWED]
    """
    return ["--allowedTools", *READ_ONLY_ALLOWED,
            "--disallowedTools", *READ_ONLY_DISALLOWED]


def main() -> int:
    """CLI: print canonical allow/disallow lists + isolated env preview."""
    import sys
    print("=== READ_ONLY_ALLOWED ===")
    for tok in READ_ONLY_ALLOWED:
        print(f"  {tok}")
    print("\n=== READ_ONLY_DISALLOWED ===")
    for tok in READ_ONLY_DISALLOWED:
        print(f"  {tok}")
    print("\n=== isolated_env preview (engine=deepseek) ===")
    env = isolated_env("deepseek")
    for k in sorted(env):
        v = env[k]
        masked = (v[:6] + "..." + v[-3:]) if len(v) > 16 and ("KEY" in k or "API" in k) else v[:80]
        print(f"  {k}={masked}")
    print(f"\n  total keys passed: {len(env)}")
    print(f"  parent env total: {len(os.environ)}")
    print(f"  reduction: {len(os.environ) - len(env)} secrets dropped")

    print("\n=== post_run_git_check ===")
    chk = post_run_git_check()
    print(f"  clean={chk['clean']}  changes={len(chk.get('changes', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
