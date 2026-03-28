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
You are a professional media analyst indexing a scene from an animated TV show.

Analyze the video content between {start_timecode} and {end_timecode} (scene {scene_number} of {total_scenes}).

Return a JSON object with ALL of the following fields. Be thorough — this data powers a search engine, export system, and metadata script. Every field matters.

{{
  "characters_present": [
    {{"name": "Full Name", "confidence": 0.95, "is_speaking": true, "screen_position": "center"}}
  ],
  "key_dialog": [
    {{"speaker": "Name", "quote": "exact or close quote", "timestamp": 123.4, "emotion": "angry", "volume_level": "normal"}}
  ],
  "character_interactions": [
    {{"character_a": "Name A", "character_b": "Name B", "interaction_type": "arguing", "description": "brief description"}}
  ],
  "character_motivations_feelings": "Per-character emotional state and goals in this scene",
  "actions": "Description of physical actions and movements",
  "visual_gags": "Slapstick, sight gags, background jokes (null if none)",
  "dialog_based_humor": "Puns, callbacks, irony, sarcasm (null if none)",
  "objects_present": [
    {{"name": "donut", "category": "food", "prominence": "foreground", "confidence": 0.95, "state": "half-eaten", "spatial_relationship": "in_hand", "first_appearance_timestamp": 142.5}}
  ],
  "location": "Specific named location (e.g., Springfield Nuclear Plant, Sector 7-G)",
  "time_of_day": "morning|afternoon|evening|night|ambiguous",
  "setting_type": "interior|exterior|both",
  "color_palette": ["#FFD521", "#4A90D9", "#8B4513"],
  "lighting": "bright|dim|dramatic|natural|neon|mixed",
  "camera_shot_type": "wide|medium|close-up|extreme_close-up|over-the-shoulder|establishing|aerial|POV|mixed",
  "camera_movement": "static|pan|zoom|tracking|dolly|mixed",
  "scene_composition": "rule_of_thirds|centered|asymmetric|dynamic",
  "visual_style_notes": "Any notable artistic choices or visual techniques",
  "music_present": true,
  "music_description": "Genre, mood, tempo. Is it diegetic (in-scene) or score?",
  "sound_effects": "Notable sounds (explosion, doorbell, laugh track, etc.)",
  "ambient_audio": "Background noise description",
  "mood_ambience": "Overall emotional feeling of the scene",
  "scene_pacing": "fast|moderate|slow|building|frenetic",
  "tone": "comedic|dramatic|tense|melancholy|absurd|heartfelt|mixed",
  "emotional_arc": "How the mood shifts within the scene (e.g., comedic to melancholy)",
  "tropes_memes": ["recognizable TV tropes", "meme-worthy moments"],
  "cultural_references": ["specific movies, songs, events being referenced or parodied"],
  "recurring_gags": "Callbacks to previous episodes or running jokes (null if none)",
  "plot_significance": "low|medium|high|critical",
  "continuity_notes": "References to events in other episodes (null if none)",
  "explicitness_language": 0.1,
  "explicitness_violence": 0.0,
  "explicitness_sexual": 0.0,
  "explicitness_substance": 0.2,
  "explicitness_thematic": 0.1,
  "scene_transitions": "How this scene starts and ends (cut, fade, wipe, dissolve)",
  "text_on_screen": "Signs, chalkboard gags, newspaper headlines, screen text (null if none)",
  "overall_scene_confidence": 0.85,
  "description_text": "A comprehensive 3-4 sentence natural language summary of this entire scene. Include who is present, what happens, the emotional tone, key dialog, setting, and any memorable moments. This powers the search engine — be rich and specific."
}}

Rules:
- Return ONLY valid JSON, no markdown fences, no extra text
- Confidence values: 0.0-1.0
- Explicitness scores: 0.0-1.0 per dimension
- Be specific about character names (full names when known)
- If you cannot determine a field, use null (not empty string)
- objects_present categories: food, vehicle, setting_element, prop, signage, animal, clothing, document, weapon, technology, furniture, decoration
- objects_present state: full, partial, broken, lit, open, closed, half-eaten, etc.
- objects_present spatial_relationship: on_table, in_hand, on_wall, background, foreground, etc.
- color_palette: Use hex color codes
- screen_position: left, center, right, background
- volume_level: whisper, quiet, normal, loud, shouting
- description_text should be rich, detailed, and optimized for semantic search
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
