from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Scene, SceneObject
from app.schemas.schemas import SceneOut, SceneBulkCreate

router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.get("/episode/{episode_id}", response_model=list[SceneOut])
async def list_scenes(episode_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Scene).where(Scene.episode_id == episode_id).order_by(Scene.start_timestamp)
    )
    return result.scalars().all()


@router.get("/{scene_id}", response_model=SceneOut)
async def get_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.post("/episode/{episode_id}/bulk", response_model=dict)
async def bulk_create_scenes(
    episode_id: int, body: SceneBulkCreate, db: AsyncSession = Depends(get_db)
):
    """Ingest Gemini-generated scene data (with optional embeddings) for an episode."""
    # Clear existing scenes for this episode (re-indexing)
    existing = await db.execute(
        select(Scene).where(Scene.episode_id == episode_id)
    )
    for old_scene in existing.scalars().all():
        await db.delete(old_scene)

    created = 0
    for scene_data in body.scenes:
        # Extract embedding if present (768-dim float list from generate_embeddings.py)
        embedding = scene_data.get("description_embedding")

        scene = Scene(
            episode_id=episode_id,
            start_timestamp=scene_data["start_timestamp"],
            end_timestamp=scene_data["end_timestamp"],
            duration=scene_data.get("duration", scene_data["end_timestamp"] - scene_data["start_timestamp"]),
            # Characters & Dialog
            characters_present=scene_data.get("characters_present", []),
            key_dialog=scene_data.get("key_dialog", []),
            character_interactions=scene_data.get("character_interactions", []),
            character_motivations_feelings=scene_data.get("character_motivations_feelings"),
            # Actions & Humor
            actions=scene_data.get("actions"),
            interactions=scene_data.get("interactions"),
            visual_gags=scene_data.get("visual_gags"),
            dialog_based_humor=scene_data.get("dialog_based_humor"),
            # Location & Setting
            location=scene_data.get("location"),
            time_of_day=scene_data.get("time_of_day"),
            setting_type=scene_data.get("setting_type"),
            background=scene_data.get("background"),
            # Visual & Cinematographic
            color_palette=scene_data.get("color_palette", []),
            lighting=scene_data.get("lighting"),
            camera_shot_type=scene_data.get("camera_shot_type"),
            camera_movement=scene_data.get("camera_movement"),
            scene_composition=scene_data.get("scene_composition"),
            visual_style_notes=scene_data.get("visual_style_notes"),
            # Audio & Music
            music_present=scene_data.get("music_present"),
            music_description=scene_data.get("music_description"),
            sound_effects=scene_data.get("sound_effects"),
            ambient_audio=scene_data.get("ambient_audio"),
            # Mood & Tone
            mood_ambience=scene_data.get("mood_ambience"),
            scene_pacing=scene_data.get("scene_pacing"),
            tone=scene_data.get("tone"),
            emotional_arc=scene_data.get("emotional_arc"),
            # Narrative & Context
            tropes_memes=scene_data.get("tropes_memes", []),
            cultural_references=scene_data.get("cultural_references", []),
            recurring_gags=scene_data.get("recurring_gags"),
            plot_significance=scene_data.get("plot_significance"),
            continuity_notes=scene_data.get("continuity_notes"),
            # Explicitness (5 dimensions)
            explicitness=scene_data.get("explicitness", "none"),
            explicitness_language=scene_data.get("explicitness_language", 0),
            explicitness_violence=scene_data.get("explicitness_violence", 0),
            explicitness_sexual=scene_data.get("explicitness_sexual", 0),
            explicitness_substance=scene_data.get("explicitness_substance", 0),
            explicitness_thematic=scene_data.get("explicitness_thematic", 0),
            # Scene Structure
            scene_transitions=scene_data.get("scene_transitions"),
            text_on_screen=scene_data.get("text_on_screen"),
            # Search & Meta
            overall_confidence=scene_data.get("overall_scene_confidence", 0),
            description_text=scene_data.get("description_text"),
            description_embedding=embedding,
            merged_transcript=scene_data.get("merged_transcript", []),
            raw_gemini_json=scene_data,
        )
        db.add(scene)
        await db.flush()  # Get scene.id for objects

        # Create scene_objects from objects_present
        for obj in scene_data.get("objects_present", []):
            if isinstance(obj, dict):
                db.add(SceneObject(
                    scene_id=scene.id,
                    name=obj.get("name", ""),
                    category=obj.get("category", ""),
                    prominence=obj.get("prominence"),
                    confidence=obj.get("confidence"),
                    first_appearance_timestamp=obj.get("first_appearance_timestamp"),
                ))

        created += 1

    await db.commit()
    return {"created": created, "replaced_existing": True}
