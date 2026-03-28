#!/usr/bin/env python3
"""
CutPrint™ — Automatic Scene Calibration for Narralytica

Analyzes the editing rhythm of a TV show by processing sample episodes
and computing optimal scene detection parameters. Each show gets a
"CutPrint" profile that's stored and reused for all future episode processing.

Usage:
    # Calibrate from specific files
    python cutprint.py calibrate \
        --files ep1.mp4 ep2.mp4 ep3.mp4 \
        --genre classic_animation

    # Calibrate from a show's Plex library (auto-selects episodes)
    python cutprint.py calibrate \
        --show "The Simpsons" \
        --library-path "/Volumes/Chaos/TV Shows" \
        --genre classic_animation

    # Test a specific episode with an existing profile
    python cutprint.py test \
        --file episode.mp4 \
        --threshold 27 \
        --min-scene 45

Output: JSON profile with threshold, min_scene_duration, and diagnostics.
"""

import argparse
import json
import os
import re
import subprocess
import statistics
import sys
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

try:
    import scenedetect
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector
except ImportError:
    print("ERROR: pip install 'scenedetect[opencv]'")
    sys.exit(1)


# Genre presets — starting points for calibration
GENRE_PRESETS = {
    "classic_animation": {
        "threshold_range": (22, 35),
        "min_scene_range": (35, 60),
        "expected_scenes_per_minute": (1.0, 1.5),
        "description": "Hand-drawn/cel animation (Simpsons, Futurama, classic Disney TV)",
    },
    "modern_animation": {
        "threshold_range": (25, 38),
        "min_scene_range": (30, 50),
        "expected_scenes_per_minute": (1.0, 1.8),
        "description": "Digital animation (Rick & Morty, Archer, Bob's Burgers)",
    },
    "anime": {
        "threshold_range": (20, 30),
        "min_scene_range": (45, 90),
        "expected_scenes_per_minute": (0.5, 1.2),
        "description": "Japanese animation (longer scenes, more static shots)",
    },
    "live_action_comedy": {
        "threshold_range": (28, 42),
        "min_scene_range": (30, 60),
        "expected_scenes_per_minute": (0.8, 1.5),
        "description": "Sitcoms, sketch shows (multi-cam and single-cam)",
    },
    "live_action_drama": {
        "threshold_range": (28, 42),
        "min_scene_range": (45, 90),
        "expected_scenes_per_minute": (0.5, 1.0),
        "description": "Dramas, thrillers (longer scenes, more atmosphere)",
    },
    "live_action_action": {
        "threshold_range": (30, 45),
        "min_scene_range": (25, 50),
        "expected_scenes_per_minute": (1.0, 2.0),
        "description": "Action shows (fast cuts during action, longer dialog scenes)",
    },
    "reality_documentary": {
        "threshold_range": (25, 40),
        "min_scene_range": (40, 90),
        "expected_scenes_per_minute": (0.5, 1.2),
        "description": "Reality TV, documentaries, interview formats",
    },
}


@dataclass
class CutPrintProfile:
    """The calibrated scene detection profile for a show."""
    show_name: str
    genre: str
    threshold: int
    min_scene_duration: int  # seconds
    # Diagnostics
    sample_episodes: list
    raw_cuts_per_minute: float
    median_scene_duration: float
    scene_duration_stddev: float
    scenes_per_minute: float
    total_sample_duration_minutes: float
    calibration_version: str = "1.0"

    def to_dict(self):
        return asdict(self)

    def summary(self) -> str:
        return (
            f"CutPrint Profile: {self.show_name}\n"
            f"  Genre: {self.genre}\n"
            f"  Threshold: {self.threshold}\n"
            f"  Min Scene Duration: {self.min_scene_duration}s\n"
            f"  Scenes/minute: {self.scenes_per_minute:.1f}\n"
            f"  Median scene: {self.median_scene_duration:.0f}s\n"
            f"  Stddev: {self.scene_duration_stddev:.1f}s\n"
            f"  Raw cuts/minute: {self.raw_cuts_per_minute:.1f}\n"
            f"  Calibrated from {len(self.sample_episodes)} episodes "
            f"({self.total_sample_duration_minutes:.1f} min total)"
        )


