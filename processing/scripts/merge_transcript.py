#!/usr/bin/env python3
"""
Narralytica: Merge Whisper + Gemini Transcripts (Run on M5 Mac)

Takes Whisper's verbatim word-level transcript and Gemini's scene analysis
with named speakers, then merges them into a unified diarized transcript.

Strategy:
  - Whisper provides: exact words + precise timestamps
  - Gemini provides: speaker names + contextual understanding
  - Merge: align by timestamp, replace generic speakers with named characters

Usage:
    python merge_transcript.py \
        processing/output/whisper_transcript.json \
        processing/output/scenes_gemini.json

Output: processing/output/scenes_final.json (updates scenes with merged transcript)

Install:
    pip install rapidfuzz
"""
import json
import sys
import os
import argparse

from rapidfuzz import fuzz


def find_scene_for_timestamp(scenes: list[dict], timestamp: float) -> dict | None:
    """Find which scene a timestamp falls into."""
    for scene in scenes:
        if scene["start_timestamp"] <= timestamp <= scene["end_timestamp"]:
            return scene
    return None


def match_speaker(whisper_text: str, gemini_dialog: list[dict], threshold: int = 60) -> str:
    """Use fuzzy matching to find which Gemini speaker said this line."""
    best_match = "Unknown"
    best_score = 0

    for entry in gemini_dialog:
        if not isinstance(entry, dict) or "quote" not in entry:
            continue
        score = fuzz.partial_ratio(whisper_text.lower(), entry["quote"].lower())
        if score > best_score and score >= threshold:
            best_score = score
            best_match = entry.get("speaker", "Unknown")

    return best_match


def get_scene_speakers(scene: dict) -> list[str]:
    """Get ordered list of character names from a scene."""
    chars = scene.get("characters_present", [])
    return [c["name"] for c in chars if isinstance(c, dict) and c.get("confidence", 0) > 0.5]


def merge(whisper_path: str, gemini_path: str, output_path: str) -> None:
    with open(whisper_path) as f:
        whisper_data = json.load(f)
    with open(gemini_path) as f:
        scenes = json.load(f)

    print(f"Whisper: {whisper_data['total_words']} words, {whisper_data['total_segments']} segments")
    print(f"Gemini: {len(scenes)} scenes")

    # Build merged transcript for each scene
    for scene in scenes:
        scene_start = scene["start_timestamp"]
        scene_end = scene["end_timestamp"]
        gemini_dialog = scene.get("key_dialog", [])
        scene_speakers = get_scene_speakers(scene)

        # Find Whisper segments that overlap this scene
        scene_transcript = []
        for seg in whisper_data["segments"]:
            # Check if segment overlaps with scene
            if seg["end"] < scene_start or seg["start"] > scene_end:
                continue

            text = seg["text"].strip()
            if not text:
                continue

            # Try to identify the speaker via fuzzy match against Gemini dialog
            speaker = match_speaker(text, gemini_dialog)

            # If no fuzzy match but scene has only 1-2 characters, use context
            if speaker == "Unknown" and len(scene_speakers) == 1:
                speaker = scene_speakers[0]

            entry = {
                "speaker": speaker,
                "text": text,
                "start": round(seg["start"], 3),
                "end": round(seg["end"], 3),
                "words": seg.get("words", []),
                "source": "whisper",
            }

            # Flag low-confidence merges
            if speaker == "Unknown" and len(scene_speakers) > 1:
                entry["needs_review"] = True

            scene_transcript.append(entry)

        scene["merged_transcript"] = scene_transcript

        matched = sum(1 for t in scene_transcript if t["speaker"] != "Unknown")
        total = len(scene_transcript)
        print(f"  Scene {scene.get('scene_number', '?')}: "
              f"{total} segments, {matched}/{total} speakers identified")

    # Save updated scenes with transcript
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(scenes, f, indent=2)

    total_segments = sum(len(s.get("merged_transcript", [])) for s in scenes)
    needs_review = sum(
        1 for s in scenes
        for t in s.get("merged_transcript", [])
        if t.get("needs_review")
    )

    print(f"\nMerge complete! {total_segments} transcript segments across {len(scenes)} scenes")
    if needs_review:
        print(f"  {needs_review} segments flagged for manual speaker review")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge Whisper + Gemini transcripts")
    parser.add_argument("whisper_json", help="Path to whisper_transcript.json")
    parser.add_argument("gemini_json", help="Path to scenes_gemini.json")
    parser.add_argument(
        "--output",
        default="processing/output/scenes_merged.json",
        help="Output path for merged scenes",
    )
    args = parser.parse_args()

    merge(args.whisper_json, args.gemini_json, args.output)
