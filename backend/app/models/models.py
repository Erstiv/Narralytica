from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Show(Base):
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    theme_config = Column(JSON, default={})
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
    characters_present = Column(JSON, default=[])
    key_dialog = Column(JSON, default=[])
    actions = Column(Text)
    interactions = Column(Text)
    mood_ambience = Column(Text)
    color_palette = Column(JSON, default=[])
    tropes_memes = Column(JSON, default=[])
    explicitness = Column(String(50), default="none")
    background = Column(Text)
    scene_transitions = Column(Text)
    motivations_feelings = Column(Text)
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
