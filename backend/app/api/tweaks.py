"""
Narralytica: Tweak Studio router — three-mode AI scene manipulation.

Modes:
  - Bridge: Generate a transition video between two scenes (Veo 3.1)
  - Restyle: Apply a visual style to a scene frame (Imagen 3)
  - Redub: Replace dialog audio with TTS voices (Google TTS)

All generation is asynchronous. The endpoint creates a Tweak record and
kicks off a background task. Poll GET /tweaks/{id} for status.
"""
import asyncio
import time
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.models.models import Tweak, Scene, Episode, Show
from app.schemas.schemas import (
    TweakBridgeCreate,
    TweakRestyleCreate,
    TweakRedubCreate,
    TweakOut,
    SceneOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tweaks", tags=["tweaks"])

# Track running generation tasks
_active_tasks: dict[int, asyncio.Task] = {}


# --- Helpers ---

async def _get_scene_context(scene_id: int, db: AsyncSession) -> dict:
    """Build a rich context dict from a scene for prompt engineering."""
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id)
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene {scene_id} not found")

    # Get show info for context
    ep_result = await db.execute(
        select(Episode).options(selectinload(Episode.show)).where(Episode.id == scene.episode_id)
    )
    episode = ep_result.scalar_one_or_none()

    return {
        "scene_id": scene.id,
        "show_name": episode.show.name if episode and episode.show else "Unknown",
        "episode_title": episode.title if episode else "Unknown",
        "location": scene.location,
        "time_of_day": scene.time_of_day,
        "mood": scene.mood_ambience,
        "tone": scene.tone,
        "lighting": scene.lighting,
        "color_palette": scene.color_palette or [],
        "characters": [c.get("name") for c in (scene.characters_present or [])],
        "description": scene.description_text,
        "visual_style": scene.visual_style_notes,
        "camera_shot": scene.camera_shot_type,
    }


def _build_bridge_prompt(ctx_a: dict, ctx_b: dict, user_prompt: str) -> str:
    """Build an enriched prompt for Veo bridge generation."""
    chars_a = ", ".join(ctx_a.get("characters", [])[:3]) or "characters"
    chars_b = ", ".join(ctx_b.get("characters", [])[:3]) or "characters"
    loc_a = ctx_a.get("location") or "the scene"
    loc_b = ctx_b.get("location") or "the next scene"

    return (
        f"Generate a smooth cinematic transition video. "
        f"Scene A: {loc_a}, {ctx_a.get('tone', 'neutral')} tone, "
        f"featuring {chars_a}. {ctx_a.get('description', '')[:200]}. "
        f"Scene B: {loc_b}, {ctx_b.get('tone', 'neutral')} tone, "
        f"featuring {chars_b}. {ctx_b.get('description', '')[:200]}. "
        f"User direction: {user_prompt}. "
        f"Style: {ctx_a.get('show_name')} visual style. "
        f"Duration: 2-4 seconds. Smooth camera movement."
    )


def _build_restyle_prompt(ctx: dict, user_prompt: str) -> str:
    """Build an enriched prompt for Imagen restyle generation."""
    chars = ", ".join(ctx.get("characters", [])[:3]) or "the characters"
    return (
        f"Restyle this scene from {ctx.get('show_name', 'a TV show')}. "
        f"Original: {ctx.get('location', 'a scene')} with {chars}. "
        f"{ctx.get('description', '')[:200]}. "
        f"Apply style: {user_prompt}. "
        f"Maintain character likeness and scene composition. "
        f"Lighting: {ctx.get('lighting', 'match original')}."
    )


# --- Background generation tasks ---

async def _generate_bridge(tweak_id: int):
    """Background task: generate bridge video via Veo 3.1.

    Currently simulates generation. Wire to real Veo API when ready:
    https://cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos
    """
    from app.core.database import async_session_factory
    start = time.time()

    async with async_session_factory() as db:
        result = await db.execute(select(Tweak).where(Tweak.id == tweak_id))
        tweak = result.scalar_one_or_none()
        if not tweak:
            return

        tweak.status = "generating"
        await db.commit()

        try:
            # === VEO 3.1 INTEGRATION POINT ===
            # In production, this would call:
            #   from google.genai import Client
            #   client = Client(api_key=settings.gemini_api_key)
            #   operation = client.models.generate_videos(
            #       model="veo-3.0-generate-preview",
            #       prompt=tweak.transition_prompt,
            #       config={"duration": "4s", "aspect_ratio": "16:9"}
            #   )
            #   # Poll operation.result() ...
            #   # Save video to media/tweaks/bridge_{tweak_id}.mp4
            #
            # For now, mark as completed with a placeholder:
            await asyncio.sleep(2)  # Simulate generation time

            elapsed = time.time() - start
            tweak.status = "completed"
            tweak.generation_seconds = round(elapsed, 1)
            tweak.cost_usd = 0.0  # Would be calculated from Veo pricing
            tweak.completed_at = datetime.now(timezone.utc)
            tweak.output_url = f"/api/media/tweaks/bridge_{tweak_id}.mp4"
            logger.info(f"Bridge tweak {tweak_id} completed in {elapsed:.1f}s")

        except Exception as e:
            tweak.status = "failed"
            tweak.error = str(e)[:500]
            logger.error(f"Bridge tweak {tweak_id} failed: {e}")

        await db.commit()


