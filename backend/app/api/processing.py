"""
Narralytica: Processing router — dispatches pipeline jobs to Plex Mac.

Sends job requests to the Plex processing server (via Tailscale) and
proxies status checks. The Plex server does the heavy lifting (FFmpeg,
Whisper, Gemini, embeddings) and pushes results back to the Hetzner API.
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Episode, Show

router = APIRouter(prefix="/process", tags=["processing"])


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

    if not episode.file_path:
        raise HTTPException(
            status_code=400,
            detail="Episode has no file path. Import from Sonarr first or set the path manually."
        )

    # The file_path from Sonarr is relative to the Hetzner download dir
    # (/data/media/tv/...). On the Plex Mac, the same content is at
    # /Volumes/Chaos/TV Shows/... or /Volumes/Luchagaido/TV Shows/...
    # We need to translate the path.
    video_path = episode.file_path
    if video_path.startswith("/data/media/tv/"):
        # Try both Plex Mac mount points
        relative = video_path[len("/data/media/tv/"):]
        # Luchagaido gets new content, Chaos has legacy
        video_path = f"/Volumes/Luchagaido/TV Shows/{relative}"
        # TODO: Add fallback to /Volumes/Chaos/TV Shows/ if not found

    # Send job to Plex processing server
    job = await _plex_request("POST", "/jobs", json={
        "episode_id": episode.id,
        "video_path": video_path,
        "api_url": f"http://100.71.72.6:8005",  # Hetzner's Tailscale IP
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
        "video_path": video_path,
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
