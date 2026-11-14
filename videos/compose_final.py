#!/usr/bin/env python3
"""
Compose final SAM videos from rendered Manim scenes using MoviePy.
Run from the videos/ directory after rendering: python compose_final.py
"""

import os
from moviepy.editor import *

# Configuration
SCENES_DIR = "media/videos/01_chain_diagram"
QUALITY_DIR = "1080p60"  # or 4K, 720p, 480p
OUTPUT_DIR = "output"

SCENE_FILES = [
    ("ChainDiagram.mp4", "01_chain_diagram"),
    ("FourGates.mp4", "02_four_gates"),
    ("NormalizationStates.mp4", "03_normalization_states"),
    ("ReconciliationTiers.mp4", "04_reconciliation_tiers"),
    ("RightsAlgebra.mp4", "05_rights_algebra"),
    ("TopTraps.mp4", "06_top_traps"),
]

# Video metadata
VIDEO_META = {
    "title": "ServiceNow SAM Masterclass",
    "author": "ServiceNow Learning",
    "description": "Core SAM concepts for CIS-SAM exam and job interviews",
}

def find_scene_file(scene_name, quality=QUALITY_DIR):
    """Find the rendered scene file."""
    path = os.path.join(SCENES_DIR, quality, scene_name)
    if os.path.exists(path):
        return path
    # Try alternative quality dirs
    for q in ["4K", "1080p60", "720p", "480p"]:
        alt_path = os.path.join(SCENES_DIR, q, scene_name)
        if os.path.exists(alt_path):
            print(f"  Found at {q}: {alt_path}")
            return alt_path
    return None

def create_intro_card(text, duration=3, fontsize=48, color="#58a6ff"):
    """Create a simple text card for transitions."""
    from moviepy.editor import TextClip, ColorClip
    
    bg = ColorClip(size=(1920, 1080), color=(13, 17, 23), duration=duration)
    txt = TextClip(text, fontsize=fontsize, color=color, font="DejaVu-Sans-Bold",
                   method='caption', size=(1600, None))
    txt = txt.set_position('center').set_duration(duration)
    return CompositeVideoClip([bg, txt])

def create_outro_card(duration=4):
    """Create outro card with links."""
    from moviepy.editor import TextClip, ColorClip
    
    bg = ColorClip(size=(1920, 1080), color=(13, 17, 23), duration=duration)
    
    lines = [
        "ServiceNow SAM Masterclass",
        "",
        "GitHub: github.com/eltonaguiar/alt_parallelswarm_SAM",
        "Guide: eltonaguiar.github.io/ServiceNow_Learning_.../sam/sam-guide/",
        "",
        "CIS-SAM Exam Ready • Job Interview Ready",
    ]
    
    txt = TextClip("\n".join(lines), fontsize=36, color="#c9d1d9", 
                   font="DejaVu-Sans", method='caption', size=(1600, None))
    txt = txt.set_position('center').set_duration(duration)
    return CompositeVideoClip([bg, txt])

def compose_masterclass():
    """Compose all scenes into one masterclass video."""
    print("Composing SAM Masterclass video...")
    
    clips = []
    
    # Intro
    clips.append(create_intro_card("ServiceNow SAM Masterclass\nCore Concepts for CIS-SAM & Job Interviews", 4))
    
    # Scene transitions
    scene_titles = [
        "1. The SAM Chain: Install → Discovery Model → Software Model → Entitlement → Result",
        "2. The Four Gates: Prerequisites for SAM to Work",
        "3. Normalization States: Six States (Not Four!)",
        "4. Reconciliation Results: Three Tiers",
        "5. Rights Algebra: The Core Math of Compliance",
        "6. Top 7 SAM Traps: Interview Gold",
    ]
    
    for i, (scene_file, _) in enumerate(SCENE_FILES):
        # Title card
        clips.append(create_intro_card(scene_titles[i], 2.5, fontsize=36))
        
        # Scene
        path = find_scene_file(scene_file)
        if path:
            clip = VideoFileClip(path)
            clips.append(clip)
            print(f"  Added: {scene_file} ({clip.duration:.1f}s)")
        else:
            print(f"  WARNING: Missing {scene_file}")
            # Placeholder
            clips.append(create_intro_card(f"[MISSING: {scene_file}]", 3, color="#f85149"))
    
    # Outro
    clips.append(create_outro_card(5))
    
    # Concatenate
    print("\nConcatenating clips...")
    final = concatenate_videoclips(clips, method="compose")
    
    # Output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "SAM_Masterclass_Phase1_VisualOnly.mp4")
    
    print(f"Rendering to: {output_path}")
    print(f"Total duration: {final.duration:.1f}s ({final.duration/60:.1f} min)")
    
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="medium",
        bitrate="8000k",
        threads=4,
        logger="bar"
    )
    
    print(f"\n✓ Masterclass video created: {output_path}")
    return output_path

def compose_individual_videos():
    """Create individual topic videos (better for YouTube playlist)."""
    print("\nCreating individual topic videos...")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for i, (scene_file, short_name) in enumerate(SCENE_FILES):
        path = find_scene_file(scene_file)
        if not path:
            print(f"  Skipping {short_name}: source not found")
            continue
        
        clip = VideoFileClip(path)
        
        # Add title card at start
        title_text = f"SAM Concept {i+1}: {short_name.replace('_', ' ').title()}"
        title_card = create_intro_card(title_text, 2, fontsize=40)
        
        # Add brief outro
        outro = create_intro_card("Next: " + (SCENE_FILES[i+1][1].replace('_', ' ').title() if i+1 < len(SCENE_FILES) else "End of Series"), 2, fontsize=32, color="#7ee787")
        
        combined = concatenate_videoclips([title_card, clip, outro], method="compose")
        
        output_path = os.path.join(OUTPUT_DIR, f"SAM_{short_name}_Phase1.mp4")
        combined.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="medium",
            bitrate="6000k",
            logger=None
        )
        print(f"  ✓ Created: {output_path}")

def main():
    print("=" * 60)
    print("SAM Video Composer (MoviePy)")
    print("=" * 60)
    
    # Check MoviePy
    try:
        import moviepy
        print(f"MoviePy version: {moviepy.__version__}")
    except ImportError:
        print("✗ MoviePy not installed: pip install moviepy")
        return
    
    # Check FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("FFmpeg: Available")
    except:
        print("✗ FFmpeg not found. Install: sudo apt install ffmpeg")
        return
    
    # Check source files exist
    found = 0
    for scene_file, _ in SCENE_FILES:
        if find_scene_file(scene_file):
            found += 1
    print(f"Found {found}/{len(SCENE_FILES)} scene files")
    
    if found == 0:
        print("No rendered scenes found. Run render_all.py first.")
        return
    
    # Compose
    compose_masterclass()
    compose_individual_videos()
    
    print("\n" + "="*60)
    print("COMPOSITION COMPLETE")
    print("="*60)
    print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    import subprocess
    main()