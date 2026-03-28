"""
Narralytica: Analytics router — Stage H "Wow Features".

Provides computed analytics endpoints for the frontend dashboards:
  - Mood Timeline: tone/mood arc across an episode's scenes
  - Screen Time: character appearance duration by episode or show
  - Scene DNA: radar-chart data for a scene's attributes
  - Dialog Search: full-text search across key_dialog JSON
  - AI Recommendations: "scenes like this" via embedding similarity
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text, func as sqlfunc, distinct, desc, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.embeddings import embed_query
from app.models.models import Scene, Episode, Show
from app.schemas.schemas import SceneOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# =============================================================================
# Mood Timeline — tone/mood/pacing arc across an episode
# =============================================================================

@router.get("/mood-timeline/{episode_id}")
async def mood_timeline(episode_id: int, db: AsyncSession = Depends(get_db)):
    """Return scene-by-scene mood data for timeline visualization.

    Each entry has the scene's start time, tone, mood, pacing, and
    explicitness dimensions — everything needed for a multi-track timeline.
    """
    result = await db.execute(
        select(Scene)
        .where(Scene.episode_id == episode_id)
        .order_by(Scene.start_timestamp)
    )
    scenes = result.scalars().all()
    if not scenes:
        raise HTTPException(status_code=404, detail="No scenes found for this episode")

    # Map tone/pacing to numeric intensities for chart rendering
    TONE_INTENSITY = {
        "comedic": 0.7, "humorous": 0.6, "lighthearted": 0.5, "playful": 0.5,
        "neutral": 0.3, "informational": 0.2,
        "dramatic": 0.6, "tense": 0.8, "suspenseful": 0.9, "dark": 0.9,
        "emotional": 0.7, "melancholic": 0.8, "sad": 0.8,
        "action": 0.8, "chaotic": 0.9, "frenetic": 1.0,
    }
    PACING_SPEED = {
        "slow": 0.2, "moderate": 0.5, "fast": 0.8, "building": 0.6, "frenetic": 1.0,
    }

    timeline = []
    for s in scenes:
        tone_str = (s.tone or "").lower()
        pacing_str = (s.scene_pacing or "").lower()
        timeline.append({
            "scene_id": s.id,
            "start": s.start_timestamp,
            "end": s.end_timestamp,
            "duration": s.duration,
            "tone": s.tone,
            "tone_intensity": TONE_INTENSITY.get(tone_str, 0.4),
            "mood": s.mood_ambience,
            "pacing": s.scene_pacing,
            "pacing_speed": PACING_SPEED.get(pacing_str, 0.5),
            "location": s.location,
            "characters": [c.get("name") for c in (s.characters_present or [])],
            "explicitness": {
                "language": s.explicitness_language,
                "violence": s.explicitness_violence,
                "sexual": s.explicitness_sexual,
                "substance": s.explicitness_substance,
                "thematic": s.explicitness_thematic,
            },
            "music_present": s.music_present,
            "plot_significance": s.plot_significance,
        })

    return {
        "episode_id": episode_id,
        "scene_count": len(timeline),
        "timeline": timeline,
    }


# =============================================================================
# Screen Time Dashboard — character duration across episodes
# =============================================================================

@router.get("/screen-time/{show_id}")
async def screen_time(
    show_id: int,
    season: int = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Calculate character screen time across a show or season.

    Sums scene durations where each character appears.
    Returns ranked list plus per-episode breakdown.
    """
    query = (
        select(Scene, Episode)
        .join(Episode, Scene.episode_id == Episode.id)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode_number, Scene.start_timestamp)
    )
    if season:
        query = query.where(Episode.season == season)

    result = await db.execute(query)
    rows = result.all()

    if not rows:
        raise HTTPException(status_code=404, detail="No indexed scenes for this show")

    # Aggregate screen time
    char_totals: dict[str, float] = {}
    char_episodes: dict[str, dict[str, float]] = {}  # char -> {ep_label: duration}

    for scene, episode in rows:
        ep_label = f"S{episode.season:02d}E{episode.episode_number:02d}"
        for char in (scene.characters_present or []):
            name = char.get("name", "Unknown")
            char_totals[name] = char_totals.get(name, 0) + scene.duration
            if name not in char_episodes:
                char_episodes[name] = {}
            char_episodes[name][ep_label] = char_episodes[name].get(ep_label, 0) + scene.duration

    # Sort by total screen time descending
    ranked = sorted(char_totals.items(), key=lambda x: -x[1])

    return {
        "show_id": show_id,
        "season": season,
        "characters": [
            {
                "name": name,
                "total_seconds": round(total, 1),
                "total_formatted": f"{int(total // 60)}m {int(total % 60)}s",
                "episodes": char_episodes.get(name, {}),
            }
            for name, total in ranked
        ],
    }


