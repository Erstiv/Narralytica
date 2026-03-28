-- Narralytica: Expanded metadata schema (Stage B)
-- Adds 20+ new fields to scenes table for full 35+ field coverage.
-- Splits single explicitness string into 5 dimensional scores.

-- Characters & Dialog (enriched)
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS character_interactions JSONB DEFAULT '[]';
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS character_motivations_feelings TEXT;

-- Visual & Humor
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS visual_gags TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS dialog_based_humor TEXT;

-- Location (replaces generic "background")
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS time_of_day VARCHAR(20);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS setting_type VARCHAR(20);

-- Cinematography
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS lighting TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS camera_shot_type TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS camera_movement TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS scene_composition TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS visual_style_notes TEXT;

-- Audio & Music
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS music_present BOOLEAN DEFAULT false;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS music_description TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS sound_effects TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS ambient_audio TEXT;

-- Mood & Tone (enriched)
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS scene_pacing VARCHAR(30);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS tone VARCHAR(50);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS emotional_arc TEXT;

-- Narrative & Context
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS cultural_references JSONB DEFAULT '[]';
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS recurring_gags TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS plot_significance VARCHAR(20);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS continuity_notes TEXT;

-- Explicitness (5 dimensions, replacing single string)
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS explicitness_language FLOAT DEFAULT 0;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS explicitness_violence FLOAT DEFAULT 0;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS explicitness_sexual FLOAT DEFAULT 0;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS explicitness_substance FLOAT DEFAULT 0;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS explicitness_thematic FLOAT DEFAULT 0;

-- Text on screen
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS text_on_screen TEXT;
