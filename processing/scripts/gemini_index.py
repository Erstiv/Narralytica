#!/usr/bin/env python3
"""
Narralytica: Gemini Video Indexing (Run on M5 Mac)

Uploads compressed video to Gemini, then analyzes each scene to produce
structured JSON matching the Narralytica Scene model.

Usage:
    export GEMINI_API_KEY=your_key_here
    python gemini_index.py processing/output/compressed.mp4 processing/output/scenes.json

Output: processing/output/scenes_gemini.json
"""
import json
import sys
import os
import time
import argparse

from google import genai
from google.genai import types


ANALYSIS_PROMPT = """\
You are analyzing a specific scene from The Simpsons episode "Last Exit to Springfield" (S04E17).

Analyze the video content between {start_timecode} and {end_timecode} (scene {scene_number} of {total_scenes}).

Return a JSON object with EXACTLY these fields:

{{
  "characters_present": [
    {{"name": "Homer Simpson", "confidence": 0.95}},
    {{"name": "Mr. Burns", "confidence": 0.90}}
  ],
  "key_dialog": [
    {{"speaker": "Homer", "quote": "exact or close quote", "timestamp": 123.4}}
  ],
  "actions": "Brief description of physical actions and movements in this scene",
  "interactions": "How characters interact with each other",
  "mood_ambience": "Emotional tone, lighting, music cues",
  "color_palette": ["yellow", "blue", "brown"],
  "tropes_memes": ["Union negotiation", "Homer as accidental genius"],
  "explicitness": "none",
  "background": "Setting description - where the scene takes place",
  "scene_transitions": "How the scene starts and ends (cut, fade, etc.)",
  "motivations_feelings": "What characters want and feel in this scene",
  "objects_present": [
    {{"name": "donut", "category": "food", "prominence": "foreground", "confidence": 0.95, "first_appearance_timestamp": 142.5}},
    {{"name": "nuclear reactor control panel", "category": "setting_element", "prominence": "background", "confidence": 0.88, "first_appearance_timestamp": 140.0}}
  ],
  "overall_scene_confidence": 0.85,
  "description_text": "A comprehensive 2-3 sentence natural language summary of this entire scene, suitable for semantic search. Include who is present, what happens, the emotional tone, and any memorable moments."
}}

Rules:
- Return ONLY valid JSON, no markdown fences, no extra text
- Confidence values 0.0-1.0
- description_text should be rich and searchable (this powers the search engine)
- Be specific about Simpsons characters by full name
- If you can't see the scene clearly, lower the confidence values
- objects_present: Tag every notable object. Categories: food, vehicle, setting_element, prop, signage, animal, clothing, document. Prominence: foreground, midground, background.
"""


def upload_video(client: genai.Client, video_path: str) -> types.File:
    """Upload video to Gemini Files API and wait for processing."""
    print(f"Uploading {video_path} to Gemini...")
    video_file = client.files.upload(file=video_path)
    print(f"Upload complete. File name: {video_file.name}")

    # Wait for video processing
    while video_file.state.name == "PROCESSING":
        print("  Waiting for Gemini to process video...")
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        print(f"Video processing failed: {video_file.state}")
        sys.exit(1)

    print(f"Video ready! State: {video_file.state.name}")
    return video_file


def analyze_scene(
    client: genai.Client,
    video_file: types.File,
    scene: dict,
    total_scenes: int,
) -> dict:
    """Ask Gemini to analyze a specific scene in the video."""
    prompt = ANALYSIS_PROMPT.format(
        start_timecode=scene["start_timecode"],
        end_timecode=scene["end_timecode"],
        scene_number=scene["scene_number"],
        total_scenes=total_scenes,
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Content(
                parts=[
                    types.Part.from_uri(
                        file_uri=video_file.uri,
                        mime_type=video_file.mime_type,
                    ),
                    types.Part.from_text(text=prompt),
                ]
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )

    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        print(f"  WARNING: Failed to parse JSON for scene {scene['scene_number']}")
        print(f"  Raw response: {response.text[:500]}")
        result = {"parse_error": True, "raw_text": response.text[:2000]}

    return result


def main():
    parser = argparse.ArgumentParser(description="Analyze video scenes with Gemini")
    parser.add_argument("video_path", help="Path to compressed video file")
    parser.add_argument("scenes_json", help="Path to scene boundaries JSON from detect_scenes.py")
    parser.add_argument(
        "--output",
        default="processing/output/scenes_gemini.json",
        help="Output path for Gemini analysis results",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY environment variable")
        print("  export GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    if not os.path.exists(args.video_path):
        print(f"ERROR: Video not found: {args.video_path}")
        sys.exit(1)

    with open(args.scenes_json) as f:
        scenes = json.load(f)

    print(f"Loaded {len(scenes)} scenes from {args.scenes_json}")

    client = genai.Client(api_key=api_key)
    video_file = upload_video(client, args.video_path)

    results = []
    for i, scene in enumerate(scenes):
        print(f"\nAnalyzing scene {scene['scene_number']}/{len(scenes)} "
              f"({scene['start_timecode']} - {scene['end_timecode']}, {scene['duration']:.0f}s)...")

        gemini_data = analyze_scene(client, video_file, scene, len(scenes))

        # Merge scene boundaries with Gemini analysis
        merged = {
            "scene_number": scene["scene_number"],
            "start_timestamp": scene["start_timestamp"],
            "end_timestamp": scene["end_timestamp"],
            "duration": scene["duration"],
            "start_timecode": scene["start_timecode"],
            "end_timecode": scene["end_timecode"],
            **gemini_data,
        }
        results.append(merged)
        print(f"  Done. Confidence: {gemini_data.get('overall_scene_confidence', '?')}")

        # Brief pause between API calls to be respectful
        if i < len(scenes) - 1:
            time.sleep(2)

    # Save results
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nAll {len(results)} scenes analyzed!")
    print(f"Output saved to: {args.output}")

    # Clean up uploaded file
    try:
        client.files.delete(name=video_file.name)
        print("Cleaned up uploaded video from Gemini.")
    except Exception as e:
        print(f"Note: Could not delete uploaded file: {e}")


if __name__ == "__main__":
    main()
