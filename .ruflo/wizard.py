#!/usr/bin/env python3
"""
Ruflo Swarm Wizard — Interactive Tier & Model Selection Guide

Helps the user choose the right model tier for their ruflo swarm.
Shows pros/cons of each tier, available paid keys, and generates
the correct orchestrator command.

Usage:
    python3 .ruflo/wizard.py              # Interactive mode
    python3 .ruflo/wizard.py --quick       # Non-interactive: show status and suggest best tier
    python3 .ruflo/wizard.py --tier paid   # Show paid tier config only
"""

import os
import sys
import json
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parent.parent)
API_CONSULT = f"{REPO_ROOT}/tools/swarm/api_consult.py"

# Paid model mapping (mirrors orchestrator.py PAID_MODELS)
PAID_MODELS = {
    "cerebras": {
        "model": "gpt-oss-120b",
        "key_envs": ("CEREBRAS_API_KEY_PAID", "CEREBRAS_API_KEY_FREE", "CEREBRAS_API", "CEREBRAS_API_KEY", "CERBRAS_FREE_ITHINK"),
        "description": "Fast LLM inference — Cerebras hardware. Good for research/coding tasks.",
        "cost": "Subscription tier — included with Cerebras account",
        "speed": "⚡ Very fast (hardware-accelerated)",
    },
    "deepseek": {
        "model": "deepseek-chat",
        "key_envs": ("DEEPSEEK_API", "DEEPSEEK_API_KEY"),
        "description": "Strong coding model — DeepSeek V3. Excellent for quantitative analysis.",
        "cost": "~$0.27/M input, ~$1.10/M output",
        "speed": "🚀 Fast",
    },
    "xai": {
        "model": "grok-3-latest",
        "key_envs": ("X_AI_KEY", "XAI_API_KEY", "X_AI", "GROK_SUPER"),
        "description": "Grok-3 — strong reasoning. Good for architecture/strategy tasks.",
        "cost": "XAI subscription credits",
        "speed": "⚡ Fast",
    },
    "inception": {
        "model": "mercury-2",
        "key_envs": ("INCEPTION_AI_KEY", "INCEPTION_API_KEY"),
        "description": "Mercury-2 — fast text model. Good for review/lightweight tasks.",
        "cost": "Inception Labs pricing",
        "speed": "💨 Very fast (diffusion-based)",
    },
    "openrouter": {
        "model": "openai/gpt-4o-mini",
        "key_envs": ("OPENROUTER_API_KEY", "OPENROUTER", "OPENROUTER_FREE_KEY"),
        "description": "OpenRouter gateway — 200+ models. Flexible fallback provider.",
        "cost": "Varies by model (gpt-4o-mini: $0.15/M in, $0.60/M out)",
        "speed": "🚀 Fast",
    },
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "key_envs": ("GROQ_KEY", "GROQ_API_KEY"),
        "description": "Groq LPU inference. Good for coordinator/lightweight synthesis tasks.",
        "cost": "Groq free/paid tier depending on account",
        "speed": "⚡ Very fast",
    },
    "huggingface": {
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "key_envs": ("HUGGINGFACE_API", "HF_TOKEN", "HUGGINGFACE_API_KEY"),
        "description": "HuggingFace router over inference providers.",
        "cost": "Varies by provider; free tier available",
        "speed": "🚀 Fast",
    },
    "gemini_api": {
        "model": "gemini-2.5-flash-preview-05-20",
        "key_envs": ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_FREE_KEY"),
        "description": "Google AI Studio (aistudio.google.com) OpenAI-compatible Gemini endpoint.",
        "cost": "Free tier via aistudio.google.com / paid via console",
        "speed": "🚀 Fast",
    },
    "github_models": {
        "model": "gpt-4o-mini",
        "key_envs": ("GITHUB_TOKEN", "GH_TOKEN"),
        "description": "GitHub Models authenticated with a GitHub token.",
        "cost": "Free tier for GitHub users",
        "speed": "🚀 Fast",
    },
    "opencode": {
        "model": "default",
        "key_envs": ("OPENCODE_FREE_TIER",),
        "description": "OpenCode CLI (opencode.ai) — free tier, shell-out pattern (npm install -g opencode).",
        "cost": "Free tier",
        "speed": "🚀 Fast (CLI pipe)",
    },
    "ollama_cloud": {
        "model": "llama3.2:3b",
        "key_envs": ("OLLAMA_CLOUD_KEY",),
        "description": "Local Ollama CLI with cloud models. SSH-key authenticated.",
        "cost": "Ollama cloud subscription",
        "speed": "🐢 Slower (local CLI pipe)",
    },
}