# =============================================================================
# Scene DNA — radar chart fingerprint
# =============================================================================

@router.get("/scene-dna/{scene_id}")
async def scene_dna(scene_id: int, db: AsyncSession = Depends(get_db)):
    """Return a "DNA fingerprint" for a scene as radar chart dimensions.

    Computes normalized scores (0-1) across: action, humor, drama,
    visual complexity, audio richness, dialog density, explicitness.
    """
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Action score: has actions text + pacing
    action_score = 0.0
    if scene.actions:
        action_score += 0.4
        if len(scene.actions) > 100:
            action_score += 0.2
    pacing_map = {"slow": 0.1, "moderate": 0.2, "fast": 0.3, "building": 0.25, "frenetic": 0.4}
    action_score += pacing_map.get((scene.scene_pacing or "").lower(), 0.15)

    # Humor score
    humor_score = 0.0
    if scene.visual_gags:
        humor_score += 0.35
    if scene.dialog_based_humor:
        humor_score += 0.35
    tone_humor = {"comedic": 0.3, "humorous": 0.25, "playful": 0.2, "lighthearted": 0.15}
    humor_score += tone_humor.get((scene.tone or "").lower(), 0.0)

    # Drama score
    drama_map = {"dramatic": 0.7, "tense": 0.8, "suspenseful": 0.9, "emotional": 0.7,
                 "melancholic": 0.8, "sad": 0.8, "dark": 0.9}
    drama_score = drama_map.get((scene.tone or "").lower(), 0.2)
    if scene.emotional_arc and len(scene.emotional_arc) > 50:
        drama_score = min(1.0, drama_score + 0.2)

    # Visual complexity
    visual_score = 0.0
    if scene.color_palette:
        visual_score += min(0.3, len(scene.color_palette) * 0.06)
    if scene.camera_movement:
        visual_score += 0.2
    if scene.scene_composition:
        visual_score += 0.2
    if scene.visual_style_notes:
        visual_score += 0.15
    if scene.lighting:
        visual_score += 0.15

    # Audio richness
    audio_score = 0.0
    if scene.music_present:
        audio_score += 0.35
    if scene.music_description:
        audio_score += 0.15
    if scene.sound_effects:
        audio_score += 0.25
    if scene.ambient_audio:
        audio_score += 0.25

    # Dialog density
    dialog_count = len(scene.key_dialog or [])
    dialog_score = min(1.0, dialog_count * 0.15)
    char_count = len(scene.characters_present or [])
    dialog_score = min(1.0, dialog_score + char_count * 0.1)

    # Explicitness (average of 5 dimensions, normalized to 0-1 from 0-5 scale)
    expl_avg = (
        (scene.explicitness_language or 0)
        + (scene.explicitness_violence or 0)
        + (scene.explicitness_sexual or 0)
        + (scene.explicitness_substance or 0)
        + (scene.explicitness_thematic or 0)
    ) / 25.0  # 5 dims * max 5 each

    # Narrative weight
    sig_map = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
    narrative_score = sig_map.get((scene.plot_significance or "").lower(), 0.3)
    if scene.continuity_notes:
        narrative_score = min(1.0, narrative_score + 0.15)
    if scene.cultural_references:
        narrative_score = min(1.0, narrative_score + len(scene.cultural_references) * 0.1)

    return {
        "scene_id": scene.id,
        "dimensions": {
            "action": round(min(1.0, action_score), 2),
            "humor": round(min(1.0, humor_score), 2),
            "drama": round(min(1.0, drama_score), 2),
            "visual": round(min(1.0, visual_score), 2),
            "audio": round(min(1.0, audio_score), 2),
            "dialog": round(min(1.0, dialog_score), 2),
            "explicitness": round(min(1.0, expl_avg), 2),
            "narrative": round(min(1.0, narrative_score), 2),
        },
        "metadata": {
            "tone": scene.tone,
            "pacing": scene.scene_pacing,
            "location": scene.location,
            "characters": [c.get("name") for c in (scene.characters_present or [])],
            "plot_significance": scene.plot_significance,
            "confidence": scene.overall_confidence,
        },
    }


# =============================================================================
# Dialog Search — full-text search across scene dialog
# =============================================================================

