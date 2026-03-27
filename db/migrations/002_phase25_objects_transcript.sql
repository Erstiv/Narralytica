-- Phase 2.5: Object tagging + merged transcript support

-- Scene objects table (normalized from Gemini's objects_present)
CREATE TABLE IF NOT EXISTS scene_objects (
    id SERIAL PRIMARY KEY,
    scene_id INTEGER REFERENCES scenes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    prominence TEXT,
    confidence FLOAT,
    first_appearance_timestamp FLOAT
);

CREATE INDEX IF NOT EXISTS idx_objects_scene ON scene_objects(scene_id);
CREATE INDEX IF NOT EXISTS idx_objects_name ON scene_objects(name);
CREATE INDEX IF NOT EXISTS idx_objects_category ON scene_objects(category);

-- Add merged transcript column to scenes
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS merged_transcript JSONB DEFAULT '[]';