# MASSREVIEW 2026-05-05: Updated to confirmed-working free models.
# Zero-key: pollinations/default | OPENROUTER_FREE_KEY: hy3, nemotron-nano, nemotron-super, minimax-m2.5
FREE_MODELS = {
    "coordinator": "pollinations/default",
    "researcher": "tencent/hy3-preview:free",
    "coder": "nvidia/nemotron-3-nano-30b-a3b:free",
    "reviewer": "nvidia/nemotron-3-super-120b-a12b:free",
    "architect": "minimax/minimax-m2.5:free",
    "security-architect": "google/gemini-2.5-flash",
    "fallback": "pollinations/default",
}

AGENT_ASSIGNMENTS = {
    "audit_researcher": "researcher",
    "audit_quant": "coder",
    "github_hygiene": "reviewer",
    "bug_hunter": "coordinator",
    "strategist": "architect",
}


def check_keys():
    """Check which paid providers have keys available."""
    available = {}
    for name, cfg in PAID_MODELS.items():
        keys_found = [e for e in cfg["key_envs"] if os.environ.get(e)]
        if keys_found:
            available[name] = {
                **cfg,
                "key_found": keys_found[0],
            }
    return available


def print_header(title):
    print(f"\n{'=' * 65}")
    print(f"  {title}")
    print(f"{'=' * 65}")


def print_free_tier():
    print_header("🆓 FREE TIER")
    print()
    print("  Models: OpenRouter free-tier via Hermes Agent")
    print("  Cost:   $0.00 — completely free")
    print("  Speed:  🐢 Slow (free models are rate-limited, shared capacity)")
    print("  Quality: ⭐⭐ (base models, no advanced reasoning)")
    print()
    print("  Agent → Model mapping:")
    for agent, role in AGENT_ASSIGNMENTS.items():
        model = FREE_MODELS.get(role, FREE_MODELS["fallback"])
        print(f"    {agent:25s} → {model}")
    print()
    print("  ✅ Pros:")
    print("    • Zero cost — run as many swarms as you want")
    print("    • No API keys needed — works out of the box")
    print("    • Good for: background monitoring, non-urgent analysis")
    print()
    print("  ❌ Cons:")
    print("    • Rate-limited — may hit 429 errors under heavy use")
    print("    • Slower responses (free tier = shared capacity)")
    print("    • Lower quality output (base models, limited context)")
    print("    • Failover chain may exhaust all 3 attempts on busy days")
    print()
    print("  Command:")
    print("    python3 .ruflo/orchestrator.py --swarm audit --tier free")
    print("    /swarm-ruflo audit")


def print_paid_tier(available_keys):
    print_header("💰 PAID TIER")
    print()
    print("  Models: Direct API calls via tools/swarm/api_consult.py")
    print("  Cost:   Varies by provider (see breakdown below)")
    print("  Speed:  ⚡ Fast (dedicated capacity, no rate limits)")
    print("  Quality: ⭐⭐⭐⭐ (frontier models with advanced reasoning)")
    print()
    print("  Agent → Provider mapping:")
    for agent, role in AGENT_ASSIGNMENTS.items():
        provider = get_paid_provider_for_role(role)
        status = "✅" if provider in available_keys else "❌"
        model = PAID_MODELS[provider]["model"] if provider in PAID_MODELS else "N/A"
        print(f"    {status} {agent:25s} → {provider:15s} ({model})")
    print()
    print("  ✅ Pros:")
    print("    • Faster — dedicated API capacity, no cold starts")
    print("    • Higher quality — frontier models (Grok-3, DeepSeek V3, etc.)")
    print("    • Reliable — no rate limiting on paid tiers")
    print("    • Provider diversity — different strengths per task type")
    print()
    print("  ❌ Cons:")
    print("    • Costs money — per-token pricing on most providers")
    print("    • Requires API keys — setup needed per provider")
    print("    • Key management — keys must be in environment variables")
    print("    • Ollama Cloud uses local CLI pipe (slower, terminal artifacts)")
    print()
    if available_keys:
        print(f"  🔑 Available providers ({len(available_keys)}):")
        for name, cfg in available_keys.items():
            print(f"    ✅ {name:15s}  model={cfg['model']:25s}  key={cfg['key_found']}")
            print(f"       {cfg['description']}")
            print(f"       Cost: {cfg['cost']} | Speed: {cfg['speed']}")
    else:
        print("  ⚠️  No paid API keys found!")
        print("  Set any of these environment variables:")
        for name, cfg in PAID_MODELS.items():
            print(f"    {name:15s} → {', '.join(cfg['key_envs'])}")
    print()
    print_key_setup_instructions()
    print()
    print("  Command:")
    print("    python3 .ruflo/orchestrator.py --swarm audit --tier paid")
    print("    /swarm-ruflo audit --tier paid")


