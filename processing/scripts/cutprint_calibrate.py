#!/usr/bin/env python3
"""
CutPrint™ Calibration — Narralytica

Analyzes 3 sample episodes from a show to determine the optimal
scene detection parameters. Stores the resulting profile for use
in all future episode processing.

How it works:
    1. Picks 3 episodes (early / mid / late season spread)
    2. Runs ContentDetector at multiple thresholds
    3. Analyzes the raw cut distribution (cuts per minute, variance)
    4. Sweeps min_scene_duration to find the value that produces
       scenes in the target range (30-90s, targeting ~50s median)
    5. Outputs a CutPrint profile JSON

Usage:
    # Auto-select episodes from Sonarr and calibrate
    python cutprint_calibrate.py --show "The Simpsons" --media-root /Volumes/Chaos/TV\ Shows

    # Manual: provide specific video files
    python cutprint_calibrate.py --files ep1.mp4 ep2.mp4 ep3.mp4

    # Specify genre hint for initial parameter ranges
    python cutprint_calibrate.py --show "The Simpsons" --genre classic_animation --media-root /Volumes/Chaos/TV\ Shows

Output: cutprint_profile.json (or --output path)
"""
import json
import os
import sys
import glob
import argparse
import statistics
import tempfile
import subprocess

from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector

# Ensure Homebrew binaries are on PATH (macOS)
if sys.platform == "darwin":
    for brew_path in ["/usr/local/bin", "/opt/homebrew/bin"]:
        if brew_path not in os.environ.get("PATH", ""):
            os.environ["PATH"] = brew_path + ":" + os.environ.get("PATH", "")

# Genre presets: starting points for calibration
GENRE_PRESETS = {
    "classic_animation": {"threshold_range": (18, 30), "min_scene_range": (40, 70), "target_median": 50},
    "modern_animation":  {"threshold_range": (22, 35), "min_scene_range": (35, 60), "target_median": 45},
    "anime":             {"threshold_range": (20, 32), "min_scene_range": (50, 90), "target_median": 65},
    "live_action_comedy": {"threshold_range": (28, 42), "min_scene_range": (35, 60), "target_median": 50},
    "live_action_drama":  {"threshold_range": (28, 42), "min_scene_range": (50, 90), "target_median": 65},
    "reality":           {"threshold_range": (30, 45), "min_scene_range": (30, 60), "target_median": 45},
}

DEFAULT_GENRE = "classic_animation"


def convert_if_needed(video_path: str) -> str:
    """Convert video to MP4 if OpenCV can't read it directly."""
    # Always try opening directly first (fastest path)
    try:
        v = open_video(video_path)
        # Verify we can actually read a frame
        return video_path
    except Exception:
        pass

    # OpenCV can't handle this format/codec — convert via FFmpeg
    tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False, dir='/tmp')
    tmp.close()
    print(f"  Converting {os.path.basename(video_path)} to MP4...")
    result = subprocess.run(
        ['ffmpeg', '-y', '-i', video_path, '-c:v', 'libx264', '-preset', 'fast',
         '-crf', '23', '-c:a', 'aac', tmp.name],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-200:]}")
        return None  # Skip this episode instead of crashing
    return tmp.name


def detect_raw_cuts(video_path: str, threshold: float) -> list:
    """Run ContentDetector and return raw scene list."""
    video = open_video(video_path)
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=threshold))
    sm.detect_scenes(video)
    return sm.get_scene_list()


def merge_shots(raw_scenes: list, min_scene_seconds: int) -> list:
    """CutPrint merge algorithm."""
    if not raw_scenes:
        return []

    merged = []
    cs, ce = raw_scenes[0]
    for i in range(1, len(raw_scenes)):
        ss, se = raw_scenes[i]
        if (ce - cs).get_seconds() < min_scene_seconds:
            ce = se
        else:
            merged.append((cs, ce))
            cs, ce = ss, se
    merged.append((cs, ce))

    final = []
    for s, e in merged:
        d = (e - s).get_seconds()
        if final and d < min_scene_seconds:
            final[-1] = (final[-1][0], e)
        else:
            final.append((s, e))

    return final


def get_durations(scenes: list) -> list:
    """Extract durations from scene list (handles both tuple and dict formats)."""
    durations = []
    for s in scenes:
        if isinstance(s, tuple):
            durations.append((s[1] - s[0]).get_seconds())
        elif isinstance(s, dict):
            durations.append(s.get("duration", 0))
    return durations


