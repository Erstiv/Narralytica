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

    # Let the Plex processing server find the file itself using
    # show name + season + episode number. It searches both
    # /Volumes/Chaos/ and /Volumes/Luchagaido/ automatically.
    job = await _plex_request("POST", "/jobs", json={
        "episode_id": episode.id,
        "show_id": show.id,
        "video_path": "",  # Let Plex server resolve from filesystem
        "api_url": "http://100.71.72.6:8005",  # Hetzner's Tailscale IP
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
