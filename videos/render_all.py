#!/usr/bin/env python3
"""
Render all SAM video scenes using Manim.
Run from the videos/ directory: python render_all.py
"""

import subprocess
import sys
import os

SCENES = [
    ("ChainDiagram", "01_chain_diagram.mp4", "The SAM Chain Diagram"),
    ("FourGates", "02_four_gates.mp4", "The Four Gates"),
    ("NormalizationStates", "03_normalization_states.mp4", "Normalization States (Six)"),
    ("ReconciliationTiers", "04_reconciliation_tiers.mp4", "Reconciliation Three Tiers"),
    ("RightsAlgebra", "05_rights_algebra.mp4", "Rights Algebra"),
    ("TopTraps", "06_top_traps.mp4", "Top 7 SAM Traps"),
]

SCENE_FILE = "scenes/01_chain_diagram.py"
QUALITY = "h"  # h=1080p60, k=4K, m=720p, l=480p
PREVIEW = False  # Set True to auto-open after render

def render_scene(scene_class, output_name, description):
    print(f"\n{'='*60}")
    print(f"Rendering: {description}")
    print(f"Scene: {scene_class} -> {output_name}")
    print(f"{'='*60}")
    
    cmd = [
        "manim",
        f"-pq{QUALITY}",
        SCENE_FILE,
        scene_class,
        "-o", output_name,
    ]
    
    if not PREVIEW:
        cmd.insert(2, "--disable_caching")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✓ Success: {output_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed: {scene_class} (exit code {e.returncode})")
        return False
    except FileNotFoundError:
        print("✗ Error: 'manim' command not found. Install with: pip install manim")
        return False

def main():
    print("SAM Video Renderer")
    print("=" * 60)
    print(f"Scene file: {SCENE_FILE}")
    print(f"Quality: {'1080p60' if QUALITY=='h' else '4K' if QUALITY=='k' else '720p' if QUALITY=='m' else '480p'}")
    print(f"Preview mode: {PREVIEW}")
    
    if not os.path.exists(SCENE_FILE):
        print(f"✗ Scene file not found: {SCENE_FILE}")
        sys.exit(1)
    
    os.makedirs("output", exist_ok=True)
    
    results = []
    for scene_class, output_name, description in SCENES:
        success = render_scene(scene_class, output_name, description)
        results.append((description, success))
    
    print("\n" + "="*60)
    print("RENDER SUMMARY")
    print("="*60)
    all_ok = True
    for desc, ok in results:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"  {status}: {desc}")
        if not ok:
            all_ok = False
    
    if all_ok:
        print("\n✓ All scenes rendered successfully!")
        print(f"Output files in: {os.path.abspath('media/videos')}")
    else:
        print("\n✗ Some scenes failed. Check errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()