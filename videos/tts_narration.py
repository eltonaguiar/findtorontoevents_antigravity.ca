#!/usr/bin/env python3
"""
TTS Narration Generator for SAM Videos - Phase 2
Supports: Piper (local, free), Coqui XTTS (local, free), ElevenLabs (cloud, free tier), OpenAI TTS (cloud, pay-per-use)
"""

import os
import sys
import json
from pathlib import Path

# Narration scripts for each scene
NARRATION_SCRIPTS = {
    "01_chain_diagram": """
Welcome to the ServiceNow SAM Masterclass. This video covers the fundamental chain that drives all Software Asset Management.

SAM reconciles what you own against what exists and is used, per software model and license metric, turning the difference into a compliance position.

The chain has five links: First, a Configuration Item in the CMDB, governed by IRE rules. Second, an install record — one per device — in cmdb_sam_sw_install. Third, a discovery model in cmdb_sam_sw_discovery_model, carrying the raw fingerprint and normalized fields. Fourth, a software product model in cmdb_software_product_model, representing what you purchased. Fifth, an entitlement in alm_license, holding your rights, metric, and dates.

Reconciliation compares rights versus demand and produces three result tiers: product-level in samp_product_result, software-model-level in Software Model Results, and license-metric-level in samp_license_metric_result. The run is recorded in samp_reconciliation_result.

Memorize this chain: Install → Discovery Model → Software Model → Entitlement → Result. This is the backbone of every SAM question you'll face.
""",
    
    "02_four_gates": """
Before SAM can produce meaningful results, four gates must pass.

Gate one: Schema and Edition. The correct SAM plugin must be installed, and SAM tables must be present. Without this, nothing works.

Gate two: CMDB and CI Identity. There must be one CI per device, and IRE rules must be reviewed. Duplicate CIs mean duplicate installs.

Gate three: Discovery Feed. One trusted source must populate installs. Multiple uncoordinated sources inflate demand.

Gate four: Normalization and Entitlements. Models must normalize, and every entitlement must have a model and a metric. An entitlement without a metric is meaningless.

If any gate fails, reconciliation produces garbage data, and you get the wrong compliance position. Verify all four before trusting any SAM report.
""",
    
    "03_normalization_states": """
Normalization statuses — there are six, not four. This is a common exam trap.

New: Auto-created from discovery. No manual action, no revert.
Match Not Found: No match in the content library. You CAN manually normalize. Cannot revert — it's already the floor.
Publisher Normalized: Matched to publisher content. You CAN manually normalize. CAN revert — goes back to Match Not Found.
Partially Normalized: Partial match, version or edition missing. You CAN manually normalize. CAN revert — goes back to Match Not Found.
Normalized: Fully matched to a software model. No manual normalize needed. CAN revert — goes back to Match Not Found.
Manually Normalized: Admin manually assigned the model. No manual normalize, no revert.

Key rule: All reverts go to Match Not Found. Pattern-normalized models CANNOT be reverted. Know this table cold for the CIS-SAM exam.
""",
    
    "04_reconciliation_tiers": """
Reconciliation produces three tiers of results.

Product tier: samp_product_result. Answers: Is the product compliant? What is the cost or savings? This is your executive roll-up view.

Software Model tier: Software Model Results. Answers: Which specific model is the problem? Drill down from product to model.

License Metric tier: samp_license_metric_result. Answers: Rights owned versus used versus available, per metric. This is the math layer — user, device, core, PVU, RVU, each calculated separately.

The reconciliation run itself is recorded in samp_reconciliation_result. Note: There is NO single documented table called sam_sw_reconciliation_result. That's a common misconception.
""",
    
    "05_rights_algebra": """
The rights algebra is the core math of compliance. Master these five equations.

Rights Owned equals the sum of active entitlements sharing the metric.
Rights Used equals Allocated In Use plus Not Allocated In Use plus Installed.
Rights Available equals Rights Owned minus Rights Used.
Allocated Not In Use equals wasted rights — the fix is to remove allocations.
Not Allocated In Use equals unallocated consumption — the fix is to create allocations or remove unallocated installs.

Three compliance positions emerge:
Compliant: Rights Owned greater than or equal to Rights Used.
Under-licensed: Rights Used greater than Rights Owned — this is audit exposure.
Over-licensed: Rights Owned greater than Rights Used — this is wasted spend.

Every optimization action — reclamation, true-up, downgrade, harvest — moves you between these positions.
""",
    
    "06_top_traps": """
Top seven SAM traps. These appear constantly in exams and real implementations.

Trap one: Metric mismatch. The software model metric differs from the entitlement metric. Result: silently meaningless reconciliation. Always verify metric alignment.

Trap two: Duplicate installs. Multiple discovery sources feed the same device. Result: inflated demand. Configure deduplication rules in sam_sw_dedup_rule.

Trap three: Unnormalized titles. Raw discovery titles stay unlicensed or unknown. Normalize BEFORE enabling auto-create software models.

Trap four: Maintenance treated as a license. Support and maintenance contracts are not license entitlements. Including them creates false compliance.

Trap five: Out-of-scope devices. Leased, ignored, or non-managed devices keep installs. Retired and Stolen CI status deletes installs automatically, but other states need the exclude-CI job.

Trap six: First reconciliation treated as an invoice. The first run is a data quality loop, not a true-up. Fix the data, then re-reconcile.

Trap seven: Dead SaaS connector. The connector fails silently. You see 'no waste' but it's an illusion. Monitor connector health religiously.
""",
}