def ensure_mp4(video_path: str) -> str:
    """Convert video to MP4 if needed (OpenCV can't read .ogm, .mkv, etc.)."""
    ext = Path(video_path).suffix.lower()
    if ext in (".mp4", ".m4v"):
        return video_path

    tmp = tempfile.mktemp(suffix=".mp4")
    print(f"  Converting {ext} -> .mp4 for analysis...")
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-an",  # No audio needed for scene detection
            tmp,
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-500:]}")
        sys.exit(1)
    return tmp


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def detect_raw_cuts(video_path: str, threshold: int) -> list:
    """Run ContentDetector and return raw scene boundaries."""
    video = open_video(video_path)
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=threshold))
    sm.detect_scenes(video)
    return sm.get_scene_list()


def merge_scenes(raw_scenes: list, min_scene_seconds: int) -> list:
    """Merge raw shot-level cuts into scene-level segments."""
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

    # Second pass: catch any remaining short scenes
    final = []
    for s, e in merged:
        d = (e - s).get_seconds()
        if final and d < min_scene_seconds:
            final[-1] = (final[-1][0], e)
        else:
            final.append((s, e))

    return final


def score_segmentation(scenes: list, duration_minutes: float, genre_preset: dict) -> float:
    """Score a segmentation result. Higher = better.

    Rewards:
    - Scene count within expected range for genre
    - Low variance in scene durations (consistent segments)
    - No extremely short or long scenes

    Penalizes:
    - Too many or too few scenes
    - High variance (mix of 10s and 120s scenes = bad)
    - Any scene < 15s or > 3 minutes
    """
    if not scenes:
        return 0.0

    durations = [(e - s).get_seconds() for s, e in scenes]
    n = len(scenes)
    avg = statistics.mean(durations)
    median = statistics.median(durations)
    stddev = statistics.stdev(durations) if len(durations) > 1 else 0

    scenes_per_min = n / duration_minutes if duration_minutes > 0 else 0

    expected_low, expected_high = genre_preset["expected_scenes_per_minute"]
    score = 100.0

    # Penalty: scenes/minute outside expected range
    if scenes_per_min < expected_low:
        score -= (expected_low - scenes_per_min) * 30
    elif scenes_per_min > expected_high:
        score -= (scenes_per_min - expected_high) * 30

    # Penalty: high coefficient of variation (want consistent scenes)
    cv = stddev / avg if avg > 0 else 0
    score -= cv * 40

    # Penalty: any scene under 15s
    short_count = sum(1 for d in durations if d < 15)
    score -= short_count * 10

    # Penalty: any scene over 180s (3 min)
    long_count = sum(1 for d in durations if d > 180)
    score -= long_count * 15

    # Bonus: median close to genre sweet spot
    min_scene_low, min_scene_high = genre_preset["min_scene_range"]
    ideal_median = (min_scene_low + min_scene_high) / 2
    median_diff = abs(median - ideal_median) / ideal_median
    score -= median_diff * 20

    return max(0, score)


def calibrate_episode(video_path: str, genre: str) -> dict:
    """Test multiple parameter combinations on a single episode."""
    preset = GENRE_PRESETS[genre]
    mp4_path = ensure_mp4(video_path)
    duration = get_video_duration(mp4_path)
    duration_min = duration / 60

    print(f"  Duration: {duration_min:.1f} min")

    t_low, t_high = preset["threshold_range"]
    ms_low, ms_high = preset["min_scene_range"]

    best_score = -1
    best_params = None
    results = []

    # Sweep threshold and min_scene combinations
    thresholds = range(t_low, t_high + 1, 3)
    min_scenes = range(ms_low, ms_high + 1, 5)

    for threshold in thresholds:
        raw = detect_raw_cuts(mp4_path, threshold)
        raw_count = len(raw)

        for min_scene in min_scenes:
            scenes = merge_scenes(raw, min_scene)
            durations = [(e - s).get_seconds() for s, e in scenes]

            if len(durations) < 2:
                continue

            score = score_segmentation(scenes, duration_min, preset)

            result = {
                "threshold": threshold,
                "min_scene": min_scene,
                "raw_cuts": raw_count,
                "scene_count": len(scenes),
                "median_duration": statistics.median(durations),
                "stddev": statistics.stdev(durations),
                "score": score,
            }
            results.append(result)

            if score > best_score:
                best_score = score
                best_params = result

    # Clean up temp file
    if mp4_path != video_path and os.path.exists(mp4_path):
        os.unlink(mp4_path)

    return {
        "video_path": video_path,
        "duration_minutes": duration_min,
        "best": best_params,
        "all_results": sorted(results, key=lambda x: -x["score"])[:10],
    }