def score_distribution(durations: list, target_median: float) -> float:
    """Score a scene distribution. Lower is better.

    Penalizes:
    - Median far from target
    - High variance (inconsistent scene lengths)
    - Very short scenes (< 20s)
    - Very long scenes (> 120s)
    """
    if not durations or len(durations) < 3:
        return float('inf')

    med = statistics.median(durations)
    std = statistics.stdev(durations) if len(durations) > 1 else 0

    # How far is median from target?
    median_penalty = abs(med - target_median) * 2.0

    # Variance penalty (prefer consistent scene lengths)
    cv = std / med if med > 0 else 0  # coefficient of variation
    variance_penalty = cv * 20.0

    # Short scene penalty
    short_count = sum(1 for d in durations if d < 20)
    short_penalty = short_count * 10.0

    # Long scene penalty
    long_count = sum(1 for d in durations if d > 120)
    long_penalty = long_count * 15.0

    # Scene count reasonableness (for 22-min episode, want 15-30 scenes)
    total_time = sum(durations)
    expected_count = total_time / target_median
    actual_count = len(durations)
    count_penalty = abs(actual_count - expected_count) * 2.0

    return median_penalty + variance_penalty + short_penalty + long_penalty + count_penalty


def find_episodes(show_name: str, media_root: str) -> list:
    """Auto-select 3 episodes for calibration.

    Strategy:
    - Find the show directory
    - Pick episodes from early, mid, and late seasons
    - Avoid S01E01 (pilots are weird) and finales
    - Prefer episode 4 or 5 from each season
    """
    show_dir = os.path.join(media_root, show_name)
    if not os.path.isdir(show_dir):
        # Try case-insensitive match
        for d in os.listdir(media_root):
            if d.lower() == show_name.lower():
                show_dir = os.path.join(media_root, d)
                break

    if not os.path.isdir(show_dir):
        print(f"Error: Show directory not found: {show_dir}")
        print(f"Available shows: {', '.join(sorted(os.listdir(media_root))[:10])}...")
        sys.exit(1)

    # Find all seasons
    seasons = sorted([
        d for d in os.listdir(show_dir)
        if os.path.isdir(os.path.join(show_dir, d)) and 'season' in d.lower()
    ])

    if not seasons:
        print(f"Error: No season directories found in {show_dir}")
        sys.exit(1)

    # Pick early, mid, late seasons
    if len(seasons) >= 3:
        selected_seasons = [seasons[0], seasons[len(seasons) // 2], seasons[-1]]
    elif len(seasons) == 2:
        selected_seasons = [seasons[0], seasons[1], seasons[0]]  # repeat first
    else:
        selected_seasons = [seasons[0], seasons[0], seasons[0]]

    episodes = []
    for season_dir in selected_seasons:
        season_path = os.path.join(show_dir, season_dir)
        files = sorted([
            f for f in os.listdir(season_path)
            if os.path.isfile(os.path.join(season_path, f))
            and not f.startswith('.')
            and any(f.lower().endswith(ext) for ext in
                    ('.mp4', '.mkv', '.avi', '.ogm', '.m4v', '.mov', '.ts', '.wmv'))
        ])

        if not files:
            continue

        # Pick episode 4 or 5 (avoid pilot and finale)
        # If < 5 episodes, pick the middle one
        if len(files) >= 5:
            pick = files[3]  # 0-indexed, so this is episode 4
        elif len(files) >= 3:
            pick = files[len(files) // 2]
        else:
            pick = files[0]

        episodes.append(os.path.join(season_path, pick))

    # Deduplicate (in case we had to repeat a season)
    seen = set()
    unique = []
    for ep in episodes:
        if ep not in seen:
            seen.add(ep)
            unique.append(ep)

    return unique[:3]


def calibrate(video_paths: list, genre: str = DEFAULT_GENRE) -> dict:
    """Run CutPrint calibration on sample episodes.

    Returns a profile dict with optimal threshold and min_scene_duration.
    """
    preset = GENRE_PRESETS.get(genre, GENRE_PRESETS[DEFAULT_GENRE])
    thresh_low, thresh_high = preset["threshold_range"]
    min_low, min_high = preset["min_scene_range"]
    target_median = preset["target_median"]

    print(f"\nCutPrint™ Calibration")
    print(f"Genre preset: {genre}")
    print(f"Target median scene duration: {target_median}s")
    print(f"Threshold search range: {thresh_low}-{thresh_high}")
    print(f"Min scene search range: {min_low}-{min_high}s")
    print(f"Sample episodes: {len(video_paths)}")

    # Phase 1: Find optimal threshold by analyzing raw cut patterns
    print(f"\n{'='*60}")
    print("Phase 1: Analyzing raw cut patterns...")

    all_cuts_per_minute = {}
    converted_paths = []

    for vp in video_paths:
        print(f"\n  Episode: {os.path.basename(vp)}")
        converted = convert_if_needed(vp)
        if converted is None:
            print(f"  WARNING: Skipping (conversion failed)")
            continue
        converted_paths.append(converted)

        for threshold in range(thresh_low, thresh_high + 1, 2):
            raw = detect_raw_cuts(converted, threshold)
            if raw:
                total_time = (raw[-1][1] - raw[0][0]).get_seconds()
                cpm = len(raw) / (total_time / 60) if total_time > 0 else 0
                all_cuts_per_minute.setdefault(threshold, []).append(cpm)

    # Find the threshold with most consistent cuts/min across episodes
    print(f"\n  Threshold analysis:")
    best_threshold = thresh_low
    best_cv = float('inf')

    for threshold in sorted(all_cuts_per_minute.keys()):
        cpms = all_cuts_per_minute[threshold]
        avg_cpm = statistics.mean(cpms)
        cv = statistics.stdev(cpms) / avg_cpm if avg_cpm > 0 and len(cpms) > 1 else 0
        print(f"    threshold={threshold}: avg {avg_cpm:.1f} cuts/min, CV={cv:.2f}")
        if cv < best_cv:
            best_cv = cv
            best_threshold = threshold

    print(f"\n  → Best threshold: {best_threshold} (most consistent across episodes, CV={best_cv:.2f})")

    # Phase 2: Find optimal min_scene_duration using best threshold
    print(f"\n{'='*60}")
    print("Phase 2: Finding optimal scene merge window...")

    best_score = float('inf')
    best_min_scene = min_low
    best_stats = {}

    for min_scene in range(min_low, min_high + 1, 5):
        all_durations = []
        for converted in converted_paths:
            raw = detect_raw_cuts(converted, best_threshold)
            merged = merge_shots(raw, min_scene)
            durations = get_durations(merged)
            all_durations.extend(durations)

        if not all_durations:
            continue

        score = score_distribution(all_durations, target_median)
        med = statistics.median(all_durations)
        avg = statistics.mean(all_durations)
        std = statistics.stdev(all_durations) if len(all_durations) > 1 else 0
        n = len(all_durations) // len(video_paths)  # scenes per episode

        print(f"    min_scene={min_scene}s: {n} scenes/ep, median={med:.0f}s, avg={avg:.0f}s, σ={std:.0f}s, score={score:.1f}")

        if score < best_score:
            best_score = score
            best_min_scene = min_scene
            best_stats = {
                "scenes_per_episode": n,
                "median_duration": round(med, 1),
                "mean_duration": round(avg, 1),
                "stddev": round(std, 1),
                "calibration_score": round(score, 1),
            }

    print(f"\n  → Best min_scene: {best_min_scene}s (score={best_score:.1f})")

    # Build profile
    profile = {
        "cutprint_version": "1.0",
        "genre": genre,
        "threshold": best_threshold,
        "min_scene_duration": best_min_scene,
        "target_median": target_median,
        "calibration_stats": best_stats,
        "sample_episodes": [os.path.basename(vp) for vp in video_paths],
    }

    # Cleanup temp files
    for converted in converted_paths:
        if converted.startswith('/tmp/') and converted not in video_paths:
            try:
                os.unlink(converted)
            except OSError:
                pass

    return profile


def main():
    parser = argparse.ArgumentParser(
        description="CutPrint™ — Calibrate scene detection for a TV show"
    )
    parser.add_argument("--show", help="Show name (matches directory in media-root)")
    parser.add_argument("--media-root", help="Root media directory (e.g., /Volumes/Chaos/TV Shows)")
    parser.add_argument("--files", nargs="+", help="Manual: provide specific video files")
    parser.add_argument("--genre", default=DEFAULT_GENRE, choices=list(GENRE_PRESETS.keys()),
                        help=f"Genre preset (default: {DEFAULT_GENRE})")
    parser.add_argument("--output", default="cutprint_profile.json", help="Output profile path")

    args = parser.parse_args()

    if args.files:
        video_paths = args.files
        for vp in video_paths:
            if not os.path.exists(vp):
                print(f"Error: File not found: {vp}")
                sys.exit(1)
    elif args.show and args.media_root:
        print(f"Finding episodes for '{args.show}' in {args.media_root}...")
        video_paths = find_episodes(args.show, args.media_root)
        if not video_paths:
            print("Error: No episodes found")
            sys.exit(1)
        for vp in video_paths:
            print(f"  Selected: {os.path.basename(vp)}")
    else:
        parser.error("Provide either --show + --media-root, or --files")

    profile = calibrate(video_paths, args.genre)

    # Save profile
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(profile, f, indent=2)

    print(f"\n{'='*60}")
    print(f"CutPrint™ Profile saved: {args.output}")
    print(f"  Threshold:          {profile['threshold']}")
    print(f"  Min scene duration: {profile['min_scene_duration']}s")
    print(f"  Scenes per episode: ~{profile['calibration_stats']['scenes_per_episode']}")
    print(f"  Median duration:    {profile['calibration_stats']['median_duration']}s")
    print(f"  Genre:              {profile['genre']}")
    print(f"\nUse with: python detect_scenes.py video.mp4 scenes.json --profile {args.output}")


if __name__ == "__main__":
    main()
