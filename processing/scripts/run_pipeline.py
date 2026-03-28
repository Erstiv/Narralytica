#!/usr/bin/env python3
"""
Narralytica: Full Indexing Pipeline (Run on Plex Mac)

Runs the complete pipeline:
  0. CutPrint™ scene detection (if --show-id provided)
  1. Whisper transcription (parallel)  ─┐
  2. Gemini video analysis (parallel)  ─┤
  3. Merge transcripts (waits for 1+2) ─┘
  4. Generate embeddings
  5. Push to server

Usage:
    export GEMINI_API_KEY=your_key_here

    # With CutPrint (fetches profile from API, runs scene detection automatically):
    python run_pipeline.py video.mp4 --show-id 1 --episode-id 5

    # Without CutPrint (provide pre-existing scenes JSON):
    python run_pipeline.py video.mp4 --scenes-json scenes.json --episode-id 5

    # With a local CutPrint profile file:
    python run_pipeline.py video.mp4 --cutprint-profile cutprint_simpsons.json --episode-id 5
"""
import subprocess
import sys
import os
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


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


def fetch_cutprint_profile(api_url: str, show_id: int) -> dict:
    """Fetch a show's CutPrint profile from the Narralytica API."""
    if not HAS_HTTPX:
        print("ERROR: httpx not installed. Install it or use --cutprint-profile with a local file.")
        sys.exit(1)

    url = f"{api_url}/api/library/shows/{show_id}/cutprint"
    print(f"Fetching CutPrint™ profile from {url}...")
    r = httpx.get(url, timeout=10.0)
    if r.status_code == 404:
        print(f"ERROR: No CutPrint™ profile for show {show_id}. Run cutprint_calibrate.py first.")
        sys.exit(1)
    r.raise_for_status()
    profile = r.json()
    print(f"  Threshold: {profile.get('threshold')}, Min scene: {profile.get('min_scene_duration')}s, Genre: {profile.get('genre')}")
    return profile


def main():
    parser = argparse.ArgumentParser(description="Run full Narralytica indexing pipeline")
    parser.add_argument("original_video", help="Path to original video file")
    parser.add_argument("--scenes-json", help="Path to pre-existing scene boundaries JSON (skip CutPrint detection)")
    parser.add_argument("--show-id", type=int, help="Show ID — fetches CutPrint profile from API and runs scene detection")
    parser.add_argument("--cutprint-profile", help="Path to local CutPrint profile JSON (alternative to --show-id)")
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
    output_dir = "processing/output"
    os.makedirs(output_dir, exist_ok=True)
    start_time = time.time()

    # === STEP 0: CutPrint™ Scene Detection ===
    scenes_json = args.scenes_json

    if not scenes_json:
        # Need to run scene detection
        scenes_json = os.path.join(output_dir, "scenes.json")

        detect_cmd = [
            sys.executable, os.path.join(scripts_dir, "detect_scenes.py"),
            args.original_video, scenes_json,
        ]

        if args.show_id:
            # Fetch profile from API, write to temp file
            profile = fetch_cutprint_profile(args.api_url, args.show_id)
            profile_path = os.path.join(output_dir, "cutprint_profile.json")
            with open(profile_path, "w") as f:
                json.dump(profile, f, indent=2)
            detect_cmd.extend(["--profile", profile_path])
        elif args.cutprint_profile:
            detect_cmd.extend(["--profile", args.cutprint_profile])
        else:
            print("WARNING: No CutPrint profile provided. Using default threshold (27) with no merge.")
            print("         For better results, use --show-id or --cutprint-profile.")

        name, success, _ = run_step("CutPrint™ Scene Detection", detect_cmd)
        if not success:
            sys.exit(1)
    else:
        print(f"Using pre-existing scenes: {scenes_json}")

    # === PARALLEL: Whisper + Gemini ===
    print("\n" + "=" * 60)
    print("PHASE 1: Whisper + Gemini (running in parallel)")
    print("=" * 60)

    whisper_cmd = [
        sys.executable, os.path.join(scripts_dir, "whisper_transcribe.py"),
        args.original_video,
        "--output", os.path.join(output_dir, "whisper_transcript.json"),
    ]
    gemini_cmd = [
        sys.executable, os.path.join(scripts_dir, "gemini_index.py"),
        args.compressed_video, scenes_json,
        "--output", os.path.join(output_dir, "scenes_gemini.json"),
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
        os.path.join(output_dir, "whisper_transcript.json"),
        os.path.join(output_dir, "scenes_gemini.json"),
        "--output", os.path.join(output_dir, "scenes_merged.json"),
    ])
    if not success:
        sys.exit(1)

    # Step 4: Embeddings
    name, success, _ = run_step("Generate Embeddings", [
        sys.executable, os.path.join(scripts_dir, "generate_embeddings.py"),
        os.path.join(output_dir, "scenes_merged.json"),
        "--output", os.path.join(output_dir, "scenes_final.json"),
    ])
    if not success:
        sys.exit(1)

    # Step 5: Push to server
    name, success, _ = run_step("Push to Server", [
        sys.executable, os.path.join(scripts_dir, "push_scenes.py"),
        os.path.join(output_dir, "scenes_final.json"),
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