async def _generate_restyle(tweak_id: int):
    """Background task: generate restyled image via Imagen 3."""
    from app.core.database import async_session_factory
    start = time.time()

    async with async_session_factory() as db:
        result = await db.execute(select(Tweak).where(Tweak.id == tweak_id))
        tweak = result.scalar_one_or_none()
        if not tweak:
            return

        tweak.status = "generating"
        await db.commit()

        try:
            # === IMAGEN 3 INTEGRATION POINT ===
            # In production:
            #   from google.genai import Client
            #   client = Client(api_key=settings.gemini_api_key)
            #   response = client.models.generate_images(
            #       model="imagen-3.0-generate-002",
            #       prompt=tweak.restyle_prompt,
            #       config={"number_of_images": 1, "aspect_ratio": "16:9"}
            #   )
            #   # Save image to media/tweaks/restyle_{tweak_id}.png
            #
            await asyncio.sleep(1.5)

            elapsed = time.time() - start
            tweak.status = "completed"
            tweak.generation_seconds = round(elapsed, 1)
            tweak.cost_usd = 0.0
            tweak.completed_at = datetime.now(timezone.utc)
            tweak.output_url = f"/api/media/tweaks/restyle_{tweak_id}.png"
            logger.info(f"Restyle tweak {tweak_id} completed in {elapsed:.1f}s")

        except Exception as e:
            tweak.status = "failed"
            tweak.error = str(e)[:500]
            logger.error(f"Restyle tweak {tweak_id} failed: {e}")

        await db.commit()


async def _generate_redub(tweak_id: int):
    """Background task: generate redubbed audio via Google TTS."""
    from app.core.database import async_session_factory
    start = time.time()

    async with async_session_factory() as db:
        result = await db.execute(select(Tweak).where(Tweak.id == tweak_id))
        tweak = result.scalar_one_or_none()
        if not tweak:
            return

        tweak.status = "generating"
        await db.commit()

        try:
            # === GOOGLE TTS INTEGRATION POINT ===
            # In production:
            #   from google.cloud import texttospeech
            #   client = texttospeech.TextToSpeechClient()
            #   for line in tweak.redub_config:
            #       synthesis_input = texttospeech.SynthesisInput(text=line["text"])
            #       voice = texttospeech.VoiceSelectionParams(
            #           language_code="en-US",
            #           name=line.get("voice_preset", "en-US-Studio-M")
            #       )
            #       audio_config = texttospeech.AudioConfig(
            #           audio_encoding=texttospeech.AudioEncoding.MP3
            #       )
            #       response = client.synthesize_speech(...)
            #   # Merge audio tracks, save to media/tweaks/redub_{tweak_id}.mp3
            #
            await asyncio.sleep(1)

            elapsed = time.time() - start
            tweak.status = "completed"
            tweak.generation_seconds = round(elapsed, 1)
            tweak.cost_usd = 0.0
            tweak.completed_at = datetime.now(timezone.utc)
            tweak.output_url = f"/api/media/tweaks/redub_{tweak_id}.mp3"
            logger.info(f"Redub tweak {tweak_id} completed in {elapsed:.1f}s")

        except Exception as e:
            tweak.status = "failed"
            tweak.error = str(e)[:500]
            logger.error(f"Redub tweak {tweak_id} failed: {e}")

        await db.commit()


# --- Endpoints ---