@router.get("/dialog-search")
async def dialog_search(
    q: str = Query(..., min_length=2),
    show_id: int = Query(None),
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search across all key_dialog and merged_transcript text.

    Returns matching scenes with the specific dialog lines highlighted.
    """
    like_pattern = f"%{q}%"

    query = (
        select(Scene, Episode)
        .join(Episode, Scene.episode_id == Episode.id)
        .where(
            Scene.key_dialog.cast(text("text")).ilike(like_pattern)
            | Scene.merged_transcript.cast(text("text")).ilike(like_pattern)
        )
        .order_by(Scene.overall_confidence.desc())
        .limit(limit)
    )
    if show_id:
        query = query.where(Episode.show_id == show_id)

    result = await db.execute(query)
    rows = result.all()

    results = []
    q_lower = q.lower()
    for scene, episode in rows:
        # Find matching dialog lines
        matching_lines = []
        for d in (scene.key_dialog or []):
            quote = d.get("exact_quote", "")
            if q_lower in quote.lower():
                matching_lines.append({
                    "speaker": d.get("speaker", "Unknown"),
                    "quote": quote,
                    "timestamp": d.get("timestamp"),
                })

        # Also check merged transcript
        for t in (scene.merged_transcript or []):
            txt = t.get("text", "")
            if q_lower in txt.lower() and not any(m["quote"] == txt for m in matching_lines):
                matching_lines.append({
                    "speaker": t.get("speaker", "Unknown"),
                    "quote": txt,
                    "timestamp": t.get("start"),
                })

        results.append({
            "scene_id": scene.id,
            "episode_id": episode.id,
            "episode_label": f"S{episode.season:02d}E{episode.episode_number:02d}",
            "episode_title": episode.title,
            "start_timestamp": scene.start_timestamp,
            "location": scene.location,
            "matching_lines": matching_lines[:5],
        })

    return {"query": q, "count": len(results), "results": results}


# =============================================================================
# AI Recommender — "scenes like this"
# =============================================================================

@router.get("/similar/{scene_id}")
async def similar_scenes(
    scene_id: int,
    limit: int = Query(8, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Find scenes similar to the given scene using embedding similarity.

    Uses the scene's existing description_embedding vector to find
    nearest neighbors via pgvector cosine distance.
    """
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Scene not found")
    if source.description_embedding is None:
        raise HTTPException(status_code=400, detail="Scene has no embedding")

    similarity_expr = (
        1 - Scene.description_embedding.cosine_distance(source.description_embedding)
    )

    query = (
        select(Scene, Episode, similarity_expr.label("similarity"))
        .join(Episode, Scene.episode_id == Episode.id)
        .where(Scene.id != scene_id)
        .where(Scene.description_embedding.isnot(None))
        .order_by(similarity_expr.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return {
        "source_scene_id": scene_id,
        "similar": [
            {
                "scene_id": scene.id,
                "episode_id": episode.id,
                "episode_label": f"S{episode.season:02d}E{episode.episode_number:02d}",
                "episode_title": episode.title,
                "similarity": round(float(sim), 4),
                "location": scene.location,
                "tone": scene.tone,
                "characters": [c.get("name") for c in (scene.characters_present or [])],
                "description": (scene.description_text or "")[:200],
                "start_timestamp": scene.start_timestamp,
            }
            for scene, episode, sim in rows
        ],
    }


# =============================================================================
# Episode Overview — summary stats for an episode
# =============================================================================

@router.get("/episode-overview/{episode_id}")
async def episode_overview(episode_id: int, db: AsyncSession = Depends(get_db)):
    """Quick stats overview for an episode's indexed scenes."""
    ep_result = await db.execute(
        select(Episode).options(selectinload(Episode.show)).where(Episode.id == episode_id)
    )
    episode = ep_result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    scenes_result = await db.execute(
        select(Scene).where(Scene.episode_id == episode_id).order_by(Scene.start_timestamp)
    )
    scenes = scenes_result.scalars().all()

    # Compute stats
    all_chars: dict[str, float] = {}
    tones: dict[str, int] = {}
    locations: dict[str, int] = {}
    total_dialog = 0

    for s in scenes:
        for c in (s.characters_present or []):
            name = c.get("name", "Unknown")
            all_chars[name] = all_chars.get(name, 0) + s.duration
        if s.tone:
            tones[s.tone] = tones.get(s.tone, 0) + 1
        if s.location:
            locations[s.location] = locations.get(s.location, 0) + 1
        total_dialog += len(s.key_dialog or [])

    return {
        "episode_id": episode_id,
        "show_name": episode.show.name if episode.show else "Unknown",
        "episode_title": episode.title,
        "episode_label": f"S{episode.season:02d}E{episode.episode_number:02d}",
        "scene_count": len(scenes),
        "total_duration": round(sum(s.duration for s in scenes), 1) if scenes else 0,
        "total_dialog_lines": total_dialog,
        "unique_characters": len(all_chars),
        "top_characters": sorted(all_chars.items(), key=lambda x: -x[1])[:10],
        "tone_distribution": dict(sorted(tones.items(), key=lambda x: -x[1])),
        "location_count": len(locations),
        "top_locations": sorted(locations.items(), key=lambda x: -x[1])[:8],
    }
