"""
Narralytica: Library router — Thea integration via Sonarr/Radarr APIs.

Queries Sonarr (TV) and Radarr (movies) running on the same Hetzner server
to pull show metadata, artwork, and episode information. This replaces
manual data entry — adding a show to Narralytica automatically populates
all metadata from the existing media management stack.
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Show, Episode

router = APIRouter(prefix="/library", tags=["library"])


# --- Sonarr API helpers ---

async def _sonarr_get(path: str) -> dict | list:
    """Make a GET request to the local Sonarr API."""
    if not settings.sonarr_api_key:
        raise HTTPException(status_code=503, detail="Sonarr API key not configured")
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            f"{settings.sonarr_url}/api/v3{path}",
            headers={"X-Api-Key": settings.sonarr_api_key},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=f"Sonarr error: {r.text[:200]}")
        return r.json()


def _extract_image(images: list, cover_type: str) -> str | None:
    """Extract an image URL from Sonarr's images array by cover type."""
    for img in images or []:
        if img.get("coverType") == cover_type:
            return img.get("remoteUrl") or img.get("url")
    return None


# --- Browse Sonarr Library ---

@router.get("/sonarr/shows")
async def browse_sonarr_shows(
    q: str = Query(None, description="Filter shows by name"),
):
    """Browse all TV shows available in Sonarr.

    Returns a lightweight list for the "Browse Library" UI.
    Use POST /library/import/{sonarr_id} to import a show into Narralytica.
    """
    shows = await _sonarr_get("/series")
    results = []
    for s in shows:
        if q and q.lower() not in s.get("title", "").lower():
            continue
        results.append({
            "sonarr_id": s["id"],
            "tvdb_id": s.get("tvdbId"),
            "title": s.get("title"),
            "year": s.get("year"),
            "network": s.get("network"),
            "genres": s.get("genres", []),
            "season_count": s.get("seasonCount"),
            "episode_count": s.get("episodeCount"),
            "episode_file_count": s.get("episodeFileCount"),
            "overview": (s.get("overview") or "")[:200],
            "poster_url": _extract_image(s.get("images", []), "poster"),
            "fanart_url": _extract_image(s.get("images", []), "fanart"),
            "path": s.get("path"),
            "rating": s.get("ratings", {}).get("value"),
        })
    return {"count": len(results), "shows": results}


@router.get("/sonarr/shows/{sonarr_id}/episodes")
async def browse_sonarr_episodes(
    sonarr_id: int,
    season: int = Query(None, description="Filter by season number"),
):
    """Browse episodes for a Sonarr show. Optionally filter by season."""
    episodes = await _sonarr_get(f"/episode?seriesId={sonarr_id}")
    results = []
    for ep in episodes:
        if season is not None and ep.get("seasonNumber") != season:
            continue
        if ep.get("seasonNumber", 0) == 0:
            continue  # Skip specials
        results.append({
            "sonarr_episode_id": ep["id"],
            "title": ep.get("title"),
            "season": ep.get("seasonNumber"),
            "episode_number": ep.get("episodeNumber"),
            "air_date": ep.get("airDate"),
            "overview": ep.get("overview"),
            "has_file": ep.get("hasFile", False),
            "file_path": ep.get("episodeFile", {}).get("path") if ep.get("episodeFile") else None,
            "file_size_mb": round(ep.get("episodeFile", {}).get("size", 0) / 1024 / 1024) if ep.get("episodeFile") else None,
            "runtime": ep.get("runtime"),
        })
    results.sort(key=lambda e: (e["season"], e["episode_number"]))
    return {"count": len(results), "episodes": results}


# --- Import from Sonarr into Narralytica ---

