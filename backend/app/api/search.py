import time
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, text, func as sqlfunc, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.embeddings import embed_query
from app.models.models import Scene, Episode, SearchHistory
from app.schemas.schemas import SearchRequest, SearchResult, SceneOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


def _apply_filters(query, body: SearchRequest):
    """Apply all SQL filters from the search request to a query."""
    if body.min_confidence:
        query = query.where(Scene.overall_confidence >= body.min_confidence)

    if body.characters:
        for char in body.characters:
            query = query.where(
                Scene.characters_present.cast(text("text")).ilike(f"%{char}%")
            )

    if body.tone:
        query = query.where(Scene.tone == body.tone)

    if body.plot_significance:
        query = query.where(Scene.plot_significance == body.plot_significance)

    if body.setting_type:
        query = query.where(Scene.setting_type == body.setting_type)

    if body.max_explicitness_violence is not None:
        query = query.where(Scene.explicitness_violence <= body.max_explicitness_violence)

    if body.max_explicitness_language is not None:
        query = query.where(Scene.explicitness_language <= body.max_explicitness_language)

    if body.show_id:
        query = query.join(Episode, Scene.episode_id == Episode.id).where(
            Episode.show_id == body.show_id
        )

    if body.episode_id:
        query = query.where(Scene.episode_id == body.episode_id)

    return query


@router.post("/", response_model=list[SearchResult])
async def search_scenes(body: SearchRequest, db: AsyncSession = Depends(get_db)):
    """Hybrid search: vector similarity + SQL filters.

    Strategy:
    1. Embed the query text via Gemini text-embedding-004
    2. Find scenes by cosine similarity (pgvector)
    3. Apply SQL filters (characters, tone, explicitness, etc.)
    4. Return ranked results with similarity scores
    """
    start = time.time()

    try:
        query_embedding = await embed_query(body.query)
    except Exception as e:
        logger.warning(f"Embedding failed, falling back to text search: {e}")
        query_embedding = None

    if query_embedding is not None:
        similarity_expr = (
            1 - Scene.description_embedding.cosine_distance(query_embedding)
        )

        query = (
            select(Scene, similarity_expr.label("similarity"))
            .where(Scene.description_embedding.isnot(None))
        )
        query = _apply_filters(query, body)
        query = query.order_by(similarity_expr.desc()).limit(body.limit)

        result = await db.execute(query)
        rows = result.all()

        results = [
            SearchResult(
                scene=SceneOut.model_validate(row[0]),
                similarity=round(float(row[1]), 4),
            )
            for row in rows
        ]
    else:
        # Fallback: text-based search
        query = select(Scene)
        query = _apply_filters(query, body)

        if body.query:
            like_pattern = f"%{body.query}%"
            query = query.where(
                Scene.key_dialog.cast(text("text")).ilike(like_pattern)
                | Scene.description_text.ilike(like_pattern)
                | Scene.actions.ilike(like_pattern)
            )

        query = query.order_by(Scene.overall_confidence.desc()).limit(body.limit)
        result = await db.execute(query)
        scenes = result.scalars().all()

        results = [
            SearchResult(
                scene=SceneOut.model_validate(scene),
                similarity=0.0,
            )
            for scene in scenes
        ]

    latency = (time.time() - start) * 1000

    db.add(SearchHistory(
        query=body.query,
        result_count=len(results),
        latency_ms=latency,
    ))
    await db.commit()

    logger.info(f"Search '{body.query}': {len(results)} results in {latency:.0f}ms")
    return results


@router.get("/facets")
async def get_search_facets(db: AsyncSession = Depends(get_db)):
    """Return available filter values for the search sidebar.

    Queries the indexed scenes to find all distinct values for
    filterable fields. Used by the frontend to populate dropdowns.
    """
    # Characters: extract distinct names from JSON arrays
    char_result = await db.execute(text("""
        SELECT DISTINCT jsonb_array_elements(characters_present::jsonb)->>'name' AS name
        FROM scenes
        WHERE characters_present IS NOT NULL
        ORDER BY name
    """))
    characters = [row[0] for row in char_result.all() if row[0]]

    # Simple distinct values for categorical fields
    tone_result = await db.execute(
        select(distinct(Scene.tone)).where(Scene.tone.isnot(None)).order_by(Scene.tone)
    )
    tones = [row[0] for row in tone_result.all()]

    pacing_result = await db.execute(
        select(distinct(Scene.scene_pacing)).where(Scene.scene_pacing.isnot(None)).order_by(Scene.scene_pacing)
    )
    pacings = [row[0] for row in pacing_result.all()]

    plot_result = await db.execute(
        select(distinct(Scene.plot_significance)).where(Scene.plot_significance.isnot(None)).order_by(Scene.plot_significance)
    )
    plot_levels = [row[0] for row in plot_result.all()]

    setting_result = await db.execute(
        select(distinct(Scene.setting_type)).where(Scene.setting_type.isnot(None)).order_by(Scene.setting_type)
    )
    settings = [row[0] for row in setting_result.all()]

    return {
        "characters": characters,
        "tones": tones,
        "pacings": pacings,
        "plot_significance": plot_levels,
        "setting_types": settings,
    }
