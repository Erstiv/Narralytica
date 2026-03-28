#!/usr/bin/env python3
"""
Narralytica: Generate Vector Embeddings (Run on M5 Mac)

Takes the Gemini analysis JSON and generates 768-dim text embeddings
for each scene's description_text using Gemini's text-embedding-004 model.

Usage:
    export GEMINI_API_KEY=your_key_here
    python generate_embeddings.py processing/output/scenes_gemini.json

Output: processing/output/scenes_final.json (ready for push_scenes.py)
"""
import json
import sys
import os
import time
import argparse

from google import genai


EMBEDDING_MODEL = "gemini-embedding-001"  # 3072 native dims, truncated to 1536 via output_dimensionality
TASK_TYPE = "RETRIEVAL_DOCUMENT"  # Optimized for document storage (vs RETRIEVAL_QUERY for search)
OUTPUT_DIMS = 1536  # Match pgvector column: vector(1536)


def build_embedding_text(scene: dict) -> str:
    """Build a rich text string for embedding from all scene fields.

    Combines description_text with key structured fields so the vector
    captures characters, dialog, mood, and actions — not just the summary.
    """
    parts = []

    if scene.get("description_text"):
        parts.append(scene["description_text"])

    if scene.get("actions"):
        parts.append(f"Actions: {scene['actions']}")

    if scene.get("mood_ambience"):
        parts.append(f"Mood: {scene['mood_ambience']}")

    if scene.get("characters_present"):
        names = [c["name"] for c in scene["characters_present"] if isinstance(c, dict)]
        if names:
            parts.append(f"Characters: {', '.join(names)}")

    if scene.get("key_dialog"):
        quotes = []
        for d in scene["key_dialog"][:3]:  # Top 3 quotes
            if isinstance(d, dict) and d.get("quote"):
                speaker = d.get("speaker", "Unknown")
                quotes.append(f'{speaker}: "{d["quote"]}"')
        if quotes:
            parts.append("Dialog: " + " | ".join(quotes))

    if scene.get("background"):
        parts.append(f"Setting: {scene['background']}")

    if scene.get("objects_present"):
        obj_names = [o["name"] for o in scene["objects_present"] if isinstance(o, dict)]
        if obj_names:
            parts.append(f"Objects: {', '.join(obj_names)}")

    return " ".join(parts)


def generate_embedding(client: genai.Client, text: str) -> list[float]:
    """Generate a 1536-dim embedding for the given text."""
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={"task_type": TASK_TYPE, "output_dimensionality": OUTPUT_DIMS},
    )
    return result.embeddings[0].values


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for Gemini scene data")
    parser.add_argument("input_json", help="Path to scenes_gemini.json from gemini_index.py")
    parser.add_argument(
        "--output",
        default="processing/output/scenes_final.json",
        help="Output path with embeddings included",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY environment variable")
        sys.exit(1)

    with open(args.input_json) as f:
        scenes = json.load(f)

    print(f"Generating embeddings for {len(scenes)} scenes...")

    client = genai.Client(api_key=api_key)

    for i, scene in enumerate(scenes):
        embedding_text = build_embedding_text(scene)

        if not embedding_text.strip():
            print(f"  Scene {scene.get('scene_number', i+1)}: No text to embed, skipping")
            scene["description_embedding"] = None
            scene["embedding_text"] = ""
            continue

        print(f"  Scene {scene.get('scene_number', i+1)}: "
              f"Embedding {len(embedding_text)} chars...")

        embedding = generate_embedding(client, embedding_text)
        scene["description_embedding"] = embedding
        scene["embedding_text"] = embedding_text

        # Brief pause between calls
        if i < len(scenes) - 1:
            time.sleep(0.5)

    # Save
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(scenes, f, indent=2)

    embedded_count = sum(1 for s in scenes if s.get("description_embedding"))
    print(f"\nDone! {embedded_count}/{len(scenes)} scenes embedded.")
    print(f"Output: {args.output}")
    print(f"\nNext step: python push_scenes.py {args.output} --episode-id 1")


if __name__ == "__main__":
    main()