def print_key_setup_instructions():
    """Show how to get API keys for each provider."""
    print_header("🔑 HOW TO GET API KEYS")
    print()
    print("  Add keys to your Windows Environment Variables (System Properties →")
    print("  Environment Variables → User variables → New...) OR add to .env file.")
    print()
    instructions = [
        ("CEREBRAS_API_KEY_PAID", "https://cerebras.ai",
         "Sign up at cerebras.ai → API Keys → Create key. Use: csk-ptx8n..."),
        ("OPENROUTER_FREE_KEY", "https://openrouter.ai/credits",
         "OpenRouter dashboard → Credits → copy 'Free tier' key. sk-or-v1-42a0..."),
        ("OPENROUTER_API_KEY", "https://openrouter.ai/settings",
         "OpenRouter → API Keys → Create. Use sk-or-v1-c054..."),
        ("GEMINI_FREE_KEY", "https://aistudio.google.com/app/apikey",
         "Google AI Studio → Get API Key → Create. Free tier via aistudio.google.com"),
        ("OPENCODE_FREE_TIER", "npm install -g opencode",
         "OpenCode is a CLI tool (opencode.ai) — install via npm, auth via: opencode login"),
        ("DEEPSEEK_API", "https://platform.deepseek.com/api_keys",
         "DeepSeek platform → API Keys → Create. ~$0.27/1M input tokens"),
        ("X_AI_KEY", "https://console.x.ai",
         "X AI console → API Keys → Create. Grok-3 access via xai.com"),
        ("INCEPTION_AI_KEY", "https://dashboard.inceptionlabs.ai",
         "Inception Labs → API Keys → Create. Mercury-2 fast diffusion model"),
        ("GROQ_KEY", "https://console.groq.com/keys",
         "Groq console → API Keys → Create. Free tier available."),
        ("HUGGINGFACE_API", "https://huggingface.co/settings/tokens",
         "HuggingFace → Settings → Access Tokens → Create. HF Inference API"),
        ("GITHUB_TOKEN", "gh auth login",
         "Run: gh auth login → select GitHub.com → HTTPS → yes → login browser"),
        ("GitHub Copilot", "gh extension install github/gh-copilot",
         "Install: gh extension install github/gh-copilot → gh copilot --help")
    ]
    for env_var, url, instruction in instructions:
        print(f"  {env_var}")
        print(f"    URL: {url}")
        print(f"    How: {instruction}")
        print()


def print_hybrid_tier(available_keys):
    print_header("🔄 HYBRID TIER (Recommended)")
    print()
    print("  Strategy: Try paid first, fall back to free on failure")
    print("  Cost:   Pay only when paid models succeed")
    print("  Speed:  ⚡ Fast when paid works, 🐢 slower on fallback")
    print("  Quality: ⭐⭐⭐⭐ (paid quality when available, free baseline otherwise)")
    print()
    print("  How it works:")
    print("    1. Try paid provider for each agent")
    print("    2. If paid succeeds → use that output (better quality)")
    print("    3. If paid fails (no key, rate limit, timeout) → fall back to free")
    print("    4. Each agent decides independently (some paid, some free)")
    print()
    print("  ✅ Pros:")
    print("    • Best of both worlds — paid quality when possible, free as safety net")
    print("    • Graceful degradation — swarm always completes even if paid is down")
    print("    • Cost-efficient — only pay for providers that have keys")
    print()
    print("  ❌ Cons:")
    print("    • Slightly slower on fallback (must wait for paid timeout first)")
    print("    • Mixed quality — some agents may run free, others paid")
    print("    • Harder to predict cost (depends on which providers succeed)")
    print()
    print("  Command:")
    print("    python3 .ruflo/orchestrator.py --swarm audit --tier hybrid")
    print("    /swarm-ruflo audit --tier hybrid")


