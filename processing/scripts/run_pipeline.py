#!/usr/bin/env python3
"""
Narralytica: Full Indexing Pipeline (Run on M5 Mac)

Runs the complete Phase 2/2.5 pipeline:
  1. Whisper transcription (parallel)  ─┐
  2. Gemini video analysis (parallel)  ─┤
  3. Merge transcripts (waits for 1+2) ─┘
  4. Generate embeddings
  5. Push to server

Usage:
    export GEMINI_API_KEY=your_key_here
    python run_pipeline.py input/simpsons_s04e17.ogm processing/output/scenes.json

Steps 1 and 2 run in parallel. Steps 3-5 are sequential.
"""
import subprocess
import sys
import os
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_step(name: str, cmd: list[str]) -> tuple[str, bool, str]:
    """Run a pipeline step and return (name, success, output)."""
    print(f"\n{'='*60}")
    print(f"STARTING: {name}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr

    if result.returncode != 0:
        print(f"FAILED: {name}")
        print(output)
        return name, False, output

    print(output)
    return name, True, output


def main():
    parser = argparse.ArgumentParser(description="Run full Narralytica indexing pipeline")
    parser.add_argument("original_video", help="Path to original video file (for Whisper)")
    parser.add_argument("scenes_json", help="Path to scene boundaries JSON")
    parser.add_argument("--compressed-video", default="processing/output/compressed.mp4",
                        help="Path to compressed video (for Gemini)")
    parser.add_argument("--episode-id", type=int, default=1)
    parser.add_argument("--api-url", default="http://178.156.251.26:8005",
                        help="Narralytica API URL (direct IP to avoid SSL issues)")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY environment variable")
        sys.exit(1)

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    start_time = time.time()

    # === PARALLEL: Whisper + Gemini ===
    print("\n" + "=" * 60)
    print("PHASE 1: Whisper + Gemini (running in parallel)")
    print("=" * 60)

    whisper_cmd = [
        sys.executable, os.path.join(scripts_dir, "whisper_transcribe.py"),
        args.original_video,
        "--output", "processing/output/whisper_transcript.json",
    ]
    gemini_cmd = [
        sys.executable, os.path.join(scripts_dir, "gemini_index.py"),
        args.compressed_video, args.scenes_json,
        "--output", "processing/output/scenes_gemini.json",
    ]

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(run_step, "Whisper Transcription", whisper_cmd): "whisper",
            pool.submit(run_step, "Gemini Video Analysis", gemini_cmd): "gemini",
        }

        results = {}
        for future in as_completed(futures):
            name, success, output = future.result()
            results[futures[future]] = success
            if not success:
                print(f"\nFATAL: {name} failed. Aborting pipeline.")
                sys.exit(1)

    # === SEQUENTIAL: Merge → Embeddings → Push ===
    print("\n" + "=" * 60)
    print("PHASE 2: Merge → Embeddings → Push (sequential)")
    print("=" * 60)

    # Step 3: Merge
    name, success, _ = run_step("Transcript Merge", [
        sys.executable, os.path.join(scripts_dir, "merge_transcript.py"),
        "processing/output/whisper_transcript.json",
        "processing/output/scenes_gemini.json",
        "--output", "processing/output/scenes_merged.json",
    ])
    if not success:
        sys.exit(1)

    # Step 4: Embeddings
    name, success, _ = run_step("Generate Embeddings", [
        sys.executable, os.path.join(scripts_dir, "generate_embeddings.py"),
        "processing/output/scenes_merged.json",
        "--output", "processing/output/scenes_final.json",
    ])
    if not success:
        sys.exit(1)

    # Step 5: Push to server
    name, success, _ = run_step("Push to Server", [
        sys.executable, os.path.join(scripts_dir, "push_scenes.py"),
        "processing/output/scenes_final.json",
        "--episode-id", str(args.episode_id),
        "--api-url", args.api_url,
    ])
    if not success:
        sys.exit(1)

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"PIPELINE COMPLETE in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print("=" * 60)


if __name__ == "__main__":
    main()
