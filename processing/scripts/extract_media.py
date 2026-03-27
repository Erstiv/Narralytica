#!/usr/bin/env python3
"""
Narralytica: Extract Thumbnails + Clips (Run on M5 Mac)

Uses FFmpeg to extract a thumbnail JPG and a preview clip MP4
for each scene from the original video file.

Usage:
    python extract_media.py input/simpsons_s04e17.ogm processing/output/scenes.json

Output:
    processing/output/media/thumbs/scene_01.jpg  (640px wide)
    processing/output/media/clips/scene_01.mp4   (720p, fast-start)
"""
import json
import sys
import os
import subprocess
import argparse


def extract_thumbnail(video_path: str, timestamp: float, output_path: str) -> bool:
    """Extract a single frame as JPG at the given timestamp."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-frames:v", "1",
        "-vf", "scale=640:-1",
        "-q:v", "3",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def extract_clip(video_path: str, start: float, end: float, output_path: str) -> bool:
    """Extract a video clip between start and end timestamps."""
    duration = end - start
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", str(duration),
        "-vf", "scale=1280:720:flags=lanczos",
        "-c:v", "libx264", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Extract thumbnails and clips for each scene")
    parser.add_argument("video_path", help="Path to original video file")
    parser.add_argument("scenes_json", help="Path to scenes JSON (from detect_scenes.py)")
    parser.add_argument("--output-dir", default="processing/output/media",
                        help="Output directory for media files")
    parser.add_argument("--thumbs-only", action="store_true",
                        help="Only extract thumbnails, skip clips")
    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"ERROR: Video not found: {args.video_path}")
        sys.exit(1)

    with open(args.scenes_json) as f:
        scenes = json.load(f)

    thumbs_dir = os.path.join(args.output_dir, "thumbs")
    clips_dir = os.path.join(args.output_dir, "clips")
    os.makedirs(thumbs_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)

    print(f"Extracting media for {len(scenes)} scenes from {args.video_path}")

    for scene in scenes:
        num = scene["scene_number"]
        start = scene["start_timestamp"]
        end = scene["end_timestamp"]
        # Grab thumbnail a few seconds into the scene (not the very first frame)
        thumb_ts = start + min(2.0, (end - start) / 4)

        # Thumbnail
        thumb_path = os.path.join(thumbs_dir, f"scene_{num:02d}.jpg")
        print(f"  Scene {num}: thumbnail at {thumb_ts:.1f}s...", end=" ")
        if extract_thumbnail(args.video_path, thumb_ts, thumb_path):
            size = os.path.getsize(thumb_path) / 1024
            print(f"OK ({size:.0f}KB)")
        else:
            print("FAILED")

        # Clip
        if not args.thumbs_only:
            clip_path = os.path.join(clips_dir, f"scene_{num:02d}.mp4")
            duration = end - start
            print(f"  Scene {num}: clip {start:.0f}s-{end:.0f}s ({duration:.0f}s)...", end=" ")
            if extract_clip(args.video_path, start, end, clip_path):
                size = os.path.getsize(clip_path) / (1024 * 1024)
                print(f"OK ({size:.1f}MB)")
            else:
                print("FAILED")

    print(f"\nDone! Media saved to {args.output_dir}/")
    print(f"  Thumbnails: {thumbs_dir}/")
    if not args.thumbs_only:
        print(f"  Clips: {clips_dir}/")


if __name__ == "__main__":
    main()
