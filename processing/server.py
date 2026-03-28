#!/usr/bin/env python3
"""
Narralytica: Plex Processing Server

A lightweight FastAPI service that runs on the Plex Mac and accepts
processing job requests from the Hetzner backend via Tailscale.

Endpoints:
    GET  /health              — Health check
    POST /jobs                — Start a new processing job
    GET  /jobs/{job_id}       — Check job status
    GET  /jobs                — List recent jobs

The server runs the full pipeline (compress, detect, transcribe, index,
merge, embed, push) and reports progress back to the Hetzner backend.

Usage:
    export GEMINI_API_KEY=your_key
    python server.py

    # Or with uvicorn directly:
    uvicorn processing.server:app --host 0.0.0.0 --port 8006
"""
import os
import sys
import time
import uuid
import json
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Narralytica Processing Server",
    description="Plex Mac pipeline runner — accepts jobs from Hetzner",
    version="0.1.0",
)

# --- Job tracking ---

jobs: dict[str, dict] = {}


class JobRequest(BaseModel):
    """Request to process an episode."""
    episode_id: int
    show_id: int = 0             # Show ID for CutPrint profile lookup
    video_path: str = ""         # Absolute path on Plex Mac filesystem (optional if show/season/ep provided)
    api_url: str = "http://178.156.251.26:8005"  # Hetzner API URL
    show_name: str = ""
    season: int = 0
    episode_number: int = 0


# Media search paths on Plex Mac (ordered by preference)
PLEX_TV_PATHS = [
    "/Volumes/Luchagaido/TV Shows",
    "/Volumes/Chaos/TV Shows",
]


def find_episode_file(show_name: str, season: int, episode_number: int) -> str | None:
    """Search Plex Mac filesystem for an episode file.

    Looks through all configured TV paths for files matching the show,
    season, and episode number. Handles various naming conventions.
    """
    import glob
    import re

    for base in PLEX_TV_PATHS:
        show_dir = Path(base) / show_name
        if not show_dir.exists():
            continue

        # Check season directories
        for season_dir_name in [f"Season {season:02d}", f"Season {season}"]:
            season_dir = show_dir / season_dir_name
            if not season_dir.exists():
                continue

            # Search for files matching this episode number
            for f in season_dir.iterdir():
                if f.is_file() and f.suffix.lower() in ('.mkv', '.mp4', '.avi', '.ogm', '.ts', '.m4v'):
                    name = f.name.lower()
                    # Match patterns: S04E17, 04x17, s4e17, etc.
                    patterns = [
                        rf's0*{season}e0*{episode_number}\b',
                        rf'0*{season}x0*{episode_number}\b',
                        rf'[- .]0*{episode_number}[- .]',
                    ]
                    for pattern in patterns:
                        if re.search(pattern, name, re.IGNORECASE):
                            return str(f)

    return None


class JobStatus(BaseModel):
    job_id: str
    status: str                  # queued, running, completed, failed
    episode_id: int
    video_path: str
    current_step: str
    progress_pct: int
    started_at: str | None
    completed_at: str | None
    error: str | None
    elapsed_seconds: float | None


# --- Pipeline runner ---

PIPELINE_STEPS = [
    ("compress", "Compressing video (720p, 1fps)", 15),
    ("detect", "Detecting scene boundaries", 5),
    ("whisper", "Transcribing audio (Whisper)", 25),
    ("gemini", "Analyzing video (Gemini)", 25),
    ("merge", "Merging transcripts", 5),
    ("embed", "Generating embeddings", 10),
    ("media", "Extracting thumbnails & clips", 10),
    ("push", "Pushing to Hetzner", 5),
]


