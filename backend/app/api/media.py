"""Narralytica: Media streaming — serve scene clips on-demand via FFmpeg."""
import asyncio
import os
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Scene, Episode

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["media"])


@router.get("/clip/{scene_id}")
async def stream_scene_clip(scene_id: int, db: AsyncSession = Depends(get_db)):
    """Stream a scene clip from the source video using FFmpeg seek.

    Extracts the scene's time range from the episode's source file
    and streams it as MP4 without writing to disk.
    """
    # Look up scene + episode
    result = await db.execute(
        select(Scene, Episode)
        .join(Episode, Scene.episode_id == Episode.id)
        .where(Scene.id == scene_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Scene not found")

    scene, episode = row
    file_path = episode.file_path
    if not file_path:
        raise HTTPException(404, "Episode has no file path")

    # Check if file exists (inside container)
    if not os.path.exists(file_path):
        raise HTTPException(404, f"Media file not found: {file_path}")

    start = scene.start_timestamp
    duration = scene.duration

    # Extract clip to a temp file first (enables seeking in the player)
    import tempfile
    clip_dir = "/tmp/narralytica_clips"
    os.makedirs(clip_dir, exist_ok=True)
    clip_path = os.path.join(clip_dir, f"scene_{scene_id}.mp4")

    # Only re-extract if not cached
    if not os.path.exists(clip_path):
        cmd = [
            "ffmpeg",
            "-ss", str(start),
            "-i", file_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-y",
            clip_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

        if process.returncode != 0 or not os.path.exists(clip_path):
            raise HTTPException(500, "Failed to extract clip")

    from starlette.responses import FileResponse
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        filename=f"scene_{scene_id}.mp4",
        headers={"Cache-Control": "public, max-age=3600"},
    )
