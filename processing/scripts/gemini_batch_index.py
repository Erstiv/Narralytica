#!/usr/bin/env python3
"""
Narralytica: Gemini Batch Video Indexing

Instead of 55 individual API calls (one per scene), this sends ALL scenes
in a single prompt. Gemini analyzes the whole video once and returns
structured data for every scene in one response.

Falls back to chunked batches (10 scenes per call) if the single-call
response is too large.

Usage:
    export GEMINI_API_KEY=your_key
    python gemini_batch_index.py compressed.mp4 scenes.json --output scenes_gemini.json
"""
import json
import sys
import os
import time
import argparse

from google import genai
from google.genai import types


BATCH_PROMPT = """\
You are a professional media analyst. Analyze the following video and provide structured metadata for EVERY scene listed below.

The video has {total_scenes} scenes. For EACH scene, analyze the video content at the specified timestamps and return a JSON array with one object per scene.

Scenes to analyze:
{scene_list}

For EACH scene, return a JSON object with ALL these fields:
{{
  "scene_number": <int>,
  "characters_present": [{{"name": "Full Name", "confidence": 0.95, "is_speaking": true, "screen_position": "center"}}],
  "key_dialog": [{{"speaker": "Name", "quote": "exact or close quote", "timestamp": 123.4, "emotion": "angry", "volume_level": "normal"}}],
  "character_interactions": [{{"character_a": "Name A", "character_b": "Name B", "interaction_type": "arguing", "description": "brief"}}],
  "character_motivations_feelings": "Per-character emotional state and goals",
  "actions": "Description of physical actions and movements",
  "visual_gags": null,
  "dialog_based_humor": null,
  "location": "Specific location description",
  "time_of_day": "morning|afternoon|evening|night|ambiguous",
  "setting_type": "interior|exterior|both",
  "lighting": "natural|artificial|mixed|dramatic|dim|bright",
  "camera_shot_type": "wide|medium|close-up|extreme_close-up|establishing|aerial|POV|over-the-shoulder",
  "camera_movement": "static|pan|tilt|zoom|tracking|handheld|crane|dolly|steadicam",
  "scene_composition": "rule_of_thirds|centered|asymmetric|dynamic",
  "visual_style_notes": "Notable visual elements, color grading, effects",
  "color_palette": ["#HEX1", "#HEX2", "#HEX3"],
  "music_present": true,
  "music_description": "Genre, tempo, mood, diegetic/non-diegetic",
  "sound_effects": "Notable sound effects or null",
  "ambient_audio": "Background sounds or null",
  "mood_ambience": "Overall mood description",
  "scene_pacing": "slow|moderate|fast|building|declining",
  "tone": "comedic|dramatic|tense|action|romantic|melancholic|suspenseful|inspirational|horrific|neutral|introductory|informative|exciting",
  "emotional_arc": "How emotion changes through the scene",
  "tropes_memes": [],
  "cultural_references": [],
  "plot_significance": "low|medium|high|critical",
  "continuity_notes": null,
  "scene_transitions": "cut|dissolve|fade|wipe|match_cut",
  "text_on_screen": null,
  "description_text": "2-3 sentence description of what happens in this scene",
  "overall_scene_confidence": 0.9,
  "explicitness_language": 0.0,
  "explicitness_violence": 0.0,
  "explicitness_sexual": 0.0,
  "explicitness_substance": 0.0,
  "explicitness_thematic": 0.0
}}

Return a JSON array of {total_scenes} objects, one for each scene, in order. Respond ONLY with the JSON array, no other text.
"""


def upload_video(client, video_path):
    print(f"Uploading {video_path} to Gemini...")
    video_file = client.files.upload(file=video_path)
    print(f"Upload complete: {video_file.name}")

    while video_file.state.name == "PROCESSING":
        print("  Waiting for video processing...")
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        print(f"Video processing failed!")
        sys.exit(1)

    print(f"Video ready!")
    return video_file


