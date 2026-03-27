#!/usr/bin/env python3
"""
Narralytica: Scene Detection Script (Run on M5 Mac)

Uses PySceneDetect to find scene boundaries in a video.
Outputs a JSON file with timestamp pairs that become Gemini analysis anchors.

Usage:
    pip install scenedetect[opencv]
    python detect_scenes.py /path/to/compressed.mp4 scenes.json

What it does:
    1. Analyzes the compressed video frame by frame
    2. Detects when the scene changes (content-aware detection)
    3. Outputs a JSON file with start/end timestamps for each scene
    4. These timestamps are sent to Gemini so it knows where to focus
"""
import json
import sys
import os

from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector


def detect_scenes(video_path: str, output_path: str, threshold: float = 27.0) -> None:
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    print(f"Analyzing: {video_path}")
    print(f"Detection threshold: {threshold} (lower = more sensitive)")

    video = open_video(video_path)
    scene_manager = SceneManager()

    # ContentDetector compares adjacent frames for visual changes.
    # Threshold 27 works well for animated content (Simpsons).
    # Lower it (e.g., 20) if scenes are being missed.
    scene_manager.add_detector(ContentDetector(threshold=threshold))

    print("Detecting scenes... this may take a minute.")
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()

    print(f"Found {len(scene_list)} scenes.")

    scenes = []
    for i, (start, end) in enumerate(scene_list):
        scenes.append({
            "scene_number": i + 1,
            "start_timestamp": round(start.get_seconds(), 2),
            "end_timestamp": round(end.get_seconds(), 2),
            "duration": round(end.get_seconds() - start.get_seconds(), 2),
            "start_timecode": str(start),
            "end_timecode": str(end),
        })

    with open(output_path, "w") as f:
        json.dump(scenes, f, indent=2)

    print(f"Scene boundaries saved to: {output_path}")

    # Print summary
    durations = [s["duration"] for s in scenes]
    if durations:
        print(f"\nSummary:")
        print(f"  Total scenes: {len(scenes)}")
        print(f"  Shortest scene: {min(durations):.1f}s")
        print(f"  Longest scene: {max(durations):.1f}s")
        print(f"  Average duration: {sum(durations)/len(durations):.1f}s")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python detect_scenes.py <video_path> <output.json> [threshold]")
        print("Example: python detect_scenes.py compressed.mp4 scenes.json 27")
        sys.exit(1)

    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 27.0
    detect_scenes(sys.argv[1], sys.argv[2], threshold)