def auto_select_episodes(library_path: str, show_name: str, count: int = 3) -> list:
    """Auto-select calibration episodes from a Plex library path.

    Strategy:
    - Find all seasons
    - Pick 1 mid-season episode from up to 3 seasons (first, middle, last)
    - Avoid S01E01 (pilots are atypical) and finales
    """
    show_dir = Path(library_path) / show_name
    if not show_dir.exists():
        print(f"ERROR: Show directory not found: {show_dir}")
        sys.exit(1)

    # Find all season directories
    season_dirs = sorted([
        d for d in show_dir.iterdir()
        if d.is_dir() and re.match(r"season\s+\d+", d.name, re.IGNORECASE)
    ], key=lambda d: int(re.search(r"\d+", d.name).group()))

    if not season_dirs:
        print(f"ERROR: No season directories found in {show_dir}")
        sys.exit(1)

    # Pick seasons: first, middle, last (or fewer if show has < 3 seasons)
    if len(season_dirs) >= 3:
        selected_seasons = [
            season_dirs[0],
            season_dirs[len(season_dirs) // 2],
            season_dirs[-1],
        ]
    else:
        selected_seasons = season_dirs[:count]

    episodes = []
    for season_dir in selected_seasons:
        # Get all video files in this season
        video_exts = {".mp4", ".mkv", ".avi", ".ogm", ".m4v", ".wmv", ".flv", ".ts"}
        video_files = sorted([
            f for f in season_dir.iterdir()
            if f.suffix.lower() in video_exts
        ])

        if not video_files:
            continue

        # Pick a mid-season episode (avoid first and last)
        if len(video_files) >= 5:
            # Pick episode 4 or 5 (0-indexed: 3 or 4)
            idx = min(4, len(video_files) - 2)
        elif len(video_files) >= 3:
            idx = 1  # Second episode
        else:
            idx = 0  # Only option

        episodes.append(str(video_files[idx]))

    return episodes[:count]


def calibrate(files: list, genre: str, show_name: str = "Unknown") -> CutPrintProfile:
    """Run full calibration across multiple episodes."""
    print(f"\n{'='*60}")
    print(f"CutPrint Calibration: {show_name}")
    print(f"Genre: {genre} — {GENRE_PRESETS[genre]['description']}")
    print(f"Sample episodes: {len(files)}")
    print(f"{'='*60}\n")

    episode_results = []
    for i, f in enumerate(files):
        print(f"[{i+1}/{len(files)}] Analyzing: {Path(f).name}")
        result = calibrate_episode(f, genre)
        episode_results.append(result)
        if result["best"]:
            b = result["best"]
            print(f"  Best: threshold={b['threshold']}, min_scene={b['min_scene']}s "
                  f"-> {b['scene_count']} scenes (score={b['score']:.1f})")
        print()

    # Aggregate: take the median of best parameters across episodes
    best_thresholds = [r["best"]["threshold"] for r in episode_results if r["best"]]
    best_min_scenes = [r["best"]["min_scene"] for r in episode_results if r["best"]]

    if not best_thresholds:
        print("ERROR: Calibration failed — no valid results")
        sys.exit(1)

    final_threshold = int(statistics.median(best_thresholds))
    final_min_scene = int(statistics.median(best_min_scenes))

    # Compute final diagnostics by re-running with chosen params
    all_durations = []
    total_raw = 0
    total_duration = 0

    for r in episode_results:
        mp4_path = ensure_mp4(r["video_path"])
        raw = detect_raw_cuts(mp4_path, final_threshold)
        total_raw += len(raw)
        scenes = merge_scenes(raw, final_min_scene)
        durations = [(e - s).get_seconds() for s, e in scenes]
        all_durations.extend(durations)
        total_duration += r["duration_minutes"]
        if mp4_path != r["video_path"] and os.path.exists(mp4_path):
            os.unlink(mp4_path)

    profile = CutPrintProfile(
        show_name=show_name,
        genre=genre,
        threshold=final_threshold,
        min_scene_duration=final_min_scene,
        sample_episodes=[Path(f).name for f in files],
        raw_cuts_per_minute=total_raw / total_duration if total_duration > 0 else 0,
        median_scene_duration=statistics.median(all_durations),
        scene_duration_stddev=statistics.stdev(all_durations) if len(all_durations) > 1 else 0,
        scenes_per_minute=len(all_durations) / total_duration if total_duration > 0 else 0,
        total_sample_duration_minutes=total_duration,
    )

    print(f"\n{'='*60}")
    print(profile.summary())
    print(f"{'='*60}\n")

    return profile


def main():
    parser = argparse.ArgumentParser(
        description="CutPrint™ — Automatic Scene Calibration for Narralytica"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Calibrate command
    cal = subparsers.add_parser("calibrate", help="Calibrate scene detection for a show")
    cal.add_argument("--files", nargs="+", help="Video files to analyze")
    cal.add_argument("--show", help="Show name (for Plex library lookup)")
    cal.add_argument("--library-path", help="Plex library path (e.g., /Volumes/Chaos/TV Shows)")
    cal.add_argument("--genre", required=True, choices=list(GENRE_PRESETS.keys()))
    cal.add_argument("--output", default="cutprint_profile.json", help="Output profile path")

    # Test command
    test = subparsers.add_parser("test", help="Test scene detection on an episode")
    test.add_argument("--file", required=True, help="Video file to test")
    test.add_argument("--threshold", type=int, default=27)
    test.add_argument("--min-scene", type=int, default=45)

    # List genres
    subparsers.add_parser("genres", help="List available genre presets")

    args = parser.parse_args()

    if args.command == "genres":
        print("\nAvailable genre presets:\n")
        for name, preset in GENRE_PRESETS.items():
            print(f"  {name:25s} {preset['description']}")
            print(f"  {'':25s} threshold: {preset['threshold_range']}, "
                  f"min_scene: {preset['min_scene_range']}s")
            print()
        return

    if args.command == "test":
        mp4_path = ensure_mp4(args.file)
        raw = detect_raw_cuts(mp4_path, args.threshold)
        scenes = merge_scenes(raw, args.min_scene)
        durations = [(e - s).get_seconds() for s, e in scenes]
        duration_min = get_video_duration(mp4_path) / 60

        print(f"\nTest results: threshold={args.threshold}, min_scene={args.min_scene}s")
        print(f"Raw cuts: {len(raw)}, Merged scenes: {len(scenes)}")
        print(f"Episode duration: {duration_min:.1f} min")
        print(f"Scenes/minute: {len(scenes)/duration_min:.1f}")
        print(f"Median scene: {statistics.median(durations):.0f}s")
        print(f"\nScenes:")
        for i, d in enumerate(durations):
            print(f"  {i+1:3d}: {int(d//60)}:{int(d%60):02d} ({d:.0f}s)")

        if mp4_path != args.file and os.path.exists(mp4_path):
            os.unlink(mp4_path)
        return

    if args.command == "calibrate":
        show_name = args.show or "Unknown Show"

        if args.files:
            files = args.files
        elif args.show and args.library_path:
            files = auto_select_episodes(args.library_path, args.show)
            print(f"Auto-selected {len(files)} episodes:")
            for f in files:
                print(f"  {f}")
        else:
            print("ERROR: Provide --files or both --show and --library-path")
            sys.exit(1)

        profile = calibrate(files, args.genre, show_name)

        # Save profile
        with open(args.output, "w") as f:
            json.dump(profile.to_dict(), f, indent=2)
        print(f"Profile saved to: {args.output}")

        return

    parser.print_help()


if __name__ == "__main__":
    main()