def analyze_batch(client, video_file, scenes, batch_label=""):
    """Analyze a batch of scenes in a single API call."""
    scene_list = "\n".join([
        f"  Scene {s['scene_number']}: {s['start_timecode']} - {s['end_timecode']} ({s['duration']:.0f}s)"
        for s in scenes
    ])

    prompt = BATCH_PROMPT.format(
        total_scenes=len(scenes),
        scene_list=scene_list,
    )

    print(f"  Sending batch of {len(scenes)} scenes to Gemini{batch_label}...")
    max_retries = 3
    for attempt in range(max_retries):
        try:
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

            text = response.text.strip()
            results = json.loads(text)
            if isinstance(results, list):
                print(f"  Got {len(results)} scene analyses back.")
                return results
            else:
                print(f"  WARNING: Expected array, got {type(results)}")
                return [results]

        except json.JSONDecodeError as e:
            print(f"  JSON parse error (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return []

        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = 30 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s (attempt {attempt+1})...")
                time.sleep(wait)
                continue
            print(f"  API error (attempt {attempt+1}): {err[:200]}")
            if attempt < max_retries - 1:
                time.sleep(10)
                continue
            return []

    return []


def main():
    parser = argparse.ArgumentParser(description="Batch Gemini video indexing")
    parser.add_argument("video_path", help="Compressed video file")
    parser.add_argument("scenes_json", help="Scene boundaries JSON")
    parser.add_argument("--output", default="scenes_gemini.json")
    parser.add_argument("--batch-size", type=int, default=0,
                        help="Scenes per API call (0 = all at once)")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY")
        sys.exit(1)

    with open(args.scenes_json) as f:
        scenes = json.load(f)

    print(f"Loaded {len(scenes)} scenes")

    client = genai.Client(api_key=api_key)
    video_file = upload_video(client, args.video_path)

    t0 = time.time()

    if args.batch_size <= 0 or args.batch_size >= len(scenes):
        # Try all scenes in one call
        print(f"\nAnalyzing all {len(scenes)} scenes in ONE call...")
        results = analyze_batch(client, video_file, scenes)

        if len(results) < len(scenes) * 0.8:
            # Fallback: chunk into batches of 10
            print(f"\n  Only got {len(results)} results, falling back to chunked batches...")
            results = []
            chunk_size = 10
            for i in range(0, len(scenes), chunk_size):
                chunk = scenes[i:i+chunk_size]
                label = f" (chunk {i//chunk_size + 1}/{(len(scenes)-1)//chunk_size + 1})"
                chunk_results = analyze_batch(client, video_file, chunk, label)
                results.extend(chunk_results)
                if i + chunk_size < len(scenes):
                    time.sleep(3)
    else:
        # Explicit chunking
        results = []
        for i in range(0, len(scenes), args.batch_size):
            chunk = scenes[i:i+args.batch_size]
            label = f" (batch {i//args.batch_size + 1})"
            chunk_results = analyze_batch(client, video_file, chunk, label)
            results.extend(chunk_results)
            if i + args.batch_size < len(scenes):
                time.sleep(3)

    elapsed = time.time() - t0
    print(f"\nAnalyzed {len(results)} scenes in {elapsed:.0f}s ({elapsed/60:.1f}m)")

    # Merge scene boundaries back in
    final = []
    for i, scene in enumerate(scenes):
        merged = {
            "scene_number": scene["scene_number"],
            "start_timestamp": scene["start_timestamp"],
            "end_timestamp": scene["end_timestamp"],
            "duration": scene["duration"],
            "start_timecode": scene["start_timecode"],
            "end_timecode": scene["end_timecode"],
        }
        if i < len(results):
            merged.update(results[i])
        final.append(merged)

    # Validate: count scenes with actual data
    good = sum(1 for s in final if s.get("tone"))
    print(f"Validation: {good}/{len(final)} scenes have Gemini data")

    if good == 0:
        print("ERROR: Zero scenes have valid data! Not saving.")
        sys.exit(1)

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(final, f, indent=2)
    print(f"Saved to {args.output}")

    # Cleanup
    try:
        client.files.delete(name=video_file.name)
        print("Cleaned up uploaded video.")
    except Exception:
        pass


if __name__ == "__main__":
    main()
