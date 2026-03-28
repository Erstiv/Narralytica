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

    # Characters & Dialog
    characters_present: list = []
    key_dialog: list = []
    character_interactions: list = []
    character_motivations_feelings: str | None = None

    # Actions & Humor
    actions: str | None = None
    interactions: str | None = None
    visual_gags: str | None = None
    dialog_based_humor: str | None = None

    # Location & Setting
    location: str | None = None
    time_of_day: str | None = None
    setting_type: str | None = None
    background: str | None = None

    # Visual & Cinematographic
    color_palette: list = []
    lighting: str | None = None
    camera_shot_type: str | None = None
    camera_movement: str | None = None
    scene_composition: str | None = None
    visual_style_notes: str | None = None

    # Audio & Music
    music_present: bool | None = None
    music_description: str | None = None
    sound_effects: str | None = None
    ambient_audio: str | None = None

    # Mood & Tone
    mood_ambience: str | None = None
    scene_pacing: str | None = None
    tone: str | None = None
    emotional_arc: str | None = None

    # Narrative & Context
    tropes_memes: list = []
    cultural_references: list = []
    recurring_gags: str | None = None
    plot_significance: str | None = None
    continuity_notes: str | None = None

    # Explicitness (5 dimensions)
    explicitness: str = "none"
    explicitness_language: float = 0
    explicitness_violence: float = 0
    explicitness_sexual: float = 0
    explicitness_substance: float = 0
    explicitness_thematic: float = 0

    # Scene Structure
    scene_transitions: str | None = None
    text_on_screen: str | None = None

    # Search & Meta
    overall_confidence: float = 0
    thumbnail_path: str | None = None
    description_text: str | None = None
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
    tone: str | None = None
    plot_significance: str | None = None
    setting_type: str | None = None
    max_explicitness_violence: float | None = None
    max_explicitness_language: float | None = None
    show_id: int | None = None
    episode_id: int | None = None
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
