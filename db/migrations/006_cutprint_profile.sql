-- CutPrint™ profile storage on shows table
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_threshold FLOAT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_min_scene INTEGER;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_genre VARCHAR(50);
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_calibrated_at TIMESTAMPTZ;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_profile JSONB;
