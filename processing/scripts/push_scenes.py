#!/usr/bin/env python3
"""
Narralytica: Push Scenes to Server (Run on M5 Mac)

After Gemini indexing + embedding generation, push the final scene JSON
(with embeddings) to the Narralytica API on Hetzner.

Usage:
    python push_scenes.py processing/output/scenes_final.json --episode-id 1

What it does:
    1. Reads the scene JSON file (from generate_embeddings.py)
    2. Sends it to the Narralytica API on your Hetzner server
    3. The API stores scenes + 768-dim vector embeddings in PostgreSQL
"""
import json
import sys
import argparse
import urllib.request


def push_scenes(json_path: str, episode_id: int, api_url: str) -> None:
    with open(json_path) as f:
        scenes = json.load(f)

    embedded = sum(1 for s in scenes if s.get("description_embedding"))
    print(f"Pushing {len(scenes)} scenes ({embedded} with embeddings) to server...")
    print(f"  Endpoint: {api_url}/api/scenes/episode/{episode_id}/bulk")

    payload = json.dumps({"scenes": scenes}).encode("utf-8")
    payload_mb = len(payload) / (1024 * 1024)
    print(f"  Payload size: {payload_mb:.1f} MB")

    req = urllib.request.Request(
        f"{api_url}/api/scenes/episode/{episode_id}/bulk",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            print(f"Success! Created {result.get('created', '?')} scenes.")
            if result.get("replaced_existing"):
                print("  (Replaced any existing scenes for this episode)")
    except urllib.error.HTTPError as e:
        print(f"API error {e.code}: {e.read().decode()}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}")
        print("Is the Narralytica backend running on the server?")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push Gemini scene data to Narralytica API")
    parser.add_argument("json_path", help="Path to scenes_final.json (with embeddings)")
    parser.add_argument("--episode-id", type=int, default=1, help="Episode ID in the database")
    parser.add_argument("--api-url", default="https://captainofindustries.com",
                        help="Narralytica API URL")
    args = parser.parse_args()

    push_scenes(args.json_path, args.episode_id, args.api_url)
