#!/usr/bin/env python3
"""Sync episode file_path from Sonarr into Narralytica DB.

After Sonarr re-downloads/imports files, the filenames may differ from
what's stored in the Narralytica episodes table. This script queries
Sonarr for the actual file paths and updates the DB accordingly.

Usage:
    python3 scripts/sync_file_paths.py [--show-id SHOW_ID]

Requires: SONARR_API_KEY, DATABASE_URL environment variables
(or reads from .env on Hetzner).
"""

import os
import sys
import json
import urllib.request
import urllib.error
import psycopg2

# Config — adjust if running outside Docker
SONARR_URL = os.environ.get("SONARR_URL", "http://localhost:8989")
SONARR_API_KEY = os.environ.get("SONARR_API_KEY", "e068e976a5704fd0a74a4abc7bbb393c")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://narralytica:017c23c0ab7c64f144057c85d09a2efe@localhost:5433/narralytica")

# Path mapping: Sonarr sees /data/media/tv/, Docker container sees /data/tv/
SONARR_PREFIX = "/data/media/tv/"
CONTAINER_PREFIX = "/data/tv/"


def sonarr_get(endpoint):
    url = f"{SONARR_URL}/api/v3/{endpoint}"
    req = urllib.request.Request(url, headers={"X-Api-Key": SONARR_API_KEY})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    show_id_filter = None
    if "--show-id" in sys.argv:
        idx = sys.argv.index("--show-id")
        show_id_filter = int(sys.argv[idx + 1])

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Get shows with sonarr_id
    if show_id_filter:
        cur.execute("SELECT id, name, sonarr_id FROM shows WHERE id = %s AND sonarr_id IS NOT NULL", (show_id_filter,))
    else:
        cur.execute("SELECT id, name, sonarr_id FROM shows WHERE sonarr_id IS NOT NULL")

    shows = cur.fetchall()
    total_updated = 0

    for show_id, show_name, sonarr_id in shows:
        print(f"\n--- {show_name} (show_id={show_id}, sonarr_id={sonarr_id}) ---")

        # Get episode files from Sonarr
        try:
            ep_files = sonarr_get(f"episodefile?seriesId={sonarr_id}")
        except urllib.error.HTTPError as e:
            print(f"  Sonarr API error: {e}")
            continue

        if not ep_files:
            print("  No files in Sonarr")
            continue

        # Build map: sonarr_episode_id -> file_path
        # Each file can cover multiple episodes (multi-episode files)
        sonarr_episodes = sonarr_get(f"episode?seriesId={sonarr_id}")
        ep_id_to_file = {}
        for ep in sonarr_episodes:
            if ep.get("hasFile") and ep.get("episodeFileId"):
                file_id = ep["episodeFileId"]
                for f in ep_files:
                    if f["id"] == file_id:
                        ep_id_to_file[ep["id"]] = f["path"]
                        break

        # Get narralytica episodes for this show
        cur.execute(
            "SELECT id, sonarr_episode_id, file_path FROM episodes WHERE show_id = %s AND sonarr_episode_id IS NOT NULL",
            (show_id,)
        )
        episodes = cur.fetchall()

        for ep_id, sonarr_ep_id, old_path in episodes:
            sonarr_path = ep_id_to_file.get(sonarr_ep_id)
            if not sonarr_path:
                print(f"  Episode {ep_id} (sonarr_ep={sonarr_ep_id}): no file in Sonarr")
                continue

            # Convert Sonarr path to container path
            if sonarr_path.startswith(SONARR_PREFIX):
                new_path = CONTAINER_PREFIX + sonarr_path[len(SONARR_PREFIX):]
            else:
                new_path = sonarr_path

            if new_path != old_path:
                print(f"  Episode {ep_id}: UPDATE")
                print(f"    old: {old_path}")
                print(f"    new: {new_path}")
                cur.execute("UPDATE episodes SET file_path = %s WHERE id = %s", (new_path, ep_id))
                total_updated += 1
            else:
                print(f"  Episode {ep_id}: path unchanged")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n=== Done. Updated {total_updated} episode paths. ===")


if __name__ == "__main__":
    main()
