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
            characters_present=scene_data.get("characters_present", []),
            key_dialog=scene_data.get("key_dialog", []),
            actions=scene_data.get("actions"),
            interactions=scene_data.get("interactions"),
            mood_ambience=scene_data.get("mood_ambience"),
            color_palette=scene_data.get("color_palette", []),
            tropes_memes=scene_data.get("tropes_memes", []),
            explicitness=scene_data.get("explicitness", "none"),
            background=scene_data.get("background"),
            scene_transitions=scene_data.get("scene_transitions"),
            motivations_feelings=scene_data.get("motivations_feelings"),
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
