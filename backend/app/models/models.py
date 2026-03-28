from sqlalchemy import Boolean, Column, Integer, String, Float, Text, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Show(Base):
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    year = Column(Integer)
    network = Column(String(255))
    overview = Column(Text)
    genres = Column(JSON, default=[])
    sonarr_id = Column(Integer)           # Sonarr series ID for API calls
    tvdb_id = Column(Integer)             # TVDB ID for cross-referencing
    poster_url = Column(Text)             # From Sonarr/TVDB
    fanart_url = Column(Text)             # Backdrop art
    banner_url = Column(Text)             # Banner image
    clearlogo_url = Column(Text)          # Transparent logo
    media_path = Column(Text)             # Filesystem path on Plex server
    rating_value = Column(Float)          # TVDB/TMDB rating
    rating_votes = Column(Integer)        # Number of votes
    theme_config = Column(JSON, default={})

    # CutPrint™ calibration profile
    cutprint_threshold = Column(Float)
    cutprint_min_scene = Column(Integer)
    cutprint_genre = Column(String(50))
    cutprint_calibrated_at = Column(DateTime(timezone=True))
    cutprint_profile = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    episodes = relationship("Episode", back_populates="show", cascade="all, delete-orphan")


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True)
    show_id = Column(Integer, ForeignKey("shows.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    season = Column(Integer, nullable=False)
    episode_number = Column(Integer, nullable=False)
    duration_seconds = Column(Float)
    air_date = Column(String(20))         # From Sonarr (YYYY-MM-DD)
    overview = Column(Text)               # Episode synopsis from Sonarr
    sonarr_episode_id = Column(Integer)   # Sonarr episode ID
    file_path = Column(Text)
    compressed_path = Column(Text)
    status = Column(String(50), default="pending")
    gemini_cost_usd = Column(Float, default=0)
    indexed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    show = relationship("Show", back_populates="episodes")
    scenes = relationship("Scene", back_populates="episode", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("show_id", "season", "episode_number"),)


class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True)
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"))
    start_timestamp = Column(Float, nullable=False)
    end_timestamp = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)

    # Characters & Dialog
    characters_present = Column(JSON, default=[])         # [{name, confidence, is_speaking, screen_position}]
    key_dialog = Column(JSON, default=[])                 # [{speaker, quote, timestamp, emotion, volume_level}]
    character_interactions = Column(JSON, default=[])      # [{character_a, character_b, interaction_type, description}]
    character_motivations_feelings = Column(Text)

    # Actions & Humor
    actions = Column(Text)
    interactions = Column(Text)                           # Legacy field (kept for backward compat)
    visual_gags = Column(Text)
    dialog_based_humor = Column(Text)

    # Objects
    # objects_present now includes: state, spatial_relationship (via scene_objects table + raw JSON)

    # Location & Setting
    location = Column(Text)                               # Specific named location
    time_of_day = Column(String(20))                      # morning, afternoon, evening, night, ambiguous
    setting_type = Column(String(20))                     # interior, exterior, both
    background = Column(Text)                             # Legacy field

    # Visual & Cinematographic
    color_palette = Column(JSON, default=[])              # Hex color codes
    lighting = Column(Text)
    camera_shot_type = Column(Text)
    camera_movement = Column(Text)
    scene_composition = Column(Text)
    visual_style_notes = Column(Text)

    # Audio & Music
    music_present = Column(Boolean)                        # True/false for music in scene
    music_description = Column(Text)
    sound_effects = Column(Text)
    ambient_audio = Column(Text)

    # Mood & Tone
    mood_ambience = Column(Text)
    scene_pacing = Column(String(30))                     # fast, moderate, slow, building, frenetic
    tone = Column(String(50))                             # comedic, dramatic, tense, etc.
    emotional_arc = Column(Text)

    # Narrative & Context
    tropes_memes = Column(JSON, default=[])
    cultural_references = Column(JSON, default=[])
    recurring_gags = Column(Text)
    plot_significance = Column(String(20))                # low, medium, high, critical
    continuity_notes = Column(Text)

    # Explicitness (5 dimensions)
    explicitness = Column(String(50), default="none")     # Legacy single field
    explicitness_language = Column(Float, default=0)
    explicitness_violence = Column(Float, default=0)
    explicitness_sexual = Column(Float, default=0)
    explicitness_substance = Column(Float, default=0)
    explicitness_thematic = Column(Float, default=0)

    # Scene Structure
    scene_transitions = Column(Text)
    text_on_screen = Column(Text)

    # Search & Storage
    overall_confidence = Column(Float, default=0)
    thumbnail_path = Column(Text)
    description_embedding = Column(Vector(1536))
    description_text = Column(Text)
    merged_transcript = Column(JSON, default=[])
    raw_gemini_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    episode = relationship("Episode", back_populates="scenes")
    objects = relationship("SceneObject", back_populates="scene", cascade="all, delete-orphan")


class SceneObject(Base):
    __tablename__ = "scene_objects"

    id = Column(Integer, primary_key=True)
    scene_id = Column(Integer, ForeignKey("scenes.id", ondelete="CASCADE"))
    name = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    prominence = Column(Text)
    confidence = Column(Float)
    first_appearance_timestamp = Column(Float)

    scene = relationship("Scene", back_populates="objects")


class Tweak(Base):
    __tablename__ = "tweaks"

    id = Column(Integer, primary_key=True)
    scene_a_id = Column(Integer, ForeignKey("scenes.id"))
    scene_b_id = Column(Integer, ForeignKey("scenes.id"))
    transition_prompt = Column(Text, nullable=False)
    bridge_video_path = Column(Text)
    final_clip_path = Column(Text)
    status = Column(String(50), default="pending")
    veo_cost_usd = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True)
    query = Column(Text, nullable=False)
    result_count = Column(Integer, default=0)
    latency_ms = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
