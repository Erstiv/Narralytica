"""
Narralytica: Processing router — dispatches pipeline jobs to Plex Mac.

Sends job requests to the Plex processing server (via Tailscale) and
proxies status checks. The Plex server does the heavy lifting (FFmpeg,
Whisper, Gemini, embeddings) and pushes results back to the Hetzner API.

Supports both single-episode and batch (full season) processing.
Also handles direct video file uploads for shows not in Sonarr.
"""
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Episode, Show

router = APIRouter(prefix="/process", tags=["processing"])


def _translate_path_for_processing(backend_path: str) -> str:
    """Translate backend container paths to processing container paths.

    Backend mounts media at /app/media, processing mounts same volume at /data/media.
    Plex Mac paths (/Volumes/...) pass through unchanged.
    """
    if backend_path.startswith("/app/media/"):
        return backend_path.replace("/app/media/", "/data/media/", 1)
    return backend_path


async def _plex_request(method: str, path: str, **kwargs) -> dict:
    """Make a request to the Plex processing server."""
    url = f"{settings.plex_processing_url}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.request(method, url, **kwargs)
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Cannot reach Plex processing server. Is it running? "
                       f"(Tried: {settings.plex_processing_url})"
            )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text[:500])
        return r.json()


@router.get("/health")
async def processing_health():
    """Check if the Plex processing server is reachable."""
    return await _plex_request("GET", "/health")


