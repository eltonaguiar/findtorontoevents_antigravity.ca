#!/usr/bin/env python3
"""
Merge video files with TTS narration audio - Phase 2
Creates final videos with synchronized audio narration.
"""

import os
from moviepy.editor import *

VIDEO_DIR = "output"
AUDIO_DIR = "narration"
OUTPUT_DIR = "output_final"

SCENE_FILES = [
    ("SAM_01_chain_diagram_Phase1.mp4", "01_chain_diagram.wav", "SAM_01_chain_diagram_FINAL.mp4"),
    ("SAM_02_four_gates_Phase1.mp4", "02_four_gates.wav", "SAM_02_four_gates_FINAL.mp4"),
    ("SAM_03_normalization_states_Phase1.mp4", "03_normalization_states.wav", "SAM_03_normalization_states_FINAL.mp4"),
    ("SAM_04_reconciliation_tiers_Phase1.mp4", "04_reconciliation_tiers.wav", "SAM_04_reconciliation_tiers_FINAL.mp4"),
    ("SAM_05_rights_algebra_Phase1.mp4", "05_rights_algebra.wav", "SAM_05_rights_algebra_FINAL.mp4"),
    ("SAM_06_top_traps_Phase1.mp4", "06_top_traps.wav", "SAM_06_top_traps_FINAL.mp4"),
]

MASTERCLASS_VIDEO = "SAM_Masterclass_Phase1_VisualOnly.mp4"
MASTERCLASS_AUDIO = "masterclass_full.wav"
MASTERCLASS_OUTPUT = "SAM_Masterclass_FINAL.mp4"

def merge_video_audio(video_path, audio_path, output_path):
    """Merge a video file with an audio file."""
    print(f"\nMerging: {os.path.basename(video_path)} + {os.path.basename(audio_path)}")
    
    try:
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)
        
        print(f"  Video duration: {video.duration:.1f}s")
        print(f"  Audio duration: {audio.duration:.1f}s")
        
        # If audio is longer, extend video with freeze frame
        if audio.duration > video.duration:
            print(f"  Audio longer by {audio.duration - video.duration:.1f}s - extending video")
            # Add freeze frame at end
            last_frame = video.to_ImageClip(t=video.duration - 0.01).set_duration(audio.duration - video.duration)
            video = concatenate_videoclips([video, last_frame], method="compose")
        # If video is longer, loop audio or trim video
        elif video.duration > audio.duration:
            print(f"  Video longer by {video.duration - audio.duration:.1f}s - trimming video")
            video = video.subclip(0, audio.duration)
        
        # Set audio
        final = video.set_audio(audio)
        
        # Write output
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="medium",
            bitrate="8000k",
            logger="bar"
        )
        
        print(f"  ✓ Created: {output_path}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def create_masterclass_audio():
    """Concatenate all narration files into one masterclass audio."""
    print("\nCreating masterclass audio...")
    
    audio_clips = []
    for _, audio_file, _ in SCENE_FILES:
        path = os.path.join(AUDIO_DIR, audio_file)
        if os.path.exists(path):
            audio_clips.append(AudioFileClip(path))
            print(f"  Added: {audio_file}")
        else:
            print(f"  Missing: {audio_file}")
    
    if not audio_clips:
        print("No audio files found!")
        return False
    
    master_audio = concatenate_audioclips(audio_clips)
    output_path = os.path.join(AUDIO_DIR, MASTERCLASS_AUDIO)
    
    master_audio.write_audiofile(output_path, fps=44100, codec='pcm_s16le')
    print(f"  ✓ Master audio: {output_path} ({master_audio.duration:.1f}s)")
    return True

def main():
    print("=" * 60)
    print("SAM Video + Audio Merger (Phase 2)")
    print("=" * 60)
    
    # Check directories
    if not os.path.exists(VIDEO_DIR):
        print(f"✗ Video directory not found: {VIDEO_DIR}")
        print("  Run compose_final.py first to generate Phase 1 videos")
        return
    
    if not os.path.exists(AUDIO_DIR):
        print(f"✗ Audio directory not found: {AUDIO_DIR}")
        print("  Run tts_narration.py first to generate narration")
        return
    
    # Check individual videos exist
    print("\nChecking individual videos...")
    missing_videos = []
    for video_file, _, _ in SCENE_FILES:
        path = os.path.join(VIDEO_DIR, video_file)
        if not os.path.exists(path):
            missing_videos.append(video_file)
        else:
            print(f"  ✓ {video_file}")
    
    if missing_videos:
        print(f"Missing videos: {missing_videos}")
        print("Run compose_final.py to generate them")
    
    # Check audio files exist
    print("\nChecking narration audio...")
    missing_audio = []
    for _, audio_file, _ in SCENE_FILES:
        path = os.path.join(AUDIO_DIR, audio_file)
        if not os.path.exists(path):
            missing_audio.append(audio_file)
        else:
            print(f"  ✓ {audio_file}")
    
    if missing_audio:
        print(f"Missing audio: {missing_audio}")
        print("Run tts_narration.py to generate them")
        return
    
    # Merge individual videos
    print("\n" + "="*60)
    print("Merging individual topic videos...")
    print("="*60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    success = 0
    for video_file, audio_file, output_file in SCENE_FILES:
        vpath = os.path.join(VIDEO_DIR, video_file)
        apath = os.path.join(AUDIO_DIR, audio_file)
        opath = os.path.join(OUTPUT_DIR, output_file)
        
        if merge_video_audio(vpath, apath, opath):
            success += 1
    
    # Create and merge masterclass
    print("\n" + "="*60)
    print("Creating masterclass video...")
    print("="*60)
    
    master_video_path = os.path.join(VIDEO_DIR, MASTERCLASS_VIDEO)
    if os.path.exists(master_video_path):
        if create_masterclass_audio():
            master_audio_path = os.path.join(AUDIO_DIR, MASTERCLASS_AUDIO)
            master_output = os.path.join(OUTPUT_DIR, MASTERCLASS_OUTPUT)
            merge_video_audio(master_video_path, master_audio_path, master_output)
    
    print("\n" + "="*60)
    print(f"PHASE 2 COMPLETE: {success}/{len(SCENE_FILES)} videos merged")
    print(f"Final videos in: {os.path.abspath(OUTPUT_DIR)}")
    print("="*60)

if __name__ == "__main__":
    main()