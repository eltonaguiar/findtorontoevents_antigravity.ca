"""Config loader for the swarm.

Adopted from Kimi swarm `ai_swarm/config.py` pattern:
- Loads `.env` from repo root if present (no python-dotenv dependency).
- Resolves `${VAR}` and `${VAR:-default}` placeholders in YAML/JSON config.
- Hard-fails if a required key is unresolved.
- Resolves engine API keys via the same env-name precedence as
  `tools/swarm/api_consult.py`.

Usage:
    from tools.swarm.config_loader import load_config, resolve_engine_key
    cfg = load_config("tools/swarm/swarm.config.example.json")
    key = resolve_engine_key("deepseek")  # raises if missing
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

ENGINE_KEY_ENVS: dict[str, tuple[str, ...]] = {
    "deepseek": ("DEEPSEEK_API", "DEEPSEEK_API_KEY"),
    "cerebras": ("CEREBRAS_API", "CEREBRAS_API_KEY", "CERBRAS_FREE_ITHINK"),
    "xai": ("X_AI_KEY", "XAI_API_KEY", "X_AI", "GROK_SUPER"),
    "inception": ("INCEPTION_AI_KEY", "INCEPTION_API_KEY"),
    "ollama_cloud": ("OLLAMA_CLOUD_KEY",),  # informational only
    "openrouter": ("OPENROUTER",),  # OpenAI-compat gateway, 200+ models
    "nous": ("NOUS_API_KEY", "NOUS_PORTAL_KEY"),  # Nous Portal inference API (Hermes 4 family), OpenAI-compat
    "groq": ("GROQ_KEY", "GROQ_API_KEY"),  # Groq LPU inference, OpenAI-compat, free tier available
    "huggingface": ("HUGGINGFACE_API", "HF_TOKEN", "HUGGINGFACE_API_KEY"),  # HF inference providers, OpenAI-compat, free tier
    # Kimi CLI is OAuth-primary; KIMI_API_KEY / MOONSHOT_API_KEY are
    # optional CI overrides. Empty key is a valid state for OAuth-bundled
    # CLIs, so config_loader.main() will print MISS but the engine still works.
    "kimi": ("KIMI_API_KEY", "MOONSHOT_API_KEY"),
    # Codex CLI is OAuth-primary (ChatGPT login); OPENAI_API_KEY is an
    # optional alternate-auth path. Empty key is a valid state for OAuth-only
    # use; main() will print MISS but the engine still works via OAuth.
    "codex": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "gemini_api": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}

_ENV_INTERPOLATE_RE = re.compile(
    r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::-(?P<default>[^}]*))?\}"
)


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    """Read a `.env`-style file into os.environ (only keys not already set).

    Returns the dict of keys actually applied. Missing file → no-op.
    Format: KEY=value, # comments, blank lines.
    """
    p = path or (REPO / ".env")
    applied: dict[str, str] = {}
    if not p.exists():
        return applied
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if not key:
            continue
        # Treat whitespace-only existing values as unset so .env can override
        # them. Empty/blank env vars are a common artifact of shell scripts
        # that do `export X="$Y"` when $Y is unset. Pinned by
        # tests/test_swarm_tooling.py::test_load_dotenv_overrides_empty_env.
        existing = os.environ.get(key, "")
        if not existing.strip():
            os.environ[key] = val
            applied[key] = val
    return applied


def interpolate(value):
    """Replace `${VAR}` / `${VAR:-default}` in strings (recurses into dict/list)."""
    if isinstance(value, str):
        def _sub(m: re.Match) -> str:
            name = m.group("name")
            default = m.group("default")
            v = os.environ.get(name)
            if v is None:
                if default is not None:
                    return default
                raise KeyError(f"unresolved env var ${{{name}}}")
            return v
        return _ENV_INTERPOLATE_RE.sub(_sub, value)
    if isinstance(value, dict):
        return {k: interpolate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [interpolate(v) for v in value]
    return value


def load_config(path: str | Path) -> dict:
    """Load JSON/YAML config, autoload .env, interpolate ${VAR}, return dict.

    Hard-fails on unresolved vars unless caller catches KeyError.
    """
    load_dotenv()
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError as e:
            raise RuntimeError("pyyaml required for .yaml configs: pip install pyyaml") from e
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    return interpolate(data)


def resolve_engine_key(engine: str, *, raise_if_missing: bool = True) -> str | None:
    """Return the first non-empty env value from ENGINE_KEY_ENVS[engine].

    Raises RuntimeError if missing and raise_if_missing (default).
    """
    load_dotenv()
    envs = ENGINE_KEY_ENVS.get(engine, ())
    for name in envs:
        v = os.environ.get(name)
        if v:
            return v
    if raise_if_missing:
        raise RuntimeError(
            f"no key for engine '{engine}' in env (checked {envs or '(unknown engine)'})"
        )
    return None


def main() -> int:
    """CLI: print resolved engine keys (masked) and missing ones."""
    load_dotenv()
    print(f"repo: {REPO}")
    print(f".env present: {(REPO / '.env').exists()}")
    print()
    for engine, envs in ENGINE_KEY_ENVS.items():
        try:
            key = resolve_engine_key(engine)
            mask = f"{key[:5]}...{key[-3:]} (len={len(key)})"
            print(f"  {engine:<14} OK   from $({envs[0]}) {mask}")
        except RuntimeError:
            print(f"  {engine:<14} MISS  checked {envs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