@router.post("/episode/{episode_id}")
async def start_processing(
    episode_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Start processing a specific episode on the Plex server.

    Looks up the episode's file path and sends a job request to the
    Plex processing server. The Plex server runs the full pipeline
    and pushes results back to this API when done.
    """
    # Look up episode
    result = await db.execute(
        select(Episode, Show)
        .join(Show, Episode.show_id == Show.id)
        .where(Episode.id == episode_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Episode not found")

    episode, show = row

    # Send the file path + show/episode info to the Plex server.
    # If file_path is empty, the Plex server will search for the file.
    # We also pass show_name/season/episode_number as fallback identifiers.
    job = await _plex_request("POST", "/jobs", json={
        "episode_id": episode.id,
        "show_id": show.id,
        "video_path": _translate_path_for_processing(episode.file_path or ""),
        "api_url": settings.api_callback_url,
        "show_name": show.name,
        "season": episode.season,
        "episode_number": episode.episode_number,
    })

    # Update episode status
    episode.status = "processing"
    await db.commit()

    return {
        "episode_id": episode.id,
        "episode_title": episode.title,
        "job_id": job.get("job_id"),
        "message": f"Processing started for S{episode.season:02d}E{episode.episode_number:02d} '{episode.title}'",
    }


@router.get("/jobs")
async def list_processing_jobs():
    """List all processing jobs on the Plex server."""
    return await _plex_request("GET", "/jobs")


@router.get("/jobs/{job_id}")
async def get_processing_job(job_id: str):
    """Check status of a specific processing job."""
    return await _plex_request("GET", f"/jobs/{job_id}")


@router.delete("/jobs/{job_id}")
async def cancel_processing_job(job_id: str):
    """Cancel a processing job on the Plex server."""
    return await _plex_request("DELETE", f"/jobs/{job_id}")


@router.post("/jobs/clear")
async def clear_finished_jobs():
    """Clear completed/failed jobs from the Plex server."""
    return await _plex_request("POST", "/jobs/clear")


# --- Batch Processing ---

class BatchRequest(BaseModel):
    """Optional filters for batch processing."""
    skip_indexed: bool = True  # Skip episodes already indexed


@router.post("/season/{show_id}/{season}")
async def start_season_processing(
    show_id: int,
    season: int,
    body: BatchRequest = BatchRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Queue an entire season for processing.

    Dispatches one job per episode to the Plex processing server.
    Jobs run sequentially (the Plex server has a single-worker queue).
    """
    # Look up show
    show_result = await db.execute(select(Show).where(Show.id == show_id))
    show = show_result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    # Get all episodes for this season
    result = await db.execute(
        select(Episode)
        .where(Episode.show_id == show_id, Episode.season == season)
        .order_by(Episode.episode_number)
    )
    episodes = result.scalars().all()
    if not episodes:
        raise HTTPException(
            status_code=404,
            detail=f"No episodes found for {show.name} Season {season}"
        )

    queued = []
    skipped = []

    for episode in episodes:
        ep_label = f"S{episode.season:02d}E{episode.episode_number:02d}"

        # Skip already-indexed episodes if requested
        if body.skip_indexed and episode.status == "ready":
            skipped.append({"episode_id": episode.id, "label": ep_label, "reason": "already indexed"})
            continue

        # Skip episodes currently processing
        if episode.status == "processing":
            skipped.append({"episode_id": episode.id, "label": ep_label, "reason": "already processing"})
            continue

        try:
            job = await _plex_request("POST", "/jobs", json={
                "episode_id": episode.id,
                "show_id": show.id,
                "video_path": _translate_path_for_processing(episode.file_path or ""),
                "api_url": "http://100.71.72.6:8005",
                "show_name": show.name,
                "season": episode.season,
                "episode_number": episode.episode_number,
            })

            episode.status = "processing"
            queued.append({
                "episode_id": episode.id,
                "label": ep_label,
                "title": episode.title,
                "job_id": job.get("job_id"),
            })
        except HTTPException as e:
            skipped.append({
                "episode_id": episode.id,
                "label": ep_label,
                "reason": f"dispatch failed: {e.detail[:100]}",
            })

    await db.commit()

    return {
        "show": show.name,
        "season": season,
        "queued": len(queued),
        "skipped": len(skipped),
        "jobs": queued,
        "skipped_details": skipped,
        "message": f"Queued {len(queued)} episodes for {show.name} Season {season}",
    }


# --- File Upload ---

UPLOAD_DIR = os.path.join(settings.media_dir, "uploads")


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    show_name: str = Form(...),
    season: int = Form(1),
    episode_number: int = Form(1),
    episode_title: str = Form(""),
    auto_process: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    """Upload a video file directly for processing.

    Creates (or finds) the show and episode records, saves the file to
    the uploads directory, and optionally kicks off processing immediately.
    Used for content not managed by Sonarr/Plex.
    """
    # Validate file type
    allowed = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".ts"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed))}"
        )

    # Find or create show
    result = await db.execute(select(Show).where(Show.name == show_name))
    show = result.scalar_one_or_none()
    if not show:
        show = Show(name=show_name, genres=[], theme_config={})
        db.add(show)
        await db.flush()

    # Find or create episode
    result = await db.execute(
        select(Episode).where(
            Episode.show_id == show.id,
            Episode.season == season,
            Episode.episode_number == episode_number,
        )
    )
    episode = result.scalar_one_or_none()
    if not episode:
        episode = Episode(
            show_id=show.id,
            title=episode_title or f"Episode {episode_number}",
            season=season,
            episode_number=episode_number,
            status="pending",
        )
        db.add(episode)
        await db.flush()

    # Save uploaded file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"s{show.id}_ep{episode.id}_{file.filename}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)

    episode.file_path = save_path
    await db.commit()

    file_size_mb = round(os.path.getsize(save_path) / (1024 * 1024), 1)

    resp = {
        "show_id": show.id,
        "show_name": show.name,
        "episode_id": episode.id,
        "episode_title": episode.title,
        "file_path": save_path,
        "file_size_mb": file_size_mb,
        "message": f"Uploaded {file.filename} ({file_size_mb} MB) → S{season:02d}E{episode_number:02d}",
    }

    # Optionally kick off processing
    if auto_process:
        try:
            job = await _plex_request("POST", "/jobs", json={
                "episode_id": episode.id,
                "show_id": show.id,
                "video_path": _translate_path_for_processing(save_path),
                "api_url": "http://100.71.72.6:8005",
                "show_name": show.name,
                "season": episode.season,
                "episode_number": episode.episode_number,
            })
            episode.status = "processing"
            await db.commit()
            resp["job_id"] = job.get("job_id")
            resp["processing"] = True
        except HTTPException:
            resp["processing"] = False
            resp["processing_error"] = "Failed to dispatch to Plex server"

    return resp
