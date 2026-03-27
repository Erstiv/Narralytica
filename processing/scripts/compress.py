#!/usr/bin/env python3
"""
Narralytica: Video Compression Script (Run on M5 Mac)

Compresses a video file for Gemini analysis.
Target: 720p, 1 FPS, H.264 CRF 25, AAC 128kbps

Usage:
    python compress.py /path/to/input.mkv /path/to/output.mp4

What it does:
    1. Takes your original episode file (could be 1-4 GB)
    2. Shrinks it to 720p resolution
    3. Drops to 1 frame per second (enough for Gemini to analyze)
    4. Compresses with H.264 at quality level 25
    5. Keeps audio at 128kbps AAC
    6. Output is typically 50-150 MB
"""
import subprocess
import sys
import os


def compress_video(input_path: str, output_path: str) -> None:
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Get input file size for comparison
    input_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    print(f"Input: {input_path} ({input_size_mb:.1f} MB)")
    print(f"Output: {output_path}")
    print("Compressing... this may take a few minutes.")

    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vf", "scale=1280:720:flags=lanczos",
        "-r", "1",                  # 1 FPS — enough for Gemini scene analysis
        "-c:v", "libx264",
        "-crf", "25",               # Quality level (lower = better, 25 is good for animated)
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "128k",
        "-y",                       # Overwrite output if exists
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg error:\n{result.stderr}")
        sys.exit(1)

    output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    ratio = input_size_mb / output_size_mb if output_size_mb > 0 else 0
    print(f"\nDone! Output: {output_size_mb:.1f} MB (compression ratio: {ratio:.1f}x)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compress.py <input_video> <output.mp4>")
        print("Example: python compress.py /path/to/simpsons_s04e17.mkv compressed.mp4")
        sys.exit(1)

    compress_video(sys.argv[1], sys.argv[2])