# TTS Provider configurations
PROVIDERS = {
    "piper": {
        "name": "Piper TTS (Local, Free, Fast)",
        "install": "pip install piper-tts",
        "voices_dir": "~/.local/share/piper/voices",
        "default_voice": "en_US-lessac-medium",
        "cmd_template": 'piper --model {voice} --output_file "{output}" --text "{text}"',
    },
    "coqui": {
        "name": "Coqui XTTS v2 (Local, Free, Voice Cloning)",
        "install": "pip install coqui-tts",
        "default_voice": "tts_models/multilingual/multi-dataset/xtts_v2",
        "python_api": True,
    },
    "elevenlabs": {
        "name": "ElevenLabs (Cloud, Best Quality, 10k free chars/mo)",
        "install": "pip install elevenlabs",
        "env_var": "ELEVENLABS_API_KEY",
        "default_voice": "pNInz6obpgDQGcFmaJgB",  # Adam
    },
    "openai": {
        "name": "OpenAI TTS (Cloud, Pay-per-use, $15/1M chars)",
        "install": "pip install openai",
        "env_var": "OPENAI_API_KEY",
        "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        "default_voice": "onyx",
    },
}

def generate_piper(text, output_path, voice="en_US-lessac-medium"):
    """Generate TTS using Piper (local)."""
    import subprocess
    import shlex
    
    # Escape text for shell
    escaped_text = text.replace('"', '\\"').replace("'", "\\'")
    
    cmd = f'piper --model {voice} --output_file "{output_path}" --text "{escaped_text}"'
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return True
        else:
            print(f"Piper error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("Piper timeout")
        return False
    except FileNotFoundError:
        print("Piper not installed. Run: pip install piper-tts")
        return False

def generate_coqui(text, output_path, voice="tts_models/multilingual/multi-dataset/xtts_v2", speaker_wav=None):
    """Generate TTS using Coqui TTS (local)."""
    try:
        from TTS.api import TTS
        tts = TTS(voice)
        if speaker_wav:
            tts.tts_to_file(text=text, file_path=output_path, speaker_wav=speaker_wav, language="en")
        else:
            tts.tts_to_file(text=text, file_path=output_path, language="en")
        return True
    except ImportError:
        print("Coqui TTS not installed. Run: pip install coqui-tts")
        return False
    except Exception as e:
        print(f"Coqui error: {e}")
        return False

def generate_elevenlabs(text, output_path, voice_id="pNInz6obpgDQGcFmaJgB", api_key=None):
    """Generate TTS using ElevenLabs API."""
    try:
        from elevenlabs import generate, save, set_api_key
        if api_key:
            set_api_key(api_key)
        import os
        if not api_key:
            api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            print("ElevenLabs API key not set. Set ELEVENLABS_API_KEY env var.")
            return False
        audio = generate(text=text, voice=voice_id, model="eleven_monolingual_v1")
        save(audio, output_path)
        return True
    except ImportError:
        print("ElevenLabs not installed. Run: pip install elevenlabs")
        return False
    except Exception as e:
        print(f"ElevenLabs error: {e}")
        return False

def generate_openai(text, output_path, voice="onyx", api_key=None):
    """Generate TTS using OpenAI API."""
    try:
        from openai import OpenAI
        import os
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("OpenAI API key not set. Set OPENAI_API_KEY env var.")
            return False
        client = OpenAI(api_key=api_key)
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            input=text
        )
        response.stream_to_file(output_path)
        return True
    except ImportError:
        print("OpenAI not installed. Run: pip install openai")
        return False
    except Exception as e:
        print(f"OpenAI error: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate TTS narration for SAM videos")
    parser.add_argument("--provider", choices=["piper", "coqui", "elevenlabs", "openai"], 
                       default="piper", help="TTS provider to use")
    parser.add_argument("--voice", help="Voice ID/model to use")
    parser.add_argument("--scene", help="Specific scene to generate (or all)")
    parser.add_argument("--output-dir", default="narration", help="Output directory")
    parser.add_argument("--list-providers", action="store_true", help="List available providers")
    
    args = parser.parse_args()
    
    if args.list_providers:
        print("Available TTS Providers:")
        for key, cfg in PROVIDERS.items():
            print(f"  {key}: {cfg['name']}")
            print(f"    Install: {cfg['install']}")
        return
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Determine scenes to process
    scenes = {args.scene: NARRATION_SCRIPTS[args.scene]} if args.scene else NARRATION_SCRIPTS
    
    # Provider-specific setup
    provider_config = PROVIDERS[args.provider]
    voice = args.voice or provider_config.get("default_voice")
    
    print(f"Provider: {provider_config['name']}")
    print(f"Voice: {voice}")
    print(f"Output dir: {args.output_dir}")
    print(f"Scenes: {len(scenes)}")
    print("-" * 50)
    
    success_count = 0
    for scene_name, script in scenes.items():
        output_path = os.path.join(args.output_dir, f"{scene_name}.wav")
        print(f"\nGenerating: {scene_name}")
        
        if args.provider == "piper":
            ok = generate_piper(script.strip(), output_path, voice)
        elif args.provider == "coqui":
            ok = generate_coqui(script.strip(), output_path, voice)
        elif args.provider == "elevenlabs":
            ok = generate_elevenlabs(script.strip(), output_path, voice)
        elif args.provider == "openai":
            ok = generate_openai(script.strip(), output_path, voice)
        else:
            ok = False
        
        if ok:
            print(f"  ✓ Saved: {output_path}")
            success_count += 1
        else:
            print(f"  ✗ Failed: {scene_name}")
    
    print(f"\n{'='*50}")
    print(f"Complete: {success_count}/{len(scenes)} narrations generated")
    print(f"Files in: {os.path.abspath(args.output_dir)}")

if __name__ == "__main__":
    main()