@router.post("/import/{sonarr_id}")
async def import_show_from_sonarr(
    sonarr_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Import a TV show from Sonarr into Narralytica.

    Pulls all metadata and artwork. Creates the Show record plus Episode
    records for every episode that has a file on disk. Does NOT start
    the processing pipeline — that's a separate step.
    """
    # Check if already imported
    existing = await db.execute(select(Show).where(Show.sonarr_id == sonarr_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Show already imported from Sonarr")

    # Fetch full show data from Sonarr
    series_list = await _sonarr_get("/series")
    series = next((s for s in series_list if s["id"] == sonarr_id), None)
    if not series:
        raise HTTPException(status_code=404, detail=f"Sonarr series {sonarr_id} not found")

    # Create show
    ratings = series.get("ratings", {})
    show = Show(
        name=series["title"],
        year=series.get("year"),
        network=series.get("network"),
        overview=series.get("overview"),
        genres=series.get("genres", []),
        sonarr_id=sonarr_id,
        tvdb_id=series.get("tvdbId"),
        poster_url=_extract_image(series.get("images", []), "poster"),
        fanart_url=_extract_image(series.get("images", []), "fanart"),
        banner_url=_extract_image(series.get("images", []), "banner"),
        clearlogo_url=_extract_image(series.get("images", []), "clearlogo"),
        media_path=series.get("path"),
        rating_value=ratings.get("value"),
        rating_votes=ratings.get("votes"),
        theme_config={},
    )
    db.add(show)
    await db.flush()  # Get show.id

    # Fetch episodes from Sonarr
    sonarr_episodes = await _sonarr_get(f"/episode?seriesId={sonarr_id}")

    episodes_created = 0
    for ep in sonarr_episodes:
        if ep.get("seasonNumber", 0) == 0:
            continue  # Skip specials

        episode = Episode(
            show_id=show.id,
            title=ep.get("title", f"Episode {ep.get('episodeNumber', '?')}"),
            season=ep["seasonNumber"],
            episode_number=ep["episodeNumber"],
            air_date=ep.get("airDate"),
            overview=ep.get("overview"),
            sonarr_episode_id=ep["id"],
            duration_seconds=ep.get("runtime", 0) * 60 if ep.get("runtime") else None,
            file_path=ep.get("episodeFile", {}).get("path") if ep.get("episodeFile") else None,
            status="pending",
        )
        db.add(episode)
        episodes_created += 1

    await db.commit()
    await db.refresh(show)

    return {
        "show_id": show.id,
        "name": show.name,
        "sonarr_id": show.sonarr_id,
        "episodes_created": episodes_created,
        "poster_url": show.poster_url,
        "fanart_url": show.fanart_url,
        "message": f"Imported '{show.name}' with {episodes_created} episodes",
    }


# --- Shows management ---

@router.get("/shows")
async def list_shows(db: AsyncSession = Depends(get_db)):
    """List all shows in Narralytica."""
    from sqlalchemy import func as sqlfunc
    result = await db.execute(select(Show).order_by(Show.name))
    shows = result.scalars().all()

    # Count episodes per show without lazy loading
    ep_counts = {}
    count_result = await db.execute(
        select(Episode.show_id, sqlfunc.count(Episode.id))
        .group_by(Episode.show_id)
    )
    for show_id, count in count_result.all():
        ep_counts[show_id] = count

    return [
        {
            "id": s.id,
            "name": s.name,
            "year": s.year,
            "network": s.network,
            "genres": s.genres,
            "poster_url": s.poster_url,
            "fanart_url": s.fanart_url,
            "sonarr_id": s.sonarr_id,
            "episode_count": ep_counts.get(s.id, 0),
        }
        for s in shows
    ]


@router.get("/shows/{show_id}")
async def get_show_detail(show_id: int, db: AsyncSession = Depends(get_db)):
    """Get full show detail with episode list."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    eps_result = await db.execute(
        select(Episode)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode_number)
    )
    episodes = eps_result.scalars().all()

    # Group episodes by season
    seasons = {}
    for ep in episodes:
        s = ep.season
        if s not in seasons:
            seasons[s] = []
        seasons[s].append({
            "id": ep.id,
            "title": ep.title,
            "episode_number": ep.episode_number,
            "air_date": ep.air_date,
            "overview": ep.overview,
            "status": ep.status,
            "has_file": ep.file_path is not None,
            "duration_seconds": ep.duration_seconds,
        })

    return {
        "id": show.id,
        "name": show.name,
        "year": show.year,
        "network": show.network,
        "overview": show.overview,
        "genres": show.genres,
        "poster_url": show.poster_url,
        "fanart_url": show.fanart_url,
        "banner_url": show.banner_url,
        "clearlogo_url": show.clearlogo_url,
        "media_path": show.media_path,
        "rating_value": show.rating_value,
        "rating_votes": show.rating_votes,
        "theme_config": show.theme_config,
        "seasons": seasons,
        "total_episodes": len(episodes),
    }