def get_paid_provider_for_role(role):
    """Map agent role to paid provider."""
    role_map = {
        "researcher": "cerebras",
        "coder": "deepseek",
        "reviewer": "inception",
        "architect": "xai",
        "security-architect": "xai",
        "coordinator": "groq",
        "lightweight": "huggingface",
        "fallback": "openrouter",
    }
    return role_map.get(role, "openrouter")


def generate_wsl_command(swarm, tier):
    """Generate the WSL bridge command for Codebuff."""
    return (
        f"wsl bash -c \"cd /mnt/c/findtorontoevents_antigravity.ca && "
        f"python3 .ruflo/orchestrator.py --swarm {swarm} --tier {tier}\""
    )


def interactive_mode():
    """Interactive wizard flow."""
    available_keys = check_keys()

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        🦊 RUFLO SWARM WIZARD — Tier Selection Guide          ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Show key status first
    if available_keys:
        print(f"\n  🔑 {len(available_keys)} paid provider(s) detected: {', '.join(available_keys.keys())}")
    else:
        print("\n  ⚠️  No paid API keys detected. Only FREE tier is available.")
        print("  Set env vars to unlock PAID/HYBRID tiers (see below).")

    print("\n  Available tiers:")
    print("    1. FREE    — OpenRouter free models, zero cost")
    if available_keys:
        print("    2. PAID    — Direct API calls, faster/better, costs credits")
        print("    3. HYBRID  — Paid first, free fallback (recommended)")

    print("\n  Swarm types:")
    print("    • audit            — Strategy performance analysis (2 agents)")
    print("    • github           — Repo hygiene: PRs, Actions, commits")
    print("    • strategy         — New trading strategy proposals")
    print("    • bugs             — Bug & security vulnerability hunt")
    print("    • brainstorm_review — Multi-model synthesis: 6 fast → 1 reviewer")
    print("    • all              — Run all 5 swarms")

    # Ask for tier
    if available_keys:
        tier_options = ["free", "paid", "hybrid"]
        print("\n  Which tier?")
        print("    free   — $0, slower, good enough for background tasks")
        print("    paid   — costs credits, faster, better quality")
        print("    hybrid — best of both (recommended)")
        tier = input("\n  Tier [free/paid/hybrid] (default: hybrid): ").strip().lower()
        if tier not in tier_options:
            tier = "hybrid"
    else:
        tier = "free"
        print("\n  Tier: free (only option without paid keys)")

    # Ask for swarm type
    swarm_options = ["audit", "github", "strategy", "bugs", "brainstorm_review", "all"]
    swarm = input("\n  Swarm type [audit/github/strategy/bugs/brainstorm_review/all] (default: audit): ").strip().lower()
    if swarm not in swarm_options:
        swarm = "audit"

    # If brainstorm_review, ask for task description
    task = None
    if swarm == "brainstorm_review":
        print()
        task = input("  What should the brainstorm_review swarm analyze?\n  (press Enter for default: codebase analysis + top improvements)\n  > ").strip()
        if not task:
            task = None
            print("  Using default task: codebase analysis + top improvements")
        else:
            print(f"  Task: {task[:80]}{'...' if len(task) > 80 else ''}")

    # Show detailed tier info
    if tier == "free":
        print_free_tier()
    elif tier == "paid":
        print_paid_tier(available_keys)
    elif tier == "hybrid":
        print_hybrid_tier(available_keys)

    # Generate command
    print_header("🚀 YOUR COMMAND")
    print()
    if swarm == "all":
        if tier == "free":
            print("  /swarm-ruflo continuous --tier free")
        else:
            print(f"  /swarm-ruflo continuous --tier {tier}")
        print()
        print("  Or from terminal:")
        cmd = f"python3 .ruflo/orchestrator.py --continuous --tier {tier}"
        print(f"    {cmd}")
        print()
        print("  From Codebuff (Windows → WSL):")
        wsl_cmd = (
            f"wsl bash -c \"cd /mnt/c/findtorontoevents_antigravity.ca && "
            f"python3 .ruflo/orchestrator.py --continuous --tier {tier}\""
        )
        print(f"    {wsl_cmd}")
    else:
        slash = f"/swarm-ruflo {swarm}"
        if tier != "free":
            slash += f" --tier {tier}"
        print(f"  {slash}")
        print()
        print("  Or from terminal:")
        cmd = f"python3 .ruflo/orchestrator.py --swarm {swarm} --tier {tier}"
        print(f"    {cmd}")
        print()
        print("  From Codebuff (Windows → WSL):")
        wsl_cmd = generate_wsl_command(swarm, tier)
        print(f"    {wsl_cmd}")

    print()
    if swarm == "brainstorm_review":
        print("  Ὄb Brainstorm-review workflow:")
        print("    Phase 1: 6 fast models run in parallel via ThreadPoolExecutor")
        print("             pollinations (zero-key) + 4 via OPENROUTER_FREE_KEY +")
        print("             gemini-2.5-flash (via GEMINI_FREE_KEY)")
        print("    Phase 2: 1 strong reviewer (cerebras/deepseek/xai) synthesizes")
        print("             → ranked answer with citations and confidence scores")
        print("    Phase 1 pollinations/default needs NO API keys (works out of box)")
        print("    Phase 1 OPENROUTER_FREE_KEY models need that key in env")
        print("    Phase 2 reviewer uses paid keys if available, else free fallback")
        print()
    print("  Insights will be saved to: swarm_runs/ruflo-insights/")
    print("  Compiled summary:          swarm_runs/ruflo-insights/COMPILED_latest.json")
    print()


