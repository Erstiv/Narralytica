#!/usr/bin/env python3
"""
Narralytica: Scene Detection with CutPrint™ Merge

Uses PySceneDetect to find raw camera cuts, then merges them into
story-level scenes using the CutPrint min_scene_duration parameter.

Usage:
    python detect_scenes.py <video_path> <output.json> [--threshold 22] [--min-scene 50]

    # With a CutPrint profile:
    python detect_scenes.py video.mp4 scenes.json --profile cutprint_profile.json
"""
import json
import sys
import os
import argparse
import statistics

from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector

# Ensure Homebrew binaries are on PATH (macOS)
if sys.platform == "darwin":
    for brew_path in ["/usr/local/bin", "/opt/homebrew/bin"]:
        if brew_path not in os.environ.get("PATH", ""):
            os.environ["PATH"] = brew_path + ":" + os.environ.get("PATH", "")


def merge_shots_to_scenes(raw_scenes: list, min_scene_seconds: int) -> list:
    """CutPrint™ merge: combine rapid shot-level cuts into story-level scenes.

    Raw scene detection finds every camera cut (every 2-5 seconds in animation).
    This merge step groups consecutive shots that belong to the same story beat
    by enforcing a minimum scene duration.

    Two-pass algorithm:
    1. Forward pass: accumulate shots until minimum duration is reached
    2. Cleanup pass: merge any remaining short tail scenes into their predecessor
    """
    if not raw_scenes:
        return []

    # Forward pass
    merged = []
    cs, ce = raw_scenes[0]

    for i in range(1, len(raw_scenes)):
        ss, se = raw_scenes[i]
        if (ce - cs).get_seconds() < min_scene_seconds:
            ce = se  # Absorb into current scene
        else:
            merged.append((cs, ce))
            cs, ce = ss, se
    merged.append((cs, ce))

    # Cleanup pass: catch any remaining short scenes
    final = []
    for s, e in merged:
        d = (e - s).get_seconds()
        if final and d < min_scene_seconds:
            final[-1] = (final[-1][0], e)
        else:
            final.append((s, e))

    return final


def detect_scenes(
    video_path: str,
    output_path: str,
    threshold: float = 27.0,
    min_scene: int = 0,
) -> list:
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    print(f"Analyzing: {video_path}")
    print(f"Detection threshold: {threshold}")

    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))

    print("Detecting raw cuts...")
    scene_manager.detect_scenes(video)
    raw_scene_list = scene_manager.get_scene_list()
    print(f"Found {len(raw_scene_list)} raw camera cuts.")

    # Apply CutPrint merge if min_scene is set
    if min_scene > 0:
        print(f"CutPrint™ merge: min_scene_duration={min_scene}s")
        scene_list = merge_shots_to_scenes(raw_scene_list, min_scene)
        print(f"Merged to {len(scene_list)} story-level scenes.")
    else:
        scene_list = raw_scene_list

    scenes = []
    for i, (start, end) in enumerate(scene_list):
        start_sec = start.get_seconds() if hasattr(start, 'get_seconds') else start
        end_sec = end.get_seconds() if hasattr(end, 'get_seconds') else end
        scenes.append({
            "scene_number": i + 1,
            "start_timestamp": round(start_sec, 2),
            "end_timestamp": round(end_sec, 2),
            "duration": round(end_sec - start_sec, 2),
            "start_timecode": str(start),
            "end_timecode": str(end),
        })

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(scenes, f, indent=2)

    print(f"Scene boundaries saved to: {output_path}")

    # Print summary
    durations = [s["duration"] for s in scenes]
    if durations:
        print(f"\nSummary:")
        print(f"  Raw camera cuts: {len(raw_scene_list)}")
        print(f"  Story scenes:    {len(scenes)}")
        print(f"  Shortest scene:  {min(durations):.1f}s")
        print(f"  Longest scene:   {max(durations):.1f}s")
        print(f"  Average:         {sum(durations)/len(durations):.1f}s")
        print(f"  Median:          {statistics.median(durations):.1f}s")
        print(f"  Stddev:          {statistics.stdev(durations):.1f}s" if len(durations) > 1 else "")

    return scenes


def main():
    parser = argparse.ArgumentParser(description="Narralytica scene detection with CutPrint™ merge")
    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument("output_path", help="Output JSON path")
    parser.add_argument("--threshold", type=float, default=27.0, help="ContentDetector threshold (default: 27)")
    parser.add_argument("--min-scene", type=int, default=0, help="CutPrint min scene duration in seconds (0 = no merge)")
    parser.add_argument("--profile", help="Path to CutPrint profile JSON (overrides --threshold and --min-scene)")

    args = parser.parse_args()

    threshold = args.threshold
    min_scene = args.min_scene

    # Load CutPrint profile if provided
    if args.profile:
        with open(args.profile) as f:
            profile = json.load(f)
        threshold = profile.get("threshold", threshold)
        min_scene = profile.get("min_scene_duration", min_scene)
        print(f"Loaded CutPrint™ profile: threshold={threshold}, min_scene={min_scene}s")

    detect_scenes(args.video_path, args.output_path, threshold, min_scene)


if __name__ == "__main__":
    main()