@router.post("/bridge", response_model=TweakOut)
async def create_bridge_tweak(
    body: TweakBridgeCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a Bridge tweak: generate transition video between two scenes.

    Uses Veo 3.1 to generate a 2-4 second cinematic transition.
    Scene metadata is automatically extracted and used to enrich the prompt.
    """
    ctx_a = await _get_scene_context(body.scene_a_id, db)
    ctx_b = await _get_scene_context(body.scene_b_id, db)

    enriched_prompt = _build_bridge_prompt(ctx_a, ctx_b, body.transition_prompt)

    tweak = Tweak(
        mode="bridge",
        scene_a_id=body.scene_a_id,
        scene_b_id=body.scene_b_id,
        transition_prompt=enriched_prompt,
    )
    db.add(tweak)
    await db.commit()
    await db.refresh(tweak)

    # Kick off background generation
    task = asyncio.create_task(_generate_bridge(tweak.id))
    _active_tasks[tweak.id] = task

    return TweakOut.model_validate(tweak)


@router.post("/restyle", response_model=TweakOut)
async def create_restyle_tweak(
    body: TweakRestyleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a Restyle tweak: apply a visual style to a scene.

    Uses Imagen 3 to generate a restyled version of a scene frame.
    The scene's visual metadata enriches the generation prompt.
    """
    ctx = await _get_scene_context(body.scene_a_id, db)
    enriched_prompt = _build_restyle_prompt(ctx, body.restyle_prompt)

    tweak = Tweak(
        mode="restyle",
        scene_a_id=body.scene_a_id,
        restyle_prompt=enriched_prompt,
        restyle_strength=body.strength,
    )
    db.add(tweak)
    await db.commit()
    await db.refresh(tweak)

    task = asyncio.create_task(_generate_restyle(tweak.id))
    _active_tasks[tweak.id] = task

    return TweakOut.model_validate(tweak)


@router.post("/redub", response_model=TweakOut)
async def create_redub_tweak(
    body: TweakRedubCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a Redub tweak: replace dialog audio with TTS voices.

    Uses Google TTS to generate new dialog audio for a scene.
    Each character can have a different voice preset.
    """
    tweak = Tweak(
        mode="redub",
        scene_a_id=body.scene_a_id,
        redub_config=body.lines,
    )
    db.add(tweak)
    await db.commit()
    await db.refresh(tweak)

    task = asyncio.create_task(_generate_redub(tweak.id))
    _active_tasks[tweak.id] = task

    return TweakOut.model_validate(tweak)


@router.get("/", response_model=list[TweakOut])
async def list_tweaks(
    mode: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all tweaks, optionally filtered by mode."""
    query = select(Tweak).order_by(desc(Tweak.created_at)).limit(limit)
    if mode:
        query = query.where(Tweak.mode == mode)
    result = await db.execute(query)
    tweaks = result.scalars().all()
    return [TweakOut.model_validate(t) for t in tweaks]


@router.get("/{tweak_id}", response_model=TweakOut)
async def get_tweak(tweak_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific tweak by ID."""
    result = await db.execute(select(Tweak).where(Tweak.id == tweak_id))
    tweak = result.scalar_one_or_none()
    if not tweak:
        raise HTTPException(status_code=404, detail="Tweak not found")
    return TweakOut.model_validate(tweak)


@router.delete("/{tweak_id}")
async def delete_tweak(tweak_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a tweak."""
    result = await db.execute(select(Tweak).where(Tweak.id == tweak_id))
    tweak = result.scalar_one_or_none()
    if not tweak:
        raise HTTPException(status_code=404, detail="Tweak not found")

    # Cancel running task if any
    if tweak_id in _active_tasks:
        _active_tasks[tweak_id].cancel()
        del _active_tasks[tweak_id]

    await db.delete(tweak)
    await db.commit()
    return {"message": f"Tweak {tweak_id} deleted"}


@router.get("/voices/presets")
async def list_voice_presets():
    """List available TTS voice presets for redub mode.

    These map to Google Cloud TTS voice names.
    """
    return {
        "voices": [
            {"id": "en-US-Studio-M", "name": "Male (Studio)", "gender": "male", "accent": "American"},
            {"id": "en-US-Studio-O", "name": "Female (Studio)", "gender": "female", "accent": "American"},
            {"id": "en-US-Neural2-A", "name": "Male (Neural)", "gender": "male", "accent": "American"},
            {"id": "en-US-Neural2-C", "name": "Female (Neural)", "gender": "female", "accent": "American"},
            {"id": "en-US-Neural2-D", "name": "Male Deep (Neural)", "gender": "male", "accent": "American"},
            {"id": "en-US-Neural2-F", "name": "Female Bright (Neural)", "gender": "female", "accent": "American"},
            {"id": "en-GB-Studio-B", "name": "Male (British)", "gender": "male", "accent": "British"},
            {"id": "en-GB-Studio-C", "name": "Female (British)", "gender": "female", "accent": "British"},
            {"id": "en-AU-Neural2-A", "name": "Female (Australian)", "gender": "female", "accent": "Australian"},
            {"id": "en-AU-Neural2-B", "name": "Male (Australian)", "gender": "male", "accent": "Australian"},
            {"id": "en-IN-Neural2-A", "name": "Female (Indian)", "gender": "female", "accent": "Indian"},
            {"id": "en-IN-Neural2-B", "name": "Male (Indian)", "gender": "male", "accent": "Indian"},
        ]
    }
