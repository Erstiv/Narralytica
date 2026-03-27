-- Narralytica: Initial schema with pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Shows table (extensible beyond Simpsons)
CREATE TABLE shows (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    theme_config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Episodes table
CREATE TABLE episodes (
    id SERIAL PRIMARY KEY,
    show_id INTEGER REFERENCES shows(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    season INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    duration_seconds FLOAT,
    file_path TEXT,
    compressed_path TEXT,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, compressing, detecting, indexing, ready, error
    gemini_cost_usd FLOAT DEFAULT 0,
    indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(show_id, season, episode_number)
);

-- Scenes table (core of the intelligence layer)
CREATE TABLE scenes (
    id SERIAL PRIMARY KEY,
    episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
    start_timestamp FLOAT NOT NULL,
    end_timestamp FLOAT NOT NULL,
    duration FLOAT NOT NULL,
    characters_present JSONB DEFAULT '[]',       -- [{name, confidence}]
    key_dialog JSONB DEFAULT '[]',               -- [{speaker, exact_quote, timestamp}]
    actions TEXT,
    interactions TEXT,
    mood_ambience TEXT,
    color_palette JSONB DEFAULT '[]',
    tropes_memes JSONB DEFAULT '[]',
    explicitness VARCHAR(50) DEFAULT 'none',
    background TEXT,
    scene_transitions TEXT,
    motivations_feelings TEXT,
    overall_confidence FLOAT DEFAULT 0,
    thumbnail_path TEXT,
    description_embedding vector(1536),           -- for pgvector similarity search
    description_text TEXT,                        -- human-readable scene summary
    raw_gemini_json JSONB,                        -- preserve full Gemini response
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for hybrid search
CREATE INDEX idx_scenes_episode ON scenes(episode_id);
CREATE INDEX idx_scenes_confidence ON scenes(overall_confidence);
CREATE INDEX idx_scenes_timestamps ON scenes(start_timestamp, end_timestamp);
CREATE INDEX idx_scenes_embedding ON scenes USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 10);

-- Full-text search on dialog
CREATE INDEX idx_scenes_dialog ON scenes USING gin(key_dialog jsonb_path_ops);

-- Tweak Studio: generated clips
CREATE TABLE tweaks (
    id SERIAL PRIMARY KEY,
    scene_a_id INTEGER REFERENCES scenes(id),
    scene_b_id INTEGER REFERENCES scenes(id),
    transition_prompt TEXT NOT NULL,
    bridge_video_path TEXT,
    final_clip_path TEXT,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, generating, stitching, ready, error
    veo_cost_usd FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Search history for analytics
CREATE TABLE search_history (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    result_count INTEGER DEFAULT 0,
    latency_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed the Simpsons show
INSERT INTO shows (name, theme_config) VALUES (
    'The Simpsons',
    '{"primary_color": "#FFD521", "secondary_color": "#000000", "font": "Akbar", "style": "playful"}'
);

-- Seed the POC episode
INSERT INTO episodes (show_id, title, season, episode_number, duration_seconds, status) VALUES (
    1, 'Last Exit to Springfield', 4, 17, 1320, 'pending'
);
