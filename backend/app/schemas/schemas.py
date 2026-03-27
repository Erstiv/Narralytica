from pydantic import BaseModel
from datetime import datetime


# --- Shows ---
class ShowOut(BaseModel):
    id: int
    name: str
    year: int | None = None
    network: str | None = None
    overview: str | None = None
    genres: list = []
    sonarr_id: int | None = None
    tvdb_id: int | None = None
    poster_url: str | None = None
    fanart_url: str | None = None
    banner_url: str | None = None
    clearlogo_url: str | None = None
    media_path: str | None = None
    rating_value: float | None = None
    rating_votes: int | None = None
    theme_config: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class ShowCreate(BaseModel):
    """Create a show manually (without Sonarr)."""
    name: str
    year: int | None = None
    theme_config: dict = {}


# --- Episodes ---
class EpisodeOut(BaseModel):
    id: int
    show_id: int
    title: str
    season: int
    episode_number: int
    duration_seconds: float | None
    air_date: str | None = None
    overview: str | None = None
    status: str
    gemini_cost_usd: float
    indexed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EpisodeStatusUpdate(BaseModel):
    status: str


# --- Scenes ---
class SceneOut(BaseModel):
    id: int
    episode_id: int
    start_timestamp: float
    end_timestamp: float
    duration: float
    characters_present: list
    key_dialog: list
    actions: str | None
    interactions: str | None
    mood_ambience: str | None
    color_palette: list
    tropes_memes: list
    explicitness: str
    background: str | None
    scene_transitions: str | None
    motivations_feelings: str | None
    overall_confidence: float
    thumbnail_path: str | None
    description_text: str | None
    merged_transcript: list | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SceneObjectOut(BaseModel):
    id: int
    scene_id: int
    name: str
    category: str
    prominence: str | None
    confidence: float | None
    first_appearance_timestamp: float | None

    model_config = {"from_attributes": True}


class SceneBulkCreate(BaseModel):
    """For ingesting Gemini + Whisper merged output."""
    scenes: list[dict]


# --- Search ---
class SearchRequest(BaseModel):
    query: str
    min_confidence: float = 0.0
    characters: list[str] | None = None
    limit: int = 20


class SearchResult(BaseModel):
    scene: SceneOut
    similarity: float


# --- Tweaks ---
class TweakCreate(BaseModel):
    scene_a_id: int
    scene_b_id: int
    transition_prompt: str


class TweakOut(BaseModel):
    id: int
    scene_a_id: int
    scene_b_id: int
    transition_prompt: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