def quick_mode():
    """Non-interactive: show status and suggest best tier."""
    available_keys = check_keys()

    print_header("RUFLO SWARM — QUICK STATUS")
    print()

    # Agent table
    print("  Agents (5):")
    for agent, role in AGENT_ASSIGNMENTS.items():
        free_model = FREE_MODELS.get(role, FREE_MODELS["fallback"])
        provider = get_paid_provider_for_role(role)
        paid_ok = "✅" if provider in available_keys else "❌"
        print(f"    {agent:25s}  free={free_model:40s}  paid={paid_ok} {provider}")

    # Paid keys
    print(f"\n  Paid keys: {len(available_keys)} available")
    if available_keys:
        for name, cfg in available_keys.items():
            print(f"    ✅ {name:15s}  model={cfg['model']:25s}  key={cfg['key_found']}")
    else:
        print("    ❌ None — only FREE tier available")

    # Recommendation
    print()
    if len(available_keys) >= 3:
        print("  💡 RECOMMENDED: hybrid")
        print("     Multiple paid keys available. Hybrid gives you paid quality")
        print("     with free fallback for resilience.")
        print(f"     /swarm-ruflo audit --tier hybrid")
    elif len(available_keys) >= 1:
        print("  💡 RECOMMENDED: hybrid")
        print("     At least one paid key available. Hybrid will use it where possible")
        print("     and fall back to free for other roles.")
        print(f"     /swarm-ruflo audit --tier hybrid")
    else:
        print("  💡 RECOMMENDED: free")
        print("     No paid keys detected. Free tier works out of the box.")
        print("     Set env vars to unlock paid/hybrid tiers.")
        print(f"     /swarm-ruflo audit")

    print()
    print("  Run the wizard for interactive selection:")
    print("    python3 .ruflo/wizard.py")
    print("    /swarm-ruflo wizard")
    print()


def show_tier_config(tier):
    """Show detailed config for a specific tier."""
    available_keys = check_keys()

    if tier == "free":
        print_free_tier()
    elif tier == "paid":
        print_paid_tier(available_keys)
    elif tier == "hybrid":
        print_hybrid_tier(available_keys)
    else:
        print(f"Unknown tier: {tier}. Use: free, paid, hybrid")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ruflo Swarm Wizard")
    parser.add_argument("--quick", action="store_true", help="Quick status + recommendation")
    parser.add_argument("--tier", choices=["free", "paid", "hybrid"], help="Show specific tier config")
    args = parser.parse_args()

    if args.quick:
        quick_mode()
    elif args.tier:
        show_tier_config(args.tier)
    else:
        # Default: run wizard interactively
        interactive_mode()