def run_pipeline(job_id: str, request: JobRequest):
    """Run the full processing pipeline in a background thread."""
    job = jobs[job_id]
    job["status"] = "running"
    job["started_at"] = datetime.now().isoformat()
    start_time = time.time()

    scripts_dir = Path(__file__).parent / "scripts"
    work_dir = Path(__file__).parent / "work" / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    # Output paths
    compressed = work_dir / "compressed.mp4"
    scenes_json = work_dir / "scenes.json"
    whisper_json = work_dir / "whisper_transcript.json"
    gemini_json = work_dir / "scenes_gemini.json"
    merged_json = work_dir / "scenes_merged.json"
    final_json = work_dir / "scenes_final.json"
    media_dir = work_dir / "media"

    env = os.environ.copy()
    python = sys.executable

    try:
        # Step 1: Compress (positional args: input output)
        job["current_step"] = "compress"
        job["progress_pct"] = 0
        result = subprocess.run(
            [python, str(scripts_dir / "compress.py"),
             request.video_path, str(compressed)],
            capture_output=True, text=True, env=env
        )
        if result.returncode != 0:
            raise RuntimeError(f"Compress failed: {result.stderr[:500]}")

        # Step 2: Detect scenes with CutPrint™ profile
        job["current_step"] = "detect"
        job["progress_pct"] = 15
        detect_cmd = [
            python, str(scripts_dir / "detect_scenes.py"),
            str(compressed), str(scenes_json),
        ]
        # Fetch CutPrint profile from Hetzner API if show_id provided
        if request.show_id:
            try:
                import httpx
                r = httpx.get(f"{request.api_url}/api/library/shows/{request.show_id}/cutprint", timeout=10.0)
                if r.status_code == 200:
                    profile_path = work_dir / "cutprint_profile.json"
                    profile_path.write_text(json.dumps(r.json(), indent=2))
                    detect_cmd.extend(["--profile", str(profile_path)])
                    job["cutprint"] = "loaded"
                else:
                    job["cutprint"] = "not_found (using defaults)"
            except Exception as e:
                job["cutprint"] = f"fetch_error: {e}"

        result = subprocess.run(detect_cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            raise RuntimeError(f"Scene detection failed: {result.stderr[:500]}")

        # Steps 3+4: Whisper + Gemini in parallel
        job["current_step"] = "whisper+gemini"
        job["progress_pct"] = 20

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def run_whisper():
            return subprocess.run(
                [python, str(scripts_dir / "whisper_transcribe.py"),
                 request.video_path,
                 "--output", str(whisper_json)],
                capture_output=True, text=True, env=env
            )

        def run_gemini():
            return subprocess.run(
                [python, str(scripts_dir / "gemini_index.py"),
                 str(compressed), str(scenes_json),
                 "--output", str(gemini_json)],
                capture_output=True, text=True, env=env
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            whisper_future = pool.submit(run_whisper)
            gemini_future = pool.submit(run_gemini)

            for future in as_completed([whisper_future, gemini_future]):
                r = future.result()
                if r.returncode != 0:
                    name = "Whisper" if future == whisper_future else "Gemini"
                    raise RuntimeError(f"{name} failed: {r.stderr[:500]}")

        # Step 5: Merge
        job["current_step"] = "merge"
        job["progress_pct"] = 70
        result = subprocess.run(
            [python, str(scripts_dir / "merge_transcript.py"),
             str(whisper_json), str(gemini_json),
             "--output", str(merged_json)],
            capture_output=True, text=True, env=env
        )
        if result.returncode != 0:
            raise RuntimeError(f"Merge failed: {result.stderr[:500]}")

        # Step 6: Embeddings
        job["current_step"] = "embed"
        job["progress_pct"] = 75
        result = subprocess.run(
            [python, str(scripts_dir / "generate_embeddings.py"),
             str(merged_json), "--output", str(final_json)],
            capture_output=True, text=True, env=env
        )
        if result.returncode != 0:
            raise RuntimeError(f"Embeddings failed: {result.stderr[:500]}")

        # Step 7: Extract media (thumbnails + clips)
        job["current_step"] = "media"
        job["progress_pct"] = 85
        result = subprocess.run(
            [python, str(scripts_dir / "extract_media.py"),
             request.video_path, str(scenes_json),
             "--output-dir", str(media_dir)],
            capture_output=True, text=True, env=env
        )
        if result.returncode != 0:
            raise RuntimeError(f"Media extraction failed: {result.stderr[:500]}")

        # Step 8: Push to Hetzner
        job["current_step"] = "push"
        job["progress_pct"] = 95
        result = subprocess.run(
            [python, str(scripts_dir / "push_scenes.py"),
             str(final_json),
             "--episode-id", str(request.episode_id),
             "--api-url", request.api_url],
            capture_output=True, text=True, env=env
        )
        if result.returncode != 0:
            raise RuntimeError(f"Push failed: {result.stderr[:500]}")

        # Done!
        job["status"] = "completed"
        job["current_step"] = "done"
        job["progress_pct"] = 100
        job["completed_at"] = datetime.now().isoformat()
        job["elapsed_seconds"] = time.time() - start_time

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["completed_at"] = datetime.now().isoformat()
        job["elapsed_seconds"] = time.time() - start_time


# --- API endpoints ---

@app.get("/health")
async def health():
    """Health check with system info."""
    import shutil
    return {
        "status": "ok",
        "service": "narralytica-processing",
        "python": sys.version.split()[0],
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "gemini_key_set": bool(os.environ.get("GEMINI_API_KEY")),
        "active_jobs": sum(1 for j in jobs.values() if j["status"] == "running"),
    }


@app.post("/jobs")
async def create_job(request: JobRequest):
    """Start a new processing job."""
    # If no explicit path, search for the file by show/season/episode
    if not request.video_path and request.show_name and request.season and request.episode_number:
        found = find_episode_file(request.show_name, request.season, request.episode_number)
        if found:
            request.video_path = found
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Could not find {request.show_name} S{request.season:02d}E{request.episode_number:02d} "
                       f"on disk. Searched: {', '.join(PLEX_TV_PATHS)}"
            )

    # Validate video path exists
    if not request.video_path or not Path(request.video_path).exists():
        raise HTTPException(
            status_code=400,
            detail=f"Video file not found: {request.video_path}"
        )

    # Check not already processing this episode
    for j in jobs.values():
        if j["episode_id"] == request.episode_id and j["status"] == "running":
            raise HTTPException(
                status_code=409,
                detail=f"Episode {request.episode_id} is already being processed (job {j['job_id']})"
            )

    # Create job
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "episode_id": request.episode_id,
        "show_id": request.show_id,
        "video_path": request.video_path,
        "current_step": "queued",
        "progress_pct": 0,
        "started_at": None,
        "completed_at": None,
        "error": None,
        "elapsed_seconds": None,
    }

    # Run pipeline in background thread
    thread = threading.Thread(
        target=run_pipeline,
        args=(job_id, request),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "queued", "message": "Pipeline started"}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Check status of a processing job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/jobs")
async def list_jobs():
    """List all processing jobs."""
    return {
        "jobs": list(jobs.values()),
        "total": len(jobs),
        "active": sum(1 for j in jobs.values() if j["status"] == "running"),
    }


if __name__ == "__main__":
    import uvicorn
    print("Starting Narralytica Processing Server on port 8006...")
    print(f"GEMINI_API_KEY: {'set' if os.environ.get('GEMINI_API_KEY') else 'NOT SET'}")
    uvicorn.run(app, host="0.0.0.0", port=8006)